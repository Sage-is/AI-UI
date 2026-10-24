"""Pre-alembic guard: python -m unittest sage_is_ai.internal.test_legacy_db

Every branch of internal/legacy_db.prepare() on throwaway SQLite files. The
real-data proof is separate: `make test_db_upgrade` (an 18-migration snapshot),
`make upgrade_gate`, and the fresh-schema diff against the last build with peewee.
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, text

from sage_is_ai.internal import legacy_db as L

FROZEN_SHA256 = "96db67f2f94330904d350c0b7d242860367abc957a4ec9db59c216ecadadd01b"


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.tmp.name) / 'webui.db'}")

    def tearDown(self):
        self.engine.dispose()
        self.tmp.cleanup()

    def run_sql(self, *stmts):
        with self.engine.begin() as c:
            for s in stmts:
                c.exec_driver_sql(s)

    def objects(self):
        with self.engine.connect() as c:
            return sorted(
                r[0]
                for r in c.execute(
                    text("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")
                )
            )

    def history(self):
        with self.engine.connect() as c:
            return [
                r[0]
                for r in c.execute(text("SELECT name FROM migratehistory ORDER BY id"))
            ]

    def build_peewee_db(self, names, with_chat_share):
        stmts = [
            s
            for s in L.statements()
            if with_chat_share or L._table_of(s) != "chat_share"
        ]
        self.run_sql(*stmts)
        with self.engine.begin() as c:
            L._record(c, names)

    def test_frozen_ddl_is_unedited(self):
        self.assertEqual(
            hashlib.sha256(L.SCHEMA_FILE.read_bytes()).hexdigest(), FROZEN_SHA256
        )
        self.assertEqual(len(L.statements()), 31)
        self.assertEqual(len(L.legacy_tables()), 14)  # 14 tables + 17 indexes

    def test_fresh_database_gets_exactly_the_frozen_schema(self):
        self.assertEqual(L.prepare(self.engine), "fresh")
        self.assertEqual(self.objects(), sorted(L.statements()))
        self.assertEqual(self.history(), list(L.PEEWEE_MIGRATIONS))

    def test_second_boot_does_nothing(self):
        L.prepare(self.engine)
        before = (self.objects(), self.history())
        self.assertEqual(L.prepare(self.engine), "current")
        self.assertEqual((self.objects(), self.history()), before)

    def test_pre_march_database_gets_chat_share_like_peewee_did(self):
        self.build_peewee_db(L.UPSTREAM, with_chat_share=False)
        self.assertEqual(L.prepare(self.engine), "chat_share added")
        self.assertEqual(self.objects(), sorted(L.statements()))
        self.assertEqual(self.history()[-1], L.CHAT_SHARES)

    def test_existing_chat_share_is_only_recorded(self):
        self.build_peewee_db(L.UPSTREAM, with_chat_share=True)
        self.assertEqual(L.prepare(self.engine), "chat_share added")
        self.assertEqual(self.history(), list(L.PEEWEE_MIGRATIONS))

    def test_missing_upstream_migration_is_refused_and_nothing_changes(self):
        partial = tuple(n for n in L.UPSTREAM if not n.startswith("006"))
        self.build_peewee_db(partial, with_chat_share=False)
        before = (self.objects(), self.history())
        with self.assertRaisesRegex(
            L.PreAlembicDatabase,
            f"006_migrate_timestamps.*ai-ui:{L.LAST_PEEWEE_RELEASE}",
        ):
            L.prepare(self.engine)
        self.assertEqual((self.objects(), self.history()), before)

    def test_app_tables_with_no_record_are_refused(self):
        self.run_sql('CREATE TABLE "user" ("id" TEXT)')
        with self.assertRaisesRegex(L.PreAlembicDatabase, "no migration record"):
            L.prepare(self.engine)

    def test_alembic_only_database_is_left_alone(self):
        self.run_sql(
            'CREATE TABLE "alembic_version" ("version_num" TEXT)',
            'CREATE TABLE "user" ("id" TEXT)',
        )
        before = self.objects()
        self.assertEqual(L.prepare(self.engine), "alembic only")
        self.assertEqual(self.objects(), before)


if __name__ == "__main__":
    unittest.main()
