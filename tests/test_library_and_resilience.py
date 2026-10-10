import pytest
import json
from library_store import library_store
from importer import detect_playlist_source
import server

def test_library_playlists_and_favorites():
    user_id = "test_audiophile"
    # 1. Create playlist
    pl = library_store.save_user_playlist(user_id, {
        "name": "Late Night Coding",
        "description": "Deep focus synthwave",
        "tracks": [
            {"id": "synth_01", "title": "Midnight City", "artist": "M83", "duration": 240}
        ]
    })
    assert pl["name"] == "Late Night Coding"
    assert pl["track_count"] == 1

    # 2. Retrieve playlists
    playlists = library_store.get_user_playlists(user_id)
    assert len(playlists) >= 1
    assert any(p["name"] == "Late Night Coding" for p in playlists)

    # 3. Toggle favorite
    fav_res = library_store.toggle_user_favorite(user_id, {
        "id": "fav_01",
        "title": "Starboy",
        "artist": "The Weeknd",
        "duration": 230
    })
    assert fav_res["is_favorite"] is True

    favs = library_store.get_user_favorites(user_id)
    assert any(f["id"] == "fav_01" for f in favs)

    # 4. Untoggle favorite
    unfav_res = library_store.toggle_user_favorite(user_id, {"id": "fav_01"})
    assert unfav_res["is_favorite"] is False

def test_listening_history_and_smart_playlists():
    user_id = "test_listener"
    track = {"id": "track_on_repeat", "title": "Blinding Lights", "artist": "The Weeknd", "duration": 200}
    # Record play twice so it qualifies for "On Repeat"
    library_store.record_user_play(user_id, track)
    library_store.record_user_play(user_id, track)

    smart = library_store.get_smart_playlists(user_id)
    assert len(smart["recently_played"]) >= 1
    assert len(smart["on_repeat"]) >= 1
    assert smart["on_repeat"][0]["id"] == "track_on_repeat"
    assert smart["on_repeat"][0]["play_count"] >= 2

def test_playlist_importer_detection():
    assert detect_playlist_source("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M") == "spotify"
    assert detect_playlist_source("https://www.youtube.com/playlist?list=PL4fGSI1pDJn6jXS_PEoN7G9s2_01F9j8S") == "youtube"
    assert detect_playlist_source("https://music.apple.com/us/playlist/today-hits/pl.f4d1060b52a24e") == "apple_music"

def test_cookie_health_probe():
    probe = server.get_cookie_health_status()
    assert "status" in probe
    assert "entries_count" in probe
    assert probe["status"] in ("healthy", "expiring_soon", "expired", "missing")
