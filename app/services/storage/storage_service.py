"""
Storage service for the EINO Streaming Service.
This is a facade that abstracts the underlying storage implementation.
"""

from typing import Dict, Any, List, Tuple, BinaryIO, Optional
import os
import uuid
import json
from datetime import datetime
import aiofiles
import aiofiles.os

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError, StorageError, UploadError
from app.services.storage.gcs_service import GCSService
from app.services.storage.local_service import LocalService
from app.integrations.django_client import DjangoClient

settings = get_settings()


class StorageService:
    """
    Service for handling storage operations.
    This service provides a unified interface for different storage backends.
    """

    def __init__(self):
        """Initialize the storage service with appropriate backend."""
        self.django_client = DjangoClient()
        
        # Use local storage for development, GCS for production
        if settings.DEV_MODE:
            self.storage = LocalService()
        else:
            self.storage = GCSService()

    async def initialize_upload(
        self,
        filename: str,
        file_size: int,
        content_type: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        user_id: str = None,
        company_id: str = None
    ) -> Dict[str, Any]:
        """
        Initialize a new video upload.
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            content_type: Content type (e.g., "video/mp4")
            title: Video title (optional)
            description: Video description (optional)
            user_id: ID of the uploading user
            company_id: ID of the company
            
        Returns:
            Upload initialization data including video ID and upload URL
            
        Raises:
            StorageError: If there's an error initializing the upload
        """
        try:
            # Generate a unique video ID
            video_id = str(uuid.uuid4())
            
            # Generate upload URL or path
            upload_url = f"{settings.API_V1_STR}/upload/chunk"
            
            # Create a metadata record for the video
            metadata = {
                "id": video_id,
                "filename": filename,
                "size": file_size,
                "content_type": content_type,
                "title": title or os.path.splitext(filename)[0],
                "description": description or "",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "owner_id": user_id,
                "company_id": company_id,
                "upload_progress": 0,
                "chunks_received": 0,
                "total_chunks": 0
            }
            
            # Save the metadata
            await self.storage.save_metadata(video_id, metadata)
            
            # Create the video directory
            video_path = f"videos/{video_id}"
            chunks_path = f"{video_path}/chunks"
            
            await self.create_directory(video_path)
            await self.create_directory(chunks_path)
            
            # Return the initialization data
            return {
                "video_id": video_id,
                "upload_url": upload_url,
                "expiration": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error initializing upload: {str(e)}")
            raise StorageError("initialize_upload", f"Failed to initialize upload: {str(e)}")

    async def upload_chunk(
        self, video_id: str, chunk_index: int, total_chunks: int, chunk_data: bytes, user_id: str = None
    ) -> Dict[str, Any]:
        """
        Upload a chunk of a video.
        
        Args:
            video_id: ID of the video
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            chunk_data: Chunk data as bytes
            user_id: ID of the uploading user (for validation)
            
        Returns:
            Upload result data
            
        Raises:
            VideoNotFoundError: If the video is not found
            UploadError: If there's an error uploading the chunk
        """
        try:
            # Get the video metadata
            metadata = await self.get_video_metadata(video_id)
            
            # Validate owner if user_id is provided
            if user_id and metadata["owner_id"] != user_id:
                raise UploadError("User does not have permission to upload to this video")
            
            # Update total chunks if this is the first chunk
            if metadata["total_chunks"] == 0:
                metadata["total_chunks"] = total_chunks
            
            # Validate chunk index and total chunks
            if chunk_index >= total_chunks:
                raise UploadError(f"Chunk index {chunk_index} exceeds total chunks {total_chunks}")
            
            if metadata["total_chunks"] != total_chunks:
                raise UploadError(f"Total chunks mismatch: expected {metadata['total_chunks']}, got {total_chunks}")
            
            # Save the chunk
            chunk_path = f"videos/{video_id}/chunks/chunk_{chunk_index}"
            await self.storage.save_file(chunk_path, chunk_data)
            
            # Update metadata
            metadata["chunks_received"] += 1
            metadata["upload_progress"] = (metadata["chunks_received"] / total_chunks) * 100
            metadata["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated metadata
            await self.storage.save_metadata(video_id, metadata)
            
            # Return the result
            return {
                "video_id": video_id,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "progress": metadata["upload_progress"]
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error uploading chunk: {str(e)}")
            raise UploadError(f"Failed to upload chunk: {str(e)}")

    async def finalize_upload(self, video_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Finalize a video upload by combining chunks.
        
        Args:
            video_id: ID of the video
            user_id: ID of the uploading user (for validation)
            
        Returns:
            Finalization result data
            
        Raises:
            VideoNotFoundError: If the video is not found
            UploadError: If there's an error finalizing the upload
        """
        try:
            # Get the video metadata
            metadata = await self.get_video_metadata(video_id)
            
            # Validate owner if user_id is provided
            if user_id and metadata["owner_id"] != user_id:
                raise UploadError("User does not have permission to finalize this upload")
            
            # Check if all chunks are received
            if metadata["chunks_received"] != metadata["total_chunks"]:
                missing = metadata["total_chunks"] - metadata["chunks_received"]
                raise UploadError(f"Cannot finalize upload: {missing} chunks are missing")
            
            # Combine chunks into a single file
            output_path = f"videos/{video_id}/{os.path.basename(metadata['filename'])}"
            await self.storage.combine_chunks(
                video_id, metadata["total_chunks"], output_path
            )
            
            # Update metadata
            metadata["status"] = "uploaded"
            metadata["output_path"] = output_path
            metadata["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated metadata
            await self.storage.save_metadata(video_id, metadata)
            
            # Return the result
            return {
                "video_id": video_id,
                "status": "uploaded",
                "output_path": output_path
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error finalizing upload: {str(e)}")
            raise UploadError(f"Failed to finalize upload: {str(e)}")

    async def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Get metadata for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Video metadata
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata from storage
            metadata = await self.storage.get_metadata(video_id)
            
            if not metadata:
                raise VideoNotFoundError(video_id)
                
            return metadata
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting video metadata: {str(e)}")
            raise VideoNotFoundError(video_id)

    async def get_upload_status(self, video_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Get the status of a video upload.
        
        Args:
            video_id: ID of the video
            user_id: ID of the user (for validation)
            
        Returns:
            Upload status data
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata
            metadata = await self.get_video_metadata(video_id)
            
            # Validate owner if user_id is provided
            if user_id and metadata["owner_id"] != user_id:
                raise VideoNotFoundError(video_id)
                
            # Return status information
            return {
                "video_id": video_id,
                "status": metadata["status"],
                "progress": metadata["upload_progress"],
                "chunks_received": metadata["chunks_received"],
                "total_chunks": metadata["total_chunks"]
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting upload status: {str(e)}")
            raise VideoNotFoundError(video_id)

    async def cancel_upload(self, video_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Cancel an ongoing upload or delete a processed video.
        
        Args:
            video_id: ID of the video
            user_id: ID of the user (for validation)
            
        Returns:
            Cancellation result data
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata
            metadata = await self.get_video_metadata(video_id)
            
            # Validate owner if user_id is provided
            if user_id and metadata["owner_id"] != user_id:
                raise VideoNotFoundError(video_id)
                
            # Delete video directory
            video_path = f"videos/{video_id}"
            await self.storage.delete_directory(video_path)
            
            # Delete metadata
            await self.storage.delete_metadata(video_id)
            
            # Return result
            return {
                "video_id": video_id,
                "status": "deleted"
            }
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error canceling upload: {str(e)}")
            raise StorageError("cancel_upload", f"Failed to cancel upload: {str(e)}")

    async def create_directory(self, path: str) -> None:
        """
        Create a directory in storage.
        
        Args:
            path: Directory path
            
        Raises:
            StorageError: If there's an error creating the directory
        """
        try:
            await self.storage.create_directory(path)
        
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            raise StorageError("create_directory", f"Failed to create directory: {str(e)}")

    async def get_hls_manifest_url(self, video_id: str) -> str:
        """
        Get the URL for an HLS master playlist.
        
        Args:
            video_id: ID of the video
            
        Returns:
            HLS manifest URL
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Get URL from storage
            return await self.storage.get_file_url(f"videos/{video_id}/hls/master.m3u8")
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting HLS manifest URL: {str(e)}")
            raise StorageError("get_hls_manifest_url", f"Failed to get HLS manifest URL: {str(e)}")

    async def get_dash_manifest_url(self, video_id: str) -> str:
        """
        Get the URL for a DASH MPD.
        
        Args:
            video_id: ID of the video
            
        Returns:
            DASH manifest URL
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Get URL from storage
            return await self.storage.get_file_url(f"videos/{video_id}/dash/manifest.mpd")
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting DASH manifest URL: {str(e)}")
            raise StorageError("get_dash_manifest_url", f"Failed to get DASH manifest URL: {str(e)}")

    async def list_videos(
        self, user_id: str = None, skip: int = 0, limit: int = 20, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        List videos with optional filtering.
        
        Args:
            user_id: Filter by user ID
            skip: Number of items to skip
            limit: Maximum number of items to return
            filters: Additional filters
            
        Returns:
            List of video metadata
            
        Raises:
            StorageError: If there's an error listing videos
        """
        try:
            # Build filter dict
            filter_dict = filters or {}
            
            # Add user filter if provided
            if user_id:
                filter_dict["owner_id"] = user_id
                
            # Get videos from storage
            videos = await self.storage.list_videos(filter_dict, skip, limit)
            
            return videos
        
        except Exception as e:
            logger.error(f"Error listing videos: {str(e)}")
            raise StorageError("list_videos", f"Failed to list videos: {str(e)}")

    async def get_thumbnail_path(self, video_id: str) -> str:
        """
        Get the path to a video thumbnail.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Path to the thumbnail file
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata to verify video exists
            metadata = await self.get_video_metadata(video_id)
            
            # Get thumbnail path
            thumbnail_path = f"videos/{video_id}/thumbnail.jpg"
            
            # Check if thumbnail exists
            if not await self.storage.file_exists(thumbnail_path):
                raise StorageError("get_thumbnail_path", "Thumbnail not found")
                
            return thumbnail_path
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting thumbnail path: {str(e)}")
            raise StorageError("get_thumbnail_path", f"Failed to get thumbnail path: {str(e)}")

    async def get_segment(self, video_id: str, segment_path: str) -> Tuple[BinaryIO, str]:
        """
        Get a video segment file.
        
        Args:
            video_id: ID of the video
            segment_path: Path to the segment relative to the video directory
            
        Returns:
            Tuple of (file content, content type)
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error getting the segment
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Get full path
            full_path = f"videos/{video_id}/{segment_path}"
            
            # Check if segment exists
            if not await self.storage.file_exists(full_path):
                raise StorageError("get_segment", "Segment not found")
                
            # Determine content type based on extension
            ext = os.path.splitext(segment_path)[1].lower()
            content_type = {
                ".ts": "video/mp2t",
                ".m4s": "video/mp4",
                ".mp4": "video/mp4",
                ".m3u8": "application/x-mpegURL",
                ".mpd": "application/dash+xml"
            }.get(ext, "application/octet-stream")
            
            # Get file content
            content = await self.storage.get_file(full_path)
            
            return (content, content_type)
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error getting segment: {str(e)}")
            raise StorageError("get_segment", f"Failed to get segment: {str(e)}")

    async def list_hls_variants(self, video_id: str) -> List[str]:
        """
        List HLS variant playlists for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            List of variant playlist paths
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # List files in HLS directory
            hls_path = f"videos/{video_id}/hls"
            files = await self.storage.list_files(hls_path)
            
            # Filter for m3u8 files that are not the master playlist
            variants = [
                f for f in files
                if f.endswith(".m3u8") and os.path.basename(f) != "master.m3u8"
            ]
            
            return variants
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error listing HLS variants: {str(e)}")
            raise StorageError("list_hls_variants", f"Failed to list HLS variants: {str(e)}")

    async def list_dash_adaptations(self, video_id: str) -> List[str]:
        """
        List DASH adaptation sets for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            List of adaptation set IDs
            
        Raises:
            VideoNotFoundError: If the video is not found
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # List directories in DASH directory
            dash_path = f"videos/{video_id}/dash"
            dirs = await self.storage.list_directories(dash_path)
            
            # Filter for adaptation set directories (e.g., "video_720p")
            adaptations = [os.path.basename(d) for d in dirs]
            
            return adaptations
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error listing DASH adaptations: {str(e)}")
            raise StorageError("list_dash_adaptations", f"Failed to list DASH adaptations: {str(e)}")

    async def save_hls_master_playlist(self, video_id: str, content: str) -> None:
        """
        Save an HLS master playlist.
        
        Args:
            video_id: ID of the video
            content: Playlist content
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error saving the playlist
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Save master playlist
            path = f"videos/{video_id}/hls/master.m3u8"
            await self.storage.save_file(path, content.encode('utf-8'))
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error saving HLS master playlist: {str(e)}")
            raise StorageError("save_hls_master_playlist", f"Failed to save HLS master playlist: {str(e)}")

    async def save_hls_variant_playlist(self, video_id: str, quality: str, content: str) -> None:
        """
        Save an HLS variant playlist.
        
        Args:
            video_id: ID of the video
            quality: Quality level (e.g., "720p")
            content: Playlist content
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error saving the playlist
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Save variant playlist
            path = f"videos/{video_id}/hls/{quality}.m3u8"
            await self.storage.save_file(path, content.encode('utf-8'))
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error saving HLS variant playlist: {str(e)}")
            raise StorageError("save_hls_variant_playlist", f"Failed to save HLS variant playlist: {str(e)}")

    async def save_dash_mpd(self, video_id: str, content: str) -> None:
        """
        Save a DASH MPD (Media Presentation Description).
        
        Args:
            video_id: ID of the video
            content: MPD content
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error saving the MPD
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Save MPD
            path = f"videos/{video_id}/dash/manifest.mpd"
            await self.storage.save_file(path, content.encode('utf-8'))
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error saving DASH MPD: {str(e)}")
            raise StorageError("save_dash_mpd", f"Failed to save DASH MPD: {str(e)}")

    async def save_dash_init_segment(self, video_id: str, quality: str, content: bytes) -> None:
        """
        Save a DASH initialization segment.
        
        Args:
            video_id: ID of the video
            quality: Quality level (e.g., "720p")
            content: Segment content
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error saving the segment
        """
        try:
            # Get metadata to verify video exists
            await self.get_video_metadata(video_id)
            
            # Save initialization segment
            path = f"videos/{video_id}/dash/video_{quality}/init.mp4"
            await self.storage.save_file(path, content)
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error saving DASH init segment: {str(e)}")
            raise StorageError("save_dash_init_segment", f"Failed to save DASH init segment: {str(e)}")

    async def delete_video(self, video_id: str, user_id: str = None) -> None:
        """
        Delete a video and all associated files.
        
        Args:
            video_id: ID of the video
            user_id: ID of the user (for validation)
            
        Raises:
            VideoNotFoundError: If the video is not found
            StorageError: If there's an error deleting the video
        """
        try:
            # Get metadata
            metadata = await self.get_video_metadata(video_id)
            
            # Validate owner if user_id is provided
            if user_id and metadata["owner_id"] != user_id:
                # Check if user has admin permission (would be implemented in Django client)
                # For now, just raise error
                raise VideoNotFoundError(video_id)
                
            # Delete video directory
            video_path = f"videos/{video_id}"
            await self.storage.delete_directory(video_path)
            
            # Delete metadata
            await self.storage.delete_metadata(video_id)
        
        except VideoNotFoundError:
            raise
        
        except Exception as e:
            logger.error(f"Error deleting video: {str(e)}")
            raise StorageError("delete_video", f"Failed to delete video: {str(e)}")

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the storage service.
        
        Returns:
            Health status information
        """
        try:
            # Check storage health
            health_info = await self.storage.check_health()
            
            return {
                "status": "ok",
                "provider": self.storage.__class__.__name__,
                "details": health_info
            }
        
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            return {
                "status": "error",
                "provider": self.storage.__class__.__name__,
                "details": str(e)
            }