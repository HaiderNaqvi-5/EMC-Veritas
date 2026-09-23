"""add template field styles

Revision ID: f5c2d4e7b9a1
Revises: e8f1a4c3d2b7
Create Date: 2026-09-24 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f5c2d4e7b9a1"
down_revision = "e8f1a4c3d2b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("template_fields", sa.Column("font_family", sa.String(length=16), nullable=False, server_default="helv"))
    op.add_column("template_fields", sa.Column("font_size", sa.Integer(), nullable=True))
    op.add_column("template_fields", sa.Column("text_color", sa.String(length=7), nullable=False, server_default="#000000"))
    op.alter_column("template_fields", "font_family", server_default=None)
    op.alter_column("template_fields", "text_color", server_default=None)


def downgrade() -> None:
    op.drop_column("template_fields", "text_color")
    op.drop_column("template_fields", "font_size")
    op.drop_column("template_fields", "font_family")
