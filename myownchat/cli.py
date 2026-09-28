"""
MyOwnChat Gateway CLI
Run directly: python -m myownchat.gateway --key lb_live_...
"""

import argparse
import logging
import os
import sys

from .client import Message
from .gateway import MyOwnChatGateway


def main():
    parser = argparse.ArgumentParser(
        description="MyOwnChat AI Agent Gateway — Hermes-style messaging bridge"
    )
    parser.add_argument(
        "--key", "-k",
        help="MyOwnChat App API Key (lb_live_...). Defaults to MYOWNCHAT_API_KEY env var.",
        default=os.getenv("MYOWNCHAT_API_KEY"),
    )
    parser.add_argument(
        "--url", "-u",
        help="MyOwnChat API Base URL. Defaults to MYOWNCHAT_API_BASE or https://api.marcvali.org/myownchat",
        default=os.getenv("MYOWNCHAT_API_BASE", "https://api.marcvali.org/myownchat"),
    )
    parser.add_argument(
        "--name", "-n",
        help="Bot display name. Defaults to MYOWNCHAT_BOT_NAME or 'AI Assistant'",
        default=os.getenv("MYOWNCHAT_BOT_NAME", "AI Assistant"),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["echo", "hermes", "openai"],
        default="echo",
        help="Agent mode: 'echo' (default mirror test), 'hermes' (Hermes bridge), or 'openai'",
    )

    args = parser.parse_args()

    # Logging setup
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.key:
        print("❌ Error: MyOwnChat App API Key is missing!", file=sys.stderr)
        print("Provide it via --key or set the MYOWNCHAT_API_KEY environment variable.", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  export MYOWNCHAT_API_KEY=\"lb_live_...\"", file=sys.stderr)
        print("  python -m myownchat.gateway\n", file=sys.stderr)
        sys.exit(1)

    gateway = MyOwnChatGateway(
        api_key=args.key,
        api_base=args.url,
        bot_name=args.name,
    )

    # Configure message handler based on mode
    if args.mode == "echo":
        @gateway.on_message
        def handle_echo(msg: Message, gw: MyOwnChatGateway):
            print(f"  💬 User said: \"{msg.text}\"")
            reply = f"🤖 **{gw.bot_name}**: Received your message: *\"{msg.text}\"*"
            print(f"  ⚡ Replying: \"{reply}\"")
            return reply

    elif args.mode == "openai":
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️ Warning: OPENAI_API_KEY not found in environment. Falling back to Echo mode.")
            @gateway.on_message
            def handle_fallback(msg: Message):
                return f"🤖 Echo: {msg.text} (Set OPENAI_API_KEY to enable GPT responses)"
        else:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key)

                @gateway.on_message
                def handle_openai(msg: Message):
                    print(f"  🧠 Asking OpenAI for prompt: \"{msg.text}\"...")
                    resp = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant in MyOwnChat."},
                            {"role": "user", "content": msg.text},
                        ],
                    )
                    ai_text = resp.choices[0].message.content or "No response"
                    return ai_text
            except ImportError:
                print("⚠️ openai package not installed. Run: pip install openai")
                sys.exit(1)

    try:
        gateway.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
