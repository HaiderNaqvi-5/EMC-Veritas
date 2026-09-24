"""snapshot activity certificate template and rendering data

Revision ID: c1a5f8e2d3b4
Revises: edb2eefdb003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c1a5f8e2d3b4"
down_revision: Union[str, Sequence[str], None] = "edb2eefdb003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("issued_documents", sa.Column("template_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_issued_documents_template_id", "issued_documents", "templates", ["template_id"], ["id"]
    )
    op.create_index("ix_issued_documents_template_id", "issued_documents", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_issued_documents_template_id", table_name="issued_documents")
    op.drop_constraint("fk_issued_documents_template_id", "issued_documents", type_="foreignkey")
    op.drop_column("issued_documents", "template_id")
