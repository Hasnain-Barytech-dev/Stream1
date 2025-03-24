"""
Google Cloud Storage (GCS) implementation for the EINO Streaming Service.
"""

from typing import Dict, Any, List, BinaryIO, Optional
import os
import json
import io
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError, StorageError

settings = get_settings()


class GCSService:
    """
    Google Cloud Storage implementation for storage operations.
    This service provides methods for file storage and retrieval using GCS.
    """

    def __init__(self):
        """Initialize the GCS service with project settings."""
        # Load GCP credentials from service account JSON
        self.credentials = service_account.Credentials.from_service_account_info(
            info=settings.GCP_SERVICE_ACCOUNT_INFO
        )
        
        # Create storage client with credentials
        self.client = storage.Client(
            project=settings.GCP_PROJECT_ID,
            credentials=self.credentials
        )
        
        # Initialize buckets - create them if they don't exist
        self.raw_bucket = self._get_or_create_bucket(settings.RAW_VIDEOS_BUCKET)
        self.processed_bucket = self._get_or_create_bucket(settings.PROCESSED_VIDEOS_BUCKET)
        self.metadata_prefix = "metadata/"

    def _get_or_create_bucket(self, bucket_name: str) -> storage.Bucket:
        """
        Get a bucket or create it if it doesn't exist.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Bucket object
        """
        try:
            bucket = self.client.get_bucket(bucket_name)
            logger.info(f"Using existing bucket: {bucket_name}")
            return bucket
        except NotFound:
            logger.info(f"Creating new bucket: {bucket_name}")
            bucket = self.client.create_bucket(bucket_name, location=settings.GCP_REGION)
            return bucket

    async def save_metadata(self, video_id: str, metadata: Dict[str, Any]) -> None:
        """
        Save video metadata to GCS.
        
        Args:
            video_id: ID of the video
            metadata: Metadata to save
            
        Raises:
            StorageError: If there's an error saving the metadata
        """
        try:
            # Convert metadata to JSON
            metadata_json = json.dumps(metadata)
            
            # Create blob
            blob = self.raw_bucket.blob(f"{self.metadata_prefix}{video_id}.json")
            
            # Upload metadata
            blob.upload_from_string(metadata_json, content_type="application/json")
        
        except Exception as e:
            logger.error(f"Error saving metadata to GCS: {str(e)}")
            raise StorageError("save_metadata", f"Failed to save metadata to GCS: {str(e)}")

    async def get_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata from GCS.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Video metadata or None if not found
            
        Raises:
            StorageError: If there's an error getting the metadata
        """
        try:
            # Create blob
            blob = self.raw_bucket.blob(f"{self.metadata_prefix}{video_id}.json")
            
            # Check if blob exists
            if not blob.exists():
                return None
                
            # Download metadata
            metadata_json = blob.download_as_text()
            
            # Parse JSON
            metadata = json.loads(metadata_json)
            
            return metadata
        
        except NotFound:
            return None
        
        except Exception as e:
            logger.error(f"Error getting metadata from GCS: {str(e)}")
            raise StorageError("get_metadata", f"Failed to get metadata from GCS: {str(e)}")

    async def delete_metadata(self, video_id: str) -> None:
        """
        Delete video metadata from GCS.
        
        Args:
            video_id: ID of the video
            
        Raises:
            StorageError: If there's an error deleting the metadata
        """
        try:
            # Create blob
            blob = self.raw_bucket.blob(f"{self.metadata_prefix}{video_id}.json")
            
            # Delete blob
            blob.delete()
        
        except NotFound:
            # If metadata doesn't exist, consider it a success
            pass
        
        except Exception as e:
            logger.error(f"Error deleting metadata from GCS: {str(e)}")
            raise StorageError("delete_metadata", f"Failed to delete metadata from GCS: {str(e)}")

    async def save_file(self, path: str, content: bytes) -> None:
        """
        Save a file to GCS.
        
        Args:
            path: Path to the file
            content: File content as bytes
            
        Raises:
            StorageError: If there's an error saving the file
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Create blob
            blob = bucket.blob(path)
            
            # Determine content type based on extension
            ext = os.path.splitext(path)[1].lower()
            content_type = {
                ".ts": "video/mp2t",
                ".m4s": "video/mp4",
                ".mp4": "video/mp4",
                ".m3u8": "application/vnd.apple.mpegurl",
                ".mpd": "application/dash+xml",
                ".jpg": "image/jpeg",
                ".png": "image/png",
                ".json": "application/json",
                ".txt": "text/plain"
            }.get(ext, "application/octet-stream")
            
            # Upload file
            blob.upload_from_string(content, content_type=content_type)
        
        except Exception as e:
            logger.error(f"Error saving file to GCS: {str(e)}")
            raise StorageError("save_file", f"Failed to save file to GCS: {str(e)}")

    async def get_file(self, path: str) -> BinaryIO:
        """
        Get a file from GCS.
        
        Args:
            path: Path to the file
            
        Returns:
            File content as a binary stream
            
        Raises:
            StorageError: If there's an error getting the file
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Create blob
            blob = bucket.blob(path)
            
            # Check if blob exists
            if not blob.exists():
                raise StorageError("get_file", f"File not found: {path}")
                
            # Download file to memory
            file_stream = io.BytesIO()
            blob.download_to_file(file_stream)
            file_stream.seek(0)
            
            return file_stream
        
        except NotFound:
            raise StorageError("get_file", f"File not found: {path}")
        
        except Exception as e:
            logger.error(f"Error getting file from GCS: {str(e)}")
            raise StorageError("get_file", f"Failed to get file from GCS: {str(e)}")

    async def delete_file(self, path: str) -> None:
        """
        Delete a file from GCS.
        
        Args:
            path: Path to the file
            
        Raises:
            StorageError: If there's an error deleting the file
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Create blob
            blob = bucket.blob(path)
            
            # Delete blob
            blob.delete()
        
        except NotFound:
            # If file doesn't exist, consider it a success
            pass
        
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {str(e)}")
            raise StorageError("delete_file", f"Failed to delete file from GCS: {str(e)}")

    async def create_directory(self, path: str) -> None:
        """
        Create a directory in GCS (no-op since GCS doesn't have real directories).
        
        Args:
            path: Directory path
        """
        # GCS doesn't have real directories, so this is a no-op
        pass

    async def delete_directory(self, path: str) -> None:
        """
        Delete a directory and all its contents from GCS.
        
        Args:
            path: Directory path
            
        Raises:
            StorageError: If there's an error deleting the directory
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # List all blobs with the prefix
            blobs = bucket.list_blobs(prefix=path)
            
            # Delete all blobs
            for blob in blobs:
                blob.delete()
        
        except Exception as e:
            logger.error(f"Error deleting directory from GCS: {str(e)}")
            raise StorageError("delete_directory", f"Failed to delete directory from GCS: {str(e)}")

    async def list_files(self, path: str) -> List[str]:
        """
        List files in a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of file paths
            
        Raises:
            StorageError: If there's an error listing files
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Ensure path ends with a slash
            if not path.endswith("/"):
                path += "/"
                
            # List all blobs with the prefix
            blobs = bucket.list_blobs(prefix=path)
            
            # Get file paths
            files = []
            
            for blob in blobs:
                # Skip "directories" (blobs that end with a slash)
                if blob.name.endswith("/"):
                    continue
                    
                # Skip if the blob is in a subdirectory
                if "/" in blob.name[len(path):]:
                    continue
                    
                files.append(blob.name)
            
            return files
        
        except Exception as e:
            logger.error(f"Error listing files from GCS: {str(e)}")
            raise StorageError("list_files", f"Failed to list files from GCS: {str(e)}")

    async def list_directories(self, path: str) -> List[str]:
        """
        List subdirectories in a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of directory paths
            
        Raises:
            StorageError: If there's an error listing directories
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Ensure path ends with a slash
            if not path.endswith("/"):
                path += "/"
                
            # List all blobs with the prefix
            blobs = bucket.list_blobs(prefix=path, delimiter="/")
            
            # Get directory paths
            dirs = [prefix for prefix in blobs.prefixes]
            
            return dirs
        
        except Exception as e:
            logger.error(f"Error listing directories from GCS: {str(e)}")
            raise StorageError("list_directories", f"Failed to list directories from GCS: {str(e)}")

    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: Path to the file
            
        Returns:
            True if the file exists, False otherwise
            
        Raises:
            StorageError: If there's an error checking if the file exists
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Create blob
            blob = bucket.blob(path)
            
            # Check if blob exists
            return blob.exists()
        
        except Exception as e:
            logger.error(f"Error checking if file exists in GCS: {str(e)}")
            raise StorageError("file_exists", f"Failed to check if file exists in GCS: {str(e)}")

    async def get_file_url(self, path: str, expiration: int = 3600) -> str:
        """
        Get a signed URL for a file.
        
        Args:
            path: Path to the file
            expiration: URL expiration time in seconds
            
        Returns:
            Signed URL
            
        Raises:
            StorageError: If there's an error getting the URL
        """
        try:
            # Determine which bucket to use based on path
            if path.startswith("videos/") and "/processed/" in path:
                bucket = self.processed_bucket
            else:
                bucket = self.raw_bucket
                
            # Create blob
            blob = bucket.blob(path)
            
            # Check if blob exists
            if not blob.exists():
                raise StorageError("get_file_url", f"File not found: {path}")
                
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET"
            )
            
            return url
        
        except NotFound:
            raise StorageError("get_file_url", f"File not found: {path}")
        
        except Exception as e:
            logger.error(f"Error getting file URL from GCS: {str(e)}")
            raise StorageError("get_file_url", f"Failed to get file URL from GCS: {str(e)}")

    async def combine_chunks(self, video_id: str, total_chunks: int, output_path: str) -> None:
        """
        Combine video chunks into a single file.
        
        Args:
            video_id: ID of the video
            total_chunks: Total number of chunks
            output_path: Path to the output file
            
        Raises:
            StorageError: If there's an error combining chunks
        """
        try:
            # Create output blob
            output_blob = self.raw_bucket.blob(output_path)
            
            # Create a compositor
            composer = storage.Composer(self.client)
            
            # Prepare chunk blobs
            chunk_blobs = []
            
            for i in range(total_chunks):
                chunk_path = f"videos/{video_id}/chunks/chunk_{i}"
                chunk_blob = self.raw_bucket.blob(chunk_path)
                
                # Check if chunk exists
                if not chunk_blob.exists():
                    raise StorageError("combine_chunks", f"Chunk {i} not found")
                    
                chunk_blobs.append(chunk_blob)
            
            # Combine chunks
            composer.compose(chunk_blobs, output_blob)
        
        except Exception as e:
            logger.error(f"Error combining chunks in GCS: {str(e)}")
            raise StorageError("combine_chunks", f"Failed to combine chunks in GCS: {str(e)}")

    async def list_videos(
        self, filters: Dict[str, Any], skip: int, limit: int
    ) -> List[Dict[str, Any]]:
        """
        List videos with filtering, sorting, and pagination.
        
        Args:
            filters: Filter criteria
            skip: Number of items to skip
            limit: Maximum number of items to return
            
        Returns:
            List of video metadata
            
        Raises:
            StorageError: If there's an error listing videos
        """
        try:
            # List all metadata blobs
            blobs = self.raw_bucket.list_blobs(prefix=self.metadata_prefix)
            
            # Get metadata for each video
            videos = []
            
            for blob in blobs:
                try:
                    # Download metadata
                    metadata_json = blob.download_as_text()
                    
                    # Parse JSON
                    metadata = json.loads(metadata_json)
                    
                    # Apply filters
                    if self._matches_filters(metadata, filters):
                        videos.append(metadata)
                
                except Exception as e:
                    logger.error(f"Error parsing metadata for blob {blob.name}: {str(e)}")
                    continue
            
            # Sort by creation date (newest first)
            videos.sort(key=lambda v: v.get("created_at", ""), reverse=True)
            
            # Apply pagination
            paginated_videos = videos[skip:skip + limit]
            
            return paginated_videos
        
        except Exception as e:
            logger.error(f"Error listing videos from GCS: {str(e)}")
            raise StorageError("list_videos", f"Failed to list videos from GCS: {str(e)}")

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if metadata matches the filter criteria.
        
        Args:
            metadata: Video metadata
            filters: Filter criteria
            
        Returns:
            True if the metadata matches the filters, False otherwise
        """
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
                
        return True

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the GCS service.
        
        Returns:
            Health information
            
        Raises:
            Exception: If the health check fails
        """
        try:
            # Try to list buckets to check connectivity
            buckets = list(self.client.list_buckets(max_results=1))
            
            # Check if raw bucket exists
            raw_exists = self.raw_bucket.exists()
            
            # Check if processed bucket exists
            processed_exists = self.processed_bucket.exists()
            
            return {
                "connection": "ok",
                "raw_bucket": {
                    "name": settings.RAW_VIDEOS_BUCKET,
                    "exists": raw_exists
                },
                "processed_bucket": {
                    "name": settings.PROCESSED_VIDEOS_BUCKET,
                    "exists": processed_exists
                }
            }
        
        except Exception as e:
            logger.error(f"GCS health check failed: {str(e)}")
            raise Exception(f"GCS health check failed: {str(e)}")