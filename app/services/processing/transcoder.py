"""
Video transcoding service for the EINO Streaming Service.
"""

from typing import Dict, Any, List, Optional
import os
import asyncio
import subprocess
import tempfile
import shutil
import math
from pathlib import Path

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError
from app.services.storage.storage_service import StorageService

settings = get_settings()


class Transcoder:
    """
    Service for transcoding videos to different formats and qualities.
    This service uses FFmpeg to transcode videos for streaming.
    """

    def __init__(self):
        """Initialize the transcoder with storage service."""
        self.storage_service = StorageService()

    async def transcode_video_for_streaming(
        self, input_path: str, variants: List[Dict[str, Any]], video_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transcode a video for adaptive streaming.
        
        Args:
            input_path: Path to the input video file
            variants: List of variant configurations
            video_info: Video information from the analyzer
            
        Returns:
            Information about the generated segments
            
        Raises:
            VideoProcessingError: If there's an error transcoding the video
        """
        try:
            # Prepare result dictionary
            segments_info = {
                "hls_segments": {},
                "dash_segments": {}
            }
            
            # Process each variant
            for variant in variants:
                quality = variant["quality"]
                resolution = variant["resolution"]
                bitrate = variant["bitrate"]
                audio_bitrate = variant["audio_bitrate"]
                hls_output_path = variant["hls_output_path"]
                dash_output_path = variant["dash_output_path"]
                
                # Create output directories
                os.makedirs(hls_output_path, exist_ok=True)
                os.makedirs(dash_output_path, exist_ok=True)
                
                # Transcode for HLS
                hls_segments = await self._transcode_for_hls(
                    input_path,
                    hls_output_path,
                    resolution,
                    bitrate,
                    audio_bitrate,
                    settings.HLS_SEGMENT_DURATION
                )
                
                # Transcode for DASH
                dash_segments = await self._transcode_for_dash(
                    input_path,
                    dash_output_path,
                    resolution,
                    bitrate,
                    audio_bitrate,
                    settings.DASH_SEGMENT_DURATION
                )
                
                # Add to segments info
                segments_info["hls_segments"][quality] = hls_segments
                segments_info["dash_segments"][quality] = dash_segments
                
                # Upload segments to storage
                video_id = os.path.basename(os.path.dirname(hls_output_path))
                
                # Upload HLS segments
                for segment in hls_segments:
                    segment_path = os.path.join(hls_output_path, segment["filename"])
                    with open(segment_path, "rb") as f:
                        segment_data = f.read()
                    
                    await self.storage_service.save_file(
                        f"videos/{video_id}/hls/{quality}/{segment['filename']}",
                        segment_data
                    )
                
                # Upload DASH segments
                for segment in dash_segments:
                    segment_number = segment["index"]
                    
                    # Upload initialization segment
                    init_path = os.path.join(dash_output_path, "init.mp4")
                    with open(init_path, "rb") as f:
                        init_data = f.read()
                    
                    await self.storage_service.save_file(
                        f"videos/{video_id}/dash/video_{quality}/init.mp4",
                        init_data
                    )
                    
                    # Upload media segment
                    segment_path = os.path.join(dash_output_path, f"segment-{segment_number}.m4s")
                    with open(segment_path, "rb") as f:
                        segment_data = f.read()
                    
                    await self.storage_service.save_file(
                        f"videos/{video_id}/dash/video_{quality}/segment-{segment_number}.m4s",
                        segment_data
                    )
            
            return segments_info
        
        except Exception as e:
            logger.error(f"Error transcoding video: {str(e)}")
            raise VideoProcessingError("transcode", f"Failed to transcode video: {str(e)}")

    async def _transcode_for_hls(
        self,
        input_path: str,
        output_dir: str,
        resolution: str,
        bitrate: str,
        audio_bitrate: str,
        segment_duration: int
    ) -> List[Dict[str, Any]]:
        """
        Transcode a video for HLS streaming.
        
        Args:
            input_path: Path to the input video file
            output_dir: Directory for output segments
            resolution: Target resolution (e.g., "1280x720")
            bitrate: Target video bitrate (e.g., "2000k")
            audio_bitrate: Target audio bitrate (e.g., "128k")
            segment_duration: Segment duration in seconds
            
        Returns:
            List of segment information
            
        Raises:
            VideoProcessingError: If there's an error transcoding the video
        """
        try:
            # Prepare output path
            segment_template = os.path.join(output_dir, "segment_%03d.ts")
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:v", bitrate,
                "-b:a", audio_bitrate,
                "-s", resolution,
                "-profile:v", "main",
                "-level", "3.1",
                "-g", str(segment_duration * 2),  # GOP size = 2 * segment duration
                "-keyint_min", str(segment_duration),
                "-sc_threshold", "0",
                "-hls_time", str(segment_duration),
                "-hls_list_size", "0",
                "-hls_segment_filename", segment_template,
                "-f", "hls",
                "-y",  # Overwrite existing files
                os.path.join(output_dir, "playlist.m3u8")
            ]
            
            # Add FFmpeg threads if configured
            if settings.FFMPEG_THREADS > 0:
                cmd.extend(["-threads", str(settings.FFMPEG_THREADS)])
                
            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessingError(
                    "transcode_hls", 
                    f"FFmpeg error: {stderr.decode()}"
                )
                
            # Get segment information
            segments = []
            segment_index = 0
            
            while True:
                segment_path = os.path.join(output_dir, f"segment_{segment_index:03d}.ts")
                
                if not os.path.exists(segment_path):
                    break
                    
                # Get segment duration using FFprobe
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    segment_path
                ]
                
                probe_process = await asyncio.create_subprocess_exec(
                    *probe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                probe_stdout, probe_stderr = await probe_process.communicate()
                
                if probe_process.returncode != 0:
                    # If we can't get the duration, use the target duration
                    duration = segment_duration
                else:
                    try:
                        duration = float(probe_stdout.decode().strip())
                    except ValueError:
                        duration = segment_duration
                        
                segments.append({
                    "filename": f"segment_{segment_index:03d}.ts",
                    "duration": duration,
                    "index": segment_index
                })
                
                segment_index += 1
                
            return segments
        
        except Exception as e:
            logger.error(f"Error transcoding for HLS: {str(e)}")
            raise VideoProcessingError("transcode_hls", f"Failed to transcode for HLS: {str(e)}")

    async def _transcode_for_dash(
        self,
        input_path: str,
        output_dir: str,
        resolution: str,
        bitrate: str,
        audio_bitrate: str,
        segment_duration: int
    ) -> List[Dict[str, Any]]:
        """
        Transcode a video for DASH streaming.
        
        Args:
            input_path: Path to the input video file
            output_dir: Directory for output segments
            resolution: Target resolution (e.g., "1280x720")
            bitrate: Target video bitrate (e.g., "2000k")
            audio_bitrate: Target audio bitrate (e.g., "128k")
            segment_duration: Segment duration in seconds
            
        Returns:
            List of segment information
            
        Raises:
            VideoProcessingError: If there's an error transcoding the video
        """
        try:
            # Prepare output path
            segment_template = os.path.join(output_dir, "segment-$Number$.m4s")
            init_segment = os.path.join(output_dir, "init.mp4")
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:v", bitrate,
                "-b:a", audio_bitrate,
                "-s", resolution,
                "-profile:v", "main",
                "-level", "3.1",
                "-g", str(segment_duration * 2),  # GOP size = 2 * segment duration
                "-keyint_min", str(segment_duration),
                "-sc_threshold", "0",
                "-use_timeline", "1",
                "-use_template", "1",
                "-init_seg_name", "init.mp4",
                "-media_seg_name", "segment-$Number$.m4s",
                "-seg_duration", str(segment_duration),
                "-adaptation_sets", "id=0,streams=v id=1,streams=a",
                "-f", "dash",
                "-y",  # Overwrite existing files
                os.path.join(output_dir, "manifest.mpd")
            ]
            
            # Add FFmpeg threads if configured
            if settings.FFMPEG_THREADS > 0:
                cmd.extend(["-threads", str(settings.FFMPEG_THREADS)])
                
            # Run FFmpeg command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessingError(
                    "transcode_dash", 
                    f"FFmpeg error: {stderr.decode()}"
                )
                
            # Get segment information
            segments = []
            segment_index = 1  # DASH segments start from 1
            start_time = 0
            
            while True:
                segment_path = os.path.join(output_dir, f"segment-{segment_index}.m4s")
                
                if not os.path.exists(segment_path):
                    break
                    
                # Get segment duration using FFprobe
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    segment_path
                ]
                
                probe_process = await asyncio.create_subprocess_exec(
                    *probe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                probe_stdout, probe_stderr = await probe_process.communicate()
                
                if probe_process.returncode != 0:
                    # If we can't get the duration, use the target duration
                    duration = segment_duration * 1000  # Convert to milliseconds
                else:
                    try:
                        duration_seconds = float(probe_stdout.decode().strip())
                        duration = int(duration_seconds * 1000)  # Convert to milliseconds
                    except ValueError:
                        duration = segment_duration * 1000
                        
                segments.append({
                    "index": segment_index,
                    "start": start_time,
                    "duration": duration
                })
                
                start_time += duration
                segment_index += 1
                
            return segments
        
        except Exception as e:
            logger.error(f"Error transcoding for DASH: {str(e)}")
            raise VideoProcessingError("transcode_dash", f"Failed to transcode for DASH: {str(e)}")