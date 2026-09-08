from datetime import (
    datetime,
    timedelta,
    timezone,
)

from fastapi.testclient import (
    TestClient,
)

from backend.app import create_app
from backend.db import (
    create_database_engine,
    create_session_factory,
)
from backend.model_status import (
    ModelArtifactStatusService,
)
from backend.models import (
    ApplicationSettings,
    Base,
    ScanSession,
)
from backend.persistence import (
    DatabaseStatusService,
    ScanPersistenceService,
)
from backend.runtime_store import (
    RuntimeStore,
)
from backend.scanner_service import (
    ScannerService,
)
from desktop.windows.native_wifi_contract import (
    NativeWifiBssObservation,
)
from desktop.windows.wlanapi_ctypes import (
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
)


class RecordingScanner:
    def __init__(
        self,
    ):
        self.calls = []

    def scan_all(
        self,
        **kwargs,
    ):
        self.calls.append(
            dict(
                kwargs
            )
        )

        observation = (
            NativeWifiBssObservation(
                ssid=b"Settings Test",
                bssid=(
                    "00:11:22:33:44:55"
                ),
                rssi_dbm=-50,
                link_quality=80,
                beacon_period_tu=100,
                tsf_us=10,
                host_timestamp_100ns=20,
                capability_info=0,
                center_frequency_khz=2412000,
                ie_blob=bytes([
                    3,
                    1,
                    1,
                ]),
            )
        )

        native = (
            NativeWifiBssNativeMetadata(
                phy_id=1,
                bss_type_code=1,
                bss_type=(
                    "infrastructure"
                ),
                phy_type_code=7,
                phy_type="ht",
                in_reg_domain=True,
                supported_rates_mbps=(
                    6.0,
                ),
            )
        )

        interface = (
            NativeWifiInterface(
                guid="{SETTINGS-GUID}",
                description="Fake",
                state_code=1,
                state="connected",
                _guid_struct=None,
            )
        )

        return NativeWifiScanBatch(
            negotiated_api_version=2,
            interface_scans=(
                NativeWifiInterfaceScan(
                    interface=interface,
                    bss_entries=(
                        NativeWifiBssResult(
                            observation=(
                                observation
                            ),
                            native=native,
                        ),
                    ),
                    requested_fresh_scan=(
                        bool(
                            kwargs.get(
                                "request_fresh_scan"
                            )
                        )
                    ),
                    scan_wait_seconds=(
                        float(
                            kwargs.get(
                                "scan_wait_seconds"
                            )
                        )
                    ),
                    wait_strategy="fake",
                ),
            ),
        )


def _stack(
    tmp_path,
):
    engine = (
        create_database_engine(
            "sqlite:///"
            + str(
                tmp_path
                / "settings.db"
            )
        )
    )

    Base.metadata.create_all(
        engine
    )

    factory = (
        create_session_factory(
            engine
        )
    )

    persistence = (
        ScanPersistenceService(
            factory
        )
    )

    scanner = RecordingScanner()

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
                project_root=tmp_path
            )
        ),
        persistence_service=(
            persistence
        ),
        database_status_service=(
            DatabaseStatusService(
                engine,
                persistence,
            )
        ),
    )

    return (
        TestClient(
            app
        ),
        factory,
        scanner,
    )


def test_settings_defaults_are_persisted(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    response = client.get(
        "/settings"
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()
    values = payload[
        "values"
    ]

    assert (
        values[
            "request_fresh_scan"
        ]
        is True
    )

    assert (
        values[
            "scan_wait_seconds"
        ]
        == 4.2
    )

    assert (
        values[
            "auto_scan_enabled"
        ]
        is False
    )

    assert (
        values[
            "history_page_size"
        ]
        == 25
    )

    assert (
        payload[
            "model_status"
        ]
        == "not_ready"
    )

    assert set(
        payload[
            "missing_model_artifacts"
        ]
    ) == {
        "reference",
        "scaler",
        "model",
        "threshold",
    }

    policy = payload[
        "scientific_policy"
    ]

    assert (
        policy[
            "model_fit_allowed"
        ]
        is False
    )

    assert (
        policy[
            "threshold_recalibration_allowed"
        ]
        is False
    )

    with factory() as session:
        row = session.get(
            ApplicationSettings,
            1,
        )

    assert row is not None


def test_settings_patch_persists(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    response = client.patch(
        "/settings",
        json={
            "scan_wait_seconds":
                2.5,
            "auto_scan_enabled":
                True,
            "auto_scan_interval_seconds":
                45,
            "history_page_size":
                10,
            "dashboard_recent_scans":
                3,
        },
    )

    assert (
        response.status_code
        == 200
    )

    values = response.json()[
        "values"
    ]

    assert (
        values[
            "scan_wait_seconds"
        ]
        == 2.5
    )

    assert (
        values[
            "auto_scan_enabled"
        ]
        is True
    )

    assert (
        values[
            "history_page_size"
        ]
        == 10
    )

    second = client.get(
        "/settings"
    ).json()[
        "values"
    ]

    assert (
        second[
            "scan_wait_seconds"
        ]
        == 2.5
    )

    assert (
        second[
            "auto_scan_interval_seconds"
        ]
        == 45.0
    )


def test_settings_reject_scientific_mutation_fields(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    for payload in [
        {
            "threshold":
                0.1
        },
        {
            "model_path":
                "other.joblib"
        },
        {
            "reference_path":
                "other.json"
        },
        {
            "scaler_fit_allowed":
                True
        },
    ]:
        response = client.patch(
            "/settings",
            json=payload,
        )

        assert (
            response.status_code
            == 422
        )


def test_settings_validation_ranges(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    assert client.patch(
        "/settings",
        json={
            "auto_scan_interval_seconds":
                5
        },
    ).status_code == 422

    assert client.patch(
        "/settings",
        json={
            "history_page_size":
                101
        },
    ).status_code == 422

    assert client.patch(
        "/settings",
        json={
            "frontend_refresh_seconds":
                1
        },
    ).status_code == 422


def test_settings_reset_restores_defaults(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    client.patch(
        "/settings",
        json={
            "scan_wait_seconds":
                1.0,
            "history_page_size":
                7,
            "show_technical_details":
                False,
        },
    )

    response = client.post(
        "/settings/reset"
    )

    assert (
        response.status_code
        == 200
    )

    values = response.json()[
        "values"
    ]

    assert (
        values[
            "scan_wait_seconds"
        ]
        == 4.2
    )

    assert (
        values[
            "history_page_size"
        ]
        == 25
    )

    assert (
        values[
            "show_technical_details"
        ]
        is True
    )


def test_scan_uses_persisted_defaults_when_request_omits_values(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    client.patch(
        "/settings",
        json={
            "request_fresh_scan":
                False,
            "scan_wait_seconds":
                1.5,
        },
    )

    response = client.post(
        "/scan",
        json={},
    )

    assert (
        response.status_code
        == 200
    )

    call = scanner.calls[
        -1
    ]

    assert (
        call[
            "request_fresh_scan"
        ]
        is False
    )

    assert (
        call[
            "scan_wait_seconds"
        ]
        == 1.5
    )


def test_scan_explicit_values_override_settings(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    client.patch(
        "/settings",
        json={
            "request_fresh_scan":
                False,
            "scan_wait_seconds":
                1.5,
        },
    )

    response = client.post(
        "/scan",
        json={
            "request_fresh_scan":
                True,
            "scan_wait_seconds":
                0.25,
        },
    )

    assert (
        response.status_code
        == 200
    )

    call = scanner.calls[
        -1
    ]

    assert (
        call[
            "request_fresh_scan"
        ]
        is True
    )

    assert (
        call[
            "scan_wait_seconds"
        ]
        == 0.25
    )


def test_history_default_limit_uses_settings(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    now = datetime.now(
        timezone.utc
    )

    with factory() as session:
        for index in range(
            4
        ):
            session.add(
                ScanSession(
                    id=(
                        "00000000-0000-0000-0000-"
                        + f"{index + 1:012d}"
                    ),
                    observed_at_utc=(
                        now
                        + timedelta(
                            seconds=index
                        )
                    ),
                    negotiated_api_version=2,
                    interface_count=1,
                    total_networks=0,
                )
            )

        session.commit()

    client.patch(
        "/settings",
        json={
            "history_page_size":
                2
        },
    )

    payload = client.get(
        "/history/scans"
    ).json()

    assert (
        payload[
            "pagination"
        ][
            "limit"
        ]
        == 2
    )

    assert (
        payload[
            "pagination"
        ][
            "returned"
        ]
        == 2
    )

    assert (
        payload[
            "pagination"
        ][
            "total"
        ]
        == 4
    )


def test_dashboard_default_limits_use_settings(
    tmp_path,
):
    client, factory, scanner = (
        _stack(
            tmp_path
        )
    )

    now = datetime.now(
        timezone.utc
    )

    with factory() as session:
        for index in range(
            3
        ):
            session.add(
                ScanSession(
                    id=(
                        "10000000-0000-0000-0000-"
                        + f"{index + 1:012d}"
                    ),
                    observed_at_utc=(
                        now
                        + timedelta(
                            seconds=index
                        )
                    ),
                    negotiated_api_version=2,
                    interface_count=1,
                    total_networks=0,
                )
            )

        session.commit()

    client.patch(
        "/settings",
        json={
            "dashboard_recent_scans":
                1,
            "dashboard_trend_limit":
                2,
        },
    )

    overview = client.get(
        "/dashboard/overview"
    ).json()

    assert len(
        overview[
            "recent_scans"
        ]
    ) == 1

    trends = client.get(
        "/dashboard/trends"
    ).json()

    assert (
        trends[
            "requested_limit"
        ]
        == 2
    )

    assert (
        trends[
            "returned"
        ]
        == 2
    )
