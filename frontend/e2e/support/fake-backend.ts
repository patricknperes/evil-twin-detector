import * as http from "node:http";
import type {
  AddressInfo
} from "node:net";

const FEATURE_SET = [
  "ssid_bssid_count",
  "bssid_changed",
  "security_changed",
  "security_strength_delta"
];

const HASH_A =
  "a".repeat(64);

const HASH_B =
  "b".repeat(64);

interface FakeSettings {
  auto_scan_enabled: boolean;
  auto_scan_interval_seconds: number;
  high_anomaly_notifications: boolean;
  frontend_refresh_seconds: number;
}

type ScanMode =
  | "success"
  | "unsupported_platform"
  | "location_access_denied"
  | "scan_in_progress";

function jsonResponse(
  response: http.ServerResponse,
  status: number,
  payload: unknown
) {
  const body =
    JSON.stringify(
      payload
    );

  response.writeHead(
    status,
    {
      "content-type":
        "application/json",
      "content-length":
        Buffer.byteLength(
          body
        ),
      "access-control-allow-origin":
        "http://127.0.0.1:15173",
      "access-control-allow-methods":
        "GET,POST,PATCH,OPTIONS",
      "access-control-allow-headers":
        "Content-Type"
    }
  );

  response.end(
    body
  );
}

async function readJson(
  request: http.IncomingMessage
): Promise<
  Record<string, unknown>
> {
  let raw =
    "";

  for await (
    const chunk
    of request
  ) {
    raw +=
      String(
        chunk
      );
  }

  if (!raw) {
    return {};
  }

  return JSON.parse(
    raw
  ) as Record<
    string,
    unknown
  >;
}

function emptyPagination(
  total: number,
  returned: number
) {
  return {
    limit:
      25,
    offset:
      0,
    returned,
    total
  };
}

export class FakeDesktopBackend {
  readonly port:
    number;

  private server:
    http.Server
    | null =
      null;

  scannerStatus:
    | "ready"
    | "not_initialized"
    | "unsupported_platform"
    | "location_access_denied"
    | "error" =
      "not_initialized";

  modelReady =
    false;

  scanMode:
    ScanMode =
      "success";

  nextScanHigh =
    false;

  settings:
    FakeSettings = {
      auto_scan_enabled:
        false,
      auto_scan_interval_seconds:
        30,
      high_anomaly_notifications:
        true,
      frontend_refresh_seconds:
        2
    };

  private scans:
    Array<
      Record<string, unknown>
    > = [];

  private observations:
    Map<
      string,
      Array<
        Record<string, unknown>
      >
    > =
      new Map();

  private detections:
    Array<
      Record<string, unknown>
    > = [];

  private latestScan:
    Record<string, unknown>
    | null =
      null;

  constructor(
    port = 18765
  ) {
    this.port =
      port;
  }

  get baseUrl() {
    return (
      `http://127.0.0.1:${this.port}`
    );
  }

  get scanCount() {
    return (
      this.scans.length
    );
  }

  async start() {
    if (
      this.server
    ) {
      return;
    }

    this.server =
      http.createServer(
        (
          request,
          response
        ) => {
          void this.handle(
            request,
            response
          );
        }
      );

    await new Promise<void>(
      (
        resolve,
        reject
      ) => {
        const server =
          this.server!;

        server.once(
          "error",
          reject
        );

        server.listen(
          this.port,
          "127.0.0.1",
          () => {
            server.removeListener(
              "error",
              reject
            );

            resolve();
          }
        );
      }
    );
  }

  async stop() {
    const server =
      this.server;

    if (!server) {
      return;
    }

    this.server =
      null;

    await new Promise<void>(
      (
        resolve,
        reject
      ) => {
        server.close(
          (
            error?: Error
          ) => {
            if (error) {
              reject(
                error
              );
              return;
            }

            resolve();
          }
        );

        server
          .closeAllConnections?.();
      }
    );
  }

  private health() {
    return {
      status:
        "ok",
      service:
        "evil-twin-e2e-fixture",
      version:
        "e2e-step49",
      platform:
        "win32",
      windows_native_wifi_supported:
        true,
      scanner_status:
        this.scannerStatus,
      model_status:
        this.modelReady
          ? "ready"
          : "not_ready",
      database_status:
        "ready"
    };
  }

  private settingsResponse() {
    return {
      values: {
        request_fresh_scan:
          true,
        scan_wait_seconds:
          0.1,
        auto_scan_enabled:
          this.settings
            .auto_scan_enabled,
        auto_scan_interval_seconds:
          this.settings
            .auto_scan_interval_seconds,
        history_page_size:
          25,
        history_observation_page_size:
          50,
        dashboard_recent_scans:
          5,
        dashboard_recent_detections:
          5,
        dashboard_trend_limit:
          30,
        frontend_refresh_seconds:
          this.settings
            .frontend_refresh_seconds,
        show_technical_details:
          true,
        high_anomaly_notifications:
          this.settings
            .high_anomaly_notifications,
        updated_at_utc:
          "2026-09-01T18:00:00Z"
      },
      model_status:
        this.modelReady
          ? "ready"
          : "not_ready",
      missing_model_artifacts:
        this.modelReady
          ? []
          : [
              "reference",
              "scaler",
              "model",
              "threshold"
            ],
      scientific_policy: {
        reference_update_allowed:
          false,
        scaler_fit_allowed:
          false,
        scaler_partial_fit_allowed:
          false,
        model_fit_allowed:
          false,
        threshold_recalibration_allowed:
          false,
        artifact_paths_editable_via_settings:
          false
      }
    };
  }

  private modelStatus() {
    return {
      status:
        this.modelReady
          ? "ready"
          : "not_ready",
      feature_set:
        FEATURE_SET,
      reference_path:
        "desktop_normal_reference.json",
      scaler_path:
        "desktop_candidate_v1_standard_scaler.joblib",
      model_path:
        "one_class_svm_desktop_candidate_v1.joblib",
      threshold_path:
        "threshold.json",
      missing_artifacts:
        this.modelReady
          ? []
          : [
              "reference",
              "scaler",
              "model",
              "threshold"
            ],
      message:
        this.modelReady
          ? "Fixture E2E: bundle disponível apenas para teste de interface."
          : "Artefatos científicos reais ainda não estão disponíveis."
    };
  }

  private modelVersion() {
    return {
      model_version_id:
        1,
      version_name:
        "e2e-fixture-model",
      algorithm:
        "OneClassSVM",
      feature_set_name:
        "desktop_candidate_v1",
      reference_sha256:
        HASH_A,
      scaler_sha256:
        HASH_A,
      model_sha256:
        HASH_B,
      threshold_sha256:
        HASH_B,
      threshold:
        0.42,
      active:
        true,
      created_at_utc:
        "2026-09-01T18:00:00Z",
      notes:
        "Fixture determinística de interface; não é resultado científico.",
      detection_count:
        this.detections.length
    };
  }

  private network({
    high
  }: {
    high: boolean;
  }) {
    return {
      network_id:
        "e2e-network-1",
      interface_guid:
        "{E2E-INTERFACE}",
      ssid:
        "E2E-Test-Network",
      bssid:
        "02:00:00:00:00:01",
      ssid_not_broadcast:
        false,
      rssi_dbm:
        -54,
      link_quality:
        78,
      beacon_interval_ms:
        102.4,
      tsf_us:
        123456789,
      host_timestamp_100ns:
        987654321,
      center_frequency_khz:
        2412000,
      ds_parameter_channel:
        1,
      security_type:
        "WPA2_OR_NEWER",
      security_strength:
        3,
      security_source:
        "rsn",
      phy_type:
        "HT",
      bss_type:
        "infrastructure",
      supported_rates_mbps: [
        6,
        12,
        24
      ],
      analysis:
        high
          ? {
              status:
                "ready",
              anomaly_score:
                0.91,
              threshold:
                0.42,
              is_anomaly:
                true,
              suspicion_level:
                "high",
              context_available:
                true,
              context_resolution:
                "e2e_fixture",
              feature_complete:
                true,
              features: {
                ssid_bssid_count:
                  2,
                bssid_changed:
                  1,
                security_changed:
                  0,
                security_strength_delta:
                  0
              },
              model_version:
                "e2e-fixture-model",
              inference_ms:
                0.4,
              reason:
                "Fixture E2E de alta suspeita; não é resultado científico."
            }
          : {
              status:
                "not_available",
              anomaly_score:
                null,
              threshold:
                null,
              is_anomaly:
                null,
              suspicion_level:
                "unavailable",
              context_available:
                null,
              context_resolution:
                null,
              feature_complete:
                null,
              features:
                null,
              model_version:
                null,
              inference_ms:
                null,
              reason:
                "Modelo científico indisponível na fixture E2E."
            }
    };
  }

  private recordScan() {
    const high =
      this.modelReady
      && this.nextScanHigh;

    this.nextScanHigh =
      false;

    this.scannerStatus =
      "ready";

    const sequence =
      this.scans.length
      + 1;

    const scanId =
      `step49-scan-${sequence}`;

    const observedAt =
      `2026-09-01T18:00:${String(sequence).padStart(2, "0")}Z`;

    const network =
      this.network({
        high
      });

    const summary = {
      scan_id:
        scanId,
      observed_at_utc:
        observedAt,
      negotiated_api_version:
        2,
      interface_count:
        1,
      total_networks:
        1,
      feature_count:
        high
          ? 1
          : 0,
      detection_count:
        high
          ? 1
          : 0,
      anomaly_count:
        high
          ? 1
          : 0,
      insufficient_history_count:
        high
          ? 0
          : 1
    };

    const detection =
      high
        ? {
            detection_id:
              this.detections.length
              + 1,
            scan_id:
              scanId,
            observation_id:
              sequence,
            model_version_id:
              1,
            anomaly_score:
              0.91,
            threshold:
              0.42,
            is_anomaly:
              true,
            suspicion_level:
              "high",
            reason:
              "Fixture E2E; não é resultado científico.",
            inference_ms:
              0.4,
            created_at_utc:
              observedAt
          }
        : null;

    const historyObservation = {
      observation_id:
        sequence,
      scan_id:
        scanId,
      network_id:
        "e2e-network-1",
      interface_guid_hash:
        HASH_A,
      ssid_hash:
        HASH_A,
      bssid_hash:
        HASH_B,
      ssid_not_broadcast:
        false,
      rssi_dbm:
        -54,
      link_quality:
        78,
      beacon_interval_ms:
        102.4,
      tsf_us:
        123456789,
      host_timestamp_100ns:
        987654321,
      center_frequency_khz:
        2412000,
      ds_parameter_channel:
        1,
      security_type:
        "WPA2_OR_NEWER",
      security_strength:
        3,
      security_source:
        "rsn",
      phy_type:
        "HT",
      bss_type:
        "infrastructure",
      supported_rates_mbps: [
        6,
        12,
        24
      ],
      features:
        high
          ? {
              ssid_bssid_count:
                2,
              bssid_changed:
                1,
              security_changed:
                0,
              security_strength_delta:
                0,
              context_available:
                true,
              context_resolution:
                "e2e_fixture",
              feature_complete:
                true
            }
          : null,
      detection
    };

    this.scans.unshift(
      summary
    );

    this.observations.set(
      scanId,
      [
        historyObservation
      ]
    );

    if (detection) {
      this.detections.unshift(
        detection
      );
    }

    this.latestScan = {
      scan_id:
        scanId,
      observed_at_utc:
        observedAt,
      negotiated_api_version:
        2,
      interface_count:
        1,
      total_networks:
        1,
      interfaces: [
        {
          guid:
            "{E2E-INTERFACE}",
          description:
            "E2E Wi-Fi",
          state:
            "connected",
          bss_count:
            1
        }
      ],
      networks: [
        network
      ]
    };

    return (
      this.latestScan
    );
  }

  private dashboard() {
    const anomalyCount =
      this.detections.length;

    const scanCount =
      this.scans.length;

    return {
      generated_at_utc:
        "2026-09-01T18:10:00Z",
      system: {
        backend_version:
          "e2e-step49",
        platform:
          "win32",
        scanner_status:
          this.scannerStatus,
        database_status:
          "ready",
        model_status:
          this.modelReady
            ? "ready"
            : "not_ready"
      },
      metrics: {
        scan_count:
          scanCount,
        observation_count:
          scanCount,
        unique_network_count:
          scanCount
            ? 1
            : 0,
        feature_count:
          anomalyCount,
        detection_count:
          anomalyCount,
        anomaly_count:
          anomalyCount,
        normal_count:
          0,
        insufficient_history_count:
          scanCount
          - anomalyCount,
        model_version_count:
          this.modelReady
            ? 1
            : 0,
        analysis_coverage_rate:
          scanCount
            ? anomalyCount
              / scanCount
            : 0,
        anomaly_rate_among_decided:
          anomalyCount
            ? 1
            : 0
      },
      suspicion_distribution: {
        low:
          0,
        medium:
          0,
        high:
          anomalyCount,
        unavailable:
          scanCount
          - anomalyCount
      },
      latest_scan_at_utc:
        this.scans[0]
          ?.observed_at_utc
        ?? null,
      latest_detection_at_utc:
        this.detections[0]
          ?.created_at_utc
        ?? null,
      active_model:
        this.modelReady
          ? this.modelVersion()
          : null,
      recent_scans:
        this.scans.slice(
          0,
          5
        ),
      recent_detections:
        this.detections.slice(
          0,
          5
        )
    };
  }

  private diagnostics() {
    return {
      schema_version:
        "support_bundle_v1",
      generated_at_utc:
        "2026-09-01T18:10:00Z",
      application: {
        backend_version:
          "e2e-step49",
        platform:
          "win32",
        python_version:
          "3.13.0",
        windows_native_wifi_supported:
          true
      },
      runtime: {
        scanner_status:
          this.scannerStatus,
        model_status:
          this.modelReady
            ? "ready"
            : "not_ready",
        database_status:
          "ready"
      },
      database: {
        status:
          "ready",
        dialect:
          "sqlite",
        scan_count:
          this.scans.length,
        observation_count:
          this.scans.length,
        feature_count:
          this.detections.length,
        detection_count:
          this.detections.length,
        model_version_count:
          this.modelReady
            ? 1
            : 0,
        error_present:
          false
      },
      settings:
        this.settingsResponse()
          .values,
      model: {
        status:
          this.modelReady
            ? "ready"
            : "not_ready",
        feature_set:
          FEATURE_SET,
        missing_artifacts:
          this.modelReady
            ? []
            : [
                "reference",
                "scaler",
                "model",
                "threshold"
              ],
        artifact_available: {
          reference:
            this.modelReady,
          scaler:
            this.modelReady,
          model:
            this.modelReady,
          threshold:
            this.modelReady
        },
        active_model:
          this.modelReady
            ? this.modelVersion()
            : null
      },
      activity: {
        latest_scan_at_utc:
          this.scans[0]
            ?.observed_at_utc
          ?? null,
        latest_scan_network_count:
          this.scans.length
            ? 1
            : null,
        latest_scan_detection_count:
          this.scans.length
            ? (this.scans[0].detection_count as number)
            : null,
        latest_scan_anomaly_count:
          this.scans.length
            ? (this.scans[0].anomaly_count as number)
            : null,
        latest_scan_insufficient_history_count:
          this.scans.length
            ? (this.scans[0].insufficient_history_count as number)
            : null,
        latest_detection_at_utc:
          this.detections[0]
            ?.created_at_utc
          ?? null,
        latest_detection_suspicion_level:
          this.detections[0]
            ?.suspicion_level
          ?? null,
        latest_detection_is_anomaly:
          this.detections[0]
            ?.is_anomaly
          ?? null
      },
      privacy: {
        clear_wifi_identifiers_included:
          false,
        observation_records_included:
          false,
        raw_ie_bytes_included:
          false,
        filesystem_paths_included:
          false,
        environment_variables_included:
          false
      },
      warnings: []
    };
  }

  private async handle(
    request: http.IncomingMessage,
    response: http.ServerResponse
  ) {
    if (
      request.method
      === "OPTIONS"
    ) {
      response.writeHead(
        204,
        {
          "access-control-allow-origin":
            "http://127.0.0.1:15173",
          "access-control-allow-methods":
            "GET,POST,PATCH,OPTIONS",
          "access-control-allow-headers":
            "Content-Type"
        }
      );

      response.end();
      return;
    }

    const url =
      new URL(
        request.url
        ?? "/",
        this.baseUrl
      );

    if (
      request.method
      === "GET"
      && url.pathname
      === "/health"
    ) {
      jsonResponse(
        response,
        200,
        this.health()
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/settings"
    ) {
      jsonResponse(
        response,
        200,
        this.settingsResponse()
      );
      return;
    }

    if (
      request.method
      === "PATCH"
      && url.pathname
      === "/settings"
    ) {
      const patch =
        await readJson(
          request
        );

      if (
        typeof patch
          .auto_scan_enabled
        === "boolean"
      ) {
        this.settings
          .auto_scan_enabled =
            patch
              .auto_scan_enabled;
      }

      if (
        typeof patch
          .high_anomaly_notifications
        === "boolean"
      ) {
        this.settings
          .high_anomaly_notifications =
            patch
              .high_anomaly_notifications;
      }

      jsonResponse(
        response,
        200,
        this.settingsResponse()
      );
      return;
    }

    if (
      request.method
      === "POST"
      && url.pathname
      === "/settings/reset"
    ) {
      this.settings
        .auto_scan_enabled =
          false;

      this.settings
        .high_anomaly_notifications =
          true;

      jsonResponse(
        response,
        200,
        this.settingsResponse()
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/model"
    ) {
      jsonResponse(
        response,
        200,
        this.modelStatus()
      );
      return;
    }

    if (
      request.method
      === "POST"
      && url.pathname
      === "/scan"
    ) {
      if (
        this.scanMode
        === "unsupported_platform"
      ) {
        jsonResponse(
          response,
          501,
          {
            detail: {
              code:
                "unsupported_platform",
              message:
                "Fixture E2E: scanner indisponível."
            }
          }
        );
        return;
      }

      if (
        this.scanMode
        === "location_access_denied"
      ) {
        jsonResponse(
          response,
          403,
          {
            detail: {
              code:
                "location_access_denied",
              message:
                "Fixture E2E: localização necessária.",
              settings_uri:
                "ms-settings:privacy-location"
            }
          }
        );
        return;
      }

      if (
        this.scanMode
        === "scan_in_progress"
      ) {
        jsonResponse(
          response,
          409,
          {
            detail: {
              code:
                "scan_in_progress",
              message:
                "Fixture E2E: scan em andamento."
            }
          }
        );
        return;
      }

      jsonResponse(
        response,
        200,
        this.recordScan()
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/networks"
    ) {
      jsonResponse(
        response,
        200,
        this.latestScan
          ? {
              has_scan:
                true,
              scan_id:
                this.latestScan
                  .scan_id,
              observed_at_utc:
                this.latestScan
                  .observed_at_utc,
              total_networks:
                1,
              networks:
                this.latestScan
                  .networks
            }
          : {
              has_scan:
                false,
              scan_id:
                null,
              observed_at_utc:
                null,
              total_networks:
                0,
              networks: []
            }
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/dashboard/overview"
    ) {
      jsonResponse(
        response,
        200,
        this.dashboard()
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/dashboard/trends"
    ) {
      const points =
        [...this.scans]
          .reverse()
          .map(
            scan => ({
              scan_id:
                scan.scan_id,
              observed_at_utc:
                scan.observed_at_utc,
              network_count:
                scan.total_networks,
              feature_count:
                scan.feature_count,
              detection_count:
                scan.detection_count,
              anomaly_count:
                scan.anomaly_count,
              normal_count:
                0,
              insufficient_history_count:
                scan.insufficient_history_count
            })
          );

      jsonResponse(
        response,
        200,
        {
          requested_limit:
            30,
          returned:
            points.length,
          points
        }
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/history/scans"
    ) {
      jsonResponse(
        response,
        200,
        {
          pagination:
            emptyPagination(
              this.scans.length,
              this.scans.length
            ),
          items:
            this.scans
        }
      );
      return;
    }

    const scanDetailMatch =
      url.pathname.match(
        /^\/history\/scans\/([^/]+)$/
      );

    if (
      request.method
      === "GET"
      && scanDetailMatch
    ) {
      const scanId =
        decodeURIComponent(
          scanDetailMatch[1]
        );

      const scan =
        this.scans.find(
          item =>
            item.scan_id
            === scanId
        );

      if (!scan) {
        jsonResponse(
          response,
          404,
          {
            detail:
              "not_found"
          }
        );
        return;
      }

      jsonResponse(
        response,
        200,
        {
          scan,
          observations:
            this.observations.get(
              scanId
            )
            ?? []
        }
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/history/detections"
    ) {
      jsonResponse(
        response,
        200,
        {
          pagination:
            emptyPagination(
              this.detections.length,
              this.detections.length
            ),
          items:
            this.detections
        }
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/history/models"
    ) {
      const items =
        this.modelReady
          ? [
              this.modelVersion()
            ]
          : [];

      jsonResponse(
        response,
        200,
        {
          pagination:
            emptyPagination(
              items.length,
              items.length
            ),
          items
        }
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/history/models/1"
    ) {
      jsonResponse(
        response,
        200,
        this.modelVersion()
      );
      return;
    }

    if (
      request.method
      === "GET"
      && url.pathname
      === "/diagnostics/support-bundle"
    ) {
      jsonResponse(
        response,
        200,
        this.diagnostics()
      );
      return;
    }

    jsonResponse(
      response,
      404,
      {
        detail:
          "not_found"
      }
    );
  }
}
