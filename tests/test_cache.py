import pytest
import time
import threading
from server import BoundedLRUCache

@pytest.mark.unit
def test_cache_get_set(cache):
    """Test basic get/set operations"""
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("nonexistent") is None

@pytest.mark.unit
def test_cache_capacity_enforcement(cache):
    """Test that cache enforces capacity limit"""
    for i in range(10):
        cache.set(f"key{i}", f"value{i}")
    
    # Cache capacity is 5, so only last 5 items should exist
    assert cache.get("key0") is None  # Evicted
    assert cache.get("key5") == "value5"
    assert cache.get("key9") == "value9"

@pytest.mark.unit
def test_cache_lru_eviction(cache):
    """Test LRU eviction policy"""
    for i in range(5):
        cache.set(f"key{i}", f"value{i}")
    
    # Access key0 to make it most recently used
    cache.get("key0")
    
    # Add new item, should evict key1 (least recently used)
    cache.set("key5", "value5")
    
    assert cache.get("key0") == "value0"  # Still present
    assert cache.get("key1") is None  # Evicted

@pytest.mark.unit
def test_cache_ttl_expiration(cache):
    """Test TTL expiration"""
    cache.set("key1", "value1", ttl=0.5)
    assert cache.get("key1") == "value1"
    
    time.sleep(0.6)
    assert cache.get("key1") is None  # Expired

@pytest.mark.unit
def test_cache_thread_safety(cache):
    """Test thread-safe operations"""
    errors = []
    
    def write_operation(thread_id):
        try:
            for i in range(100):
                cache.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=write_operation, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Thread safety errors: {errors}"
