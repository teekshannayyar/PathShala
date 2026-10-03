import functools
import os
from typing import Any, Dict, List, Optional, Protocol

from app.core.config import settings

SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "pathshala_docs"


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Wraps a small local model (runs on CPU). The model is downloaded and
    loaded on the first encode() call, never at import or construction."""

    def __init__(self, model_name: str = SENTENCE_TRANSFORMER_MODEL):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self._load_model().encode(list(texts)).tolist()


@functools.lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.EMBEDDING_BACKEND == "fake":
        from app.services.fake_embedder import FakeEmbedder

        return FakeEmbedder()
    return SentenceTransformerEmbedder()


class EmbeddingService:
    def __init__(self, embedder: Embedder, client: Any, collection_name: str = COLLECTION_NAME):
        self.embedder = embedder
        self.client = client
        # embedding_function=None: we always pass our own vectors, so Chroma
        # must never fall back to (and download) its default ONNX model.
        self.collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    def add_chunks(self, document_id: int, chunks: List[str]):
        """Convert text chunks to embeddings and store them in ChromaDB."""
        if not chunks:
            return

        # Convert text to numerical vectors
        embeddings = self.embedder.encode(chunks)

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
            query_embeddings=self.embedder.encode([query]),
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


@functools.lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """The app-wide service, created on first use rather than at import."""
    import chromadb

    os.makedirs(settings.CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return EmbeddingService(get_embedder(), client)
