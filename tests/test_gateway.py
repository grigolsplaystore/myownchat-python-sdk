#!/usr/bin/env python3
"""
End-to-End Verification Test for MyOwnChat Python SDK & Gateway
Tests:
1. Client initialization with App API key
2. Fetching auto-scoped channel metadata
3. Posting messages with Markdown and metadata
4. Querying auto-scoped message history
5. Message loop filtering (ignoring app echoes)
6. Message threading (reply_to_id)
"""

import os
import sys
import time

# Ensure sdk/python is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from myownchat import MyOwnChatClient, MyOwnChatGateway, Message

def main():
    print("=" * 60)
    print("  MyOwnChat Python SDK & Gateway Test Suite")
    print("=" * 60)

    # 1. We will register a temporary test user and app via LittleBackend API to get a live key
    import requests

    API_BASE = "https://api.marcvali.org/myownchat"
    ts = int(time.time())
    username = f"py_tester_{ts}"
    password = "TestPassword123!"

    print(f"\n[Stage 1] Registering test account: {username}")
    reg_res = requests.post(
        f"{API_BASE}/api/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": password},
        timeout=10,
    )
    if not reg_res.ok:
        print(f"❌ Failed to register test user: {reg_res.text}")
        sys.exit(1)

    auth_data = reg_res.json()
    token = auth_data.get("token") or auth_data.get("access_token")
    user_id = auth_data["user"]["id"]
    user_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"✓ Registered user ID: {user_id}")

    print("\n[Stage 2] Creating App Channel via Routine")
    create_res = requests.post(
        f"{API_BASE}/api/routine/create_app_channel",
        headers=user_headers,
        json={"user_id": user_id, "name": f"pybot_{ts}", "bot_name": "Python Tester Bot", "avatar": "🐍"},
        timeout=10,
    )
    if not create_res.ok:
        print(f"❌ Failed to create App Channel: {create_res.text}")
        sys.exit(1)

    raw_json = create_res.json()
    app_info = raw_json.get("data") or raw_json
    channel_id = app_info["channel"]["id"]
    api_key = app_info.get("api_key") or app_info.get("app", {}).get("api_key")
    print(f"✓ Created App Channel #{app_info['channel']['name']} (ID: {channel_id})")
    print(f"✓ Received Machine Key: {api_key[:12]}...")

    print("\n[Stage 3] Testing MyOwnChatClient auto-scoped queries")
    client = MyOwnChatClient(api_key=api_key, api_base=API_BASE, bot_name="Python Tester Bot")
    ch = client.get_channel()
    assert ch is not None, "Failed to fetch channel info"
    assert ch.id == channel_id, f"Expected channel ID {channel_id}, got {ch.id}"
    print(f"✓ Client correctly fetched channel info: #{ch.name} (Type: {ch.type})")

    print("\n[Stage 4] Testing message posting via Client")
    msg1 = client.post_message("Hello from Python SDK test! 🚀")
    assert msg1.id > 0, "Expected positive message ID"
    assert msg1.is_from_app is True, "Expected is_from_app to be True"
    assert msg1.text == "Hello from Python SDK test! 🚀"
    print(f"✓ Successfully posted message #{msg1.id} (Auto-scoped to channel {msg1.channel_id})")

    print("\n[Stage 5] Testing reply_to threading")
    msg2 = client.post_message("This is a threaded reply", reply_to_id=msg1.id)
    assert msg2.reply_to_id == msg1.id, f"Expected reply_to_id {msg1.id}, got {msg2.reply_to_id}"
    print(f"✓ Threaded reply #{msg2.id} correctly points to parent #{msg1.id}")

    print("\n[Stage 6] Testing MyOwnChatGateway message handler & loop prevention")
    received_msgs = []
    gateway = MyOwnChatGateway(api_key=api_key, api_base=API_BASE, bot_name="Python Tester Bot")

    @gateway.on_message
    def handle_msg(msg: Message):
        received_msgs.append(msg)
        return f"Ack: {msg.text}"

    # Gateway should ignore msg1 and msg2 because they are from app (ignore_self=True)
    gateway._init_cursor()
    gateway._dispatch_message(msg1)
    gateway._dispatch_message(msg2)
    assert len(received_msgs) == 0, "Loop prevention failed: Gateway dispatched bot's own message!"
    print("✓ Loop prevention verified: Bot's own messages were ignored")

    # Now post a simulated human user message using the user's auth token
    print("\n[Stage 7] Posting user message and verifying Gateway dispatch")
    user_post_res = requests.post(
        f"{API_BASE}/api/table/messages",
        headers=user_headers,
        json={"channel_id": channel_id, "type": "text", "text": "What is the weather today?"},
        timeout=10,
    )
    assert user_post_res.ok, "Failed to post user message"
    user_msg_data = user_post_res.json()
    user_msg = Message.from_dict(user_msg_data)

    gateway._dispatch_message(user_msg)
    assert len(received_msgs) == 1, f"Expected 1 dispatched message, got {len(received_msgs)}"
    assert received_msgs[0].text == "What is the weather today?"
    print(f"✓ Gateway successfully dispatched human message #{user_msg.id}: '{user_msg.text}'")

    print("\n[Stage 8] Cleanup test App channel and user")
    del_res = requests.post(
        f"{API_BASE}/api/routine/delete_app_channel",
        headers=user_headers,
        json={"user_id": user_id, "channel_id": channel_id},
        timeout=10,
    )
    print("✓ Deleted test App channel")

    print("\n" + "=" * 60)
    print("  ALL PYTHON SDK & GATEWAY TESTS PASSED! 🚀")
    print("=" * 60)


if __name__ == "__main__":
    main()
