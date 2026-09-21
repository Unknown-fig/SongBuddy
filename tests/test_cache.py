import time
from server import BoundedLRUCache

def test_cache_capacity_eviction():
    cache = BoundedLRUCache(capacity=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3

    # Add 4th item -> 'a' was accessed most recently, so 'b' or least recently used is evicted
    cache.set("d", 4)
    assert cache.get("d") == 4
    # Capacity must not exceed 3
    assert len(cache._cache) == 3

def test_cache_ttl_expiration():
    cache = BoundedLRUCache(capacity=5, default_ttl=0.2)
    cache.set("temp", "hello")
    assert cache.get("temp") == "hello"

    time.sleep(0.3)
    assert cache.get("temp") is None
