"""add image urls

Revision ID: b2c3d4e5f6a7
Revises: 8fe2dccc4c44
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "8fe2dccc4c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("nutrients") as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(length=1024), nullable=True))

    with op.batch_alter_table("nutrient_food_sources") as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nutrients") as batch_op:
        batch_op.drop_column("image_url")

    with op.batch_alter_table("nutrient_food_sources") as batch_op:
        batch_op.drop_column("image_url")
