#!/usr/bin/env python3
"""
Test real-time SSE event reception and auto-reply in MyOwnChatGateway.
"""

import os
import sys
import threading
import time

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from myownchat import Message, MyOwnChatGateway


def test_live_sse():
    print("=" * 60)
    print("  Testing Live SSE Streaming in MyOwnChatGateway")
    print("=" * 60)

    API_BASE = "https://api.marcvali.org/myownchat"
    ts = int(time.time())
    username = f"sse_tester_{ts}"
    password = "TestPassword123!"

    # 1. Register user
    reg_res = requests.post(
        f"{API_BASE}/api/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": password},
        timeout=10,
    )
    assert reg_res.ok, "Registration failed"
    auth_data = reg_res.json()
    token = auth_data.get("token") or auth_data.get("access_token")
    user_id = auth_data["user"]["id"]
    user_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Create App Channel
    create_res = requests.post(
        f"{API_BASE}/api/routine/create_app_channel",
        headers=user_headers,
        json={"user_id": user_id, "name": f"ssebot_{ts}", "bot_name": "SSE Bot", "avatar": "🤖"},
        timeout=10,
    )
    assert create_res.ok, "create_app_channel failed"
    app_info = create_res.json().get("data") or create_res.json()
    channel_id = app_info["channel"]["id"]
    api_key = app_info.get("api_key") or app_info.get("app", {}).get("api_key")

    # 3. Setup Gateway
    gateway = MyOwnChatGateway(api_key=api_key, api_base=API_BASE, bot_name="SSE Bot")
    replies_sent = []

    @gateway.on_message
    def on_msg(msg: Message):
        print(f"  [Gateway Callback] Received live message: '{msg.text}'")
        reply = f"Echo: {msg.text}"
        replies_sent.append(reply)
        return reply

    # Run gateway in background thread
    gw_thread = threading.Thread(target=gateway.start, daemon=True)
    gw_thread.start()

    time.sleep(2)  # Allow SSE to connect

    # 4. Post message from human user
    print("\n[Human User] Posting message to channel...")
    post_res = requests.post(
        f"{API_BASE}/api/table/messages",
        headers=user_headers,
        json={"channel_id": channel_id, "type": "text", "text": "Hello real-time SSE!"},
        timeout=10,
    )
    assert post_res.ok, "User post failed"
    print(f"✓ Posted message #{post_res.json()['id']}")

    # Wait up to 5 seconds for gateway to receive SSE event and post reply
    for _ in range(10):
        time.sleep(0.5)
        if replies_sent:
            break

    assert len(replies_sent) > 0, "SSE Bot did not receive message or send reply in time!"
    print(f"✓ Verified gateway sent reply via SSE callback: '{replies_sent[0]}'")

    gateway.stop()

    # Cleanup
    requests.post(
        f"{API_BASE}/api/routine/delete_app_channel",
        headers=user_headers,
        json={"user_id": user_id, "channel_id": channel_id},
        timeout=10,
    )
    print("✓ Deleted App channel")
    print("\n" + "=" * 60)
    print("  LIVE SSE STREAMING TEST PASSED! 🚀")
    print("=" * 60)


if __name__ == "__main__":
    test_live_sse()
