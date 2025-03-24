"""
Image processing utilities for thumbnail generation.
"""

import os
import json
import subprocess
import logging
import math
from typing import Dict, Any, List
import cv2
import numpy as np
from PIL import Image
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Class for image and video processing for thumbnails.
    """
    
    def __init__(self):
        """Initialize the image processor."""
        # Check if FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("FFmpeg is available")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("FFmpeg may not be properly installed")
    
    def generate_thumbnails(
        self, video_path: str, output_dir: str, count: int = 5
    ) -> List[str]:
        """
        Generate thumbnails from a video.
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save thumbnails
            count: Number of thumbnails to generate
            
        Returns:
            List of thumbnail file paths
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Get video duration
            duration = self._get_video_duration(video_path)
            
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
                
                self._extract_frame(video_path, output_path, position)
                
                # Apply post-processing (enhance, resize, etc.)
                self._post_process_image(output_path)
                
                thumbnail_paths.append(output_path)
            
            return thumbnail_paths
        
        except Exception as e:
            logger.error(f"Error generating thumbnails: {str(e)}")
            raise
    
    def generate_animated_thumbnail(
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
        """
        try:
            # Get video duration
            video_duration = self._get_video_duration(video_path)
            
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
            subprocess.run(cmd, check=True, capture_output=True)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Error generating animated thumbnail: {str(e)}")
            raise
    
    def generate_poster_image(self, video_path: str, output_path: str) -> str:
        """
        Generate a high-quality poster image from a video.
        
        Args:
            video_path: Path to the video file
            output_path: Path to save the poster image
            
        Returns:
            Path to the generated poster image
        """
        try:
            # Get video duration
            video_duration = self._get_video_duration(video_path)
            
            # Extract a frame from a good position (30% of the video)
            good_position = video_duration * 0.3
            
            # Create a high-quality image
            cmd = [
                "ffmpeg",
                "-ss", str(good_position),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "1",  # Highest quality
                "-y",  # Overwrite existing file
                output_path
            ]
            
            # Run FFmpeg command
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Enhance the image
            self._enhance_image(output_path)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Error generating poster image: {str(e)}")
            raise
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        Get the duration of a video.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Video duration in seconds
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse duration
            duration = float(result.stdout.strip())
            
            return duration
        
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}")
            raise
    
    def _extract_frame(self, video_path: str, output_path: str, position: float) -> None:
        """
        Extract a frame from a video.
        
        Args:
            video_path: Path to the video file
            output_path: Path to save the extracted frame
            position: Position in seconds
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
            subprocess.run(cmd, check=True, capture_output=True)
        
        except Exception as e:
            logger.error(f"Error extracting frame: {str(e)}")
            raise
    
    def _post_process_image(self, image_path: str) -> None:
        """
        Apply post-processing to an image.
        
        Args:
            image_path: Path to the image file
        """
        try:
            # Open image with OpenCV
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            # Apply light enhancement
            img = self._apply_basic_enhancement(img)
            
            # Resize if needed (maintaining aspect ratio)
            height, width = img.shape[:2]
            max_dimension = 1280  # Maximum width or height
            
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Save the processed image
            cv2.imwrite(image_path, img)
        
        except Exception as e:
            logger.error(f"Error post-processing image: {str(e)}")
            # Don't re-raise, just log the error and continue
            logger.info("Continuing with original image without post-processing")
    
    def _enhance_image(self, image_path: str) -> None:
        """
        Enhance an image with advanced techniques.
        
        Args:
            image_path: Path to the image file
        """
        try:
            # Open image with OpenCV
            img = cv2.imread(image_path)
            
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            # Convert to LAB color space
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            
            # Split channels
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            
            # Merge channels
            limg = cv2.merge((cl, a, b))
            
            # Convert back to BGR
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            # Adjust contrast and brightness
            alpha = 1.1  # Contrast control (1.0 means no change)
            beta = 5    # Brightness control (0 means no change)
            
            # Apply contrast and brightness adjustment
            enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
            
            # Apply slight sharpening
            kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            # Save the enhanced image
            cv2.imwrite(image_path, enhanced)
        
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            # Don't re-raise, just log the error and continue
            logger.info("Continuing with original image without enhancement")
    
    def _apply_basic_enhancement(self, img: np.ndarray) -> np.ndarray:
        """
        Apply basic image enhancement.
        
        Args:
            img: Input image as numpy array
            
        Returns:
            Enhanced image
        """
        try:
            # Convert to YUV color space
            img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            
            # Equalize the histogram of the Y channel
            img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
            
            # Convert back to BGR color space
            enhanced = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
            
            return enhanced
        
        except Exception as e:
            logger.error(f"Error applying basic enhancement: {str(e)}")
            # Return original image if enhancement fails
            return img
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image and extract its properties.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary of image properties
        """
        try:
            # Open image with PIL
            with Image.open(image_path) as img:
                width, height = img.size
                format = img.format
                mode = img.mode
            
            # Get file size
            file_size = os.path.getsize(image_path)
            
            # Return image properties
            return {
                "width": width,
                "height": height,
                "format": format,
                "mode": mode,
                "file_size": file_size
            }
        
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise