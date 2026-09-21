from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

try:
    import config
except ImportError:
    from . import config

_sp_client = None

def get_spotify_client() -> spotipy.Spotify:
    global _sp_client
    if _sp_client is None:
        config.validate_environment()
        auth_manager = SpotifyClientCredentials(
            client_id=config.SPOTIPY_CLIENT_ID,
            client_secret=config.SPOTIPY_CLIENT_SECRET
        )
        _sp_client = spotipy.Spotify(auth_manager=auth_manager)
    return _sp_client

def clean_spotify_url(url: str) -> Tuple[str, str]:
    """Extracts entity type (track/playlist/album) and ID from URL or bare ID."""
    pattern = r"(?:spotify:|(?:https?://open\.spotify\.com/))(track|playlist|album)[/:]([a-zA-Z0-9]+)"
    match = re.search(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid Spotify URL format: {url}")
    return match.group(1), match.group(2)

def fetch_track_metadata(track_id: str) -> Dict[str, Any]:
    """Retrieves full canonical metadata for a single track."""
    sp = get_spotify_client()
    raw = sp.track(track_id)
    
    # Select highest resolution cover available
    images = raw["album"].get("images", [])
    cover_url = images[0]["url"] if images else None

    return {
        "id": raw["id"],
        "title": raw["name"],
        "artists": [artist["name"] for artist in raw["artists"]],
        "primary_artist": raw["artists"][0]["name"] if raw["artists"] else "Unknown Artist",
        "album": raw["album"]["name"],
        "release_date": raw["album"]["release_date"],
        "track_number": raw["track_number"],
        "total_tracks": raw["album"]["total_tracks"],
        "duration_ms": raw["duration_ms"],
        "duration_sec": raw["duration_ms"] / 1000.0,
        "isrc": raw.get("external_ids", {}).get("isrc", ""),
        "cover_url": cover_url
    }

def fetch_playlist_tracks(playlist_id: str) -> List[Dict[str, Any]]:
    """Retrieves all tracks inside a Spotify playlist handling pagination."""
    sp = get_spotify_client()
    results = sp.playlist_items(playlist_id, additional_types=['track'])
    tracks = []
    
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                images = track["album"].get("images", [])
                tracks.append({
                    "id": track["id"],
                    "title": track["name"],
                    "artists": [a["name"] for a in track["artists"]],
                    "primary_artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                    "album": track["album"]["name"],
                    "release_date": track["album"]["release_date"],
                    "track_number": track["track_number"],
                    "total_tracks": track["album"]["total_tracks"],
                    "duration_ms": track["duration_ms"],
                    "duration_sec": track["duration_ms"] / 1000.0,
                    "isrc": track.get("external_ids", {}).get("isrc", ""),
                    "cover_url": images[0]["url"] if images else None
                })
        results = sp.next(results) if results.get("next") else None
        
    return tracks
