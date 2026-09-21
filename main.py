import sys
import argparse
from pathlib import Path
from typing import Union, Dict, Any, Optional

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import config
    from metadata import clean_spotify_url, fetch_track_metadata, fetch_playlist_tracks
    from downloader import download_track_audio
    from tagger import apply_id3_tags
except ImportError:
    from spot_extractor import config
    from spot_extractor.metadata import clean_spotify_url, fetch_track_metadata, fetch_playlist_tracks
    from spot_extractor.downloader import download_track_audio
    from spot_extractor.tagger import apply_id3_tags

def process_single_track(track_or_meta: Union[str, Dict[str, Any]], output_dir: Optional[Path] = None) -> Path:
    """
    Downloads and tags a single track.
    If track_or_meta is a dict (pre-fetched from playlist), re-fetching is skipped.
    If track_or_meta is a string (track ID or URL), metadata is fetched.
    Propagates output_dir to audio downloader.
    """
    if isinstance(track_or_meta, dict):
        meta = track_or_meta
    else:
        meta = fetch_track_metadata(track_or_meta)

    dest_dir = output_dir or (config.get_download_dir() if hasattr(config, "get_download_dir") else config.DOWNLOAD_DIR)
    print(f"-> Identified: {meta['primary_artist']} - {meta['title']} ({meta.get('duration_sec', 0):.0f}s)")
    print("   Searching & downloading audio stream...")
    mp3_path = download_track_audio(meta, output_dir=dest_dir)
    print("   Writing ID3 tags and album artwork...")
    apply_id3_tags(mp3_path, meta)
    print(f"✓ Saved: {mp3_path.name}")
    return mp3_path

def main():
    parser = argparse.ArgumentParser(description="SongBuddy / Spot-Extractor Spotify Downloader")
    parser.add_argument("url", help="Spotify track or playlist URL")
    parser.add_argument("-o", "--output", dest="output_dir", default=None, help="Custom output directory for downloaded MP3s")
    args = parser.parse_args()

    custom_out = Path(args.output_dir).resolve() if args.output_dir else None

    try:
        config.validate_environment()
        entity_type, entity_id = clean_spotify_url(args.url)

        if entity_type == "track":
            process_single_track(entity_id, output_dir=custom_out)
        elif entity_type == "playlist":
            tracks = fetch_playlist_tracks(entity_id)
            print(f"Loaded playlist with {len(tracks)} tracks.\n")
            successful = 0
            failed = []

            for idx, track_meta in enumerate(tracks, 1):
                print(f"[{idx}/{len(tracks)}] Processing: {track_meta['primary_artist']} - {track_meta['title']}")
                try:
                    # Pass pre-fetched track_meta to prevent duplicate API calls, and propagate output_dir
                    process_single_track(track_meta, output_dir=custom_out)
                    successful += 1
                except Exception as track_err:
                    print(f"✗ Failed to download track [{track_meta['title']}]: {track_err}")
                    failed.append((track_meta.get("title", "Unknown"), str(track_err)))

            print("\n--- Playlist Download Summary ---")
            print(f"Successfully processed: {successful}/{len(tracks)} tracks")
            if failed:
                print(f"Failed tracks ({len(failed)}):")
                for name, err in failed:
                    print(f"  - {name}: {err}")
        else:
            print(f"Entity type '{entity_type}' is not yet supported in this build.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

