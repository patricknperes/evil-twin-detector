import pandas as pd

from ml.datasets.contextual_ml import (
    build_ml_bundle,
    CONTEXTUAL_FULL_V1,
)


def test_contextual_bundle_excludes_metadata():
    df = pd.DataFrame({
        "source_dataset": [
            "mendeley_rogue_ap"
        ],
        "session_id": [
            "session_001"
        ],
        "elapsed_ms": [
            100
        ],
        "ssid_hash": [
            "ssid-hash"
        ],
        "bssid_hash": [
            "bssid-hash"
        ],
        "label": [
            0
        ],
        "attack_type": [
            pd.NA
        ],
        "is_synthetic": [
            False
        ],
        "ssid_bssid_count": [
            1.0
        ],
        "bssid_changed": [
            0.0
        ],
        "channel_changed": [
            0.0
        ],
        "security_changed": [
            0.0
        ],
        "security_strength_delta": [
            0.0
        ],
        "is_hidden": [
            0.0
        ],
    })

    X, y, metadata = (
        build_ml_bundle(
            df
        )
    )

    assert list(
        X.columns
    ) == CONTEXTUAL_FULL_V1

    assert (
        "ssid_hash"
        not in X.columns
    )

    assert (
        metadata[
            "ssid_hash"
        ].iloc[0]
        == "ssid-hash"
    )

    assert y.iloc[0] == 0
