import type {
  ApplicationSettingsResponse,
  ApplicationSettingsUpdateRequest,
  DashboardOverviewResponse,
  DashboardTrendsResponse,
  DiagnosticsSupportBundleResponse,
  HealthResponse,
  HistoryDetectionDetailResponse,
  HistoryDetectionListResponse,
  HistoryModelVersion,
  HistoryModelVersionListResponse,
  HistoryScanDetailResponse,
  HistoryScanListResponse,
  ModelArtifactStatusResponse,
  NetworksResponse,
  ScanResponse
} from "../types/api";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL
  ?? "http://127.0.0.1:8765";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly payload: unknown
  ) {
    super(`API request failed: ${status}`);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      }
    }
  );

  const payload = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload
    );
  }

  return payload as T;
}



function queryString(
  values: Record<
    string,
    string | number | boolean | null | undefined
  >
): string {
  const params = new URLSearchParams();

  Object.entries(
    values
  ).forEach(
    ([
      key,
      value
    ]) => {
      if (
        value !== undefined
        && value !== null
        && value !== ""
      ) {
        params.set(
          key,
          String(
            value
          )
        );
      }
    }
  );

  const encoded = params.toString();

  return encoded
    ? `?${encoded}`
    : "";
}

export const api = {
  health: () =>
    request<HealthResponse>(
      "/health"
    ),

  modelStatus: () =>
    request<ModelArtifactStatusResponse>(
      "/model"
    ),

  dashboard: () =>
    request<DashboardOverviewResponse>(
      "/dashboard/overview"
    ),

  dashboardTrends: () =>
    request<DashboardTrendsResponse>(
      "/dashboard/trends"
    ),

  diagnosticsSupportBundle: () =>
    request<DiagnosticsSupportBundleResponse>(
      "/diagnostics/support-bundle"
    ),

  scan: () =>
    request<ScanResponse>(
      "/scan",
      {
        method: "POST",
        body: JSON.stringify({})
      }
    ),

  latestNetworks: () =>
    request<NetworksResponse>(
      "/networks"
    ),

  settings: () =>
    request<ApplicationSettingsResponse>(
      "/settings"
    ),

  updateSettings: (
    patch: ApplicationSettingsUpdateRequest
  ) =>
    request<ApplicationSettingsResponse>(
      "/settings",
      {
        method: "PATCH",
        body: JSON.stringify(patch)
      }
    ),

  resetSettings: () =>
    request<ApplicationSettingsResponse>(
      "/settings/reset",
      {
        method: "POST"
      }
    ),

  historyScans: (
    options: {
      limit?: number;
      offset?: number;
    } = {}
  ) =>
    request<HistoryScanListResponse>(
      `/history/scans${queryString(
        options
      )}`
    ),

  historyScanDetail: (
    scanId: string
  ) =>
    request<HistoryScanDetailResponse>(
      `/history/scans/${encodeURIComponent(
        scanId
      )}`
    ),

  historyDetections: (
    options: {
      limit?: number;
      offset?: number;
      is_anomaly?: boolean | null;
      suspicion_level?: string | null;
      model_version_id?: number | null;
    } = {}
  ) =>
    request<HistoryDetectionListResponse>(
      `/history/detections${queryString(
        options
      )}`
    ),

  historyDetectionDetail: (
    detectionId: number
  ) =>
    request<HistoryDetectionDetailResponse>(
      `/history/detections/${detectionId}`
    ),

  historyModels: (
    options: {
      limit?: number;
      offset?: number;
    } = {}
  ) =>
    request<HistoryModelVersionListResponse>(
      `/history/models${queryString(
        options
      )}`
    ),

  historyModelDetail: (
    modelVersionId: number
  ) =>
    request<HistoryModelVersion>(
      `/history/models/${modelVersionId}`
    )
};
