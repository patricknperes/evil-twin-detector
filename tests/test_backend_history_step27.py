from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db import create_database_engine, create_session_factory
from backend.model_status import ModelArtifactStatusService
from backend.models import (
    Base,
    Detection,
    ModelVersion,
    NetworkFeatures,
    NetworkObservation,
    ScanSession,
)
from backend.persistence import DatabaseStatusService, ScanPersistenceService
from backend.runtime_store import RuntimeStore
from backend.scanner_service import ScannerService


class NeverCalledScanner:
    def scan_all(self, **kwargs):
        raise AssertionError("History endpoint should not scan Wi-Fi.")


def _seed(factory):
    now = datetime.now(timezone.utc)

    with factory() as session:
        model = ModelVersion(
            version_name="desktop_candidate_v1-test",
            algorithm="OneClassSVM",
            feature_set_name="desktop_candidate_v1",
            reference_sha256="a" * 64,
            scaler_sha256="b" * 64,
            model_sha256="c" * 64,
            threshold_sha256="d" * 64,
            threshold=0.5,
            active=True,
            notes="fixture",
        )
        session.add(model)
        session.flush()

        old_scan = ScanSession(
            id="00000000-0000-0000-0000-000000000001",
            observed_at_utc=now - timedelta(minutes=5),
            negotiated_api_version=2,
            interface_count=1,
            total_networks=1,
        )
        new_scan = ScanSession(
            id="00000000-0000-0000-0000-000000000002",
            observed_at_utc=now,
            negotiated_api_version=2,
            interface_count=1,
            total_networks=2,
        )
        session.add_all([old_scan, new_scan])
        session.flush()

        old_obs = NetworkObservation(
            scan_session_id=old_scan.id,
            network_id="network-old",
            interface_guid_hash="e" * 64,
            ssid_hash="f" * 64,
            bssid_hash="1" * 64,
            ssid_not_broadcast=False,
            rssi_dbm=-70,
            link_quality=50,
            beacon_interval_ms=102.4,
            tsf_us=10,
            host_timestamp_100ns=100,
            center_frequency_khz=2412000,
            ds_parameter_channel=1,
            security_type="WPA2_OR_NEWER",
            security_strength=3,
            security_source="rsn",
            phy_type="ht",
            bss_type="infrastructure",
            supported_rates_json="[6.0,12.0]",
        )
        normal_obs = NetworkObservation(
            scan_session_id=new_scan.id,
            network_id="network-normal",
            interface_guid_hash="e" * 64,
            ssid_hash="f" * 64,
            bssid_hash="2" * 64,
            ssid_not_broadcast=False,
            rssi_dbm=-45,
            link_quality=90,
            beacon_interval_ms=102.4,
            tsf_us=20,
            host_timestamp_100ns=200,
            center_frequency_khz=2437000,
            ds_parameter_channel=6,
            security_type="WPA2_OR_NEWER",
            security_strength=3,
            security_source="rsn",
            phy_type="ht",
            bss_type="infrastructure",
            supported_rates_json="[6.0,12.0,54.0]",
        )
        unknown_obs = NetworkObservation(
            scan_session_id=new_scan.id,
            network_id="network-unknown",
            interface_guid_hash="e" * 64,
            ssid_hash="9" * 64,
            bssid_hash="3" * 64,
            ssid_not_broadcast=False,
            rssi_dbm=-60,
            link_quality=65,
            beacon_interval_ms=102.4,
            tsf_us=30,
            host_timestamp_100ns=300,
            center_frequency_khz=2462000,
            ds_parameter_channel=11,
            security_type="OPEN",
            security_strength=0,
            security_source="privacy",
            phy_type="ht",
            bss_type="infrastructure",
            supported_rates_json="[]",
        )
        session.add_all([old_obs, normal_obs, unknown_obs])
        session.flush()

        session.add(NetworkFeatures(
            network_observation_id=normal_obs.id,
            ssid_bssid_count=1.0,
            bssid_changed=0.0,
            security_changed=0.0,
            security_strength_delta=0.0,
            context_available=True,
            context_resolution="ssid_hash",
            feature_complete=True,
        ))
        session.add(NetworkFeatures(
            network_observation_id=unknown_obs.id,
            context_available=False,
            context_resolution="unresolved",
            feature_complete=False,
        ))

        normal_detection = Detection(
            scan_session_id=new_scan.id,
            network_observation_id=normal_obs.id,
            model_version_id=model.id,
            anomaly_score=0.1,
            threshold=0.5,
            is_anomaly=False,
            suspicion_level="low",
            reason="normal fixture",
            inference_ms=0.2,
        )
        unknown_detection = Detection(
            scan_session_id=new_scan.id,
            network_observation_id=unknown_obs.id,
            model_version_id=model.id,
            anomaly_score=None,
            threshold=None,
            is_anomaly=None,
            suspicion_level="unavailable",
            reason="insufficient history fixture",
            inference_ms=None,
        )
        session.add_all([normal_detection, unknown_detection])
        session.commit()

        return {
            "old_scan": old_scan.id,
            "new_scan": new_scan.id,
            "model_id": model.id,
            "normal_detection_id": normal_detection.id,
        }


def _client(tmp_path):
    engine = create_database_engine("sqlite:///" + str(tmp_path / "history.db"))
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    ids = _seed(factory)
    persistence = ScanPersistenceService(factory)

    app = create_app(
        scanner_service=ScannerService(scanner=NeverCalledScanner()),
        runtime_store=RuntimeStore(),
        model_status_service=ModelArtifactStatusService(project_root=tmp_path),
        persistence_service=persistence,
        database_status_service=DatabaseStatusService(engine, persistence),
    )
    return TestClient(app), ids


def test_scan_history_is_newest_first(tmp_path):
    client, ids = _client(tmp_path)
    response = client.get("/history/scans")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 2
    assert payload["items"][0]["scan_id"] == ids["new_scan"]
    assert payload["items"][0]["feature_count"] == 2
    assert payload["items"][0]["detection_count"] == 2
    assert payload["items"][0]["anomaly_count"] == 0
    assert payload["items"][0]["insufficient_history_count"] == 1


def test_scan_history_serializes_observed_at_with_explicit_utc(tmp_path):
    client, _ = _client(tmp_path)

    response = client.get("/history/scans")
    assert response.status_code == 200

    observed_at = response.json()["items"][0]["observed_at_utc"]

    assert (
        observed_at.endswith("Z")
        or observed_at.endswith("+00:00")
    )


def test_scan_detail_never_exposes_clear_identifiers(tmp_path):
    client, ids = _client(tmp_path)
    response = client.get("/history/scans/" + ids["new_scan"])
    assert response.status_code == 200
    observation = response.json()["observations"][0]
    assert observation["ssid_hash"] is not None
    assert observation["bssid_hash"] is not None
    assert "ssid" not in observation
    assert "bssid" not in observation
    assert "interface_guid" not in observation


def test_observation_pagination(tmp_path):
    client, ids = _client(tmp_path)
    response = client.get(
        f"/history/scans/{ids['new_scan']}/observations",
        params={"limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 2
    assert payload["pagination"]["returned"] == 1


def test_detection_filters_and_detail(tmp_path):
    client, ids = _client(tmp_path)
    response = client.get(
        "/history/detections",
        params={"is_anomaly": "false", "suspicion_level": "low"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    detection_id = payload["items"][0]["detection_id"]
    detail = client.get(f"/history/detections/{detection_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["detection"]["is_anomaly"] is False
    assert body["model_version"]["version_name"] == "desktop_candidate_v1-test"
    assert "ssid" not in body["observation"]


def test_model_history(tmp_path):
    client, ids = _client(tmp_path)
    response = client.get("/history/models")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["model_version_id"] == ids["model_id"]
    assert item["detection_count"] == 2
    detail = client.get(f"/history/models/{ids['model_id']}")
    assert detail.status_code == 200
    assert detail.json()["reference_sha256"] == "a" * 64


def test_not_found_maps_404(tmp_path):
    client, ids = _client(tmp_path)
    assert client.get("/history/scans/missing").status_code == 404
    assert client.get("/history/detections/999999").status_code == 404
    assert client.get("/history/models/999999").status_code == 404


def test_pagination_validation(tmp_path):
    client, ids = _client(tmp_path)
    assert client.get("/history/scans", params={"limit": 0}).status_code == 422
    assert client.get("/history/detections", params={"offset": -1}).status_code == 422
