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
    Base,
    Detection,
    ModelVersion,
    NetworkFeatures,
    NetworkObservation,
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


class NeverCalledScanner:
    def scan_all(
        self,
        **kwargs,
    ):
        raise AssertionError(
            "Dashboard should not invoke Wi-Fi scan."
        )


def _stack(
    tmp_path,
    *,
    seed=True,
):
    engine = create_database_engine(
        "sqlite:///"
        + str(
            tmp_path
            / "dashboard.db"
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

    if seed:
        _seed(
            factory
        )

    persistence = (
        ScanPersistenceService(
            factory
        )
    )

    app = create_app(
        scanner_service=(
            ScannerService(
                scanner=(
                    NeverCalledScanner()
                )
            )
        ),
        runtime_store=RuntimeStore(),
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

    return TestClient(
        app
    )


def _seed(
    factory,
):
    now = datetime.now(
        timezone.utc
    )

    with factory() as session:
        model = ModelVersion(
            version_name="model-active",
            algorithm="OneClassSVM",
            feature_set_name=(
                "desktop_candidate_v1"
            ),
            reference_sha256=(
                "a" * 64
            ),
            scaler_sha256=(
                "b" * 64
            ),
            model_sha256=(
                "c" * 64
            ),
            threshold_sha256=(
                "d" * 64
            ),
            threshold=0.5,
            active=True,
        )

        session.add(
            model
        )

        session.flush()

        scans = []

        for index in range(
            3
        ):
            scan = ScanSession(
                id=(
                    "00000000-0000-0000-0000-"
                    + f"{index + 1:012d}"
                ),
                observed_at_utc=(
                    now
                    - timedelta(
                        minutes=(
                            10
                            - index
                        )
                    )
                ),
                negotiated_api_version=2,
                interface_count=1,
                total_networks=1,
            )

            session.add(
                scan
            )

            session.flush()

            observation = NetworkObservation(
                scan_session_id=scan.id,
                network_id=(
                    "network-a"
                    if index < 2
                    else "network-b"
                ),
                interface_guid_hash=(
                    "e" * 64
                ),
                ssid_hash=(
                    "f" * 64
                ),
                bssid_hash=(
                    str(
                        index + 1
                    )
                    * 64
                ),
                ssid_not_broadcast=False,
                rssi_dbm=(
                    -40
                    - index
                ),
                link_quality=90,
                beacon_interval_ms=102.4,
                tsf_us=100 + index,
                host_timestamp_100ns=(
                    1000
                    + index
                ),
                center_frequency_khz=2437000,
                ds_parameter_channel=6,
                security_type=(
                    "WPA2_OR_NEWER"
                ),
                security_strength=3,
                security_source="rsn",
                phy_type="ht",
                bss_type="infrastructure",
                supported_rates_json="[]",
            )

            session.add(
                observation
            )

            session.flush()

            session.add(
                NetworkFeatures(
                    network_observation_id=(
                        observation.id
                    ),
                    ssid_bssid_count=1.0,
                    bssid_changed=0.0,
                    security_changed=0.0,
                    security_strength_delta=0.0,
                    context_available=(
                        index
                        != 2
                    ),
                    context_resolution=(
                        "ssid_hash"
                        if index != 2
                        else "unresolved"
                    ),
                    feature_complete=(
                        index
                        != 2
                    ),
                )
            )

            if index == 0:
                detection = Detection(
                    scan_session_id=scan.id,
                    network_observation_id=(
                        observation.id
                    ),
                    model_version_id=model.id,
                    anomaly_score=0.1,
                    threshold=0.5,
                    is_anomaly=False,
                    suspicion_level="low",
                    reason="normal",
                    inference_ms=0.1,
                )

            elif index == 1:
                detection = Detection(
                    scan_session_id=scan.id,
                    network_observation_id=(
                        observation.id
                    ),
                    model_version_id=model.id,
                    anomaly_score=0.8,
                    threshold=0.5,
                    is_anomaly=True,
                    suspicion_level="high",
                    reason="anomaly",
                    inference_ms=0.2,
                )

            else:
                detection = Detection(
                    scan_session_id=scan.id,
                    network_observation_id=(
                        observation.id
                    ),
                    model_version_id=model.id,
                    anomaly_score=None,
                    threshold=None,
                    is_anomaly=None,
                    suspicion_level="unavailable",
                    reason="insufficient",
                    inference_ms=None,
                )

            session.add(
                detection
            )

            scans.append(
                scan
            )

        session.commit()


def test_empty_dashboard_returns_zeroes(
    tmp_path,
):
    client = _stack(
        tmp_path,
        seed=False,
    )

    response = client.get(
        "/dashboard/overview"
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()
    metrics = payload[
        "metrics"
    ]

    assert (
        metrics[
            "scan_count"
        ]
        == 0
    )

    assert (
        metrics[
            "observation_count"
        ]
        == 0
    )

    assert (
        metrics[
            "analysis_coverage_rate"
        ]
        == 0.0
    )

    assert (
        metrics[
            "anomaly_rate_among_decided"
        ]
        == 0.0
    )

    assert (
        payload[
            "active_model"
        ]
        is None
    )


def test_overview_aggregates_dashboard_metrics(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    response = client.get(
        "/dashboard/overview"
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()
    metrics = payload[
        "metrics"
    ]

    assert (
        metrics[
            "scan_count"
        ]
        == 3
    )

    assert (
        metrics[
            "observation_count"
        ]
        == 3
    )

    assert (
        metrics[
            "unique_network_count"
        ]
        == 2
    )

    assert (
        metrics[
            "feature_count"
        ]
        == 3
    )

    assert (
        metrics[
            "detection_count"
        ]
        == 3
    )

    assert (
        metrics[
            "anomaly_count"
        ]
        == 1
    )

    assert (
        metrics[
            "normal_count"
        ]
        == 1
    )

    assert (
        metrics[
            "insufficient_history_count"
        ]
        == 1
    )

    assert (
        metrics[
            "model_version_count"
        ]
        == 1
    )

    assert (
        metrics[
            "analysis_coverage_rate"
        ]
        == 1.0
    )

    assert (
        metrics[
            "anomaly_rate_among_decided"
        ]
        == 0.5
    )


def test_suspicion_distribution_and_active_model(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    payload = client.get(
        "/dashboard/overview"
    ).json()

    assert (
        payload[
            "suspicion_distribution"
        ]
        == {
            "low":
                1,
            "medium":
                0,
            "high":
                1,
            "unavailable":
                1,
        }
    )

    assert (
        payload[
            "active_model"
        ][
            "version_name"
        ]
        == "model-active"
    )

    assert (
        payload[
            "active_model"
        ][
            "detection_count"
        ]
        == 3
    )


def test_recent_limits_are_respected(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    payload = client.get(
        "/dashboard/overview",
        params={
            "recent_scans":
                2,
            "recent_detections":
                1,
        },
    ).json()

    assert len(
        payload[
            "recent_scans"
        ]
    ) == 2

    assert len(
        payload[
            "recent_detections"
        ]
    ) == 1


def test_dashboard_trends_are_chronological(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    response = client.get(
        "/dashboard/trends",
        params={
            "limit":
                2
        },
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert (
        payload[
            "returned"
        ]
        == 2
    )

    points = payload[
        "points"
    ]

    assert (
        points[
            0
        ][
            "observed_at_utc"
        ]
        < points[
            1
        ][
            "observed_at_utc"
        ]
    )

    assert (
        points[
            0
        ][
            "anomaly_count"
        ]
        == 1
    )

    assert (
        points[
            1
        ][
            "insufficient_history_count"
        ]
        == 1
    )


def test_dashboard_contains_runtime_statuses(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    system = client.get(
        "/dashboard/overview"
    ).json()[
        "system"
    ]

    assert (
        system[
            "backend_version"
        ]
        == "1.4.0-step52"
    )

    assert (
        system[
            "database_status"
        ]
        == "ready"
    )

    # No real model artifacts exist in fixture project_root.
    assert (
        system[
            "model_status"
        ]
        == "not_ready"
    )


def test_dashboard_query_validation(
    tmp_path,
):
    client = _stack(
        tmp_path
    )

    assert client.get(
        "/dashboard/overview",
        params={
            "recent_scans":
                21
        },
    ).status_code == 422

    assert client.get(
        "/dashboard/trends",
        params={
            "limit":
                0
        },
    ).status_code == 422
