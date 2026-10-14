"""
Unit tests for Spotify-modeled Search Engine in SongBuddy
"""
import pytest
from search_engine import (
    search_engine,
    EdgeNGramIndex,
    levenshtein_distance,
    clean_track_title,
    CURATED_ARTISTS
)


def test_levenshtein_distance():
    assert levenshtein_distance("weekn", "weeknd") == 1
    assert levenshtein_distance("drke", "drake") == 1
    assert levenshtein_distance("billie elish", "billie eilish") == 1
    assert levenshtein_distance("same", "same") == 0


def test_edge_ngram_index():
    index = EdgeNGramIndex(min_gram=2, max_gram=10)
    index.add_item("item1", "The Weeknd Starboy", {"title": "Starboy", "artist": "The Weeknd"})

    # Check prefix lookups
    results = index.lookup_prefix("wee")
    assert len(results) == 1
    assert results[0]["title"] == "Starboy"

    results_star = index.lookup_prefix("star")
    assert len(results_star) == 1
    assert results_star[0]["artist"] == "The Weeknd"

    # Non-matching prefix
    assert len(index.lookup_prefix("xyz")) == 0


def test_clean_track_title():
    t, a = clean_track_title("The Weeknd - Blinding Lights (Official Music Video)", "The Weeknd VEVO")
    assert "Blinding Lights" in t
    assert "The Weeknd" in a

    t2, a2 = clean_track_title("Starboy [Official Video] ft. Daft Punk", "TheWeekndVEVO")
    assert "Starboy" in t2


def test_curated_artist_exact_and_typo_matching():
    # Exact
    m1 = search_engine.match_curated_artist("The Weeknd")
    assert m1 is not None
    assert m1["name"] == "The Weeknd"

    # Typo (Levenshtein distance <= 2)
    m2 = search_engine.match_curated_artist("weekn")
    assert m2 is not None
    assert m2["name"] == "The Weeknd"

    m3 = search_engine.match_curated_artist("drke")
    assert m3 is not None
    assert m3["name"] == "Drake"

    m4 = search_engine.match_curated_artist("arijit sing")
    assert m4 is not None
    assert m4["name"] == "Arijit Singh"


def test_search_structured_artist_top_result():
    res = search_engine.search("The Weeknd", structured=True)
    assert res["query"] == "The Weeknd"
    assert res["top_result"] is not None
    assert res["top_result"]["type"] == "artist"
    assert res["top_result"]["title"] == "The Weeknd"
    assert "Monthly Listeners" in res["top_result"]["subtitle"]
    assert "metrics" in res
    assert res["metrics"]["has_curated_artist"] is True


def test_search_flat_output_backward_compatibility():
    res = search_engine.search("The Weeknd", structured=False)
    assert isinstance(res, list)


def test_ltr_relevance_scoring_with_user_affinity():
    candidate = {
        "id": "trk_123",
        "title": "Blinding Lights",
        "artist": "The Weeknd"
    }

    # Baseline score
    score_normal = search_engine.calculate_relevance_score(
        candidate,
        query="blinding lights",
        user_affinity_artists=set(),
        user_history_ids=set()
    )
    assert score_normal >= 100.0  # Exact title match

    # With user affinity for The Weeknd
    score_affinity = search_engine.calculate_relevance_score(
        candidate,
        query="blinding lights",
        user_affinity_artists={"the weeknd"},
        user_history_ids={"trk_123"}
    )
    # Score with user affinity and history should be significantly higher
    assert score_affinity > score_normal
    assert score_affinity - score_normal >= 60.0
