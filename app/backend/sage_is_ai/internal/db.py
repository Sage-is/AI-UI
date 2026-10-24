import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from sage_is_ai.internal.legacy_db import prepare as prepare_legacy_database
from sage_is_ai.env import (
    DATABASE_URL,
    SRC_LOG_LEVELS,
)
from sqlalchemy import Dialect, create_engine, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Until 3.2.0 the 19 peewee migrations ran here, before alembic. Since 3.2.1 a
# fresh database gets their frozen DDL and a pre-alembic one is finished or
# refused with the fix named (internal/legacy_db.py). Alembic still runs later,
# from config.run_migrations.
log.info("legacy database check: %s", prepare_legacy_database(engine))

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
Base = declarative_base()
Session = scoped_session(SessionLocal)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


get_db = contextmanager(get_session)
