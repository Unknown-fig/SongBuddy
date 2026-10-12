import re
import time
import base64
import logging
import threading
from typing import List, Dict, Any, Optional
import requests
import yt_dlp

try:
    from config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET
except ImportError:
    import os
    SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
    SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

logger = logging.getLogger("songbuddy.recommender")


def format_duration(seconds: Optional[int]) -> str:
    """Formats numeric seconds into mm:ss display string."""
    if not seconds or seconds <= 0:
        return "0:00"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"


class RecommendationEngine:
    """
    Hybrid recommendation engine combining Spotify acoustic graphs,
    YouTube Music continuous radio, and diversity-filtering heuristics.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._spotify_token: Optional[str] = None
        self._spotify_token_expiry: float = 0.0
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour cache per seed

    # ---------------------------------------------------------
    # Spotify API Authentication & Client Credential Flow
    # ---------------------------------------------------------
    def _get_spotify_access_token(self) -> Optional[str]:
        """Obtains or refreshes Spotify App Access Token using client credentials."""
        if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
            return None

        now = time.time()
        with self._lock:
            if self._spotify_token and now < self._spotify_token_expiry - 60:
                return self._spotify_token

            auth_bytes = f"{SPOTIPY_CLIENT_ID}:{SPOTIPY_CLIENT_SECRET}".encode("utf-8")
            auth_header = base64.b64encode(auth_bytes).decode("utf-8")

            try:
                resp = requests.post(
                    "https://accounts.spotify.com/api/token",
                    headers={
                        "Authorization": f"Basic {auth_header}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._spotify_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._spotify_token_expiry = now + expires_in
                    return self._spotify_token
                else:
                    logger.warning(f"Spotify token request failed with status {resp.status_code}")
            except Exception as e:
                logger.error(f"Failed to authenticate with Spotify: {e}")

        return None

    # ---------------------------------------------------------
    # Metadata Normalization & Diversity Filters
    # ---------------------------------------------------------
    @staticmethod
    def _clean_title(title: str) -> str:
        """Removes common YouTube video noise to isolate song titles."""
        clean = re.sub(
            r"(?i)\s*[\(\[](official\s*(music\s*)?(video|audio)|lyrics|visualizer|hd|4k|remastered)[\)\]]|\b(4k|hd|hq)\b",
            "",
            title
        )
        return re.sub(r"\s+", " ", clean).strip()

    def _filter_and_diversify(
        self,
        candidates: List[Dict[str, Any]],
        exclude_ids: Optional[List[str]] = None,
        max_per_artist: int = 2,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates tracks, checks against the exclude history list,
        and caps recurring artists to prevent repetitive echo chambers.
        """
        exclude_set = set(exclude_ids or [])
        seen_titles = set()
        artist_counts: Dict[str, int] = {}
        filtered: List[Dict[str, Any]] = []

        for track in candidates:
            track_id = track.get("id") or track.get("videoId")
            title = self._clean_title(track.get("title", ""))
            artist = (track.get("artist") or "Unknown").strip().lower()

            if not track_id or track_id in exclude_set:
                continue

            normalized_key = f"{artist} - {title.lower()}"
            if normalized_key in seen_titles:
                continue

            # Diversity cap: avoid playing tracks exclusively from one artist
            if artist_counts.get(artist, 0) >= max_per_artist:
                continue

            seen_titles.add(normalized_key)
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
            duration_val = track.get("duration", 0) or 0
            filtered.append({
                "id": track_id,
                "title": title,
                "artist": track.get("artist", "Unknown"),
                "thumbnail": track.get("thumbnail", ""),
                "duration": duration_val,
                "duration_formatted": track.get("duration_formatted") or format_duration(duration_val),
                "source": track.get("source", "generic"),
            })

            if len(filtered) >= limit:
                break

        return filtered

    # ---------------------------------------------------------
    # Strategy 1: Spotify Acoustic Graph Recommendations
    # ---------------------------------------------------------
    def _recommend_from_spotify(
        self, artist: str, title: str, limit: int = 15
    ) -> Optional[List[Dict[str, Any]]]:
        """Resolves seed track on Spotify and queries the recommendation API."""
        token = self._get_spotify_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # 1. Search for matching Spotify Track ID
            query = f"track:{title} artist:{artist}" if artist else title
            search_resp = requests.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params={"q": query, "type": "track", "limit": 1},
                timeout=4.0,
            )
            if search_resp.status_code != 200:
                return None

            items = search_resp.json().get("tracks", {}).get("items", [])
            if not items:
                return None

            seed_track = items[0]
            seed_track_id = seed_track["id"]
            seed_artist_id = seed_track["artists"][0]["id"] if seed_track.get("artists") else None

            # 2. Query Spotify Recommendations with seed track & artist
            params = {
                "limit": limit,
                "seed_tracks": seed_track_id,
            }
            if seed_artist_id:
                params["seed_artists"] = seed_artist_id

            rec_resp = requests.get(
                "https://api.spotify.com/v1/recommendations",
                headers=headers,
                params=params,
                timeout=4.0,
            )
            if rec_resp.status_code != 200:
                return None

            tracks = rec_resp.json().get("tracks", [])
            results = []
            for t in tracks:
                dur_sec = int(t.get("duration_ms", 0) / 1000)
                results.append({
                    "id": t["id"],
                    "title": t["name"],
                    "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                    "thumbnail": t["album"]["images"][0]["url"] if t.get("album", {}).get("images") else "",
                    "duration": dur_sec,
                    "duration_formatted": format_duration(dur_sec),
                    "source": "spotify",
                })
            return results
        except Exception as e:
            logger.warning(f"Spotify recommendation failed, falling back to YouTube: {e}")
            return None

    # ---------------------------------------------------------
    # Strategy 2: YouTube Music Up-Next / Related Extractor
    # ---------------------------------------------------------
    def _recommend_from_youtube(
        self, seed_query: str, limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Queries YouTube related entries using yt-dlp search."""
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        # Search for related mix or query YouTube auto-suggestions
        search_query = f"ytsearch{limit}:{seed_query} audio radio"
        results = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []

                for entry in entries:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    title = entry.get("title", "")
                    uploader = entry.get("uploader") or entry.get("channel", "Unknown")
                    thumbnail = entry.get("thumbnail") or (
                        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
                    )

                    # Extract artist from "Artist - Title" format if available
                    artist = uploader
                    if " - " in title:
                        parts = title.split(" - ", 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()

                    dur_sec = entry.get("duration") or 0
                    results.append({
                        "id": video_id,
                        "title": title,
                        "artist": artist,
                        "thumbnail": thumbnail,
                        "duration": dur_sec,
                        "duration_formatted": format_duration(dur_sec),
                        "source": "youtube",
                    })
        except Exception as e:
            logger.error(f"YouTube related extraction error: {e}")

        return results

    # ---------------------------------------------------------
    # Unified Public Entrypoint
    # ---------------------------------------------------------
    def get_recommendations(
        self,
        title: str,
        artist: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns a diversified list of recommended songs based on the current track.
        Checks in-memory cache first, falls back gracefully across providers.
        """
        cache_key = f"{artist or ''}::{title}".lower().strip()
        now = time.time()

        # Check Cache
        cached = self._cache.get(cache_key)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return self._filter_and_diversify(cached["tracks"], exclude_ids, limit=limit)

        raw_candidates = []

        # 1. Try Spotify Acoustic Recommendations
        if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
            spotify_candidates = self._recommend_from_spotify(artist or "", title, limit=limit + 10)
            if spotify_candidates:
                raw_candidates.extend(spotify_candidates)

        # 2. Fallback to YouTube if Spotify returned nothing or is unconfigured
        if not raw_candidates:
            query = f"{artist} {title}" if artist else title
            raw_candidates = self._recommend_from_youtube(query, limit=limit + 10)

        # Update Cache
        self._cache[cache_key] = {
            "timestamp": now,
            "tracks": raw_candidates,
        }

        # Apply deduplication and diversity enforcement
        return self._filter_and_diversify(raw_candidates, exclude_ids, limit=limit)


# Global Singleton Instance
recommendation_engine = RecommendationEngine()
