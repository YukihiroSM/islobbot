"""Add user weight to morning quiz model

Revision ID: 8f2f1cbe8e42
Revises: 44138c2868f5
Create Date: 2025-03-27 23:59:38.664523

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f2f1cbe8e42"
down_revision: Union[str, None] = "44138c2868f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "user_morning_quiz", sa.Column("user_weight", sa.Float(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user_morning_quiz", "user_weight")
    # ### end Alembic commands ###
