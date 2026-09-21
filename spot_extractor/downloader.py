import shutil
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

try:
    from . import config
except ImportError:
    import config

def sanitize_filename(name: str) -> str:
    """Removes filesystem-incompatible characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_track_audio(meta: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """
    Validates FFmpeg availability, searches YouTube for matching audio,
    extracts the audio stream, and converts to 320kbps MP3.
    """
    # Validate FFmpeg before initiating search or download
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "System dependency 'ffmpeg' not found in PATH. "
            "FFmpeg is required to extract and convert audio to MP3."
        )

    target_dir = output_dir or (config.get_download_dir() if hasattr(config, "get_download_dir") else config.DOWNLOAD_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    filename_base = sanitize_filename(f"{meta['primary_artist']} - {meta['title']}")
    final_output_path = target_dir / f"{filename_base}.mp3"

    # Search query prioritization
    query = f"{meta['primary_artist']} - {meta['title']} audio"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(target_dir / f"{filename_base}.%(ext)s"),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
    }

    # Fetch 5 search candidates to find the closest match by duration
    search_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(search_opts) as searcher:
        search_results = searcher.extract_info(f"ytsearch5:{query}", download=False)
        entries = search_results.get('entries', [])

    selected_video_url = None
    if entries:
        best_candidate = None
        min_diff = float("inf")
        target_duration = meta.get("duration_sec", 0)

        for entry in entries:
            cand_dur = entry.get("duration")
            if cand_dur is not None:
                diff = abs(cand_dur - target_duration)
                # Within +- 8 seconds threshold
                if diff < min_diff and diff <= 8.0:
                    min_diff = diff
                    best_candidate = entry

        selected_video_url = (best_candidate or entries[0]).get("url")

    # Fallback to direct search if search parsing didn't locate a URL
    download_target = selected_video_url or f"ytsearch1:{query}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([download_target])

    # 1. Exact match
    if final_output_path.exists():
        return final_output_path

    # 2. Check for intermediate files (FFmpeg conversion failure diagnostic)
    for ext in ['webm', 'm4a', 'opus', 'ogg', 'aac']:
        intermediate = target_dir / f"{filename_base}.{ext}"
        if intermediate.exists():
            raise RuntimeError(
                f"Audio was downloaded to '{intermediate}', but FFmpeg conversion to MP3 failed or did not run."
            )

    # 3. Check for yt-dlp sanitized variant
    matching_mp3s = list(target_dir.glob(f"*{filename_base[:20]}*.mp3"))
    if matching_mp3s:
        return matching_mp3s[0]

    raise FileNotFoundError(f"Expected output file '{final_output_path}' was not created.")
