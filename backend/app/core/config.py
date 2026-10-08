from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    CHROMA_PATH: str = "./chroma_data"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 50
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Comma-separated list of allowed browser origins, e.g.
    # "https://pathshala.example.com,http://localhost:5173".
    FRONTEND_URL: str = "http://localhost:5173"
    GOOGLE_CLIENT_ID: str
    # "fake" swaps the sentence-transformers model for a deterministic hash
    # embedder, so the app and tests run with no model download or network.
    EMBEDDING_BACKEND: Literal["sentence-transformers", "fake"] = "sentence-transformers"

    # Vector store. persistent: on-disk at CHROMA_PATH. http: a Chroma server.
    # cloud: Chroma Cloud. ephemeral: in memory, lost on restart (dev/tests).
    CHROMA_MODE: Literal["persistent", "http", "cloud", "ephemeral"] = "persistent"
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: int = 8000
    CHROMA_SSL: bool = False
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = None
    CHROMA_DATABASE: Optional[str] = None
    CHROMA_COLLECTION: str = "pathshala_docs"

    # Per-IP rate limits on login, chat, upload and quiz generation.
    RATE_LIMIT_ENABLED: bool = True
    # Empty means in-process memory (per worker, reset on restart). Use e.g.
    # redis://host:6379 to share counters between workers or instances.
    RATE_LIMIT_STORAGE_URI: Optional[str] = None
    # Request header holding the real client IP, set by the edge proxy (e.g.
    # "cf-connecting-ip" on Render). Empty: use the connection's peer address.
    # Only set it when the proxy always overwrites the header, or clients
    # could choose their own rate-limit key.
    CLIENT_IP_HEADER: Optional[str] = None

    # Folder holding the built frontend (frontend/dist). When set, the API also
    # serves the web app from "/", so one service hosts the whole site
    # (Dockerfile.preview). Empty: the API serves only the API.
    FRONTEND_DIST_DIR: Optional[str] = None
    # Re-embed ready documents whose vectors are missing, in the background at
    # startup. For hosts without a persistent disk, where the on-disk Chroma
    # store is wiped on every restart while Postgres keeps each document's text.
    REINDEX_ON_STARTUP: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def _use_psycopg2(cls, url: str) -> str:
        # Hosts hand out postgres:// or postgresql:// URLs. SQLAlchemy rejects
        # the first and, since 2.1, maps the second to psycopg 3, which isn't
        # installed; pin both to the psycopg2 driver we ship.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    @model_validator(mode="after")
    def _check_chroma(self) -> "Settings":
        if self.CHROMA_MODE == "http" and not (self.CHROMA_HOST or "").strip():
            raise ValueError("CHROMA_MODE=http requires CHROMA_HOST (and optionally CHROMA_PORT, CHROMA_SSL, CHROMA_API_KEY)")
        if self.CHROMA_MODE == "cloud" and not (self.CHROMA_API_KEY or "").strip():
            raise ValueError("CHROMA_MODE=cloud requires CHROMA_API_KEY (and optionally CHROMA_TENANT, CHROMA_DATABASE)")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_URL.split(",") if o.strip()]

settings = Settings()
