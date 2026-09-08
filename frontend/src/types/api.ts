export type ModelStatus = "ready" | "not_ready";
export type SuspicionLevel = "low" | "medium" | "high" | "unavailable";
export type ScannerStatus =
  | "ready"
  | "unsupported_platform"
  | "not_initialized"
  | "location_access_denied"
  | "error";
export type DatabaseStatus = "ready" | "error";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  platform: string;
  windows_native_wifi_supported: boolean;
  scanner_status: ScannerStatus;
  model_status: ModelStatus;
  database_status: DatabaseStatus;
}

export interface HistoryScanSummary {
  scan_id: string;
  observed_at_utc: string;
  negotiated_api_version: number;
  interface_count: number;
  total_networks: number;
  feature_count: number;
  detection_count: number;
  anomaly_count: number;
  insufficient_history_count: number;
}

export interface HistoryDetectionSummary {
  detection_id: number;
  scan_id: string;
  observation_id: number;
  model_version_id: number | null;
  anomaly_score: number | null;
  threshold: number | null;
  is_anomaly: boolean | null;
  suspicion_level: SuspicionLevel;
  reason: string | null;
  inference_ms: number | null;
  created_at_utc: string;
}

export interface HistoryModelVersion {
  model_version_id: number;
  version_name: string;
  algorithm: string;
  feature_set_name: string;
  reference_sha256: string | null;
  scaler_sha256: string | null;
  model_sha256: string | null;
  threshold_sha256: string | null;
  threshold: number | null;
  active: boolean;
  created_at_utc: string;
  notes: string | null;
  detection_count: number;
}

export interface DashboardMetrics {
  scan_count: number;
  observation_count: number;
  unique_network_count: number;
  feature_count: number;
  detection_count: number;
  anomaly_count: number;
  normal_count: number;
  insufficient_history_count: number;
  model_version_count: number;
  analysis_coverage_rate: number;
  anomaly_rate_among_decided: number;
}

export interface DashboardOverviewResponse {
  generated_at_utc: string;
  system: {
    backend_version: string;
    platform: string;
    scanner_status: ScannerStatus;
    database_status: DatabaseStatus;
    model_status: ModelStatus;
  };
  metrics: DashboardMetrics;
  suspicion_distribution: {
    low: number;
    medium: number;
    high: number;
    unavailable: number;
  };
  latest_scan_at_utc: string | null;
  latest_detection_at_utc: string | null;
  active_model: HistoryModelVersion | null;
  recent_scans: HistoryScanSummary[];
  recent_detections: HistoryDetectionSummary[];
}

export interface DashboardTrendPoint {
  scan_id: string;
  observed_at_utc: string;
  network_count: number;
  feature_count: number;
  detection_count: number;
  anomaly_count: number;
  normal_count: number;
  insufficient_history_count: number;
}

export interface DashboardTrendsResponse {
  requested_limit: number;
  returned: number;
  points: DashboardTrendPoint[];
}

export interface NetworkFeatureValues {
  ssid_bssid_count: number | null;
  bssid_changed: number | null;
  security_changed: number | null;
  security_strength_delta: number | null;
}

export interface NetworkObservation {
  network_id: string;
  interface_guid: string;
  ssid: string;
  bssid: string;
  ssid_not_broadcast: boolean;
  rssi_dbm: number;
  link_quality: number;
  beacon_interval_ms: number;
  tsf_us: number;
  host_timestamp_100ns: number;
  center_frequency_khz: number;
  ds_parameter_channel: number | null;
  security_type: string;
  security_strength: number;
  security_source: string;
  phy_type: string;
  bss_type: string;
  supported_rates_mbps: number[];
  analysis: {
    status: "not_available" | "insufficient_history" | "ready";
    anomaly_score: number | null;
    threshold: number | null;
    is_anomaly: boolean | null;
    suspicion_level: SuspicionLevel;
    context_available: boolean | null;
    context_resolution: string | null;
    feature_complete: boolean | null;
    features?: NetworkFeatureValues | null;
    model_version: string | null;
    inference_ms: number | null;
    reason: string;
  };
}

export interface ScanResponse {
  scan_id: string;
  observed_at_utc: string;
  negotiated_api_version: number;
  interface_count: number;
  total_networks: number;
  interfaces: Array<{
    guid: string;
    description: string;
    state: string;
    bss_count: number;
  }>;
  networks: NetworkObservation[];
}

export interface NetworksResponse {
  has_scan: boolean;
  scan_id: string | null;
  observed_at_utc: string | null;
  total_networks: number;
  networks: NetworkObservation[];
}


export interface ApplicationSettingsResponse {
  values: {
    request_fresh_scan: boolean;
    scan_wait_seconds: number;
    auto_scan_enabled: boolean;
    auto_scan_interval_seconds: number;
    history_page_size: number;
    history_observation_page_size: number;
    dashboard_recent_scans: number;
    dashboard_recent_detections: number;
    dashboard_trend_limit: number;
    frontend_refresh_seconds: number;
    show_technical_details: boolean;
    high_anomaly_notifications: boolean;
    updated_at_utc: string;
  };
  model_status: ModelStatus;
  missing_model_artifacts: string[];
  scientific_policy: {
    reference_update_allowed: boolean;
    scaler_fit_allowed: boolean;
    scaler_partial_fit_allowed: boolean;
    model_fit_allowed: boolean;
    threshold_recalibration_allowed: boolean;
    artifact_paths_editable_via_settings: boolean;
  };
}



export interface PaginationMeta {
  limit: number;
  offset: number;
  returned: number;
  total: number;
}

export interface HistoryFeature {
  ssid_bssid_count: number | null;
  bssid_changed: number | null;
  security_changed: number | null;
  security_strength_delta: number | null;
  context_available: boolean;
  context_resolution: string;
  feature_complete: boolean;
}

export interface HistoryObservation {
  observation_id: number;
  scan_id: string;
  network_id: string;
  interface_guid_hash: string;
  ssid_hash: string | null;
  bssid_hash: string;
  ssid_not_broadcast: boolean;
  rssi_dbm: number;
  link_quality: number;
  beacon_interval_ms: number;
  tsf_us: number;
  host_timestamp_100ns: number;
  center_frequency_khz: number;
  ds_parameter_channel: number | null;
  security_type: string;
  security_strength: number;
  security_source: string;
  phy_type: string;
  bss_type: string;
  supported_rates_mbps: number[];
  features: HistoryFeature | null;
  detection: HistoryDetectionSummary | null;
}

export interface HistoryScanListResponse {
  pagination: PaginationMeta;
  items: HistoryScanSummary[];
}

export interface HistoryObservationListResponse {
  pagination: PaginationMeta;
  items: HistoryObservation[];
}

export interface HistoryScanDetailResponse {
  scan: HistoryScanSummary;
  observations: HistoryObservation[];
}

export interface HistoryDetectionListResponse {
  pagination: PaginationMeta;
  items: HistoryDetectionSummary[];
}

export interface HistoryDetectionDetailResponse {
  detection: HistoryDetectionSummary;
  observation: HistoryObservation;
  model_version: HistoryModelVersion | null;
}

export interface HistoryModelVersionListResponse {
  pagination: PaginationMeta;
  items: HistoryModelVersion[];
}


export interface ModelArtifactStatusResponse {
  status: ModelStatus;
  feature_set: string[];
  reference_path: string;
  scaler_path: string;
  model_path: string;
  threshold_path: string;
  missing_artifacts: string[];
  message: string;
}


export interface ApplicationSettingsUpdateRequest {
  request_fresh_scan?: boolean;
  scan_wait_seconds?: number;
  auto_scan_enabled?: boolean;
  auto_scan_interval_seconds?: number;
  history_page_size?: number;
  history_observation_page_size?: number;
  dashboard_recent_scans?: number;
  dashboard_recent_detections?: number;
  dashboard_trend_limit?: number;
  frontend_refresh_seconds?: number;
  show_technical_details?: boolean;
  high_anomaly_notifications?: boolean;
}


export interface DiagnosticsApplicationInfo {
  backend_version: string;
  platform: string;
  python_version: string;
  windows_native_wifi_supported: boolean;
}

export interface DiagnosticsRuntimeInfo {
  scanner_status: ScannerStatus;
  model_status: ModelStatus;
  database_status: DatabaseStatus;
}

export interface DiagnosticsDatabaseInfo {
  status: DatabaseStatus;
  dialect: string;
  scan_count: number | null;
  observation_count: number | null;
  feature_count: number | null;
  detection_count: number | null;
  model_version_count: number | null;
  error_present: boolean;
}

export interface DiagnosticsModelInfo {
  status: ModelStatus;
  feature_set: string[];
  missing_artifacts: string[];
  artifact_available: Record<"reference" | "scaler" | "model" | "threshold", boolean>;
  active_model: HistoryModelVersion | null;
}

export interface DiagnosticsActivityInfo {
  latest_scan_at_utc: string | null;
  latest_scan_network_count: number | null;
  latest_scan_detection_count: number | null;
  latest_scan_anomaly_count: number | null;
  latest_scan_insufficient_history_count: number | null;
  latest_detection_at_utc: string | null;
  latest_detection_suspicion_level: string | null;
  latest_detection_is_anomaly: boolean | null;
}

export interface DiagnosticsPrivacyInfo {
  clear_wifi_identifiers_included: false;
  observation_records_included: false;
  raw_ie_bytes_included: false;
  filesystem_paths_included: false;
  environment_variables_included: false;
}

export interface DiagnosticsSupportBundleResponse {
  schema_version: "support_bundle_v1";
  generated_at_utc: string;
  application: DiagnosticsApplicationInfo;
  runtime: DiagnosticsRuntimeInfo;
  database: DiagnosticsDatabaseInfo;
  settings: ApplicationSettingsResponse["values"] | null;
  model: DiagnosticsModelInfo;
  activity: DiagnosticsActivityInfo;
  privacy: DiagnosticsPrivacyInfo;
  warnings: string[];
}
