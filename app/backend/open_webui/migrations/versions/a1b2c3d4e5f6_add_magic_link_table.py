"""Add magic_link table

Revision ID: a1b2c3d4e5f6
Revises: d31026856c01
Create Date: 2026-02-19 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "magic_link",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("group_ids", sa.JSON(), nullable=True),
        sa.Column("role", sa.Text(), server_default="temporary"),
        sa.Column("expires_at", sa.BigInteger(), nullable=True),
        sa.Column("account_duration", sa.BigInteger(), nullable=True),
        sa.Column("max_uses", sa.Integer(), server_default="1"),
        sa.Column("use_count", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("magic_link")
