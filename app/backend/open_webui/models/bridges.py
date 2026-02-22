import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Text, JSON, UniqueConstraint


####################
# BridgeConnection DB Schema
####################


class BridgeConnection(Base):
    __tablename__ = "bridge_connection"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)  # admin who created it
    platform = Column(Text, nullable=False)  # "whatsapp", "telegram", etc.
    name = Column(Text, nullable=False)  # human label
    mode = Column(Text, nullable=False)  # "ai_chat" | "channel_bridge"

    config = Column(JSON, nullable=False)  # platform-specific config
    channel_id = Column(Text, nullable=True)  # linked Sage channel (channel_bridge mode)
    model_id = Column(Text, nullable=True)  # default AI model (ai_chat mode)

    user_provisioning = Column(Text, default="auto_create")  # auto_create | pre_approved | disabled
    allowed_ids = Column(JSON, nullable=True)  # phone/user allowlist
    enabled = Column(Boolean, default=True)

    status = Column(Text, default="disconnected")  # connected/disconnected/error/starting
    status_message = Column(Text, nullable=True)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class BridgeThread(Base):
    __tablename__ = "bridge_thread"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_thread_id", "external_user_id",
            name="uq_bridge_thread_conn_ext"
        ),
    )

    id = Column(Text, primary_key=True)
    connection_id = Column(Text, nullable=False)
    external_thread_id = Column(Text, nullable=False)  # platform chat/channel ID
    external_user_id = Column(Text, nullable=False)  # platform user identifier

    sage_user_id = Column(Text, nullable=True)  # mapped Sage User.id
    sage_chat_id = Column(Text, nullable=True)  # Chat.id (ai_chat mode)
    sage_channel_id = Column(Text, nullable=True)  # Channel.id (channel_bridge mode)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic Models
####################


class BridgeConnectionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    platform: str
    name: str
    mode: str

    config: dict
    channel_id: Optional[str] = None
    model_id: Optional[str] = None

    user_provisioning: str = "auto_create"
    allowed_ids: Optional[list] = None
    enabled: bool = True

    status: str = "disconnected"
    status_message: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class BridgeThreadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    connection_id: str
    external_thread_id: str
    external_user_id: str

    sage_user_id: Optional[str] = None
    sage_chat_id: Optional[str] = None
    sage_channel_id: Optional[str] = None

    data: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class BridgeConnectionForm(BaseModel):
    platform: str
    name: str
    mode: str
    config: dict
    channel_id: Optional[str] = None
    model_id: Optional[str] = None
    user_provisioning: str = "auto_create"
    allowed_ids: Optional[list] = None
    enabled: bool = True
    data: Optional[dict] = None
    meta: Optional[dict] = None


class BridgeConnectionUpdateForm(BaseModel):
    name: Optional[str] = None
    mode: Optional[str] = None
    config: Optional[dict] = None
    channel_id: Optional[str] = None
    model_id: Optional[str] = None
    user_provisioning: Optional[str] = None
    allowed_ids: Optional[list] = None
    enabled: Optional[bool] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None


####################
# Table Classes
####################


class BridgeConnectionTable:
    def insert_new_connection(
        self, form_data: BridgeConnectionForm, user_id: str
    ) -> Optional[BridgeConnectionModel]:
        with get_db() as db:
            connection = BridgeConnectionModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "status": "disconnected",
                    "status_message": None,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )
            new_conn = BridgeConnection(**connection.model_dump())
            db.add(new_conn)
            db.commit()
            return connection

    def get_connections(self) -> list[BridgeConnectionModel]:
        with get_db() as db:
            connections = db.query(BridgeConnection).all()
            return [BridgeConnectionModel.model_validate(c) for c in connections]

    def get_connection_by_id(self, id: str) -> Optional[BridgeConnectionModel]:
        with get_db() as db:
            conn = db.query(BridgeConnection).filter(BridgeConnection.id == id).first()
            return BridgeConnectionModel.model_validate(conn) if conn else None

    def get_connections_by_platform(self, platform: str) -> list[BridgeConnectionModel]:
        with get_db() as db:
            connections = (
                db.query(BridgeConnection)
                .filter(BridgeConnection.platform == platform)
                .all()
            )
            return [BridgeConnectionModel.model_validate(c) for c in connections]

    def get_enabled_connections(self) -> list[BridgeConnectionModel]:
        with get_db() as db:
            connections = (
                db.query(BridgeConnection)
                .filter(BridgeConnection.enabled == True)
                .all()
            )
            return [BridgeConnectionModel.model_validate(c) for c in connections]

    def update_connection_by_id(
        self, id: str, form_data: BridgeConnectionUpdateForm
    ) -> Optional[BridgeConnectionModel]:
        with get_db() as db:
            conn = db.query(BridgeConnection).filter(BridgeConnection.id == id).first()
            if not conn:
                return None

            update_data = form_data.model_dump(exclude_none=True)
            for key, value in update_data.items():
                setattr(conn, key, value)
            conn.updated_at = int(time.time_ns())

            db.commit()
            return BridgeConnectionModel.model_validate(conn)

    def update_connection_status(
        self, id: str, status: str, status_message: Optional[str] = None
    ) -> Optional[BridgeConnectionModel]:
        with get_db() as db:
            conn = db.query(BridgeConnection).filter(BridgeConnection.id == id).first()
            if not conn:
                return None

            conn.status = status
            conn.status_message = status_message
            conn.updated_at = int(time.time_ns())

            db.commit()
            return BridgeConnectionModel.model_validate(conn)

    def toggle_connection_by_id(self, id: str) -> Optional[BridgeConnectionModel]:
        with get_db() as db:
            conn = db.query(BridgeConnection).filter(BridgeConnection.id == id).first()
            if not conn:
                return None

            conn.enabled = not conn.enabled
            conn.updated_at = int(time.time_ns())

            db.commit()
            return BridgeConnectionModel.model_validate(conn)

    def delete_connection_by_id(self, id: str) -> bool:
        with get_db() as db:
            db.query(BridgeConnection).filter(BridgeConnection.id == id).delete()
            db.commit()
            return True


class BridgeThreadTable:
    def insert_new_thread(
        self,
        connection_id: str,
        external_thread_id: str,
        external_user_id: str,
        sage_user_id: Optional[str] = None,
        sage_chat_id: Optional[str] = None,
        sage_channel_id: Optional[str] = None,
        data: Optional[dict] = None,
        meta: Optional[dict] = None,
    ) -> Optional[BridgeThreadModel]:
        with get_db() as db:
            thread = BridgeThreadModel(
                id=str(uuid.uuid4()),
                connection_id=connection_id,
                external_thread_id=external_thread_id,
                external_user_id=external_user_id,
                sage_user_id=sage_user_id,
                sage_chat_id=sage_chat_id,
                sage_channel_id=sage_channel_id,
                data=data,
                meta=meta,
                created_at=int(time.time_ns()),
                updated_at=int(time.time_ns()),
            )
            new_thread = BridgeThread(**thread.model_dump())
            db.add(new_thread)
            db.commit()
            return thread

    def get_thread_by_id(self, id: str) -> Optional[BridgeThreadModel]:
        with get_db() as db:
            thread = db.query(BridgeThread).filter(BridgeThread.id == id).first()
            return BridgeThreadModel.model_validate(thread) if thread else None

    def get_thread_by_external(
        self, connection_id: str, external_thread_id: str, external_user_id: str
    ) -> Optional[BridgeThreadModel]:
        with get_db() as db:
            thread = (
                db.query(BridgeThread)
                .filter(
                    BridgeThread.connection_id == connection_id,
                    BridgeThread.external_thread_id == external_thread_id,
                    BridgeThread.external_user_id == external_user_id,
                )
                .first()
            )
            return BridgeThreadModel.model_validate(thread) if thread else None

    def get_threads_by_connection_id(
        self, connection_id: str
    ) -> list[BridgeThreadModel]:
        with get_db() as db:
            threads = (
                db.query(BridgeThread)
                .filter(BridgeThread.connection_id == connection_id)
                .all()
            )
            return [BridgeThreadModel.model_validate(t) for t in threads]

    def update_thread_by_id(
        self, id: str, **kwargs
    ) -> Optional[BridgeThreadModel]:
        with get_db() as db:
            thread = db.query(BridgeThread).filter(BridgeThread.id == id).first()
            if not thread:
                return None

            for key, value in kwargs.items():
                if hasattr(thread, key):
                    setattr(thread, key, value)
            thread.updated_at = int(time.time_ns())

            db.commit()
            return BridgeThreadModel.model_validate(thread)

    def delete_threads_by_connection_id(self, connection_id: str) -> bool:
        with get_db() as db:
            db.query(BridgeThread).filter(
                BridgeThread.connection_id == connection_id
            ).delete()
            db.commit()
            return True


BridgeConnections = BridgeConnectionTable()
BridgeThreads = BridgeThreadTable()
