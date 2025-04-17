"""Added timestamps to notifications

Revision ID: bfbc1339f760
Revises: a7793800b3d0
Create Date: 2025-01-10 18:51:48.168419

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bfbc1339f760"
down_revision: Union[str, None] = "a7793800b3d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "notification_preferences",
        sa.Column("last_execution_datetime", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "notification_preferences",
        sa.Column("next_execution_datetime", sa.DateTime(), nullable=True),
    )
    op.drop_column("notification_preferences", "notification_time")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "notification_preferences",
        sa.Column(
            "notification_time", postgresql.TIME(), autoincrement=False, nullable=False
        ),
    )
    op.drop_column("notification_preferences", "next_execution_datetime")
    op.drop_column("notification_preferences", "last_execution_datetime")
    # ### end Alembic commands ###
