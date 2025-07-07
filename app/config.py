# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "E-Learning Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./elearning.db"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Email
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: Optional[str] = None
    EMAIL_HOST_PASSWORD: Optional[str] = None
    DEFAULT_FROM_EMAIL: Optional[str] = None
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    UPLOAD_DIR: str = "app/static/uploads"
    
    # Company info
    COMPANY_NAME: str = "E-Learning Platform"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Create upload directories
os.makedirs(f"{settings.UPLOAD_DIR}/avatars", exist_ok=True)
os.makedirs(f"{settings.UPLOAD_DIR}/courses", exist_ok=True)
os.makedirs(f"{settings.UPLOAD_DIR}/certificates", exist_ok=True)