import pytest
import os
import io
from app.services.storage.storage_service import StorageService
from app.services.storage.local_service import LocalService
from app.core.exceptions import VideoNotFoundError

@pytest.fixture
def storage_service():
    """Create a real storage service using the local implementation."""
    return StorageService()  # This will use LocalService in test environment

@pytest.mark.asyncio
async def test_save_and_get_metadata(storage_service):
    """Test saving and retrieving video metadata."""
    video_id = "test-metadata-video"
    test_metadata = {
        "id": video_id,
        "filename": "test.mp4",
        "status": "pending",
        "created_at": "2025-03-24T12:00:00Z",
        "updated_at": "2025-03-24T12:00:00Z",
        "owner_id": "test-user",
        "company_id": "test-company"
    }
    
    # Save metadata
    await storage_service.save_metadata(video_id, test_metadata)
    
    # Retrieve metadata
    retrieved = await storage_service.get_video_metadata(video_id)
    
    assert retrieved["id"] == test_metadata["id"]
    assert retrieved["filename"] == test_metadata["filename"]
    assert retrieved["status"] == test_metadata["status"]
    
    # Clean up
    await storage_service.delete_metadata(video_id)

@pytest.mark.asyncio
async def test_nonexistent_video(storage_service):
    """Test retrieving metadata for a video that doesn't exist."""
    with pytest.raises(VideoNotFoundError):
        await storage_service.get_video_metadata("nonexistent-video")

@pytest.mark.asyncio
async def test_save_and_get_file(storage_service):
    """Test saving and retrieving a file."""
    test_path = "test-files/sample.txt"
    test_content = b"This is test content"
    
    # Save file
    await storage_service.save_file(test_path, test_content)
    
    # Get file
    file_content = await storage_service.get_file(test_path)
    
    # Read the file content
    retrieved_content = file_content.read()
    
    assert retrieved_content == test_content
    
    # Clean up
    await storage_service.delete_file(test_path)