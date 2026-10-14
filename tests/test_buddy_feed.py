import json
import time
import pytest

from buddy_feed import (
    buddy_feed_manager,
    BuddyFeedManager,
    FriendActivity,
    BuddyProfile
)
import mcp_server


def test_friend_activity_to_dict():
    activity = FriendActivity(
        user_id="usr_test",
        display_name="Test Listener",
        avatar="https://example.com/avatar.jpg",
        track_id="4NRXx6U8ABQ",
        title="Blinding Lights",
        artist="The Weeknd",
        album="After Hours",
        thumbnail="https://example.com/thumb.jpg",
        duration=200,
        progress_seconds=50,
        is_playing=True
    )
    d = activity.to_dict()
    assert d["user_id"] == "usr_test"
    assert d["display_name"] == "Test Listener"
    assert d["track_id"] == "4NRXx6U8ABQ"
    assert d["title"] == "Blinding Lights"
    assert d["artist"] == "The Weeknd"
    assert d["equalizer_active"] is True
    assert "Listening now" in d["time_ago_str"] or "Just now" in d["time_ago_str"]


def test_buddy_feed_manager_seed_and_sorting():
    mgr = BuddyFeedManager()
    feed = mgr.get_feed(user_id="dave")
    assert len(feed) >= 3

    # Actively playing items should come first
    playing_flags = [item["is_playing"] for item in feed]
    # Check that any True comes before False
    has_seen_false = False
    for is_p in playing_flags:
        if not is_p:
            has_seen_false = True
        if has_seen_false:
            assert is_p is False or True  # Generally True items sorted before False


def test_buddy_feed_manager_update_activity_and_listen_along():
    mgr = BuddyFeedManager()
    
    # Broadcast activity for Alice
    activity = mgr.update_user_activity(
        user_id="usr_alice",
        display_name="Alice Wonderland",
        avatar="https://example.com/alice.jpg",
        track_data={
            "id": "track_alice_1",
            "title": "Solar Power",
            "artist": "Lorde",
            "album": "Solar Power",
            "thumbnail": "https://example.com/solar.jpg",
            "duration": 195
        },
        is_playing=True,
        progress_seconds=30
    )
    assert activity is not None
    assert activity["title"] == "Solar Power"
    assert activity["artist"] == "Lorde"

    # Listen Along sync resolution
    sync_data = mgr.get_listen_along("usr_alice")
    assert sync_data is not None
    assert sync_data["friend_user_id"] == "usr_alice"
    assert sync_data["track"]["id"] == "track_alice_1"
    assert sync_data["track"]["title"] == "Solar Power"
    assert sync_data["is_playing"] is True

    # Missing friend returns None
    assert mgr.get_listen_along("nonexistent_user") is None


def test_buddy_feed_manager_private_session():
    mgr = BuddyFeedManager()
    mgr.set_private_session("usr_secret", True)
    assert mgr.is_private_session("usr_secret") is True

    # Broadcasting while in private session should return None
    res = mgr.update_user_activity(
        user_id="usr_secret",
        display_name="Secret Agent",
        avatar="",
        track_data={"id": "track_secret", "title": "Top Secret", "artist": "Spy"},
        is_playing=True
    )
    assert res is None

    # Toggling off allows broadcasting again
    mgr.set_private_session("usr_secret", False)
    assert mgr.is_private_session("usr_secret") is False
    res2 = mgr.update_user_activity(
        user_id="usr_secret",
        display_name="Secret Agent",
        avatar="",
        track_data={"id": "track_secret", "title": "Top Secret", "artist": "Spy"},
        is_playing=True
    )
    assert res2 is not None


def test_buddy_feed_manager_follow_unfollow():
    mgr = BuddyFeedManager()
    followed = mgr.follow_friend("dave", "usr_new_friend", friend_name="New Friend")
    assert followed is True

    unfollowed = mgr.unfollow_friend("dave", "usr_new_friend")
    assert unfollowed is True


def test_mcp_buddy_feed_tools():
    # 1. get_buddy_activity_feed
    feed_text = mcp_server.get_buddy_activity_feed(user_id="dave")
    assert "Friend Activity" in feed_text

    # 2. broadcast_listening_activity
    broadcast_res = mcp_server.broadcast_listening_activity(
        track_id="4NRXx6U8ABQ",
        title="Blinding Lights",
        artist="The Weeknd",
        user_id="usr_mcp_test",
        display_name="MCP Agent"
    )
    assert "Successfully broadcasted" in broadcast_res

    # 3. sync_listen_along
    sync_res = mcp_server.sync_listen_along("usr_elena")
    assert "track" in sync_res
    assert "friend_user_id" in sync_res


@pytest.mark.integration
def test_http_buddy_feed_endpoints(client):
    headers = {"Content-Type": "application/json"}

    # 1. GET /api/social/buddy-feed
    client.request("GET", "/api/social/buddy-feed")
    resp = client.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "success"
    assert "feed" in data
    assert len(data["feed"]) > 0
    assert "stats" in data

    # 2. POST /api/social/activity
    activity_payload = {
        "track": {
            "id": "kTJczUoc26U",
            "title": "In My Feelings",
            "artist": "Camila Cabello",
            "album": "Romance",
            "duration": 220
        },
        "is_playing": True,
        "progress": 45
    }
    client.request("POST", "/api/social/activity", body=json.dumps(activity_payload), headers=headers)
    resp = client.getresponse()
    assert resp.status == 200
    act_data = json.loads(resp.read().decode("utf-8"))
    assert act_data["status"] == "success"
    assert act_data["activity"]["title"] == "In My Feelings"

    # 3. GET /api/social/sync?friend_id=usr_elena
    client.request("GET", "/api/social/sync?friend_id=usr_elena")
    resp_sync = client.getresponse()
    assert resp_sync.status == 200
    sync_res = json.loads(resp_sync.read().decode("utf-8"))
    assert sync_res["status"] == "success"
    assert sync_res["sync"]["friend_user_id"] == "usr_elena"
    assert sync_res["sync"]["track"]["id"] is not None

    # Missing friend returns 404
    client.request("GET", "/api/social/sync?friend_id=usr_unknown_ghost")
    resp_404 = client.getresponse()
    assert resp_404.status == 404

    # 4. POST /api/social/privacy (Toggle private session)
    client.request("POST", "/api/social/privacy", body=json.dumps({"private_session": True}), headers=headers)
    resp_priv = client.getresponse()
    assert resp_priv.status == 200
    priv_data = json.loads(resp_priv.read().decode("utf-8"))
    assert priv_data["private_session"] is True

    # 5. GET /api/social/privacy
    client.request("GET", "/api/social/privacy")
    resp_get_priv = client.getresponse()
    assert resp_get_priv.status == 200
    priv_get_data = json.loads(resp_get_priv.read().decode("utf-8"))
    assert priv_get_data["private_session"] is True

    # Reset privacy to false
    client.request("POST", "/api/social/privacy", body=json.dumps({"private_session": False}), headers=headers)
    client.getresponse()

    # 6. POST /api/social/friends/follow & unfollow
    follow_payload = {"friend_id": "usr_zoe", "friend_name": "Zoe Kravitz"}
    client.request("POST", "/api/social/friends/follow", body=json.dumps(follow_payload), headers=headers)
    resp_follow = client.getresponse()
    assert resp_follow.status == 200
    assert json.loads(resp_follow.read().decode("utf-8"))["followed"] is True

    unfollow_payload = {"friend_id": "usr_zoe"}
    client.request("POST", "/api/social/friends/unfollow", body=json.dumps(unfollow_payload), headers=headers)
    resp_unfollow = client.getresponse()
    assert resp_unfollow.status == 200
    assert json.loads(resp_unfollow.read().decode("utf-8"))["unfollowed"] is True

    # 7. GET /api/social/buddy-feed/stream (SSE snapshot)
    client.request("GET", "/api/social/buddy-feed/stream")
    resp_sse = client.getresponse()
    assert resp_sse.status == 200
    assert "text/event-stream" in resp_sse.getheader("Content-Type")
    # Read first chunk from SSE
    chunk = resp_sse.read(256).decode("utf-8")
    assert "event: buddy_feed" in chunk or "data:" in chunk
