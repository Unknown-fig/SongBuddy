import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TSRC, APIC, error

# Image size bounds: 100 bytes minimum, 12 MB maximum
MIN_IMAGE_BYTES = 100
MAX_IMAGE_BYTES = 12 * 1024 * 1024

def validate_image_data(data: bytes) -> Optional[str]:
    """
    Validates binary payload size and detects MIME type via magic bytes.
    Returns MIME string if valid, or None if invalid or corrupt.
    """
    if not data or len(data) < MIN_IMAGE_BYTES or len(data) > MAX_IMAGE_BYTES:
        return None

    # JPEG: 0xFF 0xD8 0xFF
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG: 0x89 PNG \r \n 0x1A \n
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # WebP: 'RIFF' .... 'WEBP'
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"

    return None

def fetch_cover_art_with_retry(cover_url: str, max_retries: int = 2) -> Optional[Tuple[bytes, str]]:
    """
    Downloads cover artwork with transient retry backoff and validates image payload.
    """
    for attempt in range(max_retries + 1):
        try:
            with requests.Session() as session:
                resp = session.get(cover_url, timeout=(3.0, 8.0))
                if resp.status_code == 200:
                    mime = validate_image_data(resp.content)
                    if mime:
                        return resp.content, mime
                    print("Warning: Cover art payload failed validation (invalid magic bytes or size).")
                    return None
                elif resp.status_code in (404, 410):
                    return None
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                time.sleep(0.4 * (attempt + 1))
            else:
                print(f"Warning: Failed to fetch album artwork after {max_retries + 1} attempts: {e}")
        except Exception as e:
            print(f"Warning: Unexpected error fetching album artwork: {e}")
            break
    return None

def apply_id3_tags(file_path: Path, meta: Dict[str, Any]) -> None:
    """Injects ID3v2 tags and validated high-resolution album art into an MP3 file."""
    audio = MP3(str(file_path), ID3=ID3)
    
    try:
        audio.add_tags()
    except error:
        pass

    # Text metadata
    audio.tags.add(TIT2(encoding=3, text=meta.get("title", "Unknown Title")))
    artists = meta.get("artists", [meta.get("primary_artist", "Unknown Artist")])
    audio.tags.add(TPE1(encoding=3, text="/".join(artists)))
    audio.tags.add(TALB(encoding=3, text=meta.get("album", "Unknown Album")))
    audio.tags.add(TDRC(encoding=3, text=str(meta.get("release_date", ""))))
    
    track_num = meta.get("track_number", 1)
    total_tracks = meta.get("total_tracks", 1)
    audio.tags.add(TRCK(encoding=3, text=f"{track_num}/{total_tracks}"))
    
    if meta.get("isrc"):
        audio.tags.add(TSRC(encoding=3, text=meta["isrc"]))

    # High-resolution cover art injection with validation & retry
    cover_url = meta.get("cover_url")
    if cover_url:
        result = fetch_cover_art_with_retry(cover_url)
        if result:
            img_data, mime = result
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # Front cover
                    desc="Cover",
                    data=img_data
                )
            )

    audio.save(v2_version=3)
