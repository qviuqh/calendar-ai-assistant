from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.token_service import TokenService  # Changed
from app.services.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    agent_type: str = "n8n"  # or "dify"
    conversation_id: str = None

@router.post("/")
async def chat(
    request: ChatRequest,
    user_token: str,  # JWT from header
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint with auto token refresh
    """
    # Verify user
    payload = decode_access_token(user_token)
    user_id = payload.get("sub")
    
    # Get valid access token (auto-refresh if needed)
    try:
        access_token = await TokenService.get_valid_access_token(db, user_id)
        
        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="Calendar token not found. Please add your tokens first."
            )
        
        # Route to appropriate agent
        if request.agent_type == "n8n":
            stream = AgentService.chat_with_n8n(
                message=request.message,
                user_id=user_id,
                access_token=access_token
            )
        else:
            stream = AgentService.chat_with_dify(
                message=request.message,
                user_id=user_id,
                access_token=access_token,
                conversation_id=request.conversation_id
            )
        
        return StreamingResponse(stream, media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))