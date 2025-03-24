"""
Video quality analyzer for the EINO Streaming Service.
"""

from typing import Dict, Any
import os
import asyncio
import json
import re

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError

settings = get_settings()


class QualityAnalyzer:
    """
    Service for analyzing video quality metrics.
    This service uses FFprobe to analyze video files.
    """

    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze a video file to determine its properties.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video properties including duration, resolution, bitrate, etc.
            
        Raises:
            VideoProcessingError: If there's an error analyzing the video
        """
        try:
            # Build FFprobe command
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
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
                    "analyze_video", 
                    f"FFprobe error: {stderr.decode()}"
                )
                
            # Parse JSON output
            probe_data = json.loads(stdout.decode())
            
            # Extract video and audio streams
            video_stream = None
            audio_stream = None
            
            for stream in probe_data["streams"]:
                if stream["codec_type"] == "video" and not video_stream:
                    video_stream = stream
                elif stream["codec_type"] == "audio" and not audio_stream:
                    audio_stream = stream
                    
            # Get video properties
            format_info = probe_data["format"]
            duration = float(format_info["duration"])
            size = int(format_info["size"])
            bitrate = int(format_info.get("bit_rate", 0))
            
            # If bitrate is not available in format, try to calculate it
            if bitrate == 0 and duration > 0:
                bitrate = int((size * 8) / duration)
                
            # Get video dimensions
            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            
            # Get video codec
            video_codec = video_stream.get("codec_name", "unknown")
            
            # Get audio codec
            audio_codec = None
            if audio_stream:
                audio_codec = audio_stream.get("codec_name", "unknown")
                
            # Get video format
            format_name = format_info.get("format_name", "unknown")
            format_long_name = format_info.get("format_long_name", "unknown")
            
            # Determine container format
            container = self._get_container_format(format_name, os.path.basename(video_path))
            
            # Check for common video issues
            issues = await self._check_video_issues(video_path)
            
            # Return video information
            return {
                "duration": duration,
                "width": width,
                "height": height,
                "bitrate": bitrate,
                "size": size,
                "video_codec": video_codec,
                "audio_codec": audio_codec,
                "format": container,
                "format_name": format_name,
                "format_long_name": format_long_name,
                "issues": issues
            }
        
        except Exception as e:
            logger.error(f"Error analyzing video: {str(e)}")
            raise VideoProcessingError("analyze_video", f"Failed to analyze video: {str(e)}")

    async def _check_video_issues(self, video_path: str) -> Dict[str, Any]:
        """
        Check for common video issues.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary of identified issues
            
        Raises:
            VideoProcessingError: If there's an error checking for issues
        """
        try:
            issues = {}
            
            # Check for audio issues (silent or low volume)
            audio_issues = await self._check_audio_issues(video_path)
            if audio_issues:
                issues["audio"] = audio_issues
                
            # Check for video issues (low quality, odd resolution, etc.)
            video_issues = await self._check_video_quality_issues(video_path)
            if video_issues:
                issues["video"] = video_issues
                
            return issues
        
        except Exception as e:
            logger.error(f"Error checking video issues: {str(e)}")
            # Don't raise an exception, just return empty issues
            return {}

    async def _check_audio_issues(self, video_path: str) -> Dict[str, Any]:
        """
        Check for audio issues in a video.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary of audio issues
            
        Raises:
            VideoProcessingError: If there's an error checking for audio issues
        """
        try:
            # Build FFprobe command for audio volume detection
            cmd = [
                "ffprobe",
                "-v", "error",
                "-f", "lavfi",
                "-i", f"movie={video_path},volumedetect",
                "-show_entries", "frame_tags=lavfi.volumedetect.max_volume",
                "-of", "json"
            ]
            
            # Run FFprobe command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {}  # Skip audio check if it fails
                
            # Parse output
            try:
                volume_info = json.loads(stdout.decode())
                max_volume = None
                
                # Extract max volume from the frame tags
                if "frames" in volume_info and volume_info["frames"]:
                    for frame in volume_info["frames"]:
                        if "tags" in frame and "lavfi.volumedetect.max_volume" in frame["tags"]:
                            max_volume = float(frame["tags"]["lavfi.volumedetect.max_volume"])
                            break
                
                if max_volume is not None:
                    issues = {}
                    
                    # Check for silent audio
                    if max_volume <= -90:
                        issues["silent"] = True
                        
                    # Check for low volume
                    elif max_volume < -20:
                        issues["low_volume"] = True
                        issues["max_volume"] = max_volume
                        
                    return issues
                    
            except (json.JSONDecodeError, ValueError):
                # Skip audio check if parsing fails
                pass
                
            return {}
        
        except Exception as e:
            logger.error(f"Error checking audio issues: {str(e)}")
            return {}

    async def _check_video_quality_issues(self, video_path: str) -> Dict[str, Any]:
        """
        Check for video quality issues.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary of video quality issues
            
        Raises:
            VideoProcessingError: If there's an error checking for video issues
        """
        try:
            # Build FFprobe command for video quality analysis
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate,codec_name,bit_rate",
                "-of", "json",
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
                return {}  # Skip video check if it fails
                
            # Parse output
            try:
                quality_info = json.loads(stdout.decode())
                
                if "streams" in quality_info and quality_info["streams"]:
                    stream = quality_info["streams"][0]
                    issues = {}
                    
                    # Check for low resolution
                    width = stream.get("width", 0)
                    height = stream.get("height", 0)
                    
                    if width < 480 or height < 360:
                        issues["low_resolution"] = True
                        
                    # Check for odd resolution
                    if width % 2 != 0 or height % 2 != 0:
                        issues["odd_resolution"] = True
                        
                    # Check for low bitrate
                    bitrate = stream.get("bit_rate")
                    if bitrate and int(bitrate) < 500000:  # Less than 500 kbps
                        issues["low_bitrate"] = True
                        
                    # Check for low frame rate
                    frame_rate = stream.get("avg_frame_rate", "0/1")
                    try:
                        if "/" in frame_rate:
                            num, den = map(int, frame_rate.split("/"))
                            if den > 0:
                                fps = num / den
                                if fps < 24:
                                    issues["low_frame_rate"] = True
                    except ValueError:
                        pass
                        
                    return issues
                    
            except (json.JSONDecodeError, ValueError):
                # Skip video check if parsing fails
                pass
                
            return {}
        
        except Exception as e:
            logger.error(f"Error checking video quality issues: {str(e)}")
            return {}

    def _get_container_format(self, format_name: str, filename: str) -> str:
        """
        Determine the container format of a video file.
        
        Args:
            format_name: Format name from FFprobe
            filename: Video filename
            
        Returns:
            Container format name
        """
        # Check format name
        if "mp4" in format_name:
            return "mp4"
        elif "webm" in format_name:
            return "webm"
        elif "matroska" in format_name:
            return "mkv"
        elif "avi" in format_name:
            return "avi"
        elif "mov" in format_name or "quicktime" in format_name:
            return "mov"
        elif "flv" in format_name:
            return "flv"
        elif "mpegts" in format_name:
            return "ts"
        elif "mpeg" in format_name:
            return "mpeg"
            
        # Check file extension
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext in settings.ALLOWED_VIDEO_FORMATS:
            return ext
            
        # Default to generic
        return "video"