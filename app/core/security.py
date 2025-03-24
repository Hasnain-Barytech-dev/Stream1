"""
Security utilities for the EINO Streaming Service.
This module contains functions for JWT token handling and authentication.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import jwt
from jwt.exceptions import PyJWTError

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


def create_access_token(user_data: Dict[str, Any], refresh: bool = False) -> str:
    """
    Create a JWT token for authentication.
    
    Args:
        user_data: User data to encode in the token
        refresh: Whether this is a refresh token (longer expiry)
        
    Returns:
        JWT token string
    """
    # Create a copy of the data to avoid modifying the original
    to_encode = user_data.copy()
    
    # Set expiration time
    if refresh:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add expiration time to the payload
    to_encode.update({"exp": expire})
    
    # Encode the JWT token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token and return the payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        PyJWTError: If token is invalid or expired
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return payload
    except PyJWTError as e:
        logger.error(f"Error decoding JWT token: {str(e)}")
        raise