from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class OAuthConnectResponse(BaseModel):
    auth_url: str

class OAuthStatus(BaseModel):
    is_connected: bool
    provider: str
    connected_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True