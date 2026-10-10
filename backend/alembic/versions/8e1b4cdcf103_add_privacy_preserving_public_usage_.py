"""add privacy preserving public usage metrics

Revision ID: 8e1b4cdcf103
Revises: 7c9e1a4b5d2f
Create Date: 2026-10-11 02:08:52.954701
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e1b4cdcf103"
down_revision: str | None = "7c9e1a4b5d2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_student_usage",
        sa.Column("student_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("lookup_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("download_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("first_lookup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_lookup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_download_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_download_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("student_fingerprint"),
    )
    # This table is managed only through FastAPI. It must never become a
    # student-level analytics endpoint through Supabase's public Data API.
    op.execute("ALTER TABLE public_student_usage ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE public_student_usage FROM anon, authenticated")


def downgrade() -> None:
    op.drop_table("public_student_usage")
