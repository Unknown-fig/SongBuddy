import json
import time
from unittest.mock import patch, MagicMock
import pytest

from network_resilience import (
    parse_netscape_cookies,
    CookiePoolManager,
    inspect_cdn_stream_expiry,
    refresh_stream_token,
    fetch_sponsorblock_segments,
    SPONSORBLOCK_CACHE
)
import mcp_server


def test_parse_netscape_cookies():
    raw_cookie_sample = (
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tVISITOR_INFO1_LIVE\tabc123xyz\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\t__Secure-1PSIDTS\tsidts_token_value\n"
        "# Comment line\n"
        ".youtube.com\tTRUE\t/\tFALSE\t1893456000\tLOGIN_INFO\tlogin_info_val\n"
    )
    records = parse_netscape_cookies(raw_cookie_sample)
    assert len(records) == 3
    assert records[0]["name"] == "VISITOR_INFO1_LIVE"
    assert records[0]["value"] == "abc123xyz"
    assert records[0]["secure"] is True
    assert records[1]["name"] == "__Secure-1PSIDTS"
    assert records[2]["name"] == "LOGIN_INFO"
    assert records[2]["secure"] is False


def test_cookie_pool_manager_health_and_rotation():
    manager = CookiePoolManager()
    metrics = manager.get_health_metrics()
    
    assert "status" in metrics
    assert "health_score" in metrics
    assert "pool_size" in metrics
    assert "critical_cookies" in metrics
    assert metrics["health_score"] >= 0

    initial_index = manager._active_index
    if len(manager._pool) > 1:
        rotated = manager.rotate_to_next(reason="unit_test_rotation")
        assert rotated is True
        assert manager._active_index != initial_index
        assert len(manager._rotation_history) >= 1
        assert manager._rotation_history[-1]["reason"] == "unit_test_rotation"

    # Test report_error on 429
    prev_rotations = len(manager._rotation_history)
    manager.report_error(429)
    if len(manager._pool) > 1:
        assert len(manager._rotation_history) == prev_rotations + 1


def test_inspect_cdn_stream_expiry():
    future_ts = int(time.time()) + 7200
    mock_cdn_url = f"https://rr1---sn-abc.googlevideo.com/videoplayback?expire={future_ts}&ei=xyz&itag=251"
    
    info = inspect_cdn_stream_expiry(mock_cdn_url)
    assert info["has_expiry"] is True
    assert info["expire_timestamp"] == future_ts
    assert info["seconds_remaining"] > 3600
    assert info["is_expired"] is False

    past_ts = int(time.time()) - 500
    expired_cdn_url = f"https://rr1---sn-abc.googlevideo.com/videoplayback?expire={past_ts}&ei=xyz&itag=251"
    info_exp = inspect_cdn_stream_expiry(expired_cdn_url)
    assert info_exp["is_expired"] is True
    assert info_exp["seconds_remaining"] == 0

    no_exp_url = "https://example.com/audio.mp3"
    info_none = inspect_cdn_stream_expiry(no_exp_url)
    assert info_none["has_expiry"] is False


def test_sponsorblock_segments_fetching_and_caching():
    SPONSORBLOCK_CACHE._cache.clear()
    SPONSORBLOCK_CACHE._order.clear()

    mock_resp_data = [
        {
            "category": "music_offtopic",
            "actionType": "skip",
            "segment": [0.0, 14.5]
        },
        {
            "category": "outro",
            "actionType": "skip",
            "segment": [210.0, 230.0]
        }
    ]

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_get.return_value = mock_resp

        res = fetch_sponsorblock_segments("test_video_123")
        assert res["has_segments"] is True
        assert res["total_segments"] == 2
        assert res["segments"][0]["category"] == "music_offtopic"
        assert res["segments"][0]["start"] == 0.0
        assert res["segments"][0]["end"] == 14.5
        assert res["total_skipped_seconds"] == 34.5

        # Test LRU cache returns cached result without second request
        cached_res = fetch_sponsorblock_segments("test_video_123")
        assert cached_res == res
        assert mock_get.call_count == 1


def test_sponsorblock_clean_music_track_404():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        res = fetch_sponsorblock_segments("clean_music_456")
        assert res["has_segments"] is False
        assert res["total_segments"] == 0
        assert len(res["segments"]) == 0
        assert "message" in res


def test_refresh_stream_token():
    mock_server = MagicMock()
    mock_server.resolve_stream_url.return_value = {
        "stream_url": "https://googlevideo.com/videoplayback?expire=9999999999",
        "acodec": "opus",
        "duration": 240
    }
    mock_server.STREAM_CACHE = {}

    res = refresh_stream_token("test_vid_xyz", mock_server, byte_offset=1048576)
    assert res["status"] == "success"
    assert res["video_id"] == "test_vid_xyz"
    assert res["byte_offset"] == 1048576
    assert res["range_header"] == "bytes=1048576-"
    assert res["stream_url"].startswith("https://googlevideo.com")


def test_mcp_resilience_tools():
    # 1. check_cookie_pool_health
    health_json = mcp_server.check_cookie_pool_health(verbose=True)
    health = json.loads(health_json)
    assert "health_score" in health
    assert "active_session" in health

    # 2. resolve_sponsorblock_segments
    with patch("network_resilience.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        
        sb_json = mcp_server.resolve_sponsorblock_segments("test_mcp_vid")
        sb_data = json.loads(sb_json)
        assert "has_segments" in sb_data
        assert sb_data["has_segments"] is False

    # 3. refresh_stream_token
    with patch("server.resolve_stream_url") as mock_resolve:
        mock_resolve.return_value = {
            "stream_url": "https://googlevideo.com/videoplayback?expire=9999999999",
            "acodec": "opus",
            "duration": 200
        }
        rf_json = mcp_server.refresh_stream_token("test_mcp_vid", byte_offset=5000)
        rf_data = json.loads(rf_json)
        assert rf_data["status"] == "success"
        assert rf_data["video_id"] == "test_mcp_vid"
        assert rf_data["byte_offset"] == 5000
        assert rf_data["range_header"] == "bytes=5000-"


@pytest.mark.integration
def test_http_cookie_health_endpoint(client):
    client.request("GET", "/api/health/cookies")
    resp = client.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert "health_score" in data
    assert "status" in data
    assert "pool_size" in data


@pytest.mark.integration
def test_http_sponsorblock_endpoint(client):
    with patch("network_resilience.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        client.request("GET", "/api/sponsorblock?id=4NRXx6U8ABQ")
        resp = client.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "has_segments" in data

    # Invalid video ID format
    client.request("GET", "/api/sponsorblock?id=invalid_bad_id_too_long_or_short_$$")
    resp_bad = client.getresponse()
    assert resp_bad.status == 400


@pytest.mark.integration
def test_http_stream_refresh_endpoint(client):
    with patch("server.resolve_stream_url") as mock_resolve:
        mock_resolve.return_value = {
            "stream_url": "https://googlevideo.com/videoplayback?expire=9999999999",
            "acodec": "opus",
            "duration": 210
        }
        client.request("GET", "/api/stream/refresh?id=4NRXx6U8ABQ&offset=15000")
        resp = client.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"
        assert data["video_id"] == "4NRXx6U8ABQ"
        assert data["byte_offset"] == 15000


@pytest.mark.integration
def test_http_cookie_rotate_endpoint(client):
    headers = {"Content-Type": "application/json"}
    client.request("POST", "/api/cookies/rotate", body=json.dumps({}), headers=headers)
    resp = client.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert "success" in data
    assert "metrics" in data


def test_audio_disk_cache_manager(tmp_path):
    from network_resilience import AudioDiskCacheManager
    mgr = AudioDiskCacheManager(cache_dir=tmp_path / ".audio_cache", max_cache_bytes=1024 * 1024)

    # 1. Save and retrieve track head chunk
    sample_head = b"\x1a\x45\xdf\xa3" + b"\x00" * 4096
    mgr.save_head_chunk("test_vid_1", sample_head)
    retrieved = mgr.get_head_chunk("test_vid_1")
    assert retrieved == sample_head

    # 2. Cache streaming writer and finalizer
    temp_p, final_p = mgr.get_cache_writer("test_vid_1", ext="webm")
    with open(temp_p, "wb") as f:
        f.write(b"AUDIO_DATA" * 5000)  # > 32KB
    mgr.finalize_cache_file(temp_p, final_p)
    assert final_p.exists()

    # 3. Find cached file
    cached = mgr.find_cached_file("test_vid_1")
    assert cached is not None
    assert cached[0] == final_p
    assert "audio/webm" in cached[1]

    # Non-existent track returns None
    assert mgr.find_cached_file("non_existent_vid") is None


