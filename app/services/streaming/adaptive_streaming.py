"""
Adaptive streaming service for the EINO Streaming Service.
"""

from typing import Dict, Any, List, Tuple
import os

from app.config import get_settings
from app.core.logging import logger
from app.services.streaming.hls_service import HLSService
from app.services.streaming.dash_service import DASHService
from app.services.storage.storage_service import StorageService

settings = get_settings()


class AdaptiveStreamingService:
    """
    Service for adaptive streaming functionality.
    This service coordinates HLS and DASH streaming for adaptive bitrate video delivery.
    """

    def __init__(self):
        """Initialize the adaptive streaming service with dependencies."""
        self.hls_service = HLSService()
        self.dash_service = DASHService()
        self.storage_service = StorageService()

    async def prepare_adaptive_streaming(
        self, video_id: str, video_path: str, output_path: str
    ) -> Dict[str, Any]:
        """
        Prepare a video for adaptive streaming by generating necessary files and manifests.
        
        Args:
            video_id: ID of the video
            video_path: Path to the video file
            output_path: Base path for output files
            
        Returns:
            Result information
            
        Raises:
            Exception: If there's an error preparing the video
        """
        try:
            # Create output directories
            hls_output_path = os.path.join(output_path, "hls")
            dash_output_path = os.path.join(output_path, "dash")
            
            # Prepare output paths
            await self.storage_service.create_directory(hls_output_path)
            await self.storage_service.create_directory(dash_output_path)
            
            # Generate variants for different quality levels
            variants = []
            
            for quality, profile in settings.VIDEO_QUALITY_PROFILES.items():
                # Create quality-specific output directories
                hls_quality_path = os.path.join(hls_output_path, quality)
                dash_quality_path = os.path.join(dash_output_path, f"video_{quality}")
                
                await self.storage_service.create_directory(hls_quality_path)
                await self.storage_service.create_directory(dash_quality_path)
                
                # Add variant info
                variants.append({
                    "quality": quality,
                    "resolution": profile["resolution"],
                    "bitrate": profile["bitrate"],
                    "audio_bitrate": profile["audio_bitrate"],
                    "hls_output_path": hls_quality_path,
                    "dash_output_path": dash_quality_path
                })
            
            # Return the variant information for processing
            return {
                "video_id": video_id,
                "video_path": video_path,
                "hls_output_path": hls_output_path,
                "dash_output_path": dash_output_path,
                "variants": variants
            }
        
        except Exception as e:
            logger.error(f"Error preparing adaptive streaming for video {video_id}: {str(e)}")
            raise Exception(f"Failed to prepare adaptive streaming: {str(e)}")

    async def generate_manifests(
        self, video_id: str, segments_info: Dict[str, Any], duration: float
    ) -> Tuple[str, str]:
        """
        Generate HLS and DASH manifests for a processed video.
        
        Args:
            video_id: ID of the video
            segments_info: Information about the generated segments
            duration: Video duration in seconds
            
        Returns:
            Tuple of (hls_master_url, dash_mpd_url)
            
        Raises:
            Exception: If there's an error generating manifests
        """
        try:
            # Generate HLS master playlist
            hls_variants = []
            
            for quality, profile in settings.VIDEO_QUALITY_PROFILES.items():
                # Only include qualities that were actually generated
                if quality in segments_info["hls_segments"]:
                    # Get resolution dimensions
                    width, height = profile["resolution"].split("x")
                    
                    # Add variant info
                    hls_variants.append({
                        "bandwidth": int(profile["bitrate"].replace("k", "000")),
                        "resolution": profile["resolution"],
                        "name": quality
                    })
            
            # Generate HLS master playlist
            master_playlist = await self.hls_service.generate_master_playlist(video_id, hls_variants)
            
            # Generate HLS variant playlists
            for quality, segments in segments_info["hls_segments"].items():
                await self.hls_service.generate_variant_playlist(video_id, quality, segments)
            
            # Generate DASH MPD
            dash_adaptation_sets = []
            
            for quality, profile in settings.VIDEO_QUALITY_PROFILES.items():
                # Only include qualities that were actually generated
                if quality in segments_info["dash_segments"]:
                    # Get resolution dimensions
                    width, height = profile["resolution"].split("x")
                    
                    # Add adaptation set info
                    dash_adaptation_sets.append({
                        "id": f"video_{quality}",
                        "mime_type": "video/mp4",
                        "codecs": "avc1.64001f",  # H.264 High Profile
                        "width": int(width),
                        "height": int(height),
                        "bandwidth": int(profile["bitrate"].replace("k", "000")),
                        "segment_timeline": segments_info["dash_segments"][quality]
                    })
            
            # Generate DASH MPD
            mpd = await self.dash_service.generate_mpd(video_id, dash_adaptation_sets, duration)
            
            # Get manifest URLs
            hls_master_url = await self.storage_service.get_hls_manifest_url(video_id)
            dash_mpd_url = await self.storage_service.get_dash_manifest_url(video_id)
            
            return (hls_master_url, dash_mpd_url)
        
        except Exception as e:
            logger.error(f"Error generating manifests for video {video_id}: {str(e)}")
            raise Exception(f"Failed to generate manifests: {str(e)}")

    async def update_live_manifests(
        self, video_id: str, new_segments: Dict[str, Any], sequence_no: int, now: int
    ) -> Tuple[str, str]:
        """
        Update live streaming manifests with new segments.
        
        Args:
            video_id: ID of the video
            new_segments: Information about the new segments
            sequence_no: Media sequence number for HLS
            now: Current time in milliseconds for DASH
            
        Returns:
            Tuple of (hls_master_url, dash_mpd_url)
            
        Raises:
            Exception: If there's an error updating manifests
        """
        try:
            # Update HLS playlists
            for quality, segments in new_segments["hls_segments"].items():
                # Generate live playlist (without EXT-X-ENDLIST)
                playlist = self.hls_service.manifest_generator.generate_hls_live_playlist(
                    segments, sequence_no
                )
                
                # Save updated playlist
                await self.storage_service.save_hls_variant_playlist(video_id, quality, playlist)
            
            # Update DASH MPD
            dash_adaptation_sets = []
            
            for quality, profile in settings.VIDEO_QUALITY_PROFILES.items():
                # Only include qualities that were actually generated
                if quality in new_segments["dash_segments"]:
                    # Get resolution dimensions
                    width, height = profile["resolution"].split("x")
                    
                    # Add adaptation set info
                    dash_adaptation_sets.append({
                        "id": f"video_{quality}",
                        "mime_type": "video/mp4",
                        "codecs": "avc1.64001f",  # H.264 High Profile
                        "width": int(width),
                        "height": int(height),
                        "bandwidth": int(profile["bitrate"].replace("k", "000")),
                        "segment_timeline": new_segments["dash_segments"][quality],
                        "start_number": sequence_no
                    })
            
            # Generate live MPD
            mpd = self.dash_service.manifest_generator.generate_dash_live_mpd(
                dash_adaptation_sets, now
            )
            
            # Save updated MPD
            await self.storage_service.save_dash_mpd(video_id, mpd)
            
            # Get manifest URLs
            hls_master_url = await self.storage_service.get_hls_manifest_url(video_id)
            dash_mpd_url = await self.storage_service.get_dash_manifest_url(video_id)
            
            return (hls_master_url, dash_mpd_url)
        
        except Exception as e:
            logger.error(f"Error updating live manifests for video {video_id}: {str(e)}")
            raise Exception(f"Failed to update live manifests: {str(e)}")