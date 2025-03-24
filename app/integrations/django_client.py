"""
Client for integrating with the EINO Django backend.
"""

import httpx
from typing import Dict, Any, Optional, List
import json

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class DjangoClient:
    """
    Client for making requests to the EINO Django backend API.
    This client handles authentication, user and company data, and other backend interactions.
    """

    def __init__(self):
        """Initialize the Django client with base URL from settings."""
        self.base_url = settings.DJANGO_API_URL
        self.timeout = httpx.Timeout(30.0)  # 30 seconds timeout

    async def _make_request(
        self, method: str, endpoint: str, data: Any = None, headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Django API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            headers: Request headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set default headers
        if headers is None:
            headers = {}
        
        # Add JSON content type for POST, PUT, PATCH
        if method.upper() in ["POST", "PUT", "PATCH"] and "content-type" not in headers:
            headers["content-type"] = "application/json"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if method.upper() in ["POST", "PUT", "PATCH"] else None,
                    params=data if method.upper() == "GET" else None,
                )
                
                # Raise for HTTP error status
                response.raise_for_status()
                
                # Return JSON response
                return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error when calling Django API: {str(e)}")
            # Try to get error details from response
            try:
                error_detail = e.response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise Exception(f"Django API error: {error_detail}")
        
        except Exception as e:
            logger.error(f"Error making request to Django API: {str(e)}")
            raise Exception(f"Django API request failed: {str(e)}")

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with the Django backend.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            User data if authentication succeeds, None otherwise
        """
        try:
            data = {
                "email": username,
                "password": password
            }
            
            # Call the login endpoint
            response = await self._make_request("POST", "/user/login/", data=data)
            
            # Check if response contains user data
            if response.get("code") == 200 and "data" in response:
                return response["data"]
            
            return None
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    async def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """
        Get user details from the Django backend.
        
        Args:
            user_id: User ID
            
        Returns:
            User data
            
        Raises:
            Exception: If the request fails
        """
        # Call the user details endpoint
        response = await self._make_request("GET", f"/user/{user_id}/")
        
        # Check if response contains user data
        if "data" in response:
            return response["data"]
        
        raise Exception("Failed to get user details")

    async def get_company_user(self, user_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the company user relationship for a user and company.
        
        Args:
            user_id: User ID
            company_id: Company ID
            
        Returns:
            Company user data if exists, None otherwise
            
        Raises:
            Exception: If the request fails
        """
        try:
            # Call the company user endpoint
            response = await self._make_request("GET", f"/company/{company_id}/user/{user_id}/")
            
            # Check if response contains company user data
            if "data" in response:
                return response["data"]
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting company user: {str(e)}")
            return None

    async def check_department_access(self, user_id: str, department_id: str) -> bool:
        """
        Check if a user has access to a department.
        
        Args:
            user_id: User ID
            department_id: Department ID
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            # Call the department access check endpoint
            response = await self._make_request(
                "GET", f"/department/{department_id}/check-access/{user_id}/"
            )
            
            # Check if response indicates access
            return response.get("has_access", False)
        
        except Exception as e:
            logger.error(f"Error checking department access: {str(e)}")
            return False

    async def check_upload_permission(self, company_user_id: str) -> bool:
        """
        Check if a user has permission to upload videos.
        
        Args:
            company_user_id: Company user ID
            
        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Call the permission check endpoint
            response = await self._make_request(
                "GET", f"/resource/check-upload-permission/{company_user_id}/"
            )
            
            # Check if response indicates permission
            return response.get("has_permission", False)
        
        except Exception as e:
            logger.error(f"Error checking upload permission: {str(e)}")
            return False

    async def check_storage_limit(self, company_user_id: str, file_size: int) -> bool:
        """
        Check if a user has enough storage for an upload.
        
        Args:
            company_user_id: Company user ID
            file_size: File size in bytes
            
        Returns:
            True if enough storage, False otherwise
        """
        try:
            # Call the storage check endpoint
            response = await self._make_request(
                "GET", 
                f"/resource/check-storage/{company_user_id}/",
                data={"file_size": file_size}
            )
            
            # Check if response indicates enough storage
            return response.get("has_storage", False)
        
        except Exception as e:
            logger.error(f"Error checking storage limit: {str(e)}")
            return False

    async def check_video_access(self, company_user_id: str, video_id: str) -> bool:
        """
        Check if a user has access to a video.
        
        Args:
            company_user_id: Company user ID
            video_id: Video ID
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            # Call the video access check endpoint
            response = await self._make_request(
                "GET", f"/resource/check-video-access/{company_user_id}/{video_id}/"
            )
            
            # Check if response indicates access
            return response.get("has_access", False)
        
        except Exception as e:
            logger.error(f"Error checking video access: {str(e)}")
            return False

    async def update_video_metadata(self, video_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update video metadata in the Django backend.
        
        Args:
            video_id: Video ID
            metadata: Video metadata
            
        Returns:
            True if update succeeds, False otherwise
        """
        try:
            # Call the video update endpoint
            response = await self._make_request(
                "PATCH", f"/resource/video/{video_id}/", data=metadata
            )
            
            # Check if response indicates success
            return response.get("success", False)
        
        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            return False

    async def notify_video_ready(self, video_id: str, user_id: str) -> bool:
        """
        Send notification that a video is ready for streaming.
        
        Args:
            video_id: Video ID
            user_id: User ID
            
        Returns:
            True if notification sent, False otherwise
        """
        try:
            # Call the notification endpoint
            response = await self._make_request(
                "POST", 
                "/notification/send/", 
                data={
                    "type": "video_ready",
                    "video_id": video_id,
                    "user_id": user_id
                }
            )
            
            # Check if response indicates success
            return response.get("success", False)
        
        except Exception as e:
            logger.error(f"Error sending video ready notification: {str(e)}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Django backend.
        
        Returns:
            Health status
        """
        try:
            # Call the health check endpoint
            response = await self._make_request("GET", "/health/")
            
            return {
                "status": "ok",
                "details": response
            }
        
        except Exception as e:
            logger.error(f"Django health check failed: {str(e)}")
            return {
                "status": "error",
                "details": str(e)
            }