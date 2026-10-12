"""
Unit tests for SongBuddy Recommendation Engine (recommender.py) and its API / MCP interfaces.
"""
import pytest
from recommender import RecommendationEngine, recommendation_engine
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
