import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Metro Safety AI"
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///metro_safety.db")
    model_name: str = "yolo26n-metro-v1"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]


settings = Settings()
