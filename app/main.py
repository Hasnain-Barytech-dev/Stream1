"""
Main FastAPI application entry point for the EINO Streaming Service.
"""

import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.logging import logger, setup_logging
from app.config import get_settings

# Initialize settings
settings = get_settings()

# Set up logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for EINO video streaming service",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to EINO Streaming Service API",
        "documentation": f"{settings.API_V1_STR}/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0"
    }

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Run the application using Uvicorn if executed directly
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEV_MODE)