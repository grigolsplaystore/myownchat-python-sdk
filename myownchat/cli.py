"""
MyOwnChat Gateway CLI
Run directly: python -m myownchat --key lb_live_...
"""

import argparse
import logging
import os
import sys
import time
from typing import Optional

from .client import Message
from .gateway import MyOwnChatGateway

logger = logging.getLogger("myownchat.cli")


def build_persona_prompt(
    bot_name: Optional[str] = None,
    model: str = "gpt-4o-mini",
    channel_name: Optional[str] = None,
    custom_prompt: Optional[str] = None,
) -> str:
    name = bot_name or "AI Assistant"
    default_prompt = "You are a helpful, friendly AI assistant chatting inside MyOwnChat."
    ch_label = f"#{channel_name}" if channel_name else "your private App channel"
    if not custom_prompt or custom_prompt == default_prompt:
        return (
            f"You are {name}, an AI assistant powered by the {model} model. "
            f"You are chatting with the user in their private {ch_label} on MyOwnChat. "
            "Provide helpful, accurate, and engaging responses formatted with Markdown."
        )
    return (
        custom_prompt.replace("{bot_name}", name)
        .replace("{model}", model)
        .replace("{channel}", channel_name or "app")
    )


def main():
    parser = argparse.ArgumentParser(
        description="MyOwnChat AI Agent Gateway — Universal OpenAI-Compatible messaging bridge"
    )
    parser.add_argument(
        "--key",
        "-k",
        help="MyOwnChat App API Key (lb_live_...). Defaults to MYOWNCHAT_API_KEY env var.",
        default=os.getenv("MYOWNCHAT_API_KEY"),
    )
    parser.add_argument(
        "--url",
        "-u",
        help="MyOwnChat API Base URL. Defaults to MYOWNCHAT_API_BASE or https://api.marcvali.org/myownchat",
        default=os.getenv("MYOWNCHAT_API_BASE", "https://api.marcvali.org/myownchat"),
    )
    parser.add_argument(
        "--name",
        "-n",
        help="Bot display name. Defaults to MYOWNCHAT_BOT_NAME or 'AI Assistant'",
        default=os.getenv("MYOWNCHAT_BOT_NAME", "AI Assistant"),
    )
    parser.add_argument(
        "--send",
        "-s",
        help="Send a single message to the channel and exit immediately",
        default=None,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["echo", "hermes", "openai"],
        default="echo",
        help="Agent mode: 'echo' (default mirror test), 'hermes' (Hermes bridge), or 'openai' (Universal OpenAI-compatible)",
    )

    # OpenAI / OpenAI-Compatible (LM Studio, Ollama, llama.cpp, vLLM, OpenRouter, etc.) arguments
    parser.add_argument(
        "--openai-base-url",
        help="OpenAI-compatible Base URL (e.g. http://localhost:1234/v1 for LM Studio, http://localhost:11434/v1 for Ollama, http://localhost:8080/v1 for llama.cpp). Defaults to OPENAI_BASE_URL or https://api.openai.com/v1",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API Key (or dummy for local LLMs). Defaults to OPENAI_API_KEY or 'not-needed'",
        default=os.getenv("OPENAI_API_KEY", "not-needed"),
    )
    parser.add_argument(
        "--openai-model",
        help="Model identifier. Defaults to OPENAI_MODEL or 'gpt-4o-mini'",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    parser.add_argument(
        "--openai-system-prompt",
        help="System instruction prompt for the assistant.",
        default=os.getenv(
            "OPENAI_SYSTEM_PROMPT",
            "You are a helpful, friendly AI assistant chatting inside MyOwnChat.",
        ),
    )
    parser.add_argument(
        "--openai-max-history",
        type=int,
        help="Maximum number of conversation turns to retain in context. Defaults to OPENAI_MAX_HISTORY or 10.",
        default=int(os.getenv("OPENAI_MAX_HISTORY", "10")),
    )
    parser.add_argument(
        "--openai-temperature",
        type=float,
        help="Sampling temperature (0.0 to 2.0). Defaults to OPENAI_TEMPERATURE or 0.7.",
        default=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
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
        print(
            "Provide it via --key or set the MYOWNCHAT_API_KEY environment variable.",
            file=sys.stderr,
        )
        print("\nExample:", file=sys.stderr)
        print('  export MYOWNCHAT_API_KEY="lb_live_..."', file=sys.stderr)
        print("  python -m myownchat\n", file=sys.stderr)
        sys.exit(1)

    if args.send:
        from .client import MyOwnChatClient

        client = MyOwnChatClient(
            api_key=args.key,
            api_base=args.url,
            bot_name=args.name,
        )
        try:
            msg = client.post_message(args.send)
            ch = client.get_channel()
            target = f"#{ch.name}" if ch else f"channel #{msg.channel_id}"
            print(f"✅ Message #{msg.id} posted to {target}: {msg.text}")
        except Exception as err:
            print(f"❌ Failed to post message: {err}", file=sys.stderr)
            sys.exit(1)
        return

    gateway = MyOwnChatGateway(
        api_key=args.key,
        api_base=args.url,
        bot_name=args.name,
    )

    # Configure message handler based on mode
    if args.mode == "echo":

        @gateway.on_message
        def handle_echo(msg: Message, gw: MyOwnChatGateway):
            print(f'  💬 User said: "{msg.text}"')
            reply = f'🤖 **{gw.bot_name}**: Received your message: *"{msg.text}"*'
            print(f'  ⚡ Replying: "{reply}"')
            return reply

    elif args.mode == "openai":
        try:
            import openai
        except ImportError:
            print("⚠️ openai package not installed. Run: pip install openai", file=sys.stderr)
            sys.exit(1)

        openai_client = openai.OpenAI(
            base_url=args.openai_base_url.rstrip("/"),
            api_key=args.openai_api_key,
        )

        # Fetch channel metadata for dynamic persona context
        channel_info = gateway.client.get_channel()
        system_prompt = build_persona_prompt(
            bot_name=gateway.bot_name,
            model=args.openai_model,
            channel_name=channel_info.name if channel_info else None,
            custom_prompt=args.openai_system_prompt,
        )
        conversation_history: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Reconstruct initial conversation context from MyOwnChat channel messages
        try:
            recent_messages = gateway.client.get_messages(limit=args.openai_max_history, sort="id")
            for m in recent_messages:
                if m.is_from_app or m.metadata.get("is_app"):
                    if m.text and m.text.strip():
                        conversation_history.append(
                            {"role": "assistant", "content": m.text.strip()}
                        )
                elif not m.is_from_webhook and m.type != "system" and m.text and m.text.strip():
                    conversation_history.append({"role": "user", "content": m.text.strip()})
            if len(conversation_history) > 1:
                logger.info(
                    "Reconstructed %d history messages from App Channel context.",
                    len(conversation_history) - 1,
                )
        except Exception as err:
            logger.warning("Could not reconstruct initial channel history: %s", err)

        print("-" * 60)
        print("  🧠 Universal OpenAI-Compatible Bridge Active")
        print(f"  Base URL:    {args.openai_base_url}")
        print(f"  Model:       {args.openai_model}")
        print(f"  Max History: {args.openai_max_history} turns")
        print("-" * 60)

        @gateway.on_message
        def handle_openai(msg: Message, gw: MyOwnChatGateway):
            print(f"\n💬 [Incoming message #{msg.id}]: {msg.text}")
            conversation_history.append({"role": "user", "content": msg.text})

            # Send initial thinking indicator to user
            status_msg = gw.send("💭 *Thinking...*", reply_to=msg)

            try:
                # Truncate context to system prompt + last N turns
                context = [conversation_history[0]] + conversation_history[
                    -(args.openai_max_history) :
                ]

                stream = openai_client.chat.completions.create(
                    model=args.openai_model,
                    messages=context,
                    temperature=args.openai_temperature,
                    stream=True,
                )

                full_text = ""
                last_update = time.time()
                last_snippet = ""

                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else ""
                    if delta:
                        full_text += delta
                        now = time.time()
                        # Every 5 seconds, post a small 1-line snippet of progress
                        if now - last_update >= 5.0 and full_text.strip():
                            lines = [
                                line.strip()
                                for line in full_text.strip().split("\n")
                                if line.strip()
                            ]
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
                conversation_history.append({"role": "assistant", "content": final_reply})
                print(f"⚡ [LLM Response]: {final_reply[:80]}...")

            except Exception as err:
                err_msg = f"⚠️ LLM Error ({type(err).__name__}): {err}"
                logger.error(err_msg, exc_info=True)
                try:
                    gw.edit(status_msg, err_msg)
                except Exception:
                    gw.send(err_msg, reply_to=msg)

    try:
        gateway.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
