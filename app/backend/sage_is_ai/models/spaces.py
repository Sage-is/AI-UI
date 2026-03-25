import json
import time
import uuid
from typing import Optional

from sage_is_ai.internal.db import Base, get_db
from sage_is_ai.utils.access_control import has_access

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Space DB Schema
####################


class Channel(Base):
    # TODO(low): Rename DB table from "channel" to "space" via Alembic migration,
    # then rename this ORM class to Space and update __tablename__.
    __tablename__ = "channel"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    type = Column(Text, nullable=True)

    name = Column(Text)
    description = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class SpaceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: Optional[str] = None

    name: str
    description: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class SpaceForm(BaseModel):
    name: str
    description: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class SpaceTable:
    def insert_new_space(
        self, type: Optional[str], form_data: SpaceForm, user_id: str
    ) -> Optional[SpaceModel]:
        with get_db() as db:
            space = SpaceModel(
                **{
                    **form_data.model_dump(),
                    "type": type,
                    "name": form_data.name.lower(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_space = Channel(**space.model_dump())

            db.add(new_space)
            db.commit()
            return space

    def get_spaces(self) -> list[SpaceModel]:
        with get_db() as db:
            spaces = db.query(Channel).all()
            return [SpaceModel.model_validate(space) for space in spaces]

    def get_spaces_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[SpaceModel]:
        spaces = self.get_spaces()
        return [
            space
            for space in spaces
            if space.user_id == user_id
            or has_access(user_id, permission, space.access_control)
        ]

    def get_space_by_id(self, id: str) -> Optional[SpaceModel]:
        with get_db() as db:
            space = db.query(Channel).filter(Channel.id == id).first()
            return SpaceModel.model_validate(space) if space else None

    def update_space_by_id(
        self, id: str, form_data: SpaceForm
    ) -> Optional[SpaceModel]:
        with get_db() as db:
            space = db.query(Channel).filter(Channel.id == id).first()
            if not space:
                return None

            space.name = form_data.name
            space.data = form_data.data
            space.meta = form_data.meta
            space.access_control = form_data.access_control
            space.updated_at = int(time.time_ns())

            db.commit()
            return SpaceModel.model_validate(space) if space else None

    def delete_space_by_id(self, id: str):
        with get_db() as db:
            db.query(Channel).filter(Channel.id == id).delete()
            db.commit()
            return True


    def get_space_agents(self, space: SpaceModel) -> list[dict]:
        """Return the list of agent configs from a space's data field."""
        if space.data and isinstance(space.data, dict):
            return space.data.get("agents", [])
        return []


Spaces = SpaceTable()
