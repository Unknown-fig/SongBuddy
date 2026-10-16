"""
Unit tests for SongBuddy Recommendation Engine (recommender.py) and its API / MCP interfaces.
"""
import pytest
from recommender import RecommendationEngine, recommendation_engine, is_indian_hindi_track
from mcp_server import get_similar_tracks

def test_clean_title():
    engine = RecommendationEngine()
    raw = "Drake - God's Plan (Official Music Video) [Lyrics] 4K"
    cleaned = engine._clean_title(raw)
    assert "(Official Music Video)" not in cleaned
    assert "[Lyrics]" not in cleaned
    assert "4K" not in cleaned
    assert "God's Plan" in cleaned

def test_filter_and_diversify_artist_cap():
    engine = RecommendationEngine()
    tracks = [
        {"id": "t1", "title": "Song 1", "artist": "Drake"},
        {"id": "t2", "title": "Song 2", "artist": "Drake"},
        {"id": "t3", "title": "Song 3", "artist": "Drake"},  # Should be capped out
        {"id": "t4", "title": "Song 4", "artist": "Travis Scott"},
        {"id": "t5", "title": "Song 5", "artist": "Future"},
    ]
    filtered = engine._filter_and_diversify(tracks, limit=5, max_per_artist=2)
    drake_count = sum(1 for t in filtered if t["artist"] == "Drake")
    assert drake_count == 2
    assert len(filtered) == 4
    assert any(t["artist"] == "Travis Scott" for t in filtered)
    assert any(t["artist"] == "Future" for t in filtered)

def test_filter_and_diversify_exclude_ids():
    engine = RecommendationEngine()
    tracks = [
        {"id": "t1", "title": "Song 1", "artist": "Artist A"},
        {"id": "t2", "title": "Song 2", "artist": "Artist B"},
        {"id": "t3", "title": "Song 3", "artist": "Artist C"},
    ]
    filtered = engine._filter_and_diversify(tracks, exclude_ids=["t1", "t2"], limit=5)
    assert len(filtered) == 1
    assert filtered[0]["id"] == "t3"

def test_recommendations_caching(monkeypatch):
    engine = RecommendationEngine()
    call_count = {"count": 0}

    def fake_youtube_rec(seed_query, limit=15):
        call_count["count"] += 1
        return [{"id": "yt1", "title": "Recommended YT", "artist": "Artist X", "source": "youtube_radio"}]

    monkeypatch.setattr(engine, "_recommend_from_spotify", lambda *a, **kw: [])
    monkeypatch.setattr(engine.annoy_index, "query", lambda *a, **kw: [])
    monkeypatch.setattr(engine, "_recommend_from_youtube", fake_youtube_rec)

    # First call: triggers retrieval
    res1 = engine.get_recommendations(title="Starboy", artist="The Weeknd", limit=5)
    assert len(res1) == 1
    assert call_count["count"] == 1

    # Second call: served from memory cache
    res2 = engine.get_recommendations(title="Starboy", artist="The Weeknd", limit=5)
    assert len(res2) == 1
    assert call_count["count"] == 1

def test_mcp_tool_get_similar_tracks(monkeypatch):
    # Mock recommendation engine response
    def fake_get_recs(title, artist, limit=5):
        return [
            {"id": "m1", "title": "Blinding Lights", "artist": "The Weeknd", "source": "spotify_acoustic"},
            {"id": "m2", "title": "Save Your Tears", "artist": "The Weeknd", "source": "spotify_acoustic"}
        ]

    monkeypatch.setattr(recommendation_engine, "get_recommendations", fake_get_recs)

    output = get_similar_tracks(title="Starboy", artist="The Weeknd", limit=2)
    assert "Recommended tracks for 'Starboy' by The Weeknd:" in output
    assert "Blinding Lights - The Weeknd (spotify_acoustic)" in output
    assert "Save Your Tears - The Weeknd (spotify_acoustic)" in output

def test_hindi_language_detection_and_filtering():
    from recommender import is_indian_hindi_track, is_blatant_western_track
    assert is_indian_hindi_track("Kesariya", "Arijit Singh") is True
    assert is_indian_hindi_track("Tum Hi Ho", "Mithoon") is True
    assert is_indian_hindi_track("Chaleya", "Anirudh Ravichander") is True
    assert is_indian_hindi_track("Starboy", "The Weeknd") is False
    assert is_blatant_western_track("Blinding Lights", "The Weeknd") is True
    assert is_blatant_western_track("Cruel Summer", "Taylor Swift") is True
    assert is_blatant_western_track("Kesariya", "Arijit Singh") is False

def test_filter_and_diversify_western_exclusion_on_hindi():
    engine = RecommendationEngine()
    tracks = [
        {"id": "h1", "title": "Tum Hi Ho", "artist": "Arijit Singh"},
        {"id": "w1", "title": "Blinding Lights", "artist": "The Weeknd"},
        {"id": "h2", "title": "Apna Bana Le", "artist": "Sachin-Jigar"},
        {"id": "w2", "title": "Anti-Hero", "artist": "Taylor Swift"},
    ]
    filtered = engine._filter_and_diversify(tracks, limit=5, is_indian=True)
    artists = [t["artist"] for t in filtered]
    assert "The Weeknd" not in artists
    assert "Taylor Swift" not in artists
    assert len(filtered) == 2
    assert filtered[0]["id"] == "h1"
    assert filtered[1]["id"] == "h2"


@pytest.mark.unit
def test_sicklot_hustle_indian_detection():
    """Verify that SickLot and Hustle tracks are recognized as Indian/Hindi for proper language-coherent autoplay."""
    assert is_indian_hindi_track("La La La", "SickLot") is True
    assert is_indian_hindi_track("La La La", "SickLot, Aditya Pushkarna") is True
    assert is_indian_hindi_track("Hustle 5 Episode", "Various Artists") is True


# ============================================================================
# Spotify Recommendation Engine Tests: Annoy, BaRT, Daily Mixes, Discover Weekly
# ============================================================================

def test_acoustic_vector_and_similarity():
    from recommender import AcousticVector
    vec1 = AcousticVector(energy=0.8, valence=0.7, danceability=0.9, acousticness=0.1, tempo_norm=0.75)
    vec2 = AcousticVector(energy=0.8, valence=0.7, danceability=0.9, acousticness=0.1, tempo_norm=0.75)
    # Identical vectors should have similarity of 1.0
    assert abs(vec1.cosine_similarity(vec2) - 1.0) < 1e-4

    # Divergent vector
    vec3 = AcousticVector(energy=0.1, valence=0.2, danceability=0.1, acousticness=0.9, tempo_norm=0.2)
    sim = vec1.cosine_similarity(vec3)
    assert 0.0 <= sim < 0.85

    # Clamping bounds
    clamped = AcousticVector(energy=1.5, valence=-0.5)
    assert clamped.energy == 1.0
    assert clamped.valence == 0.0


def test_annoy_index_simulator():
    from recommender import AnnoyIndexSimulator, AcousticVector
    index = AnnoyIndexSimulator(n_trees=3)
    index.add_item("t1", AcousticVector(0.9, 0.8, 0.9, 0.1, 0.8), {"title": "Fast Dance"})
    index.add_item("t2", AcousticVector(0.85, 0.75, 0.85, 0.15, 0.75), {"title": "Pop Hit"})
    index.add_item("t3", AcousticVector(0.1, 0.2, 0.15, 0.9, 0.2), {"title": "Acoustic Folk"})

    index.build()
    query_vec = AcousticVector(0.9, 0.8, 0.9, 0.1, 0.8)
    results = index.query(query_vec, k=2)
    assert len(results) == 2
    # The nearest neighbor should be t1 with similarity ~1.0
    assert results[0][0] == "t1"
    assert abs(results[0][1] - 1.0) < 1e-4


def test_bart_contextual_bandit_exploration_vs_exploitation():
    from recommender import BaRTContextualBandit
    bandit = BaRTContextualBandit()
    ctx = bandit.get_context_weights("test_user_1")
    assert ctx["user_id"] == "test_user_1"
    assert "time_of_day" in ctx
    assert "acoustic_bias" in ctx
    assert ctx["exploration_rate"] >= 0.08
    assert ctx["exploitation_rate"] + ctx["exploration_rate"] == pytest.approx(1.0, 0.01)
    assert ctx["momentum_state"] == "exploratory"

    # Positive feedback
    fb = bandit.record_feedback("test_user_1", "track_123", "stream", listen_seconds=45)
    assert fb["reward_delta"] == 1.0
    assert fb["consecutive_skips"] == 0


def test_bart_session_momentum_collapse():
    from recommender import BaRTContextualBandit
    bandit = BaRTContextualBandit()
    uid = "skip_prone_user"

    # Simulate 3 consecutive rapid skips
    bandit.record_feedback(uid, "tr1", "skip", listen_seconds=5)
    bandit.record_feedback(uid, "tr2", "skip", listen_seconds=8)
    bandit.record_feedback(uid, "tr3", "skip", listen_seconds=12)

    ctx = bandit.get_context_weights(uid)
    assert ctx["consecutive_skips"] == 3
    # Churn guard: exploration collapsed to 0.0 to force safe favorites!
    assert ctx["exploration_rate"] == 0.0
    assert ctx["momentum_state"] == "recovery_conservative"

    # Now user listens to a song all the way through: retention restored!
    bandit.record_feedback(uid, "fav_track", "stream", listen_seconds=60)
    ctx_recovered = bandit.get_context_weights(uid)
    assert ctx_recovered["consecutive_skips"] == 0
    assert ctx_recovered["exploration_rate"] > 0.0
    assert ctx_recovered["momentum_state"] == "exploratory"


def test_get_daily_mixes():
    mixes = recommendation_engine.get_daily_mixes(user_id="dave")
    assert len(mixes) == 6
    assert mixes[0]["id"] == "daily_mix_1"
    assert mixes[0]["title"] == "Daily Mix 1"
    assert "tracks" in mixes[0]
    assert len(mixes[0]["tracks"]) > 0
    # Duration formatted check
    assert "duration_formatted" in mixes[0]["tracks"][0]
    assert "tag" in mixes[0]
    assert "color" in mixes[0]


def test_get_discover_weekly():
    dw = recommendation_engine.get_discover_weekly(user_id="dave")
    assert dw["id"] == "discover_weekly"
    assert dw["title"] == "Discover Weekly"
    assert dw["refresh_day"] == "Monday"
    assert len(dw["tracks"]) >= 5
    assert dw["tracks"][0]["novelty_score"] > 0.7
    assert "duration_formatted" in dw["tracks"][0]
    assert "context" in dw


def test_mcp_tools_daily_mixes_and_feedback():
    from mcp_server import get_daily_mixes, get_discover_weekly, record_recommendation_feedback
    mixes_text = get_daily_mixes(user_id="dave")
    assert "Daily Mix 1" in mixes_text
    assert "Daily Mix 6" in mixes_text

    dw_text = get_discover_weekly(user_id="dave")
    assert "Discover Weekly" in dw_text
    assert "Discovery Candidates" in dw_text

    fb_text = record_recommendation_feedback(track_id="test_mcp_trk", action="stream", listen_seconds=40)
    assert '"reward_delta": 1.0' in fb_text


@pytest.mark.integration
def test_http_recommendation_endpoints(client):
    import json
    headers = {"Content-Type": "application/json"}

    # 1. GET /api/recommendations/daily-mixes
    client.request("GET", "/api/recommendations/daily-mixes?user_id=dave")
    resp_mixes = client.getresponse()
    assert resp_mixes.status == 200
    mix_data = json.loads(resp_mixes.read().decode("utf-8"))
    assert mix_data["status"] == "success"
    assert "mixes" in mix_data
    assert len(mix_data["mixes"]) == 6
    assert mix_data["mixes"][0]["id"] == "daily_mix_1"

    # 2. GET /api/recommendations/discover-weekly
    client.request("GET", "/api/recommendations/discover-weekly?user_id=dave")
    resp_dw = client.getresponse()
    assert resp_dw.status == 200
    dw_data = json.loads(resp_dw.read().decode("utf-8"))
    assert dw_data["status"] == "success"
    assert "discover_weekly" in dw_data
    assert dw_data["discover_weekly"]["refresh_day"] == "Monday"
    assert len(dw_data["discover_weekly"]["tracks"]) >= 5

    # 3. GET /api/recommendations/daylist
    client.request("GET", "/api/recommendations/daylist?user_id=dave&hour=14&day=Friday")
    resp_dl = client.getresponse()
    assert resp_dl.status == 200
    dl_data = json.loads(resp_dl.read().decode("utf-8"))
    assert dl_data["status"] == "success"
    assert "daylist" in dl_data
    assert dl_data["daylist"]["daypart"] == "afternoon"
    assert "friday" in dl_data["daylist"]["title"].lower()
    assert len(dl_data["daylist"]["tracks"]) >= 4

    # 4. GET /api/recommendations/context
    client.request("GET", "/api/recommendations/context?user_id=dave")
    resp_ctx = client.getresponse()
    assert resp_ctx.status == 200
    ctx_data = json.loads(resp_ctx.read().decode("utf-8"))
    assert ctx_data["status"] == "success"
    assert "context" in ctx_data
    assert "exploration_rate" in ctx_data["context"]

    # 5. POST /api/recommendations/feedback
    fb_payload = {
        "user_id": "dave",
        "track_id": "4NRXx6U8ABQ",
        "action": "stream",
        "listen_seconds": 45
    }
    client.request("POST", "/api/recommendations/feedback", body=json.dumps(fb_payload), headers=headers)
    resp_fb = client.getresponse()
    assert resp_fb.status == 200
    fb_res = json.loads(resp_fb.read().decode("utf-8"))
    assert fb_res["status"] == "success"
    assert fb_res["feedback"]["reward_delta"] == 1.0


def test_get_daylist_and_dayparting():
    from recommender import recommendation_engine

    # Test Early Morning
    dl_early = recommendation_engine.get_daylist(user_id="test_user", hour=6, day_name="Sunday")
    assert dl_early["daypart"] == "early morning"
    assert "sunday" in dl_early["title"].lower()
    assert len(dl_early["palette"]) == 3
    assert len(dl_early["tracks"]) >= 4

    # Test Afternoon
    dl_afternoon = recommendation_engine.get_daylist(user_id="test_user", hour=15, day_name="Friday")
    assert dl_afternoon["daypart"] == "afternoon"
    assert "upbeat momentum" in dl_afternoon["title"]

    # Test Late Night
    dl_night = recommendation_engine.get_daylist(user_id="test_user", hour=1, day_name="Wednesday")
    assert dl_night["daypart"] == "late night"
    assert "lo-fi midnight thoughts" in dl_night["title"]



