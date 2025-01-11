"""Added timestamps to notifications

Revision ID: bfbc1339f760
Revises: a7793800b3d0
Create Date: 2025-01-10 18:51:48.168419

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bfbc1339f760"
down_revision: Union[str, None] = "a7793800b3d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("celery_tasksetmeta")
    op.drop_table("celery_taskmeta")
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
    op.create_table(
        "celery_taskmeta",
        sa.Column("id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "task_id", sa.VARCHAR(length=155), autoincrement=False, nullable=True
        ),
        sa.Column("status", sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.Column("result", postgresql.BYTEA(), autoincrement=False, nullable=True),
        sa.Column(
            "date_done", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column("traceback", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("name", sa.VARCHAR(length=155), autoincrement=False, nullable=True),
        sa.Column("args", postgresql.BYTEA(), autoincrement=False, nullable=True),
        sa.Column("kwargs", postgresql.BYTEA(), autoincrement=False, nullable=True),
        sa.Column("worker", sa.VARCHAR(length=155), autoincrement=False, nullable=True),
        sa.Column("retries", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("queue", sa.VARCHAR(length=155), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="celery_taskmeta_pkey"),
        sa.UniqueConstraint("task_id", name="celery_taskmeta_task_id_key"),
    )
    op.create_table(
        "celery_tasksetmeta",
        sa.Column("id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            "taskset_id", sa.VARCHAR(length=155), autoincrement=False, nullable=True
        ),
        sa.Column("result", postgresql.BYTEA(), autoincrement=False, nullable=True),
        sa.Column(
            "date_done", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.PrimaryKeyConstraint("id", name="celery_tasksetmeta_pkey"),
        sa.UniqueConstraint("taskset_id", name="celery_tasksetmeta_taskset_id_key"),
    )
    # ### end Alembic commands ###
