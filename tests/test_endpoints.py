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
    from server import SEARCH_CACHE
    SEARCH_CACHE.set("test_10_false", [{"id": "s1", "title": "Test Song", "artist": "Test Artist"}])
    client.request("GET", "/api/search?q=test")
    response = client.getresponse()
    
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert isinstance(data, list)

@pytest.mark.integration
def test_radio_endpoint(client):
    """Test /api/radio endpoint with seed id and artist parameter"""
    from server import RADIO_CACHE
    tracks = [{"id": "r1", "title": "Never Gonna Give You Up", "artist": "Rick Astley"}]
    RADIO_CACHE.set("dQw4w9WgXcQ_Rick Astley", tracks)
    RADIO_CACHE.set("dQw4w9WgXcQ:rick astley:en", tracks)
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
def test_radio_endpoint_with_title(client):
    """Test /api/radio endpoint with title parameter for language coherence"""
    from server import RADIO_CACHE
    tracks_in = [{"id": "r2", "title": "Kesariya", "artist": "Arijit Singh"}]
    RADIO_CACHE.set("BddP6PY427U_Arijit Singh", tracks_in)
    RADIO_CACHE.set("BddP6PY427U:arijit singh:in", tracks_in)
    client.request("GET", "/api/radio?id=BddP6PY427U&artist=Arijit+Singh&title=Kesariya")
    response = client.getresponse()
    assert response.status == 200
    data = json.loads(response.read().decode("utf-8"))
    assert isinstance(data, list)

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


@pytest.mark.integration
def test_recommendations_and_mixes_endpoints(client):
    """Test Spotify Daily Mixes 1-6, Discover Weekly, and BaRT context endpoints"""
    # 1. Daily Mixes
    client.request("GET", "/api/recommendations/daily-mixes?user_id=dave")
    resp_mixes = client.getresponse()
    assert resp_mixes.status == 200
    mix_data = json.loads(resp_mixes.read().decode("utf-8"))
    assert mix_data["status"] == "success"
    assert len(mix_data["mixes"]) == 6
    assert mix_data["mixes"][0]["id"] == "daily_mix_1"

    # 2. Discover Weekly
    client.request("GET", "/api/recommendations/discover-weekly?user_id=dave")
    resp_dw = client.getresponse()
    assert resp_dw.status == 200
    dw_data = json.loads(resp_dw.read().decode("utf-8"))
    assert dw_data["status"] == "success"
    assert "discover_weekly" in dw_data
    assert len(dw_data["discover_weekly"]["tracks"]) >= 5

    # 3. BaRT Context
    client.request("GET", "/api/recommendations/context?user_id=dave")
    resp_ctx = client.getresponse()
    assert resp_ctx.status == 200
    ctx_data = json.loads(resp_ctx.read().decode("utf-8"))
    assert ctx_data["status"] == "success"
    assert "exploration_rate" in ctx_data["context"]

    # 4. BaRT Implicit Feedback
    fb_payload = json.dumps({
        "user_id": "dave",
        "track_id": "4NRXx6U8ABQ",
        "action": "stream",
        "listen_seconds": 45
    })
    client.request("POST", "/api/recommendations/feedback", body=fb_payload, headers={"Content-Type": "application/json"})
    resp_fb = client.getresponse()
    assert resp_fb.status == 200
    fb_data = json.loads(resp_fb.read().decode("utf-8"))
    assert fb_data["status"] == "success"
    assert fb_data["feedback"]["reward_delta"] == 1.0


@pytest.mark.integration
def test_buddy_feed_endpoints(client):
    """Test Spotify-style Buddy Feed and Social listening endpoints"""
    # 1. Fetch friend activity feed
    client.request("GET", "/api/social/buddy-feed?limit=10")
    resp_feed = client.getresponse()
    assert resp_feed.status == 200
    feed_data = json.loads(resp_feed.read().decode("utf-8"))
    assert feed_data["status"] == "success"
    assert "feed" in feed_data
    assert "stats" in feed_data
    assert isinstance(feed_data["feed"], list)

    # 2. Privacy status
    client.request("GET", "/api/social/privacy")
    resp_priv = client.getresponse()
    assert resp_priv.status == 200
    priv_data = json.loads(resp_priv.read().decode("utf-8"))
    assert priv_data["status"] == "success"
    assert "private_session" in priv_data

    # 3. Listen Along sync endpoint
    client.request("GET", "/api/social/sync?friend_id=usr_elena")
    resp_sync = client.getresponse()
    assert resp_sync.status == 200
    sync_data = json.loads(resp_sync.read().decode("utf-8"))
    assert sync_data["status"] == "success"
    assert "sync" in sync_data
    assert sync_data["sync"]["friend_user_id"] == "usr_elena"


