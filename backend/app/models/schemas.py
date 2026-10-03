from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Public view of a document. Never includes original_text or file_path."""

    id: int
    filename: str
    folder: Optional[str] = None
    file_size: Optional[int] = None
    total_chunks: Optional[int] = 0
    embedding_complete: Optional[bool] = False
    processing_status: str
    processing_error: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
