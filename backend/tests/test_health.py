"""
Tests for health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_check_returns_200(client):
    """Test that health check endpoint returns 200 status."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_returns_healthy_status(client):
    """Test that health check endpoint returns healthy status."""
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert "message" in data


def test_health_check_response_structure(client):
    """Test that health check response has correct structure."""
    response = client.get("/api/health")
    data = response.json()
    
    # Check required fields exist
    assert "status" in data
    assert "message" in data
    
    # Check types
    assert isinstance(data["status"], str)
    assert isinstance(data["message"], str)
