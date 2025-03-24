"""
Custom exceptions for the EINO Streaming Service.
"""

from fastapi import HTTPException, status


class StreamingServiceException(Exception):
    """Base exception for all streaming service exceptions."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class VideoNotFoundError(StreamingServiceException):
    """Exception raised when a video is not found."""
    
    def __init__(self, video_id: str):
        self.video_id = video_id
        message = f"Video with ID {video_id} not found"
        super().__init__(message)


class VideoProcessingError(StreamingServiceException):
    """Exception raised when video processing fails."""
    
    def __init__(self, video_id: str, detail: str):
        self.video_id = video_id
        self.detail = detail
        message = f"Video processing error for video {video_id}: {detail}"
        super().__init__(message)


class UploadError(StreamingServiceException):
    """Exception raised when an upload fails."""
    
    def __init__(self, detail: str):
        self.detail = detail
        message = f"Upload error: {detail}"
        super().__init__(message)


class StorageError(StreamingServiceException):
    """Exception raised when a storage operation fails."""
    
    def __init__(self, operation: str, detail: str):
        self.operation = operation
        self.detail = detail
        message = f"Storage error during {operation}: {detail}"
        super().__init__(message)


class IntegrationError(StreamingServiceException):
    """Exception raised when an integration with external service fails."""
    
    def __init__(self, service: str, detail: str):
        self.service = service
        self.detail = detail
        message = f"Integration error with {service}: {detail}"
        super().__init__(message)


class AuthenticationError(HTTPException):
    """Exception raised for authentication errors."""
    
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(HTTPException):
    """Exception raised when a user doesn't have permission."""
    
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class StorageLimitExceededError(HTTPException):
    """Exception raised when storage limit is exceeded."""
    
    def __init__(self, detail: str = "Storage limit exceeded"):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=detail
        )


class InvalidFileTypeError(HTTPException):
    """Exception raised when an invalid file type is uploaded."""
    
    def __init__(self, detail: str = "Invalid file type"):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=detail
        )