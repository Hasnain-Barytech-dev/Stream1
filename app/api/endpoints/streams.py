"""
Streaming endpoints for the EINO Streaming Service API.
"""

from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse

from app.api.dependencies import get_current_user, check_streaming_permission
from app.api.schemas import StreamingManifest, VideoMetadata, VideoFormat, VideoQuality
from app.services.streaming.hls_service import HLSService
from app.services.streaming.dash_service import DASHService
from app.services.storage.storage_service import StorageService
from app.core.logging import logger
from app.core.exceptions import VideoNotFoundError

router = APIRouter()
hls_service = HLSService()
dash_service = DASHService()
storage_service = StorageService()


@router.get("/{video_id}", response_model=VideoMetadata)
async def get_video_metadata(
    video_id: str = Path(..., description="Video ID"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> Dict[str, Any]:
    """
    Get metadata for a specific video.
    """
    try:
        # Get video metadata from storage service
        metadata = await storage_service.get_video_metadata(video_id)
        return metadata
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting video metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving video metadata"
        )


@router.get("/{video_id}/manifest", response_model=StreamingManifest)
async def get_streaming_manifest(
    video_id: str = Path(..., description="Video ID"),
    format: VideoFormat = Query(VideoFormat.HLS, description="Streaming format: hls or dash"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> Dict[str, Any]:
    """
    Get the streaming manifest for a video.
    """
    try:
        # Check if video exists
        metadata = await storage_service.get_video_metadata(video_id)
        
        if metadata["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video is not ready for streaming. Current status: {metadata['status']}"
            )
        
        # Get manifest based on format
        if format == VideoFormat.HLS:
            manifest = await hls_service.get_manifest(video_id)
        else:
            manifest = await dash_service.get_manifest(video_id)
        
        return manifest
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting streaming manifest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving streaming manifest"
        )


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: str = Path(..., description="Video ID"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> FileResponse:
    """
    Get the thumbnail image for a video.
    """
    try:
        # Get thumbnail path
        thumbnail_path = await storage_service.get_thumbnail_path(video_id)
        
        # Return thumbnail file
        return FileResponse(
            path=thumbnail_path,
            media_type="image/jpeg",
            filename=f"{video_id}_thumbnail.jpg"
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting thumbnail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving thumbnail"
        )


@router.get("/{video_id}/segments/{segment_path:path}")
async def get_video_segment(
    video_id: str = Path(..., description="Video ID"),
    segment_path: str = Path(..., description="Segment path"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> StreamingResponse:
    """
    Get a specific video segment.
    """
    try:
        # Get segment content and content type
        segment_content, content_type = await storage_service.get_segment(video_id, segment_path)
        
        # Return streaming response
        return StreamingResponse(
            content=segment_content,
            media_type=content_type
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting video segment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving video segment"
        )


@router.get("/my-videos", response_model=List[VideoMetadata])
async def list_my_videos(
    skip: int = Query(0, ge=0, description="Skip first N items"),
    limit: int = Query(20, ge=1, le=100, description="Limit to N items"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    company_id: str = Query(None, description="Filter by company ID"),
    status: str = Query(None, description="Filter by video status")
) -> List[Dict[str, Any]]:
    """
    List videos uploaded by the current user.
    Can be filtered by company and status.
    """
    try:
        # Get videos from storage service
        filters = {}
        
        # Add company filter if provided
        if company_id:
            filters["company_id"] = company_id
        
        # Add status filter if provided
        if status:
            filters["status"] = status
        
        # Get videos for the current user
        videos = await storage_service.list_videos(
            user_id=current_user["id"],
            skip=skip,
            limit=limit,
            filters=filters
        )
        
        return videos
    
    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing videos"
        )


@router.get("/company-videos", response_model=List[VideoMetadata])
async def list_company_videos(
    skip: int = Query(0, ge=0, description="Skip first N items"),
    limit: int = Query(20, ge=1, le=100, description="Limit to N items"),
    company_id: str = Query(..., description="Company ID"),
    status: str = Query(None, description="Filter by video status"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all videos for a specific company.
    Requires company access.
    """
    try:
        # Check if user has access to the company
        # This is handled by the dependency
        
        # Add filters
        filters = {"company_id": company_id}
        
        # Add status filter if provided
        if status:
            filters["status"] = status
        
        # Get videos for the company
        videos = await storage_service.list_videos(
            skip=skip,
            limit=limit,
            filters=filters
        )
        
        return videos
    
    except Exception as e:
        logger.error(f"Error listing company videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing company videos"
        )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str = Path(..., description="Video ID"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> None:
    """
    Delete a video and all associated resources.
    Requires ownership or admin access.
    """
    try:
        # Delete video
        await storage_service.delete_video(video_id, current_user["id"])
        
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting video"
        )

@router.get("/{video_id}/analytics")
async def get_video_analytics(
    video_id: str = Path(..., description="Video ID"),
    timeframe: str = Query("all", description="Timeframe for analytics (all, week, month)"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> Dict[str, Any]:
    """
    Get analytics for a specific video including view counts and engagement metrics.
    """
    try:
        # Get video metrics from metrics service
        # This would be implemented in a real metrics service
        metrics = {
            "view_count": 0,
            "unique_viewers": 0,
            "average_watch_time": 0,
            "completion_rate": 0,
            "timeframe": timeframe,
            "video_id": video_id
        }
        
        # In a production system, you would query a metrics database or service
        # Example: metrics = await metrics_service.get_video_metrics(video_id, timeframe)
        
        return metrics
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting video analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving video analytics"
        )

@router.post("/{video_id}/viewed")
async def record_view(
    video_id: str = Path(..., description="Video ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Record that a video has been viewed by the current user.
    """
    try:
        # In a real implementation, this would call the metrics service
        # Example: await metrics_service.record_view(video_id, current_user["id"])
        
        return {
            "status": "success",
            "video_id": video_id,
            "user_id": current_user["id"]
        }
    
    except Exception as e:
        logger.error(f"Error recording video view: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error recording video view"
        )

@router.get("/{video_id}/chapters")
async def get_video_chapters(
    video_id: str = Path(..., description="Video ID"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> List[Dict[str, Any]]:
    """
    Get the chapters/segments information for a video if available.
    """
    try:
        # This would be implemented in a real system by fetching chapter metadata
        # Example: chapters = await storage_service.get_video_chapters(video_id)
        
        # Placeholder implementation
        chapters = [
            {
                "title": "Introduction",
                "start_time": 0,
                "end_time": 60,
                "thumbnail_url": f"/api/v1/streams/{video_id}/thumbnails/chapter_0.jpg"
            },
            {
                "title": "Main Content",
                "start_time":
                60,
                "end_time": 300,
                "thumbnail_url": f"/api/v1/streams/{video_id}/thumbnails/chapter_1.jpg"
            }
        ]
        
        return chapters
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting video chapters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving video chapters"
        )

@router.get("/{video_id}/subtitles")
async def get_subtitles(
    video_id: str = Path(..., description="Video ID"),
    language: str = Query("en", description="Subtitle language code"),
    current_user: Dict[str, Any] = Depends(check_streaming_permission)
) -> StreamingResponse:
    """
    Get subtitles/captions for a video in the specified language.
    """
    try:
        # In a real implementation, this would fetch subtitle files
        # Example: subtitle_content, content_type = await storage_service.get_subtitles(video_id, language)
        
        # Placeholder implementation for WebVTT subtitles
        subtitle_content = f"""WEBVTT

00:00:00.000 --> 00:00:05.000
Welcome to the EINO platform video

00:00:05.000 --> 00:00:10.000
This is a demonstration of the streaming service
"""
        
        # Return streaming response with subtitle content
        return StreamingResponse(
            content=iter([subtitle_content.encode()]),
            media_type="text/vtt"
        )
    
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting subtitles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving subtitles"
        )

@router.get("/featured")
async def get_featured_videos(
    limit: int = Query(5, ge=1, le=20, description="Number of featured videos to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get a list of featured or recommended videos for the user.
    """
    try:
        # In a real implementation, this would use a recommendation algorithm
        # Example: featured = await recommendation_service.get_featured_videos(current_user["id"], limit)
        
        # Placeholder implementation
        featured = await storage_service.list_videos(
            skip=0,
            limit=limit,
            filters={"status": "ready"}
        )
        
        return featured
    
    except Exception as e:
        logger.error(f"Error getting featured videos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving featured videos"
        )