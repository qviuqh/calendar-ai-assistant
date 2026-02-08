from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TokenInput(BaseModel):
    """
    Schema for user to input their calendar tokens manually
    """
    access_token: str
    refresh_token: str
    expires_in: int  # Seconds until expiration
    calendar_user_email: Optional[str] = None
    notes: Optional[str] = None

class TokenResponse(BaseModel):
    """
    Response after saving token
    """
    id: str
    is_active: bool
    expires_at: datetime
    calendar_user_email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenStatus(BaseModel):
    """
    Token status check
    """
    has_token: bool
    is_valid: bool
    expires_at: Optional[datetime] = None
    calendar_user_email: Optional[str] = None