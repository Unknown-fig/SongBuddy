import os
import sys
import re
import ssl
import json
import time
import psutil
import urllib.parse
import threading
from datetime import datetime, timezone
from collections import OrderedDict
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import requests
import yt_dlp
from dotenv import load_dotenv
from pydantic import ValidationError

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 1. Load configuration and environment
load_dotenv()
from config import SECRET_KEY, ENVIRONMENT, DOWNLOAD_DIR
from auth import auth_manager, extract_bearer_token
from validators import (
    SearchQueryValidator,
    VideoIDValidator,
    LyricsQueryValidator,
    UserCredentialsValidator
)
from rate_limiter import AdvancedRateLimiter

# Track server start time
SERVER_START_TIME = time.time()

# Configure structured logging (Phase 1, Step 1.1)
def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()

    if log_format == "json":
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_obj)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        handlers=[handler]
    )
    return logging.getLogger("songbuddy")

import logging
logger = setup_logging()

# Project paths
BASE_DIR = Path(__file__).parent.resolve()
PUBLIC_DIR = BASE_DIR / "public"

# Global Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
YOUTUBE_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{11}$")
TITLE_CLEANUP_REGEX = re.compile(
    r"(?i)\s*[\(\[](?:official\s*(?:video|audio|music\s*video|lyric\s*video|visualizer)?|lyrics?|4k|hd|remastered|audio|hq)[\)\]]|\s*\|\s*.*$"
)

# Concurrency & Locks
MAX_CONCURRENT_EXTRACTIONS = 4
EXTRACTION_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_EXTRACTIONS)
VIDEO_LOCKS: Dict[str, threading.Lock] = {}
VIDEO_LOCKS_GUARD = threading.Lock()

def get_video_lock(video_id: str) -> threading.Lock:
    """Returns a per-video-id mutex to deduplicate concurrent extractions for the same track."""
    with VIDEO_LOCKS_GUARD:
        if video_id not in VIDEO_LOCKS:
            VIDEO_LOCKS[video_id] = threading.Lock()
        return VIDEO_LOCKS[video_id]

# Thread-Safe Bounded LRU Cache with TTL eviction
class BoundedLRUCache:
    def __init__(self, capacity: int = 256, default_ttl: Optional[float] = None):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._cache: OrderedDict[Any, Tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expires_at = self._cache[key]
            if expires_at is not None and time.time() > expires_at:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return val

    def set(self, key: Any, value: Any, ttl: Optional[float] = None):
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expires_at)
            if len(self._cache) > self.capacity:
                self._cache.popitem(last=False)

    def pop(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            entry = self._cache.pop(key, None)
            return entry[0] if entry is not None else default

# Initialize bounded caches & persistent components
STREAM_CACHE = BoundedLRUCache(capacity=200, default_ttl=4 * 3600)   # 4h TTL
RADIO_CACHE = BoundedLRUCache(capacity=100, default_ttl=2 * 3600)    # 2h TTL
SEARCH_CACHE = BoundedLRUCache(capacity=200, default_ttl=3600)       # 1h TTL
LYRICS_CACHE = BoundedLRUCache(capacity=500, default_ttl=24 * 3600)  # 24h TTL
HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update({"User-Agent": USER_AGENT})

# Simple & Advanced Rate Limiters for Compatibility
class SimpleRateLimiter:
    def __init__(self, max_requests: int = 80, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._clients.get(client_ip, [])
            timestamps = [ts for ts in timestamps if ts > cutoff]
            if len(timestamps) >= self.max_requests:
                self._clients[client_ip] = timestamps
                return False
            timestamps.append(now)
            self._clients[client_ip] = timestamps
            if len(self._clients) > 5000:
                self._clients = {k: v for k, v in self._clients.items() if v and v[-1] > cutoff}
            return True

STREAM_RATE_LIMITER = SimpleRateLimiter(max_requests=100, window_seconds=60.0)
RATE_LIMITER = AdvancedRateLimiter()

# Multi-Tier Persistent User Store & Database
from user_store import user_store

def load_users() -> Dict[str, Dict[str, Any]]:
    return user_store.load_users()

def save_users():
    user_store.save_users(USERS_DB)

USERS_DB = load_users()

# Curated Trending Tracks for initial launch
FEATURED_TRACKS = [
    {
        "id": "4NRXx6U8ABQ",
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "album": "After Hours",
        "duration": 200,
        "duration_formatted": "3:20",
        "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg"
    },
    {
        "id": "kTJczUoc26U",
        "title": "STAY",
        "artist": "The Kid LAROI, Justin Bieber",
        "album": "F*CK LOVE 3: OVER YOU",
        "duration": 141,
        "duration_formatted": "2:21",
        "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg"
    },
    {
        "id": "0-7IHOXkiV8",
        "title": "Way Down We Go",
        "artist": "KALEO",
        "album": "A/B",
        "duration": 219,
        "duration_formatted": "3:39",
        "thumbnail": "https://i.ytimg.com/vi/0-7IHOXkiV8/hqdefault.jpg"
    },
    {
        "id": "TUVcZfQe-Kw",
        "title": "Levitating",
        "artist": "Dua Lipa",
        "album": "Future Nostalgia",
        "duration": 203,
        "duration_formatted": "3:23",
        "thumbnail": "https://i.ytimg.com/vi/TUVcZfQe-Kw/hqdefault.jpg"
    },
    {
        "id": "34Na4j8AVgA",
        "title": "Starboy",
        "artist": "The Weeknd ft. Daft Punk",
        "album": "Starboy",
        "duration": 230,
        "duration_formatted": "3:50",
        "thumbnail": "https://i.ytimg.com/vi/34Na4j8AVgA/hqdefault.jpg"
    },
    {
        "id": "fJ9rUzIMcZQ",
        "title": "Bohemian Rhapsody",
        "artist": "Queen",
        "album": "A Night at the Opera",
        "duration": 354,
        "duration_formatted": "5:54",
        "thumbnail": "https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg"
    },
    {
        "id": "YQHsXMglC9A",
        "title": "Hello",
        "artist": "Adele",
        "album": "25",
        "duration": 295,
        "duration_formatted": "4:55",
        "thumbnail": "https://i.ytimg.com/vi/YQHsXMglC9A/hqdefault.jpg"
    },
    {
        "id": "hT_nvWreIhg",
        "title": "Counting Stars",
        "artist": "OneRepublic",
        "album": "Native",
        "duration": 257,
        "duration_formatted": "4:17",
        "thumbnail": "https://i.ytimg.com/vi/hT_nvWreIhg/hqdefault.jpg"
    }
]

def is_valid_youtube_id(video_id: str) -> bool:
    """Validates YouTube video ID format to prevent arbitrary parameter injection."""
    return bool(video_id and YOUTUBE_ID_REGEX.match(video_id))

def format_duration(seconds: Optional[Union[int, float]]) -> str:
    """Safely formats seconds into M:SS."""
    if seconds is None:
        return "0:00"
    try:
        sec = float(seconds)
        if math.isnan(sec) or math.isinf(sec) or sec <= 0:
            return "0:00"
        total_sec = int(sec)
        m = total_sec // 60
        s = total_sec % 60
        return f"{m}:{s:02d}"
    except (ValueError, TypeError):
        return "0:00"

def clean_track_title(raw_title: str, default_artist: str) -> Tuple[str, str]:
    """Robust title and artist cleaner stripping noisy video annotations."""
    cleaned = TITLE_CLEANUP_REGEX.sub("", raw_title).strip()
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        artist = parts[0].strip()
        title = parts[1].strip()
        return (title or raw_title, artist or default_artist)
    return (cleaned or raw_title, default_artist)

def has_valid_netscape_cookies(path_or_content: Optional[Union[Path, str]]) -> bool:
    """Ensures a cookie file or string has actual tab-separated cookie entries, not just comments."""
    if not path_or_content:
        return False
    try:
        if isinstance(path_or_content, Path):
            if not path_or_content.exists() or path_or_content.stat().st_size < 10:
                return False
            with open(path_or_content, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        else:
            lines = path_or_content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                parts = stripped.split("\t")
                if len(parts) >= 7:
                    return True
    except Exception:
        pass
    return False

def resolve_stream_url(video_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Resolves direct audio stream URL with clean zero-cookie extraction & double-checked caching."""
    if not force_refresh:
        cached = STREAM_CACHE.get(video_id)
        if cached:
            return cached

    vlock = get_video_lock(video_id)
    acquired = vlock.acquire(timeout=15.0)
    if not acquired:
        raise TimeoutError(f"Extraction lock timeout for video {video_id}")

    try:
        if not force_refresh:
            cached = STREAM_CACHE.get(video_id)
            if cached:
                return cached

        with EXTRACTION_SEMAPHORE:
            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'quiet': True,
                'noplaylist': True,
                'no_warnings': True,
            }

            # Optional custom player clients if explicitly configured via environment
            clients_env = os.getenv("YOUTUBE_PLAYER_CLIENTS", "")
            player_clients = [c.strip() for c in clients_env.split(",") if c.strip()]
            if player_clients:
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': player_clients
                    }
                }

            # Support cookiefile ONLY if valid, authenticated cookies are explicitly provided
            cookie_path = None
            raw_cookies = os.getenv("YOUTUBE_COOKIES")
            raw_cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")
            if raw_cookies_b64 and not raw_cookies:
                try:
                    import base64
                    raw_cookies = base64.b64decode(raw_cookies_b64.strip()).decode("utf-8")
                except Exception as b64_err:
                    logger.warning(f"Failed to decode YOUTUBE_COOKIES_B64: {b64_err}")

            if not raw_cookies:
                try:
                    from cookies_data import EMBEDDED_COOKIES
                    if EMBEDDED_COOKIES and has_valid_netscape_cookies(EMBEDDED_COOKIES):
                        raw_cookies = EMBEDDED_COOKIES
                except ImportError:
                    pass

            if raw_cookies and has_valid_netscape_cookies(raw_cookies):
                cookie_path = Path("/tmp/youtube_cookies.txt") if os.getenv("VERCEL") else BASE_DIR / "cookies.txt"
                try:
                    with open(cookie_path, "w", encoding="utf-8") as cf:
                        cf.write(raw_cookies)
                except Exception as ce:
                    logger.warning(f"Failed to write cookie file: {ce}")
            elif (BASE_DIR / "cookies.txt").exists():
                candidate = BASE_DIR / "cookies.txt"
                if has_valid_netscape_cookies(candidate):
                    cookie_path = candidate

            if cookie_path and cookie_path.exists():
                ydl_opts['cookiefile'] = str(cookie_path)

            proxy_url = os.getenv("YOUTUBE_PROXY") or os.getenv("HTTP_PROXY")
            if proxy_url:
                ydl_opts['proxy'] = proxy_url

            info = None
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as first_err:
                logger.warning(f"Primary stream extraction failed for {video_id}: {first_err}. Retrying with bestaudio format.")
                retry_opts = dict(ydl_opts)
                retry_opts['format'] = 'bestaudio/best'
                try:
                    with yt_dlp.YoutubeDL(retry_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as second_err:
                    raise RuntimeError(f"Primary error: {first_err} | Retry error: {second_err}")

            stream_url = info.get("url") if info else None
            if not stream_url:
                raise ValueError(f"Could not extract stream URL for video {video_id}")

            raw_title = info.get("title", "Unknown Track")
            raw_artist = info.get("uploader") or info.get("channel") or "Unknown Artist"
            cleaned_title, cleaned_artist = clean_track_title(raw_title, raw_artist)

            result = {
                "stream_url": stream_url,
                "title": cleaned_title,
                "artist": cleaned_artist,
                "duration": info.get("duration"),
                "acodec": info.get("acodec", "aac"),
                "abr": info.get("abr", 128),
                "ext": info.get("ext", "m4a")
            }
            STREAM_CACHE.set(video_id, result)
            return result
    finally:
        vlock.release()

def search_tracks(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Searches YouTube using fast flat extraction with (query, limit) cache key."""
    q_clean = query.strip()
    if not q_clean:
        return []

    cache_key = (q_clean.lower(), limit)
    cached = SEARCH_CACHE.get(cache_key)
    if cached:
        return cached

    with EXTRACTION_SEMAPHORE:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'no_warnings': True,
            'noplaylist': True
        }

        tracks = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{limit}:{q_clean}", download=False)
            entries = res.get("entries", [])
            for entry in entries:
                vid_id = entry.get("id")
                if not vid_id:
                    continue

                thumbnails = entry.get("thumbnails") or []
                thumb = thumbnails[-1]["url"] if thumbnails else f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                duration = entry.get("duration")

                raw_title = entry.get("title", "Unknown Track")
                raw_artist = entry.get("channel") or entry.get("uploader") or "Unknown Artist"
                cleaned_title, cleaned_artist = clean_track_title(raw_title, raw_artist)

                tracks.append({
                    "id": vid_id,
                    "title": cleaned_title,
                    "artist": cleaned_artist,
                    "album": entry.get("album") or "Single",
                    "duration": duration,
                    "duration_formatted": format_duration(duration),
                    "thumbnail": thumb
                })

        SEARCH_CACHE.set(cache_key, tracks)
        return tracks

def fetch_automix_radio(video_id: str) -> List[Dict[str, Any]]:
    """Fetches YouTube Music Automix queue with intelligent fallback."""
    cached = RADIO_CACHE.get(video_id)
    if cached:
        return cached

    url = "https://music.youtube.com/youtubei/v1/next"
    payload = {
        "context": {
            "client": {
                "clientName": "WEB_REMIX",
                "clientVersion": "1.20241101.01.00",
                "hl": "en"
            }
        },
        "playlistId": f"RDAMVM{video_id}",
        "videoId": video_id,
        "enablePersistentPlaylistPanel": True
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT
    }

    tracks = []
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=(5.0, 10.0))
        if resp.status_code == 200:
            data = resp.json()
            tabs = data.get("contents", {}).get("singleColumnMusicWatchNextResultsRenderer", {})\
                       .get("tabbedRenderer", {}).get("watchNextTabbedResultsRenderer", {}).get("tabs", [])
            
            if not tabs:
                logger.warning(f"InnerTube response missing expected tabs for {video_id}.")
            else:
                panel = tabs[0].get("tabRenderer", {}).get("content", {})\
                               .get("musicQueueRenderer", {}).get("content", {})\
                               .get("playlistPanelRenderer", {})
                items = panel.get("contents", [])
                for it in items:
                    v = it.get("playlistPanelVideoRenderer")
                    if not v:
                        continue
                    item_id = v.get("videoId")
                    if not item_id:
                        continue

                    title_runs = v.get("title", {}).get("runs", [])
                    raw_title = title_runs[0].get("text", "Unknown Track") if title_runs else "Unknown Track"
                    
                    short_byline = v.get("shortBylineText", {}).get("runs", [])
                    raw_artist = short_byline[0].get("text", "Unknown Artist") if short_byline else "Unknown Artist"
                    cleaned_title, cleaned_artist = clean_track_title(raw_title, raw_artist)

                    dur_text = v.get("lengthText", {}).get("runs", [{}])[0].get("text", "")
                    sec = 0
                    if ":" in dur_text:
                        parts = dur_text.split(":")
                        if len(parts) == 2:
                            sec = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

                    thumbs = v.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{item_id}/hqdefault.jpg"

                    tracks.append({
                        "id": item_id,
                        "title": cleaned_title,
                        "artist": cleaned_artist,
                        "duration": sec,
                        "duration_formatted": dur_text or format_duration(sec),
                        "thumbnail": thumb_url
                    })

    except Exception as e:
        logger.error(f"Error fetching YouTube Music Automix for {video_id}: {e}")

    if len(tracks) < 5:
        logger.info(f"Automix yielded only {len(tracks)} tracks. Falling back to discovery search.")
        fallback_tracks = search_tracks("Best Trending Music Hits", limit=20)
        tracks = tracks + [t for t in fallback_tracks if t["id"] not in [x["id"] for x in tracks]]

    RADIO_CACHE.set(video_id, tracks)
    return tracks

def fetch_lyrics(track_title: str, artist_name: str, duration: Optional[float] = None) -> Dict[str, Any]:
    """Fetches synchronized lyrics from LRCLIB with 2-tier query resolution."""
    cache_key = (track_title.lower().strip(), artist_name.lower().strip())
    cached = LYRICS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    params: Dict[str, Any] = {
        "track_name": track_title,
        "artist_name": artist_name
    }
    if duration:
        params["duration"] = round(duration)

    lrclib_get_url = "https://lrclib.net/api/get"
    try:
        resp = HTTP_SESSION.get(lrclib_get_url, params=params, timeout=(2.0, 4.0))
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "syncedLyrics": data.get("syncedLyrics"),
                "plainLyrics": data.get("plainLyrics"),
                "instrumental": data.get("instrumental", False)
            }
            LYRICS_CACHE.set(cache_key, result)
            return result
    except Exception as e:
        logger.debug(f"Direct LRCLIB query failed: {e}")

    try:
        search_query = f"{track_title} {artist_name}".strip()
        search_res = HTTP_SESSION.get("https://lrclib.net/api/search", params={"q": search_query}, timeout=(2.0, 3.0))
        if search_res.status_code == 200:
            hits = search_res.json()
            if isinstance(hits, list) and hits:
                best = hits[0]
                result = {
                    "syncedLyrics": best.get("syncedLyrics"),
                    "plainLyrics": best.get("plainLyrics"),
                    "instrumental": best.get("instrumental", False)
                }
                LYRICS_CACHE.set(cache_key, result)
                return result
    except Exception as e:
        logger.debug(f"Fuzzy LRCLIB query failed: {e}")

    empty_result = {"syncedLyrics": None, "plainLyrics": None, "instrumental": False}
    LYRICS_CACHE.set(cache_key, empty_result)
    return empty_result

# System Health & Metrics Collection (Phase 1, Step 1.2)
def get_system_metrics() -> Dict[str, Any]:
    """Collect comprehensive system health and resource metrics."""
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        rss_mb = round(mem_info.rss / 1024 / 1024, 2)
        mem_percent = round(process.memory_percent(), 2)
        cpu_perc = round(process.cpu_percent(interval=0.05), 2)
    except Exception:
        rss_mb = 0.0
        mem_percent = 0.0
        cpu_perc = 0.0

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime_seconds": int(time.time() - SERVER_START_TIME),
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "memory": {
            "rss_mb": rss_mb,
            "percent": mem_percent
        },
        "cpu_percent": cpu_perc,
        "cache_stats": {
            "stream_cache": {
                "size": len(STREAM_CACHE._cache),
                "capacity": STREAM_CACHE.capacity
            },
            "radio_cache": {
                "size": len(RADIO_CACHE._cache),
                "capacity": RADIO_CACHE.capacity
            },
            "search_cache": {
                "size": len(SEARCH_CACHE._cache),
                "capacity": SEARCH_CACHE.capacity
            },
            "lyrics_cache": {
                "size": len(LYRICS_CACHE._cache),
                "capacity": LYRICS_CACHE.capacity
            }
        },
        "rate_limiter": {
            "tracked_clients": len(STREAM_RATE_LIMITER._clients)
        },
        "auth_storage": {
            "backend": user_store.get_backend_name(),
            "demo_account_enabled": user_store.is_demo_account_enabled(),
            "user_count": len(user_store.load_users())
        },
        "active_locks": len(VIDEO_LOCKS)
    }

# Application Request Handler with Security & Authentication Middleware
class SongBuddyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.request_start_time = time.time()
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def log_request(self, code='-', size='-'):
        """Enhanced structured request logging with latency tracking."""
        latency_ms = int((time.time() - getattr(self, "request_start_time", time.time())) * 1000)
        client_ip = self.get_client_ip()
        logger.info(
            f"HTTP {self.command} {self.path} -> {code} ({latency_ms}ms)",
            extra={
                "client_ip": client_ip,
                "method": self.command,
                "path": self.path,
                "status_code": code,
                "latency_ms": latency_ms,
                "user_agent": self.headers.get("User-Agent", "")
            }
        )

    def log_error(self, format, *args):
        """Structured error logging."""
        logger.error(f"HTTP error: {format % args}", extra={"client_ip": self.get_client_ip()})

    def get_client_ip(self) -> str:
        """Resolves client IP address, honoring X-Forwarded-For if behind reverse proxy."""
        xff = self.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return self.client_address[0]

    def end_headers(self):
        """Injects defense-in-depth security response headers (Phase 1, Step 1.3)."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

        cors_origin = os.getenv("CORS_ORIGIN", "*")
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Range")

        if os.getenv("USE_SSL", "false").lower() == "true":
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")

        super().end_headers()

    def do_OPTIONS(self):
        """CORS preflight request handling."""
        self.send_response(200)
        self.end_headers()

    def authenticate_request(self, required_scopes: Optional[list] = None) -> Optional[Dict[str, Any]]:
        """Validates JWT bearer token from Authorization header."""
        auth_header = self.headers.get("Authorization")
        token = extract_bearer_token(auth_header)

        require_auth = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

        if token:
            payload = auth_manager.verify_token(token)
            if payload:
                if required_scopes:
                    user_scopes = payload.get("scopes", [])
                    if not any(s in user_scopes for s in required_scopes):
                        return None
                return payload
            if require_auth:
                return None

        if not require_auth:
            return {"sub": "guest", "scopes": ["read", "stream"]}

        return None

    def send_auth_error(self, message: str = "Authentication required"):
        """Sends a structured 401 Unauthorized response."""
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("WWW-Authenticate", 'Bearer realm="SongBuddy Studio"')
        self.end_headers()
        body = json.dumps({"error": "unauthorized", "message": message}).encode("utf-8")
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json_error(self, status_code: int, message: str):
        """Sends a structured JSON error response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        body = json.dumps({"error": message}).encode("utf-8")
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json_response(self, data: Any, status: int = 200):
        """Sends a structured JSON success response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        """Handles authentication and account management endpoints."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self.get_client_ip()

        if os.getenv("ENVIRONMENT") != "test":
            allowed, rate_info = RATE_LIMITER.is_allowed(client_ip, endpoint="api_auth")
            if not allowed:
                self.send_response(429)
                self.send_header("Retry-After", str(rate_info.get("retry_after", 60)))
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(rate_info).encode("utf-8"))
                return

        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            post_data = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            self.send_json_error(400, "Invalid JSON body.")
            return

        if path == "/api/auth/register":
            try:
                validator = UserCredentialsValidator(**post_data)
            except ValidationError as ve:
                errors = [e["msg"] for e in ve.errors()]
                self.send_json_error(400, f"Validation error: {'; '.join(errors)}")
                return

            username = validator.username.lower()
            if username in USERS_DB:
                self.send_json_error(409, "Username already registered.")
                return

            USERS_DB[username] = {
                "password_hash": auth_manager.hash_password(validator.password),
                "name": post_data.get("name") or validator.username,
                "email": post_data.get("email") or f"{validator.username}@songbuddy.studio",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            save_users()
            logger.info(f"Registered new user '{username}' from {client_ip}")
            self.send_json_response({"message": "User registered successfully.", "username": username}, status=201)
            return

        elif path == "/api/auth/login":
            username = post_data.get("username", "").strip().lower()
            password = post_data.get("password", "")

            user = USERS_DB.get(username)
            if not user or not auth_manager.verify_password(password, user["password_hash"]):
                logger.warning(f"Failed login attempt for '{username}' from {client_ip}")
                self.send_json_error(401, "Invalid username or password.")
                return

            token = auth_manager.create_access_token(user_id=username, scopes=["read", "stream"])
            logger.info(f"User '{username}' logged in successfully from {client_ip}")
            self.send_json_response({
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "username": username,
                    "name": user.get("name", username),
                    "email": user.get("email", "")
                }
            })
            return

        elif path == "/api/auth/logout":
            auth_header = self.headers.get("Authorization")
            token = extract_bearer_token(auth_header)
            if token:
                auth_manager.revoke_token(token)
            self.send_json_response({"message": "Successfully logged out."})
            return

        self.send_error(404, "Endpoint not found.")

    def do_GET(self):
        """Handles API requests and static web client delivery."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        client_ip = self.get_client_ip()

        PUBLIC_ENDPOINTS = {"/", "/api/trending", "/api/health"}

        if path.startswith("/api/"):
            if os.getenv("ENVIRONMENT") != "test":
                allowed, rate_info = RATE_LIMITER.is_allowed(client_ip, endpoint=path)
                if not allowed:
                    self.send_response(429)
                    self.send_header("Retry-After", str(rate_info.get("retry_after", 60)))
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(rate_info).encode("utf-8"))
                    return

            if path not in PUBLIC_ENDPOINTS:
                user = self.authenticate_request()
                if not user:
                    self.send_auth_error("Valid Bearer token required to access this endpoint.")
                    return
                self.current_user = user

        # 0. API: Health Check (Phase 1, Step 1.2)
        if path == "/api/health":
            try:
                metrics = get_system_metrics()
                self.send_json_response(metrics)
                logger.debug("Health check succeeded")
            except Exception as e:
                logger.error("Health check failed", exc_info=True)
                self.send_error(503, f"Health check failed: {str(e)}")
            return

        # 1. API: Trending / Featured Tracks
        elif path == "/api/trending":
            self.send_json_response(FEATURED_TRACKS)
            return

        # 2. API: Search
        elif path == "/api/search":
            q = params.get("q", [""])[0]
            limit_raw = params.get("limit", ["16"])[0]
            try:
                validator = SearchQueryValidator(q=q, limit=int(limit_raw))
                results = search_tracks(validator.q, limit=validator.limit or 16)
                self.send_json_response(results)
            except ValidationError as ve:
                self.send_json_error(400, f"Search validation error: {ve.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"Search failure for '{q}': {e}")
                self.send_json_error(500, "Search query processing failure.")
            return

        # 3. API: Automix Radio / Up Next Recommendations
        elif path == "/api/radio":
            vid = params.get("id", [""])[0]
            try:
                validator = VideoIDValidator(id=vid)
                tracks = fetch_automix_radio(validator.id)
                self.send_json_response(tracks)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter format.")
            except Exception as e:
                logger.error(f"Radio failure for '{vid}': {e}")
                self.send_json_error(500, "Automix queue generation error.")
            return

        # 4. API: LRCLIB Synchronized Lyrics
        elif path == "/api/lyrics":
            title = params.get("track", params.get("title", [""]))[0]
            artist = params.get("artist", [""])[0]
            dur_str = params.get("duration", [""])[0]
            duration = float(dur_str) if dur_str else None

            try:
                validator = LyricsQueryValidator(title=title, artist=artist, duration=duration)
                lyrics = fetch_lyrics(validator.title, validator.artist, validator.duration)
                self.send_json_response(lyrics)
            except ValidationError as ve:
                self.send_json_error(400, f"Lyrics validation error: {ve.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"Lyrics resolution failure for '{title}': {e}")
                self.send_json_error(500, "Lyrics retrieval failure.")
            return

        # 5. API: Direct In-Memory Audio Streaming Proxy
        elif path == "/api/stream":
            vid = params.get("id", [""])[0]
            try:
                VideoIDValidator(id=vid)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter.")
                return

            try:
                stream_info = resolve_stream_url(vid)
                stream_url = stream_info["stream_url"]
            except Exception as e:
                logger.error(f"Failed to resolve stream for {vid}: {e}")
                self.send_json_error(502, f"Audio stream extraction failed for track {vid}: {str(e)}")
                return

            # On Vercel or when redirect requested: redirect to avoid serverless 10s function timeout
            if os.getenv("VERCEL") or params.get("redirect", ["false"])[0].lower() == "true":
                self.send_response(307)
                self.send_header("Location", stream_url)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                return

            req_headers = {"User-Agent": USER_AGENT}
            if "Range" in self.headers:
                req_headers["Range"] = self.headers["Range"]

            resp = None
            headers_sent = False
            try:
                max_retries = 1
                retry_count = 0
                while True:
                    resp = requests.get(stream_url, headers=req_headers, stream=True, timeout=(5.0, 20.0))
                    if resp.status_code == 403 and retry_count < max_retries:
                        resp.close()
                        retry_count += 1
                        STREAM_CACHE.pop(vid, None)
                        try:
                            stream_info = resolve_stream_url(vid, force_refresh=True)
                            stream_url = stream_info["stream_url"]
                            continue
                        except Exception as ref_err:
                            self.send_json_error(502, f"Failed to refresh CDN stream: {ref_err}")
                            return
                    break

                self.send_response(resp.status_code)
                for header in ["Content-Type", "Content-Range", "Content-Length", "Accept-Ranges"]:
                    if header in resp.headers:
                        self.send_header(header, resp.headers[header])
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                headers_sent = True

                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
                return

            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return
            except Exception as e:
                logger.error(f"Stream playback error for {vid}: {e}")
                if not headers_sent:
                    try:
                        self.send_json_error(500, f"Streaming proxy error: {str(e)}")
                    except Exception:
                        pass
                return
            finally:
                if resp is not None:
                    resp.close()

        # 6. Fallback: Static Frontend Files
        super().do_GET()

def start_server(port: int = 8000, host: str = "127.0.0.1", use_ssl: bool = False):
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, SongBuddyHandler)

    protocol = "http"
    if use_ssl:
        ssl_cert = os.getenv("SSL_CERT_PATH", "server-cert.pem")
        ssl_key = os.getenv("SSL_KEY_PATH", "server-key.pem")
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
            protocol = "https"
            logger.info(f"SSL/TLS enabled with certificate: {ssl_cert}")
        except FileNotFoundError:
            logger.error(f"SSL certificate files not found: {ssl_cert}, {ssl_key}. Reverting to HTTP.")
        except Exception as e:
            logger.error(f"SSL initialization failed: {e}. Reverting to HTTP.")

    if host == "0.0.0.0":
        logger.warning("[SECURITY WARNING] Server binding to 0.0.0.0 (all interfaces). Ensure reverse proxy & firewall isolation.")

    logger.info(f"SongBuddy Streaming Server listening at {protocol}://{host}:{port}/")
    logger.info(f"Serving static frontend from: {PUBLIC_DIR}")
    logger.info(f"Health check endpoint active at: {protocol}://{host}:{port}/api/health")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping SongBuddy Server...")
        httpd.server_close()
        RATE_LIMITER.stop()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    use_ssl = os.getenv("USE_SSL", "false").lower() == "true"
    start_server(port=port, host=host, use_ssl=use_ssl)
