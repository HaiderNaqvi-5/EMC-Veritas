"""harden_database_indexes_and_extensions

Revision ID: a5cdc1687e49
Revises: f5c2d4e7b9a1
Create Date: 2026-09-24 02:36:34.749983
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5cdc1687e49'
down_revision: Union[str, Sequence[str], None] = 'f5c2d4e7b9a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
