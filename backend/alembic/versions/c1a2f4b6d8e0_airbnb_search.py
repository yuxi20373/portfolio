"""airbnb search

Revision ID: c1a2f4b6d8e0
Revises: 8b4e6f1a9c2d
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2f4b6d8e0'
down_revision: Union[str, Sequence[str], None] = '8b4e6f1a9c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('airbnb_searches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=False),
    sa.Column('check_in', sa.Date(), nullable=False),
    sa.Column('check_out', sa.Date(), nullable=False),
    sa.Column('adults', sa.Integer(), nullable=False),
    sa.Column('children', sa.Integer(), nullable=False),
    sa.Column('infants', sa.Integer(), nullable=False),
    sa.Column('pets', sa.Integer(), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False),
    sa.Column('snapshot_id', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('results', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_airbnb_searches_location'), 'airbnb_searches', ['location'], unique=False)
    op.create_index(op.f('ix_airbnb_searches_user_id'), 'airbnb_searches', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_airbnb_searches_user_id'), table_name='airbnb_searches')
    op.drop_index(op.f('ix_airbnb_searches_location'), table_name='airbnb_searches')
    op.drop_table('airbnb_searches')
