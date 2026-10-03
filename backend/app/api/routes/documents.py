from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_owned_document
from app.models.database import get_db
from app.models.models import Document
from app.models.schemas import DocumentResponse
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.pdf_service import PDFService
from app.services.upload_service import max_upload_bytes, save_pdf_upload
from app.api.routes.auth import get_current_user
from app.core.config import settings
from app.core.rate_limit import UPLOAD_LIMIT, limiter
from app.core.timezone import get_user_tz
from app.services.activity_service import record_activity
from datetime import timedelta
from typing import Annotated, List
from zoneinfo import ZoneInfo
import os

# A document still "processing" after this long is assumed stuck (e.g. the
# server restarted mid-task) and may be reprocessed.
STALE_PROCESSING_MINUTES = 10

# Allowance for multipart boundaries/headers on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024

router = APIRouter()

@router.get("/", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .all()
    )

@router.post("/upload", response_model=DocumentResponse)
@limiter.limit(UPLOAD_LIMIT)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
    tz: ZoneInfo = Depends(get_user_tz),
):
    # Fail fast on an oversized declared body; save_pdf_upload enforces the
    # real limit while streaming, since Content-Length can be absent or wrong.
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_upload_bytes() + MULTIPART_OVERHEAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    stored_path, size_bytes, display_name = await save_pdf_upload(file)

    # Create the document in database
    try:
        db_doc = Document(
            filename=display_name,
            file_path=stored_path,
            file_size=size_bytes,
            owner_id=current_user,
            processing_status="processing",
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
    except Exception:
        db.rollback()
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise

    # Record permanent activity log for streak
    record_activity(db, current_user, tz)
    db.commit()

    # Process it in the background
    background_tasks.add_task(PDFService.process_document, db_doc.id)

    db.refresh(db_doc)
    return db_doc

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete file from disk
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
        
    # Delete from ChromaDB
    embedding_service.delete_document(document_id)
    
    # Delete from DB (Messages cascade due to our relationship)
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully"}

def _is_stale(db: Session, document_id: int) -> bool:
    """True if the document hasn't been touched for STALE_PROCESSING_MINUTES.

    Compared in SQL so the DB clock is used on both sides."""
    last_touched = func.coalesce(Document.updated_at, Document.created_at)
    cutoff = func.now() - timedelta(minutes=STALE_PROCESSING_MINUTES)
    return bool(
        db.query(last_touched < cutoff).filter(Document.id == document_id).scalar()
    )

@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    """Re-run extraction and embedding, e.g. for documents uploaded before
    original_text was stored, or after a failed run."""
    doc = get_owned_document(db, document_id, current_user)

    if doc.processing_status == "processing" and not _is_stale(db, doc.id):
        raise HTTPException(status_code=409, detail="Document is already processing")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=410, detail="The original PDF is no longer available; please upload it again")

    doc.processing_status = "processing"
    doc.processing_error = None
    doc.embedding_complete = False
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(PDFService.process_document, doc.id)
    return doc

from pydantic import BaseModel, StringConstraints

# Limits match the documents.filename / documents.folder column sizes, so bad
# input is a 422 instead of a database error.
class RenameRequest(BaseModel):
    filename: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]

class MoveFolderRequest(BaseModel):
    folder: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

class BulkDeleteRequest(BaseModel):
    document_ids: List[int]

@router.put("/{document_id}/rename", response_model=DocumentResponse)
def rename_document(document_id: int, request: RenameRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.filename = request.filename
    db.commit()
    db.refresh(doc)
    return doc

@router.put("/{document_id}/folder", response_model=DocumentResponse)
def move_document_to_folder(document_id: int, request: MoveFolderRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.folder = request.folder
    db.commit()
    db.refresh(doc)
    return doc

@router.post("/bulk-delete")
def bulk_delete_documents(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    docs = db.query(Document).filter(Document.id.in_(request.document_ids), Document.owner_id == current_user).all()
    
    deleted_ids = []
    for doc in docs:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        embedding_service.delete_document(doc.id)
        db.delete(doc)
        deleted_ids.append(doc.id)
        
    db.commit()
    return {"message": f"Successfully deleted {len(deleted_ids)} documents", "deleted_ids": deleted_ids}
