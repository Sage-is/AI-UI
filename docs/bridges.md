---
title: "Messaging Bridges"
description: "Connect external messaging platforms like WhatsApp and Telegram to Sage AI for chat and channel bridging."
date: 2026-02-22
tags:
  - bridges
  - whatsapp
  - messaging
  - integration
---

# Messaging Bridges

Sage WebUI can connect to external messaging platforms so users can interact with AI directly from WhatsApp, Telegram, and other chat apps. Bridges support two modes:

- **AI Chat** — External users message Sage and get AI responses directly in their messaging app
- **Channel Bridge** — Mirror messages between an external chat and a Sage channel for bidirectional human + AI conversations

## Supported Platforms

| Platform | Status | Adapter |
|----------|--------|---------|
| WhatsApp | Phase 1 (available) | WAHA (WhatsApp HTTP API) |
| Telegram | Planned | — |
| Slack | Planned | — |
| Discord | Planned | — |
| Signal | Planned | — |
| Matrix | Planned | — |

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

Override defaults with environment variables or `.env`:

```bash
WAHA_PORT=3001 make waha_start           # Custom port
WAHA_API_KEY=secret123 make waha_start   # Set API key
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

- **Webhook authentication**: Each adapter verifies incoming webhooks using HMAC-SHA256 signatures. The webhook endpoint is the only unauthenticated route, protected by the UUID connection ID plus signature verification.
- **User provisioning**: Configurable per-connection. Use `pre_approved` or `disabled` to restrict who can interact.
- **Allowlists**: Optional per-connection list of permitted external user IDs.
- **Rate limiting**: Per-user per-minute throttle to prevent abuse.
- **Loop prevention**: Messages from bridges carry a `data.bridge` marker. The channel forwarding hook skips these to prevent infinite loops.

## Architecture

```
External Platform (WhatsApp, etc.)
        |
        v  (webhook POST)
  /api/v1/bridges/webhook/{id}
        |
        v
  Adapter.verify_webhook_signature()
  Adapter.handle_webhook() -> IncomingMessage
        |
        v
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

Outbound (Sage channel -> external):
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

## Troubleshooting

**Bridge shows "disconnected" after creation**
- Verify WAHA is running: `make waha_status` or `curl http://localhost:3000/api/sessions`
- Check the WAHA API URL is reachable from inside the Sage Docker container. Use `http://host.docker.internal:3000` for Docker-to-Docker communication on the same host.

**Webhook not receiving messages**
- Ensure WAHA's webhook is configured to point to your Sage instance's public URL
- If running locally, you may need a tunnel (e.g. ngrok) for WhatsApp Cloud webhooks, but WAHA handles this via its own session

**"No adapter for platform" error**
- The adapter module failed to load. Check Sage container logs for import errors.

**Users not being created**
- Check the `user_provisioning` setting on the bridge connection
- Verify `BRIDGE_AUTO_CREATE_USERS` is `true` in your environment
