from pathlib import Path
import json

import pandas as pd


FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "channel_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
    "configured_beacon_interval_ms",
]


def validate_phase4_step5():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    base = (
        root
        / "data"
        / "processed"
        / "profile_evil_twin_contextual_v1"
    )

    manifest = json.loads(
        (
            base
            / "feature_manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert manifest[
        "phase"
    ] == 4

    assert manifest[
        "step"
    ] == 5

    assert manifest[
        "features_precommitted_before_this_step"
    ] == FEATURES

    for name in [
        "model_train_normal",
        "validation_normal",
        "test_normal",
        "test_attack_synthetic",
    ]:
        path = (
            base
            / f"{name}_eligible.csv.gz"
        )

        df = pd.read_csv(
            path
        )

        assert "ssid" not in df.columns
        assert "bssid" not in df.columns

        assert set(
            FEATURES
        ).issubset(
            df.columns
        )

        assert (
            df[
                FEATURES
            ]
            .notna()
            .all()
            .all()
        )

        assert (
            df[
                "context_available"
            ]
            .astype(bool)
            .all()
        )

    attack = pd.read_csv(
        base
        / "test_attack_synthetic_eligible.csv.gz"
    )

    assert (
        attack["label"] == 1
    ).all()

    normal = pd.read_csv(
        base
        / "test_normal_eligible.csv.gz"
    )

    assert (
        normal["label"] == 0
    ).all()

    print(
        "Fase 4 / Passo 5 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_phase4_step5()
