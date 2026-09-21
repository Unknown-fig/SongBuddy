import pytest
import time
from rate_limiter import AdvancedRateLimiter

def test_rate_limiter_allowance():
    limiter = AdvancedRateLimiter()
    limiter.LIMITS["test_endpoint"] = {"requests": 3, "window": 2, "burst": 1}

    client = "192.168.1.100"
    
    # First 3 requests should be allowed
    assert limiter.is_allowed(client, "test_endpoint")[0] is True
    assert limiter.is_allowed(client, "test_endpoint")[0] is True
    assert limiter.is_allowed(client, "test_endpoint")[0] is True

    # 4th request should be denied
    allowed, info = limiter.is_allowed(client, "test_endpoint")
    assert allowed is False
    assert info["error"] == "rate_limit_exceeded"
    assert info["retry_after"] > 0

    limiter.stop()

def test_rate_limiter_temporary_ban():
    limiter = AdvancedRateLimiter()
    limiter.LIMITS["test_ban"] = {"requests": 1, "window": 10, "burst": 1}
    limiter.VIOLATION_THRESHOLD = 3
    limiter.BAN_DURATION = 5

    client = "10.0.0.99"
    
    # First request OK
    assert limiter.is_allowed(client, "test_ban")[0] is True
    
    # Trigger 3 violations
    limiter.is_allowed(client, "test_ban")
    limiter.is_allowed(client, "test_ban")
    allowed, info = limiter.is_allowed(client, "test_ban")
    
    assert allowed is False
    assert info["error"] == "banned"

    limiter.stop()
