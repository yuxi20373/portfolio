"""custom emoji

Revision ID: 5a1c9d7e2f3b
Revises: 27b5db7e5878
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a1c9d7e2f3b'
down_revision: Union[str, Sequence[str], None] = '27b5db7e5878'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('custom_emoji',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('shortcode', sa.String(length=50), nullable=False),
    sa.Column('image_data', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_custom_emoji_shortcode'), 'custom_emoji', ['shortcode'], unique=False)
    op.create_index(op.f('ix_custom_emoji_user_id'), 'custom_emoji', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_custom_emoji_user_id'), table_name='custom_emoji')
    op.drop_index(op.f('ix_custom_emoji_shortcode'), table_name='custom_emoji')
    op.drop_table('custom_emoji')
