"""
Google Cloud Function for video processing.
This function processes videos for adaptive streaming.
"""

import os
import json
import tempfile
import logging
import time
from typing import Dict, Any, List

from utils.gcs_utils import GCSClient
from utils.ffmpeg_utils import FFMpegProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GCS client with provided credentials
gcs_client = GCSClient()

# Initialize FFmpeg processor
ffmpeg_processor = FFMpegProcessor()

# Quality profiles for adaptive streaming
QUALITY_PROFILES = {
    "240p": {
        "resolution": "426x240",
        "bitrate": "300k",
        "audio_bitrate": "64k",
    },
    "360p": {
        "resolution": "640x360",
        "bitrate": "800k",
        "audio_bitrate": "96k",
    },
    "480p": {
        "resolution": "854x480",
        "bitrate": "1400k", 
        "audio_bitrate": "128k",
    },
    "720p": {
        "resolution": "1280x720",
        "bitrate": "2800k",
        "audio_bitrate": "128k",
    },
    "1080p": {
        "resolution": "1920x1080",
        "bitrate": "5000k",
        "audio_bitrate": "192k",
    }
}

def process_video(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Cloud Function entry point for video processing.
    
    Args:
        event: Cloud Function event payload
        context: Cloud Function context (optional)
    
    Returns:
        Dictionary with processing results
    """
    start_time = time.time()
    
    try:
        # Extract data from event
        video_id = event.get("video_id")
        input_path = event.get("input_path")
        output_path = event.get("output_path")
        formats = event.get("formats", ["hls", "dash"])
        requested_qualities = event.get("qualities", ["360p", "480p", "720p"])
        
        # Log processing start
        logger.info(f"Starting video processing for {video_id}")
        logger.info(f"Input path: {input_path}")
        logger.info(f"Output path: {output_path}")
        
        # Validate input
        if not all([video_id, input_path, output_path]):
            raise ValueError("Missing required parameters")
            
        # Filter requested qualities to only include supported ones
        qualities = [q for q in requested_qualities if q in QUALITY_PROFILES]
        if not qualities:
            qualities = ["360p", "720p"]  # Default qualities
        
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video from GCS
            local_input_path = os.path.join(temp_dir, f"{video_id}_input.mp4")
            gcs_client.download_file(input_path, local_input_path)
            
            # Analyze video
            video_info = ffmpeg_processor.analyze_video(local_input_path)
            logger.info(f"Video info: {json.dumps(video_info)}")
            
            # Process for adaptive streaming
            streaming_results = {}
            
            # Create output directories
            os.makedirs(os.path.join(temp_dir, "hls"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "dash"), exist_ok=True)
            
            # Process each quality
            for quality in qualities:
                profile = QUALITY_PROFILES[quality]
                quality_output_dir = os.path.join(temp_dir, "output", quality)
                os.makedirs(quality_output_dir, exist_ok=True)
                
                # HLS processing
                if "hls" in formats:
                    hls_output_dir = os.path.join(temp_dir, "hls", quality)
                    os.makedirs(hls_output_dir, exist_ok=True)
                    
                    hls_segments = ffmpeg_processor.transcode_for_hls(
                        local_input_path,
                        hls_output_dir,
                        profile["resolution"],
                        profile["bitrate"],
                        profile["audio_bitrate"]
                    )
                    
                    # Upload HLS segments
                    for segment in hls_segments:
                        segment_path = os.path.join(hls_output_dir, segment["filename"])
                        gcs_segment_path = f"{output_path}/hls/{quality}/{segment['filename']}"
                        gcs_client.upload_file(segment_path, gcs_segment_path)
                    
                    # Upload variant playlist
                    playlist_path = os.path.join(hls_output_dir, "playlist.m3u8")
                    gcs_playlist_path = f"{output_path}/hls/{quality}.m3u8"
                    gcs_client.upload_file(playlist_path, gcs_playlist_path)
                    
                    if "hls" not in streaming_results:
                        streaming_results["hls"] = {}
                    
                    streaming_results["hls"][quality] = {
                        "segments": hls_segments,
                        "playlist_url": gcs_playlist_path
                    }
                
                # DASH processing
                if "dash" in formats:
                    dash_output_dir = os.path.join(temp_dir, "dash", f"video_{quality}")
                    os.makedirs(dash_output_dir, exist_ok=True)
                    
                    dash_segments = ffmpeg_processor.transcode_for_dash(
                        local_input_path,
                        dash_output_dir,
                        profile["resolution"],
                        profile["bitrate"],
                        profile["audio_bitrate"]
                    )
                    
                    # Upload init segment
                    init_path = os.path.join(dash_output_dir, "init.mp4")
                    gcs_init_path = f"{output_path}/dash/video_{quality}/init.mp4"
                    gcs_client.upload_file(init_path, gcs_init_path)
                    
                    # Upload media segments
                    for segment in dash_segments:
                        segment_path = os.path.join(dash_output_dir, f"segment-{segment['index']}.m4s")
                        gcs_segment_path = f"{output_path}/dash/video_{quality}/segment-{segment['index']}.m4s"
                        gcs_client.upload_file(segment_path, gcs_segment_path)
                    
                    if "dash" not in streaming_results:
                        streaming_results["dash"] = {}
                    
                    streaming_results["dash"][quality] = {
                        "segments": dash_segments,
                        "init_segment_url": gcs_init_path
                    }
            
            # Generate manifest files
            if "hls" in formats and "hls" in streaming_results:
                # Build master playlist
                hls_variants = []
                for quality, profile in QUALITY_PROFILES.items():
                    if quality in streaming_results["hls"]:
                        width, height = profile["resolution"].split("x")
                        hls_variants.append({
                            "bandwidth": int(profile["bitrate"].replace("k", "000")),
                            "resolution": profile["resolution"],
                            "name": quality
                        })
                
                # Generate and upload master playlist
                master_playlist = ffmpeg_processor.generate_hls_master_playlist(hls_variants)
                master_playlist_path = os.path.join(temp_dir, "hls", "master.m3u8")
                
                with open(master_playlist_path, "w") as f:
                    f.write(master_playlist)
                
                gcs_master_path = f"{output_path}/hls/master.m3u8"
                gcs_client.upload_file(master_playlist_path, gcs_master_path)
                streaming_results["hls"]["master_url"] = gcs_master_path
            
            if "dash" in formats and "dash" in streaming_results:
                # Build MPD
                dash_adaptation_sets = []
                for quality, profile in QUALITY_PROFILES.items():
                    if quality in streaming_results["dash"]:
                        width, height = profile["resolution"].split("x")
                        dash_adaptation_sets.append({
                            "id": f"video_{quality}",
                            "mime_type": "video/mp4",
                            "codecs": "avc1.64001f",
                            "width": int(width),
                            "height": int(height),
                            "bandwidth": int(profile["bitrate"].replace("k", "000")),
                            "segment_timeline": streaming_results["dash"][quality]["segments"]
                        })
                
                # Generate and upload DASH manifest
                mpd = ffmpeg_processor.generate_dash_mpd(dash_adaptation_sets, video_info["duration"])
                mpd_path = os.path.join(temp_dir, "dash", "manifest.mpd")
                
                with open(mpd_path, "w") as f:
                    f.write(mpd)
                
                gcs_mpd_path = f"{output_path}/dash/manifest.mpd"
                gcs_client.upload_file(mpd_path, gcs_mpd_path)
                streaming_results["dash"]["master_url"] = gcs_mpd_path
            
            # Process completion time
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Prepare response
            response = {
                "video_id": video_id,
                "status": "success",
                "processing_time": processing_time,
                "video_info": video_info,
                "streaming_results": streaming_results
            }
            
            # Log success
            logger.info(f"Video processing completed successfully for {video_id}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            
            # Save processing results to GCS
            results_json = json.dumps(response, indent=2)
            results_path = os.path.join(temp_dir, f"{video_id}_processing_results.json")
            
            with open(results_path, "w") as f:
                f.write(results_json)
            
            gcs_results_path = f"{output_path}/processing_results.json"
            gcs_client.upload_file(results_path, gcs_results_path)
            
            return response
            
    except Exception as e:
        # Log error
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = {
            "video_id": event.get("video_id"),
            "status": "error",
            "error": str(e)
        }
        
        return error_response

# HTTP entry point for direct invocation
def process_video_http(request):
    """
    HTTP entry point for direct Cloud Function invocation.
    
    Args:
        request: HTTP request object
    
    Returns:
        HTTP response with processing results
    """
    try:
        # Parse request data
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return {"error": "No JSON data in request"}, 400
        
        # Process the video
        result = process_video(request_json)
        
        # Return result
        return result, 200
    
    except Exception as e:
        # Return error
        logger.error(f"Error in HTTP handler: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500