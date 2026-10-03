from typing import Literal

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
    FRONTEND_URL: str = "http://localhost:5173"
    GOOGLE_CLIENT_ID: str
    # "fake" swaps the sentence-transformers model for a deterministic hash
    # embedder, so the app and tests run with no model download or network.
    EMBEDDING_BACKEND: Literal["sentence-transformers", "fake"] = "sentence-transformers"

settings = Settings()
