"""Update notification types

Revision ID: b374b5648b1b
Revises: 7fd5663f8a52
Create Date: 2025-01-20 21:10:33.194618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = 'b374b5648b1b'
down_revision: Union[str, None] = '7fd5663f8a52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Add a new value to the existing enum
    op.execute("ALTER TYPE notificationtype ADD VALUE 'CUSTOM_NOTIFICATION'")
    op.execute("ALTER TYPE notificationtype ADD VALUE 'PRE_TRAINING_NOTIFICATION'")
    op.execute("ALTER TYPE notificationtype ADD VALUE 'TRAINING_REMINDER_NOTIFICATION'")
    op.execute("ALTER TYPE notificationtype ADD VALUE 'STOP_TRAINING_NOTIFICATION'")

def downgrade():
    # Note: PostgreSQL does not support removing values from an enum directly.
    # If you need to remove a value, you'd need to create a new enum type,
    # migrate the column, and drop the old enum.
    pass
