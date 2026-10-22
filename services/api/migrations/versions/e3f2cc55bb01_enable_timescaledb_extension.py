"""enable timescaledb extension

Revision ID: e3f2cc55bb01
Revises: 15ad7071f1ec
Create Date: 2026-10-22 11:50:14.358704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f2cc55bb01'
down_revision: Union[str, Sequence[str], None] = '15ad7071f1ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS timescaledb;")
