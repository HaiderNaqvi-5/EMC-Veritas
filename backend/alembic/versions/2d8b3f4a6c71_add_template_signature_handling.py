"""require an explicit template signature-handling choice

Revision ID: 2d8b3f4a6c71
Revises: 11f1f930392e
Create Date: 2026-09-23 20:12:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2d8b3f4a6c71"
down_revision: Union[str, Sequence[str], None] = "11f1f930392e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("signature_handling", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "template_signature_handling_valid",
        "templates",
        "signature_handling IN ('retain', 'replace') OR signature_handling IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("template_signature_handling_valid", "templates", type_="check")
    op.drop_column("templates", "signature_handling")
