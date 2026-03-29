from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Required for production, but optional for development
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    MONGODB_URI: Optional[str] = None
    
    # Optional with defaults
    HF_MODEL_ID: str = "ShaibinkB/cord-layoutlmv3-onnx"
    CONFIDENCE_THRESHOLD: float = 0.75
    CORS_ORIGIN: str = "http://localhost:3000"
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
