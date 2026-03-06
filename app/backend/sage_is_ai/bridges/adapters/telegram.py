import asyncio
import hashlib
import hmac
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

TELEGRAM_API = "https://api.telegram.org"


@register_adapter("telegram")
class TelegramBridge(MessageBridge):
    """Telegram adapter using the Bot API (BotFather token)."""

    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self._bot_token: str = config.get("bot_token", "")
        self._mode: str = config.get("mode", "polling")
        self._webhook_url: str = config.get("webhook_url", "")
        self._webhook_secret: str = config.get("webhook_secret", "")
        self._parse_mode: str = config.get("parse_mode", "")
        self._poll_timeout: int = int(config.get("poll_timeout", 30))

        self._session: Optional[aiohttp.ClientSession] = None
        self._bot_info: Optional[dict] = None  # result of getMe
        self._poll_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._update_offset: int = 0

    @property
    def _api_base(self) -> str:
        return f"{TELEGRAM_API}/bot{self._bot_token}"

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        self._session = aiohttp.ClientSession()
        try:
            # Verify token via getMe
            self._bot_info = await self._api_call("getMe")
            if not self._bot_info:
                log.error("Telegram getMe failed — invalid bot token?")
                await self._session.close()
                return False

            bot_name = self._bot_info.get("username", "unknown")
            log.info(f"Telegram bot authenticated: @{bot_name}")

            if self._mode == "webhook":
                if not self._webhook_url:
                    log.error("Webhook mode selected but no webhook_url configured")
                    await self._session.close()
                    return False
                await self._setup_webhook()
            else:
                # Polling mode — delete any existing webhook first
                await self._api_call("deleteWebhook")
                self._stop_event.clear()
                self._poll_task = asyncio.create_task(self._poll_loop())

            self._connected = True
            return True
        except Exception as e:
            log.error(f"Telegram connect error: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._stop_event.set()

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self._mode == "webhook":
            try:
                await self._api_call("deleteWebhook")
            except Exception:
                pass

        if self._session:
            await self._session.close()
            self._session = None

        log.info("Telegram bridge disconnected")

    async def health_check(self) -> bool:
        if not self._session:
            return False
        try:
            result = await self._api_call("getMe")
            return result is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(self, message: OutgoingMessage) -> bool:
        if not self._session or not self._connected:
            return False

        try:
            # Send media attachments first (if any with data)
            for attachment in message.media:
                await self._send_media(message.thread_id, attachment)

            # Send text message
            if message.content:
                params: dict = {
                    "chat_id": message.thread_id,
                    "text": message.content,
                }
                if self._parse_mode:
                    params["parse_mode"] = self._parse_mode
                if message.reply_to_message_id:
                    params["reply_to_message_id"] = message.reply_to_message_id

                result = await self._api_call("sendMessage", params)
                if result is None:
                    return False

            return True
        except Exception as e:
            log.error(f"Telegram send_message error: {e}")
            return False

    async def _send_media(self, chat_id: str, attachment: MediaAttachment) -> None:
        """Send a single media attachment to a Telegram chat."""
        if not self._session or not attachment.data:
            return

        mime = attachment.mime_type or ""
        filename = attachment.filename or "file"

        # Choose the right Telegram method based on MIME type
        if mime.startswith("image/"):
            method = "sendPhoto"
            field = "photo"
        elif mime.startswith("audio/"):
            method = "sendAudio"
            field = "audio"
        elif mime.startswith("video/"):
            method = "sendVideo"
            field = "video"
        else:
            method = "sendDocument"
            field = "document"

        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field(field, attachment.data, filename=filename, content_type=mime)

        url = f"{self._api_base}/{method}"
        try:
            async with self._session.post(url, data=data) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.error(f"Telegram {method} failed: {resp.status} - {body}")
        except Exception as e:
            log.error(f"Telegram media send error: {e}")

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------

    async def handle_webhook(
        self, body: bytes, headers: dict
    ) -> Optional[IncomingMessage]:
        try:
            update = json.loads(body)
        except json.JSONDecodeError:
            log.error("Invalid JSON in Telegram webhook")
            return None

        return await self._parse_update(update)

    async def verify_webhook_signature(
        self, body: bytes, headers: dict
    ) -> bool:
        if not self._webhook_secret:
            return True

        # Telegram sends the secret in X-Telegram-Bot-Api-Secret-Token
        token = headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(token, self._webhook_secret)

    async def _setup_webhook(self) -> None:
        """Register the webhook URL with Telegram."""
        params: dict = {"url": self._webhook_url}
        if self._webhook_secret:
            params["secret_token"] = self._webhook_secret
        params["allowed_updates"] = json.dumps(["message", "edited_message"])

        result = await self._api_call("setWebhook", params)
        if result:
            log.info(f"Telegram webhook set: {self._webhook_url}")
        else:
            log.error("Failed to set Telegram webhook")

    # ------------------------------------------------------------------
    # Long-polling loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Background task that long-polls Telegram getUpdates."""
        log.info(
            f"Telegram poll loop started (timeout={self._poll_timeout}s)"
        )
        while not self._stop_event.is_set():
            try:
                params = {
                    "offset": self._update_offset,
                    "timeout": self._poll_timeout,
                    "allowed_updates": json.dumps(["message", "edited_message"]),
                }
                result = await self._api_call(
                    "getUpdates", params, timeout=self._poll_timeout + 10
                )
                if result is None:
                    # API error — back off briefly
                    await asyncio.sleep(5)
                    continue

                for update in result:
                    update_id = update.get("update_id", 0)
                    if update_id >= self._update_offset:
                        self._update_offset = update_id + 1

                    incoming = await self._parse_update(update)
                    if incoming and self._incoming_handler:
                        try:
                            await self._incoming_handler(incoming)
                        except Exception as e:
                            log.error(f"Error in incoming handler for Telegram: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Telegram poll error: {e}")
                await asyncio.sleep(5)

    # ------------------------------------------------------------------
    # Update parsing
    # ------------------------------------------------------------------

    async def _parse_update(self, update: dict) -> Optional[IncomingMessage]:
        """Parse a Telegram Update object into an IncomingMessage."""
        message = update.get("message") or update.get("edited_message")
        if not message:
            return None

        # Skip messages from the bot itself
        from_user = message.get("from", {})
        if self._bot_info and from_user.get("id") == self._bot_info.get("id"):
            return None

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        user_id = str(from_user.get("id", ""))
        is_group = chat.get("type") in ("group", "supergroup")

        # Build sender display name
        first = from_user.get("first_name", "")
        last = from_user.get("last_name", "")
        username = from_user.get("username", "")
        sender_name = f"{first} {last}".strip() or username or None

        # Extract text
        text = message.get("text", "") or message.get("caption", "")

        # Check bot mention in groups
        mentions_bot = False
        if is_group and self._bot_info:
            bot_username = self._bot_info.get("username", "")
            if bot_username:
                # Check entities for bot_command or mention
                for entity in message.get("entities", []):
                    if entity.get("type") == "mention":
                        offset = entity["offset"]
                        length = entity["length"]
                        mention_text = text[offset : offset + length]
                        if mention_text.lower() == f"@{bot_username.lower()}":
                            mentions_bot = True
                            break
                    elif entity.get("type") == "bot_command":
                        mentions_bot = True
                        break

                # Also match plain @username in text
                if not mentions_bot and f"@{bot_username.lower()}" in text.lower():
                    mentions_bot = True

        # Build media attachments
        media: list[MediaAttachment] = []
        media_types = [
            ("photo", True),
            ("document", False),
            ("audio", False),
            ("video", False),
            ("voice", False),
            ("video_note", False),
            ("sticker", False),
        ]
        for media_key, is_photo in media_types:
            media_obj = message.get(media_key)
            if not media_obj:
                continue

            if is_photo:
                # photo is a list of PhotoSize — pick the largest
                if isinstance(media_obj, list) and media_obj:
                    media_obj = media_obj[-1]

            file_id = media_obj.get("file_id")
            if file_id:
                mime_type = media_obj.get("mime_type", "application/octet-stream")
                if is_photo:
                    mime_type = "image/jpeg"
                elif media_key == "voice":
                    mime_type = media_obj.get("mime_type", "audio/ogg")
                elif media_key == "sticker":
                    mime_type = "image/webp" if not media_obj.get("is_animated") else "application/x-tgsticker"

                media.append(
                    MediaAttachment(
                        url=file_id,  # store file_id in url field for download_media
                        mime_type=mime_type,
                        filename=media_obj.get("file_name"),
                        size=media_obj.get("file_size"),
                    )
                )

        if not text and not media:
            return None

        return IncomingMessage(
            connection_id=self.connection_id,
            platform="telegram",
            external_thread_id=chat_id,
            external_user_id=user_id,
            external_user_name=sender_name,
            content=text,
            media=media,
            raw_event=update,
            is_group=is_group,
            mentions_bot=mentions_bot,
        )

    # ------------------------------------------------------------------
    # Media download
    # ------------------------------------------------------------------

    async def download_media(self, attachment: MediaAttachment) -> Optional[bytes]:
        """Download media via Telegram getFile API. attachment.url holds the file_id."""
        if not self._session:
            return None

        try:
            # Step 1: get file path
            file_info = await self._api_call("getFile", {"file_id": attachment.url})
            if not file_info:
                return None

            file_path = file_info.get("file_path")
            if not file_path:
                return None

            # Step 2: download file
            download_url = f"{TELEGRAM_API}/file/bot{self._bot_token}/{file_path}"
            async with self._session.get(download_url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    log.error(f"Telegram file download failed: {resp.status}")
        except Exception as e:
            log.error(f"Telegram media download error: {e}")
        return None

    # ------------------------------------------------------------------
    # API helper
    # ------------------------------------------------------------------

    async def _api_call(
        self, method: str, params: Optional[dict] = None, timeout: int = 30
    ) -> Optional[dict | list]:
        """Call a Telegram Bot API method. Returns the 'result' field or None on error."""
        if not self._session:
            return None

        url = f"{self._api_base}/{method}"
        try:
            client_timeout = aiohttp.ClientTimeout(total=timeout)
            async with self._session.post(
                url, json=params or {}, timeout=client_timeout
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                else:
                    description = data.get("description", "unknown error")
                    log.error(f"Telegram API {method} failed: {description}")
                    return None
        except asyncio.TimeoutError:
            # Expected for long-poll getUpdates when no updates arrive
            if method == "getUpdates":
                return []
            log.error(f"Telegram API {method} timeout")
            return None
        except Exception as e:
            log.error(f"Telegram API {method} error: {e}")
            return None

    # ------------------------------------------------------------------
    # Platform info
    # ------------------------------------------------------------------

    @classmethod
    def get_platform_info(cls) -> PlatformInfo:
        return PlatformInfo(
            platform="telegram",
            display_name="Telegram",
            description="Connect a Telegram bot via BotFather Bot API",
            supports_media=True,
            supports_groups=True,
            config_schema=[
                ConfigField(
                    name="bot_token",
                    label="Bot Token",
                    type="password",
                    required=True,
                    placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                ),
                ConfigField(
                    name="mode",
                    label="Update Mode",
                    type="select",
                    required=True,
                    default="polling",
                    options=[
                        {"value": "polling", "label": "Long Polling (no public URL needed)"},
                        {"value": "webhook", "label": "Webhook (requires public HTTPS URL)"},
                    ],
                ),
                ConfigField(
                    name="webhook_url",
                    label="Webhook URL",
                    type="url",
                    required=False,
                    placeholder="https://yourdomain.com/api/v1/bridges/webhook/telegram/...",
                ),
                ConfigField(
                    name="webhook_secret",
                    label="Webhook Secret",
                    type="password",
                    required=False,
                    placeholder="Secret token for webhook verification",
                ),
                ConfigField(
                    name="parse_mode",
                    label="Message Parse Mode",
                    type="select",
                    required=False,
                    default="",
                    options=[
                        {"value": "", "label": "Plain text"},
                        {"value": "Markdown", "label": "Markdown"},
                        {"value": "MarkdownV2", "label": "MarkdownV2"},
                        {"value": "HTML", "label": "HTML"},
                    ],
                ),
                ConfigField(
                    name="poll_timeout",
                    label="Poll Timeout (seconds)",
                    type="number",
                    required=False,
                    default="30",
                    placeholder="30",
                ),
            ],
        )
