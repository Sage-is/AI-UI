"""Peewee migrations -- 019_add_chat_shares.py."""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator

with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class ChatShare(pw.Model):
        id = pw.TextField(unique=True)
        chat_id = pw.TextField()
        shared_by = pw.TextField()
        target_type = pw.TextField()
        target_id = pw.TextField()
        share_mode = pw.TextField(default="live")
        snapshot_chat_id = pw.TextField(null=True)
        created_at = pw.BigIntegerField(null=False)

        class Meta:
            table_name = "chat_share"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    migrator.remove_model("chat_share")
