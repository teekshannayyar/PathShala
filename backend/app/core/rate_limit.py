"""Per-client-IP rate limits (slowapi). Behind a proxy, uvicorn must run with
--proxy-headers so request.client is the real client, not the proxy."""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

AUTH_LIMIT = "10/minute"          # login, register, Google sign-in
PASSWORD_CHANGE_LIMIT = "10/hour"
CHAT_LIMIT = "30/minute"
QUIZ_GENERATE_LIMIT = "10/hour"
UPLOAD_LIMIT = "20/hour"

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI or "memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # Like slowapi's default handler, but the message goes in "detail", which
    # is where the frontend reads FastAPI errors from.
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests ({exc.detail}). Please wait and try again."},
    )
