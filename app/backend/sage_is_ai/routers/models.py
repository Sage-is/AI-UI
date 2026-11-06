import logging
from typing import Optional

from sage_is_ai.env import SRC_LOG_LEVELS
from sage_is_ai.models.models import (
    ModelForm,
    ModelModel,
    ModelResponse,
    ModelUserResponse,
    Models,
)
from sage_is_ai.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status


from sage_is_ai.utils.auth import get_admin_user, get_verified_user
from sage_is_ai.utils.access_control import (
    has_access,
    has_facilitator_access,
    has_permission,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


async def _reindex(request: Request, user) -> None:
    """Rebuild app.state.MODELS after a write. The chat path finds a model only
    there, so a model made through this API answered "Model not found" until
    someone listed models (2026-11-02). Cheap: the base-models cache spares the
    provider probes. Every write route below ends here."""
    from sage_is_ai.utils.models import get_all_models  # lazy, as spaces.py does

    try:
        await get_all_models(request, user=user)
    except Exception as e:  # the write landed; a stale index must not fail it
        log.warning(
            f"model index refresh failed after a write: {type(e).__name__}: {e}"
        )


###########################
# GetModels
###########################


@router.get("/", response_model=list[ModelUserResponse])
async def get_models(id: Optional[str] = None, user=Depends(get_verified_user)):
    if user.role == "admin":
        return Models.get_models()
    elif user.role == "facilitator":
        all_models = Models.get_models()
        return [
            m
            for m in all_models
            if m.user_id == user.id
            or has_access(user.id, "write", m.access_control)
            or has_facilitator_access(user.id, "write", m.access_control)
        ]
    else:
        return Models.get_models_by_user_id(user.id)


###########################
# GetBaseModels
###########################


@router.get("/base", response_model=list[ModelResponse])
async def get_base_models(user=Depends(get_admin_user)):
    return Models.get_base_models()


############################
# CreateNewModel
############################


@router.post("/create", response_model=Optional[ModelModel])
async def create_new_model(
    request: Request,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    if user.role != "admin" and not has_permission(
        user.id, "workshop.models", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    model = Models.get_model_by_id(form_data.id)
    if model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.MODEL_ID_TAKEN,
        )

    else:
        model = Models.insert_new_model(form_data, user.id)
        if model:
            await _reindex(request, user)
            return model
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.DEFAULT(),
            )


###########################
# GetModelById
###########################


# Note: We're not using the typical url path param here, but instead using a query parameter to allow '/' in the id
@router.get("/model", response_model=Optional[ModelResponse])
async def get_model_by_id(id: str, user=Depends(get_verified_user)):
    model = Models.get_model_by_id(id)
    if model:
        if (
            user.role == "admin"
            or model.user_id == user.id
            or has_access(user.id, "read", model.access_control)
        ):
            return model
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# ToggelModelById
############################


@router.post("/model/toggle", response_model=Optional[ModelResponse])
async def toggle_model_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    model = Models.get_model_by_id(id)
    if model:
        if (
            user.role == "admin"
            or model.user_id == user.id
            or has_access(user.id, "write", model.access_control)
        ):
            model = Models.toggle_model_by_id(id)

            if model:
                await _reindex(request, user)
                return model
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error updating function"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateModelById
############################


@router.post("/model/update", response_model=Optional[ModelModel])
async def update_model_by_id(
    request: Request,
    id: str,
    form_data: ModelForm,
    user=Depends(get_verified_user),
):
    model = Models.get_model_by_id(id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    model = Models.update_model_by_id(id, form_data)
    await _reindex(request, user)
    return model


############################
# DeleteModelById
############################


@router.delete("/model/delete", response_model=bool)
async def delete_model_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    model = Models.get_model_by_id(id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and model.user_id != user.id
        and not has_access(user.id, "write", model.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Models.delete_model_by_id(id)
    await _reindex(request, user)
    return result


@router.delete("/delete/all", response_model=bool)
async def delete_all_models(request: Request, user=Depends(get_admin_user)):
    result = Models.delete_all_models()
    await _reindex(request, user)
    return result
