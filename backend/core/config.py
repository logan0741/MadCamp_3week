"""
Application Configuration
Environment variables and settings management
"""
import os
from typing import List


class Settings:
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./musinsa_tracker.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "musinsa-tracker-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # Upload directories
    UPLOAD_DIR: str = "uploads"
    VIDEO_UPLOAD_DIR: str = "uploads/videos"
    AVATAR_UPLOAD_DIR: str = "uploads/avatars"
    GARMENT_UPLOAD_DIR: str = "uploads/garments"

    # AI Pipeline Integration
    AI_PIPELINE_BASE_URL: str = os.getenv("AI_PIPELINE_BASE_URL", "http://localhost:8001")
    AI_PIPELINE_TIMEOUT_SECONDS: float = float(os.getenv("AI_PIPELINE_TIMEOUT_SECONDS", "10"))
    
    # API
    API_V1_PREFIX: str = "/api/v1"


settings = Settings()
