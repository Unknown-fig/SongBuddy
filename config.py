import os
import shutil
import secrets
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("songbuddy.config")

# Load .env in development by default
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT != "production":
    load_dotenv()

INSECURE_PLACEHOLDER_KEYS = {
    "generate-with-secrets.token_urlsafe(32)",
    "change-me-to-a-secure-random-secret-key-32-chars",
    "your-secret-key-here-must-be-at-least-32-chars",
    "your_secret_key_here_must_be_at_least_32_characters",
    "replace_with_a_secure_random_key_of_at_least_32_chars"
}

def is_valid_secret_key(key: Optional[str]) -> bool:
    """Verifies that the provided secret key meets minimum length and is not a known template placeholder."""
    if not key:
        return False
    k = key.strip()
    if len(k) < 32:
        return False
    lower_k = k.lower()
    if (
        lower_k in INSECURE_PLACEHOLDER_KEYS
        or lower_k.startswith("generate-with-secrets")
        or lower_k.startswith("your-secret")
        or lower_k.startswith("your_secret")
        or lower_k.startswith("change-me")
        or lower_k.startswith("replace-with")
    ):
        logger.warning(
            "Insecure placeholder SECRET_KEY detected in environment. "
            "Rejecting placeholder to enforce cryptographic security."
        )
        return False
    return True

# Generate or retrieve secure random secret for JWT session management
def get_or_create_secret_key() -> str:
    """Generate or retrieve application secret key with production consistency guarantees."""
    key = os.getenv("SECRET_KEY")
    if is_valid_secret_key(key):
        return key.strip()

    env = os.getenv("ENVIRONMENT", ENVIRONMENT).lower()
    is_production = (env == "production") or bool(os.getenv("VERCEL"))
    if is_production:
        # In production/serverless, missing SECRET_KEY causes session drops.
        # Derive a stable, deterministic key from deployment metadata so all edge instances match.
        stable_seed = (
            os.getenv("VERCEL_PROJECT_ID")
            or os.getenv("VERCEL_DEPLOYMENT_ID")
            or os.getenv("VERCEL_GIT_COMMIT_SHA")
            or os.getenv("HEROKU_APP_ID")
            or os.getenv("RENDER_SERVICE_ID")
        )
        if stable_seed:
            import hashlib
            derived = hashlib.sha256(f"songbuddy-stable-auth-secret-{stable_seed}".encode()).hexdigest()
            logger.warning(
                "SECRET_KEY not explicitly set in production! Derived stable key from deployment metadata "
                "to prevent session invalidation across serverless instances."
            )
            return derived
        logger.warning("SECRET_KEY not configured in production. Using stable fallback key.")
        return "songbuddy-prod-default-secret-key-32-chars-long-minimum!"

    # Development / local fallback
    return secrets.token_urlsafe(32)

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

def validate_environment(require_ffmpeg: bool = False):
    """Validates required environment variables and system dependencies."""
    global DOWNLOAD_DIR
    DOWNLOAD_DIR = get_download_dir()

    # Spotify credentials are optional for web streaming (YouTube and LRCLIB are primary)
    if not os.getenv("SPOTIPY_CLIENT_ID") or not os.getenv("SPOTIPY_CLIENT_SECRET"):
        logger.warning(
            "Spotify API credentials (SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET) not configured. "
            "Web streaming continues normally; Spotify metadata extraction will be disabled."
        )

    has_ffmpeg = bool(shutil.which("ffmpeg"))
    if not has_ffmpeg:
        if require_ffmpeg:
            raise EnvironmentError(
                "System dependency 'ffmpeg' not found in PATH. "
                "Please install FFmpeg to allow audio extraction and conversion to MP3."
            )
        else:
            logger.warning(
                "System dependency 'ffmpeg' not found in PATH. "
                "Audio streaming operates via in-memory/browser driver; offline MP3 conversion will be unavailable."
            )

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
