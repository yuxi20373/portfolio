"""calendar events

Revision ID: 8b4e6f1a9c2d
Revises: 5a1c9d7e2f3b
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b4e6f1a9c2d'
down_revision: Union[str, Sequence[str], None] = '5a1c9d7e2f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('calendar_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('event_date', sa.Date(), nullable=False),
    sa.Column('remind_at', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_events_event_date'), 'calendar_events', ['event_date'], unique=False)
    op.create_index(op.f('ix_calendar_events_user_id'), 'calendar_events', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_calendar_events_user_id'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_event_date'), table_name='calendar_events')
    op.drop_table('calendar_events')
