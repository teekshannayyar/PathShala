import os
import uuid

from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
PDF_MAGIC = b"%PDF-"
MAGIC_WINDOW = 1024
CHUNK_SIZE = 1024 * 1024  # 1 MiB
DEFAULT_DISPLAY_NAME = "document.pdf"


def max_upload_bytes() -> int:
    return settings.MAX_UPLOAD_MB * 1024 * 1024


def _display_name(raw: str | None) -> str:
    name = os.path.basename(raw or "").strip()
    if len(name) > 255:
        # Keep the extension so long names still pass the .pdf check.
        stem, ext = os.path.splitext(name)
        name = stem[: 255 - len(ext)] + ext
    return name or DEFAULT_DISPLAY_NAME


async def save_pdf_upload(file: UploadFile) -> tuple[str, int, str]:
    """Validate an uploaded PDF and stream it to UPLOAD_DIR under a random name.

    Returns (stored_path, size_bytes, display_name).
    """
    display_name = _display_name(file.filename)

    if not display_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are allowed")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF files are allowed")

    head = await file.read(MAGIC_WINDOW)
    if not head:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if PDF_MAGIC not in head:
        raise HTTPException(status_code=415, detail="Only PDF files are allowed")

    limit = max_upload_bytes()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}.pdf")

    size = 0
    try:
        with open(stored_path, "wb") as out:
            chunk = head
            while chunk:
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB limit",
                    )
                out.write(chunk)
                chunk = await file.read(CHUNK_SIZE)
    except BaseException:
        # The `with` block has already closed the file; remove the partial upload.
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise

    return stored_path, size, display_name
