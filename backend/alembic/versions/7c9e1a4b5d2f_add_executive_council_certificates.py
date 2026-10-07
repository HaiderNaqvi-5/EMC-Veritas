"""add executive council certificates

Revision ID: 7c9e1a4b5d2f
Revises: 4422a1f3825a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7c9e1a4b5d2f"
down_revision: str | None = "4422a1f3825a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'EXECUTIVE_COUNCIL_CERTIFICATE'")
    op.add_column(
        "templates",
        sa.Column("purpose", sa.String(length=32), server_default="PARTICIPANT", nullable=False),
    )
    op.create_table(
        "activity_organizers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executive_membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["executive_membership_id"], ["executive_memberships.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_id", "executive_membership_id", name="uq_organizer_per_activity"
        ),
    )
    op.create_index(
        op.f("ix_activity_organizers_activity_id"),
        "activity_organizers",
        ["activity_id"],
    )
    op.create_index(
        op.f("ix_activity_organizers_executive_membership_id"),
        "activity_organizers",
        ["executive_membership_id"],
    )
    # Managed only through the authenticated FastAPI service; do not expose
    # organizer assignments through Supabase's public Data API.
    op.execute("ALTER TABLE activity_organizers ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE activity_organizers FROM anon, authenticated")


def downgrade() -> None:
    op.drop_index(
        op.f("ix_activity_organizers_executive_membership_id"),
        table_name="activity_organizers",
    )
    op.drop_index(op.f("ix_activity_organizers_activity_id"), table_name="activity_organizers")
    op.drop_table("activity_organizers")
    op.drop_column("templates", "purpose")
    # PostgreSQL enum values are intentionally retained: issued immutable
    # records may still reference this historical document type.
