import json
import time
import pytest
from unittest.mock import patch, MagicMock

from social_jukebox import (
    jukebox_manager,
    share_link_manager,
    generate_qr_svg,
    JukeboxRoom
)
import mcp_server


def test_generate_qr_svg():
    svg = generate_qr_svg("https://songbuddy-swart.vercel.app/#party=TEST01")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "jukebox-qr-svg" in svg


def test_jukebox_room_enqueue_and_duplicates():
    room, host_token = jukebox_manager.create_room(name="Synthwave Lounge", max_guest_songs=3)
    track1 = {
        "id": "track_abc_1",
        "title": "Midnight City",
        "artist": "M83",
        "duration": 240,
        "thumbnail": "https://img.youtube.com/vi/track_abc_1/0.jpg"
    }

    # 1. Enqueue track
    item = room.enqueue_track(track1, guest_id="guest_alice", guest_name="Alice")
    assert item["track_id"] == "track_abc_1"
    assert item["score"] == 1
    assert item["upvotes_count"] == 1
    assert len(room.queue) == 1

    # 2. Duplicate prevention test
    with pytest.raises(ValueError, match="already in the party queue"):
        room.enqueue_track(track1, guest_id="guest_bob", guest_name="Bob")

    # 3. Rate limit test (max 3 songs per guest)
    for i in range(2, 4):
        room.enqueue_track(
            {"id": f"track_abc_{i}", "title": f"Song {i}", "artist": "Artist", "duration": 200},
            guest_id="guest_alice"
        )
    assert len(room.queue) == 3

    # 4th song should breach rate limit
    with pytest.raises(ValueError, match="rate limit reached"):
        room.enqueue_track(
            {"id": "track_abc_4", "title": "Song 4", "artist": "Artist", "duration": 200},
            guest_id="guest_alice"
        )


def test_jukebox_voting_and_queue_sorting():
    room, host_token = jukebox_manager.create_room(name="Voting Room")
    
    # Enqueue track 1 (score 1 from guest A)
    item1 = room.enqueue_track(
        {"id": "song_1", "title": "Track One", "artist": "A", "duration": 180},
        guest_id="user_a"
    )
    # Enqueue track 2 (score 1 from guest B)
    item2 = room.enqueue_track(
        {"id": "song_2", "title": "Track Two", "artist": "B", "duration": 180},
        guest_id="user_b"
    )

    # Guest C upvotes track 2 -> track 2 score becomes 2
    room.vote_track(item2["queue_id"], guest_id="user_c", direction="up")
    assert room.queue[0].track_id == "song_2"
    assert room.queue[0].score == 2

    # Guest D downvotes track 2 -> track 2 score becomes 1
    room.vote_track(item2["queue_id"], guest_id="user_d", direction="down")
    assert room.queue[0].score == 1

    # Pop next track with host token
    next_up = room.pop_next_track(host_token=host_token)
    assert next_up is not None
    assert room.active_track is not None
    assert len(room.queue) == 1

    # Invalid host token raises PermissionError
    with pytest.raises(PermissionError):
        room.pop_next_track(host_token="wrong_secret")


def test_share_link_lifecycle():
    # 1. Mint valid token
    minted = share_link_manager.mint_token(
        item_type="track",
        item_id="4NRXx6U8ABQ",
        title="Blinding Lights",
        artist="The Weeknd",
        duration_hours=2,
        allow_download=True
    )
    assert minted["status"] == "success"
    token = minted["token"]
    assert "." in token

    # 2. Resolve token
    res = share_link_manager.resolve_token(token)
    assert res["valid"] is True
    assert res["status"] == "active"
    assert res["item_id"] == "4NRXx6U8ABQ"
    assert res["allow_download"] is True
    assert res["hours_remaining"] > 0

    # 3. Tampered signature test
    bad_token = token[:-4] + "ffff"
    res_bad = share_link_manager.resolve_token(bad_token)
    assert res_bad["valid"] is False
    assert res_bad["status"] == "invalid_signature"

    # 4. Expired token test (mint with 0 duration or mock time)
    with patch("time.time", return_value=time.time() + 86400 * 3):
        res_exp = share_link_manager.resolve_token(token)
        assert res_exp["valid"] is False
        assert res_exp["status"] == "expired"


def test_mcp_social_jukebox_tools():
    # 1. create_jukebox_party
    party_json = mcp_server.create_jukebox_party(name="Agent Party Suite", max_guest_songs=4)
    party = json.loads(party_json)
    assert party["status"] == "success"
    assert "room_code" in party
    code = party["room_code"]

    # 2. enqueue_jukebox_track
    enq_json = mcp_server.enqueue_jukebox_track(room_code=code, track_id="test_vid_888", title="Starboy")
    enq = json.loads(enq_json)
    assert enq["status"] == "success"
    assert enq["item"]["track_id"] == "test_vid_888"

    # 3. get_jukebox_queue
    q_json = mcp_server.get_jukebox_queue(room_code=code)
    q = json.loads(q_json)
    assert q["total_queued"] == 1
    queue_id = q["queue"][0]["queue_id"]

    # 4. vote_jukebox_track
    vote_json = mcp_server.vote_jukebox_track(room_code=code, queue_id=queue_id, direction="up")
    vote = json.loads(vote_json)
    assert vote["status"] == "success"

    # 5. mint_expirable_share_link
    share_json = mcp_server.mint_expirable_share_link("test_vid_888", title="Starboy", duration_hours=12)
    share = json.loads(share_json)
    assert share["status"] == "success"
    assert "token" in share
    assert "public_url" in share


@pytest.mark.integration
def test_http_jukebox_endpoints(client):
    headers = {"Content-Type": "application/json"}

    # 1. Create Room via POST /api/jukebox/room
    room_payload = {"name": "VIP Neon Lounge", "max_guest_songs": 5}
    client.request("POST", "/api/jukebox/room", body=json.dumps(room_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 201
    room_data = json.loads(resp.read().decode("utf-8"))
    code = room_data["room_code"]
    host_token = room_data["host_token"]

    # 2. Get Room via GET /api/jukebox/room
    client.request("GET", f"/api/jukebox/room?code={code}")
    resp = client.getresponse()
    assert resp.status == 200
    fetched_room = json.loads(resp.read().decode("utf-8"))
    assert fetched_room["room_code"] == code

    # 3. Enqueue Track via POST /api/jukebox/queue
    track_payload = {
        "room_code": code,
        "guest_id": "test_guest_1",
        "guest_name": "Audiophile Sam",
        "track": {
            "id": "4NRXx6U8ABQ",
            "title": "Blinding Lights",
            "artist": "The Weeknd",
            "duration": 200
        }
    }
    client.request("POST", "/api/jukebox/queue", body=json.dumps(track_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 201
    enq_res = json.loads(resp.read().decode("utf-8"))
    assert enq_res["success"] is True
    queue_id = enq_res["item"]["queue_id"]

    # 4. Duplicate Enqueue should return HTTP 400
    client.request("POST", "/api/jukebox/queue", body=json.dumps(track_payload), headers=headers)
    resp_dup = client.getresponse()
    assert resp_dup.status == 400

    # 5. Vote on Track via POST /api/jukebox/vote
    vote_payload = {
        "room_code": code,
        "queue_id": queue_id,
        "direction": "up",
        "guest_id": "test_guest_2"
    }
    client.request("POST", "/api/jukebox/vote", body=json.dumps(vote_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 200
    vote_res = json.loads(resp.read().decode("utf-8"))
    assert vote_res["item"]["score"] == 2

    # 6. QR Code via GET /api/jukebox/qr
    client.request("GET", f"/api/jukebox/qr?code={code}")
    resp_qr = client.getresponse()
    assert resp_qr.status == 200
    assert "image/svg+xml" in resp_qr.getheader("Content-Type")
    svg_body = resp_qr.read().decode("utf-8")
    assert "<svg" in svg_body

    # 7. Advance Track via POST /api/jukebox/next
    next_payload = {"room_code": code, "host_token": host_token}
    client.request("POST", "/api/jukebox/next", body=json.dumps(next_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 200
    next_res = json.loads(resp.read().decode("utf-8"))
    assert next_res["next_track"]["track_id"] == "4NRXx6U8ABQ"


@pytest.mark.integration
def test_http_share_link_endpoints(client):
    headers = {"Content-Type": "application/json"}

    # 1. Mint Share Link via POST /api/share/mint
    mint_payload = {
        "type": "track",
        "id": "4NRXx6U8ABQ",
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "duration_hours": 48,
        "allow_download": True
    }
    client.request("POST", "/api/share/mint", body=json.dumps(mint_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 201
    minted = json.loads(resp.read().decode("utf-8"))
    token = minted["token"]

    # 2. Resolve Share Link via GET /api/share/resolve
    client.request("GET", f"/api/share/resolve?token={token}")
    resp = client.getresponse()
    assert resp.status == 200
    resolved = json.loads(resp.read().decode("utf-8"))
    assert resolved["valid"] is True
    assert resolved["item_id"] == "4NRXx6U8ABQ"
    assert resolved["allow_download"] is True
    assert resolved["hours_remaining"] > 40
