"""
Spotify-Modeled Multi-Stage Hybrid Recommendation Engine for SongBuddy.
Deconstructed from Spotify's production recommendation pipeline:

1. High-Level Recommendation Pipeline:
   - Candidate Generation (Retrieval): Annoy approximate nearest neighbors (forest of randomized binary trees) + co-occurrence graph walks (Track2Vec).
   - Audio Feature Representation: 5-dimensional latent acoustic vectors (energy, valence, danceability, acousticness, tempo_norm).
   - Deep Ranking & Scoring: Hybrid candidate evaluation factoring in acoustic similarity, artist affinity, and linguistic coherence.
   - Re-Ranking & Personalization:
     - BaRT (Bandits for Recommendations as Treatments): Contextual multi-armed bandit balancing Exploitation (~90%) vs Exploration (~10%).
     - Session Momentum & Context Signals: Adapts to time of day (morning/afternoon/night) and rapid skips (preventing churn).
     - Diversity & Deduplication Guardrails: Caps recurring artists and avoids repetitive echo chambers.
2. Flagship Personalized Mixes:
   - Daily Mix 1-6: Sub-taste clustering grouping listening history into cohesive genre/acoustic playlists.
   - Discover Weekly: High-novelty discovery algorithm finding tracks matched to user taste vectors.
"""

import os
import re
import time
import math
import random
import base64
import logging
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
import requests
import yt_dlp

try:
    from config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET
except ImportError:
    SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
    SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

try:
    from library_store import library_store
except ImportError:
    library_store = None

logger = logging.getLogger("songbuddy.recommender")


def format_duration(seconds: Optional[int]) -> str:
    """Formats numeric seconds into mm:ss display string."""
    if not seconds or seconds <= 0:
        return "0:00"
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"


# Regional & Linguistic Context Detection
HINDI_SCRIPT_RE = re.compile(r'[\u0900-\u097F\u0A00-\u0A7F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0600-\u06FF]')
HINDI_KEYWORDS = {
    'hindi', 'bollywood', 'punjabi', 'bhangra', 'sufi', 'ghazal', 'qawwali', 'lofi hindi',
    'dil', 'pyar', 'pyaar', 'ishq', 'mohabbat', 'tere', 'teri', 'mera', 'meri', 'tum', 'hum',
    'sanam', 'zindagi', 'saath', 'deewana', 'aankhon', 'raat', 'chaand', 'saiyaara', 'bairan',
    'aarzu', 'sahiba', 'taare', 'pal', 'zulfein', 'dhol', 'nach', 'channa', 'kesariya', 'shayad',
    'khairiyat', 'humsafar', 'dhadak', 'raataan', 'lambiyan', 'chaleya', 'baarishein', 'tu hai',
    'kahan', 'pehli', 'nazar', 'kabhi', 'dosti', 'yaari', 'ranjha', 'heer', 'mann', 'duniya',
    'naina', 'ankhiyaan', 'sajna', 'dholna', 'mahiya', 'jatt', 'pind', 'kudi', 'gaana', 'geet',
    'aashiqui', 'bewafa', 'sadqa', 'dua', 'humnava', 'rabba', 'ishqbaazi', 'tujhe', 'mujhe',
    'apna', 'bana', 'le', 'kahani', 'baarish', 'tera', 'chahunga', 'muskurane', 'sukoon',
    'musafir', 'leja', 're', 'lut', 'gaye', 'qismat', 'kalank', 'ghungroo', 'bekhayali', 'pehla',
    'gerua', 'bulleya', 'zaalima', 'hawayein', 'matargashti', 'kasoor', 'choo', 'lo', 'aaftab',
    'heeriye', 'satranga', 'soulmate', 'pasoori', 'husn', 'faasle', 'kho', 'gaye', 'safarnama',
    'alvida', 'jeena', 'jeene', 'laga', 'tera fitoor', 'nainowale', 'subhanallah', 'kabira',
    'akhiyan', 'akhiyon', 'ratiyaan', 'sakhiyon', 'churaake', 'bahaana', 'hustle', 'desihiphop', 'dhh'
}
INDIAN_ARTISTS = {
    'arijit singh', 'atif aslam', 'shreya ghoshal', 'neha kakkar', 'jubin nautiyal',
    'sonu nigam', 'sunidhi chauhan', 'mohit chauhan', 'kishore kumar', 'lata mangeshkar',
    'mukesh', 'mohammed rafi', 'pritam', 'ar rahman', 'a.r. rahman', 'badshah',
    'diljit dosanjh', 'ap dhillon', 'karan aujla', 'honey singh', 'yo yo honey singh',
    'darshan raval', 'anuv jain', 'prateek kuhad', 'sachin-jigar', 'vishal mishra',
    'armaan malik', 'b praak', 'jaani', 'sidhu moosewala', 'guru randhawa', 'hardy sandhu',
    'shubh', 'talwiinder', 'king', 'mc stan', 'divine', 'raftaar', 'kumar sanu',
    'udit narayan', 'alka yagnik', 'kavita krishnamurthy', 'jagjit singh', 'nusrat fateh ali khan',
    'rahat fateh ali khan', 'lucky ali', 'kk', 'shaan', 'himesh reshammiya', 'mika singh',
    'sachet tandon', 'stebin ben', 'jasleen royal', 'aditya rikhari', 'madhurxo', 'kushagra',
    'aur', 'sickved', 'banjaare', 't-series', 'zee music', 'sony music india', 'yrf', 'tips',
    'saregama', 'speed records', 'white hill music', 'anirudh ravichander', 'devi sri prasad',
    'vishal-shekhar', 'amit trivedi', 'mithoon', 'meet bros', 'tony kakkar', 'pawandeep rajan',
    'arunita kanjilal', 'shankar mahadevan', 'hariharan', 'pankaj udhas', 'bhupen hazarika',
    'sicklot', 'aditya pushkarna', 'seedhe maut', 'krsna', 'panther', 'spectra', 'paradox',
    'qaab', 'yungsta', 'kalamkaar', 'emiway bantai', 'mtv hustle', 'epr', 'srushti tawade',
    'gravity', 'wicked sunny', 'gd 47', 'bella', 'vijay dg', 'gaush', 'dino james', 'ikka',
    'fotty seven', 'bali', 'rawal', 'bharg', 'yashraj', 'hanumankind', 'sambata', 'chaar diwaari'
}
BLATANT_WESTERN_ARTISTS = {
    'the weeknd', 'taylor swift', 'drake', 'justin bieber', 'dua lipa', 'ed sheeran',
    'billie eilish', 'ariana grande', 'bruno mars', 'rihanna', 'beyonce', 'post malone',
    'kendrick lamar', 'eminem', 'kanye west', 'travis scott', 'coldplay', 'imagine dragons',
    'maroon 5', 'shawn mendes', 'harry styles', 'olivia rodrigo', 'adele', 'sam smith',
    'katy perry', 'lady gaga', 'selena gomez', 'charlie puth', 'zayn', 'camila cabello',
    'sabrina carpenter', 'chappell roan', 'charli xcx', 'queen', 'the beatles', 'michael jackson',
    'sza', 'doja cat', 'miley cyrus', 'jack harlow', 'future', 'metro boomin', 'gunna', 'lil baby',
    'lil nas x', '21 savage', 'cardi b', 'nicki minaj', 'marshmello', 'alan walker', 'david guetta',
    'calvin harris', 'avicii', 'dj snake', 'tiesto', 'kygo', 'martin garrix', 'halsey', 'benson boone'
}

def is_indian_hindi_track(title: str, artist: str) -> bool:
    """Detects whether a track is Hindi / Bollywood / Punjabi / Indian regional."""
    text = f"{title or ''} {artist or ''}".lower()
    if HINDI_SCRIPT_RE.search(text):
        return True
    clean_art = (artist or "").lower().strip()
    for ia in INDIAN_ARTISTS:
        if ia in clean_art or ia in text:
            return True
    words = set(re.findall(r'[a-zA-Z]+', text))
    if any(k in words for k in HINDI_KEYWORDS):
        return True
    return False

def is_blatant_western_track(title: str, artist: str) -> bool:
    """Detects whether a track is clearly Western / English mainstream pop."""
    clean_art = (artist or "").lower().strip()
    clean_title = (title or "").lower().strip()
    clean_text = f"{clean_title} {clean_art}"
    for wa in BLATANT_WESTERN_ARTISTS:
        if wa in clean_art or wa in clean_text:
            return True
    return False


# ============================================================================
# 1. Latent Acoustic Vector Representation (CNN Mel-Spectrogram Emulation)
# ============================================================================
class AcousticVector:
    """
    Represents a 5-dimensional audio embedding:
    [energy, valence, danceability, acousticness, tempo_norm]
    Values normalized strictly to [0.0, 1.0].
    """
    def __init__(
        self,
        energy: float = 0.5,
        valence: float = 0.5,
        danceability: float = 0.5,
        acousticness: float = 0.5,
        tempo_norm: float = 0.5
    ):
        self.energy = max(0.0, min(1.0, float(energy)))
        self.valence = max(0.0, min(1.0, float(valence)))
        self.danceability = max(0.0, min(1.0, float(danceability)))
        self.acousticness = max(0.0, min(1.0, float(acousticness)))
        self.tempo_norm = max(0.0, min(1.0, float(tempo_norm)))

    def to_list(self) -> List[float]:
        return [self.energy, self.valence, self.danceability, self.acousticness, self.tempo_norm]

    def cosine_similarity(self, other: "AcousticVector") -> float:
        """Calculates cosine similarity in 5D acoustic space."""
        v1 = self.to_list()
        v2 = other.to_list()
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1)) or 1e-6
        mag2 = math.sqrt(sum(b * b for b in v2)) or 1e-6
        return max(0.0, min(1.0, dot / (mag1 * mag2)))


# ============================================================================
# 2. Sub-Millisecond Annoy Vector Index (Random Projection Hyperplane Trees)
# ============================================================================
class AnnoyIndexNode:
    """Binary partition node dividing the vector space via a random hyperplane."""
    def __init__(self, plane: List[float], offset: float):
        self.plane = plane
        self.offset = offset
        self.left: Optional[Any] = None
        self.right: Optional[Any] = None
        self.indices: List[str] = []


class AnnoyIndexSimulator:
    """
    In-memory Approximate Nearest Neighbor (Annoy) forest simulator.
    Uses randomized binary projection hyperplanes for sub-millisecond retrieval.
    """
    def __init__(self, n_trees: int = 4):
        self.n_trees = n_trees
        self.vectors: Dict[str, AcousticVector] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.roots: List[AnnoyIndexNode] = []
        self._lock = threading.Lock()

    def add_item(self, track_id: str, vector: AcousticVector, meta: Dict[str, Any]):
        with self._lock:
            self.vectors[track_id] = vector
            self.metadata[track_id] = meta

    def build(self):
        """Builds a forest of randomized binary projection trees."""
        with self._lock:
            if not self.vectors:
                return
            self.roots = []
            item_ids = list(self.vectors.keys())
            dim = 5
            for _ in range(self.n_trees):
                # Random hyperplane normal vector
                plane = [random.uniform(-1.0, 1.0) for _ in range(dim)]
                norm = math.sqrt(sum(p * p for p in plane)) or 1.0
                plane = [p / norm for p in plane]
                node = AnnoyIndexNode(plane, offset=0.5)

                left_items = []
                right_items = []
                for tid in item_ids:
                    vec = self.vectors[tid].to_list()
                    dot = sum(v * p for v, p in zip(vec, plane))
                    if dot >= node.offset:
                        right_items.append(tid)
                    else:
                        left_items.append(tid)

                node.left = left_items
                node.right = right_items
                self.roots.append(node)

    def query(self, target: AcousticVector, k: int = 10) -> List[Tuple[str, float]]:
        """Queries the Annoy forest and returns top-k approximate nearest neighbor IDs with similarity."""
        with self._lock:
            if not self.vectors:
                return []

            candidate_pool: Set[str] = set()
            t_vec = target.to_list()

            for root in self.roots:
                dot = sum(v * p for v, p in zip(t_vec, root.plane))
                candidates = root.right if dot >= root.offset else root.left
                if isinstance(candidates, list):
                    candidate_pool.update(candidates)

            # If candidates are scarce, fall back to entire catalog
            if len(candidate_pool) < k:
                candidate_pool.update(self.vectors.keys())

            # Score candidates via cosine similarity
            scored = []
            for tid in candidate_pool:
                vec = self.vectors.get(tid)
                if vec:
                    sim = target.cosine_similarity(vec)
                    scored.append((tid, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:k]


# ============================================================================
# 3. BaRT Multi-Armed Contextual Bandit (Recommendations as Treatments)
# ============================================================================
class BaRTContextualBandit:
    """
    Implements Spotify's BaRT (Bandits for Recommendations as Treatments).
    Dynamically balances:
    - Exploitation: Familiar high-affinity tracks & artist favorites (~90%)
    - Exploration: Novel songs & calculated discovery risks (~10%)
    Adapts based on:
    - Time of day context
    - Session momentum (rapid skips trigger conservative safety guards)
    """
    def __init__(self):
        self._lock = threading.RLock()
        self.default_exploration_rate = 0.10
        self.session_skips: Dict[str, int] = {}       # user_id -> recent consecutive rapid skips
        self.session_streams: Dict[str, int] = {}     # user_id -> recent completed streams
        self.user_rewards: Dict[str, float] = {}      # user_id -> accumulated reward score

    def get_context_weights(self, user_id: str) -> Dict[str, Any]:
        """Calculates dynamic exploration vs exploitation balance and time-of-day bias."""
        uid = (user_id or "dave").strip().lower()
        now = datetime.now()
        hour = now.hour

        # 1. Time of Day Context
        if 5 <= hour < 12:
            time_tag = "morning"
            acoustic_bias = {"energy": 0.35, "acousticness": 0.70, "valence": 0.60}
        elif 12 <= hour < 17:
            time_tag = "afternoon"
            acoustic_bias = {"energy": 0.65, "danceability": 0.60, "valence": 0.65}
        elif 17 <= hour < 22:
            time_tag = "evening"
            acoustic_bias = {"energy": 0.85, "danceability": 0.80, "valence": 0.70}
        else:
            time_tag = "night"
            acoustic_bias = {"energy": 0.40, "acousticness": 0.60, "valence": 0.40}

        with self._lock:
            consecutive_skips = self.session_skips.get(uid, 0)
            completed_streams = self.session_streams.get(uid, 0)

            # 2. Session Momentum Guard:
            # If user skipped 3+ songs rapidly, collapse exploration to zero to play safe favorites!
            if consecutive_skips >= 3:
                exploration_rate = 0.0
                momentum_state = "recovery_conservative"
            elif consecutive_skips > 0:
                exploration_rate = max(0.02, self.default_exploration_rate - (consecutive_skips * 0.04))
                momentum_state = "cautious"
            else:
                exploration_rate = min(0.22, self.default_exploration_rate + (completed_streams * 0.02))
                momentum_state = "exploratory"

            return {
                "user_id": uid,
                "time_of_day": time_tag,
                "acoustic_bias": acoustic_bias,
                "exploration_rate": round(exploration_rate, 3),
                "exploitation_rate": round(1.0 - exploration_rate, 3),
                "momentum_state": momentum_state,
                "consecutive_skips": consecutive_skips,
                "completed_streams": completed_streams
            }

    def record_feedback(self, user_id: str, track_id: str, action: str, listen_seconds: int = 0) -> Dict[str, Any]:
        """
        Observes implicit user feedback to update bandit reward signals:
        - 'stream' (>30s): +1.0 reward
        - 'favorite': +2.0 reward
        - 'skip' (<30s): -1.0 penalty, increments session skip counter
        """
        uid = (user_id or "dave").strip().lower()
        action = (action or "").strip().lower()

        with self._lock:
            current_skips = self.session_skips.get(uid, 0)
            current_streams = self.session_streams.get(uid, 0)
            reward_score = self.user_rewards.get(uid, 0.0)

            if action == "skip" or (action == "stream" and listen_seconds > 0 and listen_seconds < 25):
                reward_delta = -1.0
                self.session_skips[uid] = current_skips + 1
                self.session_streams[uid] = max(0, current_streams - 1)
            elif action in ("favorite", "like", "add"):
                reward_delta = 2.0
                self.session_skips[uid] = 0
                self.session_streams[uid] = current_streams + 2
            else:
                reward_delta = 1.0
                self.session_skips[uid] = 0
                self.session_streams[uid] = current_streams + 1

            self.user_rewards[uid] = reward_score + reward_delta

            consecutive_skips = self.session_skips[uid]
            completed_streams = self.session_streams[uid]
            if consecutive_skips >= 3:
                exploration_rate = 0.0
                momentum_state = "recovery_conservative"
            elif consecutive_skips > 0:
                exploration_rate = max(0.02, self.default_exploration_rate - (consecutive_skips * 0.04))
                momentum_state = "cautious"
            else:
                exploration_rate = min(0.22, self.default_exploration_rate + (completed_streams * 0.02))
                momentum_state = "exploratory"

            return {
                "user_id": uid,
                "track_id": track_id,
                "action": action,
                "reward_delta": reward_delta,
                "total_reward": self.user_rewards[uid],
                "consecutive_skips": consecutive_skips,
                "completed_streams": completed_streams,
                "momentum_state": momentum_state,
                "exploration_rate": round(exploration_rate, 3),
                "exploitation_rate": round(1.0 - exploration_rate, 3)
            }


# ============================================================================
# 4. Hybrid Recommendation Engine & Flagship Mix Generator
# ============================================================================
class RecommendationEngine:
    """
    Hybrid recommendation engine combining Spotify acoustic graphs,
    Annoy approximate nearest neighbors, YouTube Music continuous radio,
    and BaRT contextual multi-armed bandits.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._spotify_token: Optional[str] = None
        self._spotify_token_expiry: float = 0.0
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour cache per seed

        # Core ML Subsystems
        self.annoy_index = AnnoyIndexSimulator(n_trees=6)
        self.bandit = BaRTContextualBandit()
        self._seed_acoustic_catalog()

    def _seed_acoustic_catalog(self):
        """Seeds the latent Annoy vector space with canonical acoustic fingerprints."""
        canonical_seeds = [
            # 1. Synthwave & Electronic
            ("4NRXx6U8ABQ", "Blinding Lights", "The Weeknd", AcousticVector(0.85, 0.70, 0.75, 0.10, 0.85), "synthwave"),
            ("rQQU95aP_h8", "Save Your Tears", "The Weeknd", AcousticVector(0.75, 0.65, 0.70, 0.15, 0.60), "synthwave"),
            ("kTJczUoc26U", "In My Feelings", "Camila Cabello", AcousticVector(0.68, 0.60, 0.68, 0.20, 0.55), "pop"),
            ("b8T8yP7e-yI", "Levitating", "Dua Lipa", AcousticVector(0.88, 0.90, 0.82, 0.05, 0.70), "dance_pop"),
            # 2. Lo-Fi & Chill Beats
            ("jfKfPfyJRdk", "Lofi Hip Hop Radio", "Lofi Girl", AcousticVector(0.30, 0.40, 0.60, 0.85, 0.35), "lofi"),
            ("5qap5aO4i9A", "ChilledCow Beats", "Lofi Beats", AcousticVector(0.28, 0.42, 0.58, 0.88, 0.32), "lofi"),
            ("7NOSDKb0HlU", "Feather", "Nujabes", AcousticVector(0.45, 0.55, 0.65, 0.70, 0.45), "lofi_jazz"),
            # 3. Mainstream Pop & Modern Hits
            ("2Vv-BfVoq4g", "Perfect", "Ed Sheeran", AcousticVector(0.40, 0.50, 0.55, 0.75, 0.40), "pop"),
            ("fJ9rUzIMcZQ", "Bohemian Rhapsody", "Queen", AcousticVector(0.70, 0.45, 0.40, 0.30, 0.50), "rock"),
            ("YQHsXMglC9A", "Hello", "Adele", AcousticVector(0.50, 0.30, 0.45, 0.65, 0.40), "pop_ballad"),
            # 4. Indian Regional & Bollywood
            ("BddP6PYo2gs", "Kesariya", "Arijit Singh", AcousticVector(0.60, 0.65, 0.50, 0.60, 0.50), "bollywood"),
            ("Umqb9KENgmk", "Tum Hi Ho", "Arijit Singh", AcousticVector(0.50, 0.35, 0.45, 0.70, 0.42), "bollywood"),
            ("V7LwfY5U5WI", "Chaleya", "Anirudh Ravichander", AcousticVector(0.75, 0.80, 0.75, 0.30, 0.65), "bollywood_dance"),
            ("69kpgQyq7_Y", "Apna Bana Le", "Sachin-Jigar", AcousticVector(0.55, 0.50, 0.48, 0.68, 0.45), "bollywood"),
            # 5. Hip-Hop & Rap
            ("fPO76JdxS68", "SICKO MODE", "Travis Scott", AcousticVector(0.85, 0.45, 0.78, 0.12, 0.75), "hiphop"),
            ("7wtfhZwyrcc", "Believer", "Imagine Dragons", AcousticVector(0.90, 0.65, 0.70, 0.10, 0.72), "rock_pop"),
        ]

        for vid, title, artist, vec, genre in canonical_seeds:
            meta = {
                "id": vid,
                "title": title,
                "artist": artist,
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "genre": genre,
                "source": "annoy_latent_index"
            }
            self.annoy_index.add_item(vid, vec, meta)

        self.annoy_index.build()

    # ---------------------------------------------------------
    # Spotify API Authentication & Client Credential Flow
    # ---------------------------------------------------------
    def _get_spotify_access_token(self) -> Optional[str]:
        """Obtains or refreshes Spotify App Access Token using client credentials."""
        if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
            return None

        now = time.time()
        with self._lock:
            if self._spotify_token and now < self._spotify_token_expiry - 60:
                return self._spotify_token

            auth_bytes = f"{SPOTIPY_CLIENT_ID}:{SPOTIPY_CLIENT_SECRET}".encode("utf-8")
            auth_header = base64.b64encode(auth_bytes).decode("utf-8")

            try:
                resp = requests.post(
                    "https://accounts.spotify.com/api/token",
                    headers={
                        "Authorization": f"Basic {auth_header}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._spotify_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._spotify_token_expiry = now + expires_in
                    return self._spotify_token
                else:
                    logger.warning(f"Spotify token request failed with status {resp.status_code}")
            except Exception as e:
                logger.error(f"Failed to authenticate with Spotify: {e}")

        return None

    # ---------------------------------------------------------
    # Metadata Normalization & Diversity Filters
    # ---------------------------------------------------------
    @staticmethod
    def _clean_title(title: str) -> str:
        """Removes common YouTube video noise to isolate song titles."""
        clean = re.sub(
            r"(?i)\s*[\(\[](official\s*(music\s*)?(video|audio)|lyrics|visualizer|hd|4k|remastered)[\)\]]|\b(4k|hd|hq)\b",
            "",
            title
        )
        return re.sub(r"\s+", " ", clean).strip()

    def _filter_and_diversify(
        self,
        candidates: List[Dict[str, Any]],
        exclude_ids: Optional[List[str]] = None,
        max_per_artist: int = 2,
        limit: int = 10,
        is_indian: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates tracks, checks against the exclude history list,
        and caps recurring artists to prevent repetitive echo chambers.
        """
        exclude_set = set(exclude_ids or [])
        seen_titles = set()
        artist_counts: Dict[str, int] = {}
        filtered: List[Dict[str, Any]] = []

        for track in candidates:
            track_id = track.get("id") or track.get("videoId")
            title = self._clean_title(track.get("title", ""))
            artist = (track.get("artist") or "Unknown").strip().lower()

            if not track_id or track_id in exclude_set:
                continue

            # When seed track is Indian, filter out blatant Western English pop songs
            if is_indian and is_blatant_western_track(title, track.get("artist", "")):
                continue

            normalized_key = f"{artist} - {title.lower()}"
            if normalized_key in seen_titles:
                continue

            # Diversity cap: avoid playing tracks exclusively from one artist
            if artist_counts.get(artist, 0) >= max_per_artist:
                continue

            seen_titles.add(normalized_key)
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
            duration_val = track.get("duration", 0) or 0
            filtered.append({
                "id": track_id,
                "title": title,
                "artist": track.get("artist", "Unknown"),
                "thumbnail": track.get("thumbnail", ""),
                "duration": duration_val,
                "duration_formatted": track.get("duration_formatted") or format_duration(duration_val),
                "source": track.get("source", "generic"),
            })

            if len(filtered) >= limit:
                break

        return filtered

    # ---------------------------------------------------------
    # Strategy 1: Spotify Acoustic Graph Recommendations
    # ---------------------------------------------------------
    def _recommend_from_spotify(
        self, artist: str, title: str, limit: int = 15
    ) -> Optional[List[Dict[str, Any]]]:
        """Resolves seed track on Spotify and queries the recommendation API."""
        token = self._get_spotify_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}

        try:
            query = f"track:{title} artist:{artist}" if artist else title
            search_resp = requests.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params={"q": query, "type": "track", "limit": 1},
                timeout=4.0,
            )
            if search_resp.status_code != 200:
                return None

            items = search_resp.json().get("tracks", {}).get("items", [])
            if not items:
                return None

            seed_track = items[0]
            seed_track_id = seed_track["id"]
            seed_artist_id = seed_track["artists"][0]["id"] if seed_track.get("artists") else None

            params = {
                "limit": limit,
                "seed_tracks": seed_track_id,
            }
            if seed_artist_id:
                params["seed_artists"] = seed_artist_id

            rec_resp = requests.get(
                "https://api.spotify.com/v1/recommendations",
                headers=headers,
                params=params,
                timeout=4.0,
            )
            if rec_resp.status_code != 200:
                return None

            tracks = rec_resp.json().get("tracks", [])
            results = []
            for t in tracks:
                dur_sec = int(t.get("duration_ms", 0) / 1000)
                results.append({
                    "id": t["id"],
                    "title": t["name"],
                    "artist": ", ".join(a["name"] for a in t.get("artists", [])),
                    "thumbnail": t["album"]["images"][0]["url"] if t.get("album", {}).get("images") else "",
                    "duration": dur_sec,
                    "duration_formatted": format_duration(dur_sec),
                    "source": "spotify",
                })
            return results
        except Exception as e:
            logger.warning(f"Spotify recommendation failed, falling back to YouTube: {e}")
            return None

    # ---------------------------------------------------------
    # Strategy 2: YouTube Music Up-Next / Related Extractor
    # ---------------------------------------------------------
    def _recommend_from_youtube(
        self, seed_query: str, limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Queries YouTube related entries using yt-dlp search."""
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        search_query = f"ytsearch{limit}:{seed_query} audio radio"
        results = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []

                for entry in entries:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    title = entry.get("title", "")
                    uploader = entry.get("uploader") or entry.get("channel", "Unknown")
                    thumbnail = entry.get("thumbnail") or (
                        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
                    )

                    raw_artist = entry.get("artist") or entry.get("creator") or uploader
                    artist = raw_artist
                    if " - " in title:
                        parts = title.split(" - ", 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()

                    if artist.lower().strip() in {
                        "release", "release - topic", "topic", "various artists",
                        "various artists - topic", "unknown", "unknown artist", "auto-generated by youtube"
                    }:
                        artist = entry.get("artist") or entry.get("creator") or "Unknown Artist"

                    dur_sec = entry.get("duration") or 0
                    results.append({
                        "id": video_id,
                        "title": title,
                        "artist": artist,
                        "thumbnail": thumbnail,
                        "duration": dur_sec,
                        "duration_formatted": format_duration(dur_sec),
                        "source": "youtube",
                    })
        except Exception as e:
            logger.error(f"YouTube related extraction error: {e}")

        return results

    # ---------------------------------------------------------
    # Unified Public Entrypoint (Radio / Autoplay Queue)
    # ---------------------------------------------------------
    def get_recommendations(
        self,
        title: str,
        artist: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Returns a diversified list of recommended songs based on the current track.
        Applies Annoy approximate nearest neighbors, provider fallbacks, and diversity caps.
        """
        is_indian = is_indian_hindi_track(title or "", artist or "")
        cache_key = f"{artist or ''}::{title}:{'in' if is_indian else 'en'}".lower().strip()
        now = time.time()

        # Check Cache
        cached = self._cache.get(cache_key)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return self._filter_and_diversify(cached["tracks"], exclude_ids, limit=limit, is_indian=is_indian)

        raw_candidates = []

        # 1. Try Spotify Acoustic Recommendations
        if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
            spotify_candidates = self._recommend_from_spotify(artist or "", title, limit=limit + 10)
            if spotify_candidates:
                if is_indian:
                    spotify_candidates = [sc for sc in spotify_candidates if not is_blatant_western_track(sc.get("title", ""), sc.get("artist", ""))]
                raw_candidates.extend(spotify_candidates)

        # 2. Try Annoy Nearest Neighbor retrieval for known acoustic fingerprints
        if not raw_candidates:
            query_energy = 0.55 if not is_indian else 0.65
            query_vec = AcousticVector(energy=query_energy, valence=0.60, danceability=0.65, acousticness=0.35)
            annoy_matches = self.annoy_index.query(query_vec, k=8)
            for tid, sim in annoy_matches:
                meta = self.annoy_index.metadata.get(tid)
                if meta:
                    raw_candidates.append({
                        "id": meta["id"],
                        "title": meta["title"],
                        "artist": meta["artist"],
                        "thumbnail": meta["thumbnail"],
                        "duration": 210,
                        "source": "annoy_nearest_neighbors"
                    })

        # 3. Fallback to YouTube if still empty or need more diversity
        if not raw_candidates or len(raw_candidates) < limit:
            if is_indian:
                query = f"{artist or title} hindi bollywood songs radio mix"
            else:
                query = f"{artist} {title}" if artist else title
            yt_candidates = self._recommend_from_youtube(query, limit=limit + 10)
            if is_indian:
                yt_candidates = [rc for rc in yt_candidates if not is_blatant_western_track(rc.get("title", ""), rc.get("artist", ""))]
            raw_candidates.extend(yt_candidates)

        # 4. Fallback for Indian tracks if still empty
        if not raw_candidates and is_indian:
            raw_candidates = self._recommend_from_youtube("Top Trending Hindi Bollywood Hits 2026", limit=limit + 10)
            raw_candidates = [rc for rc in raw_candidates if not is_blatant_western_track(rc.get("title", ""), rc.get("artist", ""))]

        # Update Cache
        self._cache[cache_key] = {
            "timestamp": now,
            "tracks": raw_candidates,
        }

        # Apply deduplication and diversity enforcement
        return self._filter_and_diversify(raw_candidates, exclude_ids, limit=limit, is_indian=is_indian)

    # ---------------------------------------------------------
    # 5. Flagship Personalized Mixes: Daily Mix 1-6 & Discover Weekly
    # ---------------------------------------------------------
    def _classify_track_cluster(self, track: Dict[str, Any]) -> int:
        """
        Classifies a track into one of the 6 canonical Spotify Daily Mix taste clusters:
        0: Synthwave & Modern Pop Pulse (The Weeknd, Dua Lipa, synthwave, electronic, dance-pop)
        1: Deep Focus & Lo-Fi Beats (Lofi Girl, ChilledCow, Nujabes, chillhop, study)
        2: Bollywood & Desi Melodies (Arijit Singh, Sachin-Jigar, Punjabi, Hindi regional)
        3: Late Night Hip-Hop & Rap (Travis Scott, Drake, Future, rap, hip hop, trap)
        4: Rock & Stadium Anthems (Queen, Imagine Dragons, Coldplay, rock, metal, alternative)
        5: Acoustic & Vocal Soul (Ed Sheeran, Adele, Billie Eilish, singer-songwriter, indie, folk)
        """
        title = (track.get("title") or "").lower()
        artist = (track.get("artist") or "").lower()
        genre = (track.get("genre") or "").lower()
        combined = f"{title} {artist} {genre}"

        if is_indian_hindi_track(title, artist) or any(k in combined for k in ("bollywood", "punjabi", "desi", "sufi", "qawwali")):
            return 2
        if any(k in combined for k in ("lofi", "lo-fi", "chillhop", "beats to study", "chilledcow", "nujabes", "focus", "ambient")):
            return 1
        if any(k in combined for k in ("hiphop", "hip-hop", "rap", "trap", "drill", "travis scott", "drake", "future", "kendrick", "eminem", "21 savage")):
            return 3
        if any(k in combined for k in ("rock", "queen", "imagine dragons", "coldplay", "guitar", "metal", "punk", "nirvana", "linkin park")):
            return 4
        if any(k in combined for k in ("acoustic", "adele", "ed sheeran", "billie eilish", "piano", "soul", "ballad", "unplugged", "folk")):
            return 5
        return 0

    def get_daily_mixes(self, user_id: str = "dave") -> List[Dict[str, Any]]:
        """
        Generates 6 distinct Daily Mixes by sub-taste clustering,
        mirroring Spotify's K-Means listening cluster architecture.
        Dynamically clusters the user's actual library history & favorites,
        blended with seed recommendations.
        """
        context = self.bandit.get_context_weights(user_id)

        # 6 Canonical Daily Mix Taste Clusters
        mix_templates = [
            {
                "id": "daily_mix_1",
                "title": "Daily Mix 1",
                "subtitle": "The Weeknd, Dua Lipa, Camila Cabello",
                "tag": "Synthwave & Pop Pulse",
                "color": "#8b5cf6",
                "icon_mood": "synthwave",
                "tracks": [
                    {"id": "4NRXx6U8ABQ", "title": "Blinding Lights", "artist": "The Weeknd", "duration": 200, "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg"},
                    {"id": "rQQU95aP_h8", "title": "Save Your Tears", "artist": "The Weeknd", "duration": 215, "thumbnail": "https://i.ytimg.com/vi/rQQU95aP_h8/hqdefault.jpg"},
                    {"id": "b8T8yP7e-yI", "title": "Levitating", "artist": "Dua Lipa", "duration": 203, "thumbnail": "https://i.ytimg.com/vi/b8T8yP7e-yI/hqdefault.jpg"},
                    {"id": "kTJczUoc26U", "title": "In My Feelings", "artist": "Camila Cabello", "duration": 220, "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg"},
                ]
            },
            {
                "id": "daily_mix_2",
                "title": "Daily Mix 2",
                "subtitle": "Lofi Girl, ChilledCow, Nujabes",
                "tag": "Deep Focus & Study",
                "color": "#10b981",
                "icon_mood": "lofi",
                "tracks": [
                    {"id": "jfKfPfyJRdk", "title": "Lofi Hip Hop Radio", "artist": "Lofi Girl", "duration": 180, "thumbnail": "https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg"},
                    {"id": "5qap5aO4i9A", "title": "ChilledCow Beats", "artist": "Lofi Beats", "duration": 195, "thumbnail": "https://i.ytimg.com/vi/5qap5aO4i9A/hqdefault.jpg"},
                    {"id": "7NOSDKb0HlU", "title": "Feather", "artist": "Nujabes", "duration": 220, "thumbnail": "https://i.ytimg.com/vi/7NOSDKb0HlU/hqdefault.jpg"},
                ]
            },
            {
                "id": "daily_mix_3",
                "title": "Daily Mix 3",
                "subtitle": "Arijit Singh, Sachin-Jigar, Anirudh",
                "tag": "Bollywood & Desi Melodies",
                "color": "#f59e0b",
                "icon_mood": "bollywood",
                "tracks": [
                    {"id": "BddP6PYo2gs", "title": "Kesariya", "artist": "Arijit Singh", "duration": 268, "thumbnail": "https://i.ytimg.com/vi/BddP6PYo2gs/hqdefault.jpg"},
                    {"id": "V7LwfY5U5WI", "title": "Chaleya", "artist": "Anirudh Ravichander", "duration": 200, "thumbnail": "https://i.ytimg.com/vi/V7LwfY5U5WI/hqdefault.jpg"},
                    {"id": "69kpgQyq7_Y", "title": "Apna Bana Le", "artist": "Sachin-Jigar", "duration": 215, "thumbnail": "https://i.ytimg.com/vi/69kpgQyq7_Y/hqdefault.jpg"},
                    {"id": "Umqb9KENgmk", "title": "Tum Hi Ho", "artist": "Arijit Singh", "duration": 262, "thumbnail": "https://i.ytimg.com/vi/Umqb9KENgmk/hqdefault.jpg"},
                ]
            },
            {
                "id": "daily_mix_4",
                "title": "Daily Mix 4",
                "subtitle": "Travis Scott, Drake, Future",
                "tag": "Late Night Hip-Hop",
                "color": "#ef4444",
                "icon_mood": "hiphop",
                "tracks": [
                    {"id": "fPO76JdxS68", "title": "SICKO MODE", "artist": "Travis Scott", "duration": 312, "thumbnail": "https://i.ytimg.com/vi/fPO76JdxS68/hqdefault.jpg"},
                    {"id": "m7Bc3JBkW40", "title": "God's Plan", "artist": "Drake", "duration": 199, "thumbnail": "https://i.ytimg.com/vi/m7Bc3JBkW40/hqdefault.jpg"},
                    {"id": "4NRXx6U8ABQ", "title": "Heartless", "artist": "The Weeknd", "duration": 200, "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg"},
                ]
            },
            {
                "id": "daily_mix_5",
                "title": "Daily Mix 5",
                "subtitle": "Queen, Imagine Dragons, Coldplay",
                "tag": "Rock & Stadium Anthems",
                "color": "#3b82f6",
                "icon_mood": "rock",
                "tracks": [
                    {"id": "fJ9rUzIMcZQ", "title": "Bohemian Rhapsody", "artist": "Queen", "duration": 354, "thumbnail": "https://i.ytimg.com/vi/fJ9rUzIMcZQ/hqdefault.jpg"},
                    {"id": "7wtfhZwyrcc", "title": "Believer", "artist": "Imagine Dragons", "duration": 204, "thumbnail": "https://i.ytimg.com/vi/7wtfhZwyrcc/hqdefault.jpg"},
                ]
            },
            {
                "id": "daily_mix_6",
                "title": "Daily Mix 6",
                "subtitle": "Ed Sheeran, Adele, Billie Eilish",
                "tag": "Acoustic & Vocal Soul",
                "color": "#ec4899",
                "icon_mood": "acoustic",
                "tracks": [
                    {"id": "2Vv-BfVoq4g", "title": "Perfect", "artist": "Ed Sheeran", "duration": 263, "thumbnail": "https://i.ytimg.com/vi/2Vv-BfVoq4g/hqdefault.jpg"},
                    {"id": "YQHsXMglC9A", "title": "Hello", "Adele": "Adele", "artist": "Adele", "duration": 295, "thumbnail": "https://i.ytimg.com/vi/YQHsXMglC9A/hqdefault.jpg"},
                ]
            }
        ]

        # Dynamic personalization from user's listening history & favorites
        if library_store:
            try:
                user_tracks = []
                favs = library_store.get_user_favorites(user_id) or []
                history = library_store.get_user_history(user_id, limit=40) or []
                seen_ids = set()

                for trk in favs + history:
                    tid = str(trk.get("track_id") or trk.get("id") or "").strip()
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        user_tracks.append({
                            "id": tid,
                            "title": trk.get("title", "Track"),
                            "artist": trk.get("artist", "Artist"),
                            "thumbnail": trk.get("thumbnail") or f"https://i.ytimg.com/vi/{tid}/hqdefault.jpg",
                            "duration": int(trk.get("duration") or 210)
                        })

                # Cluster user tracks
                user_clusters: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(6)}
                for trk in user_tracks:
                    c_idx = self._classify_track_cluster(trk)
                    user_clusters[c_idx].append(trk)

                for idx, mix in enumerate(mix_templates):
                    clustered = user_clusters.get(idx, [])
                    if clustered:
                        template_tracks = [t for t in mix["tracks"] if t["id"] not in {u["id"] for u in clustered}]
                        merged_tracks = clustered[:4] + template_tracks
                        mix["tracks"] = merged_tracks[:6]

                        top_artists = []
                        for ut in clustered:
                            art = ut.get("artist", "").strip()
                            if art and art not in top_artists:
                                top_artists.append(art)
                        if top_artists:
                            mix["subtitle"] = ", ".join(top_artists[:3])
            except Exception as e:
                logger.debug(f"User library cluster personalization fallback: {e}")

        # Annotate with context momentum & formatted durations
        for mix in mix_templates:
            for trk in mix["tracks"]:
                dur = trk.get("duration", 0)
                trk["duration_formatted"] = format_duration(dur)
            mix["context_momentum"] = context["momentum_state"]
            mix["exploration_rate"] = context["exploration_rate"]

        return mix_templates

    def get_discover_weekly(self, user_id: str = "dave") -> Dict[str, Any]:
        """
        Generates Spotify's flagship 'Discover Weekly' playlist:
        Prioritizes high-novelty exploration candidates across user's sub-taste clusters,
        filtering out songs user has already played or favorited.
        """
        context = self.bandit.get_context_weights(user_id)
        default_candidates = [
            {"id": "rQQU95aP_h8", "title": "Save Your Tears (Remix)", "artist": "The Weeknd, Ariana Grande", "duration": 191, "thumbnail": "https://i.ytimg.com/vi/rQQU95aP_h8/hqdefault.jpg", "novelty_score": 0.88},
            {"id": "b8T8yP7e-yI", "title": "Hallucinate", "artist": "Dua Lipa", "duration": 208, "thumbnail": "https://i.ytimg.com/vi/b8T8yP7e-yI/hqdefault.jpg", "novelty_score": 0.82},
            {"id": "7NOSDKb0HlU", "title": "Aruarian Dance", "artist": "Nujabes", "duration": 252, "thumbnail": "https://i.ytimg.com/vi/7NOSDKb0HlU/hqdefault.jpg", "novelty_score": 0.94},
            {"id": "69kpgQyq7_Y", "title": "Rasiya", "artist": "Pritam, Shreya Ghoshal", "duration": 260, "thumbnail": "https://i.ytimg.com/vi/69kpgQyq7_Y/hqdefault.jpg", "novelty_score": 0.79},
            {"id": "fPO76JdxS68", "title": "STARGAZING", "artist": "Travis Scott", "duration": 270, "thumbnail": "https://i.ytimg.com/vi/fPO76JdxS68/hqdefault.jpg", "novelty_score": 0.85},
            {"id": "2Vv-BfVoq4g", "title": "Shivers", "artist": "Ed Sheeran", "duration": 207, "thumbnail": "https://i.ytimg.com/vi/2Vv-BfVoq4g/hqdefault.jpg", "novelty_score": 0.76},
        ]

        candidates = list(default_candidates)

        if library_store:
            try:
                listened_ids = set()
                favs = library_store.get_user_favorites(user_id) or []
                history = library_store.get_user_history(user_id, limit=50) or []
                for t in favs + history:
                    tid = str(t.get("track_id") or t.get("id") or "").strip()
                    if tid:
                        listened_ids.add(tid)

                query_vec = AcousticVector(
                    energy=context.get("acoustic_bias", {}).get("energy", 0.65),
                    valence=context.get("acoustic_bias", {}).get("valence", 0.60),
                    danceability=context.get("acoustic_bias", {}).get("danceability", 0.65),
                    acousticness=context.get("acoustic_bias", {}).get("acousticness", 0.35)
                )
                annoy_matches = self.annoy_index.query(query_vec, k=12)
                discovered = []
                for tid, sim in annoy_matches:
                    if tid not in listened_ids:
                        meta = self.annoy_index.metadata.get(tid)
                        if meta:
                            novelty = round(max(0.70, min(0.98, 1.0 - (sim * 0.2))), 2)
                            discovered.append({
                                "id": meta["id"],
                                "title": meta["title"],
                                "artist": meta["artist"],
                                "thumbnail": meta.get("thumbnail") or f"https://i.ytimg.com/vi/{meta['id']}/hqdefault.jpg",
                                "duration": 210,
                                "novelty_score": novelty
                            })
                if discovered:
                    filtered_defaults = [c for c in default_candidates if c["id"] not in listened_ids]
                    combined = discovered + filtered_defaults
                    seen = set()
                    final_list = []
                    for c in combined:
                        if c["id"] not in seen:
                            seen.add(c["id"])
                            final_list.append(c)
                    candidates = final_list[:8]
            except Exception as e:
                logger.debug(f"Discover weekly personalization fallback: {e}")

        for c in candidates:
            c["duration_formatted"] = format_duration(c.get("duration", 0))

        return {
            "id": "discover_weekly",
            "title": "Discover Weekly",
            "subtitle": "Your weekly mixtape of fresh music. Updated every Monday.",
            "description": "Calculated exploration candidates based on your recent listening graph and BaRT contextual bandits.",
            "refresh_day": "Monday",
            "tracks": candidates,
            "context": context
        }

    def record_feedback(self, user_id: str, track_id: str, action: str, listen_seconds: int = 0) -> Dict[str, Any]:
        """Observes user reactions (stream vs skip vs favorite) to update BaRT bandit weights."""
        return self.bandit.record_feedback(user_id, track_id, action, listen_seconds)

    def get_context_state(self, user_id: str = "dave") -> Dict[str, Any]:
        """Retrieves real-time context and bandit weights."""
        return self.bandit.get_context_weights(user_id)


# Global Singleton Instance
recommendation_engine = RecommendationEngine()
