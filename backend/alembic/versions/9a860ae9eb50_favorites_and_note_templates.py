"""favorites and note templates/tags

Revision ID: 9a860ae9eb50
Revises: 94e7129901e0
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a860ae9eb50'
down_revision: Union[str, Sequence[str], None] = '94e7129901e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # nullable=False + server_default backfills every pre-existing row to
    # false in the same ALTER TABLE (Postgres 11+ does this without a table
    # rewrite for a constant default) - required because SessionOut.is_favorited
    # is a non-Optional bool (a NULL there would 500 on every old session).
    op.add_column('wiki_entries', sa.Column('is_favorited', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index(op.f('ix_wiki_entries_is_favorited'), 'wiki_entries', ['is_favorited'], unique=False)

    op.add_column('chat_sessions', sa.Column('is_favorited', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index(op.f('ix_chat_sessions_is_favorited'), 'chat_sessions', ['is_favorited'], unique=False)

    op.add_column('notes', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('notes', sa.Column('is_favorited', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index(op.f('ix_notes_is_favorited'), 'notes', ['is_favorited'], unique=False)

    op.create_table('note_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_note_templates_user_id'), 'note_templates', ['user_id'], unique=False)

    op.create_table('note_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_note_tags_user_id'), 'note_tags', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_note_tags_user_id'), table_name='note_tags')
    op.drop_table('note_tags')

    op.drop_index(op.f('ix_note_templates_user_id'), table_name='note_templates')
    op.drop_table('note_templates')

    op.drop_index(op.f('ix_notes_is_favorited'), table_name='notes')
    op.drop_column('notes', 'is_favorited')
    op.drop_column('notes', 'tags')

    op.drop_index(op.f('ix_chat_sessions_is_favorited'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'is_favorited')

    op.drop_index(op.f('ix_wiki_entries_is_favorited'), table_name='wiki_entries')
    op.drop_column('wiki_entries', 'is_favorited')
