# MyOwnChat Python SDK & Gateway — Workspace Summary

## Overview
This repository (`myownchat-python-sdk`) is the official, standalone Python SDK and AI Agent Gateway bridge for **MyOwnChat** (`https://myownchat.app`). It connects AI Agents (Nous Hermes Agent, OpenAI, Anthropic, Ollama, LM Studio, llama.cpp, LangChain, CrewAI, custom bots) to MyOwnChat App Channels via **LittleBackend** with 1-key zero-configuration setup (comparable to Telegram `@BotFather` and Slack `Socket Mode`).

---

## Architecture & LittleBackend Gateway Integration

### High-Level Architecture
- **Host Platform**: MyOwnChat (`https://myownchat.app`)
- **Backend as a Service (BaaS)**: LittleBackend
- **Public API Base**: `https://api.marcvali.org/myownchat`
- **Real-Time Stream**: SSE at `https://api.marcvali.org/myownchat/api/events`
- **Machine Authentication**: Bearer API tokens (`Authorization: Bearer lb_live_<64hex>`)

### Zero-Configuration Gateway Auto-Scoping
LittleBackend automatically enforces channel binding and isolation for machine integrations:
1. **Auto-Scoped Message Ingestion (`POST /api/table/messages`)**:
   - The agent sends message text without needing to manage or know `channel_id`.
   - LittleBackend automatically scopes and binds the message to the App channel.
   - Cross-channel tampering is rejected with `403 Forbidden`.
2. **Auto-Scoped History Query (`GET /api/table/messages`)**:
   - History queries automatically return only messages belonging to the authorized App channel.
3. **Real-Time SSE Event Scoping (`GET /api/events?subscriptions=messages`)**:
   - SSE stream automatically routes only events pertinent to the authorized channel.

---

## SDK Data Models & Protocol

### Message Model
The SDK communicates with LittleBackend using the standard `Message` data model:
- `id`: Unique message identifier (int).
- `channel_id`: Bound channel ID (int).
- `sender_user_id`: User ID of human sender (null when sent by bot/app).
- `sender_app_id`: App ID when sent by machine/bot.
- `text`: Markdown-formatted message content.
- `type`: Message type (`'text'`, `'system'`, `'file'`).
- `metadata`: JSON object containing:
  - `is_app`: boolean flag indicating machine app origin.
  - `bot_name`: display name of the bot.
  - `reply_to_id`: parent message ID for threaded conversations.
  - `embed`: rich embed card (title, description, color, fields).

### Channel Model
- `id`: Channel identifier (int).
- `name`: App channel handle.
- `type`: Channel type (`'app'`).
- `settings`: Configuration object (bot display name, avatar, etc.).

---

## Python SDK Components

### 1. `MyOwnChatClient` (`myownchat/client.py`)
- Low-level REST & SSE client for LittleBackend.
- Methods:
  - `get_channel()` -> `ChannelInfo` (fetches bound app channel metadata).
  - `get_messages(limit=50, after_id=None, sort="id")` -> `list[Message]` (fetches history).
  - `post_message(text, reply_to_id=None, metadata=None, bot_name=None)` -> `Message` (posts auto-scoped message).
  - `edit_message(message_id, text, metadata=None)` -> `Message` (updates/edits an existing message).
  - `delete_message(message_id)` -> `bool`.
  - `stream_sse(subscriptions=None)` -> `Generator[dict, None, None]` (SSE event parser).

### 2. `MyOwnChatGateway` (`myownchat/gateway.py`)
- High-level Hermes-style real-time event loop.
- Features:
  - `@gateway.on_message` decorator supporting synchronous and asynchronous callback functions.
  - Automatic return-value reply posting: if the callback returns a string, it automatically posts as a reply.
  - Loop prevention: drops bot self-messages (`is_from_app`), webhook alerts (`is_from_webhook`), and system messages (`type: 'system'`).
  - Cursor tracking & reconnection: tracks `last_message_id`, performs catchup polling upon SSE reconnect, exponential backoff.
  - Method `send(text, reply_to=None, metadata=None)` -> `Message`.
  - Method `edit(message_or_id, text, metadata=None)` -> `Message`.

### 3. CLI (`myownchat/cli.py` & `myownchat/__main__.py`)
- Run directly from the command line: `python -m myownchat` or `myownchat-gateway`.
- Modes & Actions:
  - `--send` (`-s`): Send a one-off message directly to the channel and exit immediately without running daemon.
  - `--mode echo`: Default echo test loop.
  - `--mode openai`: Universal OpenAI-compatible bridge supporting LM Studio, Ollama, llama.cpp, vLLM, OpenRouter, OpenAI. Features channel context reconstruction upon boot and 5-second streaming progress updates.
  - `--mode hermes`: Hermes bridge integration.
- Arguments:
  - `--key` (`-k`): App API key (`lb_live_...`).
  - `--url` (`-u`): LittleBackend API base URL.
  - `--name` (`-n`): Bot display name.
  - `--send` (`-s`): Message text to send directly and exit.
  - `--openai-base-url`: OpenAI-compatible endpoint URL (`http://localhost:1234/v1`, `http://localhost:11434/v1`, etc.).
  - `--openai-api-key`: API key or dummy for local LLMs.
  - `--openai-model`: Model identifier.
  - `--openai-system-prompt`: System prompt.
  - `--openai-max-history`: Max context turns (default 30).
  - `--openai-temperature`: Sampling temperature.

---

## Verification & Code Quality Suite
- **Linter & Formatter**: `.venv/bin/ruff format . && .venv/bin/ruff check .` (0 errors, strict code formatting).
- **Type Checker**: `.venv/bin/mypy myownchat tests examples` (0 errors across all 11 source files).
- **Full Test Suite**: `.venv/bin/pytest` (7/7 tests passing).
- **Gateway Integration Test**: `PYTHONPATH=. python3 tests/test_gateway.py` (Tests auto-scoped client, threaded replies, edit_message interface, gateway loop prevention, user message dispatch).
- **Live Real-Time SSE Stream Test**: `PYTHONPATH=. python3 tests/test_live_sse.py` (Verifies real-time event delivery and automatic callback reply over live SSE stream).

---

## Environment Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `MYOWNCHAT_API_KEY` | Machine App API Key (`lb_live_...`) | *Required* |
| `MYOWNCHAT_API_BASE` | LittleBackend API Base URL | `https://api.marcvali.org/myownchat` |
| `MYOWNCHAT_BOT_NAME` | Display name of the bot | `AI Assistant` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint URL | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | API Key (or dummy for local LLMs) | `not-needed` |
| `OPENAI_MODEL` | Model identifier | `gpt-4o-mini` |
| `OPENAI_SYSTEM_PROMPT` | System prompt instruction | Default friendly prompt |
| `OPENAI_MAX_HISTORY` | Max conversation turns retained | `30` |
| `HERMES_API_KEY` | Nous / OpenRouter API Key for Hermes Agent | `None` |
