import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request

from sage_is_ai.models.folders import FolderForm, FolderModel, Folders
from sage_is_ai.models.chats import Chats
from sage_is_ai.constants import ERROR_MESSAGES
from sage_is_ai.utils.auth import get_verified_user
from sage_is_ai.utils.access_control import has_permission
from sage_is_ai.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])
router = APIRouter()

class FolderParentIdForm(BaseModel):
    parent_id: Optional[str] = None

class FolderIsExpandedForm(BaseModel):
    is_expanded: bool

def safe_execute(operation, error_msg: str, folder_id: str = ""):
    """Execute operation with unified error handling."""
    try:
        result = operation()
        if result is False:  # Handle explicit False returns
            raise Exception("Operation failed")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"{error_msg}: {folder_id}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, ERROR_MESSAGES.DEFAULT(error_msg))

def get_folder(folder_id: str, user_id: str) -> FolderModel:
    """Get folder or raise 404."""
    folder = Folders.get_folder_by_id_and_user_id(folder_id, user_id)
    if not folder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ERROR_MESSAGES.NOT_FOUND)
    return folder

def ensure_unique_name(parent_id: Optional[str], user_id: str, name: str, exclude_id: str = None):
    """Ensure folder name is unique in parent."""
    existing = Folders.get_folder_by_parent_id_and_user_id_and_name(parent_id, user_id, name)
    if existing and existing.id != exclude_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, ERROR_MESSAGES.DEFAULT("Folder already exists"))

def require_delete_permission(user, request: Request):
    """Require delete permission."""
    if user.role != "admin" and not has_permission(user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, ERROR_MESSAGES.ACCESS_PROHIBITED)

@router.get("/", response_model=list[FolderModel])
async def get_folders(user=Depends(get_verified_user)):
    folders = Folders.get_folders_by_user_id(user.id)
    return [{
        **folder.model_dump(),
        "items": {"chats": [{"title": c.title, "id": c.id, "updated_at": c.updated_at} 
                           for c in Chats.get_chats_by_folder_id_and_user_id(folder.id, user.id)]}
    } for folder in folders]

@router.post("/")
def create_folder(form_data: FolderForm, user=Depends(get_verified_user)):
    ensure_unique_name(None, user.id, form_data.name)
    return safe_execute(lambda: Folders.insert_new_folder(user.id, form_data), "Error creating folder")

@router.get("/{id}", response_model=Optional[FolderModel])
async def get_folder_by_id(id: str, user=Depends(get_verified_user)):
    return get_folder(id, user.id)

@router.post("/{id}/update")
async def update_folder_name(id: str, form_data: FolderForm, user=Depends(get_verified_user)):
    folder = get_folder(id, user.id)
    ensure_unique_name(folder.parent_id, user.id, form_data.name, id)
    return safe_execute(lambda: Folders.update_folder_by_id_and_user_id(id, user.id, form_data), "Error updating folder", id)

@router.post("/{id}/update/parent")
async def update_folder_parent(id: str, form_data: FolderParentIdForm, user=Depends(get_verified_user)):
    folder = get_folder(id, user.id)
    ensure_unique_name(form_data.parent_id, user.id, folder.name)
    return safe_execute(lambda: Folders.update_folder_parent_id_by_id_and_user_id(id, user.id, form_data.parent_id), "Error updating folder", id)

@router.post("/{id}/update/expanded")
async def update_folder_expanded(id: str, form_data: FolderIsExpandedForm, user=Depends(get_verified_user)):
    get_folder(id, user.id)  # Verify exists
    return safe_execute(lambda: Folders.update_folder_is_expanded_by_id_and_user_id(id, user.id, form_data.is_expanded), "Error updating folder", id)

@router.delete("/{id}")
async def delete_folder(request: Request, id: str, user=Depends(get_verified_user)):
    require_delete_permission(user, request)
    get_folder(id, user.id)
    return safe_execute(lambda: Folders.delete_folder_by_id_and_user_id(id, user.id), "Error deleting folder", id)