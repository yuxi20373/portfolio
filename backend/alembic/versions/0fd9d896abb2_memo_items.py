"""memo items

Revision ID: 0fd9d896abb2
Revises: 9a860ae9eb50
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fd9d896abb2'
down_revision: Union[str, Sequence[str], None] = '9a860ae9eb50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('memo_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(length=500), nullable=True),
    sa.Column('done', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memo_items_user_id'), 'memo_items', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_memo_items_user_id'), table_name='memo_items')
    op.drop_table('memo_items')
