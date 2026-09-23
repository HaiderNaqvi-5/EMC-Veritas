"""classify issued documents

Revision ID: 11f1f930392e
Revises: c8dc00f20398
Create Date: 2026-09-23 19:53:35.995064
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '11f1f930392e'
down_revision: Union[str, Sequence[str], None] = 'c8dc00f20398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    document_type = postgresql.ENUM(
        'ACTIVITY_CERTIFICATE', 'LEADERSHIP_RECOGNITION', 'END_OF_TENURE_APPRECIATION',
        name='document_type',
    )
    document_type.create(op.get_bind(), checkfirst=True)
    op.add_column('issued_documents', sa.Column('document_type', document_type, nullable=False))


def downgrade() -> None:
    op.drop_column('issued_documents', 'document_type')
    postgresql.ENUM(name='document_type').drop(op.get_bind(), checkfirst=True)
