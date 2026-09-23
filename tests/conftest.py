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
