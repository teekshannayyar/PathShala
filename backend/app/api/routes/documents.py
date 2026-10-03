from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Document
from app.services.pdf_service import PDFService
from app.api.routes.auth import get_current_user
from app.core.config import settings
import os

router = APIRouter()

@router.get("/")
def get_documents(db: Session = Depends(get_db), current_user: int = Depends(get_current_user)):
    return db.query(Document).filter(Document.owner_id == current_user).all()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    # Save the file temporarily
    file_location = os.path.join(settings.UPLOAD_DIR, file.filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # Create the document in database
    db_doc = Document(
        filename=file.filename,
        file_path=file_location,
        file_size=os.path.getsize(file_location),
        owner_id=current_user
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

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
    if os.path.exists(doc.file_path):
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
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        embedding_service.delete_document(doc.id)
        db.delete(doc)
        deleted_ids.append(doc.id)
        
    db.commit()
    return {"message": f"Successfully deleted {len(deleted_ids)} documents", "deleted_ids": deleted_ids}
