import pytest
from server import is_valid_youtube_id, format_duration, clean_track_title

@pytest.mark.unit
def test_youtube_id_validation():
    """Test YouTube video ID validation"""
    assert is_valid_youtube_id("dQw4w9WgXcQ") is True
    assert is_valid_youtube_id("abc123_-ABC") is True
    assert is_valid_youtube_id("invalid!") is False
    assert is_valid_youtube_id("toolongid123") is False
    assert is_valid_youtube_id("") is False

@pytest.mark.unit
def test_duration_formatting():
    """Test duration formatting"""
    assert format_duration(0) == "0:00"
    assert format_duration(59) == "0:59"
    assert format_duration(60) == "1:00"
    assert format_duration(125) == "2:05"
    assert format_duration(3661) == "61:01"
    assert format_duration(None) == "0:00"
    assert format_duration(-10) == "0:00"

@pytest.mark.unit
def test_title_cleanup():
    """Test track title cleanup"""
    title, artist = clean_track_title("Artist - Track Name (Official Video)", "Unknown")
    assert artist == "Artist"
    assert title == "Track Name"
    
    title, artist = clean_track_title("Track [HD]", "Default Artist")
    assert title == "Track"
    assert artist == "Default Artist"
