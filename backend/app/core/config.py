from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    CHROMA_PATH: str = "./chroma_data"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 50
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_URL: str = "http://localhost:5173"
    GOOGLE_CLIENT_ID: str

    class Config:
        env_file = ".env"

settings = Settings()
