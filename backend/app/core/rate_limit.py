"""Per-client-IP rate limits (slowapi).

The client IP is the CLIENT_IP_HEADER request header when that's configured
(a header the platform's edge proxy sets and overwrites, such as Cloudflare's
CF-Connecting-IP), otherwise the socket peer `request.client.host`. Behind a
proxy that header is the only trustworthy source: X-Forwarded-For is appended
to, so its left-most entry is whatever the client sent."""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

AUTH_LIMIT = "10/minute"          # login, register, Google sign-in
PASSWORD_CHANGE_LIMIT = "10/hour"
CHAT_LIMIT = "30/minute"
QUIZ_GENERATE_LIMIT = "10/hour"
UPLOAD_LIMIT = "20/hour"


def client_ip(request: Request) -> str:
    header = (settings.CLIENT_IP_HEADER or "").strip()
    if header:
        value = request.headers.get(header, "").split(",")[0].strip()
        if value:
            return value
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=client_ip,
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
