"""initial local persistence schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_session",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("negotiated_api_version", sa.Integer(), nullable=False),
        sa.Column("interface_count", sa.Integer(), nullable=False),
        sa.Column("total_networks", sa.Integer(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scan_session_observed_at_utc",
        "scan_session",
        ["observed_at_utc"],
    )

    op.create_table(
        "network_observation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_session_id",
            sa.String(length=36),
            sa.ForeignKey("scan_session.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("network_id", sa.String(length=64), nullable=False),
        sa.Column("interface_guid_hash", sa.String(length=64), nullable=False),
        sa.Column("ssid_hash", sa.String(length=64), nullable=True),
        sa.Column("bssid_hash", sa.String(length=64), nullable=False),
        sa.Column("ssid_not_broadcast", sa.Boolean(), nullable=False),
        sa.Column("rssi_dbm", sa.Integer(), nullable=False),
        sa.Column("link_quality", sa.Integer(), nullable=False),
        sa.Column("beacon_interval_ms", sa.Float(), nullable=False),
        sa.Column("tsf_us", sa.Integer(), nullable=False),
        sa.Column("host_timestamp_100ns", sa.Integer(), nullable=False),
        sa.Column("center_frequency_khz", sa.Integer(), nullable=False),
        sa.Column("ds_parameter_channel", sa.Integer(), nullable=True),
        sa.Column("security_type", sa.String(length=64), nullable=False),
        sa.Column("security_strength", sa.Integer(), nullable=False),
        sa.Column("security_source", sa.String(length=64), nullable=False),
        sa.Column("phy_type", sa.String(length=64), nullable=False),
        sa.Column("bss_type", sa.String(length=64), nullable=False),
        sa.Column("supported_rates_json", sa.Text(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_network_observation_scan_session_id",
        "network_observation",
        ["scan_session_id"],
    )
    op.create_index(
        "ix_network_observation_network_id",
        "network_observation",
        ["network_id"],
    )
    op.create_index(
        "ix_network_observation_ssid_hash",
        "network_observation",
        ["ssid_hash"],
    )
    op.create_index(
        "ix_network_observation_bssid_hash",
        "network_observation",
        ["bssid_hash"],
    )
    op.create_index(
        "ix_network_observation_scan_network",
        "network_observation",
        ["scan_session_id", "network_id"],
    )

    op.create_table(
        "network_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "network_observation_id",
            sa.Integer(),
            sa.ForeignKey("network_observation.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ssid_bssid_count", sa.Float(), nullable=True),
        sa.Column("bssid_changed", sa.Float(), nullable=True),
        sa.Column("security_changed", sa.Float(), nullable=True),
        sa.Column("security_strength_delta", sa.Float(), nullable=True),
        sa.Column("context_available", sa.Boolean(), nullable=False),
        sa.Column("context_resolution", sa.String(length=64), nullable=False),
        sa.Column("feature_complete", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_network_features_network_observation_id",
        "network_features",
        ["network_observation_id"],
        unique=True,
    )

    op.create_table(
        "model_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("version_name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column("feature_set_name", sa.String(length=128), nullable=False),
        sa.Column("model_sha256", sa.String(length=64), nullable=True),
        sa.Column("scaler_sha256", sa.String(length=64), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_model_version_version_name",
        "model_version",
        ["version_name"],
        unique=True,
    )
    op.create_index(
        "ix_model_version_active",
        "model_version",
        ["active"],
    )

    op.create_table(
        "detection",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_session_id",
            sa.String(length=36),
            sa.ForeignKey("scan_session.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "network_observation_id",
            sa.Integer(),
            sa.ForeignKey("network_observation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            sa.Integer(),
            sa.ForeignKey("model_version.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=True),
        sa.Column("suspicion_level", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("inference_ms", sa.Float(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_detection_scan_session_id",
        "detection",
        ["scan_session_id"],
    )
    op.create_index(
        "ix_detection_network_observation_id",
        "detection",
        ["network_observation_id"],
    )
    op.create_index(
        "ix_detection_model_version_id",
        "detection",
        ["model_version_id"],
    )
    op.create_index(
        "ix_detection_created_at_utc",
        "detection",
        ["created_at_utc"],
    )
    op.create_index(
        "ix_detection_scan_anomaly",
        "detection",
        ["scan_session_id", "is_anomaly"],
    )


def downgrade() -> None:
    op.drop_index("ix_detection_scan_anomaly", table_name="detection")
    op.drop_index("ix_detection_created_at_utc", table_name="detection")
    op.drop_index("ix_detection_model_version_id", table_name="detection")
    op.drop_index("ix_detection_network_observation_id", table_name="detection")
    op.drop_index("ix_detection_scan_session_id", table_name="detection")
    op.drop_table("detection")

    op.drop_index("ix_model_version_active", table_name="model_version")
    op.drop_index("ix_model_version_version_name", table_name="model_version")
    op.drop_table("model_version")

    op.drop_index(
        "ix_network_features_network_observation_id",
        table_name="network_features",
    )
    op.drop_table("network_features")

    op.drop_index(
        "ix_network_observation_scan_network",
        table_name="network_observation",
    )
    op.drop_index(
        "ix_network_observation_bssid_hash",
        table_name="network_observation",
    )
    op.drop_index(
        "ix_network_observation_ssid_hash",
        table_name="network_observation",
    )
    op.drop_index(
        "ix_network_observation_network_id",
        table_name="network_observation",
    )
    op.drop_index(
        "ix_network_observation_scan_session_id",
        table_name="network_observation",
    )
    op.drop_table("network_observation")

    op.drop_index(
        "ix_scan_session_observed_at_utc",
        table_name="scan_session",
    )
    op.drop_table("scan_session")
