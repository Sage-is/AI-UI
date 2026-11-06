"""Give every prompt command its leading slash

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-11-02 00:00:00.000000

Every reader looks a prompt up as "/<command>", but the create route stored the
command verbatim and the UI's import strips the slash, so those rows could never
be fetched, edited or deleted. PromptForm adds the slash on the way in now; this
repairs the rows already stored. A row whose slashed twin exists is left alone:
the twin is the one every reader already finds, and the key stays unique.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE prompt SET command = '/' || command "
            "WHERE command NOT LIKE '/%' "
            "AND '/' || command NOT IN (SELECT command FROM prompt)"
        )
    )


def downgrade():
    # Nothing to undo: the slashed form is the only one any reader finds.
    pass
