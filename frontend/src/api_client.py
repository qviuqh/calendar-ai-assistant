import requests
from typing import Generator, Optional, Dict, Any
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class BackendAPIClient:
    """
    Client for communicating with Calendar AI Assistant Backend
    """
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or st.secrets.get("BACKEND_URL", "http://localhost:8000")
        self.api_v1 = f"{self.base_url}/api/v1"
        self.session = requests.Session()
    
    @property
    def auth_token(self) -> Optional[str]:
        """Get auth token from session state"""
        return st.session_state.get("auth_token")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    # ========== Authentication ==========
    
    def register(self, email: str, password: str) -> Dict[str, Any]:
        """Register new user"""
        try:
            response = self.session.post(
                f"{self.api_v1}/auth/register",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Registration failed: {str(e)}")
            raise
    
    def login(self, email: str, password: str) -> str:
        """Login and get access token"""
        try:
            response = self.session.post(
                f"{self.api_v1}/auth/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            return data["access_token"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Login failed: {str(e)}")
            raise
    
    # ========== Calendar Service Token Management ==========
    
    def login_to_calendar_service(
        self,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Login to Calendar Service (third-party) via backend
        
        Backend will:
        1. Call Calendar Service /auth/login
        2. Get access_token, refresh_token, expires_in
        3. Save to database
        4. Return token info
        
        Args:
            email: Calendar Service email
            password: Calendar Service password
            
        Returns:
            Token response from backend
        """
        try:
            response = self.session.post(
                f"{self.api_v1}/token/calendar-login",
                json={
                    "email": email,
                    "password": password
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Calendar login failed: {str(e)}")
            # Try to get error detail from response
            try:
                error_detail = e.response.json().get("detail", str(e))
            except:
                error_detail = str(e)
            raise Exception(error_detail)
    
    def save_calendar_token(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        calendar_user_email: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save calendar service tokens manually
        
        Alternative to login_to_calendar_service when user
        manually obtains tokens from Calendar Service.
        
        Args:
            access_token: Access token from calendar service
            refresh_token: Refresh token from calendar service
            expires_in: Token expiration in seconds
            calendar_user_email: Optional email on calendar service
            notes: Optional notes
            
        Returns:
            Token response
        """
        try:
            payload = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in
            }
            
            if calendar_user_email:
                payload["calendar_user_email"] = calendar_user_email
            
            if notes:
                payload["notes"] = notes
            
            response = self.session.post(
                f"{self.api_v1}/token/save",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Save token failed: {str(e)}")
            raise
    
    def check_token_status(self) -> Dict[str, Any]:
        """
        Check if user has valid calendar token
        
        Returns:
            Token status
        """
        try:
            response = self.session.get(
                f"{self.api_v1}/token/status",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Check token status failed: {str(e)}")
            raise
    
    def refresh_token(self) -> Dict[str, Any]:
        """
        Manually refresh calendar token
        
        Returns:
            Refresh result
        """
        try:
            response = self.session.post(
                f"{self.api_v1}/token/refresh",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Refresh token failed: {str(e)}")
            raise
    
    def delete_token(self) -> Dict[str, Any]:
        """
        Delete calendar token
        
        Returns:
            Delete result
        """
        try:
            response = self.session.delete(
                f"{self.api_v1}/token/delete",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Delete token failed: {str(e)}")
            raise
    
    # ========== Chat ==========
    
    def chat_stream(
        self,
        message: str,
        agent_type: str = "n8n",
        conversation_id: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Send chat message and stream response"""
        try:
            payload = {
                "message": message,
                "agent_type": agent_type
            }
            
            if conversation_id:
                payload["conversation_id"] = conversation_id
            
            response = self.session.post(
                f"{self.api_v1}/chat/",
                json=payload,
                headers=self._get_headers(),
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    yield line
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Chat stream failed: {str(e)}")
            yield f"❌ Error: {str(e)}"
    
    def health_check(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False