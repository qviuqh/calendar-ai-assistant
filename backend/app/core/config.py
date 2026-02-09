from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Calendar AI Assistant Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str
    
    # Custom Calendar Service
    CALENDAR_SERVICE_URL: str  # Base URL: http://localhost:8000
    CALENDAR_LOGIN_ENDPOINT: str  # Full path: /auth/login
    CALENDAR_TOKEN_REFRESH_ENDPOINT: str  # Full path: /auth/refresh
    
    TOKEN_ENCRYPTION_KEY: str
    
    # AI Agents
    N8N_WEBHOOK_URL: Optional[str] = None
    DIFY_API_URL: Optional[str] = None
    DIFY_API_KEY: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8501"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()