import pandas as pd

from ml.features.contextual_evil_twin import (
    build_reference,
    transform_contextual,
)


def _normal_reference():
    return pd.DataFrame({
        "source_dataset": [
            "mendeley_rogue_ap",
            "mendeley_rogue_ap",
        ],
        "session_id": [
            "session_001",
            "session_001",
        ],
        "elapsed_ms": [
            0,
            100,
        ],
        "ssid": [
            "Home",
            "Home",
        ],
        "bssid": [
            "00:11:22:33:44:55",
            "00:11:22:33:44:55",
        ],
        "channel": [
            6,
            6,
        ],
        "security_type": [
            "WPA2",
            "WPA2",
        ],
        "configured_beacon_interval_ms": [
            102.4,
            102.4,
        ],
        "is_hidden": [
            False,
            False,
        ],
        "label": [
            0,
            0,
        ],
        "attack_type": [
            pd.NA,
            pd.NA,
        ],
        "is_synthetic": [
            False,
            False,
        ],
    })


def test_bssid_channel_security_changes():
    reference = build_reference(
        _normal_reference()
    )

    current = pd.DataFrame({
        "source_dataset": [
            "mendeley_rogue_ap"
        ],
        "session_id": [
            "synthetic"
        ],
        "elapsed_ms": [
            1000
        ],
        "ssid": [
            "Home"
        ],
        "bssid": [
            "00:11:22:33:44:99"
        ],
        "channel": [
            11
        ],
        "security_type": [
            "OPEN"
        ],
        "configured_beacon_interval_ms": [
            102.4
        ],
        "is_hidden": [
            False
        ],
        "label": [
            1
        ],
        "attack_type": [
            "synthetic"
        ],
        "is_synthetic": [
            True
        ],
    })

    result = transform_contextual(
        current,
        reference,
    )

    row = result.iloc[0]

    assert row[
        "bssid_changed"
    ] == 1.0

    assert row[
        "channel_changed"
    ] == 1.0

    assert row[
        "security_changed"
    ] == 1.0

    assert row[
        "security_strength_delta"
    ] == -3.0


def test_hidden_ssid_can_resolve_by_known_bssid():
    reference = build_reference(
        _normal_reference()
    )

    current = _normal_reference().iloc[
        [0]
    ].copy()

    current["ssid"] = pd.NA
    current["is_hidden"] = True

    result = transform_contextual(
        current,
        reference,
    )

    row = result.iloc[0]

    assert bool(
        row[
            "context_available"
        ]
    )

    assert (
        row[
            "context_resolution"
        ]
        == "bssid_fallback"
    )

    assert row[
        "is_hidden"
    ] == 1.0


def test_output_does_not_store_raw_identifiers():
    reference = build_reference(
        _normal_reference()
    )

    result = transform_contextual(
        _normal_reference(),
        reference,
    )

    assert "ssid" not in result.columns
    assert "bssid" not in result.columns

    assert "ssid_hash" in result.columns
    assert "bssid_hash" in result.columns
