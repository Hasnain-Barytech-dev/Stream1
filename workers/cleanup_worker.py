"""
Worker for handling cleanup operations in the EINO Streaming Service.

This module handles the cleanup of temporary files, expired content,
and error recovery in the video processing pipeline.
"""

import os
import asyncio
import datetime
from typing import Dict, Any, List, Optional

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import StorageError
from app.services.storage.storage_service import StorageService
from app.services.metrics.metrics_service import MetricsService
from app.integrations.django_client import DjangoClient

settings = get_settings()


class CleanupWorker:
    """
    Worker for cleanup operations.
    This worker handles cleanup of temporary files and expired content.
    """

    def __init__(self):
        """Initialize the cleanup worker with required services."""
        self.storage_service = StorageService()
        self.metrics_service = MetricsService()
        self.django_client = DjangoClient()

    async def cleanup_temporary_files(self, video_id: str) -> None:
        """
        Clean up temporary files for a video.
        
        Args:
            video_id: ID of the video
            
        Raises:
            StorageError: If there's an error cleaning up files
        """
        try:
            # Clean up chunk files
            chunks_path = f"videos/{video_id}/chunks"
            await self.storage_service.delete_directory(chunks_path)
            
            logger.info(f"Cleaned up temporary chunk files for video {video_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up temporary files for video {video_id}: {str(e)}")
            # Non-fatal error, just log it

    async def cleanup_failed_processing(self, video_id: str) -> None:
        """
        Clean up after failed video processing.
        
        Args:
            video_id: ID of the video
            
        Raises:
            StorageError: If there's an error cleaning up
        """
        try:
            # Get video metadata
            metadata = await self.storage_service.get_video_metadata(video_id)
            
            if metadata["status"] != "error":
                # Only clean up failed processing
                return
                
            # Clean up processing directories
            hls_path = f"videos/{video_id}/hls"
            dash_path = f"videos/{video_id}/dash"
            
            await self.storage_service.delete_directory(hls_path)
            await self.storage_service.delete_directory(dash_path)
            
            # Update metadata
            metadata["cleanup_performed"] = True
            metadata["cleaned_at"] = datetime.datetime.utcnow().isoformat()
            await self.storage_service.save_metadata(video_id, metadata)
            
            logger.info(f"Cleaned up failed processing for video {video_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up failed processing for video {video_id}: {str(e)}")
            # Non-fatal error, just log it

    async def cleanup_expired_content(self, expiration_days: int = 30) -> List[str]:
        """
        Clean up expired videos.
        
        Args:
            expiration_days: Number of days after which videos are considered expired
            
        Returns:
            List of cleaned up video IDs
            
        Raises:
            StorageError: If there's an error cleaning up
        """
        try:
            # Get all videos
            videos = await self.storage_service.list_videos({}, 0, 1000)
            
            # Calculate expiration date
            expiration_date = datetime.datetime.utcnow() - datetime.timedelta(days=expiration_days)
            expiration_str = expiration_date.isoformat()
            
            cleaned_videos = []
            
            # Check each video for expiration
            for video in videos:
                # Skip if not expired
                if video.get("created_at", "") > expiration_str:
                    continue
                    
                # Skip if not marked for cleanup
                if not video.get("allow_cleanup", False):
                    continue
                
                # Clean up video
                video_id = video["id"]
                await self.cleanup_video(video_id)
                
                cleaned_videos.append(video_id)
            
            logger.info(f"Cleaned up {len(cleaned_videos)} expired videos")
            
            return cleaned_videos
        
        except Exception as e:
            logger.error(f"Error cleaning up expired content: {str(e)}")
            raise StorageError("cleanup_expired", f"Failed to clean up expired content: {str(e)}")

    async def cleanup_video(self, video_id: str) -> None:
        """
        Clean up all resources for a video.
        
        Args:
            video_id: ID of the video
            
        Raises:
            StorageError: If there's an error cleaning up
        """
        try:
            # Delete video directory
            video_path = f"videos/{video_id}"
            await self.storage_service.delete_directory(video_path)
            
            # Delete metadata
            await self.storage_service.delete_metadata(video_id)
            
            logger.info(f"Cleaned up all resources for video {video_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up video {video_id}: {str(e)}")
            raise StorageError("cleanup_video", f"Failed to clean up video: {str(e)}")

    async def recover_stalled_processing(self, stall_hours: int = 4) -> List[str]:
        """
        Recover stalled video processing.
        
        Args:
            stall_hours: Number of hours after which processing is considered stalled
            
        Returns:
            List of recovered video IDs
            
        Raises:
            StorageError: If there's an error recovering
        """
        try:
            # Get all videos
            videos = await self.storage_service.list_videos({"status": "processing"}, 0, 100)
            
            # Calculate stall time
            stall_time = datetime.datetime.utcnow() - datetime.timedelta(hours=stall_hours)
            stall_str = stall_time.isoformat()
            
            recovered_videos = []
            
            # Check each video for stalled processing
            for video in videos:
                # Skip if not stalled
                if video.get("updated_at", "") > stall_str:
                    continue
                
                # Mark as error
                video_id = video["id"]
                metadata = await self.storage_service.get_video_metadata(video_id)
                metadata["status"] = "error"
                metadata["error"] = f"Processing stalled for over {stall_hours} hours"
                metadata["stalled_at"] = datetime.datetime.utcnow().isoformat()
                await self.storage_service.save_metadata(video_id, metadata)
                
                # Clean up stalled processing
                await self.cleanup_failed_processing(video_id)
                
                # Notify Django backend
                await self.django_client.update_video_metadata(video_id, {
                    "status": "error",
                    "error": f"Processing stalled for over {stall_hours} hours"
                })
                
                recovered_videos.append(video_id)
            
            logger.info(f"Recovered {len(recovered_videos)} stalled videos")
            
            return recovered_videos
        
        except Exception as e:
            logger.error(f"Error recovering stalled processing: {str(e)}")
            raise StorageError("recover_stalled", f"Failed to recover stalled processing: {str(e)}")

    async def cleanup_orphaned_files(self) -> int:
        """
        Clean up orphaned files (files without associated metadata).
        
        Returns:
            Number of cleaned up files
            
        Raises:
            StorageError: If there's an error cleaning up
        """
        try:
            # Get all video IDs from metadata
            videos = await self.storage_service.list_videos({}, 0, 10000)
            video_ids = {video["id"] for video in videos}
            
            # List all video directories
            video_dirs = await self.storage_service.list_directories("videos")
            
            cleaned_count = 0
            
            # Check each directory for orphaned files
            for dir_path in video_dirs:
                # Extract video ID from path
                parts = dir_path.split('/')
                if len(parts) < 2:
                    continue
                dir_video_id = parts[1]
                
                # Skip if directory has associated metadata
                if dir_video_id in video_ids:
                    continue
                
                # Clean up orphaned directory
                await self.storage_service.delete_directory(dir_path)
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} orphaned directories")
            
            return cleaned_count
        
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {str(e)}")
            raise StorageError("cleanup_orphaned", f"Failed to clean up orphaned files: {str(e)}")


async def run_cleanup_job():
    """
    Run a cleanup job.
    
    Returns:
        Cleanup summary
    """
    worker = CleanupWorker()
    
    try:
        # Clean up temporary files
        # This is just a placeholder, in a real job we'd have specific videos to clean up
        
        # Clean up expired content
        expired_videos = await worker.cleanup_expired_content()
        
        # Recover stalled processing
        recovered_videos = await worker.recover_stalled_processing()
        
        # Clean up orphaned files
        orphaned_count = await worker.cleanup_orphaned_files()
        
        return {
            "expired_videos_cleaned": len(expired_videos),
            "stalled_videos_recovered": len(recovered_videos),
            "orphaned_directories_cleaned": orphaned_count,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup job: {str(e)}")
        raise