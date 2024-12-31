"""Add canceled field for training

Revision ID: a7793800b3d0
Revises: ed19b7987db7
Create Date: 2024-12-31 22:30:43.041919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7793800b3d0'
down_revision: Union[str, None] = 'ed19b7987db7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_training', sa.Column('canceled', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_training', 'canceled')
    # ### end Alembic commands ###
