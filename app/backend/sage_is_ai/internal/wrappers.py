import logging
from contextvars import ContextVar

from sage_is_ai.env import SRC_LOG_LEVELS
from peewee import *
from peewee import InterfaceError as PeeWeeInterfaceError
from playhouse.db_url import connect
from playhouse.shortcuts import ReconnectMixin

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(object):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        value = self._state.get()[name]
        return value


class CustomReconnectMixin(ReconnectMixin):
    reconnect_errors = (
        (PeeWeeInterfaceError, "closed"),
    )


def register_connection(db_url):
    db = connect(db_url, unquote_user=True, unquote_password=True)
    if isinstance(db, SqliteDatabase):
        db.autoconnect = True
        db.reuse_if_open = True
        log.info("Connected to SQLite database")
    else:
        raise ValueError("Unsupported database connection")
    return db
