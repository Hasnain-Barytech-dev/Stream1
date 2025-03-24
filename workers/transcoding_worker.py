"""
Worker for handling video transcoding in the EINO Streaming Service.

This module handles the transcoding of videos into multiple quality levels
for adaptive streaming using HLS and DASH formats.
"""

import os
import asyncio
import tempfile
from typing import Dict, Any, List, Optional
import math

from app.config import get_settings
from app.core.logging import logger
from app.core.exceptions import VideoProcessingError
from app.services.storage.storage_service import StorageService
from app.services.metrics.metrics_service import MetricsService

settings = get_settings()


class TranscodingWorker:
    """
    Worker for transcoding videos into multiple quality levels.
    This worker handles the FFmpeg encoding processes for creating
    adaptive streaming formats.
    """

    def __init__(self):
        """Initialize the transcoding worker with required services."""
        self.storage_service = StorageService()
        self.metrics_service = MetricsService()

    async def transcode_video(
        self, video_id: str, input_path: str, output_directory: str, quality_profile: Dict[str, Any], format_type: str
    ) -> Dict[str, Any]:
        """
        Transcode a video to a specific quality level and format.
        
        Args:
            video_id: ID of the video
            input_path: Path to the input video file
            output_directory: Directory to save transcoded files
            quality_profile: Quality profile configuration
            format_type: "hls" or "dash"
            
        Returns:
            Transcoding result data
            
        Raises:
            VideoProcessingError: If there's an error transcoding the video
        """
        try:
            # Extract quality profile parameters
            resolution = quality_profile["resolution"]
            bitrate = quality_profile["bitrate"]
            audio_bitrate = quality_profile["audio_bitrate"]
            quality = quality_profile["name"]
            
            # Create output directories
            os.makedirs(output_directory, exist_ok=True)
            
            start_time = asyncio.get_event_loop().time()
            
            if format_type == "hls":
                segment_info = await self._transcode_for_hls(
                    input_path, 
                    output_directory, 
                    resolution, 
                    bitrate, 
                    audio_bitrate,
                    settings.HLS_SEGMENT_DURATION
                )
            elif format_type == "dash":
                segment_info = await self._transcode_for_dash(
                    input_path, 
                    output_directory, 
                    resolution, 
                    bitrate, 
                    audio_bitrate,
                    settings.DASH_SEGMENT_DURATION
                )
            else:
                raise VideoProcessingError(
                    video_id, f"Unsupported format type: {format_type}"
                )
                
            # Calculate processing time
            duration = asyncio.get_event_loop().time() - start_time
            
            # Record metrics
            await self.metrics_service.record_video_processing_time(video_id, duration, True)
            
            # Upload segments to storage
            for segment in segment_info:
                segment_path = os.path.join(output_directory, segment["filename"])
                with open(segment_path, "rb") as f:
                    segment_data = f.read()
                
                # Save to appropriate path based on format type
                storage_path = f"videos/{video_id}/{format_type}/{quality}/{segment['filename']}"
                await self.storage_service.save_file(storage_path, segment_data)
            
            return {
                "video_id": video_id,
                "quality": quality,
                "format": format_type,
                "segments": segment_info,
                "resolution": resolution,
                "bitrate": bitrate
            }
            
        except Exception as e:
            logger.error(f"Error transcoding video {video_id} to {quality_profile['name']}: {str(e)}")
            
            # Record failure metrics
            await self.metrics_service.record_video_processing_time(video_id, 0, False)
            
            raise VideoProcessingError(
                video_id, f"Failed to transcode video to {quality_profile['name']}: {str(e)}"
            )

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
                
            # Also upload initialization segment
            with open(init_segment, "rb") as f:
                init_data = f.read()
                
            return segments
        
        except Exception as e:
            logger.error(f"Error transcoding for DASH: {str(e)}")
            raise VideoProcessingError("transcode_dash", f"Failed to transcode for DASH: {str(e)}")

    async def process_all_qualities(
        self, video_id: str, input_path: str, output_base_dir: str, format_type: str
    ) -> Dict[str, Any]:
        """
        Process a video into all configured quality levels.
        
        Args:
            video_id: ID of the video
            input_path: Path to the input video file
            output_base_dir: Base directory for output files
            format_type: "hls" or "dash"
            
        Returns:
            Processing results for all qualities
            
        Raises:
            VideoProcessingError: If there's an error processing the video
        """
        try:
            quality_profiles = settings.VIDEO_QUALITY_PROFILES
            results = {}
            
            # Process each quality profile
            for quality, profile in quality_profiles.items():
                output_dir = os.path.join(output_base_dir, format_type, quality)
                
                # Skip higher qualities if the video resolution is lower
                if format_type == "dash":
                    output_dir = os.path.join(output_base_dir, format_type, f"video_{quality}")
                
                profile_with_name = profile.copy()
                profile_with_name["name"] = quality
                
                result = await self.transcode_video(
                    video_id, input_path, output_dir, profile_with_name, format_type
                )
                
                results[quality] = result
                
            return results
        
        except Exception as e:
            logger.error(f"Error processing video {video_id} for {format_type}: {str(e)}")
            raise VideoProcessingError(
                video_id, f"Failed to process video for {format_type}: {str(e)}"
            )


async def transcode_video_job(video_id: str, input_path: str, formats: List[str] = None):
    """
    Run a transcoding job for a video.
    
    Args:
        video_id: ID of the video
        input_path: Path to the input video file
        formats: List of formats to transcode to (default: ["hls", "dash"])
        
    Returns:
        Transcoding results
    """
    worker = TranscodingWorker()
    storage_service = StorageService()
    
    if formats is None:
        formats = ["hls", "dash"]
    
    results = {}
    
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the video if it's a storage path
            if not os.path.exists(input_path):
                logger.info(f"Downloading video {video_id} for processing")
                local_input_path = os.path.join(temp_dir, "input_video")
                
                with open(local_input_path, "wb") as f:
                    input_file = await storage_service.get_file(input_path)
                    f.write(input_file.read())
                
                input_path = local_input_path
            
            # Process for each format
            for format_type in formats:
                output_dir = os.path.join(temp_dir, format_type)
                result = await worker.process_all_qualities(
                    video_id, input_path, output_dir, format_type
                )
                results[format_type] = result
            
        return results
    
    except Exception as e:
        logger.error(f"Error in transcoding job for video {video_id}: {str(e)}")
        
        # Update video status to error
        metadata = await storage_service.get_video_metadata(video_id)
        metadata["status"] = "error"
        metadata["error"] = f"Transcoding failed: {str(e)}"
        await storage_service.save_metadata(video_id, metadata)
        
        raise VideoProcessingError(video_id, f"Transcoding job failed: {str(e)}")