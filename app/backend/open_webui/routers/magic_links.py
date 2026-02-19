import datetime
import logging
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from open_webui.models.magic_links import (
    MagicLinks,
    MagicLinkForm,
    MagicLinkResponse,
    RedeemForm,
)
from open_webui.models.auths import Auths
from open_webui.models.users import Users
from open_webui.models.groups import Groups

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS

from open_webui.env import (
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
)
from open_webui.utils.auth import (
    create_token,
    get_admin_or_facilitator_user,
    get_password_hash,
)
from open_webui.utils.facilitator import can_facilitator_manage_group

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


############################
# Create Magic Link
############################


@router.post("/create", response_model=Optional[MagicLinkResponse])
async def create_magic_link(
    form_data: MagicLinkForm, user=Depends(get_admin_or_facilitator_user)
):
    # Facilitators can only create links for groups they facilitate
    if user.role == "facilitator" and form_data.group_ids:
        for group_id in form_data.group_ids:
            if not can_facilitator_manage_group(user.id, group_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not facilitate group {group_id}",
                )

    # Facilitators can only create temporary accounts
    if user.role == "facilitator" and form_data.role != "temporary":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Facilitators can only create temporary account links",
        )

    link = MagicLinks.create(user.id, form_data)
    if link:
        return link

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Error creating magic link",
    )


############################
# Get Magic Links
############################


@router.get("/", response_model=list[MagicLinkResponse])
async def get_magic_links(user=Depends(get_admin_or_facilitator_user)):
    if user.role == "admin":
        return MagicLinks.get_all()
    return MagicLinks.get_by_creator(user.id)


############################
# Get Magic Link by ID
############################


@router.get("/{id}", response_model=Optional[MagicLinkResponse])
async def get_magic_link_by_id(id: str, user=Depends(get_admin_or_facilitator_user)):
    link = MagicLinks.get_by_id(id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role != "admin" and link.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return link


############################
# Deactivate Magic Link
############################


@router.post("/{id}/deactivate", response_model=Optional[MagicLinkResponse])
async def deactivate_magic_link(
    id: str, user=Depends(get_admin_or_facilitator_user)
):
    link = MagicLinks.get_by_id(id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role != "admin" and link.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = MagicLinks.deactivate(id)
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Error deactivating magic link",
    )


############################
# Delete Magic Link
############################


@router.delete("/{id}", response_model=bool)
async def delete_magic_link(id: str, user=Depends(get_admin_or_facilitator_user)):
    link = MagicLinks.get_by_id(id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if user.role != "admin" and link.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return MagicLinks.delete(id)


############################
# Redeem Magic Link (Public)
############################


class RedeemResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str


@router.post("/redeem", response_model=RedeemResponse)
async def redeem_magic_link(response: Response, form_data: RedeemForm):
    link = MagicLinks.get_by_token(form_data.token)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid magic link",
        )

    if not link.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This magic link has been deactivated",
        )

    # Check link expiry
    if link.expires_at and int(time.time()) > link.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This magic link has expired",
        )

    # Check max uses
    if link.use_count >= link.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This magic link has reached its maximum number of uses",
        )

    # Create temporary user
    name = form_data.name or f"Guest_{link.use_count + 1}"
    email = f"temp_{uuid.uuid4().hex[:12]}@magic.local"
    password = uuid.uuid4().hex

    try:
        hashed = get_password_hash(password)
        new_user = Auths.insert_new_auth(
            email=email,
            password=hashed,
            name=name,
            role="temporary",
        )

        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating temporary account",
            )

        # Set temporary account info
        expires_at = None
        if link.account_duration:
            expires_at = int(time.time()) + link.account_duration

        info = new_user.info or {}
        info["temporary"] = {
            "expires_at": expires_at,
            "created_by": link.created_by,
            "magic_link_id": link.id,
        }
        Users.update_user_by_id(new_user.id, {"info": info})

        # Add user to groups
        if link.group_ids:
            for group_id in link.group_ids:
                Groups.add_users_to_group(group_id, [new_user.id])

        # Increment use count
        MagicLinks.increment_use_count(link.id)

        # Auto-deactivate if max uses reached
        if (link.use_count + 1) >= link.max_uses:
            MagicLinks.deactivate(link.id)

        # Fire webhook if configured
        if link.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        link.webhook_url,
                        json={
                            "event": "magic_link_redeemed",
                            "magic_link_id": link.id,
                            "user_id": new_user.id,
                            "user_name": name,
                            "user_email": email,
                            "group_ids": link.group_ids,
                            "created_by": link.created_by,
                            "timestamp": int(time.time()),
                        },
                        timeout=10,
                    )
            except Exception as e:
                log.warning(f"Webhook failed for magic link {link.id}: {e}")

        jwt_token = create_token(data={"id": new_user.id})

        # Set the cookie token (same as signin/signup)
        response.set_cookie(
            key="token",
            value=jwt_token,
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )

        return {
            "token": jwt_token,
            "token_type": "Bearer",
            "id": new_user.id,
            "email": email,
            "name": name,
            "role": "temporary",
            "profile_image_url": new_user.profile_image_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error redeeming magic link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while redeeming the magic link",
        )
