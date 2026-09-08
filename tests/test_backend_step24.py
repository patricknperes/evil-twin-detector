import hashlib
import json

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


class FakeScanner:
    def scan_all(self, **kwargs):
        strong = NativeWifiBssObservation(
            ssid=b"Rede Forte",
            bssid="00:11:22:33:44:55",
            rssi_dbm=-41,
            link_quality=92,
            beacon_period_tu=100,
            tsf_us=100000,
            host_timestamp_100ns=1000000,
            capability_info=0x0010,
            center_frequency_khz=2437000,
            ie_blob=bytes([3, 1, 6]),
        )

        weak = NativeWifiBssObservation(
            ssid=b"Rede Fraca",
            bssid="00:11:22:33:44:66",
            rssi_dbm=-80,
            link_quality=30,
            beacon_period_tu=100,
            tsf_us=200000,
            host_timestamp_100ns=2000000,
            capability_info=0,
            center_frequency_khz=2462000,
            ie_blob=bytes([3, 1, 11]),
        )

        native = NativeWifiBssNativeMetadata(
            phy_id=1,
            bss_type_code=1,
            bss_type="infrastructure",
            phy_type_code=7,
            phy_type="ht",
            in_reg_domain=True,
            supported_rates_mbps=(6.0, 12.0),
        )

        interface = NativeWifiInterface(
            guid="{FAKE-GUID}",
            description="Fake Wi-Fi",
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
                            4.2,
                        )
                    ),
                    wait_strategy="fake",
                ),
            ),
        )


class UnsupportedScanner:
    def scan_all(self, **kwargs):
        raise UnsupportedPlatformError(
            "Windows required."
        )


class DeniedScanner:
    def scan_all(self, **kwargs):
        raise LocationAccessDeniedError(
            "WlanGetNetworkBssList",
            5,
        )


def _client(
    tmp_path,
    scanner,
):
    app = create_app(
        scanner_service=ScannerService(
            scanner=scanner
        ),
        runtime_store=RuntimeStore(),
        model_status_service=(
            ModelArtifactStatusService(
                project_root=tmp_path
            )
        ),
    )
    return TestClient(app)


def test_global_app_import_is_safe_off_windows():
    # Import already happened during collection of this test module.
    # Lazy initialization is the behavior under test.
    from backend.app import app

    assert app is not None
    assert (
        app.state.scanner_service.initialized
        is False
    )


def test_health(tmp_path):
    client = _client(
        tmp_path,
        FakeScanner(),
    )

    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["model_status"] == "not_ready"


def test_networks_empty_before_first_scan(
    tmp_path,
):
    client = _client(
        tmp_path,
        FakeScanner(),
    )

    payload = client.get(
        "/networks"
    ).json()

    assert payload["has_scan"] is False
    assert payload["total_networks"] == 0
    assert payload["networks"] == []


def test_scan_stores_latest_networks(
    tmp_path,
):
    client = _client(
        tmp_path,
        FakeScanner(),
    )

    response = client.post(
        "/scan",
        json={
            "request_fresh_scan": True,
            "scan_wait_seconds": 0,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total_networks"] == 2

    # Ordered by strongest RSSI.
    assert payload["networks"][0]["ssid"] == "Rede Forte"
    assert payload["networks"][0]["ds_parameter_channel"] == 6
    assert (
        payload["networks"][0]["analysis"]["status"]
        == "not_available"
    )

    latest = client.get(
        "/networks"
    ).json()

    assert latest["has_scan"] is True
    assert latest["scan_id"] == payload["scan_id"]
    assert latest["total_networks"] == 2


def test_model_status_missing(
    tmp_path,
):
    client = _client(
        tmp_path,
        FakeScanner(),
    )

    payload = client.get(
        "/model"
    ).json()

    assert payload["status"] == "not_ready"

    assert set(
        payload["missing_artifacts"]
    ) == {
        "reference",
        "scaler",
        "model",
        "threshold",
    }


def test_model_status_ready_when_files_exist(
    tmp_path,
):
    reference = (
        tmp_path
        / "data/processed/desktop_candidate_v1/"
        "desktop_normal_reference.json"
    )

    reference.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    reference.write_text(
        json.dumps({
            "schema_version":
                "desktop_normal_reference_v1",
            "status":
                "frozen",
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
        }),
        encoding="utf-8",
    )

    scaler = (
        tmp_path
        / "ml/models/preprocessing/"
        "desktop_candidate_v1_standard_scaler.joblib"
    )

    model = (
        tmp_path
        / "ml/models/desktop_candidate_v1/ocsvm_v1/"
        "one_class_svm_desktop_candidate_v1.joblib"
    )

    threshold = (
        tmp_path
        / "ml/models/desktop_candidate_v1/ocsvm_v1/"
        "threshold.json"
    )

    for path in [
        scaler,
        model,
        threshold,
    ]:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    scaler.write_bytes(
        b"fixture-scaler"
    )

    model.write_bytes(
        b"fixture-model"
    )

    sha = lambda path: hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    threshold.write_text(
        json.dumps({
            "schema_version":
                "desktop_threshold_v2",
            "feature_set_name":
                "desktop_candidate_v1",
            "features": [
                "ssid_bssid_count",
                "bssid_changed",
                "security_changed",
                "security_strength_delta",
            ],
            "source_split":
                "validation",
            "source_label":
                "normal_only",
            "threshold":
                1.0,
            "attack_used_for_calibration":
                False,
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
            "reference_file_sha256":
                sha(
                    reference
                ),
            "scaler_file_sha256":
                sha(
                    scaler
                ),
            "model_file_sha256":
                sha(
                    model
                ),
            "artifact_lineage_file_sha256":
                "c"
                * 64,
        }),
        encoding="utf-8",
    )

    client = _client(
        tmp_path,
        FakeScanner(),
    )

    payload = client.get(
        "/model"
    ).json()

    assert payload["status"] == "ready"
    assert payload["missing_artifacts"] == []


def test_unsupported_platform_maps_501(
    tmp_path,
):
    client = _client(
        tmp_path,
        UnsupportedScanner(),
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds": 0,
        },
    )

    assert response.status_code == 501
    assert (
        response.json()["detail"]["code"]
        == "unsupported_platform"
    )


def test_location_denied_maps_403(
    tmp_path,
):
    client = _client(
        tmp_path,
        DeniedScanner(),
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds": 0,
        },
    )

    assert response.status_code == 403

    detail = response.json()["detail"]

    assert detail["code"] == "location_access_denied"
    assert (
        detail["settings_uri"]
        == "ms-settings:privacy-location"
    )


def test_scan_request_validation(
    tmp_path,
):
    client = _client(
        tmp_path,
        FakeScanner(),
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds": -1,
        },
    )

    assert response.status_code == 422
