"""
Upload endpoints for the EINO Streaming Service API.
"""

from typing import Dict, Any
import os

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_user, check_upload_permission
from app.api.schemas import UploadInitializationRequest, UploadInitializationResponse, ChunkUploadRequest, ChunkUploadResponse
from app.services.storage.storage_service import StorageService
from app.services.processing.video_processor import VideoProcessor
from app.core.logging import logger
from app.config import get_settings

settings = get_settings()
router = APIRouter()
storage_service = StorageService()
video_processor = VideoProcessor()


@router.post("/initialize", response_model=UploadInitializationResponse)
async def initialize_upload(
    data: UploadInitializationRequest,
    company_user: Dict[str, Any] = Depends(check_upload_permission)
) -> Dict[str, Any]:
    """
    Initialize a new video upload.
    Returns a video ID and upload URL for chunk uploads.
    """
    try:
        # Check if content type is valid
        file_extension = os.path.splitext(data.filename)[1].lower().replace('.', '')
        if file_extension not in settings.ALLOWED_VIDEO_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported video format: {file_extension}. Supported formats: {settings.ALLOWED_VIDEO_FORMATS}"
            )
        
        # Initialize upload in storage service
        initialization = await storage_service.initialize_upload(
            filename=data.filename,
            file_size=data.file_size,
            content_type=data.content_type,
            title=data.title,
            description=data.description,
            user_id=company_user["user"]["id"],
            company_id=company_user["company"]["id"]
        )
        
        return initialization
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error initializing upload"
        )


@router.post("/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    video_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    company_user: Dict[str, Any] = Depends(check_upload_permission)
) -> Dict[str, Any]:
    """
    Upload a video chunk.
    If this is the last chunk, the video processing will be triggered.
    """
    try:
        # Read chunk data
        chunk_data = await file.read()
        
        # Upload chunk to storage service
        result = await storage_service.upload_chunk(
            video_id=video_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_data=chunk_data,
            user_id=company_user["user"]["id"]
        )
        
        # If this is the last chunk, start processing
        if chunk_index == total_chunks - 1:
            # Run processing in background
            background_tasks.add_task(
                video_processor.process_video,
                video_id=video_id,
                user_id=company_user["user"]["id"],
                company_id=company_user["company"]["id"]
            )
            
            result["status"] = "processing_started"
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading chunk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading chunk"
        )


@router.get("/status/{video_id}")
async def get_upload_status(
    video_id: str,
    company_user: Dict[str, Any] = Depends(check_upload_permission)
) -> Dict[str, Any]:
    """
    Get the status of a video upload and processing.
    """
    try:
        # Get upload status from storage service
        status = await storage_service.get_upload_status(
            video_id=video_id,
            user_id=company_user["user"]["id"]
        )
        
        return status
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting upload status"
        )


@router.delete("/{video_id}")
async def cancel_upload(
    video_id: str,
    company_user: Dict[str, Any] = Depends(check_upload_permission)
) -> Dict[str, Any]:
    """
    Cancel an ongoing upload or delete a processed video.
    """
    try:
        # Cancel upload in storage service
        result = await storage_service.cancel_upload(
            video_id=video_id,
            user_id=company_user["user"]["id"]
        )
        
        return {"status": "deleted", "video_id": video_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error canceling upload"
        )