"""add student support requests

Revision ID: c7d4a9e2b105
Revises: 8e1b4cdcf103
Create Date: 2026-10-11 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c7d4a9e2b105"
down_revision: str | None = "8e1b4cdcf103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    support_status = sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", name="support_request_status")
    op.create_table(
        "support_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_number", sa.String(length=24), nullable=False),
        sa.Column("roll_number", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("problem_category", sa.String(length=48), nullable=False),
        sa.Column("problem_details", sa.Text(), nullable=False),
        sa.Column("status", support_status, nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolution_message", sa.Text(), nullable=True),
        sa.Column("resolved_by_admin_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["resolved_by_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_support_requests_ticket_number", "support_requests", ["ticket_number"])
    op.create_index("ix_support_requests_roll_number", "support_requests", ["roll_number"])
    op.create_index("ix_support_requests_contact_email", "support_requests", ["contact_email"])
    op.create_index("ix_support_requests_status", "support_requests", ["status"])
    op.execute("ALTER TABLE support_requests ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE support_requests FROM anon, authenticated")


def downgrade() -> None:
    op.drop_table("support_requests")
    sa.Enum(name="support_request_status").drop(op.get_bind(), checkfirst=True)
