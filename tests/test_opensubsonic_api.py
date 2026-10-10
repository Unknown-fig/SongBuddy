import os
import json
import hashlib
import requests
import xml.etree.ElementTree as ET
import pytest

from mcp_server import subsonic_ping, subsonic_search, subsonic_stream_info, subsonic_client_connect_info
from opensubsonic import authenticate_subsonic, build_subsonic_response, format_subsonic_song


def test_authenticate_subsonic_token_and_salt():
    salt = "random_salt_123"
    token = hashlib.md5(("songbuddy" + salt).encode("utf-8")).hexdigest()
    params = {"u": ["admin"], "t": [token], "s": [salt]}
    is_auth, user, err = authenticate_subsonic(params, {})
    assert is_auth is True
    assert user == "admin"
    assert err is None


def test_authenticate_subsonic_legacy_password():
    params = {"u": ["admin"], "p": ["songbuddy"]}
    is_auth, user, err = authenticate_subsonic(params, {})
    assert is_auth is True
    assert user == "admin"


def test_authenticate_subsonic_invalid_credentials():
    old_env = os.environ.get("ENVIRONMENT")
    old_req = os.environ.get("REQUIRE_AUTH")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["REQUIRE_AUTH"] = "true"
        params = {"u": ["admin"], "p": ["wrong_password"]}
        is_auth, user, err = authenticate_subsonic(params, {})
        assert is_auth is False
        assert err is not None
    finally:
        if old_env is not None:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        if old_req is not None:
            os.environ["REQUIRE_AUTH"] = old_req
        else:
            os.environ.pop("REQUIRE_AUTH", None)


def test_build_subsonic_response_json():
    body, ctype, status = build_subsonic_response({"testKey": "testVal"}, is_json=True)
    assert status == 200
    assert "application/json" in ctype
    data = json.loads(body.decode("utf-8"))
    assert data["subsonic-response"]["status"] == "ok"
    assert data["subsonic-response"]["testKey"] == "testVal"
    assert data["subsonic-response"]["openSubsonic"] is True


def test_build_subsonic_response_xml():
    body, ctype, status = build_subsonic_response({"testKey": "testVal"}, is_json=False)
    assert status == 200
    assert "text/xml" in ctype
    root = ET.fromstring(body.decode("utf-8"))
    assert root.attrib.get("status") == "ok"
    assert root.attrib.get("openSubsonic") == "true"


def test_subsonic_ping_endpoint_json(test_server):
    salt = "s123"
    token = hashlib.md5(("songbuddy" + salt).encode("utf-8")).hexdigest()
    resp = requests.get(f"{test_server}/rest/ping.view?u=admin&t={token}&s={salt}&f=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert data["subsonic-response"]["version"] == "1.16.1"


def test_subsonic_ping_endpoint_xml(test_server):
    resp = requests.get(f"{test_server}/rest/ping?u=admin&p=songbuddy")
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    assert root.attrib.get("status") == "ok"


def test_subsonic_get_open_subsonic_extensions(test_server):
    # Discovery must be public
    resp = requests.get(f"{test_server}/rest/getOpenSubsonicExtensions.view?f=json")
    assert resp.status_code == 200
    data = resp.json()
    exts = data["subsonic-response"]["openSubsonicExtensions"]
    ext_names = [e["name"] for e in exts]
    assert "transcodeOffset" in ext_names
    assert "apiKeyAuthentication" in ext_names


def test_subsonic_get_license(test_server):
    resp = requests.get(f"{test_server}/rest/getLicense.view?u=admin&p=songbuddy&f=json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subsonic-response"]["license"]["valid"] is True


def test_subsonic_get_music_folders(test_server):
    resp = requests.get(f"{test_server}/rest/getMusicFolders.view?u=admin&p=songbuddy&f=json")
    assert resp.status_code == 200
    data = resp.json()
    folders = data["subsonic-response"]["musicFolders"]["musicFolder"]
    assert len(folders) >= 1
    assert folders[0]["name"] == "SongBuddy Library"


def test_subsonic_search3(test_server):
    resp = requests.get(f"{test_server}/rest/search3.view?query=blinding&u=admin&p=songbuddy&f=json")
    assert resp.status_code == 200
    data = resp.json()
    sr = data["subsonic-response"]["searchResult3"]
    assert "song" in sr
    assert len(sr["song"]) >= 1
    song = sr["song"][0]
    assert "id" in song
    assert "title" in song
    assert "artist" in song
    assert "duration" in song


def test_subsonic_get_song(test_server):
    resp = requests.get(f"{test_server}/rest/getSong.view?id=4NRXx6U8ABQ&u=admin&p=songbuddy&f=json")
    assert resp.status_code == 200
    data = resp.json()
    song = data["subsonic-response"]["song"]
    assert song["id"] == "4NRXx6U8ABQ"
    assert song["title"] == "Blinding Lights"
    assert song["artist"] == "The Weeknd"


def test_subsonic_get_cover_art(test_server):
    resp = requests.get(f"{test_server}/rest/getCoverArt.view?id=4NRXx6U8ABQ&u=admin&p=songbuddy", allow_redirects=False)
    assert resp.status_code == 307
    assert "i.ytimg.com" in resp.headers.get("Location", "")


def test_subsonic_get_lyrics(test_server):
    resp = requests.get(f"{test_server}/rest/getLyrics.view?id=4NRXx6U8ABQ&title=Blinding%20Lights&artist=The%20Weeknd&u=admin&p=songbuddy&f=json")
    assert resp.status_code == 200
    data = resp.json()
    lyrics = data["subsonic-response"]["lyrics"]
    assert "artist" in lyrics
    assert "title" in lyrics
    assert "value" in lyrics


def test_subsonic_playlists_and_playback_events(test_server):
    # 1. Create playlist
    create_resp = requests.get(
        f"{test_server}/rest/createPlaylist.view?name=Mobile+Sync+Playlist&songId=4NRXx6U8ABQ&u=admin&p=songbuddy&f=json"
    )
    assert create_resp.status_code == 200
    pl_data = create_resp.json()["subsonic-response"]["playlist"]
    pl_id = pl_data["id"]
    assert pl_data["name"] == "Mobile Sync Playlist"

    # 2. Get playlists
    list_resp = requests.get(f"{test_server}/rest/getPlaylists.view?u=admin&p=songbuddy&f=json")
    assert list_resp.status_code == 200
    playlists = list_resp.json()["subsonic-response"]["playlists"]["playlist"]
    assert any(p["id"] == pl_id for p in playlists)

    # 3. Get single playlist
    get_resp = requests.get(f"{test_server}/rest/getPlaylist.view?id={pl_id}&u=admin&p=songbuddy&f=json")
    assert get_resp.status_code == 200
    assert get_resp.json()["subsonic-response"]["playlist"]["id"] == pl_id

    # 4. Scrobble & Star
    scrobble_resp = requests.get(f"{test_server}/rest/scrobble.view?id=4NRXx6U8ABQ&u=admin&p=songbuddy&f=json")
    assert scrobble_resp.status_code == 200
    star_resp = requests.get(f"{test_server}/rest/star.view?id=4NRXx6U8ABQ&u=admin&p=songbuddy&f=json")
    assert star_resp.status_code == 200

    # 5. Delete playlist
    del_resp = requests.get(f"{test_server}/rest/deletePlaylist.view?id={pl_id}&u=admin&p=songbuddy&f=json")
    assert del_resp.status_code == 200


def test_mcp_subsonic_tools():
    # 1. Subsonic Ping tool
    ping_res = json.loads(subsonic_ping(username="admin", password="songbuddy"))
    assert ping_res["status"] == "ok"
    assert ping_res["openSubsonic"] is True
    assert "transcodeOffset" in ping_res["extensions_supported"]

    # 2. Subsonic Search tool
    search_res = json.loads(subsonic_search(query="blinding", count=5))
    assert search_res["subsonic-response"]["status"] == "ok"
    assert len(search_res["subsonic-response"]["searchResult3"]["song"]) >= 1

    # 3. Subsonic Stream Info tool
    stream_res = json.loads(subsonic_stream_info(track_id="4NRXx6U8ABQ"))
    assert stream_res["status"] == "success"
    assert "rest/stream" in stream_res["stream_endpoint"]
    assert "Symfonium (Android)" in stream_res["supported_clients"]

    # 4. Subsonic Client Connect Info tool
    conn_res = json.loads(subsonic_client_connect_info())
    assert conn_res["status"] == "success"
    assert conn_res["server_configuration"]["username"] == "admin"
    assert "Symfonium" in conn_res["compatible_apps"]["android"][0]["name"]
