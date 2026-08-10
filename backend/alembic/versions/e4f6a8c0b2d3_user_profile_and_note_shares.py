"""user profile fields and note shares

Revision ID: e4f6a8c0b2d3
Revises: d2b3e5c7f9a1
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f6a8c0b2d3'
down_revision: Union[str, Sequence[str], None] = 'd2b3e5c7f9a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('display_name', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('avatar', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('status', sa.String(length=140), nullable=True))

    op.create_table('note_shares',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('note_id', sa.Integer(), nullable=False),
    sa.Column('shared_with_user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['note_id'], ['notes.id'], ),
    sa.ForeignKeyConstraint(['shared_with_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('note_id', 'shared_with_user_id', name='uq_note_share_target')
    )
    op.create_index(op.f('ix_note_shares_note_id'), 'note_shares', ['note_id'], unique=False)
    op.create_index(op.f('ix_note_shares_shared_with_user_id'), 'note_shares', ['shared_with_user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_note_shares_shared_with_user_id'), table_name='note_shares')
    op.drop_index(op.f('ix_note_shares_note_id'), table_name='note_shares')
    op.drop_table('note_shares')

    op.drop_column('users', 'status')
    op.drop_column('users', 'avatar')
    op.drop_column('users', 'display_name')
