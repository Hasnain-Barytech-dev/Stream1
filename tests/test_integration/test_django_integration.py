import pytest
from unittest.mock import patch, MagicMock
from app.integrations.django_client import DjangoClient
from app.core.exceptions import IntegrationError

@pytest.fixture
def django_client():
    """Create a django client for testing."""
    return DjangoClient()

@pytest.mark.asyncio
async def test_authenticate_user(django_client):
    """Test user authentication with Django backend."""
    with patch('app.integrations.django_client.DjangoClient._make_request') as mock_request:
        mock_request.return_value = {
            "code": 200,
            "data": {
                "id": "test-user-id",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User"
            }
        }
        
        user = await django_client.authenticate_user("test@example.com", "password123")
        
        assert user is not None
        assert user["id"] == "test-user-id"
        assert user["email"] == "test@example.com"
        
        # Verify the correct endpoint was called
        mock_request.assert_called_once_with(
            "POST", 
            "/user/login/", 
            data={"email": "test@example.com", "password": "password123"}
        )

@pytest.mark.asyncio
async def test_check_upload_permission(django_client):
    """Test checking upload permission from Django."""
    with patch('app.integrations.django_client.DjangoClient._make_request') as mock_request:
        mock_request.return_value = {
            "has_permission": True
        }
        
        result = await django_client.check_upload_permission("company-user-id")
        
        assert result is True
        
        # Verify the correct endpoint was called
        mock_request.assert_called_once_with(
            "GET", 
            "/resource/check-upload-permission/company-user-id/"
        )

@pytest.mark.asyncio
async def test_update_video_metadata(django_client):
    """Test updating video metadata in Django backend."""
    with patch('app.integrations.django_client.DjangoClient._make_request') as mock_request:
        mock_request.return_value = {
            "success": True
        }
        
        metadata = {
            "status": "ready",
            "duration": 60.5,
            "playback_url": "https://example.com/videos/test-video"
        }
        
        result = await django_client.update_video_metadata("test-video-id", metadata)
        
        assert result is True
        
        # Verify the correct endpoint was called
        mock_request.assert_called_once_with(
            "PATCH", 
            "/resource/video/test-video-id/", 
            data=metadata
        )