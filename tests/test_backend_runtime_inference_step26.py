import json

import joblib
import pandas as pd
from fastapi.testclient import (
    TestClient,
)
from sklearn.preprocessing import (
    StandardScaler,
)
from sklearn.svm import (
    OneClassSVM,
)
from sqlalchemy import (
    func,
    select,
)

from backend.app import create_app
from backend.db import (
    create_database_engine,
    create_session_factory,
)
from backend.inference import (
    FrozenDesktopInferenceService,
    sha256_file,
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
from desktop.windows.scan_serialization import (
    hash_identifier,
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


FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]


class FakeScanner:
    def __init__(
        self,
        *,
        ssid=b"Rede Modelo",
        bssid="00:11:22:33:44:55",
        security_capability=0x0010,
    ):
        self.ssid = ssid
        self.bssid = bssid
        self.security_capability = (
            security_capability
        )

    def scan_all(
        self,
        **kwargs,
    ):
        observation = (
            NativeWifiBssObservation(
                ssid=self.ssid,
                bssid=self.bssid,
                rssi_dbm=-45,
                link_quality=88,
                beacon_period_tu=100,
                tsf_us=123456,
                host_timestamp_100ns=987654,
                capability_info=(
                    self
                    .security_capability
                ),
                center_frequency_khz=2437000,
                ie_blob=bytes([
                    3,
                    1,
                    6,
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
                    12.0,
                ),
            )
        )

        interface = (
            NativeWifiInterface(
                guid="{FAKE-GUID}",
                description="Fake Wi-Fi",
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
                    requested_fresh_scan=True,
                    scan_wait_seconds=0.0,
                    wait_strategy="fake",
                ),
            ),
        )


def _write_runtime_artifacts(
    root,
    *,
    reference_ssid="Rede Modelo",
    reference_bssid=(
        "00:11:22:33:44:55"
    ),
):
    reference_path = (
        root
        / "data/processed/"
        "desktop_candidate_v1/"
        "desktop_normal_reference.json"
    )

    scaler_path = (
        root
        / "ml/models/preprocessing/"
        "desktop_candidate_v1_standard_scaler.joblib"
    )

    model_path = (
        root
        / "ml/models/"
        "desktop_candidate_v1/"
        "ocsvm_v1/"
        "one_class_svm_desktop_candidate_v1.joblib"
    )

    threshold_path = (
        root
        / "ml/models/"
        "desktop_candidate_v1/"
        "ocsvm_v1/"
        "threshold.json"
    )

    for path in [
        reference_path,
        scaler_path,
        model_path,
        threshold_path,
    ]:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    ssid_hash = hash_identifier(
        "ssid",
        reference_ssid,
    )

    bssid_hash = hash_identifier(
        "bssid",
        reference_bssid,
    )

    reference = {
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
        "ssid_profile_count":
            1,
        "bssid_mapping_count":
            1,
        "ssid_profiles": {
            ssid_hash: {
                "bssid_hashes": [
                    bssid_hash
                ],
                "bssid_count":
                    1,
                "security_types": [
                    "LEGACY_PRIVACY"
                ],
                "security_strength_median":
                    1.0,
                "reference_rows":
                    10,
                "reference_sessions": [
                    "ref-session"
                ],
            }
        },
        "bssid_to_ssids": {
            bssid_hash: [
                ssid_hash
            ]
        },
    }

    reference_path.write_text(
        json.dumps(
            reference
        ),
        encoding="utf-8",
    )

    # Software fixture only.
    train = pd.DataFrame({
        "ssid_bssid_count": [
            1.0,
            1.0,
            1.0,
            1.0,
            2.0,
            2.0,
        ],
        "bssid_changed": [
            0.0
        ] * 6,
        "security_changed": [
            0.0
        ] * 6,
        "security_strength_delta": [
            0.0
        ] * 6,
    })

    scaler = StandardScaler()

    scaler.fit(
        train[
            FEATURES
        ]
    )

    scaled = pd.DataFrame(
        scaler.transform(
            train[
                FEATURES
            ]
        ),
        columns=FEATURES,
    )

    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
    )

    model.fit(
        scaled
    )

    joblib.dump(
        scaler,
        scaler_path,
    )

    joblib.dump(
        model,
        model_path,
    )

    # Deliberately permissive software-only threshold fixture.
    # Its lineage contract mirrors the real frozen runtime bundle.
    threshold_path.write_text(
        json.dumps({
            "schema_version":
                "desktop_threshold_v2",
            "feature_set_name":
                "desktop_candidate_v1",
            "features":
                FEATURES,
            "source_split":
                "validation",
            "source_label":
                "normal_only",
            "threshold":
                999.0,
            "attack_used_for_calibration":
                False,
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
            "reference_file_sha256":
                sha256_file(
                    reference_path
                ),
            "scaler_file_sha256":
                sha256_file(
                    scaler_path
                ),
            "model_file_sha256":
                sha256_file(
                    model_path
                ),
            "artifact_lineage_file_sha256":
                "c"
                * 64,
        }),
        encoding="utf-8",
    )


def _client(
    tmp_path,
    *,
    scanner=None,
    artifacts=False,
):
    if artifacts:
        _write_runtime_artifacts(
            tmp_path
        )

    engine = create_database_engine(
        "sqlite:///"
        + str(
            tmp_path
            / "runtime.db"
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

    database_status = (
        DatabaseStatusService(
            engine,
            persistence,
        )
    )

    model_status = (
        ModelArtifactStatusService(
            project_root=tmp_path
        )
    )

    inference = (
        FrozenDesktopInferenceService(
            model_status
        )
    )

    app = create_app(
        scanner_service=(
            ScannerService(
                scanner=(
                    scanner
                    or FakeScanner()
                )
            )
        ),
        runtime_store=RuntimeStore(),
        model_status_service=(
            model_status
        ),
        inference_service=inference,
        persistence_service=(
            persistence
        ),
        database_status_service=(
            database_status
        ),
    )

    return (
        TestClient(
            app
        ),
        factory,
    )


def test_missing_artifacts_keep_scan_available(
    tmp_path,
):
    client, factory = _client(
        tmp_path,
        artifacts=False,
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds":
                0,
        },
    )

    assert (
        response.status_code
        == 200
    )

    analysis = (
        response.json()[
            "networks"
        ][
            0
        ][
            "analysis"
        ]
    )

    assert (
        analysis[
            "status"
        ]
        == "not_available"
    )

    with factory() as session:
        assert session.scalar(
            select(
                func.count()
            ).select_from(
                NetworkObservation
            )
        ) == 1

        assert session.scalar(
            select(
                func.count()
            ).select_from(
                NetworkFeatures
            )
        ) == 0

        assert session.scalar(
            select(
                func.count()
            ).select_from(
                Detection
            )
        ) == 0

        assert session.scalar(
            select(
                func.count()
            ).select_from(
                ModelVersion
            )
        ) == 0


def test_ready_runtime_persists_features_detection_and_model(
    tmp_path,
):
    client, factory = _client(
        tmp_path,
        artifacts=True,
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds":
                0,
        },
    )

    assert (
        response.status_code
        == 200
    )

    network = (
        response.json()[
            "networks"
        ][
            0
        ]
    )

    analysis = network[
        "analysis"
    ]

    assert (
        analysis[
            "status"
        ]
        == "ready"
    )

    assert (
        analysis[
            "context_available"
        ]
        is True
    )

    assert (
        analysis[
            "feature_complete"
        ]
        is True
    )

    assert (
        analysis[
            "features"
        ][
            "ssid_bssid_count"
        ]
        == 1.0
    )

    assert (
        analysis[
            "features"
        ][
            "bssid_changed"
        ]
        == 0.0
    )

    assert (
        analysis[
            "features"
        ][
            "security_changed"
        ]
        == 0.0
    )

    assert (
        analysis[
            "features"
        ][
            "security_strength_delta"
        ]
        == 0.0
    )

    assert (
        analysis[
            "model_version"
        ]
        .startswith(
            "desktop_candidate_v1-"
        )
    )

    # threshold=999 in fixture => software observation is not anomaly.
    assert (
        analysis[
            "is_anomaly"
        ]
        is False
    )

    assert (
        analysis[
            "suspicion_level"
        ]
        == "low"
    )

    with factory() as session:
        feature = (
            session.scalar(
                select(
                    NetworkFeatures
                )
            )
        )

        detection = (
            session.scalar(
                select(
                    Detection
                )
            )
        )

        model_version = (
            session.scalar(
                select(
                    ModelVersion
                )
            )
        )

    assert feature is not None

    assert (
        feature
        .ssid_bssid_count
        == 1.0
    )

    assert detection is not None

    assert (
        detection
        .is_anomaly
        is False
    )

    assert (
        detection
        .suspicion_level
        == "low"
    )

    assert model_version is not None

    assert (
        model_version.active
        is True
    )

    assert (
        model_version
        .reference_sha256
    )

    assert (
        model_version
        .threshold_sha256
    )


def test_unknown_network_is_insufficient_history_not_attack(
    tmp_path,
):
    _write_runtime_artifacts(
        tmp_path,
        reference_ssid=(
            "Rede Conhecida"
        ),
        reference_bssid=(
            "00:AA:BB:CC:DD:EE"
        ),
    )

    engine = create_database_engine(
        "sqlite:///"
        + str(
            tmp_path
            / "unknown.db"
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

    model_status = (
        ModelArtifactStatusService(
            project_root=tmp_path
        )
    )

    app = create_app(
        scanner_service=(
            ScannerService(
                scanner=FakeScanner(
                    ssid=b"Outra Rede",
                    bssid=(
                        "00:00:00:00:00:01"
                    ),
                )
            )
        ),
        runtime_store=RuntimeStore(),
        model_status_service=(
            model_status
        ),
        inference_service=(
            FrozenDesktopInferenceService(
                model_status
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

    client = TestClient(
        app
    )

    response = client.post(
        "/scan",
        json={
            "scan_wait_seconds":
                0
        },
    )

    assert (
        response.status_code
        == 200
    )

    analysis = (
        response.json()[
            "networks"
        ][
            0
        ][
            "analysis"
        ]
    )

    assert (
        analysis[
            "status"
        ]
        == "insufficient_history"
    )

    assert (
        analysis[
            "is_anomaly"
        ]
        is None
    )

    assert (
        analysis[
            "suspicion_level"
        ]
        == "unavailable"
    )

    with factory() as session:
        feature = (
            session.scalar(
                select(
                    NetworkFeatures
                )
            )
        )

        detection = (
            session.scalar(
                select(
                    Detection
                )
            )
        )

    assert feature is not None

    assert (
        feature
        .context_available
        is False
    )

    assert detection is not None

    assert (
        detection
        .is_anomaly
        is None
    )

    assert (
        detection
        .suspicion_level
        == "unavailable"
    )


def test_same_artifact_bundle_reuses_model_version(
    tmp_path,
):
    client, factory = _client(
        tmp_path,
        artifacts=True,
    )

    for _ in range(
        2
    ):
        response = client.post(
            "/scan",
            json={
                "scan_wait_seconds":
                    0
            },
        )

        assert (
            response.status_code
            == 200
        )

    with factory() as session:
        versions = (
            session.scalars(
                select(
                    ModelVersion
                )
            ).all()
        )

        detections = (
            session.scalars(
                select(
                    Detection
                )
            ).all()
        )

    assert len(
        versions
    ) == 1

    assert len(
        detections
    ) == 2


def test_database_endpoint_counts_runtime_records(
    tmp_path,
):
    client, factory = _client(
        tmp_path,
        artifacts=True,
    )

    client.post(
        "/scan",
        json={
            "scan_wait_seconds":
                0
        },
    )

    payload = client.get(
        "/database"
    ).json()

    assert (
        payload[
            "scan_count"
        ]
        == 1
    )

    assert (
        payload[
            "observation_count"
        ]
        == 1
    )

    assert (
        payload[
            "feature_count"
        ]
        == 1
    )

    assert (
        payload[
            "detection_count"
        ]
        == 1
    )

    assert (
        payload[
            "model_version_count"
        ]
        == 1
    )


def test_model_status_requires_reference_too(
    tmp_path,
):
    service = (
        ModelArtifactStatusService(
            project_root=tmp_path
        )
    )

    payload = (
        service
        .get_status()
    )

    assert (
        payload.status
        == "not_ready"
    )

    assert set(
        payload
        .missing_artifacts
    ) == {
        "reference",
        "scaler",
        "model",
        "threshold",
    }