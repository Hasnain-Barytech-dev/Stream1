"""
URL configuration for Django integration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Header, Body
from typing import Dict, Any, List, Optional

from app.core.logging import logger
from app.api.dependencies import get_current_user

from . import views


# Create router
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Check the health of the Django integration.
    """
    return await views.check_health()


@router.post("/auth")
async def authenticate(username: str = Body(...), password: str = Body(...)):
    """
    Authenticate a user with Django backend.
    """
    user = await views.authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    return user


@router.get("/user/{user_id}")
async def get_user(user_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get user details from Django backend.
    """
    return await views.get_user_details(user_id)


@router.patch("/user/{user_id}")
async def update_user(
    user_id: str, 
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user details in Django backend.
    """
    return await views.update_user_details(user_id, data)


@router.get("/company/{company_id}")
async def get_company(company_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get company details from Django backend.
    """
    return await views.get_company_details(company_id)


@router.get("/company/{company_id}/user/{user_id}")
async def get_company_user_relation(
    company_id: str, 
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get company user relationship from Django backend.
    """
    return await views.get_company_user(user_id, company_id)


@router.get("/department/{department_id}/access/{user_id}")
async def check_department_access_endpoint(
    department_id: str, 
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a user has access to a department.
    """
    has_access = await views.check_department_access(user_id, department_id)
    return {"has_access": has_access}


@router.patch("/video/{video_id}/metadata")
async def update_video_metadata_endpoint(
    video_id: str, 
    metadata: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update video metadata in Django backend.
    """
    success = await views.update_video_metadata(video_id, metadata)
    return {"success": success}


@router.post("/notify/video-ready")
async def notify_video_ready_endpoint(
    video_id: str = Body(...), 
    user_id: str = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send notification that a video is ready for streaming.
    """
    success = await views.notify_video_ready(video_id, user_id)
    return {"success": success}


@router.get("/check/upload-permission/{company_user_id}")
async def check_upload_permission_endpoint(
    company_user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a user has permission to upload videos.
    """
    has_permission = await views.check_upload_permission(company_user_id)
    return {"has_permission": has_permission}


@router.get("/check/storage-limit/{company_user_id}")
async def check_storage_limit_endpoint(
    company_user_id: str,
    file_size: int = Query(..., description="File size in bytes"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a user has enough storage for an upload.
    """
    has_storage = await views.check_storage_limit(company_user_id, file_size)
    return {"has_storage": has_storage}


@router.get("/check/video-access/{company_user_id}/{video_id}")
async def check_video_access_endpoint(
    company_user_id: str,
    video_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Check if a user has access to a video.
    """
    has_access = await views.check_video_access(company_user_id, video_id)
    return {"has_access": has_access}