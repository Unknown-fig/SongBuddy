import os
import shutil
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("songbuddy.config")

# Load .env in development by default
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT != "production":
    load_dotenv()

# Generate or retrieve secure random secret for JWT session management
def get_or_create_secret_key() -> str:
    """Generate or retrieve application secret key."""
    key = os.getenv("SECRET_KEY")
    if not key:
        # In production, warn if ephemeral key is used
        key = secrets.token_urlsafe(32)
        if ENVIRONMENT == "production":
            logger.warning("SECRET_KEY not explicitly configured in production. Ephemeral key generated.")
    return key

SECRET_KEY = get_or_create_secret_key()
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

def get_download_dir() -> Path:
    """Dynamically resolves the download directory from environment variables."""
    return Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()

DOWNLOAD_DIR = get_download_dir()

def reload_config():
    """Reloads environment variables and updates configuration dynamically."""
    global SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, DOWNLOAD_DIR, SECRET_KEY
    load_dotenv(override=True)
    SECRET_KEY = get_or_create_secret_key()
    SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
    SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
    DOWNLOAD_DIR = get_download_dir()

def validate_environment():
    """Validates required environment variables and system dependencies."""
    global DOWNLOAD_DIR
    DOWNLOAD_DIR = get_download_dir()

    missing = []
    if not os.getenv("SPOTIPY_CLIENT_ID"):
        missing.append("SPOTIPY_CLIENT_ID")
    if not os.getenv("SPOTIPY_CLIENT_SECRET"):
        missing.append("SPOTIPY_CLIENT_SECRET")
    
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please check your .env file or environment variables."
        )
    
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "System dependency 'ffmpeg' not found in PATH. "
            "Please install FFmpeg to allow audio extraction and conversion to MP3."
        )
    
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
