"""
Network Resilience & Anti-Bot Infrastructure for SongBuddy.
Includes:
1. Cookie Health Heartbeat & Dynamic Session Rotation:
   Multi-tier cookie pool management, inspection of critical session cookies
   (__Secure-1PSIDTS, VISITOR_INFO1_LIVE, LOGIN_INFO), automated rotation upon HTTP 429,
   and webhook alert notifications.
2. Smart Stream CDN Re-routing & Token Recovery:
   Extracts and parses Google Video signature expiration (expire param) to prevent
   mid-stream playback stalls and resume playback at exact byte offsets via HTTP 206.
3. SponsorBlock Auto-Skipping Engine:
   Queries SponsorBlock API for music videos to automatically identify and skip
   non-music intros, comedy skits, promotional commentary, and outros.
"""

import os
import sys
import time
import json
import logging
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
import requests

from cookies_data import EMBEDDED_COOKIES

logger = logging.getLogger("songbuddy.network_resilience")
BASE_DIR = Path(__file__).parent.resolve()

# Dedicated Bounded LRU Cache for SponsorBlock segments
class BoundedLRUCache:
    def __init__(self, capacity: int = 300, default_ttl: float = 24 * 3600):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache = {}
        self._order = []

    def get(self, key):
        if key not in self._cache:
            return None
        val, exp = self._cache[key]
        if exp and time.time() > exp:
            del self._cache[key]
            self._order.remove(key)
            return None
        self._order.remove(key)
        self._order.append(key)
        return val

    def set(self, key, value, ttl=None):
        ttl_sec = ttl if ttl is not None else self.default_ttl
        exp = time.time() + ttl_sec if ttl_sec else None
        if key in self._cache:
            self._order.remove(key)
        self._cache[key] = (value, exp)
        self._order.append(key)
        if len(self._cache) > self.capacity:
            oldest = self._order.pop(0)
            self._cache.pop(oldest, None)

SPONSORBLOCK_CACHE = BoundedLRUCache(capacity=400, default_ttl=24 * 3600)
STREAM_EXPIRY_CACHE = BoundedLRUCache(capacity=200, default_ttl=4 * 3600)


def parse_netscape_cookies(cookie_text: str) -> List[Dict[str, Any]]:
    """Parses Netscape cookie file content into structured records."""
    records = []
    if not cookie_text:
        return records
    for line in cookie_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            try:
                exp_ts = int(parts[4])
            except (ValueError, TypeError):
                exp_ts = 0
            records.append({
                "domain": parts[0],
                "flag": parts[1].upper() == "TRUE",
                "path": parts[2],
                "secure": parts[3].upper() == "TRUE",
                "expiration": exp_ts,
                "name": parts[5],
                "value": parts[6]
            })
    return records


class CookiePoolManager:
    """
    Manages a resilient pool of YouTube session cookies with automated health probes,
    dynamic rotation upon bot verification / HTTP 429 rate limits, and fallback recovery.
    """
    def __init__(self):
        self._pool: List[Dict[str, Any]] = []
        self._active_index: int = 0
        self._rotation_history: List[Dict[str, Any]] = []
        self._consecutive_errors: int = 0
        self._last_alert_time: float = 0.0
        self._init_pool()

    def _init_pool(self):
        """Initializes primary, secondary, and fallback cookie sets."""
        self._pool = []

        # 1. Primary from environment or file
        env_cookie = os.getenv("YOUTUBE_COOKIES")
        env_b64 = os.getenv("YOUTUBE_COOKIES_B64")
        if env_b64 and not env_cookie:
            try:
                import base64
                env_cookie = base64.b64decode(env_b64.strip()).decode("utf-8", errors="ignore")
            except Exception:
                pass

        if env_cookie:
            self._pool.append({
                "id": "env_primary",
                "label": "Environment Session Cookies",
                "raw": env_cookie,
                "status": "active"
            })

        # 2. Local filesystem cookies.txt
        local_cf = BASE_DIR / "cookies.txt"
        if local_cf.exists():
            try:
                txt = local_cf.read_text(encoding="utf-8", errors="ignore")
                if txt and ("LOGIN_INFO" in txt or "SID" in txt):
                    self._pool.append({
                        "id": "file_local",
                        "label": "Workspace Local cookies.txt",
                        "raw": txt,
                        "status": "ready"
                    })
            except Exception:
                pass

        # 3. Secondary pool from YOUTUBE_COOKIE_POOL_JSON if provided
        pool_json = os.getenv("YOUTUBE_COOKIE_POOL_JSON")
        if pool_json:
            try:
                extra_sets = json.loads(pool_json)
                if isinstance(extra_sets, list):
                    for idx, s in enumerate(extra_sets):
                        raw_s = s if isinstance(s, str) else s.get("raw", "")
                        if raw_s:
                            self._pool.append({
                                "id": f"pool_secondary_{idx+1}",
                                "label": f"Secondary Cookie Pool Pair {idx+1}",
                                "raw": raw_s,
                                "status": "ready"
                            })
            except Exception as pe:
                logger.warning(f"Failed to parse YOUTUBE_COOKIE_POOL_JSON: {pe}")

        # 4. Embedded fallback cookies from cookies_data.py
        if EMBEDDED_COOKIES and ("LOGIN_INFO" in EMBEDDED_COOKIES or "SID" in EMBEDDED_COOKIES):
            self._pool.append({
                "id": "embedded_fallback",
                "label": "Embedded High-Availability Session",
                "raw": EMBEDDED_COOKIES,
                "status": "ready"
            })

        logger.info(f"Initialized CookiePoolManager with {len(self._pool)} session sets.")

    def get_active_cookie_content(self) -> Optional[str]:
        """Returns the active cookie payload string."""
        if not self._pool:
            return None
        idx = self._active_index % len(self._pool)
        return self._pool[idx].get("raw")

    def get_active_cookie_file(self) -> Optional[Path]:
        """Writes and returns the active cookie file path for yt-dlp."""
        raw = self.get_active_cookie_content()
        if not raw:
            return None
        target = Path("/tmp/youtube_cookies.txt") if os.getenv("VERCEL") else BASE_DIR / "cookies.txt"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(raw, encoding="utf-8")
            return target
        except Exception as e:
            logger.warning(f"Failed to write cookie file: {e}")
            return None

    def rotate_to_next(self, reason: str = "bot_challenge_429") -> bool:
        """Dynamically cycles to the next cookie session in the pool."""
        if len(self._pool) <= 1:
            logger.warning(f"Cannot rotate cookie pool: only {len(self._pool)} set available.")
            return False

        old_idx = self._active_index
        self._active_index = (self._active_index + 1) % len(self._pool)
        new_set = self._pool[self._active_index]

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_id": self._pool[old_idx].get("id"),
            "to_id": new_set.get("id"),
            "reason": reason
        }
        self._rotation_history.append(record)
        if len(self._rotation_history) > 50:
            self._rotation_history.pop(0)

        logger.warning(
            f"Rotated YouTube cookie session from {self._pool[old_idx].get('id')} "
            f"to {new_set.get('id')} (Reason: {reason})"
        )
        self.get_active_cookie_file()
        self._maybe_send_alert(f"YouTube Cookie Rotated to {new_set.get('id')} ({reason})")
        return True

    def report_error(self, status_code: int = 429):
        """Records extraction failure and automatically rotates if rate-limited or blocked."""
        self._consecutive_errors += 1
        if status_code in (429, 403) or self._consecutive_errors >= 3:
            self.rotate_to_next(reason=f"HTTP_{status_code}_error_burst")
            self._consecutive_errors = 0

    def report_success(self):
        """Resets consecutive error tracker on clean extraction."""
        self._consecutive_errors = 0

    def get_health_metrics(self) -> Dict[str, Any]:
        """Calculates session health score (0-100), expiration horizons, and pool metrics."""
        raw = self.get_active_cookie_content()
        if not raw:
            return {
                "health_score": 0,
                "status": "missing",
                "pool_size": len(self._pool),
                "active_index": self._active_index,
                "active_id": "none",
                "authenticated": False,
                "days_remaining": 0,
                "critical_cookies": {},
                "rotation_count": len(self._rotation_history),
                "message": "No cookies found in pool. Operating in client-side bypass mode."
            }

        cookies = parse_netscape_cookies(raw)
        cookie_map = {c["name"]: c for c in cookies}
        now_ts = int(time.time())

        # Inspect critical session tokens
        critical_names = ["__Secure-1PSIDTS", "__Secure-3PSIDTS", "VISITOR_INFO1_LIVE", "LOGIN_INFO", "SID", "SAPISID"]
        critical_status = {}
        min_expiry_days = 999.0
        has_auth = "LOGIN_INFO" in cookie_map or "SID" in cookie_map

        for name in critical_names:
            c = cookie_map.get(name)
            if c:
                exp = c["expiration"]
                days = round((exp - now_ts) / 86400, 1) if exp > 0 else 999.0
                if exp > 0 and days < min_expiry_days:
                    min_expiry_days = days
                critical_status[name] = {
                    "present": True,
                    "days_remaining": days,
                    "status": "valid" if days > 0 else "expired"
                }
            else:
                critical_status[name] = {"present": False, "status": "missing"}

        # Health score calculation (0 - 100)
        score = 100
        if not has_auth:
            score -= 30
        if min_expiry_days <= 0:
            score -= 50
        elif min_expiry_days < 3:
            score -= 30
        elif min_expiry_days < 7:
            score -= 15

        if self._consecutive_errors > 0:
            score -= min(30, self._consecutive_errors * 10)

        score = max(0, min(100, score))

        active_set = self._pool[self._active_index % len(self._pool)] if self._pool else {}
        
        if min_expiry_days <= 0:
            status_label = "expired"
        elif min_expiry_days < 7 or score < 70:
            status_label = "expiring_soon"
        else:
            status_label = "healthy"

        return {
            "health_score": score,
            "status": status_label,
            "source": active_set.get("id", "default"),
            "entries_count": len(cookies),
            "pool_size": len(self._pool),
            "active_index": self._active_index,
            "active_id": active_set.get("id", "default"),
            "active_label": active_set.get("label", "Default"),
            "authenticated": has_auth,
            "total_cookies": len(cookies),
            "days_remaining": min_expiry_days if min_expiry_days < 900 else None,
            "critical_cookies": critical_status,
            "rotation_count": len(self._rotation_history),
            "recent_rotations": self._rotation_history[-5:],
            "message": f"Cookie pool active with {len(self._pool)} sessions. Health score: {score}/100."
        }

    def _maybe_send_alert(self, message: str):
        """Sends webhook notifications to Discord or Telegram if configured."""
        now = time.time()
        if (now - self._last_alert_time) < 300:  # Throttled to max 1 alert per 5 minutes
            return

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if webhook_url:
            try:
                requests.post(
                    webhook_url,
                    json={"content": f"[SongBuddy Anti-Bot Monitor] {message}"},
                    timeout=3.0
                )
                self._last_alert_time = now
            except Exception as we:
                logger.warning(f"Failed to deliver Discord alert: {we}")

        if telegram_token and telegram_chat_id:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={"chat_id": telegram_chat_id, "text": f"[SongBuddy] {message}"},
                    timeout=3.0
                )
                self._last_alert_time = now
            except Exception as te:
                logger.warning(f"Failed to deliver Telegram alert: {te}")


cookie_pool_manager = CookiePoolManager()


# --------------------------------------------------------------------------
# 2. Smart Stream CDN Re-routing & Token Recovery
# --------------------------------------------------------------------------
def inspect_cdn_stream_expiry(stream_url: str) -> Dict[str, Any]:
    """
    Parses signature expiration parameter ('expire') from Google Video CDN URLs.
    Allows predicting stream death before the client stalls mid-playback.
    """
    if not stream_url:
        return {"has_expiry": False, "is_expired": True, "seconds_remaining": 0}

    cached = STREAM_EXPIRY_CACHE.get(stream_url)
    if cached:
        return cached

    try:
        parsed = urllib.parse.urlparse(stream_url)
        params = urllib.parse.parse_qs(parsed.query)
        expire_param = params.get("expire", [None])[0]

        if expire_param and expire_param.isdigit():
            expire_ts = int(expire_param)
            now_ts = int(time.time())
            raw_diff = expire_ts - now_ts
            seconds_remaining = max(0, raw_diff)
            is_expired = raw_diff <= 15  # Buffer 15s safety margin

            info = {
                "has_expiry": True,
                "expire_timestamp": expire_ts,
                "expire_iso": datetime.fromtimestamp(expire_ts, tz=timezone.utc).isoformat(),
                "seconds_remaining": seconds_remaining,
                "is_expired": is_expired
            }
            STREAM_EXPIRY_CACHE.set(stream_url, info, ttl=max(10, min(seconds_remaining, 3600)))
            return info
    except Exception as e:
        logger.debug(f"Failed to parse stream URL expiry: {e}")

    return {"has_expiry": False, "is_expired": False, "seconds_remaining": 3600}


def refresh_stream_token(video_id: str, server_module, byte_offset: int = 0) -> Dict[str, Any]:
    """
    Forces an immediate background CDN token refresh and builds resumption headers
    so client can resume playing at the exact byte offset without restarting track.
    """
    # Invalidate cached stream for this video
    cache_key_high = f"{video_id}_high"
    cache_key_low = f"{video_id}_low"
    cached_stream = getattr(server_module, "STREAM_CACHE", None)
    if cached_stream:
        cached_stream.pop(cache_key_high, None)
        cached_stream.pop(cache_key_low, None)

    # Force fresh extraction
    fresh_stream = server_module.resolve_stream_url(video_id, quality="high", force_refresh=True)
    stream_url = fresh_stream.get("stream_url", "")
    expiry_info = inspect_cdn_stream_expiry(stream_url)

    resumption_headers = {"User-Agent": "Mozilla/5.0"}
    if byte_offset > 0:
        resumption_headers["Range"] = f"bytes={byte_offset}-"

    return {
        "status": "success",
        "video_id": video_id,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "stream_url": stream_url,
        "byte_offset": byte_offset,
        "range_header": resumption_headers.get("Range"),
        "expires_in_seconds": expiry_info.get("seconds_remaining", 3600),
        "acodec": fresh_stream.get("acodec", "aac"),
        "duration": fresh_stream.get("duration", 0)
    }


# --------------------------------------------------------------------------
# 3. SponsorBlock Auto-Skipping Engine
# --------------------------------------------------------------------------
def fetch_sponsorblock_segments(video_id: str) -> Dict[str, Any]:
    """
    Queries SponsorBlock API for music videos to detect and skip:
    - music_offtopic (spoken dialogue, intro comedy skits, cinematic interludes)
    - intro (channel branding, intro sequences)
    - outro (credits, channel promotions)
    - preview (teaser clips)
    - filler (dead air, pauses)
    """
    if not video_id:
        return {"has_segments": False, "segments": []}

    cached = SPONSORBLOCK_CACHE.get(video_id)
    if cached:
        return cached

    url = "https://sponsorblock.kellr.net/api/skipSegments"
    categories = ["music_offtopic", "intro", "outro", "preview", "filler", "sponsor"]
    params = {
        "videoID": video_id,
        "categories": json.dumps(categories)
    }

    try:
        resp = requests.get(url, params=params, timeout=3.0)
        if resp.status_code == 200:
            raw_segments = resp.json()
            parsed_segments = []
            for item in raw_segments:
                seg_times = item.get("segment", [])
                if len(seg_times) >= 2:
                    start_s = round(float(seg_times[0]), 2)
                    end_s = round(float(seg_times[1]), 2)
                    dur = round(end_s - start_s, 2)
                    category = item.get("category", "music_offtopic")
                    
                    category_labels = {
                        "music_offtopic": "Non-Music Video Intro / Skit",
                        "intro": "Video Intro Sequence",
                        "outro": "Outro Commentary / Credits",
                        "sponsor": "Sponsor Message",
                        "filler": "Non-Musical Intermission"
                    }

                    parsed_segments.append({
                        "category": category,
                        "label": category_labels.get(category, "Non-Music Interlude"),
                        "start": start_s,
                        "end": end_s,
                        "duration": dur,
                        "action_type": item.get("actionType", "skip")
                    })

            # Sort segments by chronological start time
            parsed_segments.sort(key=lambda s: s["start"])

            result = {
                "has_segments": len(parsed_segments) > 0,
                "video_id": video_id,
                "total_segments": len(parsed_segments),
                "total_skipped_seconds": sum(s["duration"] for s in parsed_segments),
                "segments": parsed_segments
            }
            SPONSORBLOCK_CACHE.set(video_id, result)
            return result

        elif resp.status_code == 404:
            # Clean track: no non-music segments reported
            clean_res = {
                "has_segments": False,
                "video_id": video_id,
                "total_segments": 0,
                "total_skipped_seconds": 0,
                "segments": [],
                "message": "Pure music track: No non-music skits or intros detected."
            }
            SPONSORBLOCK_CACHE.set(video_id, clean_res, ttl=12 * 3600)
            return clean_res

    except Exception as e:
        logger.warning(f"SponsorBlock resolution failed for {video_id}: {e}")

    return {"has_segments": False, "segments": [], "error": "API unreachable"}
