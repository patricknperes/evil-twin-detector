from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.model_status import (
    ModelArtifactStatusService,
)
from backend.runtime_store import RuntimeStore
from backend.scanner_service import ScannerService
from desktop.windows.native_wifi_contract import (
    NativeWifiBssObservation,
)
from desktop.windows.wlanapi_ctypes import (
    LocationAccessDeniedError,
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
    UnsupportedPlatformError,
)


SCHEMA_VERSION = (
    "desktop_integration_backend_v1"
)


class DeterministicScanner:
    def scan_all(
        self,
        **kwargs,
    ) -> NativeWifiScanBatch:
        strong = NativeWifiBssObservation(
            ssid=b"Lab Network",
            bssid="02:11:22:33:44:55",
            rssi_dbm=-42,
            link_quality=91,
            beacon_period_tu=100,
            tsf_us=100_000,
            host_timestamp_100ns=1_000_000,
            capability_info=0x0010,
            center_frequency_khz=2_437_000,
            ie_blob=bytes([
                3,
                1,
                6,
            ]),
        )

        weak = NativeWifiBssObservation(
            ssid=b"Guest Network",
            bssid="02:11:22:33:44:66",
            rssi_dbm=-78,
            link_quality=35,
            beacon_period_tu=100,
            tsf_us=200_000,
            host_timestamp_100ns=2_000_000,
            capability_info=0,
            center_frequency_khz=2_462_000,
            ie_blob=bytes([
                3,
                1,
                11,
            ]),
        )

        native = NativeWifiBssNativeMetadata(
            phy_id=1,
            bss_type_code=1,
            bss_type="infrastructure",
            phy_type_code=7,
            phy_type="ht",
            in_reg_domain=True,
            supported_rates_mbps=(
                6.0,
                12.0,
            ),
        )

        interface = NativeWifiInterface(
            guid="{STEP48-FAKE-GUID}",
            description=(
                "Step 48 deterministic Wi-Fi"
            ),
            state_code=1,
            state="connected",
            _guid_struct=None,
        )

        return NativeWifiScanBatch(
            negotiated_api_version=2,
            interface_scans=(
                NativeWifiInterfaceScan(
                    interface=interface,
                    bss_entries=(
                        NativeWifiBssResult(
                            observation=strong,
                            native=native,
                        ),
                        NativeWifiBssResult(
                            observation=weak,
                            native=native,
                        ),
                    ),
                    requested_fresh_scan=bool(
                        kwargs.get(
                            "request_fresh_scan",
                            True,
                        )
                    ),
                    scan_wait_seconds=float(
                        kwargs.get(
                            "scan_wait_seconds",
                            0.0,
                        )
                    ),
                    wait_strategy=(
                        "step48_deterministic"
                    ),
                ),
            ),
        )


class UnsupportedScanner:
    def scan_all(
        self,
        **kwargs,
    ):
        raise UnsupportedPlatformError(
            "Step 48 unsupported platform scenario."
        )


class LocationDeniedScanner:
    def scan_all(
        self,
        **kwargs,
    ):
        raise LocationAccessDeniedError(
            "WlanGetNetworkBssList",
            5,
        )


def _client(
    workspace: Path,
    scanner,
) -> TestClient:
    workspace.mkdir(
        parents=True,
        exist_ok=True,
    )

    database_path = (
        workspace
        / "integration.db"
    )

    app = create_app(
        scanner_service=(
            ScannerService(
                scanner=scanner
            )
        ),
        runtime_store=(
            RuntimeStore()
        ),
        model_status_service=(
            ModelArtifactStatusService(
                project_root=workspace
            )
        ),
        database_url=(
            "sqlite:///"
            + str(
                database_path
            )
        ),
    )

    return TestClient(
        app
    )


def _scenario(
    scenario_id: str,
    title: str,
    checks: list[
        tuple[
            str,
            bool,
        ]
    ],
    evidence: dict[
        str,
        Any,
    ],
) -> dict[
    str,
    Any,
]:
    failures = [
        name
        for name, passed
        in checks
        if not passed
    ]

    return {
        "id":
            scenario_id,
        "title":
            title,
        "status": (
            "PASSED"
            if not failures
            else "FAILED"
        ),
        "checks": {
            name:
                bool(
                    passed
                )
            for name, passed
            in checks
        },
        "failures":
            failures,
        "evidence":
            evidence,
    }


def run_backend_integration_scenarios(
    workspace_root: str
    | Path
    | None = None,
) -> dict[
    str,
    Any,
]:
    temporary = None

    if workspace_root is None:
        temporary = TemporaryDirectory(
            prefix=(
                "evil-twin-step48-"
            )
        )

        root = Path(
            temporary.name
        )
    else:
        root = Path(
            workspace_root
        )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenarios = []

    # ------------------------------------------------------------
    # 1. Backend online, DB ready, scientific model unavailable.
    # ------------------------------------------------------------
    online = _client(
        root
        / "online",
        DeterministicScanner(),
    )

    health_response = (
        online.get(
            "/health"
        )
    )

    model_response = (
        online.get(
            "/model"
        )
    )

    health = (
        health_response
        .json()
    )

    model = (
        model_response
        .json()
    )

    scenarios.append(
        _scenario(
            "backend_online_model_not_ready",
            "Backend online with model not ready",
            [
                (
                    "health_http_200",
                    health_response.status_code
                    == 200,
                ),
                (
                    "service_ok",
                    health.get(
                        "status"
                    )
                    == "ok",
                ),
                (
                    "database_ready",
                    health.get(
                        "database_status"
                    )
                    == "ready",
                ),
                (
                    "model_not_ready",
                    model.get(
                        "status"
                    )
                    == "not_ready",
                ),
                (
                    "four_artifacts_missing",
                    set(
                        model.get(
                            "missing_artifacts",
                            [],
                        )
                    )
                    == {
                        "reference",
                        "scaler",
                        "model",
                        "threshold",
                    },
                ),
            ],
            {
                "backend_version":
                    health.get(
                        "version"
                    ),
                "database_status":
                    health.get(
                        "database_status"
                    ),
                "model_status":
                    model.get(
                        "status"
                    ),
                "missing_artifacts":
                    model.get(
                        "missing_artifacts",
                        [],
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # 2. Unsupported scanner -> specific 501 contract.
    # ------------------------------------------------------------
    unsupported = _client(
        root
        / "unsupported",
        UnsupportedScanner(),
    )

    unsupported_response = (
        unsupported.post(
            "/scan",
            json={
                "request_fresh_scan":
                    False,
                "scan_wait_seconds":
                    0,
            },
        )
    )

    unsupported_payload = (
        unsupported_response
        .json()
    )

    scenarios.append(
        _scenario(
            "scanner_unsupported",
            "Unsupported Native Wi-Fi platform",
            [
                (
                    "http_501",
                    unsupported_response
                    .status_code
                    == 501,
                ),
                (
                    "error_code",
                    unsupported_payload
                    .get(
                        "detail",
                        {},
                    )
                    .get(
                        "code"
                    )
                    == "unsupported_platform",
                ),
            ],
            {
                "http_status":
                    unsupported_response
                    .status_code,
                "error_code":
                    unsupported_payload
                    .get(
                        "detail",
                        {},
                    )
                    .get(
                        "code"
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # 3. Location permission denial -> specific 403 contract.
    # ------------------------------------------------------------
    denied = _client(
        root
        / "location_denied",
        LocationDeniedScanner(),
    )

    denied_response = (
        denied.post(
            "/scan",
            json={
                "request_fresh_scan":
                    False,
                "scan_wait_seconds":
                    0,
            },
        )
    )

    denied_payload = (
        denied_response
        .json()
    )

    denied_detail = (
        denied_payload.get(
            "detail",
            {},
        )
    )

    scenarios.append(
        _scenario(
            "scanner_location_access_denied",
            "Windows location access denied",
            [
                (
                    "http_403",
                    denied_response
                    .status_code
                    == 403,
                ),
                (
                    "error_code",
                    denied_detail.get(
                        "code"
                    )
                    == "location_access_denied",
                ),
                (
                    "settings_uri_present",
                    isinstance(
                        denied_detail.get(
                            "settings_uri"
                        ),
                        str,
                    )
                    and bool(
                        denied_detail.get(
                            "settings_uri"
                        )
                    ),
                ),
            ],
            {
                "http_status":
                    denied_response
                    .status_code,
                "error_code":
                    denied_detail.get(
                        "code"
                    ),
                "settings_uri_present":
                    bool(
                        denied_detail.get(
                            "settings_uri"
                        )
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # 4. Manual scan succeeds with model unavailable.
    #    This exercises scanner -> inference semantics -> persistence
    #    -> latest networks -> history -> diagnostics.
    # ------------------------------------------------------------
    manual = _client(
        root
        / "manual_scan",
        DeterministicScanner(),
    )

    manual_response = (
        manual.post(
            "/scan",
            json={
                "request_fresh_scan":
                    False,
                "scan_wait_seconds":
                    0,
            },
        )
    )

    manual_payload = (
        manual_response
        .json()
    )

    latest = (
        manual.get(
            "/networks"
        ).json()
    )

    history = (
        manual.get(
            "/history/scans",
            params={
                "limit":
                    25,
                "offset":
                    0,
            },
        ).json()
    )

    diagnostics = (
        manual.get(
            "/diagnostics/support-bundle"
        ).json()
    )

    analyses = [
        network.get(
            "analysis",
            {},
        )
        for network
        in manual_payload.get(
            "networks",
            [],
        )
    ]

    scenarios.append(
        _scenario(
            "manual_scan_model_not_ready",
            "Manual scan while model is not ready",
            [
                (
                    "scan_http_200",
                    manual_response
                    .status_code
                    == 200,
                ),
                (
                    "two_networks",
                    manual_payload.get(
                        "total_networks"
                    )
                    == 2,
                ),
                (
                    "analysis_not_available",
                    bool(
                        analyses
                    )
                    and all(
                        analysis.get(
                            "status"
                        )
                        == "not_available"
                        for analysis
                        in analyses
                    ),
                ),
                (
                    "no_false_negative_decision",
                    all(
                        analysis.get(
                            "is_anomaly"
                        )
                        is None
                        for analysis
                        in analyses
                    ),
                ),
                (
                    "latest_runtime_scan_matches",
                    latest.get(
                        "scan_id"
                    )
                    == manual_payload.get(
                        "scan_id"
                    ),
                ),
                (
                    "history_persisted",
                    history.get(
                        "pagination",
                        {},
                    )
                    .get(
                        "total"
                    )
                    == 1,
                ),
                (
                    "diagnostics_scan_count",
                    diagnostics.get(
                        "database",
                        {},
                    )
                    .get(
                        "scan_count"
                    )
                    == 1,
                ),
                (
                    "diagnostics_privacy",
                    diagnostics.get(
                        "privacy",
                        {},
                    )
                    .get(
                        "clear_wifi_identifiers_included"
                    )
                    is False,
                ),
            ],
            {
                "scan_http_status":
                    manual_response
                    .status_code,
                "total_networks":
                    manual_payload.get(
                        "total_networks"
                    ),
                "analysis_statuses":
                    sorted({
                        str(
                            analysis.get(
                                "status"
                            )
                        )
                        for analysis
                        in analyses
                    }),
                "is_anomaly_values":
                    sorted({
                        str(
                            analysis.get(
                                "is_anomaly"
                            )
                        )
                        for analysis
                        in analyses
                    }),
                "history_scan_total":
                    history.get(
                        "pagination",
                        {},
                    )
                    .get(
                        "total"
                    ),
                "diagnostics_scan_count":
                    diagnostics.get(
                        "database",
                        {},
                    )
                    .get(
                        "scan_count"
                    ),
            },
        )
    )

    passed = all(
        scenario[
            "status"
        ]
        == "PASSED"
        for scenario
        in scenarios
    )

    report = {
        "schema_version":
            SCHEMA_VERSION,
        "status": (
            "passed"
            if passed
            else "failed"
        ),
        "scenario_count":
            len(
                scenarios
            ),
        "passed_count":
            sum(
                scenario[
                    "status"
                ]
                == "PASSED"
                for scenario
                in scenarios
            ),
        "real_windows_native_wifi_used":
            False,
        "real_scientific_artifacts_used":
            False,
        "fake_final_metrics_created":
            False,
        "clear_wifi_identifiers_in_report":
            False,
        "scenarios":
            scenarios,
    }

    if temporary is not None:
        temporary.cleanup()

    return report


def save_backend_integration_report(
    report: dict[
        str,
        Any,
    ],
    path: str
    | Path,
) -> None:
    destination = Path(
        path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
