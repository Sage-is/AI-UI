import logging
import time
from typing import Optional
import uuid

from sage_is_ai.internal.db import Base, get_db
from sage_is_ai.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, or_, and_


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# ChatShare DB Schema
####################


class ChatShare(Base):
    __tablename__ = "chat_share"

    id = Column(String, primary_key=True)
    chat_id = Column(String, nullable=False)
    shared_by = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # "user" or "group"
    target_id = Column(String, nullable=False)
    share_mode = Column(String, default="live")  # "live" or "snapshot"
    snapshot_chat_id = Column(String, nullable=True)
    created_at = Column(BigInteger)


class ChatShareModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    shared_by: str
    target_type: str
    target_id: str
    share_mode: str = "live"
    snapshot_chat_id: Optional[str] = None
    created_at: int


####################
# Forms
####################


class ShareTarget(BaseModel):
    type: str  # "user" or "group"
    id: str
    mode: str = "live"  # "live" or "snapshot"


class ChatShareForm(BaseModel):
    targets: list[ShareTarget]


class ChatShareResponse(BaseModel):
    id: str
    chat_id: str
    shared_by: str
    shared_by_name: Optional[str] = None
    target_type: str
    target_id: str
    target_name: Optional[str] = None
    share_mode: str
    snapshot_chat_id: Optional[str] = None
    created_at: int


class SharedWithMeResponse(BaseModel):
    share_id: str
    chat_id: str
    chat_title: str
    shared_by: str
    shared_by_name: Optional[str] = None
    share_mode: str
    snapshot_chat_id: Optional[str] = None
    created_at: int


class SharedByMeResponse(BaseModel):
    chat_id: str
    chat_title: str
    share_count: int  # 0 for link-only shares
    share_type: str = "targets"  # "link", "targets", or "both"
    share_id: Optional[str] = None  # for link shares
    created_at: int


####################
# ChatShareTable
####################


class ChatShareTable:
    def share_chat(
        self,
        chat_id: str,
        shared_by: str,
        targets: list[ShareTarget],
    ) -> list[ChatShareModel]:
        results = []
        with get_db() as db:
            for target in targets:
                # Check if share already exists for this chat+target combo
                existing = (
                    db.query(ChatShare)
                    .filter_by(
                        chat_id=chat_id,
                        target_type=target.type,
                        target_id=target.id,
                    )
                    .first()
                )
                if existing:
                    # Update mode if changed
                    if existing.share_mode != target.mode:
                        existing.share_mode = target.mode
                        # Handle snapshot creation if switching to snapshot
                        if target.mode == "snapshot" and not existing.snapshot_chat_id:
                            snapshot_id = self._create_snapshot(db, chat_id)
                            existing.snapshot_chat_id = snapshot_id
                        db.commit()
                        db.refresh(existing)
                    results.append(ChatShareModel.model_validate(existing))
                    continue

                snapshot_chat_id = None
                if target.mode == "snapshot":
                    snapshot_chat_id = self._create_snapshot(db, chat_id)

                share = ChatShareModel(
                    id=str(uuid.uuid4()),
                    chat_id=chat_id,
                    shared_by=shared_by,
                    target_type=target.type,
                    target_id=target.id,
                    share_mode=target.mode,
                    snapshot_chat_id=snapshot_chat_id,
                    created_at=int(time.time()),
                )
                result = ChatShare(**share.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                results.append(ChatShareModel.model_validate(result))
        return results

    def _create_snapshot(self, db, chat_id: str) -> Optional[str]:
        from sage_is_ai.models.chats import Chats

        shared_chat = Chats.insert_shared_chat_by_chat_id(chat_id)
        return shared_chat.id if shared_chat else None

    def get_shares_by_chat_id(self, chat_id: str) -> list[ChatShareModel]:
        with get_db() as db:
            return [
                ChatShareModel.model_validate(share)
                for share in db.query(ChatShare)
                .filter_by(chat_id=chat_id)
                .order_by(ChatShare.created_at.desc())
                .all()
            ]

    def delete_share(self, share_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(ChatShare).filter_by(id=share_id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_shares_by_chat_id(self, chat_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(ChatShare).filter_by(chat_id=chat_id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def get_chats_shared_with_user(
        self, user_id: str, group_ids: list[str] = None
    ) -> list[ChatShareModel]:
        if group_ids is None:
            group_ids = []

        with get_db() as db:
            conditions = [
                and_(
                    ChatShare.target_type == "user",
                    ChatShare.target_id == user_id,
                )
            ]
            if group_ids:
                conditions.append(
                    and_(
                        ChatShare.target_type == "group",
                        ChatShare.target_id.in_(group_ids),
                    )
                )

            return [
                ChatShareModel.model_validate(share)
                for share in db.query(ChatShare)
                .filter(or_(*conditions))
                .order_by(ChatShare.created_at.desc())
                .all()
            ]

    def get_chats_shared_by_user(self, user_id: str) -> list[ChatShareModel]:
        with get_db() as db:
            return [
                ChatShareModel.model_validate(share)
                for share in db.query(ChatShare)
                .filter_by(shared_by=user_id)
                .order_by(ChatShare.created_at.desc())
                .all()
            ]

    def is_chat_shared_with_user(
        self, chat_id: str, user_id: str, group_ids: list[str] = None
    ) -> bool:
        if group_ids is None:
            group_ids = []

        with get_db() as db:
            conditions = [
                and_(
                    ChatShare.chat_id == chat_id,
                    ChatShare.target_type == "user",
                    ChatShare.target_id == user_id,
                )
            ]
            if group_ids:
                conditions.append(
                    and_(
                        ChatShare.chat_id == chat_id,
                        ChatShare.target_type == "group",
                        ChatShare.target_id.in_(group_ids),
                    )
                )

            return (
                db.query(ChatShare).filter(or_(*conditions)).first() is not None
            )


ChatShares = ChatShareTable()
