"""
Network Resilience & Anti-Bot Infrastructure for SongBuddy (spot_extractor package mirror).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network_resilience import (
    CookiePoolManager,
    cookie_pool_manager,
    AudioDiskCacheManager,
    audio_disk_cache,
    fetch_sponsorblock_segments,
    inspect_cookie_health,
    get_cdn_signature_expiration,
    trigger_cdn_signature_recovery
)

__all__ = [
    "CookiePoolManager",
    "cookie_pool_manager",
    "AudioDiskCacheManager",
    "audio_disk_cache",
    "fetch_sponsorblock_segments",
    "inspect_cookie_health",
    "get_cdn_signature_expiration",
    "trigger_cdn_signature_recovery"
]
