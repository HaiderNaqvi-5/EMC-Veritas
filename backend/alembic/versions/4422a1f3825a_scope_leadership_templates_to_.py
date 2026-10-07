"""scope leadership templates to memberships

Revision ID: 4422a1f3825a
Revises: b1e4c2d7f901
Create Date: 2026-10-08 01:03:30.256780
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4422a1f3825a'
down_revision: Union[str, Sequence[str], None] = 'b1e4c2d7f901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leadership_templates",
        sa.Column("executive_membership_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_leadership_templates_executive_membership_id",
        "leadership_templates",
        "executive_memberships",
        ["executive_membership_id"],
        ["id"],
    )
    op.create_index(
        "ix_leadership_templates_executive_membership_id",
        "leadership_templates",
        ["executive_membership_id"],
    )
    op.drop_index("uq_active_leadership_template", table_name="leadership_templates")
    op.create_index(
        "uq_active_role_leadership_template",
        "leadership_templates",
        ["role", "document_type"],
        unique=True,
        postgresql_where=sa.text(
            "active AND NOT archived AND executive_membership_id IS NULL"
        ),
    )
    op.create_index(
        "uq_active_membership_leadership_template",
        "leadership_templates",
        ["executive_membership_id", "document_type"],
        unique=True,
        postgresql_where=sa.text(
            "active AND NOT archived AND executive_membership_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_membership_leadership_template",
        table_name="leadership_templates",
    )
    op.drop_index(
        "uq_active_role_leadership_template",
        table_name="leadership_templates",
    )
    op.create_index(
        "uq_active_leadership_template",
        "leadership_templates",
        ["role", "document_type"],
        unique=True,
        postgresql_where=sa.text("active AND NOT archived"),
    )
    op.drop_index(
        "ix_leadership_templates_executive_membership_id",
        table_name="leadership_templates",
    )
    op.drop_constraint(
        "fk_leadership_templates_executive_membership_id",
        "leadership_templates",
        type_="foreignkey",
    )
    op.drop_column("leadership_templates", "executive_membership_id")
