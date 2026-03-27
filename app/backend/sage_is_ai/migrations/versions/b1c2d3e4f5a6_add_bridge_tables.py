"""Add bridge_connection and bridge_thread tables

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "bridge_connection",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("user_provisioning", sa.Text(), server_default="auto_create"),
        sa.Column("allowed_ids", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("status", sa.Text(), server_default="disconnected"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    op.create_table(
        "bridge_thread",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("connection_id", sa.Text(), nullable=False),
        sa.Column("external_thread_id", sa.Text(), nullable=False),
        sa.Column("external_user_id", sa.Text(), nullable=False),
        sa.Column("sage_user_id", sa.Text(), nullable=True),
        sa.Column("sage_chat_id", sa.Text(), nullable=True),
        sa.Column("sage_channel_id", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    with op.batch_alter_table("bridge_thread") as batch_op:
        batch_op.create_unique_constraint(
            "uq_bridge_thread_conn_ext",
            ["connection_id", "external_thread_id", "external_user_id"],
        )


def downgrade():
    op.drop_table("bridge_thread")
    op.drop_table("bridge_connection")
