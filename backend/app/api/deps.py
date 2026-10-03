from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Document


def get_owned_document(db: Session, document_id: int, user_id: int) -> Document:
    """Return the document if it exists and belongs to user_id.

    Raises 404 (not 403) for both "missing" and "not yours", so callers can't
    probe which document IDs exist.
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
