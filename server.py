import os
import sys
import re
import ssl
import json
import time
import io
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
from library_store import library_store
from importer import import_playlist_by_url
from network_resilience import (
    cookie_pool_manager,
    fetch_sponsorblock_segments,
    inspect_cdn_stream_expiry,
    refresh_stream_token
)

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
    r"(?i)\s*[\(\[](?:official\s*(?:video|audio|music\s*video|lyric\s*video|visualizer|mv|performance)?|lyrics?|4k|8k|hd|remastered|audio|hq|full\s*song|video|lyric|special\s*version)[\)\]]"
)
CHANNEL_CLEANUP_REGEX = re.compile(
    r"(?i)\s*(?:VEVO|Official|Topic|Channel|Music|Records|Entertainment)$"
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
THUMB_COLOR_CACHE = BoundedLRUCache(capacity=300, default_ttl=24 * 3600)  # 24h TTL
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

def clean_track_title(raw_title: str, default_artist: str, query: str = "") -> Tuple[str, str]:
    """
    Intelligently extracts the true Song Title and Artist from noisy YouTube video titles.
    Preserves exact song names instead of swapping them with movie names or descriptors.
    """
    if not raw_title:
        return ("Unknown Track", default_artist or "Unknown Artist")

    raw = raw_title.strip()

    # 1. Clean bracketed boilerplates: [Official Video], (Audio), (Lyrics), [4K], etc.
    cleaned = TITLE_CLEANUP_REGEX.sub("", raw).strip()
    cleaned = re.sub(r"^[\"\'“‘]+|[\"\'”’]+$", "", cleaned).strip()
    # Normalize unicode dashes (en-dash, em-dash) to standard " - "
    cleaned = re.sub(r"\s*[–—]\s*", " - ", cleaned)

    # 2. Check for pipe delimiter: e.g. "Kesariya - Brahmāstra | Ranbir Kapoor... | Pritam | Arijit Singh"
    pipe_parts = [p.strip() for p in cleaned.split("|") if p.strip()]
    first_segment = pipe_parts[0] if pipe_parts else cleaned
    other_segments = pipe_parts[1:] if len(pipe_parts) > 1 else []

    # Clean channel / default artist
    clean_chan = CHANNEL_CLEANUP_REGEX.sub("", default_artist).strip() if default_artist else "Unknown Artist"
    is_label_channel = any(lbl in (default_artist or "").lower() for lbl in [
        "music", "records", "series", "vevo", "label", "entertainment", 
        "films", "company", "official", "bollywood", "studio", "tips", "zee"
    ])

    title = first_segment
    artist = clean_chan or default_artist or "Unknown Artist"

    # 3. Check for dash delimiter " - " in the first segment
    if " - " in first_segment:
        parts = [x.strip() for x in first_segment.split(" - ", 1)]
        p0 = TITLE_CLEANUP_REGEX.sub("", parts[0]).strip()
        p1 = TITLE_CLEANUP_REGEX.sub("", parts[1]).strip()

        p0_lower = p0.lower()
        p1_lower = p1.lower()
        chan_lower = clean_chan.lower()
        q_lower = query.lower().strip() if query else ""

        # Case A: Channel matches p0 -> p0 is Artist, p1 is Title
        if chan_lower and len(chan_lower) > 2 and (chan_lower in p0_lower or p0_lower in chan_lower):
            artist = p0
            title = p1
        # Case B: Channel matches p1 -> p1 is Artist, p0 is Title
        elif chan_lower and len(chan_lower) > 2 and (chan_lower in p1_lower or p1_lower in chan_lower):
            artist = p1
            title = p0
        # Case C: Query specifically matches p0 (e.g. query "kesariya", p0 is "Kesariya", p1 is "Brahmāstra")
        elif q_lower and q_lower in p0_lower and q_lower not in p1_lower:
            title = p0
            found_artist = None
            for seg in other_segments:
                seg_clean = TITLE_CLEANUP_REGEX.sub("", seg).strip()
                if any(w in seg.lower() for w in ["singh", "sharma", "pritam", "sheeran", "kapoor", "feat", "ft.", "ft "]):
                    found_artist = seg_clean
                    break
            if not found_artist and other_segments:
                found_artist = TITLE_CLEANUP_REGEX.sub("", other_segments[-1]).strip()
            artist = found_artist or (clean_chan if not is_label_channel else p1)
        # Case D: Query specifically matches p1 (e.g. query "starboy", p0 is "The Weeknd", p1 is "Starboy")
        elif q_lower and q_lower in p1_lower and q_lower not in p0_lower:
            title = p1
            artist = p0
        # Case E: p1 indicates a version or subtitle (e.g., "Kesariya - Film Version", "Numb - Live in Texas")
        elif any(sub in p1_lower for sub in ["film version", "remix", "acoustic", "live", "slowed", "reverb", "version", "mix", "cover"]):
            title = f"{p0} ({p1})" if any(x in p1_lower for x in ["version", "mix", "remix"]) else p0
            if other_segments:
                for seg in other_segments:
                    seg_clean = TITLE_CLEANUP_REGEX.sub("", seg).strip()
                    if not any(k in seg.lower() for k in ["4k", "8k", "video", "official", "full song"]):
                        artist = seg_clean
                        break
            if is_label_channel and not other_segments:
                artist = clean_chan
        else:
            # Default convention: Artist - Title
            artist = p0
            title = p1
    else:
        # No " - " in first segment: e.g. "Believer" or "Kesariya | Brahmāstra | Arijit Singh"
        title = first_segment
        if other_segments:
            for seg in other_segments:
                seg_clean = TITLE_CLEANUP_REGEX.sub("", seg).strip()
                if not any(k in seg.lower() for k in ["4k", "8k", "video", "official", "lyrics", "full song", "remastered"]):
                    artist = seg_clean
                    break

    # Clean double spaces, quotes, and punctuation
    title = re.sub(r"\s{2,}", " ", title).strip(" -|:,\"'")
    artist = re.sub(r"\s{2,}", " ", artist).strip(" -|:,\"'")
    artist = CHANNEL_CLEANUP_REGEX.sub("", artist).strip()

    # Deduplicate repeated featuring credits (e.g. "ft. Daft Punk ft. Daft Punk")
    title = re.sub(r"(?i)\b(ft\.?|feat\.?)\s+([A-Za-z0-9\s&,]+?)\s+\1\s+\2\b", r"\1 \2", title).strip()

    return (title or raw_title, artist or default_artist or "Unknown Artist")

def clean_primary_artist(artist_name: Optional[str]) -> str:
    """
    Extracts and normalizes the primary lead artist name for similarity & diversity logic.
    Strips out collaborators, featured artists, brackets, and noisy channel labels.
    """
    if not artist_name:
        return ""
    cleaned = CHANNEL_CLEANUP_REGEX.sub("", artist_name).strip()
    primary = re.split(r'[,&/]|(?:\s+[-–—]\s+)|\b(?:feat\.?|ft\.?|with|x|vs\.?)\b', cleaned, flags=re.IGNORECASE)[0]
    primary = re.sub(r'[\(\[\{].*?[\)\]\}]', '', primary)
    primary = re.sub(r'^[^\w]+|[^\w]+$', '', primary)
    return primary.strip().lower()

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

def get_cookie_health_status() -> Dict[str, Any]:
    """Automated probe inspecting YouTube session cookies, pool rotation, and expiry horizons."""
    return cookie_pool_manager.get_health_metrics()

def resolve_stream_fallback(video_id: str, quality: str = "high") -> Optional[Dict[str, Any]]:
    """Secondary audio resolver querying high-availability Piped API and Invidious public instances."""
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.privacy.com.de",
        "https://piped-api.lunar.icu"
    ]
    for instance in piped_instances:
        try:
            resp = HTTP_SESSION.get(f"{instance}/streams/{video_id}", timeout=(3.0, 5.0))
            if resp.status_code == 200:
                data = resp.json()
                audio_streams = data.get("audioStreams", [])
                if audio_streams:
                    if quality == "low":
                        audio_streams.sort(key=lambda s: s.get("bitrate", 0))
                    else:
                        audio_streams.sort(key=lambda s: s.get("bitrate", 0), reverse=True)
                    best = audio_streams[0]
                    raw_title = data.get("title", "Unknown Track")
                    raw_uploader = data.get("uploader", "Unknown Artist")
                    cleaned_title, cleaned_artist = clean_track_title(raw_title, raw_uploader)
                    logger.info(f"Resolved secondary fallback audio via Piped for video {video_id}")
                    return {
                        "stream_url": best["url"],
                        "title": cleaned_title,
                        "artist": cleaned_artist,
                        "duration": data.get("duration"),
                        "acodec": best.get("codec", "opus"),
                        "abr": (best.get("bitrate", 128000) // 1000) if best.get("bitrate") else 128,
                        "ext": best.get("format", "webm"),
                        "source": "piped_fallback"
                    }
        except Exception as pe:
            logger.debug(f"Piped fallback via {instance} failed: {pe}")
            continue

    # Second fallback: Invidious API
    invidious_instances = [
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de"
    ]
    for instance in invidious_instances:
        try:
            resp = HTTP_SESSION.get(f"{instance}/api/v1/videos/{video_id}", timeout=(3.0, 5.0))
            if resp.status_code == 200:
                data = resp.json()
                adaptive = data.get("adaptiveFormats", [])
                audio_formats = [f for f in adaptive if "audio" in f.get("type", "").lower()]
                if audio_formats:
                    audio_formats.sort(key=lambda f: int(f.get("bitrate", 0)), reverse=(quality != "low"))
                    best = audio_formats[0]
                    cleaned_title, cleaned_artist = clean_track_title(data.get("title", ""), data.get("author", ""))
                    logger.info(f"Resolved secondary fallback audio via Invidious for video {video_id}")
                    return {
                        "stream_url": best["url"],
                        "title": cleaned_title,
                        "artist": cleaned_artist,
                        "duration": data.get("lengthSeconds"),
                        "acodec": best.get("audioEncoding", "opus"),
                        "abr": 128,
                        "ext": "webm",
                        "source": "invidious_fallback"
                    }
        except Exception:
            continue

    return None

def resolve_stream_url(video_id: str, quality: str = "high", force_refresh: bool = False) -> Dict[str, Any]:
    """Resolves direct audio stream URL with clean zero-cookie extraction, quality selection & secondary fallbacks."""
    cache_key = f"{video_id}_{quality}"
    if not force_refresh:
        cached = STREAM_CACHE.get(cache_key)
        if cached:
            return cached

    vlock = get_video_lock(video_id)
    acquired = vlock.acquire(timeout=15.0)
    if not acquired:
        raise TimeoutError(f"Extraction lock timeout for video {video_id}")

    try:
        if not force_refresh:
            cached = STREAM_CACHE.get(cache_key)
            if cached:
                return cached

        with EXTRACTION_SEMAPHORE:
            url = f"https://www.youtube.com/watch?v={video_id}"

            # Audio format specification according to selected quality tier
            if quality == "low":
                audio_fmt = "bestaudio[abr<=80]/bestaudio[ext=webm]/bestaudio"
            elif quality == "high":
                audio_fmt = "bestaudio[abr>=128]/bestaudio/best"
            else:
                audio_fmt = "bestaudio/best"

            # Support cookiefile managed dynamically by CookiePoolManager
            cookie_path = cookie_pool_manager.get_active_cookie_file()

            proxy_url = os.getenv("YOUTUBE_PROXY") or os.getenv("HTTP_PROXY")
            info = None
            last_err = None

            # Attempt 1: Modern mobile/visionos clients (visionos, android) WITHOUT cookies.
            try:
                opts_tier1 = {
                    'format': audio_fmt,
                    'quiet': True,
                    'noplaylist': True,
                    'no_warnings': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['visionos', 'android']
                        }
                    }
                }
                if proxy_url:
                    opts_tier1['proxy'] = proxy_url
                with yt_dlp.YoutubeDL(opts_tier1) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e1:
                last_err = e1
                logger.warning(f"Tier 1 (visionos/android) extraction failed for {video_id}: {e1}")

            # Attempt 2: If Tier 1 failed and cookies are available, try cookie-supporting clients
            if not info and cookie_path and cookie_path.exists():
                try:
                    opts_tier2 = {
                        'format': audio_fmt,
                        'quiet': True,
                        'noplaylist': True,
                        'no_warnings': True,
                        'cookiefile': str(cookie_path),
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['web_safari', 'tv', 'web']
                            }
                        }
                    }
                    if proxy_url:
                        opts_tier2['proxy'] = proxy_url
                    with yt_dlp.YoutubeDL(opts_tier2) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e2:
                    last_err = e2
                    logger.warning(f"Tier 2 (authenticated) extraction failed for {video_id}: {e2}")

            # Attempt 3: General fallback without client restrictions
            if not info:
                try:
                    opts_tier3 = {
                        'format': audio_fmt,
                        'quiet': True,
                        'noplaylist': True,
                        'no_warnings': True,
                    }
                    if cookie_path and cookie_path.exists():
                        opts_tier3['cookiefile'] = str(cookie_path)
                    if proxy_url:
                        opts_tier3['proxy'] = proxy_url
                    with yt_dlp.YoutubeDL(opts_tier3) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e3:
                    last_err = e3
                    logger.warning(f"Tier 3 extraction failed for {video_id}: {e3}")

            # Attempt 4: High-Availability Secondary Resolvers (Piped / Invidious)
            if not info:
                logger.warning(f"All yt-dlp tiers failed for {video_id}. Attempting secondary audio resolvers...")
                info = resolve_stream_fallback(video_id, quality=quality)
                if info:
                    STREAM_CACHE.set(cache_key, info)
                    return info

            if not info:
                if "429" in str(last_err) or "bot" in str(last_err).lower():
                    cookie_pool_manager.report_error(429)
                raise RuntimeError(f"All extraction tiers and secondary resolvers failed: {last_err}")

            cookie_pool_manager.report_success()

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
            STREAM_CACHE.set(cache_key, result)
            return result
    finally:
        vlock.release()

def search_tracks(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Searches YouTube using fast flat extraction with intelligent title cleaning and candidate ranking."""
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
        fetch_count = min(limit + 8, 25)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{fetch_count}:{q_clean}", download=False)
            entries = res.get("entries", [])
            for entry in entries:
                vid_id = entry.get("id")
                if not vid_id:
                    continue

                duration = entry.get("duration")
                # Filter out teaser clips under 35 seconds (unless requested in query)
                if duration and duration < 35 and "teaser" not in q_clean.lower() and "short" not in q_clean.lower():
                    continue

                thumbnails = entry.get("thumbnails") or []
                thumb = thumbnails[-1]["url"] if thumbnails else f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                if "hq720.jpg" in thumb:
                    thumb = thumb.replace("hq720.jpg", "hqdefault.jpg")

                raw_title = entry.get("title", "Unknown Track")
                raw_artist = entry.get("channel") or entry.get("uploader") or "Unknown Artist"
                cleaned_title, cleaned_artist = clean_track_title(raw_title, raw_artist, query=q_clean)

                # Attempt to extract album / soundtrack if indicated
                album = entry.get("album")
                if not album:
                    album_match = re.search(r'(?i)\b(?:from|soundtrack|film)\s+["\']?([^"\'|()]+)["\']?', raw_title)
                    album = album_match.group(1).strip() if album_match else "Single"

                tracks.append({
                    "id": vid_id,
                    "title": cleaned_title,
                    "artist": cleaned_artist,
                    "album": album or "Single",
                    "duration": duration,
                    "duration_formatted": format_duration(duration),
                    "thumbnail": thumb
                })

                if len(tracks) >= limit:
                    break

        SEARCH_CACHE.set(cache_key, tracks)
        return tracks

def fetch_automix_radio(video_id: str, seed_artist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches YouTube Music Automix queue with artist diversity & related recommendations."""
    norm_seed_artist = clean_primary_artist(seed_artist)
    cache_key = f"{video_id}:{norm_seed_artist}" if norm_seed_artist else video_id
    cached = RADIO_CACHE.get(cache_key)
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

    raw_tracks = []
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

                    raw_tracks.append({
                        "id": item_id,
                        "title": cleaned_title,
                        "artist": cleaned_artist,
                        "duration": sec,
                        "duration_formatted": dur_text or format_duration(sec),
                        "thumbnail": thumb_url
                    })

    except Exception as e:
        logger.error(f"Error fetching YouTube Music Automix for {video_id}: {e}")

    # Exclude seed video itself from recommendations so autoplay won't immediately repeat the current track
    seen_ids = {video_id}
    deduped_raw = []
    for t in raw_tracks:
        tid = t.get("id")
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            deduped_raw.append(t)

    # Separate into related artists vs. same artist
    same_artist_tracks: List[Dict[str, Any]] = []
    related_artist_tracks: List[Dict[str, Any]] = []

    for t in deduped_raw:
        art = clean_primary_artist(t.get("artist", ""))
        if norm_seed_artist and art == norm_seed_artist:
            same_artist_tracks.append(t)
        else:
            related_artist_tracks.append(t)

    # Intelligent related discovery fallback:
    # If related artists count is low, query for musically similar artists rather than the same singer!
    if len(related_artist_tracks) < 10:
        logger.info(f"Automix yielded only {len(related_artist_tracks)} related tracks. Fetching musically related discovery mix.")
        query = f"{seed_artist} radio mix similar songs" if seed_artist else "Best Trending Music Hits"
        try:
            fallback_tracks = search_tracks(query, limit=20)
            for ft in fallback_tracks:
                fid = ft.get("id")
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    f_art = clean_primary_artist(ft.get("artist", ""))
                    if norm_seed_artist and f_art == norm_seed_artist:
                        same_artist_tracks.append(ft)
                    else:
                        related_artist_tracks.append(ft)
        except Exception as fb_err:
            logger.warning(f"Discovery search fallback failed: {fb_err}")

    # Diversity Interleaving & Capping:
    # 1. Enforce max 2 tracks per related artist in primary queue
    artist_counts: Dict[str, int] = {}
    capped_related: List[Dict[str, Any]] = []
    overflow_related: List[Dict[str, Any]] = []
    for t in related_artist_tracks:
        art = clean_primary_artist(t.get("artist", "")) or "unknown"
        cnt = artist_counts.get(art, 0)
        if cnt < 2:
            artist_counts[art] = cnt + 1
            capped_related.append(t)
        else:
            overflow_related.append(t)

    # 2. Interleave so no two adjacent songs are by the same artist
    interleaved: List[Dict[str, Any]] = []
    pool = list(capped_related)
    while pool:
        last_art = clean_primary_artist(interleaved[-1].get("artist", "")) if interleaved else None
        found_idx = -1
        for idx, cand in enumerate(pool):
            cand_art = clean_primary_artist(cand.get("artist", ""))
            if last_art is None or cand_art != last_art:
                found_idx = idx
                break
        if found_idx != -1:
            interleaved.append(pool.pop(found_idx))
        else:
            interleaved.append(pool.pop(0))

    # 3. Insert AT MOST ONE track by the seed singer at index 3 (or index 2)
    # The immediate top recommendations (indexes 0, 1, 2) are guaranteed to be DIFFERENT related artists!
    final_tracks: List[Dict[str, Any]] = list(interleaved)
    if same_artist_tracks:
        one_same = same_artist_tracks[0]
        insert_pos = min(3, len(final_tracks))
        final_tracks.insert(insert_pos, one_same)

    # 4. Append remaining overflow or later same-artist tracks at the tail (after index 20)
    for extra in (overflow_related + same_artist_tracks[1:]):
        if len(final_tracks) >= 50:
            break
        final_tracks.append(extra)

    RADIO_CACHE.set(cache_key, final_tracks)
    return final_tracks

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

def parse_lrc_to_cues(lrc_text: Optional[str]) -> List[Dict[str, Any]]:
    """Parses standard LRC synced lyrics into millisecond-accurate timeline cues."""
    if not lrc_text:
        return []
    cues = []
    regex = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
    for line in lrc_text.splitlines():
        match = regex.match(line.strip())
        if match:
            mins = int(match.group(1))
            secs = int(match.group(2))
            ms_str = match.group(3)
            ms = float(f"0.{ms_str}")
            total_sec = round(mins * 60 + secs + ms, 3)
            text = match.group(4).strip()
            if text:
                cues.append({
                    "time": total_sec,
                    "text": text
                })
    cues.sort(key=lambda x: x["time"])
    for i in range(len(cues)):
        if i < len(cues) - 1:
            cues[i]["duration"] = round(cues[i + 1]["time"] - cues[i]["time"], 2)
        else:
            cues[i]["duration"] = 5.0
    return cues

def analyze_karaoke_profile(track_title: str, artist_name: str, duration: Optional[float] = None) -> Dict[str, Any]:
    """Analyzes track structure for karaoke readiness and vocal cancellation parameters."""
    lyrics_data = fetch_lyrics(track_title, artist_name, duration)
    cues = parse_lrc_to_cues(lyrics_data.get("syncedLyrics"))
    is_instrumental = lyrics_data.get("instrumental", False) or len(cues) == 0
    first_vocal_time = cues[0]["time"] if cues else 0.0
    total_lyric_lines = len(cues)
    return {
        "status": "ready",
        "title": track_title,
        "artist": artist_name,
        "instrumental": is_instrumental,
        "has_synced_karaoke": len(cues) > 0,
        "total_cues": total_lyric_lines,
        "first_vocal_timestamp": first_vocal_time,
        "intro_countdown_seconds": round(max(0.0, first_vocal_time), 2),
        "vocal_cancellation": {
            "dsp_profile": "center_channel_phase_inversion",
            "vocal_frequency_band_hz": [140, 7500],
            "bass_preservation_cutoff_hz": 120,
            "air_preservation_cutoff_hz": 8000,
            "estimated_attenuation_db": -24.0
        },
        "lead_vocal_difficulty": "medium" if total_lyric_lines > 25 else "easy",
        "cues": cues[:15]
    }

def extract_thumbnail_color(video_id: str, thumb_url: Optional[str] = None) -> Dict[str, Any]:
    """Extracts dominant vibrant accent RGB from track thumbnail using Pillow."""
    cached = THUMB_COLOR_CACHE.get(video_id)
    if cached:
        return cached

    url = thumb_url or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    try:
        from PIL import Image
        req_headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=req_headers, timeout=(3.0, 5.0))
        if resp.status_code != 200 and "hqdefault" not in url:
            url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            resp = requests.get(url, headers=req_headers, timeout=(3.0, 5.0))

        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            w, h = img.size
            if "ytimg.com" in url or "youtube.com" in url:
                img = img.crop((0, int(h * 0.125), w, int(h * 0.875)))

            img = img.resize((32, 32), Image.Resampling.LANCZOS)
            pixels = [img.getpixel((x, y)) for y in range(32) for x in range(32)]

            best = None
            max_score = -1.0
            r_sum = g_sum = b_sum = count = 0

            for r, g, b in pixels:
                delta = max(r, g, b) - min(r, g, b)
                sum_val = r + g + b
                r_sum += r
                g_sum += g
                b_sum += b
                count += 1
                if 40 < sum_val < 720 and delta > 18:
                    score = delta * (1.0 + max(r, g, b) / 255.0)
                    if score > max_score:
                        max_score = score
                        best = (r, g, b)

            if not best and count > 0:
                best = (int(r_sum / count), int(g_sum / count), int(b_sum / count))

            if not best:
                best = (255, 255, 255)

            r, g, b = best
            if (r + g + b) < 90:
                boost = 110.0 / max(1.0, float(r + g + b))
                r = min(255, int(r * boost))
                g = min(255, int(g * boost))
                b = min(255, int(b * boost))

            result = {
                "r": r,
                "g": g,
                "b": b,
                "hex": f"#{r:02x}{g:02x}{b:02x}"
            }
            THUMB_COLOR_CACHE.set(video_id, result)
            return result
    except Exception as e:
        logger.warning(f"Thumbnail color extraction error for {video_id}: {e}")

    default_color = {"r": 255, "g": 255, "b": 255, "hex": "#ffffff"}
    THUMB_COLOR_CACHE.set(video_id, default_color)
    return default_color

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
        "cookie_health": get_cookie_health_status(),
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

    def handle_subsonic_request(self, path: str, params: Dict[str, List[str]], http_method: str = "GET"):
        """Dispatches OpenSubsonic requests to the OpenSubsonic controller or streaming proxy."""
        method_name = path[len("/rest/"):].strip("/")
        is_json = params.get("f", ["xml"])[0].lower() == "json"

        # 1. Media streaming endpoint
        if method_name in ("stream", "stream.view"):
            from opensubsonic import authenticate_subsonic, build_subsonic_response
            is_auth, user, err = authenticate_subsonic(params, USERS_DB)
            if not is_auth:
                body, ctype, status = build_subsonic_response(error=(40, err or "Wrong username or password"), is_json=is_json)
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
                return

            vid = params.get("id", [""])[0]
            if not vid:
                body, ctype, status = build_subsonic_response(error=(10, "Required parameter 'id' is missing"), is_json=is_json)
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
                return

            try:
                stream_info = resolve_stream_url(vid, quality="high")
                stream_url = stream_info["stream_url"]
            except Exception as e:
                logger.error(f"OpenSubsonic stream resolution failure for {vid}: {e}")
                body, ctype, status = build_subsonic_response(error=(70, f"Audio stream unavailable: {str(e)}"), is_json=is_json)
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
                return

            # Always redirect on Vercel or when redirect requested
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
            try:
                resp = requests.get(stream_url, headers=req_headers, stream=True, timeout=(5.0, 20.0))
                self.send_response(resp.status_code)
                for header in ["Content-Type", "Content-Range", "Content-Length", "Accept-Ranges"]:
                    if header in resp.headers:
                        self.send_header(header, resp.headers[header])
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
                return
            except Exception as e:
                logger.error(f"OpenSubsonic stream proxy error for {vid}: {e}")
                return
            finally:
                if resp is not None:
                    resp.close()

        # 2. Cover art retrieval
        if method_name in ("getCoverArt", "getCoverArt.view"):
            vid = params.get("id", [""])[0]
            thumb_url = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "https://songbuddy-swart.vercel.app/logo.png"
            self.send_response(307)
            self.send_header("Location", thumb_url)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            return

        # 3. All other OpenSubsonic endpoints
        from opensubsonic import OpenSubsonicController
        controller = OpenSubsonicController(sys.modules[__name__])
        body, ctype, status = controller.handle_request(method_name, params, http_method=http_method)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle_subsonic_post(self, path: str, params: Dict[str, List[str]], body_bytes: bytes):
        """Handles OpenSubsonic POST requests (form-encoded and JSON payloads)."""
        method_name = path[len("/rest/"):].strip("/")
        post_data = {}
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in content_type:
            try:
                body_params = urllib.parse.parse_qs(body_bytes.decode("utf-8"))
                for k, v in body_params.items():
                    params[k] = v
            except Exception:
                pass
        elif "application/json" in content_type:
            try:
                post_data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                pass

        from opensubsonic import OpenSubsonicController
        controller = OpenSubsonicController(sys.modules[__name__])
        body, ctype, status = controller.handle_request(method_name, params, http_method="POST", post_body=post_data)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
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

        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        # 0. OpenSubsonic POST Gateway
        if path.startswith("/rest/"):
            params = urllib.parse.parse_qs(parsed.query)
            if os.getenv("ENVIRONMENT") != "test":
                allowed, rate_info = RATE_LIMITER.is_allowed(client_ip, endpoint="rest_subsonic")
                if not allowed:
                    self.send_response(429)
                    self.send_header("Retry-After", str(rate_info.get("retry_after", 60)))
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(rate_info).encode("utf-8"))
                    return
            self.handle_subsonic_post(path, params, body_bytes)
            return

        if os.getenv("ENVIRONMENT") != "test":
            allowed, rate_info = RATE_LIMITER.is_allowed(client_ip, endpoint="api_auth")
            if not allowed:
                self.send_response(429)
                self.send_header("Retry-After", str(rate_info.get("retry_after", 60)))
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(rate_info).encode("utf-8"))
                return

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

        # 1. Custom User Playlists (Create / Update)
        elif path == "/api/user/playlists":
            user = self.authenticate_request() or {"sub": "guest"}
            pl = library_store.save_user_playlist(user.get("sub", "guest"), post_data)
            self.send_json_response(pl, status=200)
            return

        # 2. Custom User Playlists (Delete)
        elif path == "/api/user/playlists/delete":
            user = self.authenticate_request() or {"sub": "guest"}
            pl_id = post_data.get("id", "")
            success = library_store.delete_user_playlist(user.get("sub", "guest"), pl_id)
            self.send_json_response({"success": success, "deleted_id": pl_id}, status=200)
            return

        # 3. User Favorites (Toggle / Add / Remove)
        elif path == "/api/user/favorites":
            user = self.authenticate_request() or {"sub": "guest"}
            track = post_data.get("track", post_data)
            remove = bool(post_data.get("remove", False))
            res = library_store.toggle_user_favorite(user.get("sub", "guest"), track, remove=remove)
            self.send_json_response(res, status=200)
            return

        # 4. User Listening History (Record Play)
        elif path == "/api/user/history":
            user = self.authenticate_request() or {"sub": "guest"}
            track = post_data.get("track", post_data)
            res = library_store.record_user_play(user.get("sub", "guest"), track)
            self.send_json_response(res, status=200)
            return

        # 5. Bulk Playlist Importer (Spotify, YouTube, Apple Music)
        elif path == "/api/import/playlist":
            url = post_data.get("url", "").strip()
            if not url:
                self.send_json_error(400, "Missing playlist URL parameter.")
                return
            try:
                imported = import_playlist_by_url(url)
                self.send_json_response(imported, status=200)
            except Exception as ie:
                logger.error(f"Failed to import playlist from {url}: {ie}")
                self.send_json_error(400, f"Playlist import failure: {str(ie)}")
            return

        # 6. Anti-Bot: Dynamic Cookie Session Rotation
        elif path == "/api/cookies/rotate":
            rotated = cookie_pool_manager.rotate_to_next(reason="api_manual_trigger")
            self.send_json_response({"success": rotated, "metrics": cookie_pool_manager.get_health_metrics()})
            return

        # 7. Smart Stream CDN Token Refresh
        elif path == "/api/stream/refresh":
            vid = post_data.get("id", "")
            offset = int(post_data.get("offset", 0))
            try:
                VideoIDValidator(id=vid)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter.")
                return
            try:
                refreshed = refresh_stream_token(vid, sys.modules[__name__], byte_offset=offset)
                self.send_json_response(refreshed)
            except Exception as e:
                logger.error(f"Failed to refresh stream token for {vid}: {e}")
                self.send_json_error(500, f"Stream token refresh failed: {str(e)}")
            return

        self.send_error(404, "Endpoint not found.")

    def do_DELETE(self):
        """Handles RESTful DELETE requests for user resources."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/user/playlists":
            user = self.authenticate_request() or {"sub": "guest"}
            pl_id = params.get("id", [""])[0]
            if not pl_id:
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len > 0:
                    try:
                        b = json.loads(self.rfile.read(content_len).decode("utf-8"))
                        pl_id = b.get("id", "")
                    except Exception:
                        pass
            success = library_store.delete_user_playlist(user.get("sub", "guest"), pl_id)
            self.send_json_response({"success": success, "deleted_id": pl_id})
            return

        self.send_error(404, "Endpoint not found.")

    def do_GET(self):
        """Handles API requests and static web client delivery."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        client_ip = self.get_client_ip()
        # OpenSubsonic API Gateway (/rest/<method> or /rest/<method>.view)
        if path.startswith("/rest/"):
            if os.getenv("ENVIRONMENT") != "test":
                allowed, rate_info = RATE_LIMITER.is_allowed(client_ip, endpoint="rest_subsonic")
                if not allowed:
                    self.send_response(429)
                    self.send_header("Retry-After", str(rate_info.get("retry_after", 60)))
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(rate_info).encode("utf-8"))
                    return
            self.handle_subsonic_request(path, params, http_method="GET")
            return

        PUBLIC_ENDPOINTS = {
            "/", "/api/trending", "/api/health", "/api/health/cookies", "/api/search", "/api/radio",
            "/api/lyrics", "/api/lyrics/sse", "/api/karaoke", "/api/stream", "/api/stream/refresh",
            "/api/sponsorblock", "/api/cookies/rotate",
            "/api/user/playlists", "/api/user/favorites", "/api/user/history",
            "/api/user/smart-playlists", "/api/import/playlist"
        }

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
            else:
                self.current_user = self.authenticate_request() or {"sub": "guest"}

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

        # 0a. API: Cookie Pool Health Heartbeat
        elif path == "/api/health/cookies":
            self.send_json_response(cookie_pool_manager.get_health_metrics())
            return

        # 0b. API: SponsorBlock Auto-Skip Segments
        elif path == "/api/sponsorblock":
            vid = params.get("id", [""])[0]
            try:
                VideoIDValidator(id=vid)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter format.")
                return
            segments = fetch_sponsorblock_segments(vid)
            self.send_json_response(segments)
            return

        # 0c. API: Smart Stream Token Refresh & Byte Resumption
        elif path == "/api/stream/refresh":
            vid = params.get("id", [""])[0]
            offset_str = params.get("offset", ["0"])[0]
            try:
                VideoIDValidator(id=vid)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter format.")
                return
            try:
                byte_offset = int(offset_str)
            except (ValueError, TypeError):
                byte_offset = 0
            try:
                refreshed = refresh_stream_token(vid, sys.modules[__name__], byte_offset=byte_offset)
                self.send_json_response(refreshed)
            except Exception as e:
                logger.error(f"Failed to refresh stream token for {vid}: {e}")
                self.send_json_error(500, f"Stream token refresh failed: {str(e)}")
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
            artist = params.get("artist", [""])[0]
            try:
                validator = VideoIDValidator(id=vid)
                tracks = fetch_automix_radio(validator.id, seed_artist=artist)
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

        # 4a. API: Real-Time Timeline & Lyrics SSE Stream (Server-Sent Events)
        elif path == "/api/lyrics/sse":
            title = params.get("track", params.get("title", [""]))[0]
            artist = params.get("artist", [""])[0]
            dur_str = params.get("duration", [""])[0]
            duration = float(dur_str) if dur_str else None

            try:
                validator = LyricsQueryValidator(title=title, artist=artist, duration=duration)
                lyrics = fetch_lyrics(validator.title, validator.artist, validator.duration)
                cues = parse_lrc_to_cues(lyrics.get("syncedLyrics"))

                self.close_connection = True
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-transform")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                # Event 1: Manifest with metadata and millisecond cues
                init_payload = json.dumps({
                    "title": validator.title,
                    "artist": validator.artist,
                    "instrumental": lyrics.get("instrumental", False),
                    "total_cues": len(cues),
                    "cues": cues
                })
                self.wfile.write(f"event: manifest\ndata: {init_payload}\n\n".encode("utf-8"))
                self.wfile.flush()

                # Event 2: Sync pulse
                sync_payload = json.dumps({
                    "status": "synchronized",
                    "cues_available": len(cues) > 0,
                    "mode": "realtime_sse"
                })
                self.wfile.write(f"event: sync\ndata: {sync_payload}\n\n".encode("utf-8"))
                self.wfile.flush()
            except ValidationError as ve:
                self.send_json_error(400, f"Lyrics validation error: {ve.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"SSE Lyrics stream failure for '{title}': {e}")
                self.send_json_error(500, "SSE lyrics stream error.")
            return

        # 4b. API: Dynamic Karaoke & Instrumental Analysis
        elif path == "/api/karaoke":
            title = params.get("track", params.get("title", [""]))[0]
            artist = params.get("artist", [""])[0]
            dur_str = params.get("duration", [""])[0]
            duration = float(dur_str) if dur_str else None

            try:
                validator = LyricsQueryValidator(title=title, artist=artist, duration=duration)
                profile = analyze_karaoke_profile(validator.title, validator.artist, validator.duration)
                self.send_json_response(profile)
            except ValidationError as ve:
                self.send_json_error(400, f"Karaoke validation error: {ve.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"Karaoke analysis failure for '{title}': {e}")
                self.send_json_error(500, "Karaoke profile generation failed.")
            return

        # 4b. API: Dynamic Thumbnail Accent Color Probe
        elif path == "/api/thumb_color":
            vid = params.get("id", [""])[0]
            thumb = params.get("url", [""])[0]
            try:
                validator = VideoIDValidator(id=vid)
                color = extract_thumbnail_color(validator.id, thumb or None)
                self.send_json_response(color)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter format.")
            except Exception as e:
                logger.error(f"Thumb color failure for '{vid}': {e}")
                self.send_json_error(500, "Color extraction error.")
            return

        # 5. API: Direct In-Memory Audio Streaming Proxy
        elif path == "/api/stream":
            vid = params.get("id", [""])[0]
            quality = params.get("quality", ["high"])[0].lower()
            if quality not in ("low", "high", "auto"):
                quality = "high"

            try:
                VideoIDValidator(id=vid)
            except ValidationError:
                self.send_json_error(400, "Invalid YouTube video ID parameter.")
                return

            try:
                stream_info = resolve_stream_url(vid, quality=quality)
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
                        STREAM_CACHE.pop(f"{vid}_{quality}", None)
                        try:
                            stream_info = resolve_stream_url(vid, quality=quality, force_refresh=True)
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

        # 6. User Library: Custom Playlists
        elif path == "/api/user/playlists":
            user = getattr(self, "current_user", None) or {"sub": "guest"}
            playlists = library_store.get_user_playlists(user.get("sub", "guest"))
            self.send_json_response(playlists)
            return

        # 7. User Library: Favorites
        elif path == "/api/user/favorites":
            user = getattr(self, "current_user", None) or {"sub": "guest"}
            favorites = library_store.get_user_favorites(user.get("sub", "guest"))
            self.send_json_response(favorites)
            return

        # 8. User Library: Listening History
        elif path == "/api/user/history":
            user = getattr(self, "current_user", None) or {"sub": "guest"}
            history = library_store.get_user_history(user.get("sub", "guest"))
            self.send_json_response(history)
            return

        # 9. User Library: Dynamic Smart Playlists ("On Repeat", "Recently Played", "Jump Back In")
        elif path == "/api/user/smart-playlists":
            user = getattr(self, "current_user", None) or {"sub": "guest"}
            smart = library_store.get_smart_playlists(user.get("sub", "guest"))
            self.send_json_response(smart)
            return

        # 10. Fallback: Static Frontend Files
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
