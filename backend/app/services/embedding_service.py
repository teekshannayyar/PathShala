import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os
from app.core.config import settings

class EmbeddingService:
    def __init__(self):
        # We use a small, fast model for embeddings (runs locally on CPU)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Ensure the chroma data directory exists
        os.makedirs(settings.CHROMA_PATH, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name="pathshala_docs",
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, document_id: int, chunks: List[str]):
        """Convert text chunks to embeddings and store them in ChromaDB."""
        if not chunks:
            return

        # Convert text to numerical vectors
        embeddings = self.model.encode(chunks).tolist()
        
        # Prepare data for ChromaDB
        ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"document_id": document_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Upsert so re-processing a document can't fail on duplicate IDs
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(self, query: str, n_results: int = 5, document_id: Optional[int] = None) -> List[Dict]:
        """Search for the most relevant chunks based on a question."""
        where_clause = {"document_id": document_id} if document_id else None
        
        results = self.collection.query(
            query_embeddings=self.model.encode([query]).tolist(),
            n_results=n_results,
            where=where_clause
        )
        
        if not results["documents"] or not results["documents"][0]:
            return []
            
        # Format the output cleanly
        return [
            {"text": doc, "distance": dist, "metadata": meta}
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0]
            )
        ]

    def delete_document(self, document_id: int):
        """Remove all chunks for a specific document."""
        ids_to_delete = self.collection.get(
            where={"document_id": document_id}
        )["ids"]
        
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)

# Create a single instance to be used across the app
embedding_service = EmbeddingService()
