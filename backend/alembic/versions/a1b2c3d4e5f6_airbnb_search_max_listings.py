"""airbnb search max_listings

Revision ID: a1b2c3d4e5f6
Revises: f5a7c9e1d3b5
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f5a7c9e1d3b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 使用者現在可以自己選要爬幾筆,不用固定 200 - 存起來給快取比對用(見
    # models/airbnb_search.py)。舊資料一律當時就是用固定的 200。
    op.add_column('airbnb_searches', sa.Column('max_listings', sa.Integer(), nullable=False, server_default='200'))
    op.alter_column('airbnb_searches', 'max_listings', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('airbnb_searches', 'max_listings')
