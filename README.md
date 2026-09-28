# MyOwnChat Python SDK & AI Agent Messaging Gateway

> **Zero-Configuration Messaging Bridge for AI Agents, Hermes Agent, and Chat Bots**

Connect any AI Agent to [MyOwnChat](https://myownchat.app) using the same 1-key simplicity as Telegram (`@BotFather`) and Slack (`Socket Mode`).

---

## Key Features

- ⚡ **1-Key Setup**: No `channel_id`, `user_id`, or database setup needed. **LittleBackend Gateway Auto-Scoping** automatically binds all reads and writes to the App Channel.
- 📡 **Real-Time SSE Stream**: Instant message delivery via Server-Sent Events with automatic cursor tracking and reconnects.
- 🛡️ **Loop Prevention**: Built-in filtering to ignore bot echoes, webhooks, and system notices.
- 🧵 **Threading & Formatting**: Full support for Markdown, emojis, and `reply_to_id` message threading.
- 🏛️ **Hermes Agent & LLM Ready**: Works out of the box with [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/), OpenAI, Anthropic, Ollama, LangChain, and CrewAI.

---

## Installation

```bash
pip install myownchat
# or for local development:
pip install -e sdk/python
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

## Command Line Usage

Run the gateway directly from your terminal:

```bash
# 1. Set your API key from MyOwnChat App Channel
export MYOWNCHAT_API_KEY="lb_live_..."

# 2. Run the real-time gateway listener (Echo mode)
python -m myownchat.gateway

# 3. Or run with OpenAI integration
export OPENAI_API_KEY="sk-..."
python -m myownchat.gateway --mode openai
```

---

## Hermes Agent Integration

To connect [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/) to MyOwnChat:

```bash
export MYOWNCHAT_API_KEY="lb_live_..."
export HERMES_API_KEY="your_api_key"
python sdk/python/examples/hermes_agent_bridge.py
```

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MYOWNCHAT_API_KEY` | Machine App API Key (`lb_live_...`) | *Required* |
| `MYOWNCHAT_API_BASE` | MyOwnChat API Base URL | `https://api.marcvali.org/myownchat` |
| `MYOWNCHAT_BOT_NAME` | Display name of the bot | `AI Assistant` |
| `OPENAI_API_KEY` | (Optional) OpenAI API Key for GPT responses | `None` |
| `HERMES_API_KEY` | (Optional) Nous / OpenRouter API Key for Hermes | `None` |

---

## License

MIT License. Developed for the MyOwnChat ecosystem.
