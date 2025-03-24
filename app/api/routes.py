"""
Main router for the EINO Streaming Service API.
This module includes all the API endpoints from various modules.
"""

from fastapi import APIRouter

from app.api.endpoints import auth, streams, upload, health

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(streams.router, prefix="/streams", tags=["Streaming"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])