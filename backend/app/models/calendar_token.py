from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.core.database import Base

class CalendarToken(Base):
    """
    Store user's calendar service tokens
    User manually inputs these tokens through the UI
    """
    __tablename__ = "calendar_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Token information
    access_token = Column(Text, nullable=False)
    refresh_token_enc = Column(Text, nullable=False)  # Encrypted
    expires_at = Column(DateTime, nullable=False)
    
    # Metadata
    token_type = Column(String, default="Bearer")  # Bearer, Basic, etc.
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional info (optional)
    calendar_user_email = Column(String, nullable=True)  # Email on calendar service
    notes = Column(Text, nullable=True)  # User's notes about this token
    
    # Relationships
    user = relationship("User", back_populates="calendar_token")