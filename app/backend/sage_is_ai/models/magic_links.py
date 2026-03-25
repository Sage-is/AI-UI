import logging
import time
import uuid
import secrets
from typing import Optional

from sage_is_ai.internal.db import Base, get_db
from sage_is_ai.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, JSON


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# MagicLink DB Schema
####################


class MagicLink(Base):
    __tablename__ = "magic_link"

    id = Column(Text, unique=True, primary_key=True)
    token = Column(Text, unique=True, nullable=False)
    created_by = Column(Text, nullable=False)

    group_ids = Column(JSON, nullable=True)
    role = Column(Text, default="temporary")

    expires_at = Column(BigInteger, nullable=True)
    account_duration = Column(BigInteger, nullable=True)

    max_uses = Column(Integer, default=1)
    use_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    meta = Column(JSON, nullable=True)
    webhook_url = Column(Text, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class MagicLinkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    token: str
    created_by: str

    group_ids: Optional[list[str]] = None
    role: str = "temporary"

    expires_at: Optional[int] = None
    account_duration: Optional[int] = None

    max_uses: int = 1
    use_count: int = 0

    is_active: bool = True
    meta: Optional[dict] = None
    webhook_url: Optional[str] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class MagicLinkForm(BaseModel):
    group_ids: Optional[list[str]] = None
    role: str = "temporary"
    expires_at: Optional[int] = None
    account_duration: Optional[int] = None
    max_uses: int = 1
    meta: Optional[dict] = None
    webhook_url: Optional[str] = None


class MagicLinkResponse(BaseModel):
    id: str
    token: str
    created_by: str
    group_ids: Optional[list[str]] = None
    role: str
    expires_at: Optional[int] = None
    account_duration: Optional[int] = None
    max_uses: int
    use_count: int
    is_active: bool
    meta: Optional[dict] = None
    webhook_url: Optional[str] = None
    created_at: int
    updated_at: int


class RedeemForm(BaseModel):
    token: str
    name: Optional[str] = None


####################
# MagicLinkTable
####################


class MagicLinkTable:
    def create(
        self, created_by: str, form_data: MagicLinkForm
    ) -> Optional[MagicLinkModel]:
        with get_db() as db:
            now = int(time.time())
            magic_link = MagicLinkModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "token": secrets.token_urlsafe(32),
                    "created_by": created_by,
                    "use_count": 0,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            try:
                result = MagicLink(**magic_link.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return MagicLinkModel.model_validate(result)
                return None
            except Exception as e:
                log.exception(e)
                return None

    def get_by_token(self, token: str) -> Optional[MagicLinkModel]:
        try:
            with get_db() as db:
                link = db.query(MagicLink).filter_by(token=token).first()
                return MagicLinkModel.model_validate(link) if link else None
        except Exception:
            return None

    def get_by_id(self, id: str) -> Optional[MagicLinkModel]:
        try:
            with get_db() as db:
                link = db.query(MagicLink).filter_by(id=id).first()
                return MagicLinkModel.model_validate(link) if link else None
        except Exception:
            return None

    def get_by_creator(self, user_id: str) -> list[MagicLinkModel]:
        with get_db() as db:
            return [
                MagicLinkModel.model_validate(link)
                for link in db.query(MagicLink)
                .filter_by(created_by=user_id)
                .order_by(MagicLink.created_at.desc())
                .all()
            ]

    def get_all(self) -> list[MagicLinkModel]:
        with get_db() as db:
            return [
                MagicLinkModel.model_validate(link)
                for link in db.query(MagicLink)
                .order_by(MagicLink.created_at.desc())
                .all()
            ]

    def increment_use_count(self, id: str) -> Optional[MagicLinkModel]:
        try:
            with get_db() as db:
                link = db.query(MagicLink).filter_by(id=id).first()
                if link:
                    link.use_count = (link.use_count or 0) + 1
                    link.updated_at = int(time.time())
                    db.commit()
                    db.refresh(link)
                    return MagicLinkModel.model_validate(link)
                return None
        except Exception:
            return None

    def deactivate(self, id: str) -> Optional[MagicLinkModel]:
        try:
            with get_db() as db:
                db.query(MagicLink).filter_by(id=id).update(
                    {"is_active": False, "updated_at": int(time.time())}
                )
                db.commit()
                return self.get_by_id(id)
        except Exception:
            return None

    def delete(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(MagicLink).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


MagicLinks = MagicLinkTable()
