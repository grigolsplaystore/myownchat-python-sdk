"""
MyOwnChat REST & Real-Time HTTP Client
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

DEFAULT_API_BASE = "https://api.marcvali.org/myownchat"


@dataclass
class Message:
    """Represents a chat message in MyOwnChat."""

    id: int
    channel_id: int
    sender_user_id: Optional[int] = None
    sender_app_id: Optional[int] = None
    text: str = ""
    type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)
    is_pinned: bool = False
    created_at: Optional[str] = None
    edited_at: Optional[str] = None
    deleted_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        meta = data.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        uid, aid = data.get("sender_user_id"), data.get("sender_app_id")
        return cls(
            id=int(data.get("id", 0)),
            channel_id=int(data.get("channel_id", 0)),
            sender_user_id=int(uid) if uid is not None else None,
            sender_app_id=int(aid) if aid is not None else None,
            text=str(data.get("text") or data.get("content") or ""),
            type=str(data.get("type", "text")),
            metadata=meta if isinstance(meta, dict) else {},
            is_pinned=bool(data.get("is_pinned", False)),
            created_at=data.get("created_at"),
            edited_at=data.get("edited_at"),
            deleted_at=data.get("deleted_at"),
        )

    @property
    def is_from_app(self) -> bool:
        """Returns True if the message was posted by an AI bot or App."""
        return bool(
            self.sender_app_id is not None
            or self.metadata.get("is_app")
            or self.metadata.get("bot_name")
        )

    @property
    def is_from_webhook(self) -> bool:
        """Returns True if the message was posted by an Inbound Webhook."""
        return bool(self.metadata.get("is_webhook"))

    @property
    def bot_name(self) -> Optional[str]:
        """Returns the bot name if present in metadata."""
        return self.metadata.get("bot_name")

    @property
    def reply_to_id(self) -> Optional[int]:
        """Returns the ID of the parent message being replied to, if threaded."""
        reply_id = self.metadata.get("reply_to_id")
        return int(reply_id) if reply_id is not None else None


@dataclass
class ChannelInfo:
    """Represents App channel information."""

    id: int
    name: str
    type: str
    is_open: bool = False
    members: int = 1
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelInfo:
        st = data.get("settings") or {}
        if isinstance(st, str):
            try:
                st = json.loads(st)
            except Exception:
                st = {}

        return cls(
            id=int(data.get("id", 0)),
            name=str(data.get("name", "")),
            type=str(data.get("type", "app")),
            is_open=bool(data.get("is_open", False)),
            members=int(data.get("members", 1)),
            settings=st if isinstance(st, dict) else {},
            created_at=data.get("created_at"),
        )


class MyOwnChatClient:
    """
    Low-level LittleBackend client communicating with MyOwnChat API.
    Zero-Knowledge Auto-Scoping: LittleBackend automatically stamps and bounds
    all requests to the authorized App channel.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        bot_name: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or os.getenv("MYOWNCHAT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "MyOwnChat API Key is required. Set MYOWNCHAT_API_KEY environment variable "
                "or pass api_key to MyOwnChatClient."
            )

        self.api_base = (api_base or os.getenv("MYOWNCHAT_API_BASE") or DEFAULT_API_BASE).rstrip(
            "/"
        )

        self.bot_name = bot_name or os.getenv("MYOWNCHAT_BOT_NAME", "AI Assistant")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"MyOwnChat-PythonSDK/0.1.0 ({self.bot_name})",
            }
        )

    def get_channel(self) -> Optional[ChannelInfo]:
        """Fetches the bound App channel metadata."""
        url = f"{self.api_base}/api/table/channels"
        resp = self._session.get(url, timeout=self.timeout)
        if not resp.ok:
            return None

        data = resp.json()
        items = data.get("items", [])
        if items:
            return ChannelInfo.from_dict(items[0])
        elif isinstance(data, dict) and "id" in data:
            return ChannelInfo.from_dict(data)
        return None

    def get_messages(
        self,
        limit: int = 50,
        after_id: Optional[int] = None,
        sort: str = "id",
    ) -> list[Message]:
        """
        Retrieves recent messages from the channel (auto-scoped).
        """
        url = f"{self.api_base}/api/table/messages?limit={limit}&sort={sort}"
        if after_id is not None and after_id > 0:
            url += f"&filter=id > {after_id}"

        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])
        return [Message.from_dict(item) for item in items]

    def post_message(
        self,
        text: str,
        reply_to_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        bot_name: Optional[str] = None,
    ) -> Message:
        """
        Posts a new message to the App channel.
        Zero-Knowledge: Gateway automatically assigns channel_id.
        """
        if not text or not text.strip():
            raise ValueError("Message text cannot be empty")

        meta: dict[str, Any] = {
            "is_app": True,
            "bot_name": bot_name or self.bot_name,
        }
        if reply_to_id is not None:
            meta["reply_to_id"] = reply_to_id
        if metadata:
            meta.update(metadata)

        payload: dict[str, Any] = {
            "type": "text",
            "text": text.strip(),
            "metadata": meta,
        }

        url = f"{self.api_base}/api/table/messages"
        resp = self._session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        res_data = resp.json()
        return Message.from_dict(res_data)

    def edit_message(
        self,
        message_id: int,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """
        Updates/edits an existing message previously posted by this app.
        """
        if not text or not text.strip():
            raise ValueError("Message text cannot be empty")

        payload: dict[str, Any] = {
            "text": text.strip(),
        }
        if metadata is not None:
            payload["metadata"] = metadata

        url = f"{self.api_base}/api/table/messages/{message_id}"
        resp = self._session.patch(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()

        res_data = resp.json()
        return Message.from_dict(res_data)

    def delete_message(self, message_id: int) -> bool:
        """Deletes a message previously posted by this app."""
        url = f"{self.api_base}/api/table/messages/{message_id}"
        resp = self._session.delete(url, timeout=self.timeout)
        return resp.status_code in (200, 204)

    def stream_sse(
        self,
        subscriptions: Optional[list[str]] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Opens a persistent SSE connection to LittleBackend's /api/events endpoint.
        Yields decoded event objects as they arrive in real-time.
        """
        subs = subscriptions or ["messages"]
        url = f"{self.api_base}/api/events"
        params = {"subscriptions": ",".join(subs)}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }

        with self._session.get(
            url, params=params, headers=headers, stream=True, timeout=(10, None)
        ) as r:
            r.raise_for_status()
            event_name = "message"
            data_buffer: list[str] = []

            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue

                line_str: str = (
                    raw_line.decode("utf-8") if isinstance(raw_line, bytes) else str(raw_line)
                ).strip()

                if not line_str:
                    # Empty line triggers event dispatch
                    if data_buffer:
                        raw_data = "\n".join(data_buffer)
                        data_buffer = []
                        try:
                            parsed_json = json.loads(raw_data)
                        except Exception:
                            parsed_json = {"raw": raw_data}

                        yield {
                            "event": event_name,
                            "data": parsed_json,
                        }
                    event_name = "message"
                    continue

                if line_str.startswith(":"):
                    continue

                field, _, val = line_str.partition(":")
                val = val.strip()
                if field == "event":
                    event_name = val
                elif field == "data":
                    data_buffer.append(val)
