from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_owned_document
from app.models.database import get_db
from app.models.models import Document
from app.models.schemas import DocumentResponse
from app.services.pdf_service import PDFService
from app.services.upload_service import max_upload_bytes, save_pdf_upload
from app.api.routes.auth import get_current_user
from app.core.config import settings
from typing import List
import os

# Allowance for multipart boundaries/headers on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024

router = APIRouter()

@router.get("/", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    return db.query(Document).filter(Document.owner_id == current_user).all()

@router.post("/upload", response_model=DocumentResponse)
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
    background_tasks.add_task(PDFService.process_document, db_doc.id)

    db.refresh(db_doc)
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

    if doc.processing_status == "processing":
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

from pydantic import BaseModel

class RenameRequest(BaseModel):
    filename: str

class MoveFolderRequest(BaseModel):
    folder: str

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
