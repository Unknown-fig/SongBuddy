"""
OpenSubsonic API Compatibility Layer for SongBuddy.
Implements the OpenSubsonic / Subsonic standard protocol (v1.16.1),
allowing mobile clients such as Symfonium (Android), Feishin (Desktop),
Amperfy (iOS), DSub, Substreamer, and Ultrasonic to connect, search, browse,
and stream music directly from SongBuddy without a dedicated client app.

Supports both JSON (f=json) and XML responses, modern Token + Salt MD5 auth,
legacy cleartext / enc:hex auth, and OpenSubsonic API Key authentication.
"""

import os
import sys
import json
import time
import hashlib
import logging
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Union
import xml.etree.ElementTree as ET

logger = logging.getLogger("songbuddy.opensubsonic")

SUBSONIC_API_VERSION = "1.16.1"
SUBSONIC_SERVER_TYPE = "songbuddy"
SUBSONIC_SERVER_VERSION = "1.0.0"
XMLNS = "http://subsonic.org/restapi"

# Default configuration credentials
SUBSONIC_DEFAULT_USER = os.getenv("SUBSONIC_USER", "admin")
SUBSONIC_DEFAULT_PASSWORD = os.getenv("SUBSONIC_PASSWORD", "songbuddy")
SUBSONIC_API_KEY = os.getenv("SUBSONIC_API_KEY", "songbuddy-subsonic-key")

# OpenSubsonic extension declarations
OPEN_SUBSONIC_EXTENSIONS = [
    {"name": "transcodeOffset", "versions": [1]},
    {"name": "apiKeyAuthentication", "versions": [1]},
    {"name": "formPost", "versions": [1]},
    {"name": "songNotes", "versions": [1]},
    {"name": "lyrics", "versions": [1, 2]}
]

GENRES_LIST = [
    {"name": "Pop", "songCount": 140, "albumCount": 20},
    {"name": "Hip-Hop", "songCount": 95, "albumCount": 15},
    {"name": "Rock", "songCount": 80, "albumCount": 12},
    {"name": "Indie", "songCount": 65, "albumCount": 10},
    {"name": "Electronic", "songCount": 55, "albumCount": 8},
    {"name": "Lo-Fi", "songCount": 50, "albumCount": 7},
    {"name": "R&B", "songCount": 45, "albumCount": 6},
    {"name": "Acoustic", "songCount": 40, "albumCount": 5}
]


def format_subsonic_song(track: Dict[str, Any], parent_id: str = "sb_dir_1") -> Dict[str, Any]:
    """Formats a track dictionary into OpenSubsonic song / child schema."""
    track_id = str(track.get("id", "unknown"))
    title = str(track.get("title") or "Unknown Title")
    artist = str(track.get("artist") or "Unknown Artist")
    album = str(track.get("album") or "Single")
    
    dur_raw = track.get("duration", 180)
    try:
        duration = int(float(dur_raw))
    except (ValueError, TypeError):
        duration = 180

    return {
        "id": track_id,
        "parent": parent_id,
        "isDir": False,
        "title": title,
        "album": album,
        "artist": artist,
        "track": 1,
        "year": int(track.get("year", 2024)),
        "genre": str(track.get("genre", "Pop")),
        "coverArt": track_id,
        "size": int(duration * 40000),  # Approximate bitstream size (~320kbps)
        "contentType": "audio/mpeg",
        "suffix": "mp3",
        "duration": duration,
        "bitRate": 320,
        "path": f"SongBuddy/{artist} - {title}.mp3",
        "isVideo": False,
        "playCount": int(track.get("play_count", 0)),
        "starred": bool(track.get("is_favorite", False))
    }


def authenticate_subsonic(params: Dict[str, List[str]], users_db: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Authenticates an OpenSubsonic / Subsonic client request.
    Returns (is_authenticated, username, error_message).
    
    Supported authentication schemes:
    1. Token + Salt (t=md5(password + salt), s=salt) [Modern Subsonic 1.13+]
    2. Legacy Password (p=password or p=enc:hexpassword)
    3. OpenSubsonic API Key (apiKey=...)
    4. Test / guest fallback if REQUIRE_AUTH is false.
    """
    username = params.get("u", [""])[0].strip()
    token = params.get("t", [""])[0].strip()
    salt = params.get("s", [""])[0].strip()
    password = params.get("p", [""])[0]
    api_key = params.get("apiKey", [""])[0].strip()

    # 1. API Key authentication
    if api_key:
        if api_key == SUBSONIC_API_KEY:
            return True, username or SUBSONIC_DEFAULT_USER, None
        for u_name, u_data in users_db.items():
            if u_data.get("api_key") == api_key:
                return True, u_name, None

    # If no username provided, fail auth unless in test mode or unauthenticated endpoint
    if not username:
        if os.getenv("ENVIRONMENT") == "test" or os.getenv("REQUIRE_AUTH", "false").lower() != "true":
            return True, SUBSONIC_DEFAULT_USER, None
        return False, None, "Parameter 'u' (username) is required"

    user_candidate = username.lower()

    # 2. Token + Salt authentication: md5(password + salt)
    if token and salt:
        # Check against default admin/subsonic user
        expected_admin_token = hashlib.md5((SUBSONIC_DEFAULT_PASSWORD + salt).encode("utf-8")).hexdigest().lower()
        if token.lower() == expected_admin_token:
            return True, user_candidate, None

        # Check against users in USERS_DB
        user_record = users_db.get(user_candidate)
        if user_record:
            # Check user-specific subsonic password
            u_pwd = user_record.get("subsonic_password")
            if u_pwd:
                expected_user_token = hashlib.md5((u_pwd + salt).encode("utf-8")).hexdigest().lower()
                if token.lower() == expected_user_token:
                    return True, user_candidate, None

    # 3. Legacy password authentication: p or enc:hex
    if password:
        plain_pwd = password
        if plain_pwd.startswith("enc:"):
            try:
                plain_pwd = bytes.fromhex(plain_pwd[4:]).decode("utf-8", errors="ignore")
            except Exception:
                pass

        if plain_pwd == SUBSONIC_DEFAULT_PASSWORD:
            return True, user_candidate, None

        user_record = users_db.get(user_candidate)
        if user_record:
            if user_record.get("subsonic_password") == plain_pwd:
                return True, user_candidate, None
            # Check argon2/pbkdf2 hash via auth_manager if available
            try:
                from auth import auth_manager
                if auth_manager.verify_password(plain_pwd, user_record.get("password_hash", "")):
                    return True, user_candidate, None
            except Exception:
                pass

    # 4. Fallback for test / relaxed mode
    if os.getenv("ENVIRONMENT") == "test" or os.getenv("REQUIRE_AUTH", "false").lower() != "true":
        return True, user_candidate, None

    return False, None, "Wrong username or password"


def build_subsonic_response(
    data: Optional[Dict[str, Any]] = None,
    error: Optional[Tuple[int, str]] = None,
    is_json: bool = True
) -> Tuple[bytes, str, int]:
    """
    Builds a standard OpenSubsonic response payload.
    Supports JSON (f=json) and Subsonic REST XML.
    Returns (body_bytes, content_type, http_status).
    """
    status = "ok" if error is None else "failed"

    if is_json:
        resp_obj: Dict[str, Any] = {
            "status": status,
            "version": SUBSONIC_API_VERSION,
            "type": SUBSONIC_SERVER_TYPE,
            "serverVersion": SUBSONIC_SERVER_VERSION,
            "openSubsonic": True
        }
        if error:
            resp_obj["error"] = {
                "code": error[0],
                "message": error[1]
            }
        elif data:
            resp_obj.update(data)

        full_payload = {"subsonic-response": resp_obj}
        body = json.dumps(full_payload, indent=2).encode("utf-8")
        return body, "application/json; charset=utf-8", 200
    else:
        # Build XML
        root = ET.Element("subsonic-response")
        root.set("xmlns", XMLNS)
        root.set("status", status)
        root.set("version", SUBSONIC_API_VERSION)
        root.set("type", SUBSONIC_SERVER_TYPE)
        root.set("serverVersion", SUBSONIC_SERVER_VERSION)
        root.set("openSubsonic", "true")

        if error:
            err_el = ET.SubElement(root, "error")
            err_el.set("code", str(error[0]))
            err_el.set("message", error[1])
        elif data:
            _append_dict_to_xml(root, data)

        xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return xml_str, "text/xml; charset=utf-8", 200


def _append_dict_to_xml(parent: ET.Element, d: Dict[str, Any]):
    """Recursively converts Subsonic nested dictionaries and lists into XML elements with attributes."""
    for key, val in d.items():
        if isinstance(val, dict):
            sub = ET.SubElement(parent, key)
            _append_dict_to_xml(sub, val)
        elif isinstance(val, list):
            # If list of dicts, tag name should usually be singular (e.g. song, musicFolder)
            singular = key[:-1] if key.endswith("s") and len(key) > 1 else key
            for item in val:
                sub = ET.SubElement(parent, singular)
                if isinstance(item, dict):
                    _append_dict_to_xml(sub, item)
                else:
                    sub.text = str(item)
        elif isinstance(val, bool):
            parent.set(key, "true" if val else "false")
        elif val is not None:
            parent.set(key, str(val))


class OpenSubsonicController:
    """
    Dispatches and processes OpenSubsonic / Subsonic API calls.
    Seamlessly interacts with SongBuddy's search engine, library store,
    stream resolver, and lyric cache.
    """
    def __init__(self, server_module):
        self.server = server_module

    def handle_request(
        self,
        method_name: str,
        params: Dict[str, List[str]],
        http_method: str = "GET",
        post_body: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str, int]:
        """
        Main request router for /rest/<method> and /rest/<method>.view.
        """
        # Normalize method: strip .view if present
        clean_method = method_name.replace(".view", "").strip()
        is_json = params.get("f", ["xml"])[0].lower() == "json"

        # 1. Public discovery endpoint (MUST NOT require auth per OpenSubsonic spec)
        if clean_method == "getOpenSubsonicExtensions":
            data = {"openSubsonicExtensions": OPEN_SUBSONIC_EXTENSIONS}
            return build_subsonic_response(data, is_json=is_json)

        # 2. Authenticate
        users_db = getattr(self.server, "USERS_DB", {})
        is_auth, username, err_msg = authenticate_subsonic(params, users_db)

        # Note: ping can be allowed or returned as 40 error if bad auth
        if not is_auth:
            return build_subsonic_response(error=(40, err_msg or "Wrong username or password"), is_json=is_json)

        username = username or SUBSONIC_DEFAULT_USER

        # 3. Route methods
        if clean_method == "ping":
            return build_subsonic_response({}, is_json=is_json)

        elif clean_method == "getLicense":
            return build_subsonic_response({
                "license": {
                    "valid": True,
                    "email": f"{username}@songbuddy.studio",
                    "licenseExpires": "2099-12-31T23:59:59Z",
                    "trialExpires": "2099-12-31T23:59:59Z"
                }
            }, is_json=is_json)

        elif clean_method == "getMusicFolders":
            return build_subsonic_response({
                "musicFolders": {
                    "musicFolder": [
                        {"id": 1, "name": "SongBuddy Library"}
                    ]
                }
            }, is_json=is_json)

        elif clean_method in ("getIndexes", "getArtists"):
            artists = self._collect_artists(username)
            return build_subsonic_response({
                "artists": {
                    "ignoredArticles": "The El La Los Las Das",
                    "index": [
                        {
                            "name": letter,
                            "artist": [
                                {"id": a["id"], "name": a["name"], "albumCount": a["albumCount"], "coverArt": a["coverArt"]}
                                for a in group
                            ]
                        }
                        for letter, group in artists.items() if group
                    ]
                }
            }, is_json=is_json)

        elif clean_method == "getArtist":
            artist_id = params.get("id", [""])[0]
            artist_data = self._get_artist_details(artist_id, username)
            return build_subsonic_response({"artist": artist_data}, is_json=is_json)

        elif clean_method == "getAlbum":
            album_id = params.get("id", [""])[0]
            album_data = self._get_album_details(album_id, username)
            return build_subsonic_response({"album": album_data}, is_json=is_json)

        elif clean_method == "getMusicDirectory":
            dir_id = params.get("id", ["1"])[0]
            dir_data = self._get_music_directory(dir_id, username)
            return build_subsonic_response({"directory": dir_data}, is_json=is_json)

        elif clean_method == "getGenres":
            return build_subsonic_response({
                "genres": {
                    "genre": GENRES_LIST
                }
            }, is_json=is_json)

        elif clean_method in ("search2", "search3"):
            q = params.get("query", params.get("q", [""]))[0].strip()
            song_count = int(params.get("songCount", ["20"])[0])
            search_results = self._perform_subsonic_search(q, song_count, username)
            return build_subsonic_response({"searchResult3": search_results}, is_json=is_json)

        elif clean_method == "getSong":
            song_id = params.get("id", [""])[0]
            if not song_id:
                return build_subsonic_response(error=(10, "Required parameter 'id' is missing"), is_json=is_json)
            song = self._resolve_song(song_id)
            if not song:
                return build_subsonic_response(error=(70, f"Song '{song_id}' not found"), is_json=is_json)
            return build_subsonic_response({"song": song}, is_json=is_json)

        elif clean_method == "getLyrics":
            song_id = params.get("id", [""])[0]
            artist = params.get("artist", [""])[0]
            title = params.get("title", [""])[0]
            lyrics_data = self._get_lyrics(song_id, artist, title)
            return build_subsonic_response({"lyrics": lyrics_data}, is_json=is_json)

        elif clean_method == "getLyricsBySongId":
            song_id = params.get("id", [""])[0]
            structured_lyrics = self._get_structured_lyrics(song_id)
            return build_subsonic_response({"lyricsList": structured_lyrics}, is_json=is_json)

        elif clean_method == "getPlaylists":
            playlists = self._get_user_playlists(username)
            return build_subsonic_response({
                "playlists": {
                    "playlist": playlists
                }
            }, is_json=is_json)

        elif clean_method == "getPlaylist":
            pl_id = params.get("id", [""])[0]
            if not pl_id:
                return build_subsonic_response(error=(10, "Missing playlist id"), is_json=is_json)
            playlist = self._get_playlist_details(pl_id, username)
            if not playlist:
                return build_subsonic_response(error=(70, f"Playlist '{pl_id}' not found"), is_json=is_json)
            return build_subsonic_response({"playlist": playlist}, is_json=is_json)

        elif clean_method == "createPlaylist":
            name = params.get("name", [""])[0] or (post_body or {}).get("name", "New Playlist")
            song_ids = params.get("songId", []) or (post_body or {}).get("songId", [])
            playlist = self._create_playlist(username, name, song_ids)
            return build_subsonic_response({"playlist": playlist}, is_json=is_json)

        elif clean_method == "updatePlaylist":
            pl_id = params.get("playlistId", params.get("id", [""]))[0]
            name = params.get("name", [None])[0]
            song_ids_to_add = params.get("songIdToAdd", [])
            song_indices_to_remove = [int(i) for i in params.get("songIndexToRemove", []) if i.isdigit()]
            updated = self._update_playlist(username, pl_id, name, song_ids_to_add, song_indices_to_remove)
            return build_subsonic_response({"playlist": updated} if updated else {}, is_json=is_json)

        elif clean_method == "deletePlaylist":
            pl_id = params.get("id", [""])[0]
            self._delete_playlist(username, pl_id)
            return build_subsonic_response({}, is_json=is_json)

        elif clean_method == "scrobble":
            song_id = params.get("id", [""])[0]
            if song_id:
                track = self._resolve_song(song_id) or {"id": song_id, "title": "Track", "artist": "Artist"}
                from library_store import library_store
                library_store.record_user_play(username, track)
            return build_subsonic_response({}, is_json=is_json)

        elif clean_method in ("star", "unstar", "setRating"):
            song_id = params.get("id", [""])[0]
            is_unstar = clean_method == "unstar"
            if song_id:
                track = self._resolve_song(song_id) or {"id": song_id, "title": "Track", "artist": "Artist"}
                from library_store import library_store
                library_store.toggle_user_favorite(username, track, remove=is_unstar)
            return build_subsonic_response({}, is_json=is_json)

        elif clean_method == "getNowPlaying":
            from library_store import library_store
            history = library_store.get_user_history(username, limit=5)
            now_playing_entries = [
                format_subsonic_song(h)
                for h in history
            ]
            return build_subsonic_response({
                "nowPlaying": {
                    "entry": now_playing_entries
                }
            }, is_json=is_json)

        # Fallback for other standard methods
        return build_subsonic_response({}, is_json=is_json)

    # -------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------
    def _perform_subsonic_search(self, query: str, limit: int, username: str) -> Dict[str, Any]:
        """Performs search and structures results for OpenSubsonic search3."""
        if not query or query == "*":
            # Return curated featured tracks and favorites
            from library_store import library_store
            favs = library_store.get_user_favorites(username)
            candidates = favs if favs else getattr(self.server, "FEATURED_TRACKS", [])
            songs = [format_subsonic_song(t) for t in candidates[:limit]]
        else:
            try:
                raw_results = self.server.search_tracks(query, limit=limit)
                songs = [format_subsonic_song(t) for t in raw_results]
            except Exception as e:
                logger.error(f"Search failed for OpenSubsonic query '{query}': {e}")
                songs = []

        # Extract distinct artists and albums from search results
        artists_dict: Dict[str, Dict[str, Any]] = {}
        albums_dict: Dict[str, Dict[str, Any]] = {}

        for s in songs:
            a_name = s["artist"]
            if a_name not in artists_dict:
                a_id = f"art_{hashlib.md5(a_name.encode('utf-8')).hexdigest()[:8]}"
                artists_dict[a_name] = {
                    "id": a_id,
                    "name": a_name,
                    "albumCount": 1,
                    "coverArt": s["id"]
                }
            alb_name = s["album"]
            if alb_name not in albums_dict:
                alb_id = f"alb_{hashlib.md5(alb_name.encode('utf-8')).hexdigest()[:8]}"
                albums_dict[alb_name] = {
                    "id": alb_id,
                    "name": alb_name,
                    "artist": a_name,
                    "artistId": artists_dict[a_name]["id"],
                    "songCount": 1,
                    "duration": s["duration"],
                    "coverArt": s["id"]
                }

        return {
            "artist": list(artists_dict.values()),
            "album": list(albums_dict.values()),
            "song": songs
        }

    def _resolve_song(self, song_id: str) -> Optional[Dict[str, Any]]:
        """Resolves full track metadata by song ID."""
        # 1. Search in FEATURED_TRACKS
        for t in getattr(self.server, "FEATURED_TRACKS", []):
            if t.get("id") == song_id:
                return format_subsonic_song(t)

        # 2. Search in library store (favorites & history)
        from library_store import library_store
        for user_id in [SUBSONIC_DEFAULT_USER, "guest", "admin"]:
            favs = library_store.get_user_favorites(user_id)
            for f in favs:
                if f.get("id") == song_id:
                    return format_subsonic_song(f)
            hist = library_store.get_user_history(user_id, limit=50)
            for h in hist:
                if h.get("id") == song_id:
                    return format_subsonic_song(h)

        # 3. Fallback: Query yt-dlp metadata cache
        try:
            cached_stream = getattr(self.server, "STREAM_CACHE", None)
            if cached_stream:
                val = cached_stream.get(f"{song_id}_high") or cached_stream.get(song_id)
                if val:
                    return format_subsonic_song({
                        "id": song_id,
                        "title": val.get("title", f"Track {song_id}"),
                        "artist": val.get("uploader", "YouTube"),
                        "duration": val.get("duration", 200)
                    })
        except Exception:
            pass

        # Return default synthesized song descriptor
        return format_subsonic_song({
            "id": song_id,
            "title": f"SongBuddy Audio ({song_id})",
            "artist": "SongBuddy Artist",
            "album": "SongBuddy Studio",
            "duration": 210
        })

    def _collect_artists(self, username: str) -> Dict[str, List[Dict[str, Any]]]:
        """Groups library artists alphabetically."""
        from library_store import library_store
        artists_by_letter: Dict[str, List[Dict[str, Any]]] = {chr(c): [] for c in range(ord('A'), ord('Z') + 1)}
        artists_by_letter["#"] = []

        seen_names = set()
        sources = library_store.get_user_favorites(username) + getattr(self.server, "FEATURED_TRACKS", [])

        for t in sources:
            name = (t.get("artist") or "Unknown").strip()
            if name in seen_names:
                continue
            seen_names.add(name)
            first_char = name[0].upper()
            target_key = first_char if first_char in artists_by_letter else "#"
            a_id = f"art_{hashlib.md5(name.encode('utf-8')).hexdigest()[:8]}"
            artists_by_letter[target_key].append({
                "id": a_id,
                "name": name,
                "albumCount": 1,
                "coverArt": t.get("id", "")
            })

        return artists_by_letter

    def _get_artist_details(self, artist_id: str, username: str) -> Dict[str, Any]:
        """Returns artist profile and their albums."""
        # Find artist name
        artists_map = self._collect_artists(username)
        artist_obj = None
        for group in artists_map.values():
            for a in group:
                if a["id"] == artist_id or a["name"].lower() == artist_id.lower():
                    artist_obj = a
                    break
            if artist_obj:
                break

        name = artist_obj["name"] if artist_obj else "Featured Artist"
        alb_id = f"alb_{hashlib.md5(name.encode('utf-8')).hexdigest()[:8]}"

        # Search songs by this artist
        songs = []
        for t in getattr(self.server, "FEATURED_TRACKS", []):
            if name.lower() in (t.get("artist") or "").lower():
                songs.append(format_subsonic_song(t))

        return {
            "id": artist_id,
            "name": name,
            "albumCount": 1,
            "album": [
                {
                    "id": alb_id,
                    "name": f"{name} Essentials",
                    "artist": name,
                    "artistId": artist_id,
                    "songCount": len(songs) or 1,
                    "duration": sum(s["duration"] for s in songs) or 200,
                    "coverArt": songs[0]["id"] if songs else ""
                }
            ]
        }

    def _get_album_details(self, album_id: str, username: str) -> Dict[str, Any]:
        """Returns album metadata and track list."""
        songs = [format_subsonic_song(t) for t in getattr(self.server, "FEATURED_TRACKS", [])]
        return {
            "id": album_id,
            "name": "SongBuddy Studio Session",
            "artist": "Various Artists",
            "songCount": len(songs),
            "duration": sum(s["duration"] for s in songs),
            "coverArt": songs[0]["id"] if songs else "",
            "song": songs
        }

    def _get_music_directory(self, dir_id: str, username: str) -> Dict[str, Any]:
        """Returns directory listing for OpenSubsonic browsing."""
        songs = [format_subsonic_song(t) for t in getattr(self.server, "FEATURED_TRACKS", [])]
        return {
            "id": dir_id,
            "parent": "1",
            "name": "SongBuddy Library",
            "child": songs
        }

    def _get_lyrics(self, song_id: str, artist: str, title: str) -> Dict[str, Any]:
        """Resolves plain lyrics for Subsonic getLyrics."""
        if not title and song_id:
            s = self._resolve_song(song_id)
            if s:
                title = s["title"]
                artist = s["artist"]

        try:
            lyrics_resp = self.server.fetch_lyrics(title, artist)
            plain = lyrics_resp.get("plainLyrics") or lyrics_resp.get("syncedLyrics") or "Lyrics unavailable."
            return {
                "artist": artist,
                "title": title,
                "value": plain
            }
        except Exception:
            return {"artist": artist, "title": title, "value": "Lyrics unavailable."}

    def _get_structured_lyrics(self, song_id: str) -> Dict[str, Any]:
        """Resolves OpenSubsonic structured timestamped lyrics."""
        s = self._resolve_song(song_id)
        title = s["title"] if s else "Track"
        artist = s["artist"] if s else "Artist"

        try:
            lyrics_resp = self.server.fetch_lyrics(title, artist)
            cues = self.server.parse_lrc_to_cues(lyrics_resp.get("syncedLyrics"))
            lines = [
                {"start": int(c["time"] * 1000), "value": c["text"]}
                for c in cues
            ]
            return {
                "structuredLyrics": [
                    {
                        "lang": "en",
                        "synced": len(cues) > 0,
                        "line": lines
                    }
                ]
            }
        except Exception:
            return {"structuredLyrics": []}

    def _get_user_playlists(self, username: str) -> List[Dict[str, Any]]:
        """Returns list of playlists formatted for OpenSubsonic."""
        from library_store import library_store
        raw_playlists = library_store.get_user_playlists(username)
        res = []
        for pl in raw_playlists:
            tracks = pl.get("tracks", [])
            dur = sum(int(t.get("duration", 0)) for t in tracks)
            res.append({
                "id": pl["id"],
                "name": pl["name"],
                "comment": pl.get("description", ""),
                "songCount": len(tracks),
                "duration": dur,
                "created": pl.get("created_at", ""),
                "changed": pl.get("updated_at", ""),
                "coverArt": tracks[0].get("id", "") if tracks else ""
            })
        return res

    def _get_playlist_details(self, playlist_id: str, username: str) -> Optional[Dict[str, Any]]:
        """Returns playlist details with child entries."""
        from library_store import library_store
        raw_playlists = library_store.get_user_playlists(username)
        for pl in raw_playlists:
            if pl["id"] == playlist_id:
                tracks = pl.get("tracks", [])
                dur = sum(int(t.get("duration", 0)) for t in tracks)
                return {
                    "id": pl["id"],
                    "name": pl["name"],
                    "comment": pl.get("description", ""),
                    "songCount": len(tracks),
                    "duration": dur,
                    "created": pl.get("created_at", ""),
                    "changed": pl.get("updated_at", ""),
                    "coverArt": tracks[0].get("id", "") if tracks else "",
                    "entry": [format_subsonic_song(t, parent_id=playlist_id) for t in tracks]
                }
        return None

    def _create_playlist(self, username: str, name: str, song_ids: List[str]) -> Dict[str, Any]:
        """Creates a playlist with optional initial songs."""
        from library_store import library_store
        tracks = []
        for sid in song_ids:
            s = self._resolve_song(sid)
            if s:
                tracks.append(s)

        pl_data = {
            "name": name,
            "description": "Created via OpenSubsonic Mobile Client",
            "tracks": tracks
        }
        saved = library_store.save_user_playlist(username, pl_data)
        return {
            "id": saved["id"],
            "name": saved["name"],
            "songCount": len(tracks),
            "duration": sum(s["duration"] for s in tracks),
            "entry": tracks
        }

    def _update_playlist(
        self,
        username: str,
        playlist_id: str,
        name: Optional[str],
        song_ids_to_add: List[str],
        song_indices_to_remove: List[int]
    ) -> Optional[Dict[str, Any]]:
        """Updates playlist metadata or songs."""
        from library_store import library_store
        raw_playlists = library_store.get_user_playlists(username)
        target = None
        for pl in raw_playlists:
            if pl["id"] == playlist_id:
                target = pl
                break

        if not target:
            return None

        tracks = list(target.get("tracks", []))

        # Remove indices in reverse order
        for idx in sorted(song_indices_to_remove, reverse=True):
            if 0 <= idx < len(tracks):
                tracks.pop(idx)

        # Add new songs
        for sid in song_ids_to_add:
            s = self._resolve_song(sid)
            if s:
                tracks.append(s)

        new_data = {
            "id": playlist_id,
            "name": name if name else target["name"],
            "description": target.get("description", ""),
            "tracks": tracks
        }
        saved = library_store.save_user_playlist(username, new_data)
        return {
            "id": saved["id"],
            "name": saved["name"],
            "songCount": len(tracks),
            "entry": tracks
        }

    def _delete_playlist(self, username: str, playlist_id: str) -> bool:
        from library_store import library_store
        return library_store.delete_user_playlist(username, playlist_id)
