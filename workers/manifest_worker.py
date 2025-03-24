"""
Worker for generating streaming manifests in the EINO Streaming Service.

This module handles the generation of HLS and DASH manifests
for adaptive streaming of videos.
"""

import os
import asyncio
import datetime
import math
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError
from app.services.storage.storage_service import StorageService
from app.services.streaming.manifest_generator import ManifestGenerator

settings = get_settings()


class ManifestWorker:
    """
    Worker for generating streaming manifests.
    This worker creates HLS playlists and DASH MPD files for adaptive streaming.
    """

    def __init__(self):
        """Initialize the manifest worker with required services."""
        self.storage_service = StorageService()
        self.manifest_generator = ManifestGenerator()

    async def generate_hls_master_playlist(
        self, video_id: str, variant_playlists: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an HLS master playlist.
        
        Args:
            video_id: ID of the video
            variant_playlists: List of variant playlist data
            
        Returns:
            Master playlist content
            
        Raises:
            VideoProcessingError: If there's an error generating the playlist
        """
        try:
            # Generate the master playlist
            master_playlist = self.manifest_generator.generate_hls_master_playlist(variant_playlists)
            
            # Save to storage
            master_path = f"videos/{video_id}/hls/master.m3u8"
            await self.storage_service.save_file(master_path, master_playlist.encode('utf-8'))
            
            # Get the URL for the master playlist
            master_url = await self.storage_service.get_file_url(master_path)
            
            return master_url
        
        except Exception as e:
            logger.error(f"Error generating HLS master playlist for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to generate HLS master playlist: {str(e)}"
            )

    async def generate_hls_variant_playlists(
        self, video_id: str, segments_by_quality: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, str]:
        """
        Generate HLS variant playlists for each quality level.
        
        Args:
            video_id: ID of the video
            segments_by_quality: Dictionary of segments grouped by quality
            
        Returns:
            Dictionary of variant playlist URLs by quality
            
        Raises:
            VideoProcessingError: If there's an error generating the playlists
        """
        try:
            variant_urls = {}
            
            # Generate variant playlist for each quality
            for quality, segments in segments_by_quality.items():
                # Generate variant playlist
                variant_playlist = self.manifest_generator.generate_hls_variant_playlist(segments)
                
                # Save to storage
                variant_path = f"videos/{video_id}/hls/{quality}.m3u8"
                await self.storage_service.save_file(variant_path, variant_playlist.encode('utf-8'))
                
                # Get the URL for the variant playlist
                variant_url = await self.storage_service.get_file_url(variant_path)
                variant_urls[quality] = variant_url
            
            return variant_urls
        
        except Exception as e:
            logger.error(f"Error generating HLS variant playlists for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to generate HLS variant playlists: {str(e)}"
            )

    async def generate_dash_mpd(
        self, video_id: str, adaptation_sets: List[Dict[str, Any]], duration: float
    ) -> str:
        """
        Generate a DASH MPD (Media Presentation Description).
        
        Args:
            video_id: ID of the video
            adaptation_sets: List of adaptation set data
            duration: Video duration in seconds
            
        Returns:
            MPD URL
            
        Raises:
            VideoProcessingError: If there's an error generating the MPD
        """
        try:
            # Generate the MPD
            mpd = self.manifest_generator.generate_dash_mpd(adaptation_sets, duration)
            
            # Save to storage
            mpd_path = f"videos/{video_id}/dash/manifest.mpd"
            await self.storage_service.save_file(mpd_path, mpd.encode('utf-8'))
            
            # Get the URL for the MPD
            mpd_url = await self.storage_service.get_file_url(mpd_path)
            
            return mpd_url
        
        except Exception as e:
            logger.error(f"Error generating DASH MPD for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to generate DASH MPD: {str(e)}"
            )

    async def update_live_manifests(
        self, video_id: str, new_segments: Dict[str, Any], sequence_no: int, now: int
    ) -> Dict[str, str]:
        """
        Update live streaming manifests with new segments.
        
        Args:
            video_id: ID of the video
            new_segments: Information about the new segments
            sequence_no: Media sequence number for HLS
            now: Current time in milliseconds for DASH
            
        Returns:
            Dictionary with updated manifest URLs
            
        Raises:
            VideoProcessingError: If there's an error updating the manifests
        """
        try:
            # Update HLS playlists
            for quality, segments in new_segments["hls_segments"].items():
                # Generate live playlist (without EXT-X-ENDLIST)
                playlist = self.manifest_generator.generate_hls_live_playlist(segments, sequence_no)
                
                # Save updated playlist
                playlist_path = f"videos/{video_id}/hls/{quality}.m3u8"
                await self.storage_service.save_file(playlist_path, playlist.encode('utf-8'))
            
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
            mpd = self.manifest_generator.generate_dash_live_mpd(dash_adaptation_sets, now)
            
            # Save updated MPD
            mpd_path = f"videos/{video_id}/dash/manifest.mpd"
            await self.storage_service.save_file(mpd_path, mpd.encode('utf-8'))
            
            # Get manifest URLs
            hls_master_url = await self.storage_service.get_file_url(f"videos/{video_id}/hls/master.m3u8")
            dash_mpd_url = await self.storage_service.get_file_url(mpd_path)
            
            return {
                "hls_url": hls_master_url,
                "dash_url": dash_mpd_url
            }
        
        except Exception as e:
            logger.error(f"Error updating live manifests for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to update live manifests: {str(e)}"
            )

    async def prepare_hls_variant_data(
        self, video_id: str, transcoding_results: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare variant data for HLS master playlist generation.
        
        Args:
            video_id: ID of the video
            transcoding_results: Results from the transcoding process
            
        Returns:
            List of variant data for master playlist
        """
        try:
            variants = []
            
            for quality, result in transcoding_results.items():
                # Extract resolution dimensions
                width, height = result["resolution"].split("x")
                
                # Calculate bandwidth from bitrate
                bitrate = result["bitrate"]
                bandwidth = int(bitrate.replace("k", "000"))
                
                # Add variant info
                variants.append({
                    "bandwidth": bandwidth,
                    "resolution": result["resolution"],
                    "name": quality
                })
            
            return variants
        
        except Exception as e:
            logger.error(f"Error preparing HLS variant data for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to prepare HLS variant data: {str(e)}"
            )
    
    async def prepare_dash_adaptation_data(
        self, video_id: str, transcoding_results: Dict[str, Dict[str, Any]], duration: float
    ) -> List[Dict[str, Any]]:
        """
        Prepare adaptation set data for DASH MPD generation.
        
        Args:
            video_id: ID of the video
            transcoding_results: Results from the transcoding process
            duration: Video duration in seconds
            
        Returns:
            List of adaptation set data for MPD
        """
        try:
            adaptation_sets = []
            
            for quality, result in transcoding_results.items():
                # Extract resolution dimensions
                width, height = result["resolution"].split("x")
                
                # Calculate bandwidth from bitrate
                bitrate = result["bitrate"]
                bandwidth = int(bitrate.replace("k", "000"))
                
                # Add adaptation set info
                adaptation_sets.append({
                    "id": f"video_{quality}",
                    "mime_type": "video/mp4",
                    "codecs": "avc1.64001f",  # H.264 High Profile
                    "width": int(width),
                    "height": int(height),
                    "bandwidth": bandwidth,
                    "segment_timeline": result["segments"]
                })
            
            return adaptation_sets
        
        except Exception as e:
            logger.error(f"Error preparing DASH adaptation data for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to prepare DASH adaptation data: {str(e)}"
            )
    
    async def generate_all_manifests(
        self, video_id: str, transcoding_results: Dict[str, Dict[str, Dict[str, Any]]], duration: float
    ) -> Dict[str, str]:
        """
        Generate all streaming manifests for a video.
        
        Args:
            video_id: ID of the video
            transcoding_results: Results from the transcoding process
            duration: Video duration in seconds
            
        Returns:
            Dictionary with manifest URLs
            
        Raises:
            VideoProcessingError: If there's an error generating the manifests
        """
        try:
            urls = {}
            
            # Generate HLS manifests
            if "hls" in transcoding_results:
                hls_results = transcoding_results["hls"]
                
                # Prepare variant data
                variants = await self.prepare_hls_variant_data(video_id, hls_results)
                
                # Generate master playlist
                master_url = await self.generate_hls_master_playlist(video_id, variants)
                urls["hls_url"] = master_url
                
                # Generate variant playlists
                segments_by_quality = {
                    quality: result["segments"]
                    for quality, result in hls_results.items()
                }
                await self.generate_hls_variant_playlists(video_id, segments_by_quality)
            
            # Generate DASH manifest
            if "dash" in transcoding_results:
                dash_results = transcoding_results["dash"]
                
                # Prepare adaptation set data
                adaptation_sets = await self.prepare_dash_adaptation_data(video_id, dash_results, duration)
                
                # Generate MPD
                mpd_url = await self.generate_dash_mpd(video_id, adaptation_sets, duration)
                urls["dash_url"] = mpd_url
            
            return urls
        
        except Exception as e:
            logger.error(f"Error generating manifests for video {video_id}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to generate manifests: {str(e)}"
            )


async def generate_manifests_job(
    video_id: str, transcoding_results: Dict[str, Dict[str, Dict[str, Any]]], duration: float
):
    """
    Run a job to generate streaming manifests.
    
    Args:
        video_id: ID of the video
        transcoding_results: Results from the transcoding process
        duration: Video duration in seconds
        
    Returns:
        Dictionary with manifest URLs
    """
    worker = ManifestWorker()
    storage_service = StorageService()
    
    try:
        # Generate all manifests
        manifest_urls = await worker.generate_all_manifests(video_id, transcoding_results, duration)
        
        # Update video metadata with manifest URLs
        metadata = await storage_service.get_video_metadata(video_id)
        metadata["hls_url"] = manifest_urls.get("hls_url")
        metadata["dash_url"] = manifest_urls.get("dash_url")
        metadata["playback_url"] = manifest_urls.get("hls_url")  # Default to HLS
        await storage_service.save_metadata(video_id, metadata)
        
        return manifest_urls
        
    except Exception as e:
        logger.error(f"Error in manifests job for video {video_id}: {str(e)}")
        
        # Update video status to error
        metadata = await storage_service.get_video_metadata(video_id)
        metadata["status"] = "error"
        metadata["error"] = f"Manifest generation failed: {str(e)}"
        await storage_service.save_metadata(video_id, metadata)
        
        raise VideoProcessingError(video_id, f"Manifests job failed: {str(e)}")