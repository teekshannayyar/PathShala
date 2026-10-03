from typing import Annotated, Optional

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr, StringConstraints
from sqlalchemy import func
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import bcrypt
import re
import jwt
import datetime

from app.models.database import get_db
from app.models.models import User
from app.core.config import settings
from app.core.rate_limit import AUTH_LIMIT, PASSWORD_CHANGE_LIMIT, limiter
from app.core.timezone import get_user_tz, local_date, to_local_date
from app.services.embedding_service import EmbeddingService, get_embedding_service

router = APIRouter()

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72

class GoogleLoginRequest(BaseModel):
    credential: str

INVALID_LOGIN = "Invalid email or password"

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class LoginRequest(BaseModel):
    # Plain str, not EmailStr: accounts created before validation existed
    # must still be able to log in.
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Name


class UpdateProfileRequest(BaseModel):
    name: Name


class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str
    # Google-only accounts prove it's really them with a fresh Google ID token.
    google_credential: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    user: dict

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_user_by_email(db: Session, email: str):
    """Case-insensitive lookup, so accounts stored before emails were
    lowercased are still found. Oldest account wins if legacy rows differ
    only by case."""
    return (
        db.query(User)
        .filter(func.lower(User.email) == normalize_email(email))
        .order_by(User.id)
        .first()
    )


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture or "",
        "has_password": bool(user.hashed_password),
    }


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="Invalid token")
    # A token outlives its account (e.g. after deletion): treat it as invalid.
    if db.query(User.id).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def validate_new_password(password: str) -> None:
    """The signup rules, for every new password. The frontend checks the
    same ones (Auth.jsx, ProfileSettings.jsx)."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    # bcrypt only uses the first 72 bytes and bcrypt>=5 raises beyond that.
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(status_code=400, detail=f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain an uppercase letter")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain a symbol")

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

# Rate-limited endpoints take the Starlette request as `request` (slowapi
# needs it by that name), so their JSON body is called `body`.
@router.post("/register", response_model=LoginResponse)
@limiter.limit(AUTH_LIMIT)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    email = normalize_email(body.email)
    if find_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")

    validate_new_password(body.password)

    hashed_password = hash_password(body.password)
    user = User(email=email, hashed_password=hashed_password, name=body.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "user": user_payload(user)}

@router.post("/login", response_model=LoginResponse)
@limiter.limit(AUTH_LIMIT)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    # One message for unknown email, Google-only account and wrong password,
    # so the endpoint doesn't reveal which emails are registered.
    user = find_user_by_email(db, body.email)
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "user": user_payload(user)}

def verify_google_credential(credential: str) -> dict:
    """Verify a Google ID token for our client. Raises ValueError if invalid."""
    idinfo = id_token.verify_oauth2_token(
        credential,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID
    )
    if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
        raise ValueError('Could not verify audience.')
    return idinfo

@router.post("/google", response_model=LoginResponse)
@limiter.limit(AUTH_LIMIT)
def google_login(request: Request, body: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = verify_google_credential(body.credential)

        email = normalize_email(idinfo['email'])
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')

        user = find_user_by_email(db, email)
        
        if not user:
            user = User(email=email, name=name, picture=picture)
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        
        return {"access_token": access_token, "user": user_payload(user)}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

class DeleteAccountRequest(BaseModel):
    password: str

@router.get("/me")
def get_current_user_profile(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = get_current_user(authorization, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {**user_payload(user), "tier": getattr(user, "tier", "free")}

@router.put("/me")
def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    user = db.get(User, current_user)
    user.name = request.name
    db.commit()
    db.refresh(user)
    return user_payload(user)

@router.put("/me/password")
@limiter.limit(PASSWORD_CHANGE_LIMIT)
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    user = db.get(User, current_user)
    # Failures are 403, not 401: the session itself is valid.
    if user.hashed_password:
        if not body.current_password or not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=403, detail="Current password is incorrect")
    else:
        # A Google-only account has no password to check, and a stolen
        # session token alone must not be enough to add a permanent one:
        # require a fresh Google sign-in for this same account.
        if not body.google_credential:
            raise HTTPException(status_code=403, detail="Sign in with Google again to set a password")
        try:
            idinfo = verify_google_credential(body.google_credential)
        except Exception:
            raise HTTPException(status_code=403, detail="Google sign-in could not be verified")
        if normalize_email(str(idinfo.get("email") or "")) != normalize_email(user.email):
            raise HTTPException(status_code=403, detail="That Google account does not match this account")
    validate_new_password(body.new_password)
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated"}

@router.delete("/me")
def delete_account(
    request: DeleteAccountRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    user_id = get_current_user(authorization, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If the user has a password (not just Google OAuth), verify it.
    # 403, not 401: the session is valid, so the client must not log out.
    if user.hashed_password:
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=403, detail="Invalid password")
    
    # Remove the user's uploaded files and vectors; the DB rows cascade.
    from app.models.models import Document
    import os
    for doc in db.query(Document).filter(Document.owner_id == user_id).all():
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        embedding_service.delete_document(doc.id)

    db.delete(user)
    db.commit()
    return {"message": "Account successfully deleted"}

@router.get("/me/stats")
def get_user_stats(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    tz: ZoneInfo = Depends(get_user_tz),
):
    from app.models.models import ActivityLog, Document, Message

    user_id = get_current_user(authorization, db)

    # Total documents analyzed (processed successfully)
    total_docs = db.query(Document).filter(
        Document.owner_id == user_id, Document.processing_status == "ready"
    ).count()

    # Active chats (documents with messages)
    active_chats = db.query(Document).join(Message).filter(Document.owner_id == user_id).distinct().count()

    # Study days: the user's local calendar days with an upload or message,
    # plus the permanent activity log (already stored as local dates).
    # Timestamps are converted in Python, not with SQL date(), so the day
    # boundary is the user's midnight rather than the database's.
    doc_times = db.query(Document.created_at).filter(Document.owner_id == user_id).all()
    msg_times = db.query(Message.created_at).join(Document).filter(Document.owner_id == user_id).all()
    log_dates = db.query(ActivityLog.date_string).filter(ActivityLog.user_id == user_id).all()

    dates_set: set[datetime.date] = set()
    for (created_at,) in doc_times + msg_times:
        if created_at:
            dates_set.add(to_local_date(created_at, tz))
    for (date_string,) in log_dates:
        try:
            dates_set.add(datetime.date.fromisoformat(date_string))
        except (TypeError, ValueError):
            continue

    sorted_dates = sorted(dates_set)
    current_streak, highest_streak = compute_streaks(sorted_dates, local_date(tz))

    return {
        "total_documents": total_docs,
        "active_chats": active_chats,
        "current_streak": current_streak,
        "highest_streak": highest_streak,
        "activity_dates": [d.isoformat() for d in sorted_dates],
    }


def compute_streaks(sorted_dates: list[datetime.date], today: datetime.date) -> tuple[int, int]:
    """(current, highest) runs of consecutive days. The current run counts
    only if its last day is today or yesterday."""
    if not sorted_dates:
        return 0, 0
    highest = run = 1
    for prev, day in zip(sorted_dates, sorted_dates[1:]):
        run = run + 1 if (day - prev).days == 1 else 1
        highest = max(highest, run)
    current = run if (today - sorted_dates[-1]).days <= 1 else 0
    return current, highest
