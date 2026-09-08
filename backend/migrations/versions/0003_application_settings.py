"""add application settings

Revision ID: 0003_application_settings
Revises: 0002_runtime_artifacts
Create Date: 2026-08-31
"""

from typing import (
    Sequence,
    Union,
)

from alembic import op
import sqlalchemy as sa


revision: str = (
    "0003_application_settings"
)

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0002_runtime_artifacts"

branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_settings",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "request_fresh_scan",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "scan_wait_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "auto_scan_enabled",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "auto_scan_interval_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "history_page_size",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "history_observation_page_size",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "dashboard_recent_scans",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "dashboard_recent_detections",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "dashboard_trend_limit",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "frontend_refresh_seconds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "show_technical_details",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "high_anomaly_notifications",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "updated_at_utc",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table(
        "application_settings"
    )
