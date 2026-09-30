#!/usr/bin/env python3
"""
Hermes Agent Gateway Bridge for MyOwnChat
==========================================
Connects Nous Research Hermes Agent (or any Hermes 2/3 model) to MyOwnChat
using the same zero-configuration pattern as Telegram (@BotFather) and Slack.

Setup:
    1. In MyOwnChat, create an App Channel (under Apps ➕).
    2. Copy the App API Key (lb_live_...).
    3. Run:
        export MYOWNCHAT_API_KEY="lb_live_..."
        export HERMES_API_KEY="your_nous_or_openrouter_key"
        python hermes_agent_bridge.py

How it works:
    - LittleBackend Gateway Auto-Scoping automatically binds all messages to the App channel.
    - Real-time SSE stream receives user messages instantly (like Slack Socket Mode).
    - Hermes Agent processes the query with persistent memory and tools, and replies.
"""

import os
import sys

from myownchat import Message, MyOwnChatGateway

# Configuration
MYOWNCHAT_KEY = os.getenv("MYOWNCHAT_API_KEY")
HERMES_API_BASE = os.getenv("HERMES_API_BASE", "https://api.nousresearch.com/v1")
HERMES_API_KEY = (
    os.getenv("HERMES_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
)
HERMES_MODEL = os.getenv("HERMES_MODEL", "NousResearch/Hermes-3-Llama-3.1-8B")

if not MYOWNCHAT_KEY:
    print("❌ Error: MYOWNCHAT_API_KEY is required.")
    print('Usage: export MYOWNCHAT_API_KEY="lb_live_..." && python hermes_agent_bridge.py')
    sys.exit(1)

# Initialize MyOwnChat Gateway
gateway = MyOwnChatGateway(
    api_key=MYOWNCHAT_KEY,
    bot_name="Hermes Agent",
)

# Conversation history cache for multi-turn context
conversation_history: list[dict[str, str]] = [
    {
        "role": "system",
        "content": (
            "You are Hermes Agent, an autonomous open-source AI assistant by Nous Research. "
            "You are communicating with the user directly inside MyOwnChat. "
            "Provide helpful, accurate, markdown-formatted responses."
        ),
    }
]


@gateway.on_message
def on_user_message(msg: Message, gw: MyOwnChatGateway):
    """Callback triggered whenever a user types in the MyOwnChat App channel."""
    print(f"\n[Hermes Gateway] Received message #{msg.id}: {msg.text}")

    # Append user turn
    conversation_history.append({"role": "user", "content": msg.text})

    # If an LLM key is configured, call Hermes completion API
    if HERMES_API_KEY:
        try:
            import requests

            resp = requests.post(
                f"{HERMES_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {HERMES_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": HERMES_MODEL,
                    "messages": conversation_history[-10:],  # Context window
                    "temperature": 0.7,
                },
                timeout=30,
            )

            if resp.ok:
                data = resp.json()
                bot_reply = data["choices"][0]["message"]["content"]
            else:
                bot_reply = f"⚠️ Hermes API error ({resp.status_code}): {resp.text}"
        except Exception as e:
            bot_reply = f"⚠️ Hermes bridge execution error: {e}"
    else:
        # Standalone demonstration response if no external LLM key is set
        bot_reply = (
            f"🏛️ **[Hermes Agent]** Hello! I received your message:\n\n"
            f"> *{msg.text}*\n\n"
            f"✅ **Gateway Connected**: Real-time SSE stream operational.\n"
            f"💡 *Tip: Set `HERMES_API_KEY` or `OPENAI_API_KEY` to enable live LLM reasoning.*"
        )

    # Append assistant turn
    conversation_history.append({"role": "assistant", "content": bot_reply})
    print(f"[Hermes Gateway] Replying: {bot_reply[:80]}...")
    return bot_reply


if __name__ == "__main__":
    print("=" * 60)
    print("  🚀 Starting Nous Research Hermes Agent Gateway for MyOwnChat")
    print(f"  Model:     {HERMES_MODEL}")
    print(f"  Endpoint:  {gateway.client.api_base}")
    print("=" * 60)
    gateway.start()
