import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_video_metadata(auth_token):
    """Test retrieving video metadata."""
    response = client.get(
        "/api/v1/streams/test-video-id",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-video-id"
    assert data["status"] == "ready"

def test_get_streaming_manifest(auth_token):
    """Test retrieving HLS streaming manifest."""
    response = client.get(
        "/api/v1/streams/test-video-id/manifest?format=hls",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "test-video-id"
    assert data["format"] == "hls"
    assert "manifest_url" in data
    assert "available_qualities" in data

def test_unauthorized_access_to_video():
    """Test accessing a video without authentication."""
    response = client.get("/api/v1/streams/test-video-id")
    assert response.status_code == 401

def test_accessing_nonexistent_video(auth_token):
    """Test accessing a video that doesn't exist."""
    response = client.get(
        "/api/v1/streams/nonexistent-video",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404