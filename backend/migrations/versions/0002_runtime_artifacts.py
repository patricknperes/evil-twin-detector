"""add contextual runtime artifact hashes

Revision ID: 0002_runtime_artifacts
Revises: 0001_initial_schema
Create Date: 2026-08-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_runtime_artifacts"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_version",
        sa.Column(
            "reference_sha256",
            sa.String(
                length=64
            ),
            nullable=True,
        ),
    )

    op.add_column(
        "model_version",
        sa.Column(
            "threshold_sha256",
            sa.String(
                length=64
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "model_version",
        "threshold_sha256",
    )

    op.drop_column(
        "model_version",
        "reference_sha256",
    )
