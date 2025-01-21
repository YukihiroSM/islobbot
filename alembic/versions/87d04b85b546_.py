"""empty message

Revision ID: 87d04b85b546
Revises: b374b5648b1b
Create Date: 2025-01-20 23:46:07.336274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87d04b85b546'
down_revision: Union[str, None] = 'b374b5648b1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE 'PRE_TRAINING_REMINDER_NOTIFICATION'")


def downgrade() -> None:
    pass
