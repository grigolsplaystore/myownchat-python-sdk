"""
MyOwnChat Messaging Gateway Adapter
Hermes-style messaging bridge for Telegram/Slack-like AI Agent integrations.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import signal
import sys
import time
from typing import Any, Callable, Optional, Union

from .client import ChannelInfo, Message, MyOwnChatClient

logger = logging.getLogger("myownchat.gateway")


class MyOwnChatGateway:
    """
    High-level real-time messaging gateway connecting AI Agents to MyOwnChat.
    Uses SSE Real-Time Stream with Cursor Polling Fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        bot_name: Optional[str] = None,
        on_message: Optional[Callable[[Message, MyOwnChatGateway], Union[str, None]]] = None,
        ignore_self: bool = True,
        ignore_webhooks: bool = True,
        ignore_system: bool = True,
    ) -> None:
        self.client = MyOwnChatClient(
            api_key=api_key,
            api_base=api_base,
            bot_name=bot_name,
        )
        self.bot_name = self.client.bot_name
        self.on_message_handler = on_message
        self.ignore_self = ignore_self
        self.ignore_webhooks = ignore_webhooks
        self.ignore_system = ignore_system

        self.last_message_id: int = 0
        self.channel_info: Optional[ChannelInfo] = None
        self._running: bool = False

    def on_message(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for registering an incoming message handler."""
        self.on_message_handler = func
        return func

    def send(
        self,
        text: str,
        reply_to: Optional[Union[int, Message]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """
        Sends a reply message to the App channel.
        Supports Markdown, threads (reply_to), and custom metadata.
        """
        reply_to_id: Optional[int] = None
        if isinstance(reply_to, Message):
            reply_to_id = reply_to.id
        elif isinstance(reply_to, int):
            reply_to_id = reply_to

        return self.client.post_message(
            text=text,
            reply_to_id=reply_to_id,
            metadata=metadata,
            bot_name=self.bot_name,
        )

    def _init_cursor(self) -> None:
        """Initializes the latest message cursor and channel metadata."""
        try:
            self.channel_info = self.client.get_channel()
            if self.channel_info:
                logger.info(
                    "Connected to MyOwnChat App Channel: #%s (ID: %d)",
                    self.channel_info.name,
                    self.channel_info.id,
                )
        except Exception as err:
            logger.warning("Could not fetch channel metadata: %s", err)

        try:
            recent = self.client.get_messages(limit=1, sort="-id")
            if recent:
                self.last_message_id = recent[0].id
            logger.info("Gateway initialized. Tracking messages after ID #%d", self.last_message_id)
        except Exception as err:
            logger.warning("Failed to initialize cursor with recent messages: %s", err)

    def _dispatch_message(self, msg: Message) -> None:
        """Filters message loops and dispatches to handler."""
        if msg.id <= 0:
            return

        # Advance cursor
        if msg.id > self.last_message_id:
            self.last_message_id = msg.id

        # Filtering
        if self.ignore_self and msg.is_from_app:
            return
        if self.ignore_webhooks and msg.is_from_webhook:
            return
        if self.ignore_system and msg.type == "system":
            return
        if not msg.text or not msg.text.strip():
            return

        logger.info("[Incoming message #%d from user %d]: %s", msg.id, msg.sender_user_id, msg.text)

        if not self.on_message_handler:
            return

        try:
            # Handle both async and sync callbacks
            sig = inspect.signature(self.on_message_handler)
            param_count = len(sig.parameters)

            result: Any = None
            if inspect.iscoroutinefunction(self.on_message_handler):
                loop = asyncio.get_event_loop()
                if param_count == 1:
                    result = loop.run_until_complete(self.on_message_handler(msg))
                else:
                    result = loop.run_until_complete(self.on_message_handler(msg, self))
            else:
                if param_count == 1:
                    result = self.on_message_handler(msg)
                else:
                    result = self.on_message_handler(msg, self)

            # If the handler returned a non-empty string, automatically post it as a reply
            if isinstance(result, str) and result.strip():
                self.send(result.strip(), reply_to=msg)

        except Exception as err:
            logger.error("Error executing on_message handler: %s", err, exc_info=True)

    def _poll_catchup(self) -> None:
        """Polls for any messages missed during reconnect."""
        try:
            missed = self.client.get_messages(limit=50, after_id=self.last_message_id, sort="id")
            for msg in missed:
                self._dispatch_message(msg)
        except Exception as err:
            logger.warning("Catchup poll failed: %s", err)

    def start(self) -> None:
        """
        Starts the real-time gateway listener (blocking).
        Uses SSE streaming with automatic cursor catchup and reconnection.
        """
        self._running = True
        self._init_cursor()

        print("=" * 60)
        print(f"  🤖 MyOwnChat AI Gateway is Running: {self.bot_name}")
        print(f"  Channel:  #{self.channel_info.name if self.channel_info else 'app'}")
        print(f"  Endpoint: {self.client.api_base}")
        print("=" * 60)
        print(f"[{time.strftime('%X')}] Listening for incoming user messages (Press Ctrl+C to stop)...")

        backoff = 1.0
        while self._running:
            try:
                # Catch up on any messages missed before connecting
                self._poll_catchup()

                logger.debug("Connecting SSE stream to %s/api/events", self.client.api_base)
                for event in self.client.stream_sse():
                    if not self._running:
                        break

                    backoff = 1.0  # Reset backoff upon active stream traffic
                    event_type = event.get("event", "")
                    data = event.get("data")
                    if not isinstance(data, dict):
                        continue

                    if event_type == "LB_CONNECT":
                        logger.debug("SSE Handshake connected. Client ID: %s", data.get("clientId") or data.get("client_id"))
                        continue

                    # Check for table insert / mutation events
                    table = data.get("table")
                    action = data.get("action") or data.get("operation")
                    record = data.get("record") or data.get("data") or data

                    is_msg_event = (
                        event_type.startswith("messages/")
                        or table == "messages"
                        or (isinstance(record, dict) and ("channel_id" in record or "text" in record or "sender_app_id" in record))
                    )

                    if is_msg_event and isinstance(record, dict):
                        # Only handle creation/inserts, ignore deletes
                        if action not in ("delete", "destroy") and not event_type.endswith("/delete"):
                            msg = Message.from_dict(record)
                            if msg.id > self.last_message_id:
                                self._dispatch_message(msg)

            except KeyboardInterrupt:
                print(f"\n[{time.strftime('%X')}] Gateway stopped by user.")
                break
            except Exception as err:
                if not self._running:
                    break
                logger.warning("SSE connection dropped (%s). Reconnecting in %.1fs...", err, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2.0, 15.0)

    def stop(self) -> None:
        """Stops the gateway loop."""
        self._running = False
