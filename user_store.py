"""
User Storage Manager with multi-tier persistence for SongBuddy.
Supports Vercel KV (Upstash Redis REST), local filesystem, and in-memory cache.
Eliminates hardcoded credentials in production environments.
"""
import os
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("songbuddy.user_store")

BASE_DIR = Path(__file__).parent.resolve()

class UserStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

        # Upstash / Vercel KV REST configuration
        self.kv_url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        self.kv_token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

        # File-based configuration
        if os.getenv("VERCEL"):
            self.file_path = Path("/tmp/users.json")
        else:
            self.file_path = BASE_DIR / "users.json"

    def get_backend_name(self) -> str:
        if self.kv_url and self.kv_token:
            return "vercel_kv"
        if os.getenv("VERCEL"):
            return "ephemeral_tmp"
        return "file"

    def is_demo_account_enabled(self) -> bool:
        """Only enable demo accounts when explicitly configured or in development/testing."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        is_prod = (env == "production") or bool(os.getenv("VERCEL"))
        if is_prod:
            # Production: strictly opt-in via ENABLE_DEMO_ACCOUNT=true
            return os.getenv("ENABLE_DEMO_ACCOUNT", "false").lower() == "true"
        # Development / test: enabled by default for developer convenience
        return os.getenv("ENABLE_DEMO_ACCOUNT", "true").lower() == "true"

    def _load_from_kv(self) -> Optional[Dict[str, Dict[str, Any]]]:
        if not (self.kv_url and self.kv_token):
            return None
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.kv_token}"}
            resp = requests.get(f"{self.kv_url}/get/songbuddy:users_db", headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json().get("result")
                if data:
                    if isinstance(data, str):
                        return json.loads(data)
                    elif isinstance(data, dict):
                        return data
        except Exception as e:
            logger.error(f"Vercel KV user load failure: {e}")
        return None

    def _save_to_kv(self, users: Dict[str, Dict[str, Any]]) -> bool:
        if not (self.kv_url and self.kv_token):
            return False
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.kv_token}",
                "Content-Type": "application/json"
            }
            payload = json.dumps(users)
            resp = requests.post(f"{self.kv_url}/set/songbuddy:users_db", data=payload, headers=headers, timeout=3.0)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Vercel KV user save failure: {e}")
            return False

    def load_users(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            # 1. Try Vercel KV if available
            kv_data = self._load_from_kv()
            if kv_data is not None:
                self._memory_cache = kv_data
                return self._memory_cache

            # 2. Try file system
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        self._memory_cache = json.load(f)
                        return self._memory_cache
                except Exception as e:
                    logger.error(f"Error reading {self.file_path}: {e}")

            # 3. Initialize default demo user ONLY if explicitly allowed
            users: Dict[str, Dict[str, Any]] = {}
            if self.is_demo_account_enabled():
                demo_pwd = os.getenv("DEMO_ACCOUNT_PASSWORD", "SongBuddy2026!")
                from auth import auth_manager
                users["dave"] = {
                    "password_hash": auth_manager.hash_password(demo_pwd),
                    "name": "Dave Cooper",
                    "email": "dave@songbuddy.studio",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_demo": True
                }
                logger.info("Demo user 'dave' initialized for non-production development.")

            self._memory_cache = users
            return self._memory_cache

    def save_users(self, users: Dict[str, Dict[str, Any]]):
        with self._lock:
            self._memory_cache = users
            # 1. Save to KV if configured
            if self.kv_url and self.kv_token:
                self._save_to_kv(users)

            # 2. Always persist to file if possible
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(users, f, indent=2)
            except Exception as e:
                logger.error(f"Error persisting users to {self.file_path}: {e}")

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        uname = username.strip().lower()
        users = self.load_users()
        return users.get(uname)

    def save_user(self, username: str, user_data: Dict[str, Any]):
        uname = username.strip().lower()
        users = self.load_users()
        users[uname] = user_data
        self.save_users(users)

user_store = UserStore()
