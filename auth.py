import os
import secrets
import logging
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
    Includes in-memory revocation list for logout tracking.
    """
    def __init__(self):
        self._revoked_tokens: Set[str] = set()

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
            if jti and jti in self._revoked_tokens:
                logger.warning(f"Attempted use of revoked token jti={jti}")
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid JWT token: {e}")
            return None

    def revoke_token(self, token: str):
        """Revoke a token on logout."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
                logger.info(f"Revoked token jti={jti}")
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
