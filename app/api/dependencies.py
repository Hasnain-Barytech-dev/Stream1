"""
API dependencies for the EINO Streaming Service.
This module contains all the dependencies used in the API routes.
"""

from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_jwt_token
from app.core.logging import logger
from app.config import get_settings
from app.integrations.django_client import DjangoClient

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")
django_client = DjangoClient()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    department_id: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dependency to get the current authenticated user from JWT token.
    Optionally validates department access if department_id is provided.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token
        payload = decode_jwt_token(token)
        user_id: str = payload.get("id")
        
        if user_id is None:
            raise credentials_exception
        
        # Get user details from Django backend
        user = await django_client.get_user_details(user_id)
        
        # Check department access if department_id is provided
        if department_id and not await django_client.check_department_access(user_id, department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to department {department_id}"
            )
            
        return user
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception

async def get_company_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
    company_id: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dependency to get the company user relationship for the authenticated user.
    Requires a valid company_id header.
    """
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company ID is required"
        )
    
    try:
        # Get company user relationship from Django backend
        company_user = await django_client.get_company_user(current_user["id"], company_id)
        
        if not company_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to company {company_id}"
            )
            
        return company_user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving company user data"
        )

async def check_upload_permission(
    company_user: Dict[str, Any] = Depends(get_company_user),
    request: Request = None
) -> Dict[str, Any]:
    """
    Dependency to check if the user has permission to upload videos.
    Also checks storage limit.
    """
    try:
        # Check if user has upload permission
        if not await django_client.check_upload_permission(company_user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have permission to upload videos"
            )
        
        # Get content length from headers if available
        content_length = 0
        if request and "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
        
        # Check if user has enough storage
        if not await django_client.check_storage_limit(company_user["id"], content_length):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Storage limit exceeded"
            )
            
        return company_user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking upload permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking upload permission"
        )

async def check_streaming_permission(
    company_user: Dict[str, Any] = Depends(get_company_user),
    video_id: str = None
) -> Dict[str, Any]:
    """
    Dependency to check if the user has permission to stream a specific video.
    """
    try:
        # Check if user has streaming permission for this video
        if video_id and not await django_client.check_video_access(company_user["id"], video_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have access to video {video_id}"
            )
            
        return company_user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking streaming permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking streaming permission"
        )