"""
Views for the Django integration API endpoints.
These views handle the API endpoints for communicating with the Django backend.
"""

from typing import Dict, Any, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query, Header
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.core.exceptions import IntegrationError

from .services import DjangoIntegrationService
from .models import DjangoUser, DjangoCompany, DjangoCompanyUser, DjangoDepartment, DjangoResource


# Initialize the Django integration service
django_service = DjangoIntegrationService()


async def handle_django_exception(func, *args, **kwargs):
    """
    Handle exceptions from Django integration.
    
    Args:
        func: Function to call
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the function call
        
    Raises:
        HTTPException: If there's an error
    """
    try:
        return await func(*args, **kwargs)
    except IntegrationError as e:
        logger.error(f"Django integration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with Django backend: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Django integration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


async def authenticate_user(username: str, password: str) -> Optional[DjangoUser]:
    """
    Authenticate a user with Django backend.
    
    Args:
        username: Username or email
        password: Password
        
    Returns:
        DjangoUser if authentication succeeds, None otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.authenticate_user, username, password)


async def get_user_details(user_id: str) -> DjangoUser:
    """
    Get user details from Django backend.
    
    Args:
        user_id: User ID
        
    Returns:
        DjangoUser object
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.get_user_details, user_id)


async def update_user_details(user_id: str, data: Dict[str, Any]) -> DjangoUser:
    """
    Update user details in Django backend.
    
    Args:
        user_id: User ID
        data: User data to update
        
    Returns:
        Updated DjangoUser
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.update_user_details, user_id, data)


async def get_company_details(company_id: str) -> DjangoCompany:
    """
    Get company details from Django backend.
    
    Args:
        company_id: Company ID
        
    Returns:
        DjangoCompany object
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.get_company_details, company_id)


async def get_company_user(user_id: str, company_id: str) -> Optional[DjangoCompanyUser]:
    """
    Get company user relationship from Django backend.
    
    Args:
        user_id: User ID
        company_id: Company ID
        
    Returns:
        DjangoCompanyUser if exists, None otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.get_company_user, user_id, company_id)


async def check_department_access(user_id: str, department_id: str) -> bool:
    """
    Check if a user has access to a department.
    
    Args:
        user_id: User ID
        department_id: Department ID
        
    Returns:
        True if user has access, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.check_department_access, user_id, department_id)


async def update_video_metadata(video_id: str, metadata: Dict[str, Any]) -> bool:
    """
    Update video metadata in Django backend.
    
    Args:
        video_id: Video ID
        metadata: Video metadata
        
    Returns:
        True if update succeeds, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.update_video_metadata, video_id, metadata)


async def notify_video_ready(video_id: str, user_id: str) -> bool:
    """
    Send notification that a video is ready for streaming.
    
    Args:
        video_id: Video ID
        user_id: User ID
        
    Returns:
        True if notification sent, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.notify_video_ready, video_id, user_id)


async def check_upload_permission(company_user_id: str) -> bool:
    """
    Check if a user has permission to upload videos.
    
    Args:
        company_user_id: Company user ID
        
    Returns:
        True if user has permission, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.check_upload_permission, company_user_id)


async def check_storage_limit(company_user_id: str, file_size: int) -> bool:
    """
    Check if a user has enough storage for an upload.
    
    Args:
        company_user_id: Company user ID
        file_size: File size in bytes
        
    Returns:
        True if enough storage, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.check_storage_limit, company_user_id, file_size)


async def check_video_access(company_user_id: str, video_id: str) -> bool:
    """
    Check if a user has access to a video.
    
    Args:
        company_user_id: Company user ID
        video_id: Video ID
        
    Returns:
        True if user has access, False otherwise
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.check_video_access, company_user_id, video_id)


async def check_health() -> Dict[str, Any]:
    """
    Check the health of the Django backend.
    
    Returns:
        Health status
    """
    return await handle_django_exception(django_service.check_health)


async def list_videos(user_id: str = None, company_id: str = None, skip: int = 0, limit: int = 20) -> List[DjangoResource]:
    """
    List videos from Django backend.
    
    Args:
        user_id: Filter by user ID
        company_id: Filter by company ID
        skip: Number of items to skip
        limit: Maximum number of items to return
        
    Returns:
        List of DjangoResource objects
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.list_videos, user_id, company_id, skip, limit)


async def get_department_details(department_id: str) -> DjangoDepartment:
    """
    Get department details from Django backend.
    
    Args:
        department_id: Department ID
        
    Returns:
        DjangoDepartment object
        
    Raises:
        HTTPException: If there's an error communicating with the API
    """
    return await handle_django_exception(django_service.get_department_details, department_id)