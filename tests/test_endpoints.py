import os
import socket
import threading
import time
import pytest
import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

# Server fixtures are provided globally in conftest.py

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
def test_radio_endpoint(client):
    """Test /api/radio endpoint with seed id and artist parameter"""
    client.request("GET", "/api/radio?id=dQw4w9WgXcQ&artist=Rick+Astley")
    response = client.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "title" in data[0]
        assert "artist" in data[0]

@pytest.mark.integration
def test_thumb_color_endpoint(client):
    """Test /api/thumb_color endpoint extracting RGB accent color"""
    client.request("GET", "/api/thumb_color?id=4NRXx6U8ABQ")
    response = client.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert "r" in data
    assert "g" in data
    assert "b" in data
    assert "hex" in data

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

@pytest.mark.integration
def test_queue_drawer_elements(client):
    """Test that queue drawer remove and clear controls are served in HTML, CSS, and JS"""
    # 1. Verify index.html contains the skip Now Playing button and clear auto recommendations button
    client.request("GET", "/")
    resp = client.getresponse()
    assert resp.status == 200
    html_content = resp.read().decode("utf-8")
    assert "btn-queue-skip-np" in html_content
    assert "btn-clear-auto-queue" in html_content
    assert "btn-clear-queue" in html_content

    # 2. Verify styles.css contains styles for queue removal and auto playlist rows
    client.request("GET", "/styles.css")
    css_resp = client.getresponse()
    assert css_resp.status == 200
    css_content = css_resp.read().decode("utf-8")
    assert ".queue-item-remove-btn" in css_content
    assert ".btn-clear-auto-queue" in css_content

    # 3. Verify app.js contains queue remove handlers
    client.request("GET", "/app.js")
    js_resp = client.getresponse()
    assert js_resp.status == 200
    js_content = js_resp.read().decode("utf-8")
    assert "removeFromQueue" in js_content
    assert "removeFromRadioQueue" in js_content
    assert "clearRadioQueue" in js_content

