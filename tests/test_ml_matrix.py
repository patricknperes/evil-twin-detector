import pandas as pd

from ml.datasets.ml_matrix import (
    build_ml_matrix,
    FEATURE_SETS,
)


def test_ml_matrix_excludes_metadata():
    df = pd.DataFrame({
        "source_dataset": [
            "mendeley_rogue_ap"
        ],
        "session_id": [
            "s1"
        ],
        "network_identity_id": [
            "n1"
        ],
        "network_group_id": [
            "g1"
        ],
        "window_start_ms": [
            0
        ],
        "label": [
            0
        ],
        "rssi_std_db": [
            2.0
        ],
        "rssi_delta_db": [
            -1.0
        ],
        "window_count": [
            3
        ],
    })

    X, y, metadata = (
        build_ml_matrix(
            df,
            FEATURE_SETS[
                "conservative_v1"
            ],
        )
    )

    assert list(
        X.columns
    ) == [
        "rssi_std_db",
        "rssi_delta_db",
        "window_count",
    ]

    assert (
        "source_dataset"
        not in X.columns
    )

    assert (
        metadata[
            "source_dataset"
        ].iloc[0]
        == "mendeley_rogue_ap"
    )

    assert y.iloc[0] == 0
