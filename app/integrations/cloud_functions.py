"""
Client for integrating with Google Cloud Functions.
"""

import json
import base64
from typing import Dict, Any, Optional
import google.auth
from google.auth.transport.requests import AuthorizedSession
import requests

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class CloudFunctionsClient:
    """
    Client for invoking Google Cloud Functions.
    This client handles authentication and function invocation for video processing functions.
    """

    def __init__(self):
        """Initialize the Cloud Functions client with project ID and region from settings."""
        self.project_id = settings.GCP_PROJECT_ID
        self.region = settings.GCP_REGION
        self.session = None
        
        # Initialize session with Google credentials
        self._init_session()

    def _init_session(self) -> None:
        """
        Initialize an authorized session with Google Cloud credentials.
        """
        try:
            credentials, _ = google.auth.default()
            self.session = AuthorizedSession(credentials)
        except Exception as e:
            logger.error(f"Error initializing Google Cloud credentials: {str(e)}")
            raise

    async def invoke_function(
        self, function_name: str, data: Dict[str, Any], is_async: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke a Google Cloud Function.
        
        Args:
            function_name: Name of the Cloud Function
            data: Data to pass to the function
            is_async: Whether to invoke the function asynchronously
            
        Returns:
            Function response if not async, None otherwise
            
        Raises:
            Exception: If the function invocation fails
        """
        # Ensure session is initialized
        if self.session is None:
            self._init_session()

        # Build the function URL
        function_url = (
            f"https://{self.region}-{self.project_id}.cloudfunctions.net/{function_name}"
        )
        
        # Add async parameter if needed
        if is_async:
            function_url += "?async=true"
            
        try:
            # Make the request to the function
            response = self.session.post(
                function_url,
                data=json.dumps(data),
                headers={"Content-Type": "application/json"}
            )
            
            # Raise for HTTP error status
            response.raise_for_status()
            
            # Return response if not async
            if not is_async:
                return response.json()
                
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error when invoking Cloud Function: {str(e)}")
            raise Exception(f"Cloud Function invocation failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error invoking Cloud Function: {str(e)}")
            raise Exception(f"Cloud Function invocation failed: {str(e)}")

    async def process_video(self, video_id: str, storage_path: str, output_path: str) -> None:
        """
        Invoke the video processing Cloud Function.
        
        Args:
            video_id: ID of the video to process
            storage_path: GCS path to the video file
            output_path: GCS path for processed outputs
            
        Raises:
            Exception: If the function invocation fails
        """
        data = {
            "video_id": video_id,
            "input_path": storage_path,
            "output_path": output_path,
            "formats": ["hls", "dash"],
            "qualities": list(settings.VIDEO_QUALITY_PROFILES.keys())
        }
        
        await self.invoke_function(settings.VIDEO_PROCESSING_FUNCTION, data, is_async=True)

    async def generate_thumbnails(self, video_id: str, storage_path: str, output_path: str) -> None:
        """
        Invoke the thumbnail generation Cloud Function.
        
        Args:
            video_id: ID of the video to process
            storage_path: GCS path to the video file
            output_path: GCS path for thumbnail outputs
            
        Raises:
            Exception: If the function invocation fails
        """
        data = {
            "video_id": video_id,
            "input_path": storage_path,
            "output_path": output_path,
            "count": 5  # Generate 5 thumbnails
        }
        
        await self.invoke_function(settings.THUMBNAIL_GENERATION_FUNCTION, data, is_async=True)

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Cloud Functions.
        
        Returns:
            Health status
        """
        try:
            # Try to invoke a simple function to check health
            response = await self.invoke_function(
                "health-check",
                {"check": "status"},
                is_async=False
            )
            
            return {
                "status": "ok",
                "details": response
            }
        except Exception as e:
            logger.error(f"Cloud Functions health check failed: {str(e)}")
            return {
                "status": "error",
                "details": str(e)
            }