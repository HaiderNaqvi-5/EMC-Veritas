"""snapshot leadership document context

Revision ID: d4e7f9a2b6c0
Revises: 9a6d2c8f4e13
Create Date: 2026-09-24 09:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7f9a2b6c0"
down_revision: Union[str, Sequence[str], None] = "9a6d2c8f4e13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leadership_templates", sa.Column("signature_handling", sa.String(length=16), nullable=True))
    op.add_column("issued_documents", sa.Column("executive_membership_id", sa.UUID(), nullable=True))
    op.add_column("issued_documents", sa.Column("leadership_template_id", sa.UUID(), nullable=True))
    op.add_column("issued_documents", sa.Column("render_payload_json", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_issued_documents_executive_membership_id",
        "issued_documents",
        "executive_memberships",
        ["executive_membership_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_issued_documents_leadership_template_id",
        "issued_documents",
        "leadership_templates",
        ["leadership_template_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_leadership_document_membership_type_version",
        "issued_documents",
        ["executive_membership_id", "document_type", "version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_leadership_document_membership_type_version", "issued_documents", type_="unique")
    op.drop_constraint("fk_issued_documents_leadership_template_id", "issued_documents", type_="foreignkey")
    op.drop_constraint("fk_issued_documents_executive_membership_id", "issued_documents", type_="foreignkey")
    op.drop_column("issued_documents", "render_payload_json")
    op.drop_column("issued_documents", "leadership_template_id")
    op.drop_column("issued_documents", "executive_membership_id")
    op.drop_column("leadership_templates", "signature_handling")
