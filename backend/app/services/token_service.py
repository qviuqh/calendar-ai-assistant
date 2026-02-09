from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import logging

from app.models.calendar_token import CalendarToken
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Fernet cipher suite
cipher_suite = Fernet(settings.TOKEN_ENCRYPTION_KEY)

class TokenService:
    
    @staticmethod
    def encrypt_token(token: str) -> str:
        """Encrypt refresh token before storing in DB"""
        return cipher_suite.encrypt(token.encode()).decode()
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Decrypt refresh token from DB"""
        return cipher_suite.decrypt(encrypted_token.encode()).decode()
    
    @staticmethod
    async def login_to_calendar_service(email: str, password: str) -> Dict[str, Any]:
        """
        Login to Calendar Service (third-party API) to get tokens
        
        Args:
            email: User's email on calendar service
            password: User's password on calendar service
            
        Returns:
            Dict with tokens: {
                "access_token": "...",
                "refresh_token": "...",
                "expires_in": 1800,
                "token_type": "bearer"
            }
        """
        login_url = f"{settings.CALENDAR_SERVICE_URL}{settings.CALENDAR_LOGIN_ENDPOINT}"
        
        logger.info(f"Logging into Calendar Service at {login_url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    login_url,
                    json={
                        "email": email,
                        "password": password
                    },
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Calendar login failed: {error_detail}")
                    raise Exception(f"Calendar login failed: {error_detail}")
                
                data = response.json()
                
                # Validate response format
                required_fields = ["access_token", "expires_in", "refresh_token", "token_type"]
                for field in required_fields:
                    if field not in data:
                        raise Exception(f"Missing field in Calendar API response: {field}")
                
                logger.info("Successfully logged into Calendar Service")
                return data
                
            except httpx.RequestError as e:
                logger.error(f"Network error connecting to Calendar Service: {str(e)}")
                raise Exception(f"Cannot connect to Calendar Service: {str(e)}")
    
    @staticmethod
    async def save_user_token(
        db: Session,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        calendar_user_email: Optional[str] = None,
        notes: Optional[str] = None
    ) -> CalendarToken:
        """
        Save or update user's calendar token
        
        Args:
            db: Database session
            user_id: User ID (webapp user)
            access_token: Access token from calendar service
            refresh_token: Refresh token from calendar service
            expires_in: Token expiration time in seconds
            calendar_user_email: User's email on calendar service
            notes: Optional notes
            
        Returns:
            CalendarToken object
        """
        # Check if user already has a token
        existing_token = db.query(CalendarToken).filter(
            CalendarToken.user_id == user_id
        ).first()
        
        # Encrypt refresh token
        encrypted_refresh = TokenService.encrypt_token(refresh_token)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.refresh_token_enc = encrypted_refresh
            existing_token.expires_at = expires_at
            existing_token.is_active = True
            existing_token.calendar_user_email = calendar_user_email
            existing_token.notes = notes
            existing_token.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_token)
            logger.info(f"Updated calendar token for user {user_id}")
            return existing_token
        else:
            # Create new token
            new_token = CalendarToken(
                user_id=user_id,
                access_token=access_token,
                refresh_token_enc=encrypted_refresh,
                expires_at=expires_at,
                calendar_user_email=calendar_user_email,
                notes=notes
            )
            
            db.add(new_token)
            db.commit()
            db.refresh(new_token)
            logger.info(f"Created new calendar token for user {user_id}")
            return new_token
    
    @staticmethod
    async def refresh_access_token(refresh_token: str) -> dict:
        """
        Use refresh token to get new access token from calendar service
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new access_token and expires_in
        """
        refresh_url = f"{settings.CALENDAR_SERVICE_URL}{settings.CALENDAR_TOKEN_REFRESH_ENDPOINT}"
        
        logger.info(f"Refreshing token at {refresh_url}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    refresh_url,
                    json={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token
                    },
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Token refresh failed: {error_detail}")
                    raise Exception(f"Failed to refresh token: {error_detail}")
                
                data = response.json()
                
                logger.info("Successfully refreshed access token")
                return {
                    "access_token": data.get("access_token"),
                    "expires_in": data.get("expires_in", 3600)  # Default 1 hour
                }
                
            except httpx.RequestError as e:
                logger.error(f"Network error during token refresh: {str(e)}")
                raise Exception(f"Cannot connect to Calendar Service: {str(e)}")
    
    @staticmethod
    async def get_valid_access_token(db: Session, user_id: str) -> Optional[str]:
        """
        CORE LOGIC: Get valid access token, auto-refresh if expired
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Valid access token or None if refresh failed
        """
        # Get user's calendar token
        calendar_token = db.query(CalendarToken).filter(
            CalendarToken.user_id == user_id,
            CalendarToken.is_active == True
        ).first()
        
        if not calendar_token:
            logger.warning(f"No calendar token found for user {user_id}")
            return None
        
        # Check if token is expired or about to expire (1 min buffer)
        now = datetime.utcnow()
        expires_soon = calendar_token.expires_at - timedelta(minutes=1)
        
        if now < expires_soon:
            # Token still valid
            logger.info(f"Using existing valid token for user {user_id}")
            return calendar_token.access_token
        
        # Token expired, need to refresh
        logger.info(f"Token expired for user {user_id}, refreshing...")
        try:
            refresh_token = TokenService.decrypt_token(calendar_token.refresh_token_enc)
            new_tokens = await TokenService.refresh_access_token(refresh_token)
            
            # Update database with new tokens
            calendar_token.access_token = new_tokens["access_token"]
            calendar_token.expires_at = datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
            calendar_token.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(calendar_token)
            
            logger.info(f"Successfully refreshed token for user {user_id}")
            return new_tokens["access_token"]
            
        except Exception as e:
            # Refresh failed, mark as inactive
            logger.error(f"Token refresh failed for user {user_id}: {str(e)}")
            calendar_token.is_active = False
            db.commit()
            raise Exception(f"Token refresh failed: {str(e)}")
    
    @staticmethod
    def get_token_status(db: Session, user_id: str) -> dict:
        """
        Check if user has valid token
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict with token status
        """
        token = db.query(CalendarToken).filter(
            CalendarToken.user_id == user_id
        ).first()
        
        if not token:
            return {
                "has_token": False,
                "is_valid": False
            }
        
        now = datetime.utcnow()
        is_valid = token.is_active and token.expires_at > now
        
        return {
            "has_token": True,
            "is_valid": is_valid,
            "expires_at": token.expires_at,
            "calendar_user_email": token.calendar_user_email
        }
    
    @staticmethod
    def delete_user_token(db: Session, user_id: str) -> bool:
        """
        Delete user's calendar token
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        token = db.query(CalendarToken).filter(
            CalendarToken.user_id == user_id
        ).first()
        
        if token:
            db.delete(token)
            db.commit()
            logger.info(f"Deleted calendar token for user {user_id}")
            return True
        
        logger.warning(f"No token found to delete for user {user_id}")
        return False