import os
import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Configure test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long!"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["PORT"] = "8000"
os.environ["ENABLE_DEMO_ACCOUNT"] = "true"

from server import BoundedLRUCache, SimpleRateLimiter, FEATURED_TRACKS

@pytest.fixture
def cache():
    """Fixture for LRU cache instance"""
    return BoundedLRUCache(capacity=5, default_ttl=1.0)

@pytest.fixture
def rate_limiter():
    """Fixture for rate limiter instance"""
    return SimpleRateLimiter(max_requests=3, window_seconds=1.0)

@pytest.fixture
def sample_track():
    """Fixture for sample track data"""
    return {
        "id": "test123",
        "title": "Test Track",
        "artist": "Test Artist",
        "duration": 180,
        "thumbnail": "https://example.com/thumb.jpg"
    }

@pytest.fixture
def featured_tracks():
    """Fixture for featured tracks list"""
    return FEATURED_TRACKS.copy()

@pytest.fixture
def auth():
    from auth import auth_manager
    return auth_manager

import socket
import threading
import time
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

_test_server = None

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

@pytest.fixture(scope="session", autouse=True)
def ensure_server_running():
    global _test_server
    os.environ["ENVIRONMENT"] = "test"
    if not is_port_in_use(8000):
        try:
            from server import SongBuddyHandler
            _test_server = ThreadingHTTPServer(("127.0.0.1", 8000), SongBuddyHandler)
            thread = threading.Thread(target=_test_server.serve_forever, daemon=True)
            thread.start()
            time.sleep(0.4)
        except Exception as e:
            pytest.skip(f"Could not bind test server to port 8000: {e}")
    yield
    if _test_server:
        try:
            _test_server.shutdown()
            _test_server.server_close()
        except Exception:
            pass

@pytest.fixture
def client():
    """Fixture for HTTP client"""
    return HTTPConnection("127.0.0.1", 8000, timeout=10)
