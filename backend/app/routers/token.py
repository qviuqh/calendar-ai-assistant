from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import decode_access_token, reusable_oauth2
from app.services.token_service import TokenService
from app.schemas.token import TokenInput, TokenResponse, TokenStatus

router = APIRouter(prefix="/token", tags=["Calendar Token"])

@router.post("/save", response_model=TokenResponse)
async def save_calendar_token(
    token_data: TokenInput,
    user_token: str = Depends(reusable_oauth2),  # JWT from frontend
    db: Session = Depends(get_db)
):
    """
    Save user's calendar service tokens (manually inputted)
    
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
    user_token: str,
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