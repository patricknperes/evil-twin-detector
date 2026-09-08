from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from backend.app import create_app
from backend.db import create_database_engine, create_session_factory
from backend.model_status import ModelArtifactStatusService
from backend.models import Base, NetworkObservation, ScanSession
from backend.persistence import DatabaseStatusService, ScanPersistenceService
from backend.runtime_store import RuntimeStore
from backend.scanner_service import ScannerService
from desktop.windows.native_wifi_contract import NativeWifiBssObservation
from desktop.windows.wlanapi_ctypes import (
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
)


class FakeScanner:
    def scan_all(self, **kwargs):
        obs = NativeWifiBssObservation(
            ssid=b"Rede Persistida",
            bssid="00:11:22:33:44:55",
            rssi_dbm=-45,
            link_quality=88,
            beacon_period_tu=100,
            tsf_us=123456,
            host_timestamp_100ns=987654,
            capability_info=0x0010,
            center_frequency_khz=2437000,
            ie_blob=bytes([3, 1, 6]),
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
                            observation=obs,
                            native=native,
                        ),
                    ),
                    requested_fresh_scan=True,
                    scan_wait_seconds=0.0,
                    wait_strategy="fake",
                ),
            ),
        )


def _stack(tmp_path):
    engine = create_database_engine(
        "sqlite:///" + str(tmp_path / "test.db")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    persistence = ScanPersistenceService(factory)
    database_status = DatabaseStatusService(engine, persistence)

    app = create_app(
        scanner_service=ScannerService(scanner=FakeScanner()),
        runtime_store=RuntimeStore(),
        model_status_service=ModelArtifactStatusService(
            project_root=tmp_path
        ),
        persistence_service=persistence,
        database_status_service=database_status,
    )
    return TestClient(app), engine, factory


def test_schema_contains_all_five_tables(tmp_path):
    engine = create_database_engine(
        "sqlite:///" + str(tmp_path / "schema.db")
    )
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "scan_session",
        "network_observation",
        "network_features",
        "detection",
        "model_version",
    }.issubset(tables)


def test_scan_is_persisted(tmp_path):
    client, engine, factory = _stack(tmp_path)
    response = client.post(
        "/scan",
        json={"scan_wait_seconds": 0},
    )
    assert response.status_code == 200

    with factory() as session:
        scans = session.scalars(select(ScanSession)).all()
        observations = session.scalars(
            select(NetworkObservation)
        ).all()

    assert len(scans) == 1
    assert len(observations) == 1
    assert scans[0].id == response.json()["scan_id"]


def test_clear_ssid_and_bssid_are_not_stored(tmp_path):
    client, engine, factory = _stack(tmp_path)
    response = client.post(
        "/scan",
        json={"scan_wait_seconds": 0},
    )
    assert response.status_code == 200

    network = response.json()["networks"][0]
    assert network["ssid"] == "Rede Persistida"
    assert network["bssid"] == "00:11:22:33:44:55"

    with factory() as session:
        observation = session.scalar(
            select(NetworkObservation)
        )

    assert observation.ssid_hash
    assert observation.bssid_hash

    columns = {
        column["name"]
        for column in inspect(engine).get_columns(
            "network_observation"
        )
    }
    assert "ssid" not in columns
    assert "bssid" not in columns


def test_database_status_endpoint(tmp_path):
    client, engine, factory = _stack(tmp_path)

    before = client.get("/database").json()
    assert before["status"] == "ready"
    assert before["scan_count"] == 0
    assert before["observation_count"] == 0

    assert client.post(
        "/scan",
        json={"scan_wait_seconds": 0},
    ).status_code == 200

    after = client.get("/database").json()
    assert after["scan_count"] == 1
    assert after["observation_count"] == 1


def test_health_reports_database_ready(tmp_path):
    client, engine, factory = _stack(tmp_path)
    assert client.get("/health").json()["database_status"] == "ready"


def test_duplicate_scan_id_is_rejected(tmp_path):
    client, engine, factory = _stack(tmp_path)
    assert client.post(
        "/scan",
        json={"scan_wait_seconds": 0},
    ).status_code == 200

    scan = client.app.state.runtime_store.get_latest_scan()

    try:
        client.app.state.persistence_service.persist_scan(scan)
    except ValueError as exc:
        assert "scan_id já persistido" in str(exc)
    else:
        raise AssertionError("Duplicate scan_id deveria falhar.")
