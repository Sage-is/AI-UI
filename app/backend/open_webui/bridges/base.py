import logging
from abc import ABC, abstractmethod
from typing import Optional

from open_webui.bridges.types import (
    IncomingMessage,
    OutgoingMessage,
    MediaAttachment,
    PlatformInfo,
)

log = logging.getLogger(__name__)


class MessageBridge(ABC):
    """Abstract base class for messaging platform adapters."""

    def __init__(self, connection_id: str, config: dict):
        self.connection_id = connection_id
        self.config = config
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """Initialize connection to the external platform.
        Returns True if successful."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly disconnect from the external platform."""
        ...

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send a message to the external platform.
        Returns True if successful."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the connection is healthy.
        Returns True if healthy."""
        ...

    @abstractmethod
    async def handle_webhook(self, body: bytes, headers: dict) -> Optional[IncomingMessage]:
        """Parse an incoming webhook request into an IncomingMessage.
        Returns None if the event should be ignored (e.g. status updates)."""
        ...

    @abstractmethod
    async def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        """Verify that the webhook request is authentic.
        Returns True if the signature is valid."""
        ...

    async def download_media(self, attachment: MediaAttachment) -> Optional[bytes]:
        """Download media from an attachment URL.
        Default implementation uses aiohttp. Override for platform-specific auth."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            log.error(f"Failed to download media: {e}")
        return None

    @classmethod
    @abstractmethod
    def get_platform_info(cls) -> PlatformInfo:
        """Return metadata about this platform adapter including config schema."""
        ...
