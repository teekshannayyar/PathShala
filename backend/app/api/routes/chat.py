import logging
from typing import Annotated, Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.orm import Session

from app.api.deps import get_owned_document
from app.api.routes.auth import get_current_user
from app.core.rate_limit import CHAT_LIMIT, limiter
from app.core.timezone import get_user_tz
from app.models.database import get_db
from app.models.models import Message
from app.services.activity_service import record_activity
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_QUESTION_CHARS = 4000

class ChatRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)]
    document_id: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str

    model_config = ConfigDict(from_attributes=True)

@router.get("/history/{document_id}", response_model=List[MessageResponse])
def get_chat_history(document_id: int, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    get_owned_document(db, document_id, current_user)
    return db.query(Message).filter(Message.document_id == document_id).order_by(Message.created_at.asc()).all()

@router.post("/", response_model=ChatResponse)
@limiter.limit(CHAT_LIMIT)
def ask_question(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
    tz: ZoneInfo = Depends(get_user_tz),
    llm_service: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    relevant_chunks = []
    sources = []
    history = []

    # Ownership check must happen before anything is written for this user.
    if body.document_id is not None:
        get_owned_document(db, body.document_id, current_user)

    # Record permanent activity log for streak
    record_activity(db, current_user, tz)
    db.commit()

    # If a document is provided, fetch history and search for relevant context
    if body.document_id:
        # Save user message
        user_msg = Message(document_id=body.document_id, role="user", content=body.question)
        db.add(user_msg)
        db.commit()

        # Fetch last 5 messages for memory
        past_msgs = db.query(Message).filter(Message.document_id == body.document_id).order_by(Message.created_at.desc()).limit(5).all()
        # Reverse to chronological order
        past_msgs.reverse()
        history = [{"role": msg.role, "content": msg.content} for msg in past_msgs[:-1]] # exclude the one we just added

        # Search vector DB
        results = embedding_service.search(body.question, n_results=3, document_id=body.document_id)
        if results:
            relevant_chunks = results
            for res in results:
                sources.append(res['text'][:100] + "...") 

    # Pass history, chunks, and question to the LLM
    try:
        answer = llm_service.generate_response(body.question, context_chunks=relevant_chunks, history=history)
    except Exception:
        logger.exception("LLM request failed")
        raise HTTPException(status_code=502, detail="The AI service is unavailable, please try again")
    
    if body.document_id:
        # Save assistant message
        asst_msg = Message(document_id=body.document_id, role="assistant", content=answer)
        db.add(asst_msg)
        db.commit()

    return ChatResponse(answer=answer, sources=sources)
