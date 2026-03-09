import logging

from sage_is_ai.models.chat_shares import (
    ChatShareForm,
    ChatShareResponse,
    ChatShares,
    SharedByMeResponse,
    SharedWithMeResponse,
)
from sage_is_ai.models.chats import Chats
from sage_is_ai.models.groups import Groups
from sage_is_ai.models.users import Users

from sage_is_ai.constants import ERROR_MESSAGES
from sage_is_ai.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, status

from sage_is_ai.utils.auth import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# ShareChatWithTargets
############################


@router.post("/{chat_id}/share/targets", response_model=list[ChatShareResponse])
async def share_chat_with_targets(
    chat_id: str,
    form_data: ChatShareForm,
    user=Depends(get_verified_user),
):
    # Only the chat owner can share
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    shares = ChatShares.share_chat(chat_id, user.id, form_data.targets)
    return _enrich_shares(shares)


############################
# GetChatShareTargets
############################


@router.get("/{chat_id}/share/targets", response_model=list[ChatShareResponse])
async def get_chat_share_targets(
    chat_id: str,
    user=Depends(get_verified_user),
):
    # Only the chat owner can view share targets
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    shares = ChatShares.get_shares_by_chat_id(chat_id)
    return _enrich_shares(shares)


############################
# RemoveChatShareTarget
############################


@router.delete("/{chat_id}/share/targets/{share_id}", response_model=bool)
async def remove_chat_share_target(
    chat_id: str,
    share_id: str,
    user=Depends(get_verified_user),
):
    # Only the chat owner can remove share targets
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return ChatShares.delete_share(share_id)


############################
# GetChatsSharedWithMe
############################


@router.get("/shared-with-me", response_model=list[SharedWithMeResponse])
async def get_chats_shared_with_me(
    user=Depends(get_verified_user),
):
    # Get user's group memberships
    groups = Groups.get_groups_by_member_id(user.id)
    group_ids = [g.id for g in groups]

    shares = ChatShares.get_chats_shared_with_user(user.id, group_ids)

    results = []
    seen_chat_ids = set()

    for share in shares:
        # Deduplicate: if shared via both user and group, show once
        effective_chat_id = share.snapshot_chat_id if share.share_mode == "snapshot" else share.chat_id
        if effective_chat_id in seen_chat_ids:
            continue
        seen_chat_ids.add(effective_chat_id)

        # Get chat data
        chat = Chats.get_chat_by_id(effective_chat_id)
        if not chat:
            continue

        # Get sharer info
        sharer = Users.get_user_by_id(share.shared_by)

        results.append(
            SharedWithMeResponse(
                share_id=share.id,
                chat_id=effective_chat_id,
                chat_title=chat.title,
                shared_by=share.shared_by,
                shared_by_name=sharer.name if sharer else None,
                share_mode=share.share_mode,
                snapshot_chat_id=share.snapshot_chat_id,
                created_at=share.created_at,
            )
        )

    return results


############################
# GetChatsSharedByMe
############################


@router.get("/shared-by-me", response_model=list[SharedByMeResponse])
async def get_chats_shared_by_me(
    user=Depends(get_verified_user),
):
    # 1. Get chats shared with specific people/groups
    shares = ChatShares.get_chats_shared_by_user(user.id)

    chat_shares_map = {}
    for share in shares:
        if share.chat_id not in chat_shares_map:
            chat_shares_map[share.chat_id] = {
                "count": 0,
                "created_at": share.created_at,
            }
        chat_shares_map[share.chat_id]["count"] += 1

    # 2. Get link-shared chats (those with share_id set)
    link_shared = Chats.get_link_shared_chats_by_user_id(user.id)

    results = []
    seen_chat_ids = set()

    # Add target-shared chats
    for cid, info in chat_shares_map.items():
        chat = Chats.get_chat_by_id(cid)
        if not chat:
            continue
        seen_chat_ids.add(cid)

        # Check if also link-shared
        has_link = chat.share_id is not None
        share_type = "both" if has_link else "targets"

        results.append(
            SharedByMeResponse(
                chat_id=cid,
                chat_title=chat.title,
                share_count=info["count"],
                share_type=share_type,
                share_id=chat.share_id,
                created_at=info["created_at"],
            )
        )

    # Add link-only shared chats (not already in target shares)
    for chat in link_shared:
        if chat.id in seen_chat_ids:
            continue
        results.append(
            SharedByMeResponse(
                chat_id=chat.id,
                chat_title=chat.title,
                share_count=0,
                share_type="link",
                share_id=chat.share_id,
                created_at=chat.updated_at,
            )
        )

    return results


############################
# Helpers
############################


def _enrich_shares(shares) -> list[ChatShareResponse]:
    """Add resolved names to share records."""
    results = []
    for share in shares:
        target_name = None
        shared_by_name = None

        if share.target_type == "user":
            target_user = Users.get_user_by_id(share.target_id)
            target_name = target_user.name if target_user else None
        elif share.target_type == "group":
            group = Groups.get_group_by_id(share.target_id)
            target_name = group.name if group else None

        sharer = Users.get_user_by_id(share.shared_by)
        shared_by_name = sharer.name if sharer else None

        results.append(
            ChatShareResponse(
                id=share.id,
                chat_id=share.chat_id,
                shared_by=share.shared_by,
                shared_by_name=shared_by_name,
                target_type=share.target_type,
                target_id=share.target_id,
                target_name=target_name,
                share_mode=share.share_mode,
                snapshot_chat_id=share.snapshot_chat_id,
                created_at=share.created_at,
            )
        )
    return results
