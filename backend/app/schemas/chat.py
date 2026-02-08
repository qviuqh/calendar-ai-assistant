from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    agent_type: str = "n8n"  # "n8n" or "dify"
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None