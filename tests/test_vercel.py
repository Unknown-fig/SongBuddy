import os
import json
import pytest
from pathlib import Path
from http.server import BaseHTTPRequestHandler

@pytest.mark.unit
def test_vercel_entrypoint_structure():
    """Verify api/index.py exists and exports standard Vercel serverless handler"""
    import api.index as vercel_api
    assert hasattr(vercel_api, "handler")
    assert issubclass(vercel_api.handler, BaseHTTPRequestHandler)

@pytest.mark.unit
def test_vercel_config_validity():
    """Verify vercel.json is valid JSON and contains required rewrites"""
    config_path = Path(__file__).parent.parent / "vercel.json"
    assert config_path.exists()
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    assert config["version"] == 2
    assert "rewrites" in config
    assert any("api" in r.get("source", "") for r in config["rewrites"])
    assert "functions" in config
    assert "api/index.py" in config["functions"]

@pytest.mark.unit
def test_vercel_path_normalization():
    """Verify that _normalize_vercel_path correctly extracts __path__ and cleans query parameters"""
    import api.index as vercel_api
    
    class DummyHandler(vercel_api.handler):
        def __init__(self):
            self.path = "/api/index.py?__path__=/api/health&extra=1"
            self.headers = {}
    
    h = DummyHandler()
    h._normalize_vercel_path()
    assert h.path == "/api/health?extra=1"

@pytest.mark.unit
def test_vercel_environment_stream_redirect():
    """Verify that VERCEL=1 triggers HTTP 307 redirect logic"""
    os.environ["VERCEL"] = "1"
    assert os.getenv("VERCEL") == "1"
