from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import bcrypt
import jwt
import datetime

from app.models.database import get_db
from app.models.models import User
from app.core.config import settings

router = APIRouter()

class GoogleLoginRequest(BaseModel):
    credential: str

class ManualAuthRequest(BaseModel):
    email: str
    password: str
    name: str = "" # Optional for login, required for register

class LoginResponse(BaseModel):
    access_token: str
    user: dict

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

@router.post("/register", response_model=LoginResponse)
def register(request: ManualAuthRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = hash_password(request.password)
    user = User(email=request.email, hashed_password=hashed_password, name=request.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "user": {"id": user.id, "email": user.email, "name": user.name, "picture": ""}}

@router.post("/login", response_model=LoginResponse)
def login(request: ManualAuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials or please login with Google")
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "user": {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture}}

@router.post("/google", response_model=LoginResponse)
def google_login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            request.credential, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )

        if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
            raise ValueError('Could not verify audience.')

        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')

        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(email=email, name=name, picture=picture)
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        
        return {
            "access_token": access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture
            }
        }
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
    return {"id": user.id, "email": user.email, "name": user.name, "picture": user.picture, "tier": getattr(user, "tier", "free")}

@router.delete("/me")
def delete_account(request: DeleteAccountRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = get_current_user(authorization, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If the user has a password (not just Google OAuth), verify it
    if user.hashed_password:
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid password")
    
    db.delete(user)
    db.commit()
    return {"message": "Account successfully deleted"}

@router.get("/me/stats")
def get_user_stats(authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.models.models import Document, Message
    from sqlalchemy import func
    
    user_id = get_current_user(authorization, db)
    
    # Total documents analyzed
    total_docs = db.query(Document).filter(Document.owner_id == user_id).count()
    
    # Active chats (documents with messages)
    active_chats = db.query(Document).join(Message).filter(Document.owner_id == user_id).distinct().count()
    if active_chats == 0:
        active_chats = total_docs
    
    # Compute study streaks based on unique dates of activity
    doc_dates = db.query(func.date(Document.created_at)).filter(Document.owner_id == user_id).all()
    msg_dates = db.query(func.date(Message.created_at)).join(Document).filter(Document.owner_id == user_id).all()
    
    # Also include permanent activity logs
    from app.models.models import ActivityLog
    log_dates = db.query(ActivityLog.date_string).filter(ActivityLog.user_id == user_id).all()
    
    dates_set = set()
    for d in doc_dates:
        if d[0]: dates_set.add(str(d[0]))
    for d in msg_dates:
        if d[0]: dates_set.add(str(d[0]))
    for d in log_dates:
        if d[0]: dates_set.add(d[0])
            
    sorted_dates = sorted(list(dates_set))
    
    current_streak = 0
    highest_streak = 0
    
    if sorted_dates:
        import datetime
        current_streak = 1
        highest_streak = 1
        temp_streak = 1
        
        for i in range(1, len(sorted_dates)):
            date1 = datetime.datetime.strptime(sorted_dates[i-1], "%Y-%m-%d").date()
            date2 = datetime.datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()
            
            if (date2 - date1).days == 1:
                temp_streak += 1
                highest_streak = max(highest_streak, temp_streak)
            else:
                temp_streak = 1
                
        # Check if current streak is still active (active today or yesterday)
        today = datetime.datetime.utcnow().date()
        last_active = datetime.datetime.strptime(sorted_dates[-1], "%Y-%m-%d").date()
        
        if (today - last_active).days <= 1:
            current_streak = temp_streak
        else:
            current_streak = 0

    return {
        "total_documents": total_docs,
        "active_chats": active_chats,
        "current_streak": current_streak,
        "highest_streak": highest_streak,
        "activity_dates": sorted_dates
    }
