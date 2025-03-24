"""
Worker for handling video chunk processing in the EINO Streaming Service.

This module handles the chunking of video files during upload, 
combining chunks after upload, and triggering subsequent processing steps.
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError
from app.services.storage.storage_service import StorageService
from app.services.processing.video_processor import VideoProcessor
from app.integrations.django_client import DjangoClient
from app.integrations.pubsub_client import PubSubClient

settings = get_settings()


class ChunkWorker:
    """
    Worker for processing video chunks.
    This worker handles the receipt and combination of video file chunks.
    """

    def __init__(self):
        """Initialize the chunk worker with required services."""
        self.storage_service = StorageService()
        self.video_processor = VideoProcessor()
        self.django_client = DjangoClient()
        self.pubsub_client = PubSubClient()

    async def process_chunk(self, video_id: str, chunk_index: int, chunk_data: bytes, total_chunks: int) -> Dict[str, Any]:
        """
        Process a single chunk of video data.
        
        Args:
            video_id: ID of the video
            chunk_index: Index of the current chunk
            chunk_data: Chunk binary data
            total_chunks: Total number of chunks for this video
            
        Returns:
            Processing result data including upload progress
            
        Raises:
            Exception: If there's an error processing the chunk
        """
        try:
            # Save the chunk to storage
            chunk_path = f"videos/{video_id}/chunks/chunk_{chunk_index}"
            await self.storage_service.save_file(chunk_path, chunk_data)
            
            # Update metadata with chunk progress
            metadata = await self.storage_service.get_video_metadata(video_id)
            metadata["chunks_received"] += 1
            metadata["upload_progress"] = (metadata["chunks_received"] / total_chunks) * 100
            metadata["total_chunks"] = total_chunks
            await self.storage_service.save_metadata(video_id, metadata)
            
            # Check if all chunks have been received
            if metadata["chunks_received"] >= total_chunks:
                # Start combining chunks if all are received
                await self.combine_chunks(video_id, total_chunks)
            
            return {
                "video_id": video_id,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "status": "uploaded",
                "progress": metadata["upload_progress"]
            }
        
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_index} for video {video_id}: {str(e)}")
            raise Exception(f"Failed to process chunk: {str(e)}")

    async def combine_chunks(self, video_id: str, total_chunks: int) -> Dict[str, Any]:
        """
        Combine all chunks into a single video file.
        
        Args:
            video_id: ID of the video
            total_chunks: Total number of chunks
            
        Returns:
            Combination result including output path
            
        Raises:
            Exception: If there's an error combining chunks
        """
        try:
            # Get video metadata
            metadata = await self.storage_service.get_video_metadata(video_id)
            output_path = f"videos/{video_id}/{os.path.basename(metadata['filename'])}"
            
            # Combine chunks
            await self.storage_service.combine_chunks(video_id, total_chunks, output_path)
            
            # Update metadata
            metadata["status"] = "uploaded"
            metadata["output_path"] = output_path
            await self.storage_service.save_metadata(video_id, metadata)
            
            # Notify PubSub that video is ready for processing
            await self.pubsub_client.notify_video_uploaded(video_id, metadata.get("owner_id"), metadata.get("company_id"))
            
            return {
                "video_id": video_id,
                "status": "uploaded",
                "output_path": output_path
            }
        
        except Exception as e:
            logger.error(f"Error combining chunks for video {video_id}: {str(e)}")
            
            # Update metadata with error status
            metadata = await self.storage_service.get_video_metadata(video_id)
            metadata["status"] = "error"
            metadata["error"] = f"Failed to combine chunks: {str(e)}"
            await self.storage_service.save_metadata(video_id, metadata)
            
            raise Exception(f"Failed to combine chunks: {str(e)}")
    
    async def cleanup_chunks(self, video_id: str) -> None:
        """
        Clean up chunk files after successful processing.
        
        Args:
            video_id: ID of the video
            
        Raises:
            Exception: If there's an error cleaning up chunks
        """
        try:
            # Delete the chunks directory
            chunks_path = f"videos/{video_id}/chunks"
            await self.storage_service.delete_directory(chunks_path)
        
        except Exception as e:
            logger.error(f"Error cleaning up chunks for video {video_id}: {str(e)}")
            # Non-fatal error, just log it
            

async def process_video_chunks(video_id: str, user_id: Optional[str] = None, company_id: Optional[str] = None):
    """
    Process all chunks for a video and start video processing.
    
    Args:
        video_id: ID of the video
        user_id: ID of the uploading user
        company_id: ID of the company
        
    Returns:
        Processing result
    """
    worker = ChunkWorker()
    video_processor = VideoProcessor()
    
    # Combine chunks
    combine_result = await worker.combine_chunks(video_id, await worker.storage_service.get_video_metadata(video_id)["total_chunks"])
    
    # Start video processing
    processing_result = await video_processor.process_video(video_id, user_id, company_id)
    
    # Clean up chunks after processing
    await worker.cleanup_chunks(video_id)
    
    return processing_result