"""airbnb search multi-location

Revision ID: d2b3e5c7f9a1
Revises: c1a2f4b6d8e0
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2b3e5c7f9a1'
down_revision: Union[str, Sequence[str], None] = 'c1a2f4b6d8e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # location 現在存的是 JSON-encoded 的地點清單(一次搜尋可以涵蓋多個地點),
    # 不是單一字串,String(255) 放不下,改成 Text。
    op.alter_column('airbnb_searches', 'location', type_=sa.Text(), existing_type=sa.String(length=255))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('airbnb_searches', 'location', type_=sa.String(length=255), existing_type=sa.Text())
