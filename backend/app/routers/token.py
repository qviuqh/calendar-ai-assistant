from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import decode_access_token, reusable_oauth2
from app.services.token_service import TokenService
from app.schemas.token import TokenInput, TokenResponse, TokenStatus

router = APIRouter(tags=["Calendar Token"])


class CalendarLoginRequest(BaseModel):
    """Request to login to Calendar Service"""
    email: EmailStr
    password: str


@router.post("/calendar-login", response_model=TokenResponse)
async def login_to_calendar(
    login_data: CalendarLoginRequest,
    user_token: str = Depends(reusable_oauth2),  # JWT from webapp
    db: Session = Depends(get_db)
):
    """
    Login to Calendar Service (third-party) and save tokens
    
    Flow:
    1. User already logged into webapp (has JWT)
    2. User provides Calendar Service credentials
    3. Webapp calls Calendar Service /auth/login
    4. Save returned tokens to webapp DB
    
    Args:
        login_data: Calendar Service credentials
        user_token: Webapp JWT token
        db: Database session
        
    Returns:
        Saved token info
    """
    # Verify webapp user
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    try:
        # Login to Calendar Service
        calendar_tokens = await TokenService.login_to_calendar_service(
            email=login_data.email,
            password=login_data.password
        )
        
        # Save tokens to DB
        saved_token = await TokenService.save_user_token(
            db=db,
            user_id=user_id,
            access_token=calendar_tokens["access_token"],
            refresh_token=calendar_tokens["refresh_token"],
            expires_in=calendar_tokens["expires_in"],
            calendar_user_email=login_data.email,
            notes="Logged in via Calendar Service"
        )
        
        return saved_token
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calendar login failed: {str(e)}"
        )


@router.post("/save", response_model=TokenResponse)
async def save_calendar_token(
    token_data: TokenInput,
    user_token: str = Depends(reusable_oauth2),  # JWT from frontend
    db: Session = Depends(get_db)
):
    """
    Save user's calendar service tokens (manually inputted)
    
    Alternative method: User manually copies tokens from Calendar Service
    and pastes them here.
    
    User provides:
    - access_token
    - refresh_token
    - expires_in (seconds)
    - optional: calendar_user_email, notes
    """
    # Verify user
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    try:
        saved_token = await TokenService.save_user_token(
            db=db,
            user_id=user_id,
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_in=token_data.expires_in,
            calendar_user_email=token_data.calendar_user_email,
            notes=token_data.notes
        )
        
        return saved_token
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save token: {str(e)}"
        )


@router.get("/status", response_model=TokenStatus)
async def check_token_status(
    user_token: str = Depends(reusable_oauth2),
    db: Session = Depends(get_db)
):
    """
    Check if user has valid calendar token
    """
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    status_data = TokenService.get_token_status(db, user_id)
    return status_data


@router.delete("/delete")
async def delete_calendar_token(
    user_token: str = Depends(reusable_oauth2),
    db: Session = Depends(get_db)
):
    """
    Delete user's calendar token
    """
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    deleted = TokenService.delete_user_token(db, user_id)
    
    if deleted:
        return {"message": "Token deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No token found"
        )


@router.post("/refresh")
async def manually_refresh_token(
    user_token: str = Depends(reusable_oauth2),
    db: Session = Depends(get_db)
):
    """
    Manually trigger token refresh
    """
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    try:
        new_access_token = await TokenService.get_valid_access_token(db, user_id)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No token found or refresh failed"
            )
        
        return {
            "message": "Token refreshed successfully",
            "access_token": new_access_token[:20] + "..."  # Show partial for security
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )