import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Support both MCP 1.x and 2.x
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer as FastMCP


try:
    from spot_extractor import config
    from spot_extractor.metadata import clean_spotify_url, fetch_track_metadata, fetch_playlist_tracks
    from spot_extractor.downloader import download_track_audio
    from spot_extractor.tagger import apply_id3_tags
except ModuleNotFoundError as e:
    if e.name in ("spot_extractor", "config", "metadata", "downloader", "tagger"):
        import config
        from metadata import clean_spotify_url, fetch_track_metadata, fetch_playlist_tracks
        from downloader import download_track_audio
        from tagger import apply_id3_tags
    else:
        raise

# Initialize FastMCP Server
mcp = FastMCP("spot-extractor-engine")

ROOT_DIR = Path(__file__).parent.parent.resolve()

def validate_output_directory(dir_str: str) -> Path:
    """
    Safely resolves and validates a custom output directory against path traversal.
    Ensures writes stay within user workspace, home directory, or download directory,
    and explicitly blocks attempts targeting sensitive system roots.
    """
    default_dir = config.get_download_dir() if hasattr(config, "get_download_dir") else config.DOWNLOAD_DIR
    if not dir_str or not dir_str.strip():
        return default_dir

    resolved = Path(dir_str.strip()).resolve()

    # Block sensitive system directories
    disallowed_roots = [
        Path("C:/Windows").resolve(),
        Path("C:/Program Files").resolve(),
        Path("C:/Program Files (x86)").resolve(),
        Path("/etc").resolve(),
        Path("/bin").resolve(),
        Path("/sbin").resolve(),
        Path("/usr").resolve(),
        Path("/var").resolve(),
        Path("/sys").resolve(),
        Path("/proc").resolve(),
    ]

    for disallowed in disallowed_roots:
        if resolved == disallowed or disallowed in resolved.parents:
            raise PermissionError(f"Access to sensitive system directory '{resolved}' is forbidden.")

    # Allow if inside project workspace, user home directory, or default download directory
    allowed_bases = [
        ROOT_DIR,
        Path.home().resolve(),
        default_dir.resolve()
    ]

    if not any(resolved == base or base in resolved.parents for base in allowed_bases):
        raise PermissionError(
            f"Path traversal detected: Target directory '{resolved}' is outside allowed workspace or user home folders."
        )

    resolved.mkdir(parents=True, exist_ok=True)
    return resolved

@mcp.tool()
def inspect_spotify_url(spotify_url: str) -> str:
    """
    Parses a Spotify track or playlist URL and inspects its canonical metadata 
    (Artist, Title, Album, Duration, ISRC) without downloading anything.
    """
    try:
        config.validate_environment()
        entity_type, entity_id = clean_spotify_url(spotify_url)
        
        if entity_type == "track":
            meta = fetch_track_metadata(entity_id)
            return json.dumps({"type": "track", "data": meta}, indent=2)
        elif entity_type == "playlist":
            tracks = fetch_playlist_tracks(entity_id)
            return json.dumps({
                "type": "playlist", 
                "total_tracks": len(tracks), 
                "tracks": tracks[:15] # Return first 15 for context efficiency
            }, indent=2)
        else:
            return json.dumps({"error": f"Unsupported entity type: {entity_type}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def download_spotify_track(spotify_url: str, custom_output_dir: str = "") -> str:
    """
    Takes a Spotify track URL, resolves the stream via yt-dlp, 
    downloads it as an MP3, and embeds ID3 tags and cover art.
    Enforces path traversal validation on custom_output_dir.
    """
    try:
        config.validate_environment()
        entity_type, entity_id = clean_spotify_url(spotify_url)
        if entity_type != "track":
            return json.dumps({"error": f"Expected track URL, got: {entity_type}"})

        out_path = validate_output_directory(custom_output_dir)
        meta = fetch_track_metadata(entity_id)
        mp3_file = download_track_audio(meta, out_path)
        apply_id3_tags(mp3_file, meta)

        return json.dumps({
            "status": "success",
            "file_path": str(mp3_file),
            "artist": meta["primary_artist"],
            "title": meta["title"]
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    # Runs the MCP server over standard stdio for agents
    mcp.run()
