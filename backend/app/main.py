from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.routes import documents, chat, auth, quizzes

# The schema is managed by Alembic (`alembic upgrade head`); startup never
# creates or alters tables.

app = FastAPI(title="PathShala API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
# Pure-ASGI variant of SlowAPIMiddleware (no BaseHTTPMiddleware buffering).
# It enforces default limits; per-route limits are the @limiter.limit decorators.
app.add_middleware(SlowAPIASGIMiddleware)

# Added last so it is the outermost middleware: even a 429 carries CORS
# headers, so the browser can show the error instead of a CORS failure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
