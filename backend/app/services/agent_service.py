import httpx
from typing import AsyncGenerator
from app.core.config import settings

class AgentService:
    @staticmethod
    async def chat_with_n8n(
        message: str,
        user_id: str,
        access_token: str
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from n8n with fresh access token
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                settings.N8N_WEBHOOK_URL,
                json={
                    "message": message,
                    "user_id": user_id,
                    "access_token": access_token  # Fresh token!
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield line
    
    @staticmethod
    async def chat_with_dify(
        message: str,
        user_id: str,
        access_token: str,
        conversation_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Dify
        """
        payload = {
            "query": message,
            "user": user_id,
            "response_mode": "streaming",
            "inputs": {
                "google_calendar_token": access_token
            }
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                settings.DIFY_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.DIFY_API_KEY}"}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield line