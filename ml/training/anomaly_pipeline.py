from __future__ import annotations

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.preprocessing import StandardScaler


def load_bundle(
    base_dir,
    split,
):
    folder = (
        Path(
            base_dir
        )
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

    if not (
        len(X)
        == len(y)
        == len(metadata)
    ):
        raise ValueError(
            "X, y e metadata "
            "possuem tamanhos diferentes."
        )

    return (
        X,
        y,
        metadata,
    )


def fit_scaler_train_only(
    X_train,
):
    scaler = StandardScaler()

    scaler.fit(
        X_train
    )

    return scaler


def save_scaler(
    scaler,
    output_path,
):
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        scaler,
        output_path,
    )

    return output_path


def load_scaler(
    path,
):
    return joblib.load(
        path
    )


def transform_with_scaler(
    scaler,
    X,
):
    transformed = (
        scaler.transform(
            X
        )
    )

    return pd.DataFrame(
        transformed,
        columns=X.columns,
        index=X.index,
    )
