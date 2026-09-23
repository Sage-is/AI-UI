"""The real-to-fake map and the audit trail behind the privacy panel.

The map is the crown jewel: it holds the real values. Nothing here returns a
real value except ``reveal``, and every caller of that writes an audit row.
"""

import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Index, Text
from sqlalchemy.exc import IntegrityError

from sage_is_ai.internal.db import Base, get_db


class PrivacyMap(Base):
    __tablename__ = "privacy_map"

    id = Column(Text, primary_key=True)
    category = Column(Text, nullable=False)
    real = Column(Text, nullable=False)
    fake = Column(Text, nullable=False, unique=True)
    created_at = Column(BigInteger)

    __table_args__ = (Index("privacy_map_real", "category", "real"),)


class PrivacyAudit(Base):
    __tablename__ = "privacy_audit"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    action = Column(Text)  # reveal | forget | purge
    subject = Column(Text)  # what it was about, never a real value
    created_at = Column(BigInteger)


class PrivacyAuditModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: Optional[str] = None
    action: str
    subject: Optional[str] = None
    created_at: int


class PrivacyMapsTable:
    def get_fake(self, category: str, real: str) -> Optional[str]:
        with get_db() as db:
            row = db.query(PrivacyMap).filter(PrivacyMap.category == category, PrivacyMap.real == real).first()
            return row.fake if row else None

    def get_owner(self, fake: str) -> Optional[tuple[str, str]]:
        with get_db() as db:
            row = db.query(PrivacyMap).filter(PrivacyMap.fake == fake).first()
            return (row.category, row.real) if row else None

    def insert(self, category: str, real: str, fake: str) -> None:
        # get_fake-then-insert is check-then-act, and `fake` is UNIQUE. Two
        # requests meeting the same value for the first time race here; the
        # loser's row is already the row it wanted, so losing is success.
        with get_db() as db:
            db.add(PrivacyMap(id=str(uuid.uuid4()), category=category, real=real, fake=fake, created_at=int(time.time())))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

    def pairs(self) -> list[tuple[str, str]]:
        with get_db() as db:
            return [(row.fake, row.real) for row in db.query(PrivacyMap.fake, PrivacyMap.real).all()]

    def count(self) -> int:
        with get_db() as db:
            return db.query(PrivacyMap).count()

    def recent(self, limit: int = 20) -> list[dict]:
        """For the panel: fakes and categories, never the real values."""
        with get_db() as db:
            rows = db.query(PrivacyMap).order_by(PrivacyMap.created_at.desc()).limit(limit).all()
            return [{"id": r.id, "category": r.category, "fake": r.fake, "created_at": r.created_at} for r in rows]

    def reveal(self, id: str) -> Optional[dict]:
        with get_db() as db:
            row = db.query(PrivacyMap).filter(PrivacyMap.id == id).first()
            return {"id": row.id, "category": row.category, "fake": row.fake, "real": row.real} if row else None

    def forget(self, id: str) -> bool:
        with get_db() as db:
            deleted = db.query(PrivacyMap).filter(PrivacyMap.id == id).delete()
            db.commit()
            return bool(deleted)

    def purge(self) -> int:
        with get_db() as db:
            deleted = db.query(PrivacyMap).delete()
            db.commit()
            return int(deleted)


class PrivacyAuditsTable:
    def write(self, user_id: str, action: str, subject: str) -> None:
        with get_db() as db:
            db.add(PrivacyAudit(id=str(uuid.uuid4()), user_id=user_id, action=action, subject=subject[:200], created_at=int(time.time())))
            db.commit()

    def recent(self, limit: int = 10) -> list[PrivacyAuditModel]:
        with get_db() as db:
            rows = db.query(PrivacyAudit).order_by(PrivacyAudit.created_at.desc()).limit(limit).all()
            return [PrivacyAuditModel.model_validate(r) for r in rows]


PrivacyMaps = PrivacyMapsTable()
PrivacyAudits = PrivacyAuditsTable()
