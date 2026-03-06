import json
import logging
import time
from typing import Optional
import uuid

from sage_is_ai.internal.db import Base, get_db
from sage_is_ai.env import SRC_LOG_LEVELS

from sage_is_ai.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, func


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# UserGroup DB Schema
####################


class Group(Base):
    __tablename__ = "group"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    permissions = Column(JSON, nullable=True)
    user_ids = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GroupModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    permissions: Optional[dict] = None
    user_ids: list[str] = []

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class GroupResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    user_ids: list[str] = []
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None


class UserIdsForm(BaseModel):
    user_ids: Optional[list[str]] = None


class GroupUpdateForm(GroupForm, UserIdsForm):
    pass


class GroupTable:
    def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> Optional[GroupModel]:
        with get_db() as db:
            group = GroupModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Group(**group.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return GroupModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

    def get_groups(self) -> list[GroupModel]:
        with get_db() as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group).order_by(Group.updated_at.desc()).all()
            ]

    def get_groups_by_member_id(self, user_id: str) -> list[GroupModel]:
        with get_db() as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group)
                .filter(
                    func.json_array_length(Group.user_ids) > 0
                )  # Ensure array exists
                .filter(
                    Group.user_ids.cast(String).like(f'%"{user_id}"%')
                )  # String-based check
                .order_by(Group.updated_at.desc())
                .all()
            ]

    def get_group_by_id(self, id: str) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_group_user_ids_by_id(self, id: str) -> Optional[str]:
        group = self.get_group_by_id(id)
        if group:
            return group.user_ids
        else:
            return None

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_group_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_groups(self) -> bool:
        with get_db() as db:
            try:
                db.query(Group).delete()
                db.commit()

                return True
            except Exception:
                return False

    def get_facilitator_ids_by_group_id(self, id: str) -> list[str]:
        group = self.get_group_by_id(id)
        if group and group.meta:
            return group.meta.get("facilitator_ids", [])
        return []

    def add_facilitator_to_group(self, id: str, user_id: str) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                meta = group.meta or {}
                facilitator_ids = meta.get("facilitator_ids", [])
                if user_id not in facilitator_ids:
                    facilitator_ids.append(user_id)
                meta["facilitator_ids"] = facilitator_ids

                group.meta = meta
                group.updated_at = int(time.time())
                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)
        except Exception as e:
            log.exception(e)
            return None

    def remove_facilitator_from_group(
        self, id: str, user_id: str
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                meta = group.meta or {}
                facilitator_ids = meta.get("facilitator_ids", [])
                if user_id in facilitator_ids:
                    facilitator_ids.remove(user_id)
                meta["facilitator_ids"] = facilitator_ids

                group.meta = meta
                group.updated_at = int(time.time())
                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)
        except Exception as e:
            log.exception(e)
            return None

    def is_facilitator_of_group(self, user_id: str, group_id: str) -> bool:
        facilitator_ids = self.get_facilitator_ids_by_group_id(group_id)
        return user_id in facilitator_ids

    def has_admin_in_group(self, group_id: str) -> bool:
        from sage_is_ai.models.users import Users

        group = self.get_group_by_id(group_id)
        if not group or not group.user_ids:
            return False

        users = Users.get_users_by_user_ids(group.user_ids)
        return any(u.role == "admin" for u in users)

    def get_groups_where_facilitator(self, user_id: str) -> list[GroupModel]:
        with get_db() as db:
            all_groups = [
                GroupModel.model_validate(group)
                for group in db.query(Group).order_by(Group.updated_at.desc()).all()
            ]
            return [
                g
                for g in all_groups
                if g.meta and user_id in g.meta.get("facilitator_ids", [])
            ]

    def remove_user_from_all_groups(self, user_id: str) -> bool:
        with get_db() as db:
            try:
                groups = self.get_groups_by_member_id(user_id)

                for group in groups:
                    group.user_ids.remove(user_id)
                    db.query(Group).filter_by(id=group.id).update(
                        {
                            "user_ids": group.user_ids,
                            "updated_at": int(time.time()),
                        }
                    )
                    db.commit()

                return True
            except Exception:
                return False

    def create_groups_by_group_names(
        self, user_id: str, group_names: list[str]
    ) -> list[GroupModel]:

        # check for existing groups
        existing_groups = self.get_groups()
        existing_group_names = {group.name for group in existing_groups}

        new_groups = []

        with get_db() as db:
            for group_name in group_names:
                if group_name not in existing_group_names:
                    new_group = GroupModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=group_name,
                        description="",
                        created_at=int(time.time()),
                        updated_at=int(time.time()),
                    )
                    try:
                        result = Group(**new_group.model_dump())
                        db.add(result)
                        db.commit()
                        db.refresh(result)
                        new_groups.append(GroupModel.model_validate(result))
                    except Exception as e:
                        log.exception(e)
                        continue
            return new_groups

    def sync_groups_by_group_names(self, user_id: str, group_names: list[str]) -> bool:
        with get_db() as db:
            try:
                groups = db.query(Group).filter(Group.name.in_(group_names)).all()
                group_ids = [group.id for group in groups]

                # Remove user from groups not in the new list
                existing_groups = self.get_groups_by_member_id(user_id)

                for group in existing_groups:
                    if group.id not in group_ids:
                        group.user_ids.remove(user_id)
                        db.query(Group).filter_by(id=group.id).update(
                            {
                                "user_ids": group.user_ids,
                                "updated_at": int(time.time()),
                            }
                        )

                # Add user to new groups
                for group in groups:
                    if user_id not in group.user_ids:
                        group.user_ids.append(user_id)
                        db.query(Group).filter_by(id=group.id).update(
                            {
                                "user_ids": group.user_ids,
                                "updated_at": int(time.time()),
                            }
                        )

                db.commit()
                return True
            except Exception as e:
                log.exception(e)
                return False

    def add_users_to_group(
        self, id: str, user_ids: Optional[list[str]] = None
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                if not group.user_ids:
                    group.user_ids = []

                for user_id in user_ids:
                    if user_id not in group.user_ids:
                        group.user_ids.append(user_id)

                group.updated_at = int(time.time())
                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)
        except Exception as e:
            log.exception(e)
            return None

    def remove_users_from_group(
        self, id: str, user_ids: Optional[list[str]] = None
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                if not group.user_ids:
                    return GroupModel.model_validate(group)

                for user_id in user_ids:
                    if user_id in group.user_ids:
                        group.user_ids.remove(user_id)

                group.updated_at = int(time.time())
                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)
        except Exception as e:
            log.exception(e)
            return None


Groups = GroupTable()
