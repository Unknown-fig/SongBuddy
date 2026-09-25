import os
import json
import secrets
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Set
import jwt
from passlib.context import CryptContext
from config import SECRET_KEY

logger = logging.getLogger("songbuddy.auth")

# Password hashing configuration (Argon2 with pbkdf2 fallback)
pwd_context = CryptContext(
    schemes=["argon2", "pbkdf2_sha256"],
    deprecated="auto"
)

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

class AuthManager:
    """
    Manages user authentication, password hashing, and JWT token lifecycle.
    Includes multi-tier token revocation backed by Vercel KV / Upstash Redis,
    persistent filesystem cache, and in-memory fast lookups.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._revoked_tokens: Set[str] = set()

        # Upstash / Vercel KV REST configuration
        self.kv_url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        self.kv_token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

        # File-based fallback configuration
        if os.getenv("VERCEL"):
            self.file_path = Path("/tmp/revoked_tokens.json")
        else:
            self.file_path = Path(__file__).parent / "revoked_tokens.json"

        self._load_revoked_tokens()

    def _load_revoked_tokens(self):
        """Loads non-expired revoked tokens from file if present."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now_ts = datetime.now(timezone.utc).timestamp()
                    if isinstance(data, dict):
                        valid = {jti for jti, exp in data.items() if isinstance(exp, (int, float)) and exp > now_ts}
                        self._revoked_tokens.update(valid)
            except Exception as e:
                logger.error(f"Error loading revoked tokens from {self.file_path}: {e}")

    def _is_jti_revoked(self, jti: str) -> bool:
        """Checks if a JTI has been revoked across memory, Redis/KV, or file."""
        with self._lock:
            if jti in self._revoked_tokens:
                return True

        # Check Vercel KV / Redis if configured
        if self.kv_url and self.kv_token:
            try:
                import requests
                headers = {"Authorization": f"Bearer {self.kv_token}"}
                resp = requests.get(f"{self.kv_url}/get/songbuddy:revoked:{jti}", headers=headers, timeout=2.0)
                if resp.status_code == 200:
                    result = resp.json().get("result")
                    if result is not None:
                        with self._lock:
                            self._revoked_tokens.add(jti)
                        return True
            except Exception as e:
                logger.warning(f"Error checking token revocation in Vercel KV: {e}")

        # Check file in case another worker updated it
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and jti in data:
                        exp = data[jti]
                        if isinstance(exp, (int, float)) and exp > datetime.now(timezone.utc).timestamp():
                            with self._lock:
                                self._revoked_tokens.add(jti)
                            return True
            except Exception:
                pass

        return False

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using Argon2."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against an Argon2/PBKDF2 hash."""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def create_access_token(self, user_id: str, scopes: Optional[list] = None) -> str:
        """Generate a cryptographically signed JWT access token."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        token_data = {
            "sub": user_id,
            "exp": expires,
            "iat": now,
            "jti": secrets.token_urlsafe(16),
            "scopes": scopes or ["read", "stream"]
        }
        return jwt.encode(token_data, SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token, checking expiration and revocation."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            jti = payload.get("jti")
            if jti and self._is_jti_revoked(jti):
                logger.warning(f"Attempted use of revoked token jti={jti}")
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid JWT token: {e}")
            return None

    def revoke_token(self, token: str):
        """Revoke a token on logout, persisting across workers and serverless instances."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
            jti = payload.get("jti")
            exp = payload.get("exp")
            if not jti:
                return

            now_ts = datetime.now(timezone.utc).timestamp()
            ttl_seconds = max(60, int((exp - now_ts) if exp else 3600))
            expiry_ts = exp if exp else (now_ts + ttl_seconds)

            with self._lock:
                self._revoked_tokens.add(jti)

            # 1. Persist to Vercel KV / Redis if configured
            if self.kv_url and self.kv_token:
                try:
                    import requests
                    headers = {
                        "Authorization": f"Bearer {self.kv_token}",
                        "Content-Type": "application/json"
                    }
                    requests.post(
                        f"{self.kv_url}/set/songbuddy:revoked:{jti}/1/ex/{ttl_seconds}",
                        headers=headers,
                        timeout=2.0
                    )
                except Exception as e:
                    logger.error(f"Failed to persist revoked token to Vercel KV: {e}")

            # 2. Persist to file for multi-worker support
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                existing = {}
                if self.file_path.exists():
                    try:
                        with open(self.file_path, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                    except Exception:
                        existing = {}
                existing = {k: v for k, v in existing.items() if isinstance(v, (int, float)) and v > now_ts}
                existing[jti] = expiry_ts
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(existing, f)
            except Exception as e:
                logger.error(f"Failed to persist revoked tokens to {self.file_path}: {e}")

            logger.info(f"Revoked token jti={jti} with ttl={ttl_seconds}s")
        except jwt.InvalidTokenError:
            pass

# Global AuthManager singleton
auth_manager = AuthManager()

def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """Extract token from standard 'Authorization: Bearer <token>' header."""
    if not authorization_header:
        return None
    parts = authorization_header.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
