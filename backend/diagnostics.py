from __future__ import annotations

import sys
from datetime import (
    datetime,
    timezone,
)

from .schemas import (
    DiagnosticsActivityInfo,
    DiagnosticsApplicationInfo,
    DiagnosticsDatabaseInfo,
    DiagnosticsModelInfo,
    DiagnosticsPrivacyInfo,
    DiagnosticsRuntimeInfo,
    DiagnosticsSupportBundleResponse,
)


class DiagnosticsService:
    def __init__(
        self,
        *,
        backend_version: str,
        scanner_service,
        model_status_service,
        database_status_service,
        settings_service,
        history_service,
    ) -> None:
        self.backend_version = backend_version
        self.scanner_service = scanner_service
        self.model_status_service = model_status_service
        self.database_status_service = database_status_service
        self.settings_service = settings_service
        self.history_service = history_service

    def _scanner_status(self) -> str:
        if sys.platform != "win32":
            return "unsupported_platform"
        return self.scanner_service.runtime_status

    def create_support_bundle(self) -> DiagnosticsSupportBundleResponse:
        generated_at = datetime.now(timezone.utc)
        warnings: list[str] = []
        model_status = self.model_status_service.get_status()
        artifact_available = {
            name: name not in model_status.missing_artifacts
            for name in ("reference", "scaler", "model", "threshold")
        }
        database = self.database_status_service.get_status()
        settings = None
        try:
            settings = self.settings_service.get_values()
        except Exception:
            warnings.append("application_settings_unavailable")

        latest_scan = None
        latest_detection = None
        active_model = None
        if database["status"] == "ready":
            try:
                scans = self.history_service.list_scans(limit=1, offset=0)
                if scans.items:
                    latest_scan = scans.items[0]
            except Exception:
                warnings.append("latest_scan_summary_unavailable")
            try:
                detections = self.history_service.list_detections(limit=1, offset=0)
                if detections.items:
                    latest_detection = detections.items[0]
            except Exception:
                warnings.append("latest_detection_summary_unavailable")
            try:
                models = self.history_service.list_models(limit=100, offset=0)
                active_model = next((item for item in models.items if item.active), None)
            except Exception:
                warnings.append("active_model_summary_unavailable")
        else:
            warnings.append("database_status_error")

        return DiagnosticsSupportBundleResponse(
            generated_at_utc=generated_at,
            application=DiagnosticsApplicationInfo(
                backend_version=self.backend_version,
                platform=sys.platform,
                python_version=".".join(str(v) for v in sys.version_info[:3]),
                windows_native_wifi_supported=sys.platform == "win32",
            ),
            runtime=DiagnosticsRuntimeInfo(
                scanner_status=self._scanner_status(),
                model_status=model_status.status,
                database_status=database["status"],
            ),
            database=DiagnosticsDatabaseInfo(
                status=database["status"],
                dialect=str(database["dialect"]),
                scan_count=database.get("scan_count"),
                observation_count=database.get("observation_count"),
                feature_count=database.get("feature_count"),
                detection_count=database.get("detection_count"),
                model_version_count=database.get("model_version_count"),
                error_present=database.get("error") is not None,
            ),
            settings=settings,
            model=DiagnosticsModelInfo(
                status=model_status.status,
                feature_set=model_status.feature_set,
                missing_artifacts=model_status.missing_artifacts,
                artifact_available=artifact_available,
                active_model=active_model,
            ),
            activity=DiagnosticsActivityInfo(
                latest_scan_at_utc=(latest_scan.observed_at_utc if latest_scan else None),
                latest_scan_network_count=(latest_scan.total_networks if latest_scan else None),
                latest_scan_detection_count=(latest_scan.detection_count if latest_scan else None),
                latest_scan_anomaly_count=(latest_scan.anomaly_count if latest_scan else None),
                latest_scan_insufficient_history_count=(latest_scan.insufficient_history_count if latest_scan else None),
                latest_detection_at_utc=(latest_detection.created_at_utc if latest_detection else None),
                latest_detection_suspicion_level=(latest_detection.suspicion_level if latest_detection else None),
                latest_detection_is_anomaly=(latest_detection.is_anomaly if latest_detection else None),
            ),
            privacy=DiagnosticsPrivacyInfo(),
            warnings=warnings,
        )
