"""add role-specific leadership templates

Revision ID: 9a6d2c8f4e13
Revises: 7e3c5a9b1d24
Create Date: 2026-09-23 21:04:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


revision: str = "9a6d2c8f4e13"
down_revision: Union[str, Sequence[str], None] = "7e3c5a9b1d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This enum is created by the initial schema migration.  Referencing it
    # here must not emit a second CREATE TYPE on an existing Supabase database.
    document_type = postgresql.ENUM(name="document_type", create_type=False)
    op.create_table(
        "leadership_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_active_leadership_template",
        "leadership_templates",
        ["role", "document_type"],
        unique=True,
        postgresql_where=sa.text("active AND NOT archived"),
    )
    op.create_table(
        "leadership_template_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("leadership_template_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["leadership_template_id"], ["leadership_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("leadership_template_id", "field_name", name="uq_leadership_template_field"),
    )


def downgrade() -> None:
    op.drop_table("leadership_template_fields")
    op.drop_index("uq_active_leadership_template", table_name="leadership_templates")
    op.drop_table("leadership_templates")
