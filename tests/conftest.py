import os
import sys
from pathlib import Path
import pytest

# Ensure root workspace directory is in python path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars-long!"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["PORT"] = "8000"

@pytest.fixture
def auth():
    from auth import auth_manager
    return auth_manager
