import hashlib
import hmac
import json
import logging
from typing import Optional

import aiohttp

from open_webui.bridges.base import MessageBridge
from open_webui.bridges.manager import register_adapter
from open_webui.bridges.types import (
    ConfigField,
    IncomingMessage,
    MediaAttachment,
    OutgoingMessage,
    PlatformInfo,
)

log = logging.getLogger(__name__)


@register_adapter("whatsapp")
class WhatsAppBridge(MessageBridge):
    """WhatsApp adapter using WAHA (WhatsApp HTTP API)."""

    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_url = config.get("api_url", "").rstrip("/")
        self._api_key = config.get("api_key", "")
        self._session_name = config.get("session_name", "default")
        self._webhook_secret = config.get("webhook_secret", "")

    async def connect(self) -> bool:
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._session = aiohttp.ClientSession(
            base_url=self._api_url,
            headers=headers,
        )

        try:
            async with self._session.get(
                f"/api/sessions/{self._session_name}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    waha_status = data.get("status", "")
                    if waha_status in ("WORKING", "SCAN_QR_CODE"):
                        self._connected = True
                        log.info(
                            f"WhatsApp WAHA connected: session={self._session_name}, "
                            f"status={waha_status}"
                        )
                        return True
                    else:
                        log.warning(
                            f"WAHA session status: {waha_status}"
                        )
                        return False
                elif resp.status == 404:
                    # Session doesn't exist, try to create it
                    log.info(f"WAHA session not found, creating: {self._session_name}")
                    return await self._create_session()
                else:
                    log.error(f"WAHA session check failed: {resp.status}")
                    return False
        except Exception as e:
            log.error(f"WhatsApp connect error: {e}")
            return False

    async def _create_session(self) -> bool:
        """Create a new WAHA session if one doesn't exist."""
        try:
            payload = {
                "name": self._session_name,
                "start": True,
            }
            async with self._session.post(
                "/api/sessions", json=payload
            ) as resp:
                if resp.status in (200, 201):
                    self._connected = True
                    log.info(f"WAHA session created: {self._session_name}")
                    return True
                else:
                    body = await resp.text()
                    log.error(f"Failed to create WAHA session: {resp.status} - {body}")
                    return False
        except Exception as e:
            log.error(f"Error creating WAHA session: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False
        if self._session:
            await self._session.close()
            self._session = None

    async def send_message(self, message: OutgoingMessage) -> bool:
        if not self._session or not self._connected:
            return False

        try:
            payload = {
                "chatId": message.thread_id,
                "text": message.content,
                "session": self._session_name,
            }

            async with self._session.post(
                "/api/sendText", json=payload
            ) as resp:
                if resp.status == 200 or resp.status == 201:
                    return True
                else:
                    body = await resp.text()
                    log.error(f"WAHA send_message failed: {resp.status} - {body}")
                    return False
        except Exception as e:
            log.error(f"WhatsApp send_message error: {e}")
            return False

    async def health_check(self) -> bool:
        if not self._session:
            return False

        try:
            async with self._session.get(
                f"/api/sessions/{self._session_name}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("status") == "WORKING"
                return False
        except Exception:
            return False

    async def handle_webhook(
        self, body: bytes, headers: dict
    ) -> Optional[IncomingMessage]:
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            log.error("Invalid JSON in WhatsApp webhook")
            return None

        event_type = event.get("event")

        # Only handle incoming messages
        if event_type not in ("message", "message.any"):
            return None

        payload = event.get("payload", {})

        # Skip outgoing messages (from us)
        if payload.get("fromMe", False):
            return None

        # Extract message details
        chat_id = payload.get("from", "")
        sender = payload.get("participant") or chat_id  # participant for groups
        body_text = payload.get("body", "")
        has_media = payload.get("hasMedia", False)
        is_group = "@g.us" in chat_id

        # Handle contact name
        sender_name = None
        if "_data" in payload:
            notify_name = payload["_data"].get("notifyName")
            if notify_name:
                sender_name = notify_name

        # Build media attachments
        media = []
        if has_media:
            media_url = payload.get("mediaUrl")
            mime_type = payload.get("mimetype", "application/octet-stream")
            if media_url:
                media.append(
                    MediaAttachment(
                        url=media_url,
                        mime_type=mime_type,
                        filename=payload.get("filename"),
                    )
                )

        # Check if bot is mentioned (for groups)
        mentions_bot = False
        if is_group:
            mentioned_ids = payload.get("mentionedIds", [])
            # WAHA bot's own ID might vary; check content for @sage pattern too
            if any("sage" in str(mid).lower() for mid in mentioned_ids):
                mentions_bot = True
            if "@sage" in body_text.lower():
                mentions_bot = True

        return IncomingMessage(
            connection_id=self.connection_id,
            platform="whatsapp",
            external_thread_id=chat_id,
            external_user_id=sender,
            external_user_name=sender_name,
            content=body_text,
            media=media,
            raw_event=event,
            is_group=is_group,
            mentions_bot=mentions_bot,
        )

    async def verify_webhook_signature(
        self, body: bytes, headers: dict
    ) -> bool:
        if not self._webhook_secret:
            # No secret configured, allow all
            return True

        signature = headers.get("x-webhook-hmac-sha256", "")
        if not signature:
            # Also check lowercase variant
            signature = headers.get("x-webhook-hmac", "")

        if not signature:
            log.warning("No webhook signature found in request headers")
            return False

        expected = hmac.new(
            self._webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def download_media(self, attachment: MediaAttachment) -> Optional[bytes]:
        """Download media using WAHA API with authentication."""
        if not self._session:
            return None

        try:
            async with self._session.get(attachment.url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    log.error(f"WAHA media download failed: {resp.status}")
        except Exception as e:
            log.error(f"WhatsApp media download error: {e}")
        return None

    @classmethod
    def get_platform_info(cls) -> PlatformInfo:
        return PlatformInfo(
            platform="whatsapp",
            display_name="WhatsApp",
            description="Connect WhatsApp via WAHA (WhatsApp HTTP API)",
            supports_media=True,
            supports_groups=True,
            config_schema=[
                ConfigField(
                    name="api_url",
                    label="WAHA API URL",
                    type="url",
                    required=True,
                    placeholder="http://localhost:3000",
                ),
                ConfigField(
                    name="api_key",
                    label="API Key",
                    type="password",
                    required=False,
                    placeholder="Optional WAHA API key",
                ),
                ConfigField(
                    name="session_name",
                    label="Session Name",
                    type="text",
                    required=False,
                    default="default",
                    placeholder="default",
                ),
                ConfigField(
                    name="webhook_secret",
                    label="Webhook Secret",
                    type="password",
                    required=False,
                    placeholder="HMAC secret for webhook verification",
                ),
            ],
        )
