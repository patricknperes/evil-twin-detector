from __future__ import annotations

from pathlib import Path
import argparse
import json
import time

import joblib
import pandas as pd
from sklearn.ensemble import (
    IsolationForest,
)

from ml.evaluation.anomaly_protocol import (
    to_anomaly_score,
    calibrate_threshold_from_normal_validation,
    evaluate_anomaly_detection,
    evaluate_normal_only,
)


FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "channel_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
]

CONFIG = {
    "n_estimators": 300,
    "max_samples": "auto",
    "contamination": "auto",
    "max_features": 1.0,
    "bootstrap": False,
    "random_state": 20260831,
    "n_jobs": -1,
}


def load_x(
    base,
    split,
):
    return pd.read_csv(
        Path(base)
        / split
        / "X.csv.gz"
    )[FEATURES]


def train_contextual_iforest(
    scaled_base,
    output_model,
    target_fpr=0.05,
):
    X_train = load_x(
        scaled_base,
        "model_train_normal",
    )

    X_validation = load_x(
        scaled_base,
        "validation_normal",
    )

    X_test_normal = load_x(
        scaled_base,
        "test_normal",
    )

    X_test_attack = load_x(
        scaled_base,
        "test_attack_synthetic",
    )

    model = IsolationForest(
        **CONFIG
    )

    start = time.perf_counter()

    model.fit(
        X_train
    )

    fit_seconds = (
        time.perf_counter()
        - start
    )

    validation_scores = (
        to_anomaly_score(
            model.decision_function(
                X_validation
            ),
            higher_is_more_anomalous=False,
        )
    )

    calibration = (
        calibrate_threshold_from_normal_validation(
            validation_scores,
            target_false_positive_rate=target_fpr,
        )
    )

    threshold = calibration[
        "threshold"
    ]

    normal_scores = (
        to_anomaly_score(
            model.decision_function(
                X_test_normal
            ),
            higher_is_more_anomalous=False,
        )
    )

    attack_scores = (
        to_anomaly_score(
            model.decision_function(
                X_test_attack
            ),
            higher_is_more_anomalous=False,
        )
    )

    output_model = Path(
        output_model
    )

    output_model.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        output_model,
    )

    return {
        "fit_seconds":
            fit_seconds,
        "threshold":
            threshold,
        "test_normal":
            evaluate_normal_only(
                normal_scores,
                threshold,
            ),
        "test_binary_eligible":
            evaluate_anomaly_detection(
                normal_scores,
                attack_scores,
                threshold,
            ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scaled-base",
        default=(
            "data/processed/ml_ready/"
            "evil_twin_contextual_v1_scaled"
        ),
    )

    parser.add_argument(
        "--output-model",
        default=(
            "ml/models/"
            "isolation_forest_contextual/"
            "isolation_forest_contextual_full_v1.joblib"
        ),
    )

    args = parser.parse_args()

    result = (
        train_contextual_iforest(
            args.scaled_base,
            args.output_model,
        )
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
