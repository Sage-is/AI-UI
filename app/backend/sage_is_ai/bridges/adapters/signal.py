import asyncio
import base64
import json
import logging
from typing import Optional

import aiohttp

from sage_is_ai.bridges.base import MessageBridge
from sage_is_ai.bridges.manager import register_adapter
from sage_is_ai.bridges.types import (
    ConfigField,
    IncomingMessage,
    MediaAttachment,
    OutgoingMessage,
    PlatformInfo,
)

log = logging.getLogger(__name__)


@register_adapter("signal")
class SignalBridge(MessageBridge):
    """Signal adapter using signal-cli-rest-api (Docker container)."""

    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self._api_url: str = config.get("api_url", "").rstrip("/")
        self._phone_number: str = config.get("phone_number", "")
        self._mode: str = config.get("mode", "websocket")
        self._webhook_url: str = config.get("webhook_url", "")

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        self._session = aiohttp.ClientSession()
        try:
            # Verify API is reachable
            async with self._session.get(f"{self._api_url}/v1/about") as resp:
                if resp.status != 200:
                    log.error(f"Signal API not reachable: {resp.status}")
                    await self._session.close()
                    self._session = None
                    return False

            # Verify phone number is registered
            async with self._session.get(
                f"{self._api_url}/v1/accounts"
            ) as resp:
                if resp.status == 200:
                    accounts = await resp.json()
                    # accounts is a list of registered numbers
                    if isinstance(accounts, list):
                        registered = any(
                            acc.get("number") == self._phone_number
                            or acc == self._phone_number
                            for acc in (
                                accounts
                                if not accounts
                                or isinstance(accounts[0], str)
                                else accounts
                            )
                        )
                        if not registered and accounts:
                            # Also check if it's a simple list of strings
                            registered = self._phone_number in [
                                str(a) for a in accounts
                            ]
                        if not registered:
                            log.error(
                                f"Signal number {self._phone_number} not registered. "
                                f"Available: {accounts}"
                            )
                            await self._session.close()
                            self._session = None
                            return False
                else:
                    log.error(f"Signal accounts check failed: {resp.status}")
                    await self._session.close()
                    self._session = None
                    return False

            log.info(
                f"Signal API connected: number={self._phone_number}, mode={self._mode}"
            )

            if self._mode == "websocket":
                self._stop_event.clear()
                self._ws_task = asyncio.create_task(self._ws_receive_loop())
            else:
                # Webhook mode — webhook URL is configured on the Docker container
                # via RECEIVE_WEBHOOK_URL env var, not via API call
                if not self._webhook_url:
                    log.warning(
                        "Signal webhook mode selected but no webhook_url configured. "
                        "Ensure RECEIVE_WEBHOOK_URL is set on the signal-cli container."
                    )

            self._connected = True
            return True
        except Exception as e:
            log.error(f"Signal connect error: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._stop_event.set()

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

        if self._session:
            await self._session.close()
            self._session = None

        log.info("Signal bridge disconnected")

    async def health_check(self) -> bool:
        if not self._session:
            return False
        try:
            async with self._session.get(f"{self._api_url}/v1/about") as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # WebSocket receive loop
    # ------------------------------------------------------------------

    async def _ws_receive_loop(self) -> None:
        """Background task that connects to signal-cli-rest-api WebSocket."""
        # Build WS URL: replace http(s) with ws(s)
        ws_url = self._api_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        number_encoded = self._phone_number.replace("+", "%2B")
        ws_endpoint = f"{ws_url}/v1/receive/{number_encoded}"

        log.info(f"Signal WebSocket connecting: {ws_endpoint}")

        while not self._stop_event.is_set():
            try:
                async with self._session.ws_connect(ws_endpoint) as ws:
                    log.info("Signal WebSocket connected")
                    async for msg in ws:
                        if self._stop_event.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                event = json.loads(msg.data)
                                incoming = self._parse_envelope(event)
                                if incoming and self._incoming_handler:
                                    await self._incoming_handler(incoming)
                            except json.JSONDecodeError:
                                log.warning("Signal WS: invalid JSON frame")
                            except Exception as e:
                                log.error(f"Error processing Signal WS message: {e}")
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Signal WebSocket error: {e}")

            if not self._stop_event.is_set():
                log.info("Signal WebSocket reconnecting in 5s...")
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------

    async def handle_webhook(
        self, body: bytes, headers: dict
    ) -> Optional[IncomingMessage]:
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            log.error("Invalid JSON in Signal webhook")
            return None

        return self._parse_envelope(event)

    async def verify_webhook_signature(
        self, body: bytes, headers: dict
    ) -> bool:
        # signal-cli-rest-api has no HMAC webhook signing;
        # secure via Docker network / firewall rules
        return True

    # ------------------------------------------------------------------
    # Envelope parsing (shared between WS and webhook)
    # ------------------------------------------------------------------

    def _parse_envelope(self, event: dict) -> Optional[IncomingMessage]:
        """Parse a signal-cli-rest-api envelope into an IncomingMessage."""
        envelope = event.get("envelope", event)

        data_message = envelope.get("dataMessage")
        if not data_message:
            # Not a regular message (receipt, typing indicator, etc.)
            return None

        # Sender info
        source_number = envelope.get("sourceNumber", "")
        source_name = envelope.get("sourceName", "")
        source_uuid = envelope.get("sourceUuid", "")

        # Group detection
        group_info = data_message.get("groupInfo")
        is_group = group_info is not None
        if is_group:
            thread_id = group_info.get("groupId", "")
        else:
            thread_id = source_number

        # User ID: prefer UUID (stable), fall back to phone number
        user_id = source_uuid or source_number

        # Message text
        text = data_message.get("message", "") or ""

        # Media attachments
        media: list[MediaAttachment] = []
        for att in data_message.get("attachments", []):
            att_id = att.get("id")
            if att_id:
                download_url = f"{self._api_url}/v1/attachments/{att_id}"
                media.append(
                    MediaAttachment(
                        url=download_url,
                        mime_type=att.get("contentType", "application/octet-stream"),
                        filename=att.get("filename"),
                        size=att.get("size"),
                    )
                )

        # Bot mention detection in groups (text match)
        mentions_bot = False
        if is_group and text:
            if "@sage" in text.lower():
                mentions_bot = True
            # Also check signal mentions list
            for mention in data_message.get("mentions", []):
                # Check if the mention refers to our number
                if mention.get("number") == self._phone_number:
                    mentions_bot = True
                    break
                if mention.get("uuid") == source_uuid:
                    # This would be self-mention, skip
                    pass

        if not text and not media:
            return None

        return IncomingMessage(
            connection_id=self.connection_id,
            platform="signal",
            external_thread_id=thread_id,
            external_user_id=user_id,
            external_user_name=source_name or None,
            content=text,
            media=media,
            raw_event=event,
            is_group=is_group,
            mentions_bot=mentions_bot,
        )

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(self, message: OutgoingMessage) -> bool:
        if not self._session or not self._connected:
            return False

        try:
            payload: dict = {
                "message": message.content,
                "number": self._phone_number,
            }

            if self._is_group_id(message.thread_id):
                payload["recipients"] = []
                payload["group"] = message.thread_id
            else:
                payload["recipients"] = [message.thread_id]

            # Attach media as base64
            if message.media:
                b64_attachments = []
                for att in message.media:
                    if att.data:
                        mime = att.mime_type or "application/octet-stream"
                        name = att.filename or "file"
                        encoded = base64.b64encode(att.data).decode("ascii")
                        b64_attachments.append(
                            f"data:{mime};filename={name};base64,{encoded}"
                        )
                if b64_attachments:
                    payload["base64_attachments"] = b64_attachments

            async with self._session.post(
                f"{self._api_url}/v2/send", json=payload
            ) as resp:
                if resp.status in (200, 201):
                    return True
                else:
                    body = await resp.text()
                    log.error(f"Signal send_message failed: {resp.status} - {body}")
                    return False
        except Exception as e:
            log.error(f"Signal send_message error: {e}")
            return False

    # ------------------------------------------------------------------
    # Media download
    # ------------------------------------------------------------------

    async def download_media(self, attachment: MediaAttachment) -> Optional[bytes]:
        """Download media from signal-cli-rest-api attachments endpoint."""
        if not self._session:
            return None

        try:
            async with self._session.get(attachment.url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    log.error(f"Signal media download failed: {resp.status}")
        except Exception as e:
            log.error(f"Signal media download error: {e}")
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_group_id(thread_id: str) -> bool:
        """Phone numbers start with '+', group IDs don't."""
        return not thread_id.startswith("+")

    # ------------------------------------------------------------------
    # Platform info
    # ------------------------------------------------------------------

    @classmethod
    def get_platform_info(cls) -> PlatformInfo:
        return PlatformInfo(
            platform="signal",
            display_name="Signal",
            description="Connect Signal via signal-cli-rest-api (Docker container)",
            supports_media=True,
            supports_groups=True,
            config_schema=[
                ConfigField(
                    name="api_url",
                    label="Signal CLI API URL",
                    type="url",
                    required=True,
                    placeholder="http://localhost:8080",
                ),
                ConfigField(
                    name="phone_number",
                    label="Phone Number",
                    type="text",
                    required=True,
                    placeholder="+1234567890",
                ),
                ConfigField(
                    name="mode",
                    label="Receive Mode",
                    type="select",
                    required=True,
                    default="websocket",
                    options=[
                        {"value": "websocket", "label": "WebSocket (recommended)"},
                        {"value": "webhook", "label": "Webhook (set RECEIVE_WEBHOOK_URL on container)"},
                    ],
                ),
                ConfigField(
                    name="webhook_url",
                    label="Webhook URL",
                    type="url",
                    required=False,
                    placeholder="https://yourdomain.com/api/v1/bridges/webhook/signal/...",
                ),
            ],
        )
