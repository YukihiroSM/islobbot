"""Add training pdf message id field to user

Revision ID: 44138c2868f5
Revises: 1c0d25eb8362
Create Date: 2025-02-24 12:14:24.547312

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "44138c2868f5"
down_revision: Union[str, None] = "1c0d25eb8362"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users", sa.Column("training_pdf_message_id", sa.String(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "training_pdf_message_id")
    # ### end Alembic commands ###
