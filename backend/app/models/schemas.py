from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: Optional[int]
    total_chunks: int
    embedding_complete: bool
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
