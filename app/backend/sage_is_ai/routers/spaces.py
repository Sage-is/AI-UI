import asyncio
import json
import logging
import re
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel


from sage_is_ai.socket.main import sio, get_user_ids_from_room, USER_POOL
from sage_is_ai.models.users import Users, UserNameResponse

from sage_is_ai.models.spaces import Spaces, SpaceModel, SpaceForm
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


def _check_space_access(user,space):
    """Check if a user has read access to a space. Raises 403 if not."""
    if user.role == "admin":
        return
    if has_access(user.id, type="read", access_control=space.access_control):
        return
    if user.role == "facilitator" and has_facilitator_access(
        user.id, type="read", access_control=space.access_control
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
    )

############################
# GetSpaces
############################


@router.get("/", response_model=list[SpaceModel])
async def get_spaces(user=Depends(get_verified_user)):
    return Spaces.get_spaces_by_user_id(user.id)


@router.get("/list", response_model=list[SpaceModel])
async def get_all_spaces(user=Depends(get_verified_user)):
    if user.role == "admin":
        return Spaces.get_spaces()
    return Spaces.get_spaces_by_user_id(user.id)


############################
# CreateNewSpace
############################


@router.post("/create", response_model=Optional[SpaceModel])
async def create_new_space(form_data: SpaceForm, user=Depends(get_admin_or_facilitator_user)):
    try:
        space = Spaces.insert_new_space(None, form_data, user.id)
        return SpaceModel(**space.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetSpaceById
############################


@router.get("/{id}", response_model=Optional[SpaceModel])
async def get_space_by_id(id: str, user=Depends(get_verified_user)):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    return SpaceModel(**space.model_dump())


############################
# UpdateSpaceById
############################


@router.post("/{id}/update", response_model=Optional[SpaceModel])
async def update_space_by_id(
    id: str, form_data: SpaceForm, user=Depends(get_admin_or_facilitator_user)
):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        space = Spaces.update_space_by_id(id, form_data)
        return SpaceModel(**space.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteSpaceById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_space_by_id(id: str, user=Depends(get_admin_or_facilitator_user)):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        Spaces.delete_space_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetSpaceParticipants
############################


@router.get("/{id}/participants")
async def get_space_participants(id: str, user=Depends(get_verified_user)):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    # Get users with read access
    if space.access_control:
        space_users = get_users_with_access("read", space.access_control)
    else:
        # No access control -- all users have access
        result = Users.get_users()
        space_users = result.get("users", []) if isinstance(result, dict) else result
    users_list = [
        UserNameResponse(**u.model_dump()).model_dump()
        for u in space_users
    ]

    # Get agents from space data
    agents = Spaces.get_space_agents(space)

    return {"users": users_list, "agents": agents}


############################
# GetSpaceMessages
############################


class MessageUserResponse(MessageResponse):
    user: UserNameResponse


@router.get("/{id}/messages", response_model=list[MessageUserResponse])
async def get_space_messages(
    id: str, skip: int = 0, limit: int = 50, user=Depends(get_verified_user)
):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message_list = Messages.get_messages_by_space_id(id, skip, limit)
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


async def send_notification(name, webui_url, space, message, active_user_ids):
    if space.access_control:
        users = get_users_with_access("read", space.access_control)
    else:
        result = Users.get_users()
        users = result.get("users", []) if isinstance(result, dict) else result

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
                        f"#{space.name} - {webui_url}/space/{space.id}\n\n{message.content}",
                        {
                            "action": "space",
                            "message": message.content,
                            "title": space.name,
                            "url": f"{webui_url}/space/{space.id}",
                        },
                    )


async def generate_agent_response(request, space, trigger_message, agent_config, trigger_user):
    """Generate an AI agent response when @mentioned in a space."""
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
            "space-events",
            {
                "space_id": space.id,
                "data": {
                    "type": "thinking",
                    "data": {"agent": agent_info, "thinking": True},
                },
            },
            to=f"space:{space.id}",
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
            # Handle StreamingResponse -- shouldn't happen with stream=False
            log.warning("Unexpected streaming response from agent completion")
            content = "I'm sorry, I couldn't generate a response."

        # Emit "thinking done"
        await sio.emit(
            "space-events",
            {
                "space_id": space.id,
                "data": {
                    "type": "thinking",
                    "data": {"agent": agent_info, "thinking": False},
                },
            },
            to=f"space:{space.id}",
        )

        if not content:
            return

        # Build agent message data. If the response ends with '?', mark it as
        # awaiting a reply from the triggering user — so they can respond without
        # having to @mention the agent again. Other users must still @mention.
        # TODO: Add optional per-agent TTL setting for deployments that want expiration.
        agent_data = {"agent": {**agent_info}}
        if content.strip().endswith("?"):
            agent_data["agent"]["awaiting_reply_from"] = trigger_user.id

        # Save agent message
        agent_message_form = MessageForm(
            content=content,
            parent_id=trigger_message.parent_id,
            data=agent_data,
        )
        agent_message = Messages.insert_new_message(
            agent_message_form, space.id, AGENT_USER_ID
        )

        if agent_message:
            agent_user = UserNameResponse(
                id=AGENT_USER_ID,
                name=agent_name,
                role="agent",
                profile_image_url=agent_profile_image,
            )

            await sio.emit(
                "space-events",
                {
                    "space_id": space.id,
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
                    "space": space.model_dump(),
                },
                to=f"space:{space.id}",
            )

    except Exception as e:
        log.exception(f"Error generating agent response: {e}")
        # Clear thinking indicator on error
        try:
            await sio.emit(
                "space-events",
                {
                    "space_id": space.id,
                    "data": {
                        "type": "thinking",
                        "data": {"agent": agent_config, "thinking": False},
                    },
                },
                to=f"space:{space.id}",
            )
        except Exception:
            pass


async def send_mention_notifications(app, space, message, mentions, sender_user):
    """Send targeted notifications to @mentioned users."""
    try:
        for mention_name in mentions:
            mentioned_user = Users.get_user_by_name(mention_name)
            if not mentioned_user:
                continue

            # Check if user has space access
            if mentioned_user.role != "admin" and not has_access(
                mentioned_user.id, type="read", access_control=space.access_control
            ):
                continue

            # Emit targeted socket notification
            for sid in USER_POOL.get(mentioned_user.id, []):
                await sio.emit(
                    "space-mention",
                    {
                        "space_id": space.id,
                        "space_name": space.name,
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
                        f"@{sender_user.name} mentioned you in #{space.name}\n\n{message.content}",
                        {
                            "action": "mention",
                            "message": message.content,
                            "title": f"#{space.name}",
                            "url": f"{webui_url}/space/{space.id}",
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
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    try:
        message = Messages.insert_new_message(form_data, space.id, user.id)

        if message:
            event_data = {
                "space_id": space.id,
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
                "space": space.model_dump(),
            }

            await sio.emit(
                "space-events",
                event_data,
                to=f"space:{space.id}",
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = Messages.get_message_by_id(message.parent_id)

                if parent_message:
                    await sio.emit(
                        "space-events",
                        {
                            "space_id": space.id,
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
                            "space": space.model_dump(),
                        },
                        to=f"space:{space.id}",
                    )

            active_user_ids = get_user_ids_from_room(f"space:{space.id}")

            background_tasks.add_task(
                send_notification,
                request.app.state.WEBUI_NAME,
                request.app.state.config.WEBUI_URL,
                space,
                message,
                active_user_ids,
            )

            # Forward to external bridges (skip if message originated from a bridge)
            if not (form_data.data and form_data.data.get("bridge")):
                from sage_is_ai.bridges.outgoing import forward_space_message_to_bridges

                background_tasks.add_task(
                    forward_space_message_to_bridges,
                    request.app,
                    space.id,
                    message.content,
                    user.id,
                    message.id,
                )

            # --- Agent auto-reply: if an agent's last response ended with '?',
            # the triggering user can reply without @mentioning the agent.
            # We only check the last 2 messages (not a deep scan) — if the agent's
            # question isn't recent, the user isn't directly responding to it.
            # Explicit @mentions always take priority over auto-reply.
            mentions = set(re.findall(r"@([\w][\w-]*)", message.content or ""))

            if not mentions:
                recent_msgs = Messages.get_messages_by_space_id(id, skip=0, limit=2)
                for recent_msg in recent_msgs:
                    # Only look at agent messages
                    if recent_msg.user_id != AGENT_USER_ID:
                        continue
                    agent_data = (recent_msg.data or {}).get("agent", {})
                    awaiting_user = agent_data.get("awaiting_reply_from")
                    if awaiting_user and awaiting_user == user.id:
                        # This user is responding to the agent's question — auto-trigger
                        agent_model_id = agent_data.get("model_id")
                        space_agents = Spaces.get_space_agents(space)
                        for agent_config in space_agents:
                            if agent_config.get("model_id") == agent_model_id:
                                asyncio.create_task(
                                    generate_agent_response(
                                        request, space, message, agent_config, user
                                    )
                                )
                                break
                        break  # Only trigger one auto-reply agent

            if mentions:
                # Trigger agent responses for @mentioned agents
                space_agents = Spaces.get_space_agents(space)
                lower_mentions = {m.lower() for m in mentions}
                for agent_config in space_agents:
                    agent_name_lower = agent_config.get("name", "").lower()
                    if (
                        agent_name_lower in lower_mentions
                        or agent_name_lower.replace(" ", "-") in lower_mentions
                    ):
                        asyncio.create_task(
                            generate_agent_response(
                                request,
                                space,
                                message,
                                agent_config,
                                user,
                            )
                        )

                # Send @user mention notifications
                background_tasks.add_task(
                    send_mention_notifications,
                    request.app,
                    space,
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
# GetSpaceMessage
############################


@router.get("/{id}/messages/{message_id}", response_model=Optional[MessageUserResponse])
async def get_space_message(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # NOTE: message.channel_id is a DB column name -- kept for backwards compatibility
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
# GetSpaceThreadMessages
############################


@router.get(
    "/{id}/messages/{message_id}/thread", response_model=list[MessageUserResponse]
)
async def get_space_thread_messages(
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

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
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # NOTE: message.channel_id is a DB column name -- kept for backwards compatibility
    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        message = Messages.update_message_by_id(message_id, form_data)
        message = Messages.get_message_by_id(message_id)

        if message:
            await sio.emit(
                "space-events",
                {
                    "space_id": space.id,
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
                    "space": space.model_dump(),
                },
                to=f"space:{space.id}",
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
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # NOTE: message.channel_id is a DB column name -- kept for backwards compatibility
    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.add_reaction_to_message(message_id, user.id, form_data.name)
        message = Messages.get_message_by_id(message_id)

        await sio.emit(
            "space-events",
            {
                "space_id": space.id,
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
                "space": space.model_dump(),
            },
            to=f"space:{space.id}",
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
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # NOTE: message.channel_id is a DB column name -- kept for backwards compatibility
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
            "space-events",
            {
                "space_id": space.id,
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
                "space": space.model_dump(),
            },
            to=f"space:{space.id}",
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
    space = Spaces.get_space_by_id(id)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    _check_space_access(user,space)

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # NOTE: message.channel_id is a DB column name -- kept for backwards compatibility
    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.delete_message_by_id(message_id)
        await sio.emit(
            "space-events",
            {
                "space_id": space.id,
                "message_id": message.id,
                "data": {
                    "type": "message:delete",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "space": space.model_dump(),
            },
            to=f"space:{space.id}",
        )

        if message.parent_id:
            # If this message is a reply, emit to the parent message as well
            parent_message = Messages.get_message_by_id(message.parent_id)

            if parent_message:
                await sio.emit(
                    "space-events",
                    {
                        "space_id": space.id,
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
                        "space": space.model_dump(),
                    },
                    to=f"space:{space.id}",
                )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
