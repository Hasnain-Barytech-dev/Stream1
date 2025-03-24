"""
Video processing service for the EINO Streaming Service.
"""

from typing import Dict, Any, List, Optional
import os
import asyncio
import tempfile
import shutil
from datetime import datetime

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError, VideoNotFoundError
from app.services.storage.storage_service import StorageService
from app.services.processing.transcoder import Transcoder
from app.services.processing.thumbnail_generator import ThumbnailGenerator
from app.services.processing.quality_analyzer import QualityAnalyzer
from app.services.streaming.adaptive_streaming import AdaptiveStreamingService
from app.integrations.django_client import DjangoClient
from app.integrations.pubsub_client import PubSubClient

settings = get_settings()


class VideoProcessor:
    """
    Service for processing uploaded videos.
    This service coordinates video transcoding, thumbnail generation, and adaptive streaming.
    """

    def __init__(self):
        """Initialize the video processor with dependencies."""
        self.storage_service = StorageService()
        self.transcoder = Transcoder()
        self.thumbnail_generator = ThumbnailGenerator()
        self.quality_analyzer = QualityAnalyzer()
        self.adaptive_streaming = AdaptiveStreamingService()
        self.django_client = DjangoClient()
        self.pubsub_client = PubSubClient()

    async def process_video(
        self, video_id: str, user_id: str = None, company_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a video by transcoding it to different formats and qualities.
        
        Args:
            video_id: ID of the video to process
            user_id: ID of the user who uploaded the video
            company_id: ID of the company the video belongs to
            
        Returns:
            Processing result data
            
        Raises:
            VideoNotFoundError: If the video is not found
            VideoProcessingError: If there's an error processing the video
        """
        try:
            # Get video metadata
            metadata = await self.storage_service.get_video_metadata(video_id)
            
            # Update status to processing
            metadata["status"] = "processing"
            metadata["updated_at"] = datetime.utcnow().isoformat()
            await self.storage_service.save_metadata(video_id, metadata)
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # Download video file to temp directory
                    input_path = os.path.join(temp_dir, os.path.basename(metadata["filename"]))
                    
                    video_file = await self.storage_service.get_file(metadata["output_path"])
                    with open(input_path, "wb") as f:
                        f.write(video_file.read())
                    
                    # Analyze video quality
                    video_info = await self.quality_analyzer.analyze_video(input_path)
                    
                    # Update metadata with video information
                    metadata["duration"] = video_info["duration"]
                    metadata["width"] = video_info["width"]
                    metadata["height"] = video_info["height"]
                    metadata["format"] = video_info["format"]
                    metadata["bitrate"] = video_info["bitrate"]
                    metadata["updated_at"] = datetime.utcnow().isoformat()
                    await self.storage_service.save_metadata(video_id, metadata)
                    
                    # Generate thumbnails
                    thumbnails = await self.thumbnail_generator.generate_thumbnails(
                        input_path, 
                        os.path.join(temp_dir, "thumbnails"), 
                        count=3
                    )
                    
                    # Upload thumbnails to storage
                    for i, thumbnail_path in enumerate(thumbnails):
                        with open(thumbnail_path, "rb") as f:
                            thumbnail_data = f.read()
                            
                        await self.storage_service.save_file(
                            f"videos/{video_id}/thumbnails/thumbnail_{i}.jpg",
                            thumbnail_data
                        )
                    
                    # Set main thumbnail
                    with open(thumbnails[0], "rb") as f:
                        thumbnail_data = f.read()
                        
                    await self.storage_service.save_file(
                        f"videos/{video_id}/thumbnail.jpg",
                        thumbnail_data
                    )
                    
                    # Prepare for adaptive streaming
                    streaming_info = await self.adaptive_streaming.prepare_adaptive_streaming(
                        video_id,
                        input_path,
                        os.path.join(temp_dir, "streaming")
                    )
                    
                    # Transcode video to different formats and qualities
                    segments_info = await self.transcoder.transcode_video_for_streaming(
                        input_path,
                        streaming_info["variants"],
                        video_info
                    )
                    
                    # Generate manifests
                    hls_master_url, dash_mpd_url = await self.adaptive_streaming.generate_manifests(
                        video_id,
                        segments_info,
                        video_info["duration"]
                    )
                    
                    # Update metadata with streaming URLs
                    metadata["status"] = "ready"
                    metadata["thumbnail_url"] = await self.storage_service.get_file_url(
                        f"videos/{video_id}/thumbnail.jpg"
                    )
                    metadata["hls_url"] = hls_master_url
                    metadata["dash_url"] = dash_mpd_url
                    metadata["playback_url"] = hls_master_url
                    metadata["updated_at"] = datetime.utcnow().isoformat()
                    await self.storage_service.save_metadata(video_id, metadata)
                    
                    # Notify Django backend
                    await self.django_client.update_video_metadata(video_id, {
                        "status": "ready",
                        "duration": video_info["duration"],
                        "width": video_info["width"],
                        "height": video_info["height"],
                        "thumbnail_url": metadata["thumbnail_url"],
                        "playback_url": metadata["playback_url"]
                    })
                    
                    # Notify user that video is ready
                    if user_id:
                        await self.django_client.notify_video_ready(video_id, user_id)
                    
                    # Publish event to Pub/Sub
                    await self.pubsub_client.notify_video_processed(video_id, "success")
                    
                    return {
                        "video_id": video_id,
                        "status": "ready",
                        "thumbnail_url": metadata["thumbnail_url"],
                        "playback_url": metadata["playback_url"]
                    }
                
                except Exception as e:
                    # Update metadata with error status
                    metadata["status"] = "error"
                    metadata["error"] = str(e)
                    metadata["updated_at"] = datetime.utcnow().isoformat()
                    await self.storage_service.save_metadata(video_id, metadata)
                    
                    # Notify Django backend
                    await self.django_client.update_video_metadata(video_id, {
                        "status": "error",
                        "error": str(e)
                    })
                    
                    # Publish event to Pub/Sub
                    await self.pubsub_client.notify_video_processed(video_id, "error")
                    
                    logger.error(f"Error processing video {video_id}: {str(e)}")
                    raise VideoProcessingError(video_id, str(e))
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {str(e)}")
            raise VideoProcessingError(video_id, str(e))

    async def retry_processing(self, video_id: str) -> Dict[str, Any]:
        """
        Retry processing a failed video.
        
        Args:
            video_id: ID of the video to retry
            
        Returns:
            Processing result data
            
        Raises:
            VideoNotFoundError: If the video is not found
            VideoProcessingError: If there's an error processing the video
        """
        try:
            # Get video metadata
            metadata = await self.storage_service.get_video_metadata(video_id)
            
            # Check if video is in error state
            if metadata["status"] != "error":
                raise VideoProcessingError(
                    video_id, 
                    f"Cannot retry processing for video in state: {metadata['status']}"
                )
                
            # Reset status to pending
            metadata["status"] = "pending"
            metadata["error"] = None
            metadata["updated_at"] = datetime.utcnow().isoformat()
            await self.storage_service.save_metadata(video_id, metadata)
            
            # Process video
            return await self.process_video(
                video_id, 
                metadata.get("owner_id"), 
                metadata.get("company_id")
            )
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error retrying video processing {video_id}: {str(e)}")
            raise VideoProcessingError(video_id, f"Failed to retry processing: {str(e)}")