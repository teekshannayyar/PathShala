import pdfplumber
from typing import List, Tuple

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
    def process_document(document_id: int, db):
        from app.models.models import Document
        from app.services.embedding_service import embedding_service
        
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
            
        try:
            text, _ = PDFService.extract_text(doc.file_path)
            chunks = PDFService.chunk_text(text)
            embedding_service.add_chunks(document_id, chunks)
            
            doc.embedding_complete = True
            db.commit()
        except Exception as e:
            print(f"Error processing document: {e}")
