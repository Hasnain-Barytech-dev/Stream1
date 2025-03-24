"""
HLS (HTTP Live Streaming) service for the EINO Streaming Service.
"""

from typing import Dict, Any, List
import os
import aiofiles
import aiofiles.os

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError
from app.services.streaming.manifest_generator import ManifestGenerator
from app.services.storage.storage_service import StorageService
from app.api.schemas import VideoFormat, VideoQuality

settings = get_settings()


class HLSService:
    """
    Service for HLS (HTTP Live Streaming) video streaming.
    This service handles HLS manifest generation and access.
    """

    def __init__(self):
        """Initialize the HLS service with dependencies."""
        self.storage_service = StorageService()
        self.manifest_generator = ManifestGenerator()

    async def get_manifest(self, video_id: str) -> Dict[str, Any]:
        """
        Get the HLS manifest for a video.
        
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
            manifest_url = await self.storage_service.get_hls_manifest_url(video_id)
            
            # Get available qualities
            available_qualities = await self._get_available_qualities(video_id)
            
            return {
                "video_id": video_id,
                "manifest_url": manifest_url,
                "format": VideoFormat.HLS,
                "available_qualities": available_qualities
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting HLS manifest for video {video_id}: {str(e)}")
            raise Exception(f"Failed to get HLS manifest: {str(e)}")

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
            # Get the list of variant playlists
            variant_playlists = await self.storage_service.list_hls_variants(video_id)
            
            # Map variant names to quality enum values
            qualities = []
            
            # Always include AUTO quality
            qualities.append(VideoQuality.AUTO)
            
            # Add each available quality
            for playlist in variant_playlists:
                # Extract quality from playlist name (e.g., "240p.m3u8" -> "240p")
                quality_str = os.path.basename(playlist).replace(".m3u8", "")
                
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

    async def generate_master_playlist(
        self, video_id: str, variant_playlists: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a master playlist for HLS streaming.
        
        Args:
            video_id: ID of the video
            variant_playlists: List of variant playlist data
            
        Returns:
            Master playlist content
            
        Raises:
            Exception: If there's an error generating the playlist
        """
        try:
            # Generate master playlist using manifest generator
            master_playlist = self.manifest_generator.generate_hls_master_playlist(variant_playlists)
            
            # Save master playlist to storage
            await self.storage_service.save_hls_master_playlist(video_id, master_playlist)
            
            return master_playlist
        
        except Exception as e:
            logger.error(f"Error generating HLS master playlist for video {video_id}: {str(e)}")
            raise Exception(f"Failed to generate HLS master playlist: {str(e)}")

    async def generate_variant_playlist(
        self, video_id: str, quality: str, segments: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a variant playlist for a specific quality.
        
        Args:
            video_id: ID of the video
            quality: Quality level (e.g., "240p")
            segments: List of segment data
            
        Returns:
            Variant playlist content
            
        Raises:
            Exception: If there's an error generating the playlist
        """
        try:
            # Generate variant playlist using manifest generator
            variant_playlist = self.manifest_generator.generate_hls_variant_playlist(segments)
            
            # Save variant playlist to storage
            await self.storage_service.save_hls_variant_playlist(video_id, quality, variant_playlist)
            
            return variant_playlist
        
        except Exception as e:
            logger.error(f"Error generating HLS variant playlist for video {video_id}, quality {quality}: {str(e)}")
            raise Exception(f"Failed to generate HLS variant playlist: {str(e)}")