"""
Bulk Playlist Importer for SongBuddy.
Resolves public playlist and album URLs from:
- Spotify (via Spotipy API or public oEmbed / embed metadata)
- YouTube / YouTube Music (via yt-dlp flat extraction)
- Apple Music (via public meta extraction)
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
import requests
import yt_dlp

logger = logging.getLogger("songbuddy.importer")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def detect_playlist_source(url: str) -> str:
    url_lower = url.lower().strip()
    if "spotify.com" in url_lower or url_lower.startswith("spotify:"):
        return "spotify"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "music.apple.com" in url_lower:
        return "apple_music"
    return "unknown"

def import_spotify_playlist(url: str) -> Dict[str, Any]:
    """Resolves Spotify playlist or album tracks."""
    try:
        from metadata import clean_spotify_url, fetch_playlist_tracks, fetch_track_metadata
        entity_type, entity_id = clean_spotify_url(url)

        if entity_type == "playlist":
            tracks_raw = fetch_playlist_tracks(entity_id)
            title = f"Spotify Playlist ({entity_id[:8]})"
            tracks = []
            for t in tracks_raw:
                tracks.append({
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "artist": t.get("primary_artist", ", ".join(t.get("artists", []))),
                    "album": t.get("album", "Spotify"),
                    "duration": t.get("duration_sec", 0),
                    "duration_formatted": f"{int(t.get('duration_sec', 0)//60)}:{int(t.get('duration_sec', 0)%60):02d}",
                    "thumbnail": t.get("cover_url") or "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=300&q=80",
                    "source": "spotify"
                })
            return {
                "source": "spotify",
                "title": title,
                "total_tracks": len(tracks),
                "tracks": tracks
            }
        elif entity_type == "album":
            from metadata import get_spotify_client
            sp = get_spotify_client()
            album_info = sp.album(entity_id)
            album_title = album_info.get("name", "Spotify Album")
            album_cover = album_info.get("images", [{}])[0].get("url")
            tracks = []
            for it in album_info.get("tracks", {}).get("items", []):
                dur_sec = it.get("duration_ms", 0) / 1000.0
                tracks.append({
                    "id": it.get("id"),
                    "title": it.get("name"),
                    "artist": it.get("artists", [{}])[0].get("name", "Unknown Artist"),
                    "album": album_title,
                    "duration": dur_sec,
                    "duration_formatted": f"{int(dur_sec//60)}:{int(dur_sec%60):02d}",
                    "thumbnail": album_cover or "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=300&q=80",
                    "source": "spotify"
                })
            return {
                "source": "spotify",
                "title": album_title,
                "total_tracks": len(tracks),
                "tracks": tracks
            }
    except Exception as e:
        logger.warning(f"Spotipy direct fetch failed or unconfigured ({e}). Falling back to public oEmbed scraper.")

    # Fallback: scrape public oEmbed and HTML
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={requests.utils.quote(url)}"
        resp = requests.get(oembed_url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
        pl_title = "Imported Spotify Playlist"
        thumb = "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=300&q=80"
        if resp.status_code == 200:
            d = resp.json()
            pl_title = d.get("title", pl_title)
            thumb = d.get("thumbnail_url", thumb)

        # Scrape embed HTML for track list
        clean_url = url.split("?")[0]
        embed_url = clean_url.replace("open.spotify.com/", "open.spotify.com/embed/")
        embed_resp = requests.get(embed_url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
        tracks = []
        if embed_resp.status_code == 200:
            html = embed_resp.text
            # Look for JSON payload in next_data or resource script
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if match:
                data = json.loads(match.group(1))
                entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
                for item in entity.get("trackList", []):
                    dur_sec = item.get("duration", 0) / 1000.0
                    tracks.append({
                        "id": item.get("uri", "").replace("spotify:track:", ""),
                        "title": item.get("title"),
                        "artist": item.get("subtitle", "Unknown"),
                        "album": pl_title,
                        "duration": dur_sec,
                        "duration_formatted": f"{int(dur_sec//60)}:{int(dur_sec%60):02d}",
                        "thumbnail": thumb,
                        "source": "spotify"
                    })

        return {
            "source": "spotify",
            "title": pl_title,
            "total_tracks": len(tracks),
            "tracks": tracks
        }
    except Exception as scrape_err:
        raise ValueError(f"Unable to parse Spotify playlist: {scrape_err}")

def import_youtube_playlist(url: str) -> Dict[str, Any]:
    """Resolves YouTube or YouTube Music playlist tracks via yt-dlp flat extraction."""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        res = ydl.extract_info(url, download=False)

    pl_title = res.get("title", "Imported YouTube Playlist")
    entries = res.get("entries", [])
    tracks = []

    for entry in entries:
        vid_id = entry.get("id")
        if not vid_id:
            continue
        title = entry.get("title", "Unknown Track")
        uploader = entry.get("uploader") or entry.get("channel") or "Unknown Artist"
        duration = entry.get("duration", 0) or 0
        thumbs = entry.get("thumbnails", [])
        thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

        tracks.append({
            "id": vid_id,
            "title": title,
            "artist": uploader,
            "album": pl_title,
            "duration": duration,
            "duration_formatted": f"{int(duration//60)}:{int(duration%60):02d}",
            "thumbnail": thumb_url,
            "source": "youtube"
        })

    return {
        "source": "youtube",
        "title": pl_title,
        "total_tracks": len(tracks),
        "tracks": tracks
    }

def import_apple_music_playlist(url: str) -> Dict[str, Any]:
    """Resolves Apple Music playlist via public OpenGraph and webpage meta tags."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=8.0)
    if resp.status_code != 200:
        raise ValueError(f"Apple Music responded with HTTP {resp.status_code}")

    html = resp.text
    # Extract title
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    pl_title = title_match.group(1) if title_match else "Apple Music Playlist"

    # Extract image
    img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    pl_thumb = img_match.group(1) if img_match else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&q=80"

    # Extract track rows
    tracks = []
    # Search for schema.org MusicRecording or track list elements
    track_matches = re.findall(r'<div class="songs-list-row__song-name"[^>]*>([^<]+)</div>.*?<a[^>]*class="songs-list-row__link"[^>]*>([^<]+)</a>', html, re.DOTALL)
    for title, artist in track_matches:
        tracks.append({
            "id": f"am_{abs(hash(title + artist)) % 10000000}",
            "title": title.strip(),
            "artist": artist.strip(),
            "album": pl_title,
            "duration": 210,
            "duration_formatted": "3:30",
            "thumbnail": pl_thumb,
            "source": "apple_music"
        })

    return {
        "source": "apple_music",
        "title": pl_title,
        "total_tracks": len(tracks),
        "tracks": tracks
    }

def import_playlist_by_url(url: str) -> Dict[str, Any]:
    source = detect_playlist_source(url)
    if source == "spotify":
        return import_spotify_playlist(url)
    elif source == "youtube":
        return import_youtube_playlist(url)
    elif source == "apple_music":
        return import_apple_music_playlist(url)
    else:
        raise ValueError("Unsupported playlist URL. Please provide a public Spotify, YouTube, or Apple Music link.")
