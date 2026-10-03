from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Document
from app.services.pdf_service import PDFService
from app.services.upload_service import max_upload_bytes, save_pdf_upload
from app.api.routes.auth import get_current_user
from app.core.config import settings
import os

# Allowance for multipart boundaries/headers on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024

router = APIRouter()

@router.get("/")
def get_documents(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    return db.query(Document).filter(Document.owner_id == current_user).all()

@router.post("/upload")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
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
            owner_id=current_user
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
    from app.models.models import ActivityLog
    import datetime
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    existing_log = db.query(ActivityLog).filter(
        ActivityLog.user_id == current_user,
        ActivityLog.date_string == today_str
    ).first()
    
    if not existing_log:
        db.add(ActivityLog(user_id=current_user, date_string=today_str))
        db.commit()

    # Process it in the background
    background_tasks.add_task(PDFService.process_document, db_doc.id, db)
    
    return db_doc

@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    from app.services.embedding_service import embedding_service
    
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

from pydantic import BaseModel
from typing import List

class RenameRequest(BaseModel):
    filename: str

class MoveFolderRequest(BaseModel):
    folder: str

class BulkDeleteRequest(BaseModel):
    document_ids: List[int]

@router.put("/{document_id}/rename")
def rename_document(document_id: int, request: RenameRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.filename = request.filename
    db.commit()
    db.refresh(doc)
    return doc

@router.put("/{document_id}/folder")
def move_document_to_folder(document_id: int, request: MoveFolderRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.folder = request.folder
    db.commit()
    db.refresh(doc)
    return doc

@router.post("/bulk-delete")
def bulk_delete_documents(request: BulkDeleteRequest, db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    from app.services.embedding_service import embedding_service
    
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
