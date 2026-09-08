from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.types import TypeDecorator

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(
        self,
        dialect,
    ):
        return dialect.type_descriptor(
            DateTime(timezone=True)
        )

    def process_bind_param(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        value = value.astimezone(
            timezone.utc
        )

        if dialect.name == "sqlite":
            return value.replace(
                tzinfo=None
            )

        return value

    def process_result_value(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )


class Base(DeclarativeBase):
    pass


class ScanSession(Base):
    __tablename__ = "scan_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    observed_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        index=True,
    )
    negotiated_api_version: Mapped[int] = mapped_column(Integer, nullable=False)
    interface_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_networks: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
    )

    observations: Mapped[list["NetworkObservation"]] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
    )
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="scan_session",
        cascade="all, delete-orphan",
    )


class NetworkObservation(Base):
    __tablename__ = "network_observation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[str] = mapped_column(
        ForeignKey("scan_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    network_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    interface_guid_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ssid_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    bssid_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    ssid_not_broadcast: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    rssi_dbm: Mapped[int] = mapped_column(Integer, nullable=False)
    link_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    beacon_interval_ms: Mapped[float] = mapped_column(Float, nullable=False)
    tsf_us: Mapped[int] = mapped_column(Integer, nullable=False)
    host_timestamp_100ns: Mapped[int] = mapped_column(Integer, nullable=False)
    center_frequency_khz: Mapped[int] = mapped_column(Integer, nullable=False)
    ds_parameter_channel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_type: Mapped[str] = mapped_column(String(64), nullable=False)
    security_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    security_source: Mapped[str] = mapped_column(String(64), nullable=False)
    phy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    bss_type: Mapped[str] = mapped_column(String(64), nullable=False)
    supported_rates_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
    )

    scan_session: Mapped["ScanSession"] = relationship(
        back_populates="observations"
    )
    features: Mapped["NetworkFeatures | None"] = relationship(
        back_populates="observation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    detections: Mapped[list["Detection"]] = relationship(
        back_populates="observation",
        cascade="all, delete-orphan",
    )


class NetworkFeatures(Base):
    __tablename__ = "network_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network_observation_id: Mapped[int] = mapped_column(
        ForeignKey("network_observation.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    ssid_bssid_count: Mapped[float | None] = mapped_column(Float, nullable=True)
    bssid_changed: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_changed: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_strength_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    context_resolution: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="unresolved",
    )
    feature_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
    )

    observation: Mapped["NetworkObservation"] = relationship(
        back_populates="features"
    )


class ModelVersion(Base):
    __tablename__ = "model_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_set_name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    model_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    scaler_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    threshold_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    threshold: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    detections: Mapped[list["Detection"]] = relationship(
        back_populates="model_version"
    )


class Detection(Base):
    __tablename__ = "detection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[str] = mapped_column(
        ForeignKey("scan_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    network_observation_id: Mapped[int] = mapped_column(
        ForeignKey("network_observation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_version.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_anomaly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    suspicion_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unavailable",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    inference_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        index=True,
    )

    scan_session: Mapped["ScanSession"] = relationship(
        back_populates="detections"
    )
    observation: Mapped["NetworkObservation"] = relationship(
        back_populates="detections"
    )
    model_version: Mapped["ModelVersion | None"] = relationship(
        back_populates="detections"
    )


Index(
    "ix_network_observation_scan_network",
    NetworkObservation.scan_session_id,
    NetworkObservation.network_id,
)
Index(
    "ix_detection_scan_anomaly",
    Detection.scan_session_id,
    Detection.is_anomaly,
)



class ApplicationSettings(Base):
    __tablename__ = "application_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    request_fresh_scan: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    scan_wait_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=4.2,
    )

    auto_scan_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    auto_scan_interval_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=30.0,
    )

    history_page_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
    )

    history_observation_page_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )

    dashboard_recent_scans: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    dashboard_recent_detections: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    dashboard_trend_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    frontend_refresh_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    show_technical_details: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    high_anomaly_notifications: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    updated_at_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
