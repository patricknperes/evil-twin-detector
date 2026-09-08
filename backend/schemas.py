from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    platform: str
    windows_native_wifi_supported: bool
    scanner_status: Literal[
        "ready",
        "unsupported_platform",
        "not_initialized",
        "location_access_denied",
        "error",
    ]
    model_status: Literal[
        "ready",
        "not_ready",
    ]
    database_status: Literal[
        "ready",
        "error",
    ]


class ScanRequest(BaseModel):
    """
    Explicit fields override persisted application preferences.

    When request_fresh_scan/scan_wait_seconds are omitted, the backend
    resolves them from ApplicationSettings.
    """

    request_fresh_scan: bool | None = None
    scan_wait_seconds: float | None = Field(
        default=None,
        ge=0,
        le=15,
    )
    interface_guid: str | None = None


class InterfaceSummary(BaseModel):
    guid: str
    description: str
    state_code: int
    state: str
    requested_fresh_scan: bool
    scan_wait_seconds: float
    wait_strategy: str
    bss_count: int


class NetworkFeatureValues(BaseModel):
    ssid_bssid_count: float | None = None
    bssid_changed: float | None = None
    security_changed: float | None = None
    security_strength_delta: float | None = None


class NetworkAnalysisState(BaseModel):
    status: Literal[
        "not_available",
        "insufficient_history",
        "ready",
    ] = "not_available"

    anomaly_score: float | None = None
    threshold: float | None = None
    is_anomaly: bool | None = None

    suspicion_level: Literal[
        "unavailable",
        "low",
        "medium",
        "high",
    ] = "unavailable"

    context_available: bool | None = None
    context_resolution: str | None = None
    feature_complete: bool | None = None
    features: NetworkFeatureValues | None = None

    model_version: str | None = None
    inference_ms: float | None = None

    reason: str = (
        "Real desktop model artifacts are not available yet."
    )


class NetworkObservationResponse(BaseModel):
    network_id: str
    interface_guid: str
    ssid: str
    bssid: str
    ssid_not_broadcast: bool
    rssi_dbm: int
    link_quality: int
    beacon_interval_ms: float
    tsf_us: int
    host_timestamp_100ns: int
    center_frequency_khz: int
    ds_parameter_channel: int | None = None
    security_type: str
    security_strength: int
    security_source: str
    phy_type: str
    bss_type: str
    supported_rates_mbps: list[float]

    analysis: NetworkAnalysisState = Field(
        default_factory=NetworkAnalysisState
    )


class ScanResponse(BaseModel):
    scan_id: str
    observed_at_utc: datetime
    negotiated_api_version: int
    interface_count: int
    total_networks: int
    interfaces: list[InterfaceSummary]
    networks: list[NetworkObservationResponse]


class NetworksResponse(BaseModel):
    has_scan: bool
    scan_id: str | None = None
    observed_at_utc: datetime | None = None
    total_networks: int = 0
    networks: list[NetworkObservationResponse] = Field(
        default_factory=list
    )


class ModelStatusResponse(BaseModel):
    status: Literal[
        "ready",
        "not_ready",
    ]

    feature_set: list[str]

    reference_path: str
    scaler_path: str
    model_path: str
    threshold_path: str

    missing_artifacts: list[str]
    message: str


class DatabaseStatusResponse(BaseModel):
    status: Literal[
        "ready",
        "error",
    ]

    dialect: str

    scan_count: int | None = None
    observation_count: int | None = None
    feature_count: int | None = None
    detection_count: int | None = None
    model_version_count: int | None = None

    error: str | None = None


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    returned: int
    total: int


class HistoryScanSummary(BaseModel):
    scan_id: str
    observed_at_utc: datetime
    negotiated_api_version: int
    interface_count: int
    total_networks: int
    feature_count: int
    detection_count: int
    anomaly_count: int
    insufficient_history_count: int


class HistoryScanListResponse(BaseModel):
    pagination: PaginationMeta
    items: list[HistoryScanSummary]


class HistoryFeatureResponse(BaseModel):
    ssid_bssid_count: float | None = None
    bssid_changed: float | None = None
    security_changed: float | None = None
    security_strength_delta: float | None = None
    context_available: bool
    context_resolution: str
    feature_complete: bool


class HistoryDetectionSummary(BaseModel):
    detection_id: int
    scan_id: str
    observation_id: int
    model_version_id: int | None = None
    anomaly_score: float | None = None
    threshold: float | None = None
    is_anomaly: bool | None = None
    suspicion_level: str
    reason: str | None = None
    inference_ms: float | None = None
    created_at_utc: datetime


class HistoryObservationResponse(BaseModel):
    observation_id: int
    scan_id: str
    network_id: str
    interface_guid_hash: str
    ssid_hash: str | None = None
    bssid_hash: str
    ssid_not_broadcast: bool
    rssi_dbm: int
    link_quality: int
    beacon_interval_ms: float
    tsf_us: int
    host_timestamp_100ns: int
    center_frequency_khz: int
    ds_parameter_channel: int | None = None
    security_type: str
    security_strength: int
    security_source: str
    phy_type: str
    bss_type: str
    supported_rates_mbps: list[float]
    features: HistoryFeatureResponse | None = None
    detection: HistoryDetectionSummary | None = None


class HistoryObservationListResponse(BaseModel):
    pagination: PaginationMeta
    items: list[HistoryObservationResponse]


class HistoryScanDetailResponse(BaseModel):
    scan: HistoryScanSummary
    observations: list[HistoryObservationResponse]


class HistoryModelVersionResponse(BaseModel):
    model_version_id: int
    version_name: str
    algorithm: str
    feature_set_name: str
    reference_sha256: str | None = None
    scaler_sha256: str | None = None
    model_sha256: str | None = None
    threshold_sha256: str | None = None
    threshold: float | None = None
    active: bool
    created_at_utc: datetime
    notes: str | None = None
    detection_count: int


class HistoryDetectionDetailResponse(BaseModel):
    detection: HistoryDetectionSummary
    observation: HistoryObservationResponse
    model_version: HistoryModelVersionResponse | None = None


class HistoryDetectionListResponse(BaseModel):
    pagination: PaginationMeta
    items: list[HistoryDetectionSummary]


class HistoryModelVersionListResponse(BaseModel):
    pagination: PaginationMeta
    items: list[HistoryModelVersionResponse]



class DashboardSystemStatus(BaseModel):
    backend_version: str
    platform: str
    scanner_status: Literal[
        "ready",
        "unsupported_platform",
        "not_initialized",
        "location_access_denied",
        "error",
    ]
    database_status: Literal[
        "ready",
        "error",
    ]
    model_status: Literal[
        "ready",
        "not_ready",
    ]


class DashboardMetrics(BaseModel):
    scan_count: int
    observation_count: int
    unique_network_count: int
    feature_count: int
    detection_count: int
    anomaly_count: int
    normal_count: int
    insufficient_history_count: int
    model_version_count: int
    analysis_coverage_rate: float
    anomaly_rate_among_decided: float


class SuspicionDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    unavailable: int = 0


class DashboardOverviewResponse(BaseModel):
    generated_at_utc: datetime
    system: DashboardSystemStatus
    metrics: DashboardMetrics
    suspicion_distribution: SuspicionDistribution
    latest_scan_at_utc: datetime | None = None
    latest_detection_at_utc: datetime | None = None
    active_model: HistoryModelVersionResponse | None = None
    recent_scans: list[HistoryScanSummary] = Field(
        default_factory=list
    )
    recent_detections: list[HistoryDetectionSummary] = Field(
        default_factory=list
    )


class DashboardTrendPoint(BaseModel):
    scan_id: str
    observed_at_utc: datetime
    network_count: int
    feature_count: int
    detection_count: int
    anomaly_count: int
    normal_count: int
    insufficient_history_count: int


class DashboardTrendsResponse(BaseModel):
    requested_limit: int
    returned: int
    points: list[DashboardTrendPoint] = Field(
        default_factory=list
    )



class ApplicationSettingsValues(BaseModel):
    request_fresh_scan: bool
    scan_wait_seconds: float
    auto_scan_enabled: bool
    auto_scan_interval_seconds: float
    history_page_size: int
    history_observation_page_size: int
    dashboard_recent_scans: int
    dashboard_recent_detections: int
    dashboard_trend_limit: int
    frontend_refresh_seconds: int
    show_technical_details: bool
    high_anomaly_notifications: bool
    updated_at_utc: datetime


class ApplicationSettingsUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    request_fresh_scan: bool | None = None

    scan_wait_seconds: float | None = Field(
        default=None,
        ge=0,
        le=15,
    )

    auto_scan_enabled: bool | None = None

    auto_scan_interval_seconds: float | None = Field(
        default=None,
        ge=10,
        le=3600,
    )

    history_page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    history_observation_page_size: int | None = Field(
        default=None,
        ge=1,
        le=200,
    )

    dashboard_recent_scans: int | None = Field(
        default=None,
        ge=0,
        le=20,
    )

    dashboard_recent_detections: int | None = Field(
        default=None,
        ge=0,
        le=20,
    )

    dashboard_trend_limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    frontend_refresh_seconds: int | None = Field(
        default=None,
        ge=2,
        le=300,
    )

    show_technical_details: bool | None = None
    high_anomaly_notifications: bool | None = None


class ApplicationSettingsConstraints(BaseModel):
    scan_wait_seconds: str = "0..15"
    auto_scan_interval_seconds: str = "10..3600"
    history_page_size: str = "1..100"
    history_observation_page_size: str = "1..200"
    dashboard_recent_scans: str = "0..20"
    dashboard_recent_detections: str = "0..20"
    dashboard_trend_limit: str = "1..100"
    frontend_refresh_seconds: str = "2..300"


class ScientificRuntimePolicy(BaseModel):
    reference_update_allowed: bool = False
    scaler_fit_allowed: bool = False
    scaler_partial_fit_allowed: bool = False
    model_fit_allowed: bool = False
    threshold_recalibration_allowed: bool = False
    artifact_paths_editable_via_settings: bool = False


class ApplicationSettingsResponse(BaseModel):
    values: ApplicationSettingsValues
    constraints: ApplicationSettingsConstraints
    model_status: Literal[
        "ready",
        "not_ready",
    ]
    missing_model_artifacts: list[str]
    scientific_policy: ScientificRuntimePolicy


class DiagnosticsApplicationInfo(BaseModel):
    backend_version: str
    platform: str
    python_version: str
    windows_native_wifi_supported: bool


class DiagnosticsRuntimeInfo(BaseModel):
    scanner_status: str
    model_status: Literal[
        "ready",
        "not_ready",
    ]
    database_status: Literal[
        "ready",
        "error",
    ]


class DiagnosticsDatabaseInfo(BaseModel):
    status: Literal[
        "ready",
        "error",
    ]
    dialect: str
    scan_count: int | None = None
    observation_count: int | None = None
    feature_count: int | None = None
    detection_count: int | None = None
    model_version_count: int | None = None
    error_present: bool = False


class DiagnosticsModelInfo(BaseModel):
    status: Literal[
        "ready",
        "not_ready",
    ]
    feature_set: list[str]
    missing_artifacts: list[str]
    artifact_available: dict[str, bool]
    active_model: HistoryModelVersionResponse | None = None


class DiagnosticsActivityInfo(BaseModel):
    latest_scan_at_utc: datetime | None = None
    latest_scan_network_count: int | None = None
    latest_scan_detection_count: int | None = None
    latest_scan_anomaly_count: int | None = None
    latest_scan_insufficient_history_count: int | None = None
    latest_detection_at_utc: datetime | None = None
    latest_detection_suspicion_level: str | None = None
    latest_detection_is_anomaly: bool | None = None


class DiagnosticsPrivacyInfo(BaseModel):
    clear_wifi_identifiers_included: bool = False
    observation_records_included: bool = False
    raw_ie_bytes_included: bool = False
    filesystem_paths_included: bool = False
    environment_variables_included: bool = False


class DiagnosticsSupportBundleResponse(BaseModel):
    schema_version: Literal[
        "support_bundle_v1"
    ] = "support_bundle_v1"
    generated_at_utc: datetime
    application: DiagnosticsApplicationInfo
    runtime: DiagnosticsRuntimeInfo
    database: DiagnosticsDatabaseInfo
    settings: ApplicationSettingsValues | None = None
    model: DiagnosticsModelInfo
    activity: DiagnosticsActivityInfo
    privacy: DiagnosticsPrivacyInfo = Field(
        default_factory=DiagnosticsPrivacyInfo
    )
    warnings: list[str] = Field(
        default_factory=list
    )
