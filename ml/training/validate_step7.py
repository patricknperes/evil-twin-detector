from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd


def validate_step7():
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    config = json.loads(
        (
            root
            / "config"
            / "anomaly_evaluation_protocol.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert config[
        "phase"
    ] == 3

    assert config[
        "step"
    ] == 7

    assert (
        config[
            "feature_set"
        ]
        == "conservative_v2"
    )

    assert (
        config[
            "threshold_calibration"
        ][
            "attack_data_used_for_threshold"
        ]
        is False
    )

    scaler_path = (
        root
        / "ml"
        / "models"
        / "preprocessing"
        / "conservative_v2_standard_scaler.joblib"
    )

    scaler = joblib.load(
        scaler_path
    )

    base = (
        root
        / "data"
        / "processed"
        / "ml_ready"
        / "profile_rssi_temporal_5s"
        / "conservative_v2_scaled"
    )

    train = pd.read_csv(
        base
        / "train_balanced"
        / "X.csv.gz"
    )

    assert np.allclose(
        train.mean().values,
        0.0,
        atol=1e-10,
    )

    assert np.allclose(
        train.std(
            ddof=0
        ).values,
        1.0,
        atol=1e-10,
    )

    assert len(
        scaler.mean_
    ) == 2

    print(
        "Fase 3 / Passo 7 "
        "validado com sucesso."
    )


if __name__ == "__main__":
    validate_step7()
