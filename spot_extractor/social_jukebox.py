"""
Social Listening & Access Control for SongBuddy.
Includes:
1. Guest Jukebox & Party Voting Mode:
   - Dynamic room creation (6-character party room codes, host secret keys).
   - Collaborative guest queue with duplicate song prevention and per-guest rate limits.
   - Real-time upvoting & downvoting with automatic queue re-sorting by popularity score.
   - Native SVG QR Code generation for one-tap mobile camera guest onboarding.
2. Expirable Public Share Links:
   - Cryptographically signed HMAC-SHA256 share tokens with expiration timestamps.
   - Read-only streaming resolution with granular audio download permissions.
"""

import os
import sys
import io
import time
import json
import base64
import hmac
import hashlib
import secrets
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path

from config import SECRET_KEY

logger = logging.getLogger("songbuddy.social_jukebox")


def generate_qr_svg(url: str, box_size: int = 8, border: int = 2) -> str:
    """
    Generates a crisp, high-contrast, scalable SVG QR code for the given URL.
    Uses qrcode library when available, with a resilient vector fallback.
    """
    try:
        import qrcode
        import qrcode.image.svg
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
            image_factory=qrcode.image.svg.SvgPathImage
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(attrib={"class": "jukebox-qr-svg", "style": "width:100%;height:100%;border-radius:12px;background:#000000;"})
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception as e:
        logger.warning(f"qrcode library SVG generation failed ({e}), using resilient vector placeholder SVG.")
        # Minimalist OLED vector fallback with finder patterns
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" class="jukebox-qr-svg" style="background:#000000;border-radius:12px;">
<rect width="200" height="200" fill="#000000"/>
<path d="M20 20h50v50h-50zM30 30h30v30h-30zM40 40h10v10h-10z" fill="#ffffff"/>
<path d="M130 20h50v50h-50zM140 30h30v30h-30zM150 40h10v10h-10z" fill="#ffffff"/>
<path d="M20 130h50v50h-50zM30 140h30v30h-30zM40 150h10v10h-10z" fill="#ffffff"/>
<rect x="90" y="20" width="20" height="20" fill="#ffffff"/>
<rect x="90" y="60" width="20" height="20" fill="#ffffff"/>
<rect x="20" y="90" width="20" height="20" fill="#ffffff"/>
<rect x="60" y="90" width="20" height="20" fill="#ffffff"/>
<rect x="130" y="90" width="50" height="20" fill="#ffffff"/>
<rect x="90" y="130" width="20" height="50" fill="#ffffff"/>
<rect x="140" y="140" width="40" height="40" fill="#ffffff"/>
</svg>'''


class JukeboxQueueItem:
    """Represents a single track queued in a Party Jukebox room."""
    def __init__(
        self,
        queue_id: str,
        track_id: str,
        title: str,
        artist: str,
        duration: int,
        thumbnail: str,
        added_by_id: str,
        added_by_name: str,
        stream_url: str = ""
    ):
        self.queue_id = queue_id
        self.track_id = track_id
        self.title = title
        self.artist = artist
        self.duration = duration
        self.thumbnail = thumbnail
        self.added_by_id = added_by_id
        self.added_by_name = added_by_name
        self.stream_url = stream_url
        self.added_at = time.time()
        self.upvotes: Set[str] = {added_by_id}  # Submitter automatically upvotes
        self.downvotes: Set[str] = set()

    @property
    def score(self) -> int:
        return len(self.upvotes) - len(self.downvotes)

    def to_dict(self, guest_id: Optional[str] = None) -> Dict[str, Any]:
        user_vote = None
        if guest_id:
            if guest_id in self.upvotes:
                user_vote = "up"
            elif guest_id in self.downvotes:
                user_vote = "down"

        return {
            "queue_id": self.queue_id,
            "track_id": self.track_id,
            "id": self.track_id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "stream_url": self.stream_url,
            "added_by_id": self.added_by_id,
            "added_by_name": self.added_by_name,
            "added_at": self.added_at,
            "upvotes_count": len(self.upvotes),
            "downvotes_count": len(self.downvotes),
            "score": self.score,
            "user_vote": user_vote
        }


class JukeboxRoom:
    """Represents an active Party Jukebox listening session."""
    def __init__(
        self,
        code: str,
        name: str,
        host_user_id: str,
        host_token: str,
        max_guest_songs: int = 5,
        allow_guest_enqueue: bool = True,
        auto_advance: bool = True
    ):
        self.code = code.upper()
        self.name = name
        self.host_user_id = host_user_id
        self.host_token = host_token
        self.max_guest_songs = max_guest_songs
        self.allow_guest_enqueue = allow_guest_enqueue
        self.auto_advance = auto_advance
        self.created_at = time.time()
        self.active_track: Optional[Dict[str, Any]] = None
        self.queue: List[JukeboxQueueItem] = []
        self._lock = threading.Lock()

    def sort_queue(self):
        """Sorts queue strictly by score descending, then added_at ascending."""
        self.queue.sort(key=lambda item: (-item.score, item.added_at))

    def enqueue_track(
        self,
        track_data: Dict[str, Any],
        guest_id: str,
        guest_name: str = "Party Guest"
    ) -> Dict[str, Any]:
        """
        Enqueues a new track with duplicate protection and rolling rate limiting.
        """
        with self._lock:
            if not self.allow_guest_enqueue and guest_id != self.host_user_id:
                raise ValueError("Guest submissions are currently paused by the host.")

            vid = str(track_data.get("id") or track_data.get("track_id") or "").strip()
            if not vid:
                raise ValueError("Missing valid track ID.")

            # 1. Duplicate check: track currently playing or already in queue
            if self.active_track and str(self.active_track.get("id")) == vid:
                raise ValueError("This song is currently playing on the jukebox.")

            for q in self.queue:
                if q.track_id == vid:
                    raise ValueError(f"'{q.title}' is already in the party queue. Cast an upvote instead!")

            # 2. Rate limit check: maximum N songs per guest in a rolling 10-minute window
            now = time.time()
            ten_mins_ago = now - 600
            guest_recent_count = sum(
                1 for q in self.queue if q.added_by_id == guest_id and q.added_at > ten_mins_ago
            )
            if guest_recent_count >= self.max_guest_songs and guest_id != self.host_user_id:
                raise ValueError(
                    f"Queue rate limit reached: Maximum {self.max_guest_songs} songs per guest. "
                    "Wait for your songs to play before submitting more."
                )

            # 3. Create queue item
            queue_id = f"q_{vid}_{secrets.token_hex(4)}"
            item = JukeboxQueueItem(
                queue_id=queue_id,
                track_id=vid,
                title=track_data.get("title", "Untitled Track"),
                artist=track_data.get("artist", "Unknown Artist"),
                duration=int(track_data.get("duration", 0)),
                thumbnail=track_data.get("thumbnail", ""),
                added_by_id=guest_id,
                added_by_name=guest_name or "Guest",
                stream_url=track_data.get("stream_url", "")
            )
            self.queue.append(item)
            self.sort_queue()
            return item.to_dict(guest_id=guest_id)

    def vote_track(
        self,
        queue_id: str,
        guest_id: str,
        direction: str = "up"
    ) -> Dict[str, Any]:
        """
        Records an upvote or downvote from a guest.
        Guests may vote once per track; repeating the same direction clears the vote.
        """
        with self._lock:
            target: Optional[JukeboxQueueItem] = None
            for item in self.queue:
                if item.queue_id == queue_id or item.track_id == queue_id:
                    target = item
                    break

            if not target:
                raise KeyError(f"Track with queue ID '{queue_id}' not found in party queue.")

            direction = direction.lower().strip()
            if direction == "up":
                if guest_id in target.upvotes:
                    target.upvotes.remove(guest_id)  # Toggle off
                else:
                    target.upvotes.add(guest_id)
                    target.downvotes.discard(guest_id)
            elif direction == "down":
                if guest_id in target.downvotes:
                    target.downvotes.remove(guest_id)  # Toggle off
                else:
                    target.downvotes.add(guest_id)
                    target.upvotes.discard(guest_id)
            elif direction == "clear":
                target.upvotes.discard(guest_id)
                target.downvotes.discard(guest_id)
            else:
                raise ValueError(f"Invalid vote direction '{direction}'. Must be 'up', 'down', or 'clear'.")

            self.sort_queue()
            return target.to_dict(guest_id=guest_id)

    def pop_next_track(self, host_token: str) -> Optional[Dict[str, Any]]:
        """Pops the top-voted track from the queue to become active_track."""
        with self._lock:
            if host_token != self.host_token:
                raise PermissionError("Invalid host authentication token.")

            if not self.queue:
                self.active_track = None
                return None

            top_item = self.queue.pop(0)
            self.active_track = top_item.to_dict()
            return self.active_track

    def remove_track(self, queue_id: str, requester_id: str, host_token: Optional[str] = None) -> bool:
        """Removes a track if requester is the submitter or the authenticated host."""
        with self._lock:
            for idx, item in enumerate(self.queue):
                if item.queue_id == queue_id or item.track_id == queue_id:
                    is_host = host_token and (host_token == self.host_token)
                    is_owner = item.added_by_id == requester_id
                    if is_host or is_owner:
                        self.queue.pop(idx)
                        return True
                    else:
                        raise PermissionError("Only the track submitter or room host may remove this track.")
            return False

    def clear_queue(self, host_token: str) -> int:
        """Clears all tracks from the party queue."""
        with self._lock:
            if host_token != self.host_token:
                raise PermissionError("Invalid host authentication token.")
            count = len(self.queue)
            self.queue.clear()
            return count

    def to_dict(self, guest_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            return {
                "room_code": self.code,
                "name": self.name,
                "host_user_id": self.host_user_id,
                "created_at": self.created_at,
                "allow_guest_enqueue": self.allow_guest_enqueue,
                "max_guest_songs": self.max_guest_songs,
                "auto_advance": self.auto_advance,
                "active_track": self.active_track,
                "total_queued": len(self.queue),
                "queue": [item.to_dict(guest_id=guest_id) for item in self.queue]
            }


class JukeboxManager:
    """Manages active Party Jukebox rooms, guest sessions, and QR codes."""
    def __init__(self):
        self._rooms: Dict[str, JukeboxRoom] = {}
        self._lock = threading.Lock()
        self._init_default_room()

    def _init_default_room(self):
        """Initializes default party room for instant onboarding."""
        default_code = "PARTY1"
        self._rooms[default_code] = JukeboxRoom(
            code=default_code,
            name="SongBuddy VIP Lounge",
            host_user_id="usr_dave_cooper",
            host_token=secrets.token_hex(16),
            max_guest_songs=5
        )

    def create_room(
        self,
        host_user_id: str = "usr_dave_cooper",
        name: str = "SongBuddy VIP Lounge",
        max_guest_songs: int = 5,
        custom_code: Optional[str] = None
    ) -> Tuple[JukeboxRoom, str]:
        """Creates a new Jukebox room with a unique 6-character room code."""
        with self._lock:
            code = custom_code.upper().strip() if custom_code else None
            if not code or code in self._rooms:
                # Generate unique code
                for _ in range(100):
                    cand = secrets.token_hex(3).upper()  # 6 chars
                    if cand not in self._rooms:
                        code = cand
                        break
                if not code:
                    code = f"RM{int(time.time()) % 10000}"

            host_token = secrets.token_hex(16)
            room = JukeboxRoom(
                code=code,
                name=name or "SongBuddy VIP Lounge",
                host_user_id=host_user_id,
                host_token=host_token,
                max_guest_songs=max(1, min(20, max_guest_songs))
            )
            self._rooms[code] = room
            logger.info(f"Created Party Jukebox Room {code} ('{name}')")
            return room, host_token

    def get_room(self, code: str) -> Optional[JukeboxRoom]:
        """Retrieves a room by its code (case-insensitive)."""
        if not code:
            return None
        return self._rooms.get(code.upper().strip())

    def get_or_create_room(self, code: str = "PARTY1") -> JukeboxRoom:
        """Retrieves existing room or creates default."""
        room = self.get_room(code)
        if room:
            return room
        room, _ = self.create_room(custom_code=code)
        return room

    def list_rooms(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._rooms.values()]


# --------------------------------------------------------------------------
# 2. Expirable Public Share Links Engine
# --------------------------------------------------------------------------
class ShareLinkManager:
    """
    Mints and resolves cryptographically signed, expirable read-only share links.
    Allows non-authenticated guests to stream specific tracks or playlists.
    """
    def __init__(self, secret_key: str = SECRET_KEY):
        self._secret_key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key

    def mint_token(
        self,
        item_type: str,
        item_id: str,
        title: str = "",
        artist: str = "",
        duration_hours: int = 24,
        allow_download: bool = True,
        created_by: str = "host"
    ) -> Dict[str, Any]:
        """
        Mints a tamper-proof signed share token with an expiration timestamp.
        """
        now = int(time.time())
        exp_hours = max(1, min(168, duration_hours))  # 1 hour to 7 days
        exp_ts = now + (exp_hours * 3600)

        payload = {
            "t": item_type,         # 'track' or 'playlist'
            "id": item_id,
            "title": title,
            "artist": artist,
            "dl": bool(allow_download),
            "exp": exp_ts,
            "iat": now,
            "by": created_by
        }

        raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
        sig = hmac.new(self._secret_key, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        token = f"{b64_payload}.{sig}"

        return {
            "status": "success",
            "token": token,
            "item_type": item_type,
            "item_id": item_id,
            "title": title,
            "artist": artist,
            "expires_at_timestamp": exp_ts,
            "duration_hours": exp_hours,
            "allow_download": allow_download,
            "share_url": f"/#share={token}"
        }

    def resolve_token(self, token: str) -> Dict[str, Any]:
        """
        Verifies cryptographic integrity and validates expiration of share tokens.
        """
        if not token or "." not in token:
            return {"valid": False, "status": "invalid_format", "message": "Malformed share token."}

        parts = token.strip().split(".")
        if len(parts) != 2:
            return {"valid": False, "status": "invalid_format", "message": "Malformed share token."}

        b64_payload, signature = parts
        expected_sig = hmac.new(self._secret_key, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

        if not hmac.compare_digest(signature, expected_sig):
            return {"valid": False, "status": "invalid_signature", "message": "Cryptographic signature check failed."}

        # Pad base64 if needed
        padding = 4 - (len(b64_payload) % 4)
        if padding != 4:
            b64_payload += "=" * padding

        try:
            payload_bytes = base64.urlsafe_b64decode(b64_payload)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            return {"valid": False, "status": "decode_error", "message": f"Token payload decode error: {e}"}

        now = int(time.time())
        exp_ts = int(payload.get("exp", 0))

        if now > exp_ts:
            return {
                "valid": False,
                "status": "expired",
                "message": "This public share link has expired.",
                "expired_seconds_ago": now - exp_ts,
                "item_id": payload.get("id")
            }

        seconds_left = exp_ts - now
        hours_left = round(seconds_left / 3600, 1)

        item_id = payload.get("id")
        item_type = payload.get("t", "track")
        allow_download = payload.get("dl", True)

        return {
            "valid": True,
            "status": "active",
            "item_type": item_type,
            "item_id": item_id,
            "title": payload.get("title", ""),
            "artist": payload.get("artist", ""),
            "allow_download": allow_download,
            "seconds_remaining": seconds_left,
            "hours_remaining": hours_left,
            "stream_endpoint": f"/api/stream?id={item_id}" if item_type == "track" else None,
            "message": f"Active share link ({hours_left} hours remaining)."
        }


# Global Singletons
jukebox_manager = JukeboxManager()
share_link_manager = ShareLinkManager()
