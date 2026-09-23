"""seed fixed EMC societies

Revision ID: e8f1a4c3d2b7
Revises: d4e7f9a2b6c0
Create Date: 2026-09-24 12:00:00.000000
"""

from alembic import op

revision = "e8f1a4c3d2b7"
down_revision = "d4e7f9a2b6c0"
branch_labels = None
depends_on = None

SOCIETIES = (
    ("b6c28f79-d6f3-4d0f-85b5-4912250e4a39", "Social Welfare"),
    ("1e9f317f-e80d-460f-9a69-39c7fd1f1a3c", "SciTech"),
    ("f9dcc3cf-0189-4187-9dbb-2d8826cf4968", "Arts & Decor"),
    ("44e061e5-3396-4aa2-b43b-6c2117f6b31a", "Media & Graphics"),
    ("65307351-f64a-46de-bc0f-87f3ad51e01e", "Discipline"),
)


def upgrade() -> None:
    for identifier, name in SOCIETIES:
        op.execute(
            f"INSERT INTO societies (id, name, active) VALUES ('{identifier}', '{name}', true) "
            "ON CONFLICT (name) DO NOTHING"
        )


def downgrade() -> None:
    op.execute("DELETE FROM societies WHERE name IN ('Social Welfare', 'SciTech', 'Arts & Decor', 'Media & Graphics', 'Discipline')")
