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


# Regional & Linguistic Context Detection
HINDI_SCRIPT_RE = re.compile(r'[\u0900-\u097F\u0A00-\u0A7F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0600-\u06FF]')
HINDI_KEYWORDS = {
    'hindi', 'bollywood', 'punjabi', 'bhangra', 'sufi', 'ghazal', 'qawwali', 'lofi hindi',
    'dil', 'pyar', 'pyaar', 'ishq', 'mohabbat', 'tere', 'teri', 'mera', 'meri', 'tum', 'hum',
    'sanam', 'zindagi', 'saath', 'deewana', 'aankhon', 'raat', 'chaand', 'saiyaara', 'bairan',
    'aarzu', 'sahiba', 'taare', 'pal', 'zulfein', 'dhol', 'nach', 'channa', 'kesariya', 'shayad',
    'khairiyat', 'humsafar', 'dhadak', 'raataan', 'lambiyan', 'chaleya', 'baarishein', 'tu hai',
    'kahan', 'pehli', 'nazar', 'kabhi', 'dosti', 'yaari', 'ranjha', 'heer', 'mann', 'duniya',
    'naina', 'ankhiyaan', 'sajna', 'dholna', 'mahiya', 'jatt', 'pind', 'kudi', 'gaana', 'geet',
    'aashiqui', 'bewafa', 'sadqa', 'dua', 'humnava', 'rabba', 'ishqbaazi', 'tujhe', 'mujhe',
    'apna', 'bana', 'le', 'kahani', 'baarish', 'tera', 'chahunga', 'muskurane', 'sukoon',
    'musafir', 'leja', 're', 'lut', 'gaye', 'qismat', 'kalank', 'ghungroo', 'bekhayali', 'pehla',
    'gerua', 'bulleya', 'zaalima', 'hawayein', 'matargashti', 'kasoor', 'choo', 'lo', 'aaftab',
    'heeriye', 'satranga', 'soulmate', 'pasoori', 'husn', 'faasle', 'kho', 'gaye', 'safarnama',
    'alvida', 'jeena', 'jeene', 'laga', 'tera fitoor', 'nainowale', 'subhanallah', 'kabira'
}
INDIAN_ARTISTS = {
    'arijit singh', 'atif aslam', 'shreya ghoshal', 'neha kakkar', 'jubin nautiyal',
    'sonu nigam', 'sunidhi chauhan', 'mohit chauhan', 'kishore kumar', 'lata mangeshkar',
    'mukesh', 'mohammed rafi', 'pritam', 'ar rahman', 'a.r. rahman', 'badshah',
    'diljit dosanjh', 'ap dhillon', 'karan aujla', 'honey singh', 'yo yo honey singh',
    'darshan raval', 'anuv jain', 'prateek kuhad', 'sachin-jigar', 'vishal mishra',
    'armaan malik', 'b praak', 'jaani', 'sidhu moosewala', 'guru randhawa', 'hardy sandhu',
    'shubh', 'talwiinder', 'king', 'mc stan', 'divine', 'raftaar', 'kumar sanu',
    'udit narayan', 'alka yagnik', 'kavita krishnamurthy', 'jagjit singh', 'nusrat fateh ali khan',
    'rahat fateh ali khan', 'lucky ali', 'kk', 'shaan', 'himesh reshammiya', 'mika singh',
    'sachet tandon', 'stebin ben', 'jasleen royal', 'aditya rikhari', 'madhurxo', 'kushagra',
    'aur', 'sickved', 'banjaare', 't-series', 'zee music', 'sony music india', 'yrf', 'tips',
    'saregama', 'speed records', 'white hill music', 'anirudh ravichander', 'devi sri prasad',
    'vishal-shekhar', 'amit trivedi', 'mithoon', 'meet bros', 'tony kakkar', 'pawandeep rajan',
    'arunita kanjilal', 'shankar mahadevan', 'hariharan', 'pankaj udhas', 'bhupen hazarika'
}
BLATANT_WESTERN_ARTISTS = {
    'the weeknd', 'taylor swift', 'drake', 'justin bieber', 'dua lipa', 'ed sheeran',
    'billie eilish', 'ariana grande', 'bruno mars', 'rihanna', 'beyonce', 'post malone',
    'kendrick lamar', 'eminem', 'kanye west', 'travis scott', 'coldplay', 'imagine dragons',
    'maroon 5', 'shawn mendes', 'harry styles', 'olivia rodrigo', 'adele', 'sam smith',
    'katy perry', 'lady gaga', 'selena gomez', 'charlie puth', 'zayn', 'camila cabello',
    'sabrina carpenter', 'chappell roan', 'charli xcx', 'queen', 'the beatles', 'michael jackson',
    'sza', 'doja cat', 'miley cyrus', 'jack harlow', 'future', 'metro boomin', 'gunna', 'lil baby',
    'lil nas x', '21 savage', 'cardi b', 'nicki minaj', 'marshmello', 'alan walker', 'david guetta',
    'calvin harris', 'avicii', 'dj snake', 'tiesto', 'kygo', 'martin garrix', 'halsey', 'benson boone'
}

def is_indian_hindi_track(title: str, artist: str) -> bool:
    """Detects whether a track is Hindi / Bollywood / Punjabi / Indian regional."""
    text = f"{title or ''} {artist or ''}".lower()
    if HINDI_SCRIPT_RE.search(text):
        return True
    clean_art = (artist or "").lower().strip()
    for ia in INDIAN_ARTISTS:
        if ia in clean_art or ia in text:
            return True
    words = set(re.findall(r'[a-zA-Z]+', text))
    if any(k in words for k in HINDI_KEYWORDS):
        return True
    return False

def is_blatant_western_track(title: str, artist: str) -> bool:
    """Detects whether a track is clearly Western / English mainstream pop."""
    clean_art = (artist or "").lower().strip()
    clean_title = (title or "").lower().strip()
    clean_text = f"{clean_title} {clean_art}"
    for wa in BLATANT_WESTERN_ARTISTS:
        if wa in clean_art or wa in clean_text:
            return True
    return False


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
        is_indian: bool = False,
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

            # When seed track is Indian, filter out blatant Western English pop songs
            if is_indian and is_blatant_western_track(title, track.get("artist", "")):
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
        is_indian = is_indian_hindi_track(title or "", artist or "")
        cache_key = f"{artist or ''}::{title}:{'in' if is_indian else 'en'}".lower().strip()
        now = time.time()

        # Check Cache
        cached = self._cache.get(cache_key)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return self._filter_and_diversify(cached["tracks"], exclude_ids, limit=limit, is_indian=is_indian)

        raw_candidates = []

        # 1. Try Spotify Acoustic Recommendations
        if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
            spotify_candidates = self._recommend_from_spotify(artist or "", title, limit=limit + 10)
            if spotify_candidates:
                if is_indian:
                    spotify_candidates = [sc for sc in spotify_candidates if not is_blatant_western_track(sc.get("title", ""), sc.get("artist", ""))]
                raw_candidates.extend(spotify_candidates)

        # 2. Fallback to YouTube if Spotify returned nothing or is unconfigured
        if not raw_candidates:
            if is_indian:
                query = f"{artist or title} hindi bollywood songs radio mix"
            else:
                query = f"{artist} {title}" if artist else title
            raw_candidates = self._recommend_from_youtube(query, limit=limit + 10)
            if is_indian:
                raw_candidates = [rc for rc in raw_candidates if not is_blatant_western_track(rc.get("title", ""), rc.get("artist", ""))]

        # 3. Fallback for Indian tracks if still empty
        if not raw_candidates and is_indian:
            raw_candidates = self._recommend_from_youtube("Top Trending Hindi Bollywood Hits 2026", limit=limit + 10)
            raw_candidates = [rc for rc in raw_candidates if not is_blatant_western_track(rc.get("title", ""), rc.get("artist", ""))]

        # Update Cache
        self._cache[cache_key] = {
            "timestamp": now,
            "tracks": raw_candidates,
        }

        # Apply deduplication and diversity enforcement
        return self._filter_and_diversify(raw_candidates, exclude_ids, limit=limit, is_indian=is_indian)


# Global Singleton Instance
recommendation_engine = RecommendationEngine()
