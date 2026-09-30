#!/usr/bin/env python3
"""
Universal OpenAI-Compatible Agent Bridge for MyOwnChat
======================================================
Connects any OpenAI-compatible LLM endpoint to MyOwnChat in real-time.
Works with:
  - Local LLMs: LM Studio (http://localhost:1234/v1), Ollama (http://localhost:11434/v1), llama.cpp (http://localhost:8080/v1), vLLM (http://localhost:8000/v1)
  - Cloud Providers: OpenAI, OpenRouter, Groq, Together AI, Mistral, DeepSeek

Setup:
    1. Set your MyOwnChat App API key:
       export MYOWNCHAT_API_KEY="lb_live_..."

    2. (Optional) Set your model and base URL (defaults to standard OpenAI):
       # For LM Studio:
       export OPENAI_BASE_URL="http://localhost:1234/v1"
       export OPENAI_MODEL="local-model"

       # For Ollama:
       export OPENAI_BASE_URL="http://localhost:11434/v1"
       export OPENAI_MODEL="llama3.2"

       # For OpenAI:
       export OPENAI_API_KEY="sk-..."
       export OPENAI_MODEL="gpt-4o-mini"

    3. Run:
       python examples/openai_agent_bridge.py
"""

import os
import sys
import time
from typing import Any, cast

try:
    import openai
except ImportError:
    print("❌ Error: openai package is required. Run: pip install openai", file=sys.stderr)
    sys.exit(1)

from myownchat import Message, MyOwnChatGateway
from myownchat.cli import build_chat_context, build_persona_prompt

# Configuration
MYOWNCHAT_KEY = os.getenv("MYOWNCHAT_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = os.getenv(
    "OPENAI_SYSTEM_PROMPT",
    "You are a helpful, friendly AI assistant chatting inside MyOwnChat.",
)
MAX_HISTORY = int(os.getenv("OPENAI_MAX_HISTORY", "10"))

if not MYOWNCHAT_KEY:
    print("❌ Error: MYOWNCHAT_API_KEY is required.", file=sys.stderr)
    print(
        'Usage: export MYOWNCHAT_API_KEY="lb_live_..." && python examples/openai_agent_bridge.py',
        file=sys.stderr,
    )
    sys.exit(1)

# Initialize OpenAI Client and Gateway
ai_client = openai.OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_KEY)
gateway = MyOwnChatGateway(
    api_key=MYOWNCHAT_KEY,
    bot_name=os.getenv("MYOWNCHAT_BOT_NAME", "AI Assistant"),
)

channel_info = gateway.client.get_channel()
effective_system_prompt = build_persona_prompt(
    bot_name=gateway.bot_name,
    model=OPENAI_MODEL,
    channel_name=channel_info.name if channel_info else None,
    custom_prompt=SYSTEM_PROMPT,
)
dialogue_history: list[dict[str, str]] = []

# Reconstruct initial conversation context from MyOwnChat channel messages
try:
    recent_messages = gateway.client.get_messages(limit=MAX_HISTORY, sort="id")
    for m in recent_messages:
        if m.is_from_app or m.metadata.get("is_app"):
            if m.text and m.text.strip():
                dialogue_history.append({"role": "assistant", "content": m.text.strip()})
        elif not m.is_from_webhook and m.type != "system" and m.text and m.text.strip():
            dialogue_history.append({"role": "user", "content": m.text.strip()})
    if dialogue_history:
        print(f"✓ Reconstructed {len(dialogue_history)} messages from App Channel context.")
except Exception as err:
    print(f"⚠️ Could not reconstruct channel history: {err}")


@gateway.on_message
def on_user_message(msg: Message, gw: MyOwnChatGateway):
    text = (msg.text or "").strip()
    if not text:
        return

    print(f"\n💬 [Incoming User Message #{msg.id}]: {text}")
    dialogue_history.append({"role": "user", "content": text})

    # Post initial thinking indicator
    status_msg = gw.send("💭 *Thinking...*", reply_to=msg)

    try:
        context = build_chat_context(
            system_prompt=effective_system_prompt,
            dialogue_history=dialogue_history,
            max_turns=MAX_HISTORY,
        )

        stream = ai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=cast(Any, context),
            temperature=0.7,
            stream=True,
        )

        full_text = ""
        last_update = time.time()
        last_snippet = ""

        for chunk in stream:
            choices = getattr(chunk, "choices", None)
            delta = choices[0].delta.content if choices and len(choices) > 0 else ""
            if delta:
                full_text += delta
                now = time.time()
                # Update every 5 seconds with a brief line snippet
                if now - last_update >= 5.0 and full_text.strip():
                    lines = [line.strip() for line in full_text.strip().split("\n") if line.strip()]
                    current_line = lines[-1] if lines else full_text.strip()
                    snippet = current_line[-60:].strip()
                    if snippet and snippet != last_snippet:
                        try:
                            gw.edit(status_msg, f"💭 *Generating:* {snippet}...")
                        except Exception:
                            pass
                        last_snippet = snippet
                        last_update = now

        final_reply = full_text.strip() or "*(No response generated)*"
        try:
            gw.edit(status_msg, final_reply)
        except Exception:
            gw.send(final_reply, reply_to=msg)
        dialogue_history.append({"role": "assistant", "content": final_reply})
        print(f"⚡ [AI Response]: {final_reply[:80]}...")

    except Exception as err:
        err_msg = f"⚠️ LLM Error ({type(err).__name__}): {err}"
        print(err_msg, file=sys.stderr)
        try:
            gw.edit(status_msg, err_msg)
        except Exception:
            gw.send(err_msg, reply_to=msg)


if __name__ == "__main__":
    print("=" * 60)
    print("  🚀 Starting Universal OpenAI-Compatible Bridge for MyOwnChat")
    print(f"  Base URL:  {OPENAI_BASE_URL}")
    print(f"  Model:     {OPENAI_MODEL}")
    print(f"  Endpoint:  {gateway.client.api_base}")
    print("=" * 60)
    gateway.start()
