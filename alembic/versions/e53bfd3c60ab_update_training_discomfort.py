"""Update training discomfort

Revision ID: e53bfd3c60ab
Revises: 87d04b85b546
Create Date: 2025-01-21 08:49:12.259996

"""

from typing import Sequence, Union


from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e53bfd3c60ab"
down_revision: Union[str, None] = "87d04b85b546"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_training
        ALTER COLUMN training_discomfort
        TYPE BOOLEAN
        USING training_discomfort != 0;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_training
        ALTER COLUMN training_discomfort
        TYPE INTEGER
        USING CASE WHEN training_discomfort THEN 1 ELSE 0 END;
        """
    )
