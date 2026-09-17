"""Add privacy_map and privacy_audit tables

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "privacy_map",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("real", sa.Text(), nullable=False),
        sa.Column("fake", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("privacy_map_real", "privacy_map", ["category", "real"])
    op.create_table(
        "privacy_audit",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("privacy_audit")
    op.drop_index("privacy_map_real", table_name="privacy_map")
    op.drop_table("privacy_map")
