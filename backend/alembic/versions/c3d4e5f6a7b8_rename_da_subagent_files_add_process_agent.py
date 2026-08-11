"""rename da_subagent_files, add process_agent_files

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # app/agent/da_subagent/ -> app/agent/orchestrator/,新增第二種實驗性
    # 實作 app/agent/process_agent/(見 models/chat.py 的 ChatSession
    # docstring)。
    op.alter_column('chat_sessions', 'da_subagent_files', new_column_name='orchestrator_files')
    op.add_column('chat_sessions', sa.Column('process_agent_files', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_sessions', 'process_agent_files')
    op.alter_column('chat_sessions', 'orchestrator_files', new_column_name='da_subagent_files')
