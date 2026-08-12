"""drop process_agent_files

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # process_agent 改成跟 orchestrator 共用同一個 LangGraph StoreBackend
    # (namespace 用 session_id 隔開),不再需要自己複製/持久化一份 files -
    # 見 app/agent/process_agent/tools.py 的模組說明。這個欄位變成死欄位。
    op.drop_column('chat_sessions', 'process_agent_files')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('chat_sessions', sa.Column('process_agent_files', sa.Text(), nullable=True))
