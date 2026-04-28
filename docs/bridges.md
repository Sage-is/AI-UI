---
title: "Messaging Bridges"
description: "Connect external messaging platforms like WhatsApp, Telegram, and Email to Sage AI for chat and channel bridging."
date: 2026-02-24
tags:
  - bridges
  - whatsapp
  - telegram
  - signal
  - email
  - messaging
  - integration
---

# Messaging Bridges

Sage.is AI-UIcan connect to external messaging platforms so users can interact with AI directly from WhatsApp, Telegram, Email, and other chat apps. Bridges support two modes:

- **AI Chat** — External users message Sage and get AI responses directly in their messaging app
- **Channel Bridge** — Mirror messages between an external chat and a Sage channel for bidirectional human + AI conversations

## Supported Platforms

| Platform | Status | Adapter | Incoming Pattern |
|----------|--------|---------|-----------------|
| WhatsApp | Available | WAHA (WhatsApp HTTP API) | Webhook |
| Telegram | Available | Bot API (BotFather) | Long polling or webhook |
| Email | Available | SMTP/IMAP (stdlib) | IMAP polling |
| Slack | Planned | — | — |
| Discord | Planned | — | — |
| Signal | Planned | signal-cli-rest-api (Docker) | Webhook or WebSocket |
| Matrix | Planned | — | — |

## Quick Start (WhatsApp)

### 1. Start WAHA

WAHA is an open-source WhatsApp HTTP API that runs as a Docker container. You can run it locally alongside Sage or on a separate server.

**Local (same machine as Sage):**

```bash
make waha_start
```

This starts WAHA on port 3000. The dashboard is at `http://localhost:3000/dashboard` (default login: admin/admin).

**Remote server:**

```bash
docker run -d --name waha \
  -p 3000:3000 \
  -e WHATSAPP_API_KEY=your-secret-key \
  -e WAHA_DASHBOARD_ENABLED=true \
  devlikeapro/waha
```

### 2. Enable Bridges in Sage

Set the environment variable before starting Sage:

```
ENABLE_BRIDGES=true
```

Or toggle it in the admin settings after startup.

### 3. Configure via Admin UI

1. Go to **Admin Settings > Bridges**
2. Click **Add Bridge**
3. Select **WhatsApp** as the platform
4. Fill in the config:
   - **WAHA API URL**: `http://host.docker.internal:3000` (if WAHA is local and Sage is in Docker) or `http://your-waha-server:3000` (if WAHA is remote)
   - **API Key**: Your WAHA API key (if set)
   - **Session Name**: `default` (or any name)
   - **Webhook Secret**: Optional HMAC secret for verifying webhooks
5. Choose a **Mode** (AI Chat or Channel Bridge)
6. Set a **Model ID** if using AI Chat mode (or leave blank for the default)
7. Click **Create**

### 4. Configure WAHA Webhook

Point WAHA's webhook to your Sage instance. In the WAHA dashboard or API:

```
Webhook URL: https://your-sage-domain/api/v1/bridges/webhook/{connection-id}
```

Replace `{connection-id}` with the UUID shown in the Sage bridge admin panel.

### 5. Scan QR Code

Open the WAHA dashboard and scan the QR code with WhatsApp on your phone. Once linked, messages sent to that WhatsApp number will be processed by Sage.

## Quick Start (Telegram)

### 1. Create a Bot with BotFather

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to name your bot
3. Copy the bot token (e.g. `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Configure via Admin UI

1. Go to **Admin Settings > Bridges**
2. Click **Add Bridge**
3. Select **Telegram** as the platform
4. Fill in the config:
   - **Bot Token**: Paste the token from BotFather
   - **Update Mode**: `Long Polling` (recommended — no public URL needed) or `Webhook`
   - **Webhook URL**: Only needed for webhook mode — your public HTTPS URL (e.g. `https://yourdomain.com/api/v1/bridges/webhook/{connection-id}`)
   - **Webhook Secret**: Optional secret token for webhook verification
   - **Message Parse Mode**: `Plain text` (default), `Markdown`, `MarkdownV2`, or `HTML`
5. Choose a **Mode** (AI Chat or Channel Bridge)
6. Click **Create**

### 3. Start Chatting

Send a message to your bot in Telegram. In AI Chat mode, the bot responds with AI-generated replies. In Channel Bridge mode, messages appear in the linked Sage channel.

### Telegram Notes

- **Long polling** is the simplest setup — the Sage server pulls updates from Telegram. No public URL or SSL required.
- **Webhook mode** is more efficient for high-volume bots but requires a publicly accessible HTTPS endpoint.
- The bot supports all media types: photos, documents, audio, video, voice messages, and stickers.
- In groups, the bot responds when mentioned with `@yourbotname`.
- The adapter uses `getFile` to download media, which has a 20MB limit imposed by Telegram's Bot API.

## Quick Start (Email)

### 1. Configure an Email Account

Use any email account that supports SMTP and IMAP. For Gmail, you need an [App Password](https://support.google.com/accounts/answer/185833) (regular passwords won't work with 2FA enabled).

### 2. Configure via Admin UI

1. Go to **Admin Settings > Bridges**
2. Click **Add Bridge**
3. Select **Email (SMTP/IMAP)** as the platform
4. Fill in the config:

   **SMTP (outgoing):**
   - **SMTP Host**: `smtp.gmail.com` (or your provider)
   - **SMTP Port**: `587` (STARTTLS) or `465` (SSL)
   - **SMTP Security**: `STARTTLS` (recommended for port 587) or `SSL/TLS` (for port 465)

   **IMAP (incoming):**
   - **IMAP Host**: `imap.gmail.com` (or your provider)
   - **IMAP Port**: `993`
   - **IMAP Security**: `SSL/TLS`

   **Credentials:**
   - **Email Address**: `sage@yourdomain.com`
   - **Password**: Your app password

   **Optional:**
   - **Poll Interval**: How often to check for new emails (default: 30 seconds)
   - **Subject Prefix Filter**: Only process emails with subjects starting with this prefix
   - **Default Outgoing Subject**: Subject line for emails sent by Sage
5. Choose a **Mode** (AI Chat or Channel Bridge)
6. Click **Create**

### 3. Test It

Send an email to the configured address. Sage will poll IMAP for new messages, process them through the AI pipeline, and reply via SMTP.

### Email Notes

- **No extra dependencies** — uses Python's built-in `smtplib`, `imaplib`, and `email` modules.
- **Fresh connections per operation** — avoids stale connection issues with long-lived IMAP/SMTP sessions.
- **Self-loop prevention** — emails from the configured address are automatically skipped.
- **Subject prefix filtering** — applied both server-side (IMAP SEARCH) and client-side for reliability.
- **Attachments** — incoming email attachments are parsed and passed as `MediaAttachment` objects. Outgoing messages support MIME attachments.
- The `thread_id` for email is the sender's email address (conversations are per-sender).

### Common Email Provider Settings

| Provider | SMTP Host | SMTP Port | IMAP Host | IMAP Port |
|----------|-----------|-----------|-----------|-----------|
| Gmail | smtp.gmail.com | 587 (STARTTLS) | imap.gmail.com | 993 (SSL) |
| Outlook/Hotmail | smtp-mail.outlook.com | 587 (STARTTLS) | outlook.office365.com | 993 (SSL) |
| Yahoo | smtp.mail.yahoo.com | 465 (SSL) | imap.mail.yahoo.com | 993 (SSL) |
| iCloud | smtp.mail.me.com | 587 (STARTTLS) | imap.mail.me.com | 993 (SSL) |
| Fastmail | smtp.fastmail.com | 465 (SSL) | imap.fastmail.com | 993 (SSL) |

## Quick Start (Signal)

### 1. Start signal-cli-rest-api

Signal integration uses [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) — a Go/Java container that exposes signal-cli as an HTTP REST API. Like WAHA for WhatsApp, it runs as a **separate Docker container**.

**Local (same machine as Sage):**

```bash
make signal_start
```

This starts signal-cli-rest-api on port 8081 in `json-rpc` mode (persistent JVM, fastest).

### 2. Register or Link a Phone Number

**Option A: Link to your existing Signal account (secondary device):**

Open `http://localhost:8081/v1/qrcodelink?device_name=sage-bridge` in your browser, then scan the QR code from Signal on your phone (Settings > Linked Devices > +).

**Option B: Register a dedicated number:**

```bash
# Trigger SMS verification
curl -X POST http://localhost:8081/v1/register/+1234567890

# Verify with the code from SMS
curl -X POST http://localhost:8081/v1/register/+1234567890/verify/123456
```

A dedicated number is recommended for production to keep bot traffic separate from your personal messages.

### 3. Configure via Admin UI

1. Go to **Admin Settings > Bridges**
2. Click **Add Bridge**
3. Select **Signal** as the platform
4. Fill in the config:
   - **API URL**: `http://host.docker.internal:8081` (Docker-to-Docker) or `http://localhost:8081`
   - **Phone Number**: The registered/linked number (e.g. `+1234567890`)
   - **Receive Mode**: `webhook` (recommended) or `websocket`
   - **Webhook URL**: Your public Sage URL (e.g. `https://yourdomain.com/api/v1/bridges/webhook/{connection-id}`) — only for webhook mode
5. Choose a **Mode** (AI Chat or Channel Bridge)
6. Click **Create**

### 4. Test It

Send a Signal message to the registered phone number. Sage will receive it via webhook (or WebSocket) and respond through the AI pipeline.

### Signal Notes

- **Separate container** — signal-cli-rest-api runs independently. Sage connects to its REST API via HTTP, same pattern as WAHA for WhatsApp.
- **json-rpc mode** keeps the JVM running for fastest response times. Use `MODE=native` for lower memory at the cost of slightly slower sends.
- **No HMAC webhook verification** — signal-cli-rest-api doesn't sign webhook payloads. Secure via Docker network isolation (shared network, no exposed port) or a reverse proxy.
- **Rate limits** — Signal enforces server-side limits (~1-2 msg/sec sustained). First messages to new contacts are more scrutinized.
- **Unofficial** — signal-cli is third-party (not by Signal Foundation). Same risk profile as WAHA for WhatsApp. Keep the container updated — Signal protocol changes can break older versions within ~3 months.
- **Attachments** — send as base64, receive via `GET /v1/attachments/{id}`. All media types supported.
- **Groups** — supported via group IDs. The bot can send to and receive from Signal groups.
- **Device limit** — Signal allows max 5 linked devices per primary account.

## Deployment Topologies

### Local Development

Both Sage and WAHA on the same machine:

```
[WhatsApp] <-> [WAHA :3000] <-> [Sage :8080]
                localhost         localhost
```

WAHA API URL in Sage config: `http://host.docker.internal:3000` (Docker-to-Docker) or `http://localhost:3000` (if Sage is not in Docker).

### Split Setup

WAHA on a dedicated server (useful for keeping WhatsApp sessions persistent, or running multiple WAHA instances):

```
[WhatsApp] <-> [WAHA @ waha.example.com:3000] <-> [Sage @ sage.example.com:8080]
```

WAHA API URL in Sage config: `http://waha.example.com:3000`

Set `WHATSAPP_API_KEY` on the WAHA server and enter the same key in Sage's bridge config for authenticated access.

### Multiple Bridges

You can create multiple bridge connections — even multiple WhatsApp connections with different WAHA servers or sessions. Each connection has its own config, credentials, and user provisioning rules.

## Modes

### AI Chat Mode

Each external user gets their own Sage chat. Messages are processed through the configured AI model and responses are sent back.

- Chat history is preserved per user across sessions
- Users are automatically created in Sage with the role configured in bridge settings
- Media attachments (images, documents) from WhatsApp are downloaded and stored

### Channel Bridge Mode

Messages from the external platform are posted into a Sage channel, and messages from the Sage channel are forwarded back.

- AI responses happen when `@sage` is mentioned in the message
- Messages originating from bridges are marked to prevent forwarding loops
- Sender names are included when forwarding Sage channel messages outbound

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_BRIDGES` | `false` | Master toggle for the bridge system |
| `BRIDGE_DEFAULT_MODEL` | `""` | Fallback AI model for bridges without a specific model |
| `BRIDGE_AUTO_CREATE_USERS` | `true` | Allow auto-creation of user accounts from bridges |
| `BRIDGE_DEFAULT_USER_ROLE` | `user` | Role assigned to auto-created bridge users |
| `BRIDGE_RATE_LIMIT_PER_MINUTE` | `30` | Max messages per user per minute |

### Per-Connection Config (WhatsApp/WAHA)

| Field | Required | Description |
|-------|----------|-------------|
| `api_url` | Yes | Full URL to the WAHA API (e.g. `http://localhost:3000`) |
| `api_key` | No | Bearer token for WAHA API authentication |
| `session_name` | No | WAHA session name (default: `default`) |
| `webhook_secret` | No | HMAC-SHA256 secret for webhook signature verification |

### Per-Connection Config (Telegram)

| Field | Required | Description |
|-------|----------|-------------|
| `bot_token` | Yes | Bot token from @BotFather |
| `mode` | Yes | `polling` (default, no public URL needed) or `webhook` |
| `webhook_url` | No | Public HTTPS URL (required for webhook mode) |
| `webhook_secret` | No | Secret token sent in `X-Telegram-Bot-Api-Secret-Token` header |
| `parse_mode` | No | Message formatting: empty (plain), `Markdown`, `MarkdownV2`, or `HTML` |
| `poll_timeout` | No | Long-poll timeout in seconds (default: `30`) |

### Per-Connection Config (Email)

| Field | Required | Description |
|-------|----------|-------------|
| `smtp_host` | Yes | SMTP server hostname |
| `smtp_port` | Yes | SMTP port (default: `587`) |
| `smtp_tls` | Yes | `starttls`, `ssl`, or `none` (default: `starttls`) |
| `imap_host` | Yes | IMAP server hostname |
| `imap_port` | Yes | IMAP port (default: `993`) |
| `imap_tls` | Yes | `ssl`, `starttls`, or `none` (default: `ssl`) |
| `email_address` | Yes | Email address for sending and receiving |
| `password` | Yes | Account password (app password recommended) |
| `poll_interval` | No | Seconds between IMAP checks (default: `30`) |
| `subject_prefix` | No | Only process emails with subjects matching this prefix |
| `default_subject` | No | Subject line for outgoing emails (default: `Message from Sage AI`) |

### Per-Connection Config (Signal)

| Field | Required | Description |
|-------|----------|-------------|
| `api_url` | Yes | URL of the signal-cli-rest-api container (e.g. `http://localhost:8081`) |
| `phone_number` | Yes | Registered/linked Signal phone number (e.g. `+1234567890`) |
| `receive_mode` | Yes | `webhook` (recommended) or `websocket` |
| `webhook_url` | No | Public HTTPS URL for webhook callbacks (required if receive_mode is `webhook`) |

### User Provisioning Options

| Mode | Behavior |
|------|----------|
| `auto_create` | Any external user who messages gets a Sage account automatically |
| `pre_approved` | Only users in the Allowed IDs list get accounts |
| `disabled` | No new accounts created; only pre-existing mapped users can interact |

## Make Targets

| Target | Description |
|--------|-------------|
| `make waha_start` | Start WAHA container locally on port 3000 |
| `make waha_stop` | Stop WAHA container |
| `make waha_logs` | Tail WAHA container logs |
| `make waha_status` | Check if WAHA is running |
| `make signal_start` | Start signal-cli-rest-api container on port 8081 |
| `make signal_stop` | Stop signal-cli-rest-api container |
| `make signal_logs` | Tail signal-cli-rest-api container logs |
| `make signal_status` | Check if signal-cli-rest-api is running |

Override defaults with environment variables or `.env`:

```bash
WAHA_PORT=3001 make waha_start               # Custom port
WAHA_API_KEY=secret123 make waha_start       # Set API key
SIGNAL_PORT=8082 make signal_start           # Custom port
```

## API Endpoints

All endpoints except the webhook require admin authentication.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/bridges/` | List all bridge connections |
| `POST` | `/api/v1/bridges/create` | Create a new bridge |
| `GET` | `/api/v1/bridges/{id}` | Get bridge details |
| `POST` | `/api/v1/bridges/{id}/update` | Update bridge config |
| `DELETE` | `/api/v1/bridges/{id}/delete` | Delete bridge and its threads |
| `POST` | `/api/v1/bridges/{id}/toggle` | Enable/disable bridge |
| `POST` | `/api/v1/bridges/{id}/restart` | Restart bridge connection |
| `GET` | `/api/v1/bridges/status/all` | Get all bridge statuses |
| `GET` | `/api/v1/bridges/{id}/health` | Health check for a bridge |
| `POST` | `/api/v1/bridges/webhook/{id}` | Webhook receiver (no auth, signature-verified) |
| `GET` | `/api/v1/bridges/platforms/available` | List available platform adapters |
| `GET` | `/api/v1/bridges/{id}/threads` | List threads for debugging |

## Security

- **Webhook authentication**: WhatsApp uses HMAC-SHA256 signature verification. Telegram uses a `secret_token` header. Signal relies on network-level isolation (no HMAC support in signal-cli-rest-api). Email doesn't use webhooks.
- **Self-loop prevention**: Email adapter skips messages from its own address. WhatsApp skips `fromMe` messages. Telegram skips messages from the bot's own user ID.
- **User provisioning**: Configurable per-connection. Use `pre_approved` or `disabled` to restrict who can interact.
- **Allowlists**: Optional per-connection list of permitted external user IDs.
- **Rate limiting**: Per-user per-minute throttle to prevent abuse.
- **Loop prevention**: Messages from bridges carry a `data.bridge` marker. The channel forwarding hook skips these to prevent infinite loops.
- **Credential storage**: Passwords and tokens are stored in the bridge connection config (encrypted at rest if the database supports it). Use app-specific passwords where possible.

## Architecture

Bridges support two incoming patterns depending on the platform:

### Webhook Pattern (WhatsApp, Telegram webhook mode)

```
External Platform POSTs to Sage
        |
        v
  /api/v1/bridges/webhook/{id}
        |
        v
  Adapter.verify_webhook_signature()
  Adapter.handle_webhook() -> IncomingMessage
        |
        v
  MessagePipeline.process_incoming()
```

### Polling Pattern (Email, Telegram polling mode)

```
Adapter background task (asyncio.Task)
        |  polls external service periodically
        v
  _fetch_unseen_emails() / getUpdates()
        |
        v
  self._incoming_handler(IncomingMessage)
        |  (wired to pipeline by BridgeManager)
        v
  MessagePipeline.process_incoming()
```

### Message Processing Pipeline

```
  MessagePipeline.process_incoming()
        |
        +-- AI Chat Mode:
        |     resolve user -> resolve thread -> resolve chat
        |     -> save user msg -> generate_chat_completion()
        |     -> save assistant msg -> adapter.send_message()
        |
        +-- Channel Bridge Mode:
              resolve user -> post Message to channel
              -> emit Socket.IO event -> (if @sage mentioned)
              -> generate_chat_completion() -> adapter.send_message()
```

### Outbound (Sage channel -> external)

```
  Channel message posted (web UI)
        |
        v
  post_new_message() background task
        |
        v
  forward_channel_message_to_bridges()
        |  (skip if message has data.bridge marker)
        v
  adapter.send_message() to each connected thread
```

### File Layout

```
app/backend/open_webui/bridges/
├── base.py          # MessageBridge ABC + _incoming_handler callback
├── types.py         # Platform enum, IncomingMessage, OutgoingMessage, etc.
├── manager.py       # BridgeManager lifecycle, register_adapter() decorator
├── pipeline.py      # MessagePipeline — user resolution, AI chat, channel bridge
└── adapters/
    ├── whatsapp.py  # WhatsApp via WAHA (webhook-driven)
    ├── telegram.py  # Telegram Bot API (polling or webhook)
    ├── email.py     # Email via SMTP/IMAP (polling-driven, stdlib only)
    └── signal.py    # Signal via signal-cli-rest-api (webhook or websocket)
```

## Troubleshooting

### Bridge shows "disconnected" after creation

- **WhatsApp**: Verify WAHA is running: `make waha_status` or `curl http://localhost:3000/api/sessions`. Check the WAHA API URL is reachable from inside the Sage Docker container — use `http://host.docker.internal:3000` for Docker-to-Docker communication.
- **Telegram**: Verify the bot token is correct. Try `curl https://api.telegram.org/bot<TOKEN>/getMe` to test.
- **Email**: Verify SMTP/IMAP credentials. Gmail requires an App Password with 2FA enabled. Check that IMAP is enabled in your email account settings.
- **Signal**: Verify signal-cli-rest-api is running: `make signal_status` or `curl http://localhost:8081/v1/about`. Check that a number is registered: `curl http://localhost:8081/v1/accounts`.

### Webhook not receiving messages

- Ensure the webhook URL is publicly accessible over HTTPS.
- **WhatsApp**: Configure WAHA's webhook to point to `https://yourdomain/api/v1/bridges/webhook/{connection-id}`.
- **Telegram**: The adapter sets the webhook automatically on connect. Verify with `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`.

### Telegram bot not responding in groups

- The bot must be added to the group as a member.
- In groups, the bot only responds when mentioned with `@yourbotname`.
- If the bot has [privacy mode](https://core.telegram.org/bots/features#privacy-mode) enabled, it only sees messages that mention it or are replies to its messages. Disable privacy mode via BotFather (`/setprivacy`) if needed.

### Email bridge not picking up messages

- Check that the poll interval is reasonable (default 30s).
- Verify IMAP access is enabled for your email account (some providers disable it by default).
- If using a subject prefix filter, ensure incoming emails match the prefix exactly.
- Check Sage logs for IMAP connection errors — some providers rate-limit frequent IMAP connections.

### "No adapter for platform" error

- The adapter module failed to load. Check Sage container logs for import errors.

### Users not being created

- Check the `user_provisioning` setting on the bridge connection.
- Verify `BRIDGE_AUTO_CREATE_USERS` is `true` in your environment.

## Adding a New Adapter

To add support for a new messaging platform:

1. Create `app/backend/open_webui/bridges/adapters/<name>.py`
2. Subclass `MessageBridge` and decorate with `@register_adapter("<name>")`
3. Add the enum value to `Platform` in `bridges/types.py` (if not already present)
4. Add the import to `bridges/manager.py` in both `_load_adapters()` and `get_available_platforms()`
5. Implement all abstract methods from `MessageBridge`
6. For **webhook-driven** adapters: implement `handle_webhook()` and `verify_webhook_signature()`
7. For **polling-driven** adapters: start a background `asyncio.Task` in `connect()` and call `self._incoming_handler(msg)` for each incoming message
8. Define `get_platform_info()` with the config schema — the admin UI renders fields dynamically, no frontend changes needed
