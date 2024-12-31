"""Added training and morning quiz models

Revision ID: ed19b7987db7
Revises: 64b1805f6da0
Create Date: 2024-12-31 20:28:38.644205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed19b7987db7'
down_revision: Union[str, None] = '64b1805f6da0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_morning_quiz',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('quiz_datetime', sa.DateTime(), nullable=False),
    sa.Column('user_feelings', sa.Integer(), nullable=False),
    sa.Column('user_feelings_comment', sa.String(), nullable=True),
    sa.Column('user_sleeping_hours', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_morning_quiz_id'), 'user_morning_quiz', ['id'], unique=False)
    op.create_table('user_training',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('mark_before_training', sa.Integer(), nullable=False),
    sa.Column('training_start_date', sa.DateTime(), nullable=True),
    sa.Column('training_finish_date', sa.DateTime(), nullable=True),
    sa.Column('training_duration', sa.Time(), nullable=True),
    sa.Column('training_hardness', sa.Integer(), nullable=True),
    sa.Column('training_discomfort', sa.Integer(), nullable=True),
    sa.Column('stress_on_next_day', sa.Integer(), nullable=True),
    sa.Column('soreness_on_next_day', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_training_id'), 'user_training', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_training_id'), table_name='user_training')
    op.drop_table('user_training')
    op.drop_index(op.f('ix_user_morning_quiz_id'), table_name='user_morning_quiz')
    op.drop_table('user_morning_quiz')
    # ### end Alembic commands ###
