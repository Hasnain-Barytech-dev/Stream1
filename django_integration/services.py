"""
Services for integration with the Django backend.
These services handle communication with the Django API.
"""

from typing import Dict, Any, List, Optional, Tuple
import httpx
import asyncio
import json
from datetime import datetime

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import IntegrationError

from .models import DjangoUser, DjangoCompany, DjangoCompanyUser, DjangoDepartment, DjangoResource
from .serializers import (
    DjangoUserSerializer, 
    DjangoCompanySerializer, 
    DjangoCompanyUserSerializer,
    DjangoDepartmentSerializer,
    DjangoResourceSerializer
)

settings = get_settings()


class DjangoIntegrationService:
    """
    Service for integrating with the Django backend API.
    This class provides methods for interacting with Django backend services.
    """

    def __init__(self):
        """Initialize with API URL from settings."""
        self.api_url = settings.DJANGO_API_URL
        self.timeout = httpx.Timeout(30.0)  # 30 seconds timeout

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Any = None, 
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Django API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            headers: Request headers
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
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
                    params=params if method.upper() == "GET" else None,
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
            raise IntegrationError("django", f"API error: {error_detail}")
        
        except Exception as e:
            logger.error(f"Error making request to Django API: {str(e)}")
            raise IntegrationError("django", f"Request failed: {str(e)}")

    async def authenticate_user(self, username: str, password: str) -> Optional[DjangoUser]:
        """
        Authenticate a user with Django backend.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            DjangoUser if authentication succeeds, None otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
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
                return DjangoUserSerializer.from_dict(response["data"])
            
            return None
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise IntegrationError("django", f"Authentication failed: {str(e)}")

    async def get_user_details(self, user_id: str) -> DjangoUser:
        """
        Get user details from Django backend.
        
        Args:
            user_id: User ID
            
        Returns:
            DjangoUser object
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the user details endpoint
            response = await self._make_request("GET", f"/user/{user_id}/")
            
            # Check if response contains user data
            if "data" in response:
                return DjangoUserSerializer.from_dict(response["data"])
            
            raise IntegrationError("django", "Failed to get user details")
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
            raise IntegrationError("django", f"Failed to get user details: {str(e)}")

    async def update_user_details(self, user_id: str, data: Dict[str, Any]) -> DjangoUser:
        """
        Update user details in Django backend.
        
        Args:
            user_id: User ID
            data: User data to update
            
        Returns:
            Updated DjangoUser
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the user update endpoint
            response = await self._make_request("PATCH", f"/user/{user_id}/", data=data)
            
            # Check if response contains user data
            if "data" in response:
                return DjangoUserSerializer.from_dict(response["data"])
            
            raise IntegrationError("django", "Failed to update user details")
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error updating user details: {str(e)}")
            raise IntegrationError("django", f"Failed to update user details: {str(e)}")

    async def get_company_details(self, company_id: str) -> DjangoCompany:
        """
        Get company details from Django backend.
        
        Args:
            company_id: Company ID
            
        Returns:
            DjangoCompany object
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the company details endpoint
            response = await self._make_request("GET", f"/company/{company_id}/")
            
            # Check if response contains company data
            if "data" in response:
                return DjangoCompanySerializer.from_dict(response["data"])
            
            raise IntegrationError("django", "Failed to get company details")
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting company details: {str(e)}")
            raise IntegrationError("django", f"Failed to get company details: {str(e)}")

    async def get_company_user(self, user_id: str, company_id: str) -> Optional[DjangoCompanyUser]:
        """
        Get company user relationship from Django backend.
        
        Args:
            user_id: User ID
            company_id: Company ID
            
        Returns:
            DjangoCompanyUser if exists, None otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the company user endpoint
            response = await self._make_request("GET", f"/company/{company_id}/user/{user_id}/")
            
            # Check if response contains company user data
            if "data" in response:
                return DjangoCompanyUserSerializer.from_dict(response["data"])
            
            return None
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting company user: {str(e)}")
            raise IntegrationError("django", f"Failed to get company user: {str(e)}")

    async def get_department_details(self, department_id: str) -> DjangoDepartment:
        """
        Get department details from Django backend.
        
        Args:
            department_id: Department ID
            
        Returns:
            DjangoDepartment object
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the department details endpoint
            response = await self._make_request("GET", f"/department/{department_id}/")
            
            # Check if response contains department data
            if "data" in response:
                return DjangoDepartmentSerializer.from_dict(response["data"])
            
            raise IntegrationError("django", "Failed to get department details")
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting department details: {str(e)}")
            raise IntegrationError("django", f"Failed to get department details: {str(e)}")

    async def check_department_access(self, user_id: str, department_id: str) -> bool:
        """
        Check if a user has access to a department.
        
        Args:
            user_id: User ID
            department_id: Department ID
            
        Returns:
            True if user has access, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the department access check endpoint
            response = await self._make_request(
                "GET", f"/department/{department_id}/check-access/{user_id}/"
            )
            
            # Check if response indicates access
            return response.get("has_access", False)
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error checking department access: {str(e)}")
            raise IntegrationError("django", f"Failed to check department access: {str(e)}")

    async def update_video_metadata(self, video_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update video metadata in Django backend.
        
        Args:
            video_id: Video ID
            metadata: Video metadata
            
        Returns:
            True if update succeeds, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the video update endpoint
            response = await self._make_request(
                "PATCH", f"/resource/video/{video_id}/", data=metadata
            )
            
            # Check if response indicates success
            return response.get("success", False)
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            raise IntegrationError("django", f"Failed to update video metadata: {str(e)}")

    async def notify_video_ready(self, video_id: str, user_id: str) -> bool:
        """
        Send notification that a video is ready for streaming.
        
        Args:
            video_id: Video ID
            user_id: User ID
            
        Returns:
            True if notification sent, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
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
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error sending video ready notification: {str(e)}")
            raise IntegrationError("django", f"Failed to send notification: {str(e)}")

    async def list_videos(
        self, user_id: str = None, company_id: str = None, skip: int = 0, limit: int = 20
    ) -> List[DjangoResource]:
        """
        List videos from Django backend.
        
        Args:
            user_id: Filter by user ID
            company_id: Filter by company ID
            skip: Number of items to skip
            limit: Maximum number of items to return
            
        Returns:
            List of DjangoResource objects
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Build query parameters
            params = {
                "skip": skip,
                "limit": limit
            }
            
            if user_id:
                params["user_id"] = user_id
                
            if company_id:
                params["company_id"] = company_id
                
            # Call the videos list endpoint
            response = await self._make_request("GET", "/resource/videos/", params=params)
            
            # Check if response contains videos data
            if "data" in response:
                return [DjangoResourceSerializer.from_dict(video) for video in response["data"]]
            
            return []
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error listing videos: {str(e)}")
            raise IntegrationError("django", f"Failed to list videos: {str(e)}")

    async def check_upload_permission(self, company_user_id: str) -> bool:
        """
        Check if a user has permission to upload videos.
        
        Args:
            company_user_id: Company user ID
            
        Returns:
            True if user has permission, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the permission check endpoint
            response = await self._make_request(
                "GET", f"/resource/check-upload-permission/{company_user_id}/"
            )
            
            # Check if response indicates permission
            return response.get("has_permission", False)
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error checking upload permission: {str(e)}")
            raise IntegrationError("django", f"Failed to check permission: {str(e)}")

    async def check_storage_limit(self, company_user_id: str, file_size: int) -> bool:
        """
        Check if a user has enough storage for an upload.
        
        Args:
            company_user_id: Company user ID
            file_size: File size in bytes
            
        Returns:
            True if enough storage, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the storage check endpoint
            response = await self._make_request(
                "GET", 
                f"/resource/check-storage/{company_user_id}/",
                params={"file_size": file_size}
            )
            
            # Check if response indicates enough storage
            return response.get("has_storage", False)
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error checking storage limit: {str(e)}")
            raise IntegrationError("django", f"Failed to check storage: {str(e)}")

    async def check_video_access(self, company_user_id: str, video_id: str) -> bool:
        """
        Check if a user has access to a video.
        
        Args:
            company_user_id: Company user ID
            video_id: Video ID
            
        Returns:
            True if user has access, False otherwise
            
        Raises:
            IntegrationError: If there's an error communicating with the API
        """
        try:
            # Call the video access check endpoint
            response = await self._make_request(
                "GET", f"/resource/check-video-access/{company_user_id}/{video_id}/"
            )
            
            # Check if response indicates access
            return response.get("has_access", False)
        
        except IntegrationError:
            raise
        
        except Exception as e:
            logger.error(f"Error checking video access: {str(e)}")
            raise IntegrationError("django", f"Failed to check access: {str(e)}")

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