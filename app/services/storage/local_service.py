"""
Local filesystem implementation for the EINO Streaming Service.
Used primarily for development and testing.
"""

from typing import Dict, Any, List, BinaryIO, Optional
import os
import json
import io
import shutil
from pathlib import Path
import aiofiles
import aiofiles.os

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError, StorageError

settings = get_settings()


class LocalService:
    """
    Local filesystem implementation for storage operations.
    This service provides methods for file storage and retrieval using the local filesystem.
    """

    def __init__(self):
        """Initialize the local service with base directory."""
        self.base_dir = Path("storage")
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.metadata_dir = self.base_dir / "metadata"
        
        # Create directories if they don't exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

    async def save_metadata(self, video_id: str, metadata: Dict[str, Any]) -> None:
        """
        Save video metadata to the local filesystem.
        
        Args:
            video_id: ID of the video
            metadata: Metadata to save
            
        Raises:
            StorageError: If there's an error saving the metadata
        """
        try:
            # Convert metadata to JSON
            metadata_json = json.dumps(metadata, indent=2)
            
            # Create metadata path
            metadata_path = self.metadata_dir / f"{video_id}.json"
            
            # Save metadata to file
            async with aiofiles.open(metadata_path, "w") as f:
                await f.write(metadata_json)
        
        except Exception as e:
            logger.error(f"Error saving metadata to local filesystem: {str(e)}")
            raise StorageError("save_metadata", f"Failed to save metadata: {str(e)}")

    async def get_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata from the local filesystem.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Video metadata or None if not found
            
        Raises:
            StorageError: If there's an error getting the metadata
        """
        try:
            # Create metadata path
            metadata_path = self.metadata_dir / f"{video_id}.json"
            
            # Check if metadata file exists
            if not os.path.exists(metadata_path):
                return None
                
            # Read metadata from file
            async with aiofiles.open(metadata_path, "r") as f:
                metadata_json = await f.read()
                
            # Parse JSON
            metadata = json.loads(metadata_json)
            
            return metadata
        
        except FileNotFoundError:
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing metadata JSON: {str(e)}")
            raise StorageError("get_metadata", f"Failed to parse metadata JSON: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error getting metadata from local filesystem: {str(e)}")
            raise StorageError("get_metadata", f"Failed to get metadata: {str(e)}")

    async def delete_metadata(self, video_id: str) -> None:
        """
        Delete video metadata from the local filesystem.
        
        Args:
            video_id: ID of the video
            
        Raises:
            StorageError: If there's an error deleting the metadata
        """
        try:
            # Create metadata path
            metadata_path = self.metadata_dir / f"{video_id}.json"
            
            # Check if metadata file exists
            if not os.path.exists(metadata_path):
                return
                
            # Delete metadata file
            os.remove(metadata_path)
        
        except FileNotFoundError:
            # If metadata doesn't exist, consider it a success
            pass
        
        except Exception as e:
            logger.error(f"Error deleting metadata from local filesystem: {str(e)}")
            raise StorageError("delete_metadata", f"Failed to delete metadata: {str(e)}")

    async def save_file(self, path: str, content: bytes) -> None:
        """
        Save a file to the local filesystem.
        
        Args:
            path: Path to the file relative to the base directory
            content: File content as bytes
            
        Raises:
            StorageError: If there's an error saving the file
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save file
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(content)
        
        except Exception as e:
            logger.error(f"Error saving file to local filesystem: {str(e)}")
            raise StorageError("save_file", f"Failed to save file: {str(e)}")

    async def get_file(self, path: str) -> BinaryIO:
        """
        Get a file from the local filesystem.
        
        Args:
            path: Path to the file relative to the base directory
            
        Returns:
            File content as a binary stream
            
        Raises:
            StorageError: If there's an error getting the file
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if file exists
            if not os.path.exists(full_path):
                raise StorageError("get_file", f"File not found: {path}")
                
            # Read file to memory
            async with aiofiles.open(full_path, "rb") as f:
                content = await f.read()
                
            # Return as binary stream
            return io.BytesIO(content)
        
        except FileNotFoundError:
            raise StorageError("get_file", f"File not found: {path}")
        
        except Exception as e:
            logger.error(f"Error getting file from local filesystem: {str(e)}")
            raise StorageError("get_file", f"Failed to get file: {str(e)}")

    async def delete_file(self, path: str) -> None:
        """
        Delete a file from the local filesystem.
        
        Args:
            path: Path to the file relative to the base directory
            
        Raises:
            StorageError: If there's an error deleting the file
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if file exists
            if not os.path.exists(full_path):
                return
                
            # Delete file
            os.remove(full_path)
        
        except FileNotFoundError:
            # If file doesn't exist, consider it a success
            pass
        
        except Exception as e:
            logger.error(f"Error deleting file from local filesystem: {str(e)}")
            raise StorageError("delete_file", f"Failed to delete file: {str(e)}")

    async def create_directory(self, path: str) -> None:
        """
        Create a directory in the local filesystem.
        
        Args:
            path: Directory path relative to the base directory
            
        Raises:
            StorageError: If there's an error creating the directory
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Create directory
            os.makedirs(full_path, exist_ok=True)
        
        except Exception as e:
            logger.error(f"Error creating directory in local filesystem: {str(e)}")
            raise StorageError("create_directory", f"Failed to create directory: {str(e)}")

    async def delete_directory(self, path: str) -> None:
        """
        Delete a directory and all its contents from the local filesystem.
        
        Args:
            path: Directory path relative to the base directory
            
        Raises:
            StorageError: If there's an error deleting the directory
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if directory exists
            if not os.path.exists(full_path):
                return
                
            # Delete directory and all contents
            shutil.rmtree(full_path)
        
        except FileNotFoundError:
            # If directory doesn't exist, consider it a success
            pass
        
        except Exception as e:
            logger.error(f"Error deleting directory from local filesystem: {str(e)}")
            raise StorageError("delete_directory", f"Failed to delete directory: {str(e)}")

    async def list_files(self, path: str) -> List[str]:
        """
        List files in a directory.
        
        Args:
            path: Directory path relative to the base directory
            
        Returns:
            List of file paths relative to the base directory
            
        Raises:
            StorageError: If there's an error listing files
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if directory exists
            if not os.path.exists(full_path) or not os.path.isdir(full_path):
                return []
                
            # List files in directory
            files = []
            
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                
                # Skip directories
                if os.path.isdir(entry_path):
                    continue
                    
                # Add file path
                files.append(os.path.join(path, entry))
            
            return files
        
        except Exception as e:
            logger.error(f"Error listing files from local filesystem: {str(e)}")
            raise StorageError("list_files", f"Failed to list files: {str(e)}")

    async def list_directories(self, path: str) -> List[str]:
        """
        List subdirectories in a directory.
        
        Args:
            path: Directory path relative to the base directory
            
        Returns:
            List of directory paths relative to the base directory
            
        Raises:
            StorageError: If there's an error listing directories
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if directory exists
            if not os.path.exists(full_path) or not os.path.isdir(full_path):
                return []
                
            # List directories
            dirs = []
            
            for entry in os.listdir(full_path):
                entry_path = os.path.join(full_path, entry)
                
                # Skip files
                if not os.path.isdir(entry_path):
                    continue
                    
                # Add directory path
                dirs.append(os.path.join(path, entry))
            
            return dirs
        
        except Exception as e:
            logger.error(f"Error listing directories from local filesystem: {str(e)}")
            raise StorageError("list_directories", f"Failed to list directories: {str(e)}")

    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in the local filesystem.
        
        Args:
            path: Path to the file relative to the base directory
            
        Returns:
            True if the file exists, False otherwise
            
        Raises:
            StorageError: If there's an error checking if the file exists
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
            else:
                base_path = self.raw_dir
                
            # Create full path
            full_path = base_path / path
            
            # Check if file exists
            return os.path.exists(full_path) and os.path.isfile(full_path)
        
        except Exception as e:
            logger.error(f"Error checking if file exists in local filesystem: {str(e)}")
            raise StorageError("file_exists", f"Failed to check if file exists: {str(e)}")

    async def get_file_url(self, path: str, expiration: int = 3600) -> str:
        """
        Get a URL for a file in the local filesystem.
        For local development, this is just a relative URL to the file.
        
        Args:
            path: Path to the file relative to the base directory
            expiration: URL expiration time in seconds (ignored for local filesystem)
            
        Returns:
            URL to the file
            
        Raises:
            StorageError: If there's an error getting the URL
        """
        try:
            # Determine which base directory to use
            if path.startswith("videos/") and "/processed/" in path:
                base_path = self.processed_dir
                url_prefix = "/processed"
            else:
                base_path = self.raw_dir
                url_prefix = "/raw"
                
            # Create full path
            full_path = base_path / path
            
            # Check if file exists
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                raise StorageError("get_file_url", f"File not found: {path}")
                
            # Generate URL
            url = f"{url_prefix}/{path}"
            
            return url
        
        except Exception as e:
            logger.error(f"Error getting file URL from local filesystem: {str(e)}")
            raise StorageError("get_file_url", f"Failed to get file URL: {str(e)}")

    async def combine_chunks(self, video_id: str, total_chunks: int, output_path: str) -> None:
        """
        Combine video chunks into a single file in the local filesystem.
        
        Args:
            video_id: ID of the video
            total_chunks: Total number of chunks
            output_path: Path to the output file relative to the base directory
            
        Raises:
            StorageError: If there's an error combining chunks
        """
        try:
            # Create output path
            full_output_path = self.raw_dir / output_path
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(full_output_path), exist_ok=True)
            
            # Open output file
            with open(full_output_path, "wb") as output_file:
                # Combine chunks
                for i in range(total_chunks):
                    chunk_path = self.raw_dir / f"videos/{video_id}/chunks/chunk_{i}"
                    
                    # Check if chunk exists
                    if not os.path.exists(chunk_path):
                        raise StorageError("combine_chunks", f"Chunk {i} not found")
                        
                    # Read chunk and write to output file
                    with open(chunk_path, "rb") as chunk_file:
                        output_file.write(chunk_file.read())
        
        except Exception as e:
            logger.error(f"Error combining chunks in local filesystem: {str(e)}")
            raise StorageError("combine_chunks", f"Failed to combine chunks: {str(e)}")

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
            # List all metadata files
            videos = []
            
            for filename in os.listdir(self.metadata_dir):
                # Skip non-JSON files
                if not filename.endswith(".json"):
                    continue
                    
                try:
                    # Read metadata file
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    
                    async with aiofiles.open(metadata_path, "r") as f:
                        metadata_json = await f.read()
                        
                    # Parse JSON
                    metadata = json.loads(metadata_json)
                    
                    # Apply filters
                    if self._matches_filters(metadata, filters):
                        videos.append(metadata)
                
                except Exception as e:
                    logger.error(f"Error parsing metadata file {filename}: {str(e)}")
                    continue
            
            # Sort by creation date (newest first)
            videos.sort(key=lambda v: v.get("created_at", ""), reverse=True)
            
            # Apply pagination
            paginated_videos = videos[skip:skip + limit]
            
            return paginated_videos
        
        except Exception as e:
            logger.error(f"Error listing videos from local filesystem: {str(e)}")
            raise StorageError("list_videos", f"Failed to list videos: {str(e)}")

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
        Check the health of the local storage service.
        
        Returns:
            Health information
            
        Raises:
            Exception: If the health check fails
        """
        try:
            # Check if directories exist
            raw_exists = os.path.exists(self.raw_dir) and os.path.isdir(self.raw_dir)
            processed_exists = os.path.exists(self.processed_dir) and os.path.isdir(self.processed_dir)
            metadata_exists = os.path.exists(self.metadata_dir) and os.path.isdir(self.metadata_dir)
            
            # Check if directories are writable
            raw_writable = os.access(self.raw_dir, os.W_OK)
            processed_writable = os.access(self.processed_dir, os.W_OK)
            metadata_writable = os.access(self.metadata_dir, os.W_OK)
            
            return {
                "raw_directory": {
                    "path": str(self.raw_dir),
                    "exists": raw_exists,
                    "writable": raw_writable
                },
                "processed_directory": {
                    "path": str(self.processed_dir),
                    "exists": processed_exists,
                    "writable": processed_writable
                },
                "metadata_directory": {
                    "path": str(self.metadata_dir),
                    "exists": metadata_exists,
                    "writable": metadata_writable
                }
            }
        
        except Exception as e:
            logger.error(f"Local storage health check failed: {str(e)}")
            raise Exception(f"Local storage health check failed: {str(e)}")