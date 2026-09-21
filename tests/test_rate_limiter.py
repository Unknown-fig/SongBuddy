import pytest
import time
from server import SimpleRateLimiter
from rate_limiter import AdvancedRateLimiter

@pytest.mark.unit
def test_rate_limiter_allows_within_limit(rate_limiter):
    """Test that requests within limit are allowed"""
    assert rate_limiter.is_allowed("192.168.1.1") is True
    assert rate_limiter.is_allowed("192.168.1.1") is True
    assert rate_limiter.is_allowed("192.168.1.1") is True

@pytest.mark.unit
def test_rate_limiter_blocks_over_limit(rate_limiter):
    """Test that requests over limit are blocked"""
    for _ in range(3):
        rate_limiter.is_allowed("192.168.1.1")
    
    # 4th request should be blocked
    assert rate_limiter.is_allowed("192.168.1.1") is False

@pytest.mark.unit
def test_rate_limiter_separate_clients(rate_limiter):
    """Test that different IPs are tracked separately"""
    assert rate_limiter.is_allowed("192.168.1.1") is True
    assert rate_limiter.is_allowed("192.168.1.2") is True
    assert rate_limiter.is_allowed("192.168.1.3") is True

@pytest.mark.unit
@pytest.mark.slow
def test_rate_limiter_window_expiration(rate_limiter):
    """Test that rate limit window expires"""
    for _ in range(3):
        rate_limiter.is_allowed("192.168.1.1")
    
    assert rate_limiter.is_allowed("192.168.1.1") is False
    
    # Wait for window to expire
    time.sleep(1.1)
    
    assert rate_limiter.is_allowed("192.168.1.1") is True

@pytest.mark.unit
def test_advanced_rate_limiter():
    """Test advanced rate limiter with sliding window and temporary ban"""
    limiter = AdvancedRateLimiter()
    limiter.LIMITS["test_ban"] = {"requests": 1, "window": 10, "burst": 1}
    limiter.VIOLATION_THRESHOLD = 3
    limiter.BAN_DURATION = 5

    client = "10.0.0.99"
    assert limiter.is_allowed(client, "test_ban")[0] is True
    
    # Violations
    limiter.is_allowed(client, "test_ban")
    limiter.is_allowed(client, "test_ban")
    allowed, info = limiter.is_allowed(client, "test_ban")
    
    assert allowed is False
    assert info["error"] == "banned"
    limiter.stop()
