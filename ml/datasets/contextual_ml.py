from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
from sklearn.preprocessing import (
    StandardScaler,
)


CONTEXTUAL_FULL_V1 = [
    "ssid_bssid_count",
    "bssid_changed",
    "channel_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
]

CONTEXTUAL_VARIABLE_ONLY_V1 = [
    "ssid_bssid_count",
    "channel_changed",
]

METADATA_COLUMNS = [
    "source_dataset",
    "session_id",
    "elapsed_ms",
    "ssid_hash",
    "bssid_hash",
    "context_available",
    "context_resolution",
    "feature_complete",
    "ssid_missing",
    "configured_beacon_interval_delta_ms",
    "label",
    "attack_type",
    "is_synthetic",
]


def build_ml_bundle(
    df,
    features=CONTEXTUAL_FULL_V1,
):
    X = (
        df[
            features
        ]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .copy()
    )

    if X.isna().any().any():
        raise ValueError(
            "X contém NaN."
        )

    y = (
        pd.to_numeric(
            df["label"],
            errors="raise",
        )
        .astype(int)
        .rename("label")
    )

    metadata = df[
        [
            column
            for column
            in METADATA_COLUMNS
            if column
            in df.columns
        ]
    ].copy()

    leakage = (
        set(
            METADATA_COLUMNS
        )
        & set(
            X.columns
        )
    )

    if leakage:
        raise AssertionError(
            "Metadados em X: "
            + ", ".join(
                sorted(
                    leakage
                )
            )
        )

    return (
        X,
        y,
        metadata,
    )


def fit_contextual_scaler(
    X_model_train_normal,
):
    scaler = StandardScaler()

    scaler.fit(
        X_model_train_normal
    )

    return scaler


def load_protocol(
    project_root=".",
):
    path = (
        Path(
            project_root
        )
        / "config"
        / "evil_twin_contextual_evaluation_protocol.json"
    )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )
