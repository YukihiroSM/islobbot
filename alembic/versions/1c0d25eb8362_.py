"""empty message

Revision ID: 1c0d25eb8362
Revises: e53bfd3c60ab
Create Date: 2025-01-21 09:37:55.752683

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c0d25eb8362"
down_revision: Union[str, None] = "e53bfd3c60ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'morning_notification'"
    )
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'custom_notification'"
    )
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'pre_training_reminder_notification'"
    )
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'training_reminder_notification'"
    )
    op.execute(
        "ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'stop_training_notification'"
    )


def downgrade() -> None:
    pass
