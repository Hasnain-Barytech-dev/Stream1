"""
Google Cloud Function for generating thumbnails from videos.
This function creates thumbnail images from video files.
"""

import os
import json
import tempfile
import logging
import time
from typing import Dict, Any, List

from utils.gcs_utils import GCSClient
from utils.image_utils import ImageProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GCS client with provided credentials
gcs_client = GCSClient()

# Initialize image processor
image_processor = ImageProcessor()

def generate_thumbnails(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Cloud Function entry point for thumbnail generation.
    
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
        count = event.get("count", 5)  # Default to 5 thumbnails
        
        # Log processing start
        logger.info(f"Starting thumbnail generation for {video_id}")
        logger.info(f"Input path: {input_path}")
        logger.info(f"Output path: {output_path}")
        
        # Validate input
        if not all([video_id, input_path, output_path]):
            raise ValueError("Missing required parameters")
        
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video from GCS
            local_input_path = os.path.join(temp_dir, f"{video_id}_input.mp4")
            gcs_client.download_file(input_path, local_input_path)
            
            # Create output directory
            thumbnail_dir = os.path.join(temp_dir, "thumbnails")
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            # Generate thumbnails
            thumbnail_paths = image_processor.generate_thumbnails(
                local_input_path, thumbnail_dir, count
            )
            
            # Upload thumbnails to GCS
            thumbnail_urls = []
            for i, thumbnail_path in enumerate(thumbnail_paths):
                gcs_thumbnail_path = f"{output_path}/thumbnail_{i}.jpg"
                gcs_client.upload_file(thumbnail_path, gcs_thumbnail_path)
                thumbnail_urls.append(gcs_thumbnail_path)
            
            # Generate animated thumbnail (GIF)
            animated_path = os.path.join(temp_dir, f"{video_id}_animated.gif")
            animated_thumbnail = image_processor.generate_animated_thumbnail(
                local_input_path, animated_path, duration=3
            )
            
            # Upload animated thumbnail
            gcs_animated_path = f"{output_path}/animated.gif"
            gcs_client.upload_file(animated_path, gcs_animated_path)
            
            # Generate poster image (high-quality still)
            poster_path = os.path.join(temp_dir, f"{video_id}_poster.jpg")
            poster_thumbnail = image_processor.generate_poster_image(
                local_input_path, poster_path
            )
            
            # Upload poster image
            gcs_poster_path = f"{output_path}/poster.jpg"
            gcs_client.upload_file(poster_path, gcs_poster_path)
            
            # Process completion time
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Prepare response
            response = {
                "video_id": video_id,
                "status": "success",
                "processing_time": processing_time,
                "thumbnails": thumbnail_urls,
                "animated_thumbnail": gcs_animated_path,
                "poster_image": gcs_poster_path
            }
            
            # Log success
            logger.info(f"Thumbnail generation completed successfully for {video_id}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            
            # Save processing results to GCS
            results_json = json.dumps(response, indent=2)
            results_path = os.path.join(temp_dir, f"{video_id}_thumbnail_results.json")
            
            with open(results_path, "w") as f:
                f.write(results_json)
            
            gcs_results_path = f"{output_path}/thumbnail_results.json"
            gcs_client.upload_file(results_path, gcs_results_path)
            
            return response
            
    except Exception as e:
        # Log error
        logger.error(f"Error generating thumbnails: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = {
            "video_id": event.get("video_id"),
            "status": "error",
            "error": str(e)
        }
        
        return error_response

# HTTP entry point for direct invocation
def generate_thumbnails_http(request):
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
        
        # Generate thumbnails
        result = generate_thumbnails(request_json)
        
        # Return result
        return result, 200
    
    except Exception as e:
        # Return error
        logger.error(f"Error in HTTP handler: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500