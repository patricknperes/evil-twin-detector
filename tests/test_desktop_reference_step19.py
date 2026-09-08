import hashlib
import json

import pandas as pd

from desktop.windows.desktop_reference import (
    build_desktop_reference,
    transform_desktop_features,
)
from desktop.windows.desktop_split_plan import (
    make_split_plan,
)
from desktop.windows.prepare_desktop_reference import (
    prepare_desktop_reference,
)


def _session(
    index,
):
    return {
        "session_id":
            f"session-{index}",
        "environment":
            "lab-a",
        "observations_path":
            f"/tmp/session-{index}.csv.gz",
        "manifest_path":
            f"/tmp/session-{index}.json",
        "rows":
            10,
        "runtime_ready":
            True,
    }


def test_split_plan_requires_five_sessions():
    result = make_split_plan([
        _session(1),
        _session(2),
        _session(3),
        _session(4),
    ])

    assert result[
        "status"
    ] == "insufficient_sessions"

    assert result[
        "minimum_required_sessions"
    ] == 5


def test_split_plan_is_group_level_and_complete():
    result = make_split_plan([
        _session(1),
        _session(2),
        _session(3),
        _session(4),
        _session(5),
    ])

    assert result[
        "status"
    ] == "ready"

    assignments = result[
        "assignments"
    ]

    assert len(
        assignments
    ) == 5

    session_ids = [
        item[
            "session_id"
        ]
        for item in assignments
    ]

    assert len(
        session_ids
    ) == len(
        set(
            session_ids
        )
    )

    assert result[
        "split_counts"
    ][
        "reference"
    ] == 1

    assert result[
        "split_counts"
    ][
        "model_train"
    ] == 2

    assert result[
        "split_counts"
    ][
        "validation"
    ] == 1

    assert result[
        "split_counts"
    ][
        "test_normal"
    ] == 1


def test_reference_and_feature_semantics():
    reference_frame = pd.DataFrame({
        "session_id": [
            "ref",
            "ref",
        ],
        "ssid_hash": [
            "ssid-a",
            "ssid-a",
        ],
        "bssid_hash": [
            "bssid-1",
            "bssid-2",
        ],
        "security_type": [
            "WPA2_OR_NEWER",
            "WPA2_OR_NEWER",
        ],
        "security_strength": [
            3,
            3,
        ],
    })

    reference = build_desktop_reference(
        reference_frame
    )

    current = pd.DataFrame({
        "ssid_hash": [
            "ssid-a",
            "ssid-a",
        ],
        "bssid_hash": [
            "bssid-1",
            "bssid-new",
        ],
        "security_type": [
            "WPA2_OR_NEWER",
            "OPEN",
        ],
        "security_strength": [
            3,
            0,
        ],
    })

    result = transform_desktop_features(
        current,
        reference,
    )

    assert result.iloc[
        0
    ][
        "ssid_bssid_count"
    ] == 2.0

    assert result.iloc[
        0
    ][
        "bssid_changed"
    ] == 0.0

    assert result.iloc[
        0
    ][
        "security_changed"
    ] == 0.0

    assert result.iloc[
        0
    ][
        "security_strength_delta"
    ] == 0.0

    assert result.iloc[
        1
    ][
        "bssid_changed"
    ] == 1.0

    assert result.iloc[
        1
    ][
        "security_changed"
    ] == 1.0

    assert result.iloc[
        1
    ][
        "security_strength_delta"
    ] == -3.0


def test_unknown_context_stays_unknown():
    reference_frame = pd.DataFrame({
        "session_id": [
            "ref"
        ],
        "ssid_hash": [
            "known"
        ],
        "bssid_hash": [
            "bssid-known"
        ],
        "security_type": [
            "WPA2_OR_NEWER"
        ],
        "security_strength": [
            3
        ],
    })

    reference = build_desktop_reference(
        reference_frame
    )

    current = pd.DataFrame({
        "ssid_hash": [
            "unknown"
        ],
        "bssid_hash": [
            "unknown-bssid"
        ],
        "security_type": [
            "WPA2_OR_NEWER"
        ],
        "security_strength": [
            3
        ],
    })

    result = transform_desktop_features(
        current,
        reference,
    )

    assert result.iloc[
        0
    ][
        "context_available"
    ] == False

    assert result.iloc[
        0
    ][
        "feature_complete"
    ] == False


def _write_interim_session(
    root,
    session_id,
    *,
    bssid_seed="bssid-1",
    captured_at="2026-08-31T15:00:00+00:00",
):
    folder = root / session_id

    folder.mkdir(
        parents=True
    )

    ssid_hash = hashlib.sha256(
        b"ssid-a"
    ).hexdigest()

    bssid_hash = hashlib.sha256(
        bssid_seed.encode(
            "utf-8"
        )
    ).hexdigest()

    frame = pd.DataFrame({
        "source_dataset": [
            "own_windows"
        ] * 3,
        "session_id": [
            session_id
        ] * 3,
        "environment": [
            "lab-a"
        ] * 3,
        "captured_at_utc": [
            captured_at,
            captured_at,
            captured_at,
        ],
        "scan_index": [
            0,
            1,
            2,
        ],
        "interface_guid": [
            "GUID"
        ] * 3,
        "ssid_hash": [
            ssid_hash
        ] * 3,
        "bssid_hash": [
            bssid_hash
        ] * 3,
        "security_type": [
            "WPA2_OR_NEWER"
        ] * 3,
        "security_strength": [
            3
        ] * 3,
        "label": [
            0
        ] * 3,
        "attack_type": [
            None
        ] * 3,
        "is_synthetic": [
            False
        ] * 3,
    })

    observations = (
        folder
        / "observations.csv.gz"
    )

    frame.to_csv(
        observations,
        index=False,
        compression="gzip",
    )

    observation_sha = hashlib.sha256(
        observations.read_bytes()
    ).hexdigest()

    (
        folder
        / "import_manifest.json"
    ).write_text(
        json.dumps({
            "schema_version":
                "own_windows_interim_import_v1",
            "session_id":
                session_id,
            "source_dataset":
                "own_windows",
            "source_scans_sha256":
                hashlib.sha256(
                    (
                        "raw-"
                        + session_id
                    ).encode(
                        "utf-8"
                    )
                ).hexdigest(),
            "source_sha256_verified":
                True,
            "interim_observations_sha256":
                observation_sha,
            "runtime_ready":
                True,
            "rows":
                3,
            "scan_count":
                3,
            "label":
                0,
            "attack_present":
                False,
            "environment":
                "lab-a",
        }),
        encoding="utf-8",
    )


def test_prepare_desktop_reference_five_sessions(
    tmp_path,
):
    interim = tmp_path / "interim"

    for index in range(
        5
    ):
        _write_interim_session(
            interim,
            f"session-{index}",
            bssid_seed=(
                f"bssid-{index}"
            ),
            captured_at=(
                f"2026-08-31T15:{index:02d}:00+00:00"
            ),
        )

    output = tmp_path / "processed"

    result = prepare_desktop_reference(
        interim,
        output,
    )

    assert result[
        "reference_built"
    ] is True

    assert result[
        "desktop_features_built"
    ] is True

    assert result[
        "model_training_started"
    ] is False

    assert (
        output
        / "desktop_normal_reference.json"
    ).exists()

    assert (
        output
        / "session_split_plan.json"
    ).exists()

    assert (
        output
        / "scientific_freeze.json"
    ).exists()

    reference = json.loads(
        (
            output
            / "desktop_normal_reference.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        reference[
            "split_digest"
        ]
    )

    assert (
        reference[
            "reference_source_hashes"
        ]
    )