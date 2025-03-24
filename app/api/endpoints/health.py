"""
Health check endpoints for the EINO Streaming Service API.
"""

from typing import Dict, Any
from datetime import datetime
import platform
import os
import psutil

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.core.logging import logger
from app.config import get_settings
from app.services.storage.storage_service import StorageService
from app.integrations.django_client import DjangoClient

settings = get_settings()
router = APIRouter()
storage_service = StorageService()
django_client = DjangoClient()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns service status and timestamp.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "eino-streaming-service",
        "version": "0.1.0"
    }


@router.get("/storage")
async def storage_health() -> Dict[str, Any]:
    """
    Check health of storage service.
    """
    try:
        # Check storage service health
        status = await storage_service.check_health()
        return status
    except Exception as e:
        logger.error(f"Storage health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage service is not healthy"
        )


@router.get("/django")
async def django_health() -> Dict[str, Any]:
    """
    Check health of Django backend.
    """
    try:
        # Check Django API health
        status = await django_client.check_health()
        return status
    except Exception as e:
        logger.error(f"Django health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Django backend is not healthy"
        )


@router.get("/detailed", dependencies=[Depends(get_current_user)])
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with system information.
    Requires authentication.
    """
    try:
        # Get system information
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check storage and Django health
        storage_health = await storage_service.check_health()
        django_health = await django_client.check_health()
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "eino-streaming-service",
            "version": "0.1.0",
            "environment": settings.DEV_MODE and "development" or "production",
            "system": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "cpu_usage": f"{cpu_usage}%",
                "memory": {
                    "total": f"{memory.total / (1024**3):.2f} GB",
                    "available": f"{memory.available / (1024**3):.2f} GB",
                    "used_percent": f"{memory.percent}%"
                },
                "disk": {
                    "total": f"{disk.total / (1024**3):.2f} GB",
                    "free": f"{disk.free / (1024**3):.2f} GB",
                    "used_percent": f"{disk.percent}%"
                },
            },
            "dependencies": {
                "storage": storage_health,
                "django": django_health
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )