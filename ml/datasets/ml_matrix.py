from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


METADATA_COLUMNS = [
    "source_dataset",
    "session_id",
    "network_identity_id",
    "network_group_id",
    "window_start_ms",
    "split",
    "split_group_type",
    "split_group_id",
    "label",
    "attack_type",
    "is_synthetic",
]

FEATURE_SETS = {
    "conservative_v1": [
        "rssi_std_db",
        "rssi_delta_db",
        "window_count",
    ],
    "complete_v1": [
        "rssi_mean_dbm",
        "rssi_std_db",
        "rssi_min_dbm",
        "rssi_max_dbm",
        "rssi_delta_db",
        "window_count",
    ],
}


def build_ml_matrix(
    df,
    feature_columns,
):
    missing = (
        set(feature_columns)
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Features ausentes: "
            + ", ".join(
                sorted(missing)
            )
        )

    X = (
        df[
            feature_columns
        ]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .copy()
    )

    if X.isna().any().any():
        columns = X.columns[
            X.isna().any()
        ].tolist()

        raise ValueError(
            "X possui NaN em: "
            + ", ".join(columns)
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
            for column in METADATA_COLUMNS
            if column in df.columns
        ]
    ].copy()

    leakage = (
        set(METADATA_COLUMNS)
        & set(X.columns)
    )

    if leakage:
        raise AssertionError(
            "Metadados em X: "
            + ", ".join(
                sorted(leakage)
            )
        )

    return X, y, metadata


def load_feature_set(
    manifest_path,
    feature_set_name,
):
    manifest = json.loads(
        Path(
            manifest_path
        ).read_text(
            encoding="utf-8"
        )
    )

    return manifest[
        "feature_sets"
    ][feature_set_name][
        "features"
    ]
