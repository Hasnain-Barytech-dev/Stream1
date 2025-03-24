"""
DASH (Dynamic Adaptive Streaming over HTTP) service for the EINO Streaming Service.
"""

from typing import Dict, Any, List
import os

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError
from app.services.streaming.manifest_generator import ManifestGenerator
from app.services.storage.storage_service import StorageService
from app.api.schemas import VideoFormat, VideoQuality

settings = get_settings()


class DASHService:
    """
    Service for DASH (Dynamic Adaptive Streaming over HTTP) video streaming.
    This service handles DASH manifest generation and access.
    """

    def __init__(self):
        """Initialize the DASH service with dependencies."""
        self.storage_service = StorageService()
        self.manifest_generator = ManifestGenerator()

    async def get_manifest(self, video_id: str) -> Dict[str, Any]:
        """
        Get the DASH manifest for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Manifest data
            
        Raises:
            VideoNotFoundError: If the video is not found
            Exception: If there's an error getting the manifest
        """
        try:
            # Get video metadata
            metadata = await self.storage_service.get_video_metadata(video_id)
            
            # Check if video exists and is ready
            if metadata["status"] != "ready":
                raise Exception(f"Video is not ready for streaming. Status: {metadata['status']}")
            
            # Get the manifest URL
            manifest_url = await self.storage_service.get_dash_manifest_url(video_id)
            
            # Get available qualities
            available_qualities = await self._get_available_qualities(video_id)
            
            return {
                "video_id": video_id,
                "manifest_url": manifest_url,
                "format": VideoFormat.DASH,
                "available_qualities": available_qualities
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting DASH manifest for video {video_id}: {str(e)}")
            raise Exception(f"Failed to get DASH manifest: {str(e)}")

    async def _get_available_qualities(self, video_id: str) -> List[VideoQuality]:
        """
        Get available qualities for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            List of available qualities
            
        Raises:
            Exception: If there's an error getting the qualities
        """
        try:
            # Get the list of adaptation sets
            adaptation_sets = await self.storage_service.list_dash_adaptations(video_id)
            
            # Map adaptation set names to quality enum values
            qualities = []
            
            # Always include AUTO quality
            qualities.append(VideoQuality.AUTO)
            
            # Add each available quality
            for adaptation in adaptation_sets:
                # Extract quality from adaptation set ID (e.g., "video_240p" -> "240p")
                quality_str = adaptation.replace("video_", "")
                
                # Try to map to enum
                try:
                    quality = VideoQuality(quality_str)
                    qualities.append(quality)
                except ValueError:
                    # Skip unknown qualities
                    pass
            
            return qualities
        
        except Exception as e:
            logger.error(f"Error getting available qualities for video {video_id}: {str(e)}")
            return [VideoQuality.AUTO]  # Default to AUTO only

    async def generate_mpd(
        self, video_id: str, adaptation_sets: List[Dict[str, Any]], duration: float
    ) -> str:
        """
        Generate an MPD (Media Presentation Description) for DASH streaming.
        
        Args:
            video_id: ID of the video
            adaptation_sets: List of adaptation set data
            duration: Video duration in seconds
            
        Returns:
            MPD content
            
        Raises:
            Exception: If there's an error generating the MPD
        """
        try:
            # Generate MPD using manifest generator
            mpd = self.manifest_generator.generate_dash_mpd(adaptation_sets, duration)
            
            # Save MPD to storage
            await self.storage_service.save_dash_mpd(video_id, mpd)
            
            return mpd
        
        except Exception as e:
            logger.error(f"Error generating DASH MPD for video {video_id}: {str(e)}")
            raise Exception(f"Failed to generate DASH MPD: {str(e)}")

    async def generate_init_segment(
        self, video_id: str, quality: str, init_data: bytes
    ) -> None:
        """
        Generate an initialization segment for a specific quality.
        
        Args:
            video_id: ID of the video
            quality: Quality level (e.g., "240p")
            init_data: Initialization segment data
            
        Raises:
            Exception: If there's an error generating the segment
        """
        try:
            # Save initialization segment to storage
            await self.storage_service.save_dash_init_segment(video_id, quality, init_data)
        
        except Exception as e:
            logger.error(f"Error generating DASH init segment for video {video_id}, quality {quality}: {str(e)}")
            raise Exception(f"Failed to generate DASH init segment: {str(e)}")