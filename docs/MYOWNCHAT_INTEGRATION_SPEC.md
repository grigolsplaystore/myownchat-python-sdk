# LittleBackend AI Gateway Specification

## 1. Overview
The LittleBackend AI Gateway provides a zero-configuration communication bridge between autonomous AI Agents, chatbots, scripts, and **MyOwnChat** (`https://myownchat.app`).

Similar to Slack's *Socket Mode* and Telegram's *@BotFather*, an agent developer only needs a single Machine App API key (`lb_live_...`) to immediately receive real-time user prompts and stream back markdown responses.

---

## 2. Authentication & Auto-Scoping Protocol

### 2.1 Machine API Key
Machine integrations authenticate via standard HTTP Bearer tokens:
```http
Authorization: Bearer lb_live_<64hex>
```

### 2.2 Parameterized Auto-Scoping
LittleBackend automatically binds each Machine App API Key to its dedicated App Channel:
- **Write Auto-Scoping**: When an agent sends a POST request to `/api/table/messages`, LittleBackend automatically assigns and verifies the bound `channel_id`. If a caller attempts to send a message to a different channel, LittleBackend rejects the request with `403 Forbidden`.
- **Read Auto-Scoping**: Querying `/api/table/messages` automatically scopes the query to return only records within the authorized channel.
- **Event Scoping**: Opening a Server-Sent Events (SSE) stream at `/api/events` automatically streams only the events occurring within the authorized channel.

---

## 3. Gateway REST & Real-Time Endpoints

### 3.1 Fetch Bound Channel Info
```http
GET /api/table/channels
Authorization: Bearer lb_live_...
```
Returns channel metadata for the machine app (handle, display settings, creation timestamp).

### 3.2 Post Message (Auto-Scoped)
```http
POST /api/table/messages
Authorization: Bearer lb_live_...
Content-Type: application/json

{
  "type": "text",
  "text": "Hello! I am your AI assistant.",
  "metadata": {
    "is_app": true,
    "bot_name": "AI Assistant",
    "reply_to_id": 1234
  }
}
```

### 3.3 Query Message History (Auto-Scoped)
```http
GET /api/table/messages?limit=50&sort=id&filter=id > 1000
Authorization: Bearer lb_live_...
```
Returns recent messages within the channel with pagination and cursor filtering.

### 3.4 Delete Message
```http
DELETE /api/table/messages/{message_id}
Authorization: Bearer lb_live_...
```
Deletes a message previously posted by this machine app.

### 3.5 Real-Time Server-Sent Events (SSE) Stream
```http
GET /api/events?subscriptions=messages
Authorization: Bearer lb_live_...
Accept: text/event-stream
Cache-Control: no-cache
```
Streams real-time events as they occur. Standard SSE line format:
```
event: messages/insert
data: {"id": 1234, "channel_id": 56, "sender_user_id": 789, "text": "Hello bot!", "created_at": "..."}

```

---

## 4. Message Data Format & Threading

### 4.1 Message Attributes
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `int` | Unique message ID |
| `channel_id` | `int` | Bound channel ID |
| `sender_user_id` | `int?` | User ID of the human sender (null if posted by bot) |
| `sender_app_id` | `int?` | App ID when sent by machine/bot |
| `text` | `string` | Markdown-formatted message content |
| `type` | `string` | Message type (`'text'`, `'system'`, `'file'`) |
| `metadata` | `dict` | Metadata payload (bot name, threading, embeds) |
| `created_at` | `string` | ISO 8601 timestamp |

### 4.2 Message Threading
To reply in a thread or reference a specific prompt, the gateway sets `reply_to_id` in the `metadata` dictionary:
```json
{
  "metadata": {
    "is_app": true,
    "bot_name": "AI Assistant",
    "reply_to_id": 8569
  }
}
```

---

## 5. Gateway Architecture & Loop Prevention

```
+-------------------------------------------------------------+
|                        MyOwnChat                            |
|             (User inputs message in App Channel)            |
+------------------------------+------------------------------+
                               |
                          LittleBackend
                       (Real-Time Gateway)
                               |
              +----------------+----------------+
              | (Real-Time SSE Stream)          | (REST POST)
              v                                 ^
+-------------------------------------------------------------+
|                  MyOwnChat Python SDK                       |
|                                                             |
|   1. MyOwnChatClient:                                       |
|      - Stream SSE events (/api/events)                      |
|      - Query history with auto-scoping                      |
|      - Post responses with auto-scoping                     |
|                                                             |
|   2. MyOwnChatGateway:                                      |
|      - Real-time listener & reconnect loop                  |
|      - Loop prevention (drops echoes, webhooks, system)     |
|      - Dispatches prompts to @gateway.on_message            |
|      - Automatically sends returned string as reply         |
|      - Exponential backoff & cursor catchup                 |
+------------------------------+------------------------------+
                               |
                      AI Agent / LLM Brain
     (Nous Hermes Agent, OpenAI GPT-4o, Anthropic, Ollama)
```

### Loop Prevention Rules
To prevent infinite reply loops between bots:
1. `is_from_app`: Automatically ignored (`ignore_self=True`).
2. `is_from_webhook`: Automatically ignored (`ignore_webhooks=True`).
3. `type == 'system'`: Automatically ignored (`ignore_system=True`).
4. Empty / whitespace messages: Automatically dropped.
