"""Pre-alembic databases: replay, finish, or refuse. Replaced peewee in 3.2.1.

Until 3.2.0 every boot ran 19 peewee migrations before alembic. 001-018 came
from Open WebUI 0.3; 019 is AI-UI's own and creates ``chat_share`` (2026-03-09).
Each database now gets one of these outcomes, pinned by ``test_legacy_db.py``:

- Fresh: replay ``legacy_schema.sql``, the exact DDL those 19 built, and record
  all 19. Alembic then runs as always, so a new install matches every existing
  one. Alembic alone would build a different shape.
- Recorded 001-018 but not 019 (made before 2026-03-09): create ``chat_share``
  from the same DDL and record 019, which is what peewee did on 3.2.0.
- Missing any of 001-018, or app tables with no record at all: refuse to start,
  naming the fix. Only an Open WebUI 0.3-era file looks like that.

Recording the names keeps a rollback to 3.2.0 safe: its peewee finds no work.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

SCHEMA_FILE = Path(__file__).with_name("legacy_schema.sql")
HISTORY = "migratehistory"
CHAT_SHARES = "019_add_chat_shares"
UPSTREAM = (
    "001_initial_schema", "002_add_local_sharing", "003_add_auth_api_key",
    "004_add_archived", "005_add_updated_at", "006_migrate_timestamps_and_charfields",
    "007_add_user_last_active_at", "008_add_memory", "009_add_models",
    "010_migrate_modelfiles_to_models", "011_add_user_settings", "012_add_tools",
    "013_add_user_info", "014_add_files", "015_add_functions",
    "016_add_valves_and_is_active", "017_add_user_oauth_sub", "018_add_function_is_global",
)  # fmt: skip
PEEWEE_MIGRATIONS = UPSTREAM + (CHAT_SHARES,)

# The last published release that still runs the peewee migrations. The refusal
# below sends people there. If this change ships in a different release, this
# is the one line to change; test_legacy_db pins the message to it.
LAST_PEEWEE_RELEASE = "3.2.0"


class PreAlembicDatabase(RuntimeError):
    """The database needs migrations this image no longer carries."""


def statements() -> list[str]:
    body = "\n".join(
        line
        for line in SCHEMA_FILE.read_text().splitlines()
        if not line.startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


def _table_of(stmt: str) -> str:
    m = re.match(r'CREATE (?:UNIQUE )?(?:TABLE|INDEX "[^"]+" ON) "([^"]+)"', stmt)
    if not m:
        raise ValueError(f"unexpected statement in {SCHEMA_FILE.name}: {stmt[:60]}")
    return m.group(1)


def legacy_tables() -> set[str]:
    return {_table_of(s) for s in statements()}


def _record(conn, names) -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(" ")
    for name in names:
        conn.execute(
            text(f'INSERT INTO "{HISTORY}" ("name", "migrated_at") VALUES (:n, :t)'),
            {"n": name, "t": now},
        )


def _refusal(detail: str) -> PreAlembicDatabase:
    return PreAlembicDatabase(
        f"This database predates AI-UI's migration history: {detail}. Releases "
        f"after {LAST_PEEWEE_RELEASE} no longer carry the peewee migrations that "
        f"finish it. Start it once with AI-UI {LAST_PEEWEE_RELEASE} "
        f"(ghcr.io/sage-is/ai-ui:{LAST_PEEWEE_RELEASE}), which completes them, "
        "then start this version again. Nothing was changed."
    )


def _run(conn, stmts) -> None:
    for stmt in stmts:
        conn.exec_driver_sql(stmt)


def _finish_peewee_history(engine: Engine, tables: set[str]) -> str:
    """A database peewee migrated: check 001-018 landed, then finish 019."""
    with engine.begin() as conn:
        rows = conn.execute(text(f'SELECT "name" FROM "{HISTORY}"'))
        applied = {r[0] for r in rows}
        missing = [n for n in UPSTREAM if n not in applied]
        if missing:
            raise _refusal(f"peewee migrations {', '.join(missing)} were never applied")
        if CHAT_SHARES in applied:
            return "current"
        if "chat_share" not in tables:
            _run(conn, [s for s in statements() if _table_of(s) == "chat_share"])
        _record(conn, [CHAT_SHARES])
    return "chat_share added"


def _bootstrap_fresh(engine: Engine) -> str:
    if engine.dialect.name != "sqlite":
        raise PreAlembicDatabase(
            f"{SCHEMA_FILE.name} is SQLite DDL and this database is "
            f"{engine.dialect.name}; the image ships no other database driver."
        )
    with engine.begin() as conn:
        _run(conn, statements())
        _record(conn, PEEWEE_MIGRATIONS)
    return "fresh"


def prepare(engine: Engine) -> str:
    """Bring the database to where peewee left it, or refuse. Returns what it did."""
    tables = set(inspect(engine).get_table_names())
    if HISTORY in tables:
        return _finish_peewee_history(engine, tables)
    if "alembic_version" in tables:
        return "alembic only"  # never peewee-born; nothing to finish
    stray = sorted(tables & legacy_tables())
    if stray:
        raise _refusal(f"tables {stray} exist with no migration record")
    return _bootstrap_fresh(engine)
