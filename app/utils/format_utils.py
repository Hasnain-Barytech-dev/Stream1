"""
Format conversion utilities for the EINO Streaming Service.
"""

import os
import re
from typing import Dict, Any, List, Tuple


def format_file_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    # Define the units and their respective sizes in bytes
    units = [
        ("B", 1),
        ("KB", 1024),
        ("MB", 1024 * 1024),
        ("GB", 1024 * 1024 * 1024),
        ("TB", 1024 * 1024 * 1024 * 1024)
    ]
    
    # Find the appropriate unit
    unit_index = 0
    
    while unit_index < len(units) - 1 and size_bytes >= units[unit_index + 1][1]:
        unit_index += 1
        
    unit_name, unit_size = units[unit_index]
    
    # Format the size with the appropriate unit
    formatted_size = size_bytes / unit_size
    
    # Use 2 decimal places for values less than 10, otherwise use 1
    if formatted_size < 10:
        return f"{formatted_size:.2f} {unit_name}"
    else:
        return f"{formatted_size:.1f} {unit_name}"


def format_bitrate(bitrate_bps: int) -> str:
    """
    Format a bitrate in bits per second to a human-readable string.
    
    Args:
        bitrate_bps: Bitrate in bits per second
        
    Returns:
        Formatted bitrate string
    """
    # Define the units and their respective sizes in bits/second
    units = [
        ("bps", 1),
        ("Kbps", 1000),
        ("Mbps", 1000 * 1000),
        ("Gbps", 1000 * 1000 * 1000)
    ]
    
    # Find the appropriate unit
    unit_index = 0
    
    while unit_index < len(units) - 1 and bitrate_bps >= units[unit_index + 1][1]:
        unit_index += 1
        
    unit_name, unit_size = units[unit_index]
    
    # Format the bitrate with the appropriate unit
    formatted_bitrate = bitrate_bps / unit_size
    
    # Use 2 decimal places for values less than 10, otherwise use 1
    if formatted_bitrate < 10:
        return f"{formatted_bitrate:.2f} {unit_name}"
    else:
        return f"{formatted_bitrate:.1f} {unit_name}"


def parse_bitrate(bitrate_str: str) -> int:
    """
    Parse a bitrate string to bits per second.
    
    Args:
        bitrate_str: Bitrate string (e.g., "2000k", "2.5M")
        
    Returns:
        Bitrate in bits per second
        
    Raises:
        ValueError: If the string is not a valid bitrate
    """
    # Define the unit multipliers
    units = {
        "k": 1000,
        "K": 1000,
        "m": 1000 * 1000,
        "M": 1000 * 1000,
        "g": 1000 * 1000 * 1000,
        "G": 1000 * 1000 * 1000
    }
    
    # Match the pattern: a number followed by an optional unit
    pattern = r'^([\d.]+)([kKmMgG])?$'
    match = re.match(pattern, bitrate_str)
    
    if not match:
        raise ValueError(f"Invalid bitrate format: {bitrate_str}")
        
    value_str, unit = match.groups()
    
    # Parse the value
    try:
        value = float(value_str)
    except ValueError:
        raise ValueError(f"Invalid bitrate value: {value_str}")
        
    # Apply the unit multiplier
    if unit:
        value *= units[unit]
        
    return int(value)


def format_resolution(width: int, height: int) -> str:
    """
    Format width and height as a resolution string.
    
    Args:
        width: Video width in pixels
        height: Video height in pixels
        
    Returns:
        Formatted resolution string
    """
    return f"{width}x{height}"


def parse_resolution(resolution_str: str) -> Tuple[int, int]:
    """
    Parse a resolution string to width and height.
    
    Args:
        resolution_str: Resolution string (e.g., "1280x720")
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ValueError: If the string is not a valid resolution
    """
    # Match the pattern: width x height
    pattern = r'^(\d+)x(\d+)$'
    match = re.match(pattern, resolution_str)
    
    if not match:
        raise ValueError(f"Invalid resolution format: {resolution_str}")
        
    width_str, height_str = match.groups()
    
    try:
        width = int(width_str)
        height = int(height_str)
    except ValueError:
        raise ValueError(f"Invalid resolution values: {resolution_str}")
        
    return width, height


def get_aspect_ratio(width: int, height: int) -> str:
    """
    Calculate the aspect ratio from width and height.
    
    Args:
        width: Video width in pixels
        height: Video height in pixels
        
    Returns:
        Aspect ratio string
    """
    # Calculate the greatest common divisor (GCD)
    def gcd(a, b):
        while b:
            a, b = b, a % b
        return a
        
    common_divisor = gcd(width, height)
    
    # Simplify the ratio
    simplified_width = width // common_divisor
    simplified_height = height // common_divisor
    
    # Check for common aspect ratios
    if simplified_width == 16 and simplified_height == 9:
        return "16:9"
    elif simplified_width == 4 and simplified_height == 3:
        return "4:3"
    elif simplified_width == 21 and simplified_height == 9:
        return "21:9"
    elif simplified_width == 1 and simplified_height == 1:
        return "1:1"
    else:
        return f"{simplified_width}:{simplified_height}"


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension without the dot
    """
    _, ext = os.path.splitext(filename)
    
    # Remove the dot and lowercase
    return ext.lower().lstrip(".")


def get_mime_type_from_extension(extension: str) -> str:
    """
    Get the MIME type from a file extension.
    
    Args:
        extension: File extension without the dot
        
    Returns:
        MIME type string
    """
    # Define the mapping of extensions to MIME types
    mime_types = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "ogg": "video/ogg",
        "ogv": "video/ogg",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "wmv": "video/x-ms-wmv",
        "flv": "video/x-flv",
        "mkv": "video/x-matroska",
        "3gp": "video/3gpp",
        "ts": "video/mp2t",
        "m3u8": "application/x-mpegURL",
        "mpd": "application/dash+xml",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        "json": "application/json",
        "txt": "text/plain",
        "html": "text/html",
        "css": "text/css",
        "js": "application/javascript"
    }
    
    # Normalize the extension
    extension = extension.lower().lstrip(".")
    
    # Return the MIME type or a default
    return mime_types.get(extension, "application/octet-stream")


def get_extension_from_mime_type(mime_type: str) -> str:
    """
    Get the file extension from a MIME type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        File extension without the dot
    """
    # Define the mapping of MIME types to extensions
    extensions = {
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/ogg": "ogv",
        "video/x-msvideo": "avi",
        "video/quicktime": "mov",
        "video/x-ms-wmv": "wmv",
        "video/x-flv": "flv",
        "video/x-matroska": "mkv",
        "video/3gpp": "3gp",
        "video/mp2t": "ts",
        "application/x-mpegURL": "m3u8",
        "application/dash+xml": "mpd",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "application/json": "json",
        "text/plain": "txt",
        "text/html": "html",
        "text/css": "css",
        "application/javascript": "js"
    }
    
    # Normalize the MIME type
    mime_type = mime_type.lower()
    
    # Return the extension or a default
    return extensions.get(mime_type, "bin")


def format_ffmpeg_command(command: List[str]) -> str:
    """
    Format an FFmpeg command list for pretty printing.
    
    Args:
        command: FFmpeg command as a list of strings
        
    Returns:
        Formatted command string
    """
    # Escape quotes and spaces in arguments
    escaped_args = []
    
    def escape_command_args(command):
    escaped_args = []
    
    for arg in command:
        if " " in arg or '"' in arg or "'" in arg:
            # Quote the argument and escape any quotes inside it
            escaped_arg = f'"{arg.replace(\'"\', \'\\\\"\')}"'
        else:
            escaped_arg = arg
            
        escaped_args.append(escaped_arg)
        
    # Join the arguments with spaces
    return " ".join(escaped_args)


def format_hls_master_playlist(variants: List[Dict[str, Any]]) -> str:
    """
    Format an HLS master playlist.
    
    Args:
        variants: List of variant dictionaries, each with bandwidth, resolution, and name
        
    Returns:
        Formatted master playlist
    """
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    
    for variant in variants:
        # Add stream info line
        stream_info = "#EXT-X-STREAM-INF:BANDWIDTH={},RESOLUTION={}".format(
            variant["bandwidth"],
            variant["resolution"]
        )
        
        lines.append(stream_info)
        
        # Add playlist filename
        lines.append(f"{variant['name']}.m3u8")
        
    return "\n".join(lines)


def format_hls_variant_playlist(segments: List[Dict[str, Any]], target_duration: int) -> str:
    """
    Format an HLS variant playlist.
    
    Args:
        segments: List of segment dictionaries, each with duration and filename
        target_duration: Target segment duration in seconds
        
    Returns:
        Formatted variant playlist
        
    Raises:
        ValueError: If segments are empty or target_duration is not positive
    """
    if not segments:
        raise ValueError("Segments list cannot be empty.")
    
    if target_duration <= 0:
        raise ValueError("Target duration must be a positive integer.")
    
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        "#EXT-X-MEDIA-SEQUENCE:0"
    ]
    
    for segment in segments:
        if 'duration' not in segment or 'filename' not in segment:
            raise ValueError("Each segment must contain 'duration' and 'filename' keys.")
        
        # Add segment info
        lines.append(f"#EXTINF:{segment['duration']:.6f},")
        lines.append(segment["filename"])
        
    # Add end marker
    lines.append("#EXT-X-ENDLIST")
    
    return "\n".join(lines)