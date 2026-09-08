from pathlib import Path
import json

import pandas as pd


EXPECTED_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "channel_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
]


def validate_phase4_step6():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    base = (
        root
        / "data"
        / "processed"
        / "ml_ready"
        / "evil_twin_contextual_v1"
    )

    manifest = json.loads(
        (
            base
            / "ml_matrix_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest[
        "phase"
    ] == 4

    assert manifest[
        "step"
    ] == 6

    assert (
        manifest[
            "feature_sets"
        ][
            "contextual_full_v1"
        ][
            "features"
        ]
        == EXPECTED_FEATURES
    )

    assert (
        "configured_beacon_interval_ms"
        in manifest[
            "globally_constant_removed"
        ]
    )

    for split in [
        "model_train_normal",
        "validation_normal",
        "test_normal",
        "test_attack_synthetic",
    ]:
        folder = (
            base
            / "contextual_full_v1"
            / split
        )

        X = pd.read_csv(
            folder
            / "X.csv.gz"
        )

        y = pd.read_csv(
            folder
            / "y.csv.gz"
        )

        metadata = pd.read_csv(
            folder
            / "metadata.csv.gz"
        )

        assert list(
            X.columns
        ) == EXPECTED_FEATURES

        assert not X.isna().any().any()

        assert len(X) == len(y)
        assert len(X) == len(metadata)

        assert (
            "attack_type"
            not in X.columns
        )

        assert (
            "ssid_hash"
            not in X.columns
        )

    print(
        "Fase 4 / Passo 6 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_phase4_step6()
