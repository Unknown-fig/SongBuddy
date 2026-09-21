import pytest
from pydantic import ValidationError
from validators import (
    SearchQueryValidator,
    VideoIDValidator,
    LyricsQueryValidator,
    UserCredentialsValidator
)

def test_search_query_validator():
    # Valid query
    v = SearchQueryValidator(q="The Weeknd", limit=10)
    assert v.q == "The Weeknd"
    assert v.limit == 10

    # Sanitization of dangerous characters
    v_clean = SearchQueryValidator(q="<script>alert('XSS')</script>")
    assert "<" not in v_clean.q
    assert ">" not in v_clean.q

    # Empty query should fail
    with pytest.raises(ValidationError):
        SearchQueryValidator(q="")

def test_video_id_validator():
    # Valid YouTube 11-char ID
    v = VideoIDValidator(id="4NRXx6U8ABQ")
    assert v.id == "4NRXx6U8ABQ"

    # Too short
    with pytest.raises(ValidationError):
        VideoIDValidator(id="short_id")

    # Invalid characters
    with pytest.raises(ValidationError):
        VideoIDValidator(id="4NRXx6U8AB!")

def test_lyrics_query_validator():
    v = LyricsQueryValidator(title="Blinding Lights", artist="The Weeknd", duration=200.0)
    assert v.title == "Blinding Lights"
    assert v.artist == "The Weeknd"
    assert v.duration == 200.0

def test_user_credentials_validator():
    # Strong password
    v = UserCredentialsValidator(username="new_user_1", password="ValidPassword123!")
    assert v.username == "new_user_1"

    # Weak password - missing number
    with pytest.raises(ValidationError):
        UserCredentialsValidator(username="user1", password="NoNumberPassword")

    # Too short username
    with pytest.raises(ValidationError):
        UserCredentialsValidator(username="ab", password="ValidPassword123!")
