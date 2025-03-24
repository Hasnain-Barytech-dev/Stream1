"""
Pydantic models for the EINO Streaming Service API.
This module contains all the request and response models used in the API.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, validator, EmailStr
import re


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data model for decoded JWT payload."""
    id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[int] = None


class VideoStatus(str, Enum):
    """Video processing status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoFormat(str, Enum):
    """Video streaming format enum."""
    HLS = "hls"
    DASH = "dash"


class VideoQuality(str, Enum):
    """Video quality enum."""
    AUTO = "auto"
    LOW = "240p"
    MEDIUM = "360p"
    HIGH = "480p"
    HD = "720p"
    FULL_HD = "1080p"


class ChunkUploadRequest(BaseModel):
    """Chunk upload request model."""
    video_id: str
    chunk_index: int
    total_chunks: int
    

class UploadInitializationRequest(BaseModel):
    """Upload initialization request model."""
    filename: str
    file_size: int
    content_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    
    @validator('content_type')
    def validate_content_type(cls, v):
        if not re.match(r'^video/', v):
            raise ValueError('Content type must be a video format')
        return v


class UploadInitializationResponse(BaseModel):
    """Upload initialization response model."""
    video_id: str
    upload_url: str
    expiration: datetime


class ChunkUploadResponse(BaseModel):
    """Chunk upload response model."""
    video_id: str
    chunk_index: int
    total_chunks: int
    status: str


class VideoMetadata(BaseModel):
    """Video metadata model."""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    filename: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: str
    size: int
    status: VideoStatus
    thumbnail_url: Optional[HttpUrl] = None
    playback_url: Optional[HttpUrl] = None
    created_at: datetime
    updated_at: datetime
    owner_id: str
    company_id: str


class StreamingManifest(BaseModel):
    """Streaming manifest response model."""
    video_id: str
    manifest_url: str
    format: VideoFormat
    available_qualities: List[VideoQuality]


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str