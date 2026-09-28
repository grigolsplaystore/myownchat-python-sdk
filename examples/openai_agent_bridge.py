#!/usr/bin/env python3
"""
OpenAI Agent Bridge for MyOwnChat
Uses OpenAI GPT model to chat with users in MyOwnChat in real-time.
"""

import os
import sys
import openai
from myownchat import MyOwnChatGateway, Message

myownchat_key = os.getenv("MYOWNCHAT_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if not myownchat_key:
    print("❌ Error: MYOWNCHAT_API_KEY is required.")
    sys.exit(1)

if not openai_key:
    print("❌ Error: OPENAI_API_KEY is required.")
    sys.exit(1)

ai_client = openai.OpenAI(api_key=openai_key)
gateway = MyOwnChatGateway(
    api_key=myownchat_key,
    bot_name="GPT Assistant",
)

conversation_history = [
    {"role": "system", "content": "You are a helpful, friendly AI assistant chatting inside MyOwnChat."}
]

@gateway.on_message
def on_user_message(msg: Message):
    print(f"\n[User message #{msg.id}]: {msg.text}")
    conversation_history.append({"role": "user", "content": msg.text})

    try:
        completion = ai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=conversation_history[-10:],
            temperature=0.7,
        )
        reply = completion.choices[0].message.content or "No response"
    except Exception as e:
        reply = f"⚠️ OpenAI Error: {e}"

    conversation_history.append({"role": "assistant", "content": reply})
    print(f"[GPT Response]: {reply[:80]}...")
    return reply

if __name__ == "__main__":
    gateway.start()
