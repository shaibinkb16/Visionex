from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    GEMINI_API_KEY: str
    MONGODB_URI: str
    HF_MODEL_ID: str = "your-username/cord-ner-distilbert-onnx"
    CONFIDENCE_THRESHOLD: float = 0.75
    CORS_ORIGIN: str = "http://localhost:3000"
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
