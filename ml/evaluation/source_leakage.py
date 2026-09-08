from __future__ import annotations

from pathlib import Path
import argparse
import json

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)


SOURCE_NEGATIVE = "mendeley_rogue_ap"
SOURCE_POSITIVE = "zenodo_v2i"

FEATURE_SETS = {
    "conservative_v1": [
        "rssi_std_db",
        "rssi_delta_db",
        "window_count",
    ],
    "conservative_v2": [
        "rssi_std_db",
        "rssi_delta_db",
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


def source_target(metadata):
    return (
        metadata[
            "source_dataset"
        ]
        .eq(
            SOURCE_POSITIVE
        )
        .astype(int)
    )


def run_diagnostic(
    base_dir,
    feature_set,
    seed=20260831,
):
    base_dir = Path(
        base_dir
    )

    source_folder = (
        "conservative_v1"
        if feature_set
        in {
            "conservative_v1",
            "conservative_v2",
        }
        else "complete_v1"
    )

    features = (
        FEATURE_SETS[
            feature_set
        ]
    )

    train_dir = (
        base_dir
        / source_folder
        / "train_balanced"
    )

    X_train = pd.read_csv(
        train_dir
        / "X.csv.gz"
    )[features]

    meta_train = pd.read_csv(
        train_dir
        / "metadata.csv.gz"
    )

    y_train = source_target(
        meta_train
    )

    model = Pipeline([
        (
            "scaler",
            StandardScaler(),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                random_state=seed,
            ),
        ),
    ])

    model.fit(
        X_train,
        y_train,
    )

    output = {
        "feature_set":
            feature_set,
        "features":
            features,
        "splits": {},
    }

    for split in [
        "validation",
        "test_normal",
    ]:
        folder = (
            base_dir
            / source_folder
            / split
        )

        X = pd.read_csv(
            folder
            / "X.csv.gz"
        )[features]

        metadata = pd.read_csv(
            folder
            / "metadata.csv.gz"
        )

        y = source_target(
            metadata
        )

        pred = model.predict(
            X
        )

        proba = (
            model.predict_proba(
                X
            )[:, 1]
        )

        output[
            "splits"
        ][split] = {
            "accuracy": float(
                accuracy_score(
                    y,
                    pred,
                )
            ),
            "balanced_accuracy":
                float(
                    balanced_accuracy_score(
                        y,
                        pred,
                    )
                ),
            "f1_v2i": float(
                f1_score(
                    y,
                    pred,
                )
            ),
            "roc_auc": float(
                roc_auc_score(
                    y,
                    proba,
                )
            ),
        }

    return output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base",
        default=(
            "data/processed/"
            "ml_ready/"
            "profile_rssi_temporal_5s"
        ),
    )

    parser.add_argument(
        "--feature-set",
        choices=list(
            FEATURE_SETS
        ),
        default=(
            "conservative_v2"
        ),
    )

    parser.add_argument(
        "--output",
    )

    args = parser.parse_args()

    result = run_diagnostic(
        args.base,
        args.feature_set,
    )

    text = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )

    if args.output:
        Path(
            args.output
        ).write_text(
            text,
            encoding="utf-8",
        )
    else:
        print(text)


if __name__ == "__main__":
    main()
