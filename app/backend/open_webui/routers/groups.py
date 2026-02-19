import os
from pathlib import Path
from typing import Optional
import logging

from open_webui.models.users import Users
from open_webui.models.groups import (
    Groups,
    GroupForm,
    GroupUpdateForm,
    GroupResponse,
    UserIdsForm,
)

from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.utils.auth import (
    get_admin_user,
    get_verified_user,
    get_admin_or_facilitator_user,
)
from open_webui.utils.facilitator import (
    can_facilitator_manage_group,
    can_facilitator_change_permissions,
)
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

############################
# GetGroups
############################


@router.get("/", response_model=list[GroupResponse])
async def get_groups(user=Depends(get_verified_user)):
    if user.role == "admin":
        return Groups.get_groups()
    elif user.role == "facilitator":
        # Facilitators see groups they facilitate + groups they're members of
        member_groups = Groups.get_groups_by_member_id(user.id)
        facilitator_groups = Groups.get_groups_where_facilitator(user.id)
        seen_ids = set()
        combined = []
        for g in facilitator_groups + member_groups:
            if g.id not in seen_ids:
                seen_ids.add(g.id)
                combined.append(g)
        return combined
    else:
        return Groups.get_groups_by_member_id(user.id)


############################
# CreateNewGroup
############################


@router.post("/create", response_model=Optional[GroupResponse])
async def create_new_group(form_data: GroupForm, user=Depends(get_admin_user)):
    try:
        group = Groups.insert_new_group(user.id, form_data)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating group"),
            )
    except Exception as e:
        log.exception(f"Error creating a new group: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetGroupById
############################


@router.get("/id/{id}", response_model=Optional[GroupResponse])
async def get_group_by_id(id: str, user=Depends(get_admin_or_facilitator_user)):
    if user.role == "facilitator" and not can_facilitator_manage_group(user.id, id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    group = Groups.get_group_by_id(id)
    if group:
        return group
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateGroupById
############################


@router.post("/id/{id}/update", response_model=Optional[GroupResponse])
async def update_group_by_id(
    id: str, form_data: GroupUpdateForm, user=Depends(get_admin_or_facilitator_user)
):
    if user.role == "facilitator":
        if not can_facilitator_manage_group(user.id, id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
        # Facilitators cannot change permissions if admin is in group
        if form_data.permissions is not None:
            if not can_facilitator_change_permissions(user.id, id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot change permissions when an admin is in this group",
                )

    try:
        if form_data.user_ids:
            form_data.user_ids = Users.get_valid_user_ids(form_data.user_ids)

        group = Groups.update_group_by_id(id, form_data)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating group"),
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# AddUserToGroup
############################


@router.post("/id/{id}/users/add", response_model=Optional[GroupResponse])
async def add_user_to_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_or_facilitator_user)
):
    if user.role == "facilitator" and not can_facilitator_manage_group(user.id, id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        if form_data.user_ids:
            form_data.user_ids = Users.get_valid_user_ids(form_data.user_ids)

        group = Groups.add_users_to_group(id, form_data.user_ids)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error adding users to group"),
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error adding users to group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# RemoveUsersFromGroup
############################


@router.post("/id/{id}/users/remove", response_model=Optional[GroupResponse])
async def remove_users_from_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_or_facilitator_user)
):
    if user.role == "facilitator" and not can_facilitator_manage_group(user.id, id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        group = Groups.remove_users_from_group(id, form_data.user_ids)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error removing users from group"),
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error removing users from group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# DeleteGroupById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_group_by_id(id: str, user=Depends(get_admin_user)):
    try:
        result = Groups.delete_group_by_id(id)
        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting group"),
            )
    except Exception as e:
        log.exception(f"Error deleting group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Facilitator Management (admin-only)
############################


@router.post("/id/{id}/facilitators/add", response_model=Optional[GroupResponse])
async def add_facilitator_to_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_user)
):
    try:
        group = None
        if form_data.user_ids:
            for uid in form_data.user_ids:
                group = Groups.add_facilitator_to_group(id, uid)
        if group:
            return group
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error adding facilitator to group",
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error adding facilitator to group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/id/{id}/facilitators/remove", response_model=Optional[GroupResponse])
async def remove_facilitator_from_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_user)
):
    try:
        group = None
        if form_data.user_ids:
            for uid in form_data.user_ids:
                group = Groups.remove_facilitator_from_group(id, uid)
        if group:
            return group
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error removing facilitator from group",
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error removing facilitator from group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.get("/id/{id}/facilitators")
async def get_group_facilitators(id: str, user=Depends(get_admin_or_facilitator_user)):
    if user.role == "facilitator" and not can_facilitator_manage_group(user.id, id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    facilitator_ids = Groups.get_facilitator_ids_by_group_id(id)
    if facilitator_ids:
        return Users.get_users_by_user_ids(facilitator_ids)
    return []
