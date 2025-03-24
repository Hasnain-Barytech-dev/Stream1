"""
FFmpeg utilities for video processing.
"""

import os
import json
import subprocess
import logging
import math
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FFMpegProcessor:
    """
    Class for video processing using FFmpeg.
    """
    
    def __init__(self):
        """Initialize the FFmpeg processor."""
        # Check if FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("FFmpeg is available")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("FFmpeg may not be properly installed")
    
    def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze a video file to determine its properties.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video properties including duration, resolution, bitrate, etc.
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
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)
            
            # Parse JSON output
            probe_data = json.loads(result.stdout)
            
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
                "format_long_name": format_long_name
            }
        
        except Exception as e:
            logger.error(f"Error analyzing video: {str(e)}")
            raise
    
    def transcode_for_hls(
        self,
        input_path: str,
        output_dir: str,
        resolution: str,
        bitrate: str,
        audio_bitrate: str,
        segment_duration: int = 6
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
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
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
            
            # Run FFmpeg command
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            
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
                
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                
                try:
                    duration = float(probe_result.stdout.strip())
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
            raise
    
    def transcode_for_dash(
        self,
        input_path: str,
        output_dir: str,
        resolution: str,
        bitrate: str,
        audio_bitrate: str,
        segment_duration: int = 4
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
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
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
            
            # Run FFmpeg command
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            
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
                
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                
                try:
                    duration_seconds = float(probe_result.stdout.strip())
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
            raise
    
    def generate_hls_master_playlist(self, variant_playlists: List[Dict[str, Any]]) -> str:
        """
        Generate an HLS master playlist.
        
        Args:
            variant_playlists: List of variant playlist data
                Each item should contain:
                - bandwidth: Bandwidth in bits per second
                - resolution: Video resolution (e.g., "1280x720")
                - name: Quality name (e.g., "720p")
            
        Returns:
            Master playlist content as string
        """
        # Start with header
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3"
        ]
        
        # Add each variant
        for variant in variant_playlists:
            # Add stream info
            stream_info = (
                f"#EXT-X-STREAM-INF:BANDWIDTH={variant['bandwidth']},"
                f"RESOLUTION={variant['resolution']}"
            )
            lines.append(stream_info)
            
            # Add playlist filename
            lines.append(f"{variant['name']}.m3u8")
        
        # Join lines to form the playlist
        return "\n".join(lines)
    
    def generate_dash_mpd(self, adaptation_sets: List[Dict[str, Any]], duration: float) -> str:
        """
        Generate a DASH MPD (Media Presentation Description).
        
        Args:
            adaptation_sets: List of adaptation set data
            duration: Video duration in seconds
            
        Returns:
            MPD content as string
        """
        # Create MPD root element
        root = ET.Element("MPD")
        root.set("xmlns", "urn:mpeg:dash:schema:mpd:2011")
        root.set("profiles", "urn:mpeg:dash:profile:isoff-live:2011")
        root.set("type", "static")
        root.set("minBufferTime", "PT2S")
        root.set("mediaPresentationDuration", f"PT{duration:.3f}S")
        
        # Create Period element
        period = ET.SubElement(root, "Period")
        period.set("id", "1")
        period.set("start", "PT0S")
        
        # Add each adaptation set
        for adaptation in adaptation_sets:
            # Create AdaptationSet element
            adaptation_set = ET.SubElement(period, "AdaptationSet")
            adaptation_set.set("id", adaptation["id"])
            adaptation_set.set("mimeType", adaptation["mime_type"])
            adaptation_set.set("codecs", adaptation["codecs"])
            adaptation_set.set("startWithSAP", "1")
            
            # Create Representation element
            representation = ET.SubElement(adaptation_set, "Representation")
            representation.set("id", adaptation["id"])
            representation.set("width", str(adaptation["width"]))
            representation.set("height", str(adaptation["height"]))
            representation.set("bandwidth", str(adaptation["bandwidth"]))
            
            # Create SegmentTemplate element
            segment_template = ET.SubElement(representation, "SegmentTemplate")
            segment_template.set("initialization", f"{adaptation['id']}/init.mp4")
            segment_template.set("media", f"{adaptation['id']}/segment-$Number$.m4s")
            segment_template.set("timescale", "1000")
            segment_template.set("startNumber", "1")
            
            # Add SegmentTimeline if provided
            if "segment_timeline" in adaptation:
                segment_timeline = ET.SubElement(segment_template, "SegmentTimeline")
                
                for segment in adaptation["segment_timeline"]:
                    s = ET.SubElement(segment_timeline, "S")
                    s.set("t", str(segment["start"]))
                    s.set("d", str(segment["duration"]))
        
        # Convert to pretty XML string
        xml_str = ET.tostring(root, encoding="utf-8")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        return pretty_xml
    
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
        if ext in ["mp4", "mov", "wmv", "avi", "avchd", "flv", 
                  "f4v", "swf", "mkv", "webm", "mpeg-2"]:
            return ext
        
        # Default to generic
        return "video"