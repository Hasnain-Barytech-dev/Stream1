"""
Thumbnail generator for the EINO Streaming Service.
"""

from typing import Dict, Any, List
import os
import asyncio
import subprocess
import tempfile
import math

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError

settings = get_settings()


class ThumbnailGenerator:
    """
    Service for generating video thumbnails.
    This service uses FFmpeg to extract frames from videos.
    """

    async def generate_thumbnails(
        self, video_path: str, output_dir: str, count: int = 3
    ) -> List[str]:
        """
        Generate thumbnails from a video.
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save thumbnails
            count: Number of thumbnails to generate
            
        Returns:
            List of thumbnail file paths
            
        Raises:
            VideoProcessingError: If there's an error generating thumbnails
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Get video duration
            duration = await self._get_video_duration(video_path)
            
            # Calculate thumbnail positions
            positions = []
            
            if count == 1:
                # Single thumbnail at 25% of the duration
                positions.append(duration * 0.25)
            else:
                # Multiple thumbnails evenly distributed
                for i in range(count):
                    # Skip the first and last 10% of the video
                    position = duration * (0.1 + 0.8 * i / (count - 1))
                    positions.append(position)
                    
            # Generate thumbnails
            thumbnail_paths = []
            
            for i, position in enumerate(positions):
                output_path = os.path.join(output_dir, f"thumbnail_{i}.jpg")
                
                await self._extract_frame(video_path, output_path, position)
                
                thumbnail_paths.append(output_path)
                
            return thumbnail_paths
        
        except Exception as e:
            logger.error(f"Error generating thumbnails: {str(e)}")
            raise VideoProcessingError("generate_thumbnails", f"Failed to generate thumbnails: {str(e)}")

    async def generate_animated_thumbnail(
        self, video_path: str, output_path: str, duration: int = 3
    ) -> str:
        """
        Generate an animated GIF thumbnail from a video.
        
        Args:
            video_path: Path to the video file
            output_path: Path to save the animated thumbnail
            duration: Duration of the animation in seconds
            
        Returns:
            Path to the generated thumbnail
            
        Raises:
            VideoProcessingError: If there's an error generating the thumbnail
        """
        try:
            # Get video duration
            video_duration = await self._get_video_duration(video_path)
            
            # Calculate start position (25% of the video)
            start_position = video_duration * 0.25
            
            # Ensure start position + duration doesn't exceed video length
            if start_position + duration > video_duration:
                start_position = max(0, video_duration - duration)
                
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-ss", str(start_position),
                "-t", str(duration),
                "-i", video_path,
                "-vf", "fps=10,scale=320:-1:flags=lanczos",
                "-y",  # Overwrite existing file
                output_path
            ]
            
            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessingError(
                    "generate_animated_thumbnail", 
                    f"FFmpeg error: {stderr.decode()}"
                )
                
            return output_path
        
        except Exception as e:
            logger.error(f"Error generating animated thumbnail: {str(e)}")
            raise VideoProcessingError("generate_animated_thumbnail", f"Failed to generate animated thumbnail: {str(e)}")

    async def _get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of a video.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video duration in seconds
            
        Raises:
            VideoProcessingError: If there's an error getting the duration
        """
        try:
            # Build FFprobe command
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            # Run FFprobe command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessingError(
                    "get_video_duration", 
                    f"FFprobe error: {stderr.decode()}"
                )
                
            # Parse duration
            duration = float(stdout.decode().strip())
            
            return duration
        
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            raise VideoProcessingError("get_video_duration", f"Failed to get video duration: {str(e)}")

    async def _extract_frame(self, video_path: str, output_path: str, position: float) -> None:
        """
        Extract a frame from a video.
        
        Args:
            video_path: Path to the video file
            output_path: Path to save the extracted frame
            position: Position in seconds
            
        Raises:
            VideoProcessingError: If there's an error extracting the frame
        """
        try:
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-ss", str(position),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",  # High quality
                "-y",  # Overwrite existing file
                output_path
            ]
            
            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessingError(
                    "extract_frame", 
                    f"FFmpeg error: {stderr.decode()}"
                )
        
        except Exception as e:
            logger.error(f"Error extracting frame: {str(e)}")
            raise VideoProcessingError("extract_frame", f"Failed to extract frame: {str(e)}")