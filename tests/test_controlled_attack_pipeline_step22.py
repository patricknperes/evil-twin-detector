import json

import pandas as pd

from desktop.windows.controlled_attack_collection import (
    collect_controlled_attack_session,
)
from desktop.windows.import_controlled_attack import (
    import_attack_session,
)
from desktop.windows.native_wifi_contract import (
    NativeWifiBssObservation,
)
from desktop.windows.prepare_controlled_attack_features import (
    prepare_attack_features,
)
from desktop.windows.wlanapi_ctypes import (
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
    NativeWifiInterface,
    NativeWifiInterfaceScan,
    NativeWifiScanBatch,
)


TARGET_BSSID = "02:11:22:33:44:55"


class FakeScanner:
    def scan_all(
        self,
        **kwargs,
    ):
        observation = NativeWifiBssObservation(
            ssid=b"Rede",
            bssid="02:11:22:33:44:55",
            rssi_dbm=-45,
            link_quality=90,
            beacon_period_tu=100,
            tsf_us=123456,
            host_timestamp_100ns=999999,
            capability_info=0,
            center_frequency_khz=2437000,
            ie_blob=bytes([
                3, 1, 6
            ]),
        )

        native = NativeWifiBssNativeMetadata(
            phy_id=1,
            bss_type_code=1,
            bss_type="infrastructure",
            phy_type_code=7,
            phy_type="ht",
            in_reg_domain=True,
            supported_rates_mbps=(6.0,),
        )

        interface = NativeWifiInterface(
            guid="GUID-ATTACK",
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
                            observation=observation,
                            native=native,
                        ),
                    ),
                    requested_fresh_scan=True,
                    scan_wait_seconds=0.0,
                    wait_strategy="fake",
                ),
            ),
        )


def test_attack_collection_requires_authorization(
    tmp_path,
):
    try:
        collect_controlled_attack_session(
            scenario="controlled_evil_twin",
            target_bssid=TARGET_BSSID,
            environment="lab",
            authorization_note="",
            output_root=tmp_path,
            scanner=FakeScanner(),
            scans=1,
            interval_seconds=0,
            scan_wait_seconds=0,
            sleep_fn=lambda _: None,
        )
    except ValueError as exc:
        assert "authorization_note" in str(
            exc
        )
    else:
        raise AssertionError(
            "Authorization note deveria ser obrigatório."
        )


def test_attack_collection_and_import(
    tmp_path,
):
    raw = tmp_path / "raw"
    interim = tmp_path / "interim"

    result = collect_controlled_attack_session(
        scenario="controlled_evil_twin",
        environment="lab",
        target_bssid=TARGET_BSSID,
        authorization_note="authorized lab fixture",
        output_root=raw,
        scanner=FakeScanner(),
        scans=2,
        interval_seconds=0,
        scan_wait_seconds=0,
        session_id="win-attack-test",
        sleep_fn=lambda _: None,
    )

    manifest = result[
        "manifest"
    ]

    assert manifest[
        "label"
    ] == 1

    assert manifest[
        "attack_present"
    ] is True

    assert manifest[
        "authorization"
    ][
        "authorized_controlled_experiment"
    ] is True

    imported = import_attack_session(
        raw
        / "win-attack-test",
        interim,
    )

    assert imported[
        "rows"
    ] == 2

    frame = pd.read_csv(
        interim
        / "win-attack-test"
        / "observations.csv.gz"
    )

    assert set(
        frame[
            "label"
        ]
    ) == {
        1
    }

    assert set(
        frame[
            "attack_type"
        ]
    ) == {
        "controlled_evil_twin"
    }

    assert "ssid" not in frame.columns
    assert "bssid" not in frame.columns


def test_attack_features_use_frozen_reference_only(
    tmp_path,
):
    interim = tmp_path / "attack"

    folder = interim / "attack-session"
    folder.mkdir(
        parents=True
    )

    frame = pd.DataFrame({
        "source_dataset": [
            "own_windows_attack"
        ],
        "session_id": [
            "attack-session"
        ],
        "environment": [
            "lab"
        ],
        "captured_at_utc": [
            "2026-08-31T00:00:00+00:00"
        ],
        "scan_index": [
            0
        ],
        "interface_guid": [
            "GUID"
        ],
        "ssid_hash": [
            "ssid-a"
        ],
        "bssid_hash": [
            "bssid-new"
        ],
        "security_type": [
            "OPEN"
        ],
        "security_strength": [
            0
        ],
        "session_label": [
            1
        ],
        "label": [
            1
        ],
        "is_attack_target": [
            True
        ],
        "attack_type": [
            "controlled_evil_twin"
        ],
        "is_synthetic": [
            False
        ],
    })

    frame.to_csv(
        folder
        / "observations.csv.gz",
        index=False,
        compression="gzip",
    )

    reference = {
        "schema_version":
            "desktop_normal_reference_v1",
        "split_digest":
            "a"
            * 64,
        "scientific_freeze_sha256":
            "b"
            * 64,
        "normal_cohort_environment":
            "lab",
        "normal_cohort_environments": [
            "lab"
        ],
        "ssid_profiles": {
            "ssid-a": {
                "bssid_hashes": [
                    "bssid-known"
                ],
                "bssid_count":
                    1,
                "security_types": [
                    "WPA2_OR_NEWER"
                ],
                "security_strength_median":
                    3.0,
                "reference_rows":
                    10,
                "reference_sessions": [
                    "reference-session"
                ],
            }
        },
        "bssid_to_ssids": {
            "bssid-known": [
                "ssid-a"
            ]
        },
    }

    reference_path = (
        tmp_path
        / "desktop_normal_reference.json"
    )

    reference_path.write_text(
        json.dumps(
            reference
        ),
        encoding="utf-8",
    )

    output = (
        tmp_path
        / "features"
    )

    result = prepare_attack_features(
        interim,
        reference_path,
        output,
    )

    assert result[
        "status"
    ] == "attack_features_ready"

    assert result[
        "normal_reference_updated"
    ] is False

    assert result[
        "model_updated"
    ] is False

    assert result[
        "threshold_updated"
    ] is False

    assert (
        result[
            "split_digest"
        ]
        == "a"
        * 64
    )

    assert len(
        result[
            "reference_file_sha256"
        ]
    ) == 64

    features = pd.read_csv(
        output
        / "attack_features_eligible.csv.gz"
    )

    assert features.iloc[
        0
    ][
        "bssid_changed"
    ] == 1.0

    assert features.iloc[
        0
    ][
        "security_changed"
    ] == 1.0

    assert features.iloc[
        0
    ][
        "security_strength_delta"
    ] == -3.0


def test_attack_features_block_environment_mismatch_without_creating_output(
    tmp_path,
):
    interim = tmp_path / "attack"
    folder = interim / "attack-session"
    folder.mkdir(parents=True)

    pd.DataFrame({
        "source_dataset": ["own_windows_attack"],
        "session_id": ["attack-session"],
        "environment": ["other-lab"],
        "captured_at_utc": ["2026-08-31T00:00:00+00:00"],
        "scan_index": [0],
        "interface_guid": ["GUID"],
        "ssid_hash": ["ssid-a"],
        "bssid_hash": ["bssid-new"],
        "security_type": ["OPEN"],
        "security_strength": [0],
        "session_label": [1],
        "label": [1],
        "is_attack_target": [True],
        "attack_type": ["controlled_evil_twin"],
        "is_synthetic": [False],
    }).to_csv(
        folder / "observations.csv.gz",
        index=False,
        compression="gzip",
    )

    reference_path = tmp_path / "reference.json"

    reference_path.write_text(
        json.dumps({
            "split_digest": "a" * 64,
            "scientific_freeze_sha256": "b" * 64,
            "normal_cohort_environment": "lab",
            "ssid_profiles": {
                "ssid-a": {
                    "bssid_hashes": ["known"],
                    "bssid_count": 1,
                    "security_types": ["WPA2_OR_NEWER"],
                    "security_strength_median": 3.0,
                    "reference_rows": 1,
                    "reference_sessions": ["ref"],
                }
            },
            "bssid_to_ssids": {
                "known": ["ssid-a"]
            },
        }),
        encoding="utf-8",
    )

    output = tmp_path / "out"

    result = prepare_attack_features(
        interim,
        reference_path,
        output,
    )

    assert (
        result["status"]
        == "blocked_attack_environment_mismatch"
    )

    assert not output.exists()


def test_attack_features_block_low_coverage_without_creating_output(
    tmp_path,
):
    interim = tmp_path / "attack"
    folder = interim / "attack-session"
    folder.mkdir(parents=True)

    pd.DataFrame({
        "source_dataset": [
            "own_windows_attack"
        ] * 2,
        "session_id": [
            "attack-session"
        ] * 2,
        "environment": [
            "lab"
        ] * 2,
        "captured_at_utc": [
            "2026-08-31T00:00:00+00:00"
        ] * 2,
        "scan_index": [
            0,
            1
        ],
        "interface_guid": [
            "GUID"
        ] * 2,
        "ssid_hash": [
            "unknown-1",
            "unknown-2"
        ],
        "bssid_hash": [
            "new-1",
            "new-2",
        ],
        "security_type": [
            "OPEN",
            "OPEN",
        ],
        "security_strength": [
            0,
            0,
        ],
        "session_label": [
            1,
            1,
        ],
        "label": [
            1,
            0,
        ],
        "is_attack_target": [
            True,
            False,
        ],
        "attack_type": [
            "controlled_evil_twin",
            "controlled_evil_twin",
        ],
        "is_synthetic": [
            False,
            False,
        ],
    }).to_csv(
        folder / "observations.csv.gz",
        index=False,
        compression="gzip",
    )

    reference_path = tmp_path / "reference.json"

    reference_path.write_text(
        json.dumps({
            "split_digest": "a" * 64,
            "scientific_freeze_sha256": "b" * 64,
            "normal_cohort_environment": "lab",
            "ssid_profiles": {
                "known": {
                    "bssid_hashes": [
                        "known-bssid"
                    ],
                    "bssid_count": 1,
                    "security_types": [
                        "WPA2_OR_NEWER"
                    ],
                    "security_strength_median": 3.0,
                    "reference_rows": 1,
                    "reference_sessions": [
                        "ref"
                    ],
                }
            },
            "bssid_to_ssids": {
                "known-bssid": [
                    "known"
                ]
            },
        }),
        encoding="utf-8",
    )

    output = tmp_path / "out"

    result = prepare_attack_features(
        interim,
        reference_path,
        output,
    )

    assert (
        result["status"]
        == "blocked_attack_feature_coverage_below_minimum"
    )

    assert (
        result[
            "eligible_rate"
        ]
        == 0.0
    )

    assert not output.exists()


def test_attack_features_block_without_reference(
    tmp_path,
):
    result = prepare_attack_features(
        tmp_path
        / "attack",
        tmp_path
        / "missing-reference.json",
        tmp_path
        / "output",
    )

    assert result[
        "status"
    ] == "blocked_frozen_reference_missing"

    assert result[
        "features_created"
    ] is False


def test_attack_batch_import_is_idempotent_when_existing_interim_matches_source(
    tmp_path,
):
    from desktop.windows.import_controlled_attack import (
        import_all_attack_sessions,
    )

    raw = tmp_path / "raw"
    interim = tmp_path / "interim"

    collect_controlled_attack_session(
        scenario="controlled_evil_twin",
        target_bssid=TARGET_BSSID,
        environment="lab",
        authorization_note="authorized",
        output_root=raw,
        scanner=FakeScanner(),
        scans=2,
        interval_seconds=0,
        scan_wait_seconds=0,
        session_id="attack-idempotent",
        sleep_fn=lambda _: None,
    )

    first = import_all_attack_sessions(
        raw,
        interim,
    )

    assert first[
        "imported_sessions"
    ] == 1

    assert first[
        "rejected_sessions"
    ] == 0

    second = import_all_attack_sessions(
        raw,
        interim,
    )

    assert second[
        "imported_sessions"
    ] == 0

    assert second[
        "skipped_existing_sessions"
    ] == 1

    assert second[
        "rejected_sessions"
    ] == 0

    assert second[
        "real_attack_data_available"
    ] is True