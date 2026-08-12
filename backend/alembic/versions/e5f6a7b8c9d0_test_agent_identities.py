"""test agent identities

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 新的實驗性模式 "test_agent"(見 app/agent/test_agent/)要記住這個 session
    # 一開始選了哪些 fab/function 身分 - 見 models/chat.py 的 ChatSession
    # docstring。
    op.add_column('chat_sessions', sa.Column('test_agent_identities_json', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_sessions', 'test_agent_identities_json')
