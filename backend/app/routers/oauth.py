from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import decode_access_token, reusable_oauth2
from app.services.token_service import TokenService
from backend.app.models.calendar_token import CalendarToken
from app.core.config import settings

router = APIRouter(prefix="/oauth", tags=["OAuth"])

@router.get("/connect")
async def connect_google_calendar(
    user_token: str = Depends(reusable_oauth2),  # JWT from frontend
    db: Session = Depends(get_db)
):
    """
    Initiate Google OAuth flow
    """
    # Verify user
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    # Build OAuth URL
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.CALENDAR_CLIENT_ID}&"
        f"redirect_uri={settings.CALENDAR_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/calendar&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={user_id}"  # Pass user_id as state
    )
    
    return {"auth_url": oauth_url}

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,  # user_id
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Calendar provider
    """
    try:
        # Exchange code for tokens
        tokens = await TokenService.exchange_code_for_tokens(code)
        
        # Encrypt refresh token
        encrypted_refresh = TokenService.encrypt_token(tokens["refresh_token"])
        
        # Save to database
        oauth_token = CalendarToken(
            user_id=state,
            provider="calendar",
            access_token=tokens["access_token"],
            refresh_token_enc=encrypted_refresh,
            expires_at=datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
            is_active=True
        )
        
        db.add(oauth_token)
        db.commit()
        
        # Redirect back to frontend
        return RedirectResponse(url="http://localhost:8501?oauth=success")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))