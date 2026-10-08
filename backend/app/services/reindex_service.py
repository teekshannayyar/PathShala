import logging

from app.models.database import SessionLocal
from app.services import embedding_service as embedding_service_module
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


def reindex_missing_documents() -> int:
    """Re-embed every ready document that has no vectors in the store, from the
    text saved in Postgres. Returns how many documents were re-embedded.

    Used at startup on hosts whose disk is wiped on restart (REINDEX_ON_STARTUP):
    the documents survive in Postgres but their Chroma vectors do not.
    """
    from app.models.models import Document

    db = SessionLocal()
    reindexed = 0
    try:
        service = embedding_service_module.get_embedding_service()
        docs = (
            db.query(Document.id, Document.original_text)
            .filter(Document.processing_status == "ready", Document.original_text.isnot(None))
            .all()
        )
        for doc_id, text in docs:
            if service.collection.get(where={"document_id": doc_id}, limit=1)["ids"]:
                continue
            chunks = PDFService.chunk_text(text)
            if chunks:
                service.add_chunks(doc_id, chunks)
                reindexed += 1
        logger.info("Re-embedded %d of %d ready documents", reindexed, len(docs))
    except Exception:
        logger.exception("Startup re-embedding failed")
    finally:
        db.close()
    return reindexed
