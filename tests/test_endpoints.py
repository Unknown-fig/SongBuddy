import pytest
import json
from http.client import HTTPConnection

@pytest.fixture
def client():
    """Fixture for HTTP client (assumes server running on localhost:8000)"""
    return HTTPConnection("127.0.0.1", 8000, timeout=10)

@pytest.mark.integration
def test_health_endpoint(client):
    """Test /api/health endpoint"""
    client.request("GET", "/api/health")
    response = client.getresponse()
    
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert "status" in data
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "memory" in data
    assert "cache_stats" in data

@pytest.mark.integration
def test_trending_endpoint(client):
    """Test /api/trending endpoint"""
    client.request("GET", "/api/trending")
    response = client.getresponse()
    
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "title" in data[0]
    assert "artist" in data[0]

@pytest.mark.integration
def test_search_endpoint(client):
    """Test /api/search endpoint"""
    client.request("GET", "/api/search?q=test")
    response = client.getresponse()
    
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    
    assert isinstance(data, list)

@pytest.mark.integration
def test_static_file_serving(client):
    """Test static file serving"""
    client.request("GET", "/")
    response = client.getresponse()
    
    assert response.status == 200
    content_type = response.getheader("Content-Type", "")
    assert any(ct in content_type for ct in ["text/html", "text/html; charset=utf-8"])

@pytest.mark.integration
def test_security_headers(client):
    """Test security headers presence"""
    client.request("GET", "/api/trending")
    response = client.getresponse()
    
    assert response.getheader("X-Content-Type-Options") == "nosniff"
    assert response.getheader("X-Frame-Options") == "DENY"
    assert "X-XSS-Protection" in response.headers

@pytest.mark.integration
def test_auth_flow(client):
    """Test user login and token revocation lifecycle"""
    body = json.dumps({"username": "dave", "password": "SongBuddy2026!"})
    client.request("POST", "/api/auth/login", body=body, headers={"Content-Type": "application/json"})
    response = client.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert "access_token" in data
    token = data["access_token"]

    # Logout
    client.request("POST", "/api/auth/logout", body="{}", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    })
    logout_resp = client.getresponse()
    assert logout_resp.status == 200
