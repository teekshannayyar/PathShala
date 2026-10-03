from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import documents, chat, auth, quizzes

# The schema is managed by Alembic (`alembic upgrade head`); startup never
# creates or alters tables.

app = FastAPI(title="PathShala API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect our API endpoints
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(quizzes.router, prefix="/api/quizzes", tags=["Quizzes"])

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "llm_provider": "groq",
        "model": settings.GROQ_MODEL
    }
