from fastapi.testclient import TestClient
from backend.app import create_app


def client():
    return TestClient(create_app(database_url="sqlite:///:memory:"))


def test_support_bundle_is_available_without_real_wifi_data():
    response = client().get("/diagnostics/support-bundle")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "support_bundle_v1"
    assert payload["application"]["backend_version"] == "1.4.0-step52"
    assert payload["privacy"]["clear_wifi_identifiers_included"] is False
    assert payload["privacy"]["observation_records_included"] is False
    assert payload["privacy"]["filesystem_paths_included"] is False
    assert payload["privacy"]["environment_variables_included"] is False


def test_support_bundle_does_not_export_observation_or_artifact_paths():
    payload = client().get("/diagnostics/support-bundle").json()
    serialized = str(payload).lower()
    for forbidden in [
        "reference_path", "scaler_path", "model_path", "threshold_path",
        "interface_guid_hash", "ssid_hash", "bssid_hash", "supported_rates_mbps",
        "raw_ie_hex",
    ]:
        assert forbidden not in serialized


def test_support_bundle_contains_only_aggregate_activity():
    payload = client().get("/diagnostics/support-bundle").json()
    assert set(payload["activity"]) == {
        "latest_scan_at_utc", "latest_scan_network_count", "latest_scan_detection_count",
        "latest_scan_anomaly_count", "latest_scan_insufficient_history_count",
        "latest_detection_at_utc", "latest_detection_suspicion_level",
        "latest_detection_is_anomaly",
    }
