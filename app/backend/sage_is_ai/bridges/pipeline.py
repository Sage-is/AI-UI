import logging
import time
import uuid
from collections import defaultdict
from typing import Optional

from starlette.requests import Request
from starlette.datastructures import Headers

from sage_is_ai.bridges.types import IncomingMessage, OutgoingMessage, BridgeMode
from sage_is_ai.models.bridges import (
    BridgeConnections,
    BridgeConnectionModel,
    BridgeThreads,
    BridgeThreadModel,
)
from sage_is_ai.models.auths import Auths
from sage_is_ai.models.users import Users, UserModel
from sage_is_ai.models.chats import Chats, ChatForm
from sage_is_ai.models.channels import Channels
from sage_is_ai.models.messages import Messages, MessageForm
from sage_is_ai.utils.auth import get_password_hash

log = logging.getLogger(__name__)

# In-memory rate limiter: {user_id: [timestamps]}
_rate_limits: dict[str, list[float]] = defaultdict(list)


class MessagePipeline:
    """Central message processing pipeline for bridge messages."""

    def __init__(self, app):
        self.app = app

    async def process_incoming(self, message: IncomingMessage) -> None:
        """Process an incoming message from an external platform."""
        connection = BridgeConnections.get_connection_by_id(message.connection_id)
        if not connection:
            log.error(f"Connection not found: {message.connection_id}")
            return

        if not connection.enabled:
            log.debug(f"Connection disabled, ignoring message: {connection.id}")
            return

        # Check allowlist
        if connection.allowed_ids and message.external_user_id not in connection.allowed_ids:
            log.info(f"User {message.external_user_id} not in allowlist for {connection.id}")
            return

        # Resolve or create Sage user
        user = await self._resolve_user(connection, message)
        if not user:
            log.info(f"User resolution failed for {message.external_user_id}")
            return

        # Rate limiting
        if not self._check_rate_limit(user.id):
            log.warning(f"Rate limit exceeded for user {user.id}")
            return

        if connection.mode == BridgeMode.AI_CHAT:
            await self._process_ai_chat(connection, message, user)
        elif connection.mode == BridgeMode.CHANNEL_BRIDGE:
            await self._process_channel_bridge(connection, message, user)

    async def _process_ai_chat(
        self,
        connection: BridgeConnectionModel,
        message: IncomingMessage,
        user: UserModel,
    ) -> None:
        """Process a message in AI chat mode — generate AI completion and respond."""
        from sage_is_ai.utils.chat import generate_chat_completion

        # Resolve/create thread and chat
        thread = self._resolve_thread(connection, message, user)

        # Create chat if new thread
        if not thread.sage_chat_id:
            chat = Chats.insert_new_chat(
                user_id=user.id,
                form_data=ChatForm(
                    chat={
                        "title": f"Bridge: {connection.name}",
                        "models": [connection.model_id or self._get_default_model()],
                        "history": {"messages": {}, "currentId": None},
                    }
                ),
            )
            if chat:
                thread = BridgeThreads.update_thread_by_id(
                    thread.id, sage_chat_id=chat.id
                )
        else:
            chat = Chats.get_chat_by_id(thread.sage_chat_id)

        if not chat:
            log.error("Failed to create/get chat for bridge thread")
            return

        # Download and store media
        file_ids = []
        if message.media:
            file_ids = await self._process_media(message, user)

        # Build user message
        user_msg_id = str(uuid.uuid4())
        user_msg = {
            "id": user_msg_id,
            "role": "user",
            "content": message.content,
            "timestamp": int(time.time()),
        }
        if file_ids:
            user_msg["files"] = [{"type": "file", "id": fid} for fid in file_ids]

        # Update chat history with user message
        Chats.upsert_message_to_chat_by_id_and_message_id(
            chat.id, user_msg_id, user_msg
        )

        # Build messages list from chat history
        updated_chat = Chats.get_chat_by_id(chat.id)
        history = updated_chat.chat.get("history", {}) if updated_chat else {}
        messages_list = self._build_messages_from_history(history)

        # Generate AI completion
        model_id = connection.model_id or self._get_default_model()
        form_data = {
            "model": model_id,
            "messages": messages_list,
            "stream": False,
        }

        try:
            # Build a mock request for generate_chat_completion
            mock_request = Request(
                scope={
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "method": "POST",
                    "path": "/api/chat/completions",
                    "query_string": b"",
                    "headers": Headers({}).raw,
                    "client": ("127.0.0.1", 0),
                    "server": ("127.0.0.1", 80),
                    "scheme": "http",
                    "app": self.app,
                }
            )

            response = await generate_chat_completion(
                request=mock_request,
                form_data=form_data,
                user=user,
                bypass_filter=True,
            )

            # Extract assistant response
            assistant_content = ""
            if hasattr(response, "body"):
                import json

                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                data = json.loads(body)
                if "choices" in data and data["choices"]:
                    assistant_content = (
                        data["choices"][0].get("message", {}).get("content", "")
                    )
            elif isinstance(response, dict):
                if "choices" in response and response["choices"]:
                    assistant_content = (
                        response["choices"][0].get("message", {}).get("content", "")
                    )

            if not assistant_content:
                log.warning("Empty AI response for bridge message")
                return

            # Save assistant message to chat
            assistant_msg_id = str(uuid.uuid4())
            assistant_msg = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": assistant_content,
                "timestamp": int(time.time()),
                "parentId": user_msg_id,
            }
            Chats.upsert_message_to_chat_by_id_and_message_id(
                chat.id, assistant_msg_id, assistant_msg
            )

            # Send response back to external platform
            from sage_is_ai.bridges.manager import BridgeManager

            bridge_manager = getattr(self.app.state, "bridge_manager", None)
            if bridge_manager:
                adapter = bridge_manager.get_adapter(connection.id)
                if adapter:
                    await adapter.send_message(
                        OutgoingMessage(
                            thread_id=message.external_thread_id,
                            content=assistant_content,
                        )
                    )

        except Exception as e:
            log.error(f"AI completion failed for bridge message: {e}")

    async def _process_channel_bridge(
        self,
        connection: BridgeConnectionModel,
        message: IncomingMessage,
        user: UserModel,
    ) -> None:
        """Process a message in channel bridge mode — post to Sage channel."""
        from sage_is_ai.socket.main import sio
        from sage_is_ai.models.users import UserNameResponse

        if not connection.channel_id:
            log.error(f"No channel_id configured for bridge {connection.id}")
            return

        channel = Channels.get_channel_by_id(connection.channel_id)
        if not channel:
            log.error(f"Channel not found: {connection.channel_id}")
            return

        # Create message in channel
        msg = Messages.insert_new_message(
            form_data=MessageForm(
                content=message.content,
                data={"bridge": {"platform": connection.platform, "connection_id": connection.id}},
            ),
            channel_id=channel.id,
            user_id=user.id,
        )

        if msg:
            # Emit to Socket.IO channel room
            event_data = {
                "channel_id": channel.id,
                "message_id": msg.id,
                "data": {
                    "type": "message",
                    "data": {
                        **msg.model_dump(),
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            }

            await sio.emit(
                "channel-events",
                event_data,
                to=f"channel:{channel.id}",
            )

        # If @sage mentioned, generate AI response
        if message.mentions_bot and message.content:
            await self._generate_channel_ai_response(connection, channel, message, user, msg)

    async def _generate_channel_ai_response(
        self, connection, channel, message, user, channel_msg
    ) -> None:
        """Generate an AI response in a channel when @sage is mentioned."""
        from sage_is_ai.utils.chat import generate_chat_completion
        from sage_is_ai.socket.main import sio
        from sage_is_ai.models.users import UserNameResponse

        model_id = connection.model_id or self._get_default_model()
        form_data = {
            "model": model_id,
            "messages": [{"role": "user", "content": message.content}],
            "stream": False,
        }

        try:
            mock_request = Request(
                scope={
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "method": "POST",
                    "path": "/api/chat/completions",
                    "query_string": b"",
                    "headers": Headers({}).raw,
                    "client": ("127.0.0.1", 0),
                    "server": ("127.0.0.1", 80),
                    "scheme": "http",
                    "app": self.app,
                }
            )

            response = await generate_chat_completion(
                request=mock_request,
                form_data=form_data,
                user=user,
                bypass_filter=True,
            )

            assistant_content = ""
            if hasattr(response, "body"):
                import json

                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                data = json.loads(body)
                if "choices" in data and data["choices"]:
                    assistant_content = (
                        data["choices"][0].get("message", {}).get("content", "")
                    )
            elif isinstance(response, dict):
                if "choices" in response and response["choices"]:
                    assistant_content = (
                        response["choices"][0].get("message", {}).get("content", "")
                    )

            if assistant_content:
                # Post AI response to channel
                ai_msg = Messages.insert_new_message(
                    form_data=MessageForm(
                        content=assistant_content,
                        parent_id=channel_msg.id if channel_msg else None,
                        data={"bridge": {"ai_response": True}},
                    ),
                    channel_id=channel.id,
                    user_id=user.id,
                )

                if ai_msg:
                    await sio.emit(
                        "channel-events",
                        {
                            "channel_id": channel.id,
                            "message_id": ai_msg.id,
                            "data": {
                                "type": "message",
                                "data": {
                                    **ai_msg.model_dump(),
                                    "user": UserNameResponse(
                                        **user.model_dump()
                                    ).model_dump(),
                                },
                            },
                            "user": UserNameResponse(**user.model_dump()).model_dump(),
                            "channel": channel.model_dump(),
                        },
                        to=f"channel:{channel.id}",
                    )

                # Send AI response back to external platform
                bridge_manager = getattr(self.app.state, "bridge_manager", None)
                if bridge_manager:
                    adapter = bridge_manager.get_adapter(connection.id)
                    if adapter:
                        await adapter.send_message(
                            OutgoingMessage(
                                thread_id=message.external_thread_id,
                                content=assistant_content,
                            )
                        )
        except Exception as e:
            log.error(f"Channel AI response failed: {e}")

    async def _resolve_user(
        self, connection: BridgeConnectionModel, message: IncomingMessage
    ) -> Optional[UserModel]:
        """Resolve external user to a Sage user, creating if needed."""
        oauth_sub = f"bridge:{connection.platform}:{message.external_user_id}"

        # Try existing user
        user = Users.get_user_by_oauth_sub(oauth_sub)
        if user:
            return user

        # Check provisioning policy
        if connection.user_provisioning == "disabled":
            return None
        if connection.user_provisioning == "pre_approved":
            if not connection.allowed_ids or message.external_user_id not in connection.allowed_ids:
                return None

        # Auto-create user
        default_role = getattr(
            self.app.state.config, "BRIDGE_DEFAULT_USER_ROLE", "user"
        )
        name = message.external_user_name or f"Bridge User ({message.external_user_id})"
        email = f"bridge_{connection.platform}_{message.external_user_id}@bridge.local"
        password = uuid.uuid4().hex

        try:
            hashed = get_password_hash(password)
            new_user = Auths.insert_new_auth(
                email=email,
                password=hashed,
                name=name,
                role=default_role,
                oauth_sub=oauth_sub,
            )

            if new_user:
                # Store bridge metadata
                info = new_user.info or {}
                info["bridge"] = {
                    "platform": connection.platform,
                    "external_id": message.external_user_id,
                    "connection_id": connection.id,
                }
                Users.update_user_by_id(new_user.id, {"info": info})
                log.info(f"Created bridge user: {name} ({oauth_sub})")
                return new_user

        except Exception as e:
            log.error(f"Failed to create bridge user: {e}")

        return None

    def _resolve_thread(
        self,
        connection: BridgeConnectionModel,
        message: IncomingMessage,
        user: UserModel,
    ) -> BridgeThreadModel:
        """Resolve or create a bridge thread."""
        thread = BridgeThreads.get_thread_by_external(
            connection.id, message.external_thread_id, message.external_user_id
        )
        if thread:
            return thread

        return BridgeThreads.insert_new_thread(
            connection_id=connection.id,
            external_thread_id=message.external_thread_id,
            external_user_id=message.external_user_id,
            sage_user_id=user.id,
            sage_channel_id=connection.channel_id,
        )

    def _build_messages_from_history(self, history: dict) -> list[dict]:
        """Convert chat history dict to ordered messages list."""
        messages_dict = history.get("messages", {})
        if not messages_dict:
            return []

        # Build ordered list by following parentId chain
        messages = list(messages_dict.values())
        messages.sort(key=lambda m: m.get("timestamp", 0))

        return [
            {"role": m["role"], "content": m.get("content", "")}
            for m in messages
            if m.get("role") in ("user", "assistant", "system") and m.get("content")
        ]

    async def _process_media(self, message: IncomingMessage, user: UserModel) -> list[str]:
        """Download media attachments and store them as files."""
        file_ids = []
        bridge_manager = getattr(self.app.state, "bridge_manager", None)
        if not bridge_manager:
            return file_ids

        adapter = bridge_manager.get_adapter(message.connection_id)
        if not adapter:
            return file_ids

        for attachment in message.media:
            try:
                data = await adapter.download_media(attachment)
                if data:
                    # Store via Files model if available
                    log.info(
                        f"Downloaded media: {attachment.filename or 'unnamed'} "
                        f"({len(data)} bytes)"
                    )
            except Exception as e:
                log.error(f"Failed to process media attachment: {e}")

        return file_ids

    def _get_default_model(self) -> str:
        """Get the default model for bridge AI chats."""
        return getattr(
            self.app.state.config, "BRIDGE_DEFAULT_MODEL", ""
        )

    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if a user is within rate limits."""
        limit = getattr(
            self.app.state.config, "BRIDGE_RATE_LIMIT_PER_MINUTE", 30
        )
        now = time.time()
        # Clean old entries
        _rate_limits[user_id] = [
            ts for ts in _rate_limits[user_id] if now - ts < 60
        ]
        if len(_rate_limits[user_id]) >= limit:
            return False
        _rate_limits[user_id].append(now)
        return True
