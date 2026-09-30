# MyOwnChat Python SDK & AI Agent Messaging Gateway

> **Zero-Configuration Messaging Bridge for AI Agents, Hermes Agent, and Chat Bots**

Connect any AI Agent to [MyOwnChat](https://myownchat.app) using the same 1-key simplicity as Telegram (`@BotFather`) and Slack (`Socket Mode`).

---

## Key Features

- ⚡ **1-Key Setup**: No `channel_id`, `user_id`, or database setup needed. **LittleBackend Gateway Auto-Scoping** automatically binds all reads and writes to the App Channel.
- 📡 **Real-Time SSE Stream**: Instant message delivery via Server-Sent Events with automatic cursor tracking and reconnects.
- 🧠 **Universal OpenAI-Compatible Bridge**: Connect to any OpenAI-compatible LLM endpoint — including local LLMs (**LM Studio**, **Ollama**, **llama.cpp**, **vLLM**) and cloud providers (**OpenAI**, **OpenRouter**, **Groq**, **Together AI**, **DeepSeek**).
- 💬 **Live Stream Interaction**: Instant thinking indicators and periodic 5-second line progress snippets while generating.
- 🔄 **Channel Context Memory**: Reconstructs multi-turn history from channel messages upon boot, preserving context across gateway restarts.
- 🛡️ **Loop Prevention**: Built-in filtering to ignore bot echoes, webhooks, and system notices.
- 🧵 **Threading & Formatting**: Full support for Markdown, emojis, and `reply_to_id` message threading.
- 🏛️ **Hermes Agent Ready**: Works out of the box with [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/).

---

## Installation

```bash
pip install myownchat
# or for local development:
pip install -e .
```

---

## Quickstart (3 Lines of Code)

```python
from myownchat import MyOwnChatGateway

gateway = MyOwnChatGateway(api_key="lb_live_...")


@gateway.on_message
def handle_message(msg):
    return f"Hello! You said: {msg.text}"


gateway.start()
```

---

## Universal OpenAI-Compatible Bridge

Run the gateway connected directly to your local or cloud LLM:

### 1. LM Studio (Local)
```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_MODEL="local-model"

python -m myownchat --mode openai
```

### 2. Ollama (Local)
```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.2"

python -m myownchat --mode openai
```

### 3. llama.cpp Server (Local)
```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export OPENAI_BASE_URL="http://localhost:8080/v1"

python -m myownchat --mode openai
```

### 4. OpenAI (Cloud)
```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"

python -m myownchat --mode openai
```

---

## Hermes Agent Integration

To connect [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/) to MyOwnChat:

```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export HERMES_API_KEY="your_api_key"
python examples/hermes_agent_bridge.py
```

---

## Direct Message Posting via CLI

Send a one-off notification or message directly to your channel without running a persistent daemon:

```bash
export MYOWNCHAT_API_KEY="lb_live_..."
python -m myownchat --send "Deployment completed successfully! 🚀"
```

Or pass the key inline:

```bash
python -m myownchat -k "lb_live_..." -s "Hello from the CLI"
```

---

## Code Examples

### 1. Async Message Handler

```python
import asyncio
from myownchat import MyOwnChatGateway

gateway = MyOwnChatGateway(api_key="lb_live_...")


@gateway.on_message
async def handle_message(msg, gw):
    await asyncio.sleep(0.5)  # Perform async tasks or API calls
    return f"Processed asynchronously: {msg.text}"


gateway.start()
```

### 2. Low-Level REST Client

```python
from myownchat import MyOwnChatClient

client = MyOwnChatClient(api_key="lb_live_...")

# Fetch channel metadata
channel = client.get_channel()
print(f"Connected to #{channel.name} (ID: {channel.id})")

# Post a message
msg = client.post_message("Hello from the REST client!")

# Fetch recent message history (auto-scoped to your channel)
history = client.get_messages(limit=10)
for m in history:
    print(f"[{m.id}] {m.text}")
```

### 3. Threaded Replies & Progress Editing

```python
import time
from myownchat import MyOwnChatGateway

gateway = MyOwnChatGateway(api_key="lb_live_...")


@gateway.on_message
def handle_task(msg, gw):
    # 1. Send initial status replying to the user
    status = gw.send("⏳ *Starting analysis...*", reply_to=msg)

    # 2. Update progress
    time.sleep(2)
    try:
        gw.edit(status, "📊 *Processing results (50%)...*")
    except Exception:
        pass

    # 3. Final completion
    time.sleep(2)
    try:
        gw.edit(status, "✅ *Analysis complete!* All checks passed.")
    except Exception:
        gw.send("✅ *Analysis complete!*", reply_to=msg)


gateway.start()
```

### 4. Rich Embed Cards & Custom Metadata

```python
from myownchat import MyOwnChatClient

client = MyOwnChatClient(api_key="lb_live_...")

client.post_message(
    text="Deployment Report 📋",
    metadata={
        "embed": {
            "title": "Production Deployment",
            "description": "Release **v2.4.0** deployed successfully.",
            "color": "#10B981",
            "fields": [
                {"name": "Environment", "value": "Production", "inline": True},
                {"name": "Duration", "value": "42s", "inline": True},
            ],
        }
    },
)
```

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MYOWNCHAT_API_KEY` | Machine App API Key (`lb_live_...`) | *Required* |
| `MYOWNCHAT_API_BASE` | MyOwnChat API Base URL | `https://api.marcvali.org/myownchat` |
| `MYOWNCHAT_BOT_NAME` | Display name of the bot | `AI Assistant` |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint URL | `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | API Key (or dummy for local LLMs) | `not-needed` |
| `OPENAI_MODEL` | Model identifier | `gpt-4o-mini` |
| `OPENAI_SYSTEM_PROMPT` | System prompt instruction | Friendly AI prompt |
| `OPENAI_MAX_HISTORY` | Max conversation turns retained | `10` |
| `HERMES_API_KEY` | Nous / OpenRouter API Key for Hermes | `None` |

---

## License

MIT License. Developed for the MyOwnChat ecosystem.
