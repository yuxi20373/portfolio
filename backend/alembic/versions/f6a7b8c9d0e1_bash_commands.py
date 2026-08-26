"""bash commands reference table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Bash 指令查詢頁(見 routers/bash_reference.py)用的共用參考字典 - 所有
    # 使用者共用同一份,不分使用者,見 models/bash_command.py。
    op.create_table(
        'bash_commands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('command', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_bash_commands_command', 'bash_commands', ['command'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_bash_commands_command', table_name='bash_commands')
    op.drop_table('bash_commands')
