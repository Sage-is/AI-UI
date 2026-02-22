from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    SIGNAL = "signal"
    IRC = "irc"
    MATTERMOST = "mattermost"
    MATRIX = "matrix"
    GOOGLE_CHAT = "google_chat"


class BridgeMode(str, Enum):
    AI_CHAT = "ai_chat"
    CHANNEL_BRIDGE = "channel_bridge"


class UserProvisioning(str, Enum):
    AUTO_CREATE = "auto_create"
    PRE_APPROVED = "pre_approved"
    DISABLED = "disabled"


@dataclass
class MediaAttachment:
    url: str
    mime_type: str
    filename: Optional[str] = None
    size: Optional[int] = None
    data: Optional[bytes] = None  # downloaded content


@dataclass
class IncomingMessage:
    connection_id: str
    platform: str
    external_thread_id: str
    external_user_id: str
    external_user_name: Optional[str] = None
    content: str = ""
    media: list[MediaAttachment] = field(default_factory=list)
    raw_event: Optional[dict] = None
    is_group: bool = False
    mentions_bot: bool = False


@dataclass
class OutgoingMessage:
    thread_id: str  # external thread/chat ID
    content: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None


@dataclass
class ConfigField:
    name: str
    label: str
    type: str = "text"  # text, password, url, number, select
    required: bool = False
    default: Optional[str] = None
    placeholder: Optional[str] = None
    options: Optional[list[dict]] = None  # for select type


@dataclass
class PlatformInfo:
    platform: str
    display_name: str
    description: str
    config_schema: list[ConfigField]
    supports_media: bool = True
    supports_groups: bool = False
