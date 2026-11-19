"""update ingestion run status constraint

Revision ID: de66caffd14d
Revises: 38d62a1a6a02
Create Date: 2026-11-19 16:20:07.323028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de66caffd14d'
down_revision: Union[str, Sequence[str], None] = '38d62a1a6a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_ingestion_runs_status",
        "ingestion_runs",
        type_="check",
    )

    op.create_check_constraint(
        "ck_ingestion_runs_status",
        "ingestion_runs",
        "status IN ('running', 'published', 'processing', 'success', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ingestion_runs_status",
        "ingestion_runs",
        type_="check",
    )

    op.create_check_constraint(
        "ck_ingestion_runs_status",
        "ingestion_runs",
        "status IN ('running', 'success', 'failed')",
    )
