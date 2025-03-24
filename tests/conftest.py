import pytest
import tempfile
import os
from unittest.mock import MagicMock
from app.services.storage.storage_service import StorageService
from app.services.streaming.hls_service import HLSService
from app.services.streaming.dash_service import DASHService

@pytest.fixture
def mock_storage_service():
    """Mock storage service for testing."""
    mock_service = MagicMock(spec=StorageService)
    # Configure basic mocked responses
    mock_service.get_video_metadata.return_value = {
        "id": "test-video-id",
        "filename": "test_video.mp4",
        "status": "ready",
        "duration": 60.0,
        "width": 1280,
        "height": 720,
        "output_path": "videos/test-video-id/test_video.mp4"
    }
    return mock_service

@pytest.fixture
def test_video_file():
    """Create a temporary test video file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write minimal valid MP4 data
        f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
        file_path = f.name
    
    yield file_path
    # Cleanup
    os.unlink(file_path)

@pytest.fixture
def auth_token():
    """Return a mock JWT token for authentication."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InRlc3QtdXNlci1pZCIsInVzZXJuYW1lIjoidGVzdEB1c2VyLmNvbSJ9.signature"