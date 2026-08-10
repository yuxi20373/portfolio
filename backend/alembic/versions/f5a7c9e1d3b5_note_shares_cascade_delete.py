"""note_shares cascade delete on note

Revision ID: f5a7c9e1d3b5
Revises: e4f6a8c0b2d3
Create Date: 2026-08-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f5a7c9e1d3b5'
down_revision: Union[str, Sequence[str], None] = 'e4f6a8c0b2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 原本的 FK 沒有 ON DELETE CASCADE - 刪除一個已經被分享出去的筆記會直接
    # 500(ForeignKeyViolation),因為 note_shares 還留著參照它的紀錄。
    op.drop_constraint('note_shares_note_id_fkey', 'note_shares', type_='foreignkey')
    op.create_foreign_key(
        'note_shares_note_id_fkey', 'note_shares', 'notes', ['note_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('note_shares_note_id_fkey', 'note_shares', type_='foreignkey')
    op.create_foreign_key('note_shares_note_id_fkey', 'note_shares', 'notes', ['note_id'], ['id'])
