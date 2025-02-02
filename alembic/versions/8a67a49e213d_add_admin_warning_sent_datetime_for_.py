"""add admin warning sent datetime for notifications preference

Revision ID: 8a67a49e213d
Revises: 4038a43a146e
Create Date: 2025-01-20 17:06:06.235902

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a67a49e213d"
down_revision: Union[str, None] = "4038a43a146e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "notification_preferences",
        sa.Column("admin_warning_sent", sa.DateTime(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("notification_preferences", "admin_warning_sent")
    # ### end Alembic commands ###
