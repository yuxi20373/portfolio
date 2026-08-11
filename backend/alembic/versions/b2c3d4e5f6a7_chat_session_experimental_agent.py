"""chat session experimental_agent

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 讓 chat session 可以切去實驗性的 deep agent 實作(見 /da-subagent 指令,
    # models/chat.py 的 ChatSession docstring)- 跟 agent_mode 是分開獨立的
    # 欄位,不動原本的 agent_mode 邏輯。
    op.add_column('chat_sessions', sa.Column('experimental_agent', sa.String(length=30), nullable=True))
    op.add_column('chat_sessions', sa.Column('da_subagent_files', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_sessions', 'da_subagent_files')
    op.drop_column('chat_sessions', 'experimental_agent')
