import json
import pytest
from http.client import HTTPConnection
from server import parse_lrc_to_cues, analyze_karaoke_profile, LYRICS_CACHE
import mcp_server

SAMPLE_LRC = """[00:13.13] Yeah
[00:27.16] I've been tryna call
[00:29.96] I've been on my own for long enough
[00:32.71] Maybe you can show me how to love, maybe
"""

@pytest.mark.unit
def test_parse_lrc_to_cues():
    """Verify that parse_lrc_to_cues accurately parses millisecond timestamps and calculates durations."""
    cues = parse_lrc_to_cues(SAMPLE_LRC)
    assert len(cues) == 4
    assert cues[0]["time"] == 13.13
    assert cues[0]["text"] == "Yeah"
    assert cues[0]["duration"] == round(27.16 - 13.13, 2)
    assert cues[1]["time"] == 27.16
    assert cues[1]["text"] == "I've been tryna call"
    assert cues[3]["text"] == "Maybe you can show me how to love, maybe"

@pytest.mark.unit
def test_parse_lrc_empty():
    """Verify handling of empty or invalid LRC strings."""
    assert parse_lrc_to_cues(None) == []
    assert parse_lrc_to_cues("") == []
    assert parse_lrc_to_cues("Plain text without tags") == []

@pytest.mark.unit
def test_analyze_karaoke_profile_cached():
    """Verify analyze_karaoke_profile creates correct vocal isolation DSP parameters."""
    cache_key = ("test song", "test artist")
    LYRICS_CACHE.set(cache_key, {
        "syncedLyrics": SAMPLE_LRC,
        "plainLyrics": "Plain text",
        "instrumental": False
    })
    
    profile = analyze_karaoke_profile("test song", "test artist")
    assert profile["status"] == "ready"
    assert profile["has_synced_karaoke"] is True
    assert profile["total_cues"] == 4
    assert profile["first_vocal_timestamp"] == 13.13
    assert "vocal_cancellation" in profile
    assert profile["vocal_cancellation"]["estimated_attenuation_db"] == -24.0
    assert profile["vocal_cancellation"]["bass_preservation_cutoff_hz"] == 120

@pytest.mark.integration
def test_lyrics_sse_endpoint(client):
    """Verify /api/lyrics/sse delivers Server-Sent Events headers and manifest payload."""
    cache_key = ("blinding lights", "the weeknd")
    LYRICS_CACHE.set(cache_key, {
        "syncedLyrics": SAMPLE_LRC,
        "plainLyrics": "Plain",
        "instrumental": False
    })

    client.request("GET", "/api/lyrics/sse?title=blinding+lights&artist=the+weeknd")
    resp = client.getresponse()

    assert resp.status == 200
    content_type = resp.getheader("Content-Type")
    assert "text/event-stream" in content_type

    body = resp.read().decode("utf-8")
    assert "event: manifest" in body
    assert "event: sync" in body
    assert "Yeah" in body

@pytest.mark.integration
def test_karaoke_analysis_endpoint(client):
    """Verify /api/karaoke endpoint returns JSON readiness profile."""
    cache_key = ("blinding lights", "the weeknd")
    LYRICS_CACHE.set(cache_key, {
        "syncedLyrics": SAMPLE_LRC,
        "plainLyrics": "Plain",
        "instrumental": False
    })

    client.request("GET", "/api/karaoke?title=blinding+lights&artist=the+weeknd")
    resp = client.getresponse()

    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "ready"
    assert data["has_synced_karaoke"] is True
    assert "vocal_cancellation" in data

@pytest.mark.unit
def test_mcp_realtime_lyrics_tool():
    """Verify MCP tool get_realtime_lyrics_stream returns valid JSON string with timeline cues."""
    cache_key = ("blinding lights", "the weeknd")
    LYRICS_CACHE.set(cache_key, {
        "syncedLyrics": SAMPLE_LRC,
        "plainLyrics": "Plain",
        "instrumental": False
    })

    res_str = mcp_server.get_realtime_lyrics_stream("blinding lights", "the weeknd")
    data = json.loads(res_str)
    assert data["status"] == "success"
    assert data["total_cues"] == 4
    assert len(data["timeline_cues"]) == 4

@pytest.mark.unit
def test_mcp_karaoke_readiness_tool():
    """Verify MCP tool analyze_karaoke_readiness returns valid JSON profile."""
    cache_key = ("blinding lights", "the weeknd")
    LYRICS_CACHE.set(cache_key, {
        "syncedLyrics": SAMPLE_LRC,
        "plainLyrics": "Plain",
        "instrumental": False
    })

    res_str = mcp_server.analyze_karaoke_readiness("blinding lights", "the weeknd")
    data = json.loads(res_str)
    assert data["status"] == "ready"
    assert "vocal_cancellation" in data


@pytest.mark.unit
def test_is_valid_lyrics_match_rejection():
    """Verify is_valid_lyrics_match rejects completely mismatched tracks from search results."""
    from server import is_valid_lyrics_match
    bogus_candidate = {
        "trackName": "In For The Kill",
        "artistName": "La Roux"
    }
    assert is_valid_lyrics_match(bogus_candidate, "La La La", "Release") is False
    assert is_valid_lyrics_match(bogus_candidate, "La La La", "SickLot") is False

    valid_candidate = {
        "trackName": "Blinding Lights",
        "artistName": "The Weeknd"
    }
    assert is_valid_lyrics_match(valid_candidate, "Blinding Lights", "The Weeknd") is True


@pytest.mark.unit
def test_clean_track_title_youtube_distributor():
    """Verify clean_track_title extracts genuine artists from distributor description when channel is generic."""
    from server import clean_track_title
    desc = "Provided to YouTube by Erik\n\nLa La La · SickLot · Aditya Pushkarna\n\nHustle 5 - Episode 13"
    title, artist = clean_track_title("La La La", "Release - Topic", description=desc)
    assert title == "La La La"
    assert "SickLot" in artist


@pytest.mark.unit
def test_fetch_lyrics_sicklot_local_fallback():
    """Verify fetch_lyrics returns verified local lyrics for SickLot's 'La La La'."""
    from server import fetch_lyrics
    lyrics = fetch_lyrics("La La La", "SickLot")
    assert lyrics is not None
    assert lyrics.get("syncedLyrics") is not None
    assert "Milay mujhse woh akhiyaan churaake" in lyrics["syncedLyrics"]
    assert "Shawty mujhe dekhe, she go la la la" in lyrics["plainLyrics"]


@pytest.mark.integration
def test_lyrics_endpoint_generic_artist_resolution(client):
    """Verify /api/lyrics correctly resolves generic 'Release' artist for La La La to SickLot."""
    client.request("GET", "/api/lyrics?title=La+La+La&artist=Release")
    resp = client.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert "syncedLyrics" in data
    assert "Milay mujhse woh akhiyaan churaake" in data["syncedLyrics"]

