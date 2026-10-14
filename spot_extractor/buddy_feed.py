"""
Buddy Feed & Social Listening Engine for SongBuddy (spot_extractor package mirror).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from buddy_feed import (
    BuddyProfile,
    FriendActivity,
    BuddyFeedManager,
    buddy_feed_manager
)

__all__ = ["BuddyProfile", "FriendActivity", "BuddyFeedManager", "buddy_feed_manager"]
