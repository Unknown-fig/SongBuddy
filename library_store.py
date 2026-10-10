"""
User Library Storage Manager for SongBuddy.
Provides multi-tier persistence for custom user playlists, favorites,
listening history, and dynamic smart playlists ("On Repeat", "Recently Played", "Jump Back In").
Supports SQLite with automatic fallback to JSON / Vercel KV / in-memory cache.
"""

import os
import json
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("songbuddy.library_store")
BASE_DIR = Path(__file__).parent.resolve()

class LibraryStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, Any] = {
            "playlists": {},
            "favorites": {},
            "history": {}
        }

        # KV Configuration (Upstash / Vercel KV)
        self.kv_url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        self.kv_token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

        # Database / file paths
        if os.getenv("VERCEL"):
            self.db_path = Path("/tmp/songbuddy_library.db")
            self.json_path = Path("/tmp/library_backup.json")
        else:
            self.db_path = BASE_DIR / "songbuddy_library.db"
            self.json_path = BASE_DIR / "library_backup.json"

        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Initializes database schema with WAL mode and indices for rapid indexing."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")

                # Playlists Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_playlists (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        cover_url TEXT DEFAULT '',
                        tracks_json TEXT NOT NULL DEFAULT '[]',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_playlists_user ON user_playlists(user_id);")

                # Favorites Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_favorites (
                        user_id TEXT NOT NULL,
                        track_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT DEFAULT 'Single',
                        duration REAL DEFAULT 0,
                        thumbnail TEXT DEFAULT '',
                        added_at TEXT NOT NULL,
                        PRIMARY KEY(user_id, track_id)
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id);")

                # Listening History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        track_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT DEFAULT 'Single',
                        duration REAL DEFAULT 0,
                        thumbnail TEXT DEFAULT '',
                        played_at TEXT NOT NULL,
                        play_count INTEGER DEFAULT 1
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON user_history(user_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_track ON user_history(user_id, track_id);")
                conn.commit()
                logger.info(f"Initialized SQLite library schema at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database ({e}). Operating in resilient fallback mode.")

    # ---------------------------------------------------------
    # 1. Custom Playlists Management
    # ---------------------------------------------------------
    def get_user_playlists(self, user_id: str) -> List[Dict[str, Any]]:
        uid = user_id.strip().lower()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, user_id, name, description, cover_url, tracks_json, created_at, updated_at "
                        "FROM user_playlists WHERE user_id = ? ORDER BY updated_at DESC",
                        (uid,)
                    )
                    rows = cursor.fetchall()
                    playlists = []
                    for r in rows:
                        try:
                            tracks = json.loads(r["tracks_json"])
                        except Exception:
                            tracks = []
                        playlists.append({
                            "id": r["id"],
                            "user_id": r["user_id"],
                            "name": r["name"],
                            "description": r["description"],
                            "cover_url": r["cover_url"] or (tracks[0].get("thumbnail") if tracks else ""),
                            "track_count": len(tracks),
                            "tracks": tracks,
                            "created_at": r["created_at"],
                            "updated_at": r["updated_at"]
                        })
                    return playlists
            except Exception as e:
                logger.error(f"Error reading playlists for user {uid}: {e}")
                user_pl = self._memory_cache["playlists"].get(uid, {})
                return list(user_pl.values())

    def save_user_playlist(self, user_id: str, playlist_data: Dict[str, Any]) -> Dict[str, Any]:
        uid = user_id.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        pl_id = playlist_data.get("id") or f"pl_{int(datetime.now().timestamp() * 1000)}"
        name = playlist_data.get("name", "My Playlist").strip()
        description = playlist_data.get("description", "").strip()
        tracks = playlist_data.get("tracks", [])
        cover_url = playlist_data.get("cover_url", "")
        if not cover_url and tracks:
            cover_url = tracks[0].get("thumbnail", "")

        tracks_json = json.dumps(tracks)

        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO user_playlists (id, user_id, name, description, cover_url, tracks_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            name = excluded.name,
                            description = excluded.description,
                            cover_url = excluded.cover_url,
                            tracks_json = excluded.tracks_json,
                            updated_at = excluded.updated_at;
                    """, (pl_id, uid, name, description, cover_url, tracks_json, now, now))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error saving playlist to SQLite: {e}")
                if uid not in self._memory_cache["playlists"]:
                    self._memory_cache["playlists"][uid] = {}
                self._memory_cache["playlists"][uid][pl_id] = {
                    "id": pl_id, "user_id": uid, "name": name, "description": description,
                    "cover_url": cover_url, "tracks": tracks, "track_count": len(tracks),
                    "created_at": now, "updated_at": now
                }

        return {
            "id": pl_id,
            "user_id": uid,
            "name": name,
            "description": description,
            "cover_url": cover_url,
            "track_count": len(tracks),
            "tracks": tracks,
            "updated_at": now
        }

    def delete_user_playlist(self, user_id: str, playlist_id: str) -> bool:
        uid = user_id.strip().lower()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM user_playlists WHERE id = ? AND user_id = ?", (playlist_id, uid))
                    conn.commit()
                    deleted = cursor.rowcount > 0
                if uid in self._memory_cache["playlists"]:
                    self._memory_cache["playlists"][uid].pop(playlist_id, None)
                return deleted
            except Exception as e:
                logger.error(f"Error deleting playlist {playlist_id}: {e}")
                if uid in self._memory_cache["playlists"]:
                    return bool(self._memory_cache["playlists"][uid].pop(playlist_id, None))
                return False

    # ---------------------------------------------------------
    # 2. Favorites Persistence
    # ---------------------------------------------------------
    def get_user_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        uid = user_id.strip().lower()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT track_id, title, artist, album, duration, thumbnail, added_at "
                        "FROM user_favorites WHERE user_id = ? ORDER BY added_at DESC",
                        (uid,)
                    )
                    rows = cursor.fetchall()
                    return [{
                        "id": r["track_id"],
                        "title": r["title"],
                        "artist": r["artist"],
                        "album": r["album"],
                        "duration": r["duration"],
                        "thumbnail": r["thumbnail"],
                        "added_at": r["added_at"]
                    } for r in rows]
            except Exception as e:
                logger.error(f"Error getting favorites: {e}")
                return list(self._memory_cache["favorites"].get(uid, {}).values())

    def toggle_user_favorite(self, user_id: str, track: Dict[str, Any], remove: bool = False) -> Dict[str, Any]:
        uid = user_id.strip().lower()
        track_id = track.get("id")
        if not track_id:
            return {"status": "error", "message": "Missing track ID"}

        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    if remove:
                        cursor.execute("DELETE FROM user_favorites WHERE user_id = ? AND track_id = ?", (uid, track_id))
                        is_fav = False
                    else:
                        # Check existing
                        cursor.execute("SELECT 1 FROM user_favorites WHERE user_id = ? AND track_id = ?", (uid, track_id))
                        exists = cursor.fetchone()
                        if exists:
                            cursor.execute("DELETE FROM user_favorites WHERE user_id = ? AND track_id = ?", (uid, track_id))
                            is_fav = False
                        else:
                            cursor.execute("""
                                INSERT INTO user_favorites (user_id, track_id, title, artist, album, duration, thumbnail, added_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                uid, track_id, track.get("title", "Unknown"), track.get("artist", "Unknown"),
                                track.get("album", "Single"), track.get("duration", 0),
                                track.get("thumbnail", ""), now
                            ))
                            is_fav = True
                    conn.commit()
                    return {"status": "success", "is_favorite": is_fav, "track_id": track_id}
            except Exception as e:
                logger.error(f"Error toggling favorite: {e}")
                if uid not in self._memory_cache["favorites"]:
                    self._memory_cache["favorites"][uid] = {}
                favs = self._memory_cache["favorites"][uid]
                if track_id in favs:
                    favs.pop(track_id)
                    return {"status": "success", "is_favorite": False, "track_id": track_id}
                else:
                    favs[track_id] = track
                    return {"status": "success", "is_favorite": True, "track_id": track_id}

    # ---------------------------------------------------------
    # 3. Persistent Listening History & Smart Playlists
    # ---------------------------------------------------------
    def record_user_play(self, user_id: str, track: Dict[str, Any]) -> Dict[str, Any]:
        uid = user_id.strip().lower()
        track_id = track.get("id")
        if not track_id:
            return {"status": "error", "message": "Missing track ID"}

        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # Check if already played by user
                    cursor.execute(
                        "SELECT id, play_count FROM user_history WHERE user_id = ? AND track_id = ?",
                        (uid, track_id)
                    )
                    row = cursor.fetchone()
                    if row:
                        new_count = row["play_count"] + 1
                        cursor.execute("""
                            UPDATE user_history SET play_count = ?, played_at = ?,
                                title = ?, artist = ?, album = ?, duration = ?, thumbnail = ?
                            WHERE id = ?
                        """, (
                            new_count, now, track.get("title", "Unknown"), track.get("artist", "Unknown"),
                            track.get("album", "Single"), track.get("duration", 0), track.get("thumbnail", ""),
                            row["id"]
                        ))
                    else:
                        new_count = 1
                        cursor.execute("""
                            INSERT INTO user_history (user_id, track_id, title, artist, album, duration, thumbnail, played_at, play_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """, (
                            uid, track_id, track.get("title", "Unknown"), track.get("artist", "Unknown"),
                            track.get("album", "Single"), track.get("duration", 0), track.get("thumbnail", ""), now
                        ))
                    conn.commit()
                    return {"status": "success", "play_count": new_count, "track_id": track_id}
            except Exception as e:
                logger.error(f"Error recording play history: {e}")
                return {"status": "ok"}

    def get_user_history(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        uid = user_id.strip().lower()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT track_id, title, artist, album, duration, thumbnail, played_at, play_count
                        FROM user_history WHERE user_id = ? ORDER BY played_at DESC LIMIT ?
                    """, (uid, limit))
                    rows = cursor.fetchall()
                    return [{
                        "id": r["track_id"],
                        "title": r["title"],
                        "artist": r["artist"],
                        "album": r["album"],
                        "duration": r["duration"],
                        "thumbnail": r["thumbnail"],
                        "played_at": r["played_at"],
                        "play_count": r["play_count"]
                    } for r in rows]
            except Exception as e:
                logger.error(f"Error fetching history: {e}")
                return []

    def get_smart_playlists(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generates dynamic smart playlists:
        - "On Repeat": Tracks played >= 2 times, ranked by play count descending.
        - "Recently Played": Chronological order of last 20 played tracks.
        - "Jump Back In": Distinct recent tracks combined with high favorites.
        """
        uid = user_id.strip().lower()
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # 1. On Repeat
                    cursor.execute("""
                        SELECT track_id, title, artist, album, duration, thumbnail, play_count
                        FROM user_history
                        WHERE user_id = ? AND play_count >= 2
                        ORDER BY play_count DESC, played_at DESC
                        LIMIT 25;
                    """, (uid,))
                    on_repeat = [{
                        "id": r["track_id"],
                        "title": r["title"],
                        "artist": r["artist"],
                        "album": r["album"],
                        "duration": r["duration"],
                        "thumbnail": r["thumbnail"],
                        "play_count": r["play_count"]
                    } for r in cursor.fetchall()]

                    # 2. Recently Played
                    cursor.execute("""
                        SELECT track_id, title, artist, album, duration, thumbnail, played_at, play_count
                        FROM user_history
                        WHERE user_id = ?
                        ORDER BY played_at DESC
                        LIMIT 25;
                    """, (uid,))
                    recently_played = [{
                        "id": r["track_id"],
                        "title": r["title"],
                        "artist": r["artist"],
                        "album": r["album"],
                        "duration": r["duration"],
                        "thumbnail": r["thumbnail"],
                        "played_at": r["played_at"],
                        "play_count": r["play_count"]
                    } for r in cursor.fetchall()]

                    # 3. Jump Back In (Combination of top favorites and older plays)
                    cursor.execute("""
                        SELECT track_id, title, artist, album, duration, thumbnail, play_count
                        FROM user_history
                        WHERE user_id = ?
                        ORDER BY RANDOM()
                        LIMIT 15;
                    """, (uid,))
                    jump_back_in = [{
                        "id": r["track_id"],
                        "title": r["title"],
                        "artist": r["artist"],
                        "album": r["album"],
                        "duration": r["duration"],
                        "thumbnail": r["thumbnail"],
                        "play_count": r["play_count"]
                    } for r in cursor.fetchall()]

                    return {
                        "on_repeat": on_repeat,
                        "recently_played": recently_played,
                        "jump_back_in": jump_back_in
                    }
            except Exception as e:
                logger.error(f"Error generating smart playlists: {e}")
                return {"on_repeat": [], "recently_played": [], "jump_back_in": []}

library_store = LibraryStore()
