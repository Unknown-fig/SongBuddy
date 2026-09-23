import os
import pytest
from user_store import UserStore

@pytest.mark.unit
def test_demo_account_disabled_in_production(monkeypatch):
    """Verify demo account is strictly disabled by default in production"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ENABLE_DEMO_ACCOUNT", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    
    store = UserStore()
    assert store.is_demo_account_enabled() is False

@pytest.mark.unit
def test_demo_account_enabled_when_explicit(monkeypatch):
    """Verify demo account can be explicitly enabled"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENABLE_DEMO_ACCOUNT", "true")
    
    store = UserStore()
    assert store.is_demo_account_enabled() is True

@pytest.mark.unit
def test_user_store_save_and_retrieve(tmp_path):
    """Verify UserStore can save and get users locally"""
    store = UserStore()
    store.file_path = tmp_path / "test_users.json"
    
    test_user = {
        "password_hash": "hash_abc",
        "name": "Alice Tester",
        "email": "alice@test.com"
    }
    store.save_user("alice", test_user)
    
    loaded = store.get_user("alice")
    assert loaded is not None
    assert loaded["name"] == "Alice Tester"
    assert loaded["email"] == "alice@test.com"

@pytest.mark.unit
def test_config_stable_secret_in_production(monkeypatch):
    """Verify get_or_create_secret_key does not return ephemeral random keys when metadata exists"""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("VERCEL_PROJECT_ID", "prj_test123")
    
    from config import get_or_create_secret_key
    k1 = get_or_create_secret_key()
    k2 = get_or_create_secret_key()
    assert k1 == k2
    assert len(k1) >= 32
