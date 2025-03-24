"""
Authentication endpoints for the EINO Streaming Service API.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token, decode_jwt_token
from app.api.schemas import Token
from app.integrations.django_client import DjangoClient
from app.config import get_settings
from app.core.logging import logger

settings = get_settings()
router = APIRouter()
django_client = DjangoClient()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """
    OAuth2 compatible token login.
    Get an access token for future requests using username and password.
    """
    try:
        # Authenticate user with Django backend
        user = await django_client.authenticate_user(form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create JWT tokens
        access_token = create_access_token(user)
        refresh_token = create_access_token(user, refresh=True)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh access token using a valid refresh token.
    """
    try:
        # Decode refresh token
        payload = decode_jwt_token(refresh_token)
        
        # Get user details
        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user data from Django backend
        user = await django_client.get_user_details(user_id)
        
        # Create new JWT tokens
        access_token = create_access_token(user)
        new_refresh_token = create_access_token(user, refresh=True)
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )