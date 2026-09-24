"""canonicalize student roll numbers

Revision ID: f6d2a8b4c1e7
Revises: c1a5f8e2d3b4
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f6d2a8b4c1e7"
down_revision: Union[str, Sequence[str], None] = "c1a5f8e2d3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE students SET roll_number = UPPER(TRIM(roll_number))")


def downgrade() -> None:
    # Canonical case is intentionally irreversible: it is an identity invariant.
    pass
