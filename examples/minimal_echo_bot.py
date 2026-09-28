#!/usr/bin/env python3
"""
Minimal Echo Bot for MyOwnChat
"""

import os
import sys
from myownchat import MyOwnChatGateway, Message

api_key = os.getenv("MYOWNCHAT_API_KEY")
if not api_key:
    print("❌ Error: MYOWNCHAT_API_KEY is required.")
    print("Usage: export MYOWNCHAT_API_KEY=\"lb_live_...\" && python minimal_echo_bot.py")
    sys.exit(1)

gateway = MyOwnChatGateway(
    api_key=api_key,
    bot_name="Echo Assistant",
)

@gateway.on_message
def on_message(msg: Message):
    print(f"Received user message #{msg.id}: {msg.text}")
    return f"🤖 **Echo**: {msg.text}"

if __name__ == "__main__":
    gateway.start()
