import logging
from typing import List, Tuple

import pdfplumber

from app.models.database import SessionLocal
from app.services import embedding_service as embedding_service_module

logger = logging.getLogger(__name__)

NO_TEXT_ERROR = "No extractable text found (scanned/image PDF?)"
# Shown to the user for unexpected failures; the real exception is only logged.
PROCESSING_FAILED_ERROR = "Couldn't read this PDF. Try reprocessing or uploading it again."


class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, dict]:
        full_text = ""
        metadata = {"pages": 0}
        
        with pdfplumber.open(file_path) as pdf:
            metadata["pages"] = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    
        return full_text, metadata

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Sliding window chunks with overlap to preserve context at boundaries."""
        words = text.split()
        chunks = []
        step = chunk_size - overlap
        
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size])
            if chunk:
                chunks.append(chunk)
                
        return chunks

    @staticmethod
    def process_document(document_id: int) -> None:
        """Extract, chunk and embed a document, recording the outcome on its row.

        Runs as a background task, so it owns its own DB session. The document
        always ends up "ready" or "failed", never stuck in "processing".
        """
        from app.models.models import Document

        db = SessionLocal()
        chunks_added = False
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return

            try:
                text, _ = PDFService.extract_text(doc.file_path)
                # Postgres TEXT can't store NUL bytes, which some PDFs produce.
                text = text.replace("\x00", "")

                if not text.strip():
                    doc.processing_status = "failed"
                    doc.processing_error = NO_TEXT_ERROR
                    doc.embedding_complete = False
                    db.commit()
                    logger.warning("Document %s has no extractable text", document_id)
                    return

                chunks = PDFService.chunk_text(text)
                # Looked up at call time so tests can swap in a fake service.
                embedding_service = embedding_service_module.get_embedding_service()
                embedding_service.delete_document(document_id)
                embedding_service.add_chunks(document_id, chunks)
                chunks_added = True

                doc.original_text = text
                doc.total_chunks = len(chunks)
                doc.embedding_complete = True
                doc.processing_status = "ready"
                doc.processing_error = None
                db.commit()
                logger.info("Processed document %s into %d chunks", document_id, len(chunks))
            except Exception:
                db.rollback()
                # The user may have deleted the document while we were working
                # (the file vanishes and the final UPDATE matches no row).
                if db.query(Document.id).filter(Document.id == document_id).first() is None:
                    logger.info("Document %s was deleted during processing", document_id)
                    if chunks_added:
                        # The delete route may have cleared vectors before we added ours.
                        embedding_service.delete_document(document_id)
                    return

                logger.exception("Failed to process document %s", document_id)
                doc.processing_status = "failed"
                doc.processing_error = PROCESSING_FAILED_ERROR
                doc.embedding_complete = False
                db.commit()
        except Exception:
            # Never let a background task raise. If the row is left in
            # "processing", reprocess accepts it once it goes stale.
            db.rollback()
            logger.exception("Could not record processing result for document %s", document_id)
        finally:
            db.close()
