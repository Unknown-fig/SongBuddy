"""
Buddy Feed & Social Listening Engine for SongBuddy.
Modeled after Spotify Desktop's buddy-feed.spa & Dealer Push Architecture.

Features:
1. Real-time Friend Activity Stream:
   - Tracks what friends/contacts are currently playing.
   - Dynamic listening states: track title, artist, album, thumbnail, playback progress, and timestamp.
   - Animated audio soundwave state indicators.
2. "Listen Along" Playback Synchronization:
   - 1-click sync allowing any user to immediately jump into a friend's active track.
3. Private Session & Listening Broadcast Control:
   - Granular privacy toggle allowing users to suppress social broadcast.
4. Social Graph Management:
   - Follow, unfollow, and query friends and active listeners.
5. Dealer-style Event Push & Stream:
   - SSE and real-time event dispatch for live UI updates without polling overhead.
"""

import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("songbuddy.buddy_feed")


class BuddyProfile:
    """Represents a friend or community profile."""
    def __init__(
        self,
        user_id: str,
        display_name: str,
        avatar: str,
        bio: str = "",
        is_verified: bool = False
    ):
        self.user_id = user_id
        self.display_name = display_name
        self.avatar = avatar
        self.bio = bio
        self.is_verified = is_verified


class FriendActivity:
    """Represents a real-time listening activity record."""
    def __init__(
        self,
        user_id: str,
        display_name: str,
        avatar: str,
        track_id: str,
        title: str,
        artist: str,
        album: str = "",
        thumbnail: str = "",
        duration: int = 0,
        progress_seconds: int = 0,
        is_playing: bool = True,
        context_title: str = "",
        context_uri: str = "",
        timestamp: Optional[float] = None
    ):
        self.user_id = user_id
        self.display_name = display_name
        self.avatar = avatar
        self.track_id = track_id
        self.title = title
        self.artist = artist
        self.album = album or "Single"
        self.thumbnail = thumbnail
        self.duration = duration
        self.progress_seconds = progress_seconds
        self.is_playing = is_playing
        self.context_title = context_title or "SongBuddy Stream"
        self.context_uri = context_uri or f"songbuddy://track/{track_id}"
        self.timestamp = timestamp if timestamp is not None else time.time()

    def to_dict(self) -> Dict[str, Any]:
        now = time.time()
        elapsed = max(0, int(now - self.timestamp))
        if self.is_playing and elapsed < 300:
            time_ago_str = "Listening now"
        elif elapsed < 60:
            time_ago_str = "Just now"
        elif elapsed < 3600:
            time_ago_str = f"{elapsed // 60}m ago"
        elif elapsed < 86400:
            time_ago_str = f"{elapsed // 3600}h ago"
        else:
            time_ago_str = f"{elapsed // 86400}d ago"

        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "avatar": self.avatar,
            "track_id": self.track_id,
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "progress_seconds": self.progress_seconds,
            "is_playing": self.is_playing,
            "context_title": self.context_title,
            "context_uri": self.context_uri,
            "timestamp": self.timestamp,
            "time_ago_str": time_ago_str,
            "equalizer_active": self.is_playing and (elapsed < 600)
        }


class BuddyFeedManager:
    """
    Coordinates friend activity feeds, real-time broadcasts,
    and Spotify-modeled Buddy Feed social events.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._activities: Dict[str, FriendActivity] = {}
        self._profiles: Dict[str, BuddyProfile] = {}
        self._user_following: Dict[str, Set[str]] = {}  # user_id -> set of followed user_ids
        self._private_sessions: Set[str] = set()       # user_ids that disabled social sharing
        self._subscribers: List[threading.Event] = []
        self._seed_default_friends()

    def _seed_default_friends(self):
        """Initializes vibrant default friends matching Spotify's desktop friend feed."""
        now = time.time()
        seed_data = [
            {
                "user_id": "usr_elena",
                "display_name": "Elena Rostova",
                "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80",
                "bio": "Ambient & Synthwave Producer",
                "track": {
                    "id": "4NRXx6U8ABQ",
                    "title": "Blinding Lights",
                    "artist": "The Weeknd",
                    "album": "After Hours",
                    "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg",
                    "duration": 200,
                    "progress_seconds": 45,
                    "is_playing": True,
                    "context_title": "Synthwave Highway",
                    "context_uri": "sp://playlist/synthwave",
                    "time_offset": -25
                }
            },
            {
                "user_id": "usr_marcus",
                "display_name": "Marcus Vance",
                "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
                "bio": "Audio Engineer & Lo-Fi Enthusiast",
                "track": {
                    "id": "kTJczUoc26U",
                    "title": "In My Feelings",
                    "artist": "Camila Cabello",
                    "album": "Romance Deluxe",
                    "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg",
                    "duration": 220,
                    "progress_seconds": 110,
                    "is_playing": True,
                    "context_title": "Late Night Vibe",
                    "context_uri": "sp://playlist/late_night",
                    "time_offset": -80
                }
            },
            {
                "user_id": "usr_chloe",
                "display_name": "Chloe Lin",
                "avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
                "bio": "Basslines & Hyperpop",
                "track": {
                    "id": "jfKfPfyJRdk",
                    "title": "Lofi Hip Hop Radio",
                    "artist": "Lofi Girl",
                    "album": "Peaceful Beats",
                    "thumbnail": "https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg",
                    "duration": 180,
                    "progress_seconds": 90,
                    "is_playing": True,
                    "context_title": "Deep Focus Studio",
                    "context_uri": "sp://album/peaceful_beats",
                    "time_offset": -150
                }
            },
            {
                "user_id": "usr_liam",
                "display_name": "Liam Thorne",
                "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
                "bio": "Electronic & Indie Explorer",
                "track": {
                    "id": "fJ9rUzIMcZQ",
                    "title": "Bohemian Rhapsody",
                    "artist": "Queen",
                    "album": "A Night at the Opera",
                    "thumbnail": "https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg",
                    "duration": 354,
                    "progress_seconds": 210,
                    "is_playing": False,
                    "context_title": "Classic Rock Legends",
                    "context_uri": "sp://playlist/rock_legends",
                    "time_offset": -1200
                }
            }
        ]

        for s in seed_data:
            self._profiles[s["user_id"]] = BuddyProfile(
                user_id=s["user_id"],
                display_name=s["display_name"],
                avatar=s["avatar"],
                bio=s["bio"]
            )
            tr = s["track"]
            self._activities[s["user_id"]] = FriendActivity(
                user_id=s["user_id"],
                display_name=s["display_name"],
                avatar=s["avatar"],
                track_id=tr["id"],
                title=tr["title"],
                artist=tr["artist"],
                album=tr["album"],
                thumbnail=tr["thumbnail"],
                duration=tr["duration"],
                progress_seconds=tr["progress_seconds"],
                is_playing=tr["is_playing"],
                context_title=tr["context_title"],
                context_uri=tr["context_uri"],
                timestamp=now + tr["time_offset"]
            )

    def set_private_session(self, user_id: str, enabled: bool) -> bool:
        """Enables or disables private session for a user (hides listening presence)."""
        uid = (user_id or "dave").strip().lower()
        with self._lock:
            if enabled:
                self._private_sessions.add(uid)
            else:
                self._private_sessions.discard(uid)
            return uid in self._private_sessions

    def is_private_session(self, user_id: str) -> bool:
        uid = (user_id or "dave").strip().lower()
        with self._lock:
            return uid in self._private_sessions

    def update_user_activity(
        self,
        user_id: str,
        display_name: str,
        avatar: str,
        track_data: Dict[str, Any],
        is_playing: bool = True,
        progress_seconds: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Broadcasts user's current track to the social feed.
        Honors private session setting.
        """
        uid = (user_id or "dave").strip().lower()
        if self.is_private_session(uid):
            logger.info(f"User '{uid}' is in Private Session; suppressing Buddy Feed broadcast.")
            return None

        track_id = str(track_data.get("id") or track_data.get("track_id") or "").strip()
        if not track_id:
            return None

        title = track_data.get("title", "Unknown Track")
        artist = track_data.get("artist", "Unknown Artist")
        album = track_data.get("album", "SongBuddy Studio")
        thumbnail = track_data.get("thumbnail") or f"https://i.ytimg.com/vi/{track_id}/hqdefault.jpg"
        duration = int(track_data.get("duration", 0))

        with self._lock:
            activity = FriendActivity(
                user_id=uid,
                display_name=display_name or uid.capitalize(),
                avatar=avatar or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
                track_id=track_id,
                title=title,
                artist=artist,
                album=album,
                thumbnail=thumbnail,
                duration=duration,
                progress_seconds=progress_seconds,
                is_playing=is_playing,
                context_title="SongBuddy Studio Session",
                timestamp=time.time()
            )
            self._activities[uid] = activity
            self._profiles[uid] = BuddyProfile(
                user_id=uid,
                display_name=display_name or uid.capitalize(),
                avatar=activity.avatar
            )

        logger.info(f"Broadcasted listening activity for user '{uid}': {title} by {artist}")
        return activity.to_dict()

    def follow_friend(self, user_id: str, friend_id: str, friend_name: str = "") -> bool:
        """Adds a friend to user's followed list."""
        uid = (user_id or "dave").strip().lower()
        fid = friend_id.strip().lower()
        if not fid or uid == fid:
            return False

        with self._lock:
            if uid not in self._user_following:
                self._user_following[uid] = set(self._profiles.keys())
            self._user_following[uid].add(fid)
            if fid not in self._profiles:
                self._profiles[fid] = BuddyProfile(
                    user_id=fid,
                    display_name=friend_name or fid.capitalize(),
                    avatar=f"https://api.dicebear.com/7.x/identicon/svg?seed={fid}"
                )
        return True

    def unfollow_friend(self, user_id: str, friend_id: str) -> bool:
        """Removes a friend from user's followed list."""
        uid = (user_id or "dave").strip().lower()
        fid = friend_id.strip().lower()
        with self._lock:
            if uid in self._user_following:
                self._user_following[uid].discard(fid)
                return True
        return False

    def get_feed(self, user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves friend activity feed sorted by:
        1. Actively playing songs first
        2. Recency of timestamp descending
        """
        uid = (user_id or "dave").strip().lower()
        with self._lock:
            following = self._user_following.get(uid)
            activities = list(self._activities.values())

            # Filter if user has explicit following set, else show community feed
            if following:
                filtered = [a for a in activities if a.user_id in following and a.user_id != uid]
            else:
                filtered = [a for a in activities if a.user_id != uid]

            # Sort: actively playing first, then newest timestamp
            filtered.sort(key=lambda a: (not a.is_playing, -a.timestamp))
            return [a.to_dict() for a in filtered[:limit]]

    def get_listen_along(self, friend_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches full track details for instant 'Listen Along' playback sync.
        """
        fid = friend_id.strip().lower()
        with self._lock:
            activity = self._activities.get(fid)
            if not activity:
                return None
            return {
                "friend_user_id": activity.user_id,
                "friend_name": activity.display_name,
                "track": {
                    "id": activity.track_id,
                    "title": activity.title,
                    "artist": activity.artist,
                    "album": activity.album,
                    "thumbnail": activity.thumbnail,
                    "duration": activity.duration,
                    "progress_seconds": activity.progress_seconds
                },
                "is_playing": activity.is_playing,
                "synced_at": time.time()
            }

    def get_summary_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        feed = self.get_feed(user_id=user_id)
        active_count = sum(1 for item in feed if item["equalizer_active"])
        uid = (user_id or "dave").strip().lower()
        return {
            "total_friends": len(feed),
            "active_listening_count": active_count,
            "private_session": self.is_private_session(uid)
        }


# Global Singleton Instance
buddy_feed_manager = BuddyFeedManager()
