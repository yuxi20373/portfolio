"""note template default tags

Revision ID: 4299637f7969
Revises: 0fd9d896abb2
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4299637f7969'
down_revision: Union[str, Sequence[str], None] = '0fd9d896abb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('note_templates', sa.Column('tags', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('note_templates', 'tags')
