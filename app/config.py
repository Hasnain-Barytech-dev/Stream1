"""
Configuration settings for the EINO Streaming Service.
"""

import os
import json
from pydantic import BaseSettings
from functools import lru_cache
from typing import List, Optional, Dict, Any


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "EINO Streaming Service"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://localhost",
        "http://127.0.0.1",
        "capacitor://localhost",
        "https://app.eino.world",
        "https://api.eino.world",
        "https://support.eino.world",
        "https://staging.eino.world",
        "https://staging-api.eino.world",
        "https://dev.eino.world",
        "https://dev-api.eino.world",
    ]
    
    # GCP settings
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    
    # Storage buckets
    RAW_VIDEOS_BUCKET: str = os.getenv("RAW_VIDEOS_BUCKET", "")
    PROCESSED_VIDEOS_BUCKET: str = os.getenv("PROCESSED_VIDEOS_BUCKET", "")
    
    # GCP credentials - loaded from environment variables
    GCP_ACCESS_KEY: str = os.getenv("GCP_ACCESS_KEY", "")
    GCP_SECRET_KEY: str = os.getenv("GCP_SECRET_KEY", "")
    GCP_ENDPOINT_URL: str = os.getenv("GCP_ENDPOINT_URL", "https://storage.googleapis.com")
    
    # GCP Service Account Credentials
    @property
    def GCP_SERVICE_ACCOUNT_INFO(self) -> Dict[str, Any]:
        """Load service account info from environment variable JSON string"""
        service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "{}")
        try:
            return json.loads(service_account_json)
        except json.JSONDecodeError:
            # Return empty dict if JSON is invalid
            return {}
    
    # Cloud Functions
    VIDEO_PROCESSING_FUNCTION: str = os.getenv("VIDEO_PROCESSING_FUNCTION", "")
    THUMBNAIL_GENERATION_FUNCTION: str = os.getenv("THUMBNAIL_GENERATION_FUNCTION", "")
    
    # Django integration
    DJANGO_API_URL: str = os.getenv("DJANGO_API_URL", "")
    
    # JWT settings (should match Django settings)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "180"))
    
    # Development mode
    DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() == "true"
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # FFmpeg settings
    FFMPEG_THREADS: int = int(os.getenv("FFMPEG_THREADS", "4"))
    
    # Video streaming settings
    CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB chunks
    ALLOWED_VIDEO_FORMATS: List[str] = [
        'mp4', 'mov', 'wmv', 'avi', 'avchd', 'flv', 
        'f4v', 'swf', 'mkv', 'webm', 'mpeg-2'
    ]
    
    # HLS settings
    HLS_SEGMENT_DURATION: int = 6  # seconds
    HLS_PLAYLIST_SIZE: int = 5
    
    # DASH settings
    DASH_SEGMENT_DURATION: int = 4  # seconds
    
    # Video quality profiles
    VIDEO_QUALITY_PROFILES: Dict[str, Dict[str, Any]] = {
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

    class Config:
        case_sensitive = True
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()