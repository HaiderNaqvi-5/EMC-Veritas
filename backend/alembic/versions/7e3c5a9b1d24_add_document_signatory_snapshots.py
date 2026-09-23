"""snapshot selected signatories for issued documents

Revision ID: 7e3c5a9b1d24
Revises: 2d8b3f4a6c71
Create Date: 2026-09-23 20:28:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e3c5a9b1d24"
down_revision: Union[str, Sequence[str], None] = "2d8b3f4a6c71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_signatories",
        sa.Column("issued_document_id", sa.UUID(), nullable=False),
        sa.Column("signatory_id", sa.UUID(), nullable=False),
        sa.Column("official_title", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["issued_document_id"], ["issued_documents.id"]),
        sa.ForeignKeyConstraint(["signatory_id"], ["signatories.id"]),
        sa.PrimaryKeyConstraint("issued_document_id", "signatory_id"),
    )


def downgrade() -> None:
    op.drop_table("document_signatories")
