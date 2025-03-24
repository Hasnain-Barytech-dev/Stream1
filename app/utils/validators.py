"""
Validation utilities for the EINO Streaming Service.
"""

import re
import os
from typing import List, Union

from app.config import get_settings

settings = get_settings()


def validate_video_format(filename: str) -> bool:
    """
    Validate if a file has an allowed video format.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if the file has an allowed format, False otherwise
    """
    _, ext = os.path.splitext(filename)
    
    # Remove the dot and lowercase
    ext = ext.lower().lstrip(".")
    
    # Check if extension is in allowed formats
    return ext in settings.ALLOWED_VIDEO_FORMATS


def validate_email(email: str) -> bool:
    """
    Validate if a string is a valid email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if the email is valid, False otherwise
    """
    # Simple regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """
    Validate if a string is a valid username.
    
    Args:
        username: Username to validate
        
    Returns:
        True if the username is valid, False otherwise
    """
    # Username must be at least 3 characters, alphanumeric with underscores and hyphens
    pattern = r'^[a-zA-Z0-9_-]{3,}$'
    
    return bool(re.match(pattern, username))


def validate_password(password: str) -> bool:
    """
    Validate if a string is a valid password.
    
    Args:
        password: Password to validate
        
    Returns:
        True if the password is valid, False otherwise
    """
    # Password must be at least 8 characters and contain at least one number
    # and one uppercase letter
    if len(password) < 8:
        return False
        
    # Check for at least one digit
    if not any(char.isdigit() for char in password):
        return False
        
    # Check for at least one uppercase letter
    if not any(char.isupper() for char in password):
        return False
        
    return True


def validate_resolution(resolution: str) -> bool:
    """
    Validate if a string is a valid resolution.
    
    Args:
        resolution: Resolution to validate (e.g., "1280x720")
        
    Returns:
        True if the resolution is valid, False otherwise
    """
    # Resolution must be in the format WIDTHxHEIGHT
    pattern = r'^[0-9]+x[0-9]+$'
    
    if not re.match(pattern, resolution):
        return False
        
    # Check if width and height are even numbers (required for some video codecs)
    width, height = map(int, resolution.split('x'))
    
    return width % 2 == 0 and height % 2 == 0


def validate_bitrate(bitrate: str) -> bool:
    """
    Validate if a string is a valid bitrate.
    
    Args:
        bitrate: Bitrate to validate (e.g., "2000k")
        
    Returns:
        True if the bitrate is valid, False otherwise
    """
    # Bitrate must be a number followed by 'k' or 'M'
    pattern = r'^[0-9]+[kM]$'
    
    return bool(re.match(pattern, bitrate))


def validate_segment_duration(duration: int) -> bool:
    """
    Validate if a segment duration is valid.
    
    Args:
        duration: Segment duration in seconds
        
    Returns:
        True if the duration is valid, False otherwise
    """
    # Duration must be between 1 and 10 seconds
    return 1 <= duration <= 10


def validate_video_id(video_id: str) -> bool:
    """
    Validate if a string is a valid video ID.
    
    Args:
        video_id: Video ID to validate
        
    Returns:
        True if the video ID is valid, False otherwise
    """
    # Video ID must be a UUID
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    return bool(re.match(pattern, video_id, re.IGNORECASE))


def validate_mime_type(mime_type: str) -> bool:
    """
    Validate if a string is a valid video MIME type.
    
    Args:
        mime_type: MIME type to validate
        
    Returns:
        True if the MIME type is valid, False otherwise
    """
    # MIME type must start with "video/"
    return mime_type.startswith("video/")


def validate_file_size(file_size: int, max_size: int = 10 * 1024 * 1024 * 1024) -> bool:
    """
    Validate if a file size is within limits.
    
    Args:
        file_size: File size in bytes
        max_size: Maximum allowed size in bytes (default: 10GB)
        
    Returns:
        True if the file size is valid, False otherwise
    """
    # File size must be positive and less than max_size
    return 0 < file_size <= max_size


def validate_thumbnail_format(filename: str) -> bool:
    """
    Validate if a file has an allowed thumbnail format.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if the file has an allowed format, False otherwise
    """
    allowed_formats = ["jpg", "jpeg", "png", "gif"]
    
    _, ext = os.path.splitext(filename)
    
    # Remove the dot and lowercase
    ext = ext.lower().lstrip(".")
    
    # Check if extension is in allowed formats
    return ext in allowed_formats