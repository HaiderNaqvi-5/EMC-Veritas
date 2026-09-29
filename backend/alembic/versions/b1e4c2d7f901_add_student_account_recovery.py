"""add student account activation and email recovery

Revision ID: b1e4c2d7f901
Revises: f6d2a8b4c1e7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1e4c2d7f901"
down_revision: Union[str, Sequence[str], None] = "f6d2a8b4c1e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("students", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_students_email", "students", ["email"])
    op.create_table(
        "student_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id"),
    )
    op.create_table(
        "student_account_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.Enum("ACTIVATION", "PASSWORD_RESET", name="student_account_token_purpose"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_student_account_tokens_student_id", "student_account_tokens", ["student_id"])
    op.create_table(
        "email_change_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("requested_email", sa.String(length=320), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="email_change_request_status"), nullable=False),
        sa.Column("reviewed_by_admin_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_change_requests_student_id", "email_change_requests", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_email_change_requests_student_id", table_name="email_change_requests")
    op.drop_table("email_change_requests")
    op.drop_index("ix_student_account_tokens_student_id", table_name="student_account_tokens")
    op.drop_table("student_account_tokens")
    op.drop_table("student_accounts")
    op.drop_constraint("uq_students_email", "students", type_="unique")
    op.drop_column("students", "email_verified_at")
    op.drop_column("students", "email")
    op.execute("DROP TYPE IF EXISTS email_change_request_status")
    op.execute("DROP TYPE IF EXISTS student_account_token_purpose")
