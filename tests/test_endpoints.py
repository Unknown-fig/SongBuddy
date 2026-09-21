import json
import urllib.request
import pytest

BASE_URL = "http://127.0.0.1:8000"

def test_health_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/api/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "cache" in data

def test_trending_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/api/trending")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "title" in data[0]

def test_auth_login_and_logout():
    # Login as default user 'dave'
    login_data = json.dumps({"username": "dave", "password": "SongBuddy2026!"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "access_token" in data
        token = data["access_token"]

    # Logout with bearer token
    logout_req = urllib.request.Request(
        f"{BASE_URL}/api/auth/logout",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(logout_req) as resp:
        assert resp.status == 200
