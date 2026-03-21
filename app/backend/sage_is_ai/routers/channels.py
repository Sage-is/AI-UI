import asyncio
import json
import logging
import re
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel


from sage_is_ai.socket.main import sio, get_user_ids_from_room, USER_POOL
from sage_is_ai.models.users import Users, UserNameResponse

from sage_is_ai.models.channels import Channels, ChannelModel, ChannelForm
from sage_is_ai.models.messages import (
    Messages,
    MessageModel,
    MessageResponse,
    MessageForm,
)


from sage_is_ai.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from sage_is_ai.constants import ERROR_MESSAGES
from sage_is_ai.env import SRC_LOG_LEVELS


from sage_is_ai.utils.auth import get_admin_user, get_verified_user, get_admin_or_facilitator_user
from sage_is_ai.utils.access_control import has_access, has_facilitator_access, get_users_with_access
from sage_is_ai.utils.facilitator import can_facilitator_manage_group
from sage_is_ai.utils.webhook import post_webhook

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

AGENT_USER_ID = "__agent__"


def _get_user_for_message(message) -> UserNameResponse:
    """Get the UserNameResponse for a message, handling agent messages."""
    if message.user_id == AGENT_USER_ID:
        agent_info = (message.data or {}).get("agent", {})
        return UserNameResponse(
            id=AGENT_USER_ID,
            name=agent_info.get("name", "Agent"),
            role="agent",
            profile_image_url=agent_info.get(
                "profile_image_url", "/static/icons/favicon.png"
            ),
        )
    user = Users.get_user_by_id(message.user_id)
    return UserNameResponse(**user.model_dump())


def _check_channel_access(user, channel):
    """Check if a user has read access to a channel. Raises 403 if not."""
    if user.role == "admin":
        return
    if has_access(user.id, type="read", access_control=channel.access_control):
        return
    if user.role == "facilitator" and has_facilitator_access(
        user.id, type="read", access_control=channel.access_control
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
    )

############################
# GetChatList
############################


@router.get("/", response_model=list[ChannelModel])
async def get_channels(user=Depends(get_verified_user)):
    return Channels.get_channels_by_user_id(user.id)


@router.get("/list", response_model=list[ChannelModel])
async def get_all_channels(user=Depends(get_verified_user)):
    if user.role == "admin":
        return Channels.get_channels()
    return Channels.get_channels_by_user_id(user.id)


############################
# CreateNewChannel
############################


@router.post("/create", response_model=Optional[ChannelModel])
async def create_new_channel(form_data: ChannelForm, user=Depends(get_admin_or_facilitator_user)):
    try:
        channel = Channels.insert_new_channel(None, form_data, user.id)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelById
############################


@router.get("/{id}", response_model=Optional[ChannelModel])
async def get_channel_by_id(id: str, user=Depends(get_verified_user)):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    return ChannelModel(**channel.model_dump())


############################
# UpdateChannelById
############################


@router.post("/{id}/update", response_model=Optional[ChannelModel])
async def update_channel_by_id(
    id: str, form_data: ChannelForm, user=Depends(get_admin_or_facilitator_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        channel = Channels.update_channel_by_id(id, form_data)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChannelById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_channel_by_id(id: str, user=Depends(get_admin_or_facilitator_user)):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        Channels.delete_channel_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelParticipants
############################


@router.get("/{id}/participants")
async def get_channel_participants(id: str, user=Depends(get_verified_user)):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    # Get users with read access
    if channel.access_control:
        channel_users = get_users_with_access("read", channel.access_control)
    else:
        # No access control — all users have access
        result = Users.get_users()
        channel_users = result.users if hasattr(result, "users") else result
    users_list = [
        UserNameResponse(**u.model_dump()).model_dump()
        for u in channel_users
    ]

    # Get agents from channel data
    agents = Channels.get_channel_agents(channel)

    return {"users": users_list, "agents": agents}


############################
# GetChannelMessages
############################


class MessageUserResponse(MessageResponse):
    user: UserNameResponse


@router.get("/{id}/messages", response_model=list[MessageUserResponse])
async def get_channel_messages(
    id: str, skip: int = 0, limit: int = 50, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message_list = Messages.get_messages_by_channel_id(id, skip, limit)
    user_cache = {}

    messages = []
    for message in message_list:
        if message.user_id == AGENT_USER_ID:
            msg_user = _get_user_for_message(message)
        else:
            if message.user_id not in user_cache:
                user_cache[message.user_id] = _get_user_for_message(message)
            msg_user = user_cache[message.user_id]

        replies = Messages.get_replies_by_message_id(message.id)
        latest_reply_at = replies[0].created_at if replies else None

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": len(replies),
                    "latest_reply_at": latest_reply_at,
                    "reactions": Messages.get_reactions_by_message_id(message.id),
                    "user": msg_user,
                }
            )
        )

    return messages


############################
# PostNewMessage
############################


async def send_notification(name, webui_url, channel, message, active_user_ids):
    if channel.access_control:
        users = get_users_with_access("read", channel.access_control)
    else:
        result = Users.get_users()
        users = result.users if hasattr(result, "users") else result

    for user in users:
        if user.id in active_user_ids:
            continue
        else:
            if user.settings:
                webhook_url = user.settings.ui.get("notifications", {}).get(
                    "webhook_url", None
                )

                if webhook_url:
                    post_webhook(
                        name,
                        webhook_url,
                        f"#{channel.name} - {webui_url}/channels/{channel.id}\n\n{message.content}",
                        {
                            "action": "channel",
                            "message": message.content,
                            "title": channel.name,
                            "url": f"{webui_url}/channels/{channel.id}",
                        },
                    )


async def generate_agent_response(request, channel, trigger_message, agent_config, trigger_user):
    """Generate an AI agent response when @mentioned in a channel."""
    try:
        app = request.app
        model_id = agent_config.get("model_id")

        # Ensure models are loaded (may be empty on cold start)
        if not app.state.MODELS:
            from sage_is_ai.utils.models import get_all_models
            await get_all_models(request, user=trigger_user)

        if not model_id or model_id not in app.state.MODELS:
            log.warning(f"Agent model '{model_id}' not found in MODELS")
            return

        model = app.state.MODELS[model_id]
        agent_name = agent_config.get("name", model.get("name", "Agent"))
        agent_profile_image = agent_config.get(
            "profile_image_url",
            model.get("info", {}).get("meta", {}).get(
                "profile_image_url", "/static/icons/favicon.png"
            ),
        )
        agent_info = {
            "model_id": model_id,
            "name": agent_name,
            "profile_image_url": agent_profile_image,
        }

        # Emit "thinking" indicator
        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "data": {
                    "type": "thinking",
                    "data": {"agent": agent_info, "thinking": True},
                },
            },
            to=f"channel:{channel.id}",
        )

        # Build messages for the model
        system_prompt = model.get("info", {}).get("params", {}).get("system", "")
        llm_messages = []
        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        llm_messages.append({"role": "user", "content": trigger_message.content})

        form_data = {
            "model": model_id,
            "messages": llm_messages,
            "stream": False,
        }

        # Call the chat completion
        from sage_is_ai.utils.chat import generate_chat_completion

        response = await generate_chat_completion(
            request, form_data, user=trigger_user, bypass_filter=True
        )

        # Extract response content
        if isinstance(response, dict):
            content = (
                response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        else:
            # Handle StreamingResponse — shouldn't happen with stream=False
            log.warning("Unexpected streaming response from agent completion")
            content = "I'm sorry, I couldn't generate a response."

        # Emit "thinking done"
        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "data": {
                    "type": "thinking",
                    "data": {"agent": agent_info, "thinking": False},
                },
            },
            to=f"channel:{channel.id}",
        )

        if not content:
            return

        # Save agent message
        agent_message_form = MessageForm(
            content=content,
            parent_id=trigger_message.parent_id,
            data={"agent": agent_info},
        )
        agent_message = Messages.insert_new_message(
            agent_message_form, channel.id, AGENT_USER_ID
        )

        if agent_message:
            agent_user = UserNameResponse(
                id=AGENT_USER_ID,
                name=agent_name,
                role="agent",
                profile_image_url=agent_profile_image,
            )

            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "message_id": agent_message.id,
                    "data": {
                        "type": "message",
                        "data": MessageUserResponse(
                            **{
                                **agent_message.model_dump(),
                                "reply_count": 0,
                                "latest_reply_at": None,
                                "reactions": [],
                                "user": agent_user,
                            }
                        ).model_dump(),
                    },
                    "user": agent_user.model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )

    except Exception as e:
        log.exception(f"Error generating agent response: {e}")
        # Clear thinking indicator on error
        try:
            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "data": {
                        "type": "thinking",
                        "data": {"agent": agent_config, "thinking": False},
                    },
                },
                to=f"channel:{channel.id}",
            )
        except Exception:
            pass


async def send_mention_notifications(app, channel, message, mentions, sender_user):
    """Send targeted notifications to @mentioned users."""
    try:
        for mention_name in mentions:
            mentioned_user = Users.get_user_by_name(mention_name)
            if not mentioned_user:
                continue

            # Check if user has channel access
            if mentioned_user.role != "admin" and not has_access(
                mentioned_user.id, type="read", access_control=channel.access_control
            ):
                continue

            # Emit targeted socket notification
            for sid in USER_POOL.get(mentioned_user.id, []):
                await sio.emit(
                    "channel-mention",
                    {
                        "channel_id": channel.id,
                        "channel_name": channel.name,
                        "message": message.content,
                        "user": UserNameResponse(
                            **sender_user.model_dump()
                        ).model_dump(),
                    },
                    to=sid,
                )

            # Send webhook notification if configured
            if mentioned_user.settings:
                webhook_url = (
                    mentioned_user.settings.ui.get("notifications", {}).get(
                        "webhook_url", None
                    )
                )
                if webhook_url:
                    webui_url = app.state.config.WEBUI_URL
                    post_webhook(
                        app.state.WEBUI_NAME,
                        webhook_url,
                        f"@{sender_user.name} mentioned you in #{channel.name}\n\n{message.content}",
                        {
                            "action": "mention",
                            "message": message.content,
                            "title": f"#{channel.name}",
                            "url": f"{webui_url}/channels/{channel.id}",
                        },
                    )
    except Exception as e:
        log.exception(f"Error sending mention notifications: {e}")


@router.post("/{id}/messages/post", response_model=Optional[MessageModel])
async def post_new_message(
    request: Request,
    id: str,
    form_data: MessageForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    try:
        message = Messages.insert_new_message(form_data, channel.id, user.id)

        if message:
            event_data = {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message",
                    "data": MessageUserResponse(
                        **{
                            **message.model_dump(),
                            "reply_count": 0,
                            "latest_reply_at": None,
                            "reactions": Messages.get_reactions_by_message_id(
                                message.id
                            ),
                            "user": UserNameResponse(**user.model_dump()),
                        }
                    ).model_dump(),
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            }

            await sio.emit(
                "channel-events",
                event_data,
                to=f"channel:{channel.id}",
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = Messages.get_message_by_id(message.parent_id)

                if parent_message:
                    await sio.emit(
                        "channel-events",
                        {
                            "channel_id": channel.id,
                            "message_id": parent_message.id,
                            "data": {
                                "type": "message:reply",
                                "data": MessageUserResponse(
                                    **{
                                        **parent_message.model_dump(),
                                        "user": _get_user_for_message(parent_message),
                                    }
                                ).model_dump(),
                            },
                            "user": UserNameResponse(**user.model_dump()).model_dump(),
                            "channel": channel.model_dump(),
                        },
                        to=f"channel:{channel.id}",
                    )

            active_user_ids = get_user_ids_from_room(f"channel:{channel.id}")

            background_tasks.add_task(
                send_notification,
                request.app.state.WEBUI_NAME,
                request.app.state.config.WEBUI_URL,
                channel,
                message,
                active_user_ids,
            )

            # Forward to external bridges (skip if message originated from a bridge)
            if not (form_data.data and form_data.data.get("bridge")):
                from sage_is_ai.bridges.outgoing import forward_channel_message_to_bridges

                background_tasks.add_task(
                    forward_channel_message_to_bridges,
                    request.app,
                    channel.id,
                    message.content,
                    user.id,
                    message.id,
                )

            # Parse @mentions from message content
            mentions = set(re.findall(r"@([\w][\w-]*)", message.content or ""))

            if mentions:
                # Trigger agent responses for @mentioned agents
                channel_agents = Channels.get_channel_agents(channel)
                lower_mentions = {m.lower() for m in mentions}
                for agent_config in channel_agents:
                    agent_name_lower = agent_config.get("name", "").lower()
                    if (
                        agent_name_lower in lower_mentions
                        or agent_name_lower.replace(" ", "-") in lower_mentions
                    ):
                        asyncio.create_task(
                            generate_agent_response(
                                request,
                                channel,
                                message,
                                agent_config,
                                user,
                            )
                        )

                # Send @user mention notifications
                background_tasks.add_task(
                    send_mention_notifications,
                    request.app,
                    channel,
                    message,
                    mentions,
                    user,
                )

        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelMessage
############################


@router.get("/{id}/messages/{message_id}", response_model=Optional[MessageUserResponse])
async def get_channel_message(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return MessageUserResponse(
        **{
            **message.model_dump(),
            "user": _get_user_for_message(message),
        }
    )


############################
# GetChannelThreadMessages
############################


@router.get(
    "/{id}/messages/{message_id}/thread", response_model=list[MessageUserResponse]
)
async def get_channel_thread_messages(
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message_list = Messages.get_messages_by_parent_id(id, message_id, skip, limit)
    user_cache = {}

    messages = []
    for message in message_list:
        if message.user_id == AGENT_USER_ID:
            msg_user = _get_user_for_message(message)
        else:
            if message.user_id not in user_cache:
                user_cache[message.user_id] = _get_user_for_message(message)
            msg_user = user_cache[message.user_id]

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": 0,
                    "latest_reply_at": None,
                    "reactions": Messages.get_reactions_by_message_id(message.id),
                    "user": msg_user,
                }
            )
        )

    return messages


############################
# UpdateMessageById
############################


@router.post(
    "/{id}/messages/{message_id}/update", response_model=Optional[MessageModel]
)
async def update_message_by_id(
    id: str, message_id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        message = Messages.update_message_by_id(message_id, form_data)
        message = Messages.get_message_by_id(message_id)

        if message:
            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "data": {
                        "type": "message:update",
                        "data": MessageUserResponse(
                            **{
                                **message.model_dump(),
                                "user": UserNameResponse(
                                    **user.model_dump()
                                ).model_dump(),
                            }
                        ).model_dump(),
                    },
                    "user": UserNameResponse(**user.model_dump()).model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )

        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# AddReactionToMessage
############################


class ReactionForm(BaseModel):
    name: str


@router.post("/{id}/messages/{message_id}/reactions/add", response_model=bool)
async def add_reaction_to_message(
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.add_reaction_to_message(message_id, user.id, form_data.name)
        message = Messages.get_message_by_id(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:add",
                    "data": {
                        **message.model_dump(),
                        "user": _get_user_for_message(message).model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# RemoveReactionById
############################


@router.post("/{id}/messages/{message_id}/reactions/remove", response_model=bool)
async def remove_reaction_by_id_and_user_id_and_name(
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.remove_reaction_by_id_and_user_id_and_name(
            message_id, user.id, form_data.name
        )

        message = Messages.get_message_by_id(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:remove",
                    "data": {
                        **message.model_dump(),
                        "user": _get_user_for_message(message).model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteMessageById
############################


@router.delete("/{id}/messages/{message_id}/delete", response_model=bool)
async def delete_message_by_id(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_channel_access(user, channel)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.delete_message_by_id(message_id)
        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:delete",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        if message.parent_id:
            # If this message is a reply, emit to the parent message as well
            parent_message = Messages.get_message_by_id(message.parent_id)

            if parent_message:
                await sio.emit(
                    "channel-events",
                    {
                        "channel_id": channel.id,
                        "message_id": parent_message.id,
                        "data": {
                            "type": "message:reply",
                            "data": MessageUserResponse(
                                **{
                                    **parent_message.model_dump(),
                                    "user": UserNameResponse(
                                        **Users.get_user_by_id(
                                            parent_message.user_id
                                        ).model_dump()
                                    ),
                                }
                            ).model_dump(),
                        },
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                        "channel": channel.model_dump(),
                    },
                    to=f"channel:{channel.id}",
                )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
