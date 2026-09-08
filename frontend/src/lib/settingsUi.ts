import type {
  ApplicationSettingsResponse,
  ApplicationSettingsUpdateRequest
} from "../types/api";

export type SettingsValues =
  ApplicationSettingsResponse["values"];

export function editableSettings(
  values: SettingsValues
): ApplicationSettingsUpdateRequest {
  return {
    request_fresh_scan: values.request_fresh_scan,
    scan_wait_seconds: values.scan_wait_seconds,
    auto_scan_enabled: values.auto_scan_enabled,
    auto_scan_interval_seconds: values.auto_scan_interval_seconds,
    history_page_size: values.history_page_size,
    history_observation_page_size: values.history_observation_page_size,
    dashboard_recent_scans: values.dashboard_recent_scans,
    dashboard_recent_detections: values.dashboard_recent_detections,
    dashboard_trend_limit: values.dashboard_trend_limit,
    frontend_refresh_seconds: values.frontend_refresh_seconds,
    show_technical_details: values.show_technical_details,
    high_anomaly_notifications: values.high_anomaly_notifications
  };
}

export function settingsChanged(
  initial: SettingsValues,
  current: SettingsValues
): boolean {
  return JSON.stringify(
    editableSettings(initial)
  ) !== JSON.stringify(
    editableSettings(current)
  );
}

export function parseBoundedNumber(
  raw: string,
  min: number,
  max: number,
  fallback: number
): number {
  const value = Number(raw);

  if (!Number.isFinite(value)) {
    return fallback;
  }

  return Math.min(
    max,
    Math.max(min, value)
  );
}
