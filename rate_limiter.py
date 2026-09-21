import time
import threading
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple, Optional, Any

class AdvancedRateLimiter:
    """
    Production-grade multi-tier rate limiter with:
    - Per-endpoint sliding window limits
    - Sliding window timestamps with O(1) amortized queue operations
    - Abuse violation tracking and automated temporary bans
    - Periodic background cleanup thread to prevent unbounded memory growth
    """
    def __init__(self):
        # Sliding window: {client_key: deque of epoch timestamps}
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

        # Temporary bans: {client_key: unban_epoch_timestamp}
        self._banned: Dict[str, float] = {}

        # Violation counters: {client_key: violation_count}
        self._violations: Dict[str, int] = defaultdict(int)

        self._lock = threading.Lock()

        # Endpoint-specific limits (requests per window in seconds)
        self.LIMITS: Dict[str, Dict[str, int]] = {
            "api_auth": {"requests": 60, "window": 60, "burst": 15},
            "api_search": {"requests": 25, "window": 60, "burst": 5},
            "api_stream": {"requests": 120, "window": 60, "burst": 20},
            "api_radio": {"requests": 30, "window": 60, "burst": 5},
            "api_lyrics": {"requests": 40, "window": 60, "burst": 10},
            "default": {"requests": 80, "window": 60, "burst": 15}
        }

        self.VIOLATION_THRESHOLD = 8   # Ban after 8 violations
        self.BAN_DURATION = 1800       # 30-minute ban
        self.CLEANUP_INTERVAL = 300    # Run memory purge every 5 minutes

        self._running = True
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def _get_limit_config(self, endpoint: str) -> Dict[str, int]:
        """Find matching endpoint rate limit configuration."""
        for key, cfg in self.LIMITS.items():
            if key in endpoint:
                return cfg
        return self.LIMITS["default"]

    def is_allowed(self, client_id: str, endpoint: str = "default", user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate if a request from client_id (and optional user_id) is within thresholds.
        Returns (is_allowed: bool, details: dict)
        """
        now = time.time()
        key = f"{user_id}@{client_id}" if user_id else client_id

        with self._lock:
            # 1. Check if client is currently in active temporary ban
            if key in self._banned:
                unban_at = self._banned[key]
                if now < unban_at:
                    retry_after = int(unban_at - now)
                    return False, {
                        "error": "banned",
                        "message": f"Client temporarily banned due to excessive rate limit violations. Retry in {retry_after}s.",
                        "retry_after": retry_after
                    }
                else:
                    # Ban expired, restore client standing
                    del self._banned[key]
                    self._violations[key] = 0

            # 2. Retrieve limits configuration
            cfg = self._get_limit_config(endpoint)
            max_requests = cfg["requests"]
            window = cfg["window"]

            # 3. Purge timestamps outside sliding window
            req_queue = self._requests[key]
            cutoff = now - window
            while req_queue and req_queue[0] < cutoff:
                req_queue.popleft()

            # 4. Check if quota available
            current_count = len(req_queue)
            if current_count < max_requests:
                req_queue.append(now)
                return True, {
                    "allowed": True,
                    "remaining": max_requests - current_count - 1,
                    "limit": max_requests,
                    "reset": int(cutoff + window)
                }

            # 5. Rate limit exceeded -> record violation
            self._violations[key] += 1
            if self._violations[key] >= self.VIOLATION_THRESHOLD:
                self._banned[key] = now + self.BAN_DURATION
                return False, {
                    "error": "banned",
                    "message": f"Rate limit violation threshold exceeded. Client banned for {self.BAN_DURATION} seconds.",
                    "retry_after": self.BAN_DURATION
                }

            retry_after = int(window - (now - req_queue[0])) if req_queue else window
            return False, {
                "error": "rate_limit_exceeded",
                "message": f"Too many requests for '{endpoint}'. Quota is {max_requests} requests per {window}s.",
                "retry_after": max(1, retry_after)
            }

    def _periodic_cleanup(self):
        """Background thread purging expired timestamps and stale clients."""
        while self._running:
            time.sleep(self.CLEANUP_INTERVAL)
            now = time.time()
            with self._lock:
                # Cleanup expired bans
                expired_bans = [k for k, exp in self._banned.items() if now >= exp]
                for k in expired_bans:
                    del self._banned[k]
                    self._violations.pop(k, None)

                # Cleanup idle request histories (older than 10 minutes)
                idle_keys = []
                for k, q in self._requests.items():
                    cutoff = now - 600
                    while q and q[0] < cutoff:
                        q.popleft()
                    if not q:
                        idle_keys.append(k)
                for k in idle_keys:
                    del self._requests[k]

    def stop(self):
        """Gracefully stop background cleanup thread."""
        self._running = False
