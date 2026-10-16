"""
Spotify-Modeled Multi-Stage Hybrid Recommendation Engine for SongBuddy.
Deconstructed from Spotify's production recommendation pipeline:
- Latent Acoustic Vector Representation (5D Mel-spectrogram features)
- Sub-millisecond Annoy approximate nearest neighbors (random projection hyperplane trees)
- BaRT (Bandits for Recommendations as Treatments) contextual multi-armed bandit
- Dynamic Sub-Taste Clustering for Daily Mixes 1-6
- High-novelty Discover Weekly generation
- Regional & Linguistic Context Detection (Hindi/Bollywood/Punjabi coherence)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recommender import (
    AcousticVector,
    AnnoyIndexNode,
    AnnoyIndexSimulator,
    BaRTContextualBandit,
    RecommendationEngine,
    recommendation_engine,
    format_duration,
    is_indian_hindi_track,
    is_blatant_western_track,
    HINDI_KEYWORDS,
    INDIAN_ARTISTS,
    BLATANT_WESTERN_ARTISTS,
)

__all__ = [
    "AcousticVector",
    "AnnoyIndexNode",
    "AnnoyIndexSimulator",
    "BaRTContextualBandit",
    "RecommendationEngine",
    "recommendation_engine",
    "format_duration",
    "is_indian_hindi_track",
    "is_blatant_western_track",
    "HINDI_KEYWORDS",
    "INDIAN_ARTISTS",
    "BLATANT_WESTERN_ARTISTS",
]
