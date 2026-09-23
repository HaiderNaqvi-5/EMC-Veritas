"""enforce society head tenure overlap

Revision ID: c8dc00f20398
Revises: 5cc88f8a34ae
Create Date: 2026-09-23 19:49:59.784576
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8dc00f20398'
down_revision: Union[str, Sequence[str], None] = '5cc88f8a34ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE executive_memberships
        ADD CONSTRAINT excl_society_head_tenure
        EXCLUDE USING gist (
            session_id WITH =,
            society_id WITH =,
            daterange(start_date, COALESCE(end_date, 'infinity'::date), '[]') WITH &&
        )
        WHERE (role = 'Society Head')
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE executive_memberships DROP CONSTRAINT IF EXISTS excl_society_head_tenure"
    )
