from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.svm import OneClassSVM

from .artifact_lineage import (
    sha256_file,
    validate_scaled_artifact_lineage,
)


DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]

DEFAULT_CONFIG = {
    "kernel": "rbf",
    "gamma": "scale",
    "nu": 0.05,
    "shrinking": True,
    "cache_size": 512,
}


def anomaly_score(
    model: OneClassSVM,
    X,
) -> np.ndarray:
    """
    Canonical direction used throughout the project:
    higher score = more anomalous.
    """
    decision = model.decision_function(
        X
    )

    return -np.asarray(
        decision,
        dtype=float,
    ).reshape(
        -1
    )


def calibrate_p95(
    validation_normal_scores,
) -> dict[str, float]:
    """
    Calibrate exclusively from normal validation scores.

    Prediction rule:
        anomaly iff score > threshold

    Strict greater-than is preserved to match previous project protocol.
    """
    scores = np.asarray(
        validation_normal_scores,
        dtype=float,
    ).reshape(
        -1
    )

    if len(
        scores
    ) == 0:
        raise ValueError(
            "validation_normal_scores vazio."
        )

    if not np.isfinite(
        scores
    ).all():
        raise ValueError(
            "validation_normal_scores contém valor não-finito."
        )

    threshold = float(
        np.quantile(
            scores,
            0.95,
        )
    )

    observed_fpr = float(
        (
            scores
            > threshold
        ).mean()
    )

    return {
        "quantile":
            0.95,
        "threshold":
            threshold,
        "observed_validation_fpr":
            observed_fpr,
        "prediction_rule":
            "anomaly_score > threshold",
    }


def normal_only_metrics(
    scores,
    threshold: float,
) -> dict[str, object]:
    scores = np.asarray(
        scores,
        dtype=float,
    ).reshape(
        -1
    )

    if len(
        scores
    ) == 0:
        raise ValueError(
            "scores vazio."
        )

    predicted_anomaly = (
        scores
        > threshold
    )

    false_positives = int(
        predicted_anomaly.sum()
    )

    true_negatives = int(
        len(
            scores
        )
        - false_positives
    )

    return {
        "rows":
            int(
                len(
                    scores
                )
            ),
        "false_positives":
            false_positives,
        "true_negatives":
            true_negatives,
        "false_positive_rate":
            float(
                predicted_anomaly.mean()
            ),
        "score_summary": {
            "min":
                float(
                    scores.min()
                ),
            "median":
                float(
                    np.median(
                        scores
                    )
                ),
            "mean":
                float(
                    scores.mean()
                ),
            "max":
                float(
                    scores.max()
                ),
        },
    }


def _load_scaled_split(
    scaled_root: Path,
    split: str,
):
    folder = (
        scaled_root
        / split
    )

    X_path = (
        folder
        / "X.csv.gz"
    )

    y_path = (
        folder
        / "y.csv.gz"
    )

    metadata_path = (
        folder
        / "metadata.csv.gz"
    )

    missing = [
        path.name
        for path in (
            X_path,
            y_path,
            metadata_path,
        )
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            f"{split}: arquivos ausentes: "
            + ", ".join(
                missing
            )
        )

    X = pd.read_csv(
        X_path
    )

    y = pd.read_csv(
        y_path
    )

    metadata = pd.read_csv(
        metadata_path
    )

    if list(
        X.columns
    ) != DESKTOP_FEATURES:
        raise ValueError(
            f"{split}: feature order inválida: "
            f"{list(X.columns)}"
        )

    if len(
        X
    ) == 0:
        raise ValueError(
            f"{split}: X vazio."
        )

    if not np.isfinite(
        X.to_numpy(
            dtype=float
        )
    ).all():
        raise ValueError(
            f"{split}: X contém valores não-finitos."
        )

    if len(
        X
    ) != len(
        y
    ) or len(
        X
    ) != len(
        metadata
    ):
        raise ValueError(
            f"{split}: X/y/metadata com comprimentos diferentes."
        )

    if (
        "label"
        not in y.columns
    ):
        raise ValueError(
            f"{split}: y sem coluna label."
        )

    labels = pd.to_numeric(
        y[
            "label"
        ],
        errors="raise",
    ).astype(
        int
    )

    if not (
        labels
        == 0
    ).all():
        raise ValueError(
            f"{split}: treino/calibração desktop normal recebeu label != 0."
        )

    return (
        X,
        labels,
        metadata,
    )


def check_training_gate(
    scaled_root: str | Path,
) -> dict[str, object]:
    root = Path(
        scaled_root
    )

    required = [
        root
        / split
        / "X.csv.gz"
        for split in (
            "model_train",
            "validation",
            "test_normal",
        )
    ]

    missing = [
        str(
            path
        )
        for path in required
        if not path.exists()
    ]

    if missing:
        return {
            "ready":
                False,
            "status":
                "blocked_ml_ready_data_missing",
            "reason": (
                "Scaled ML-ready desktop data is not materialized yet."
            ),
            "missing":
                missing,
        }

    lineage_gate = (
        validate_scaled_artifact_lineage(
            root
        )
    )

    if not lineage_gate[
        "ready"
    ]:
        return {
            "ready":
                False,
            "status":
                lineage_gate[
                    "status"
                ],
            "reason": (
                "Scaled desktop matrices do not match a valid frozen "
                "artifact lineage."
            ),
            "missing":
                [],
            "lineage_errors":
                lineage_gate.get(
                    "errors",
                    [],
                ),
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "missing":
            [],
        "lineage":
            lineage_gate[
                "lineage"
            ],
        "identity":
            lineage_gate[
                "identity"
            ],
        "artifact_lineage_file_sha256":
            lineage_gate[
                "artifact_lineage_file_sha256"
            ],
    }


def train_and_calibrate_desktop_ocsvm(
    scaled_root: str | Path,
    output_dir: str | Path,
    *,
    config: dict[str, object]
    | None = None,
) -> dict[str, object]:
    scaled_root = Path(
        scaled_root
    )

    output_dir = Path(
        output_dir
    )

    gate = check_training_gate(
        scaled_root
    )

    if not gate[
        "ready"
    ]:
        return {
            "schema_version":
                "desktop_ocsvm_training_v2",
            "status":
                gate[
                    "status"
                ],
            "reason":
                gate[
                    "reason"
                ],
            "model_trained":
                False,
            "threshold_calibrated":
                False,
            "test_normal_evaluated":
                False,
            "model_artifact_created":
                False,
        }

    model_config = dict(
        DEFAULT_CONFIG
    )

    if config:
        model_config.update(
            config
        )

    X_train, y_train, metadata_train = (
        _load_scaled_split(
            scaled_root,
            "model_train",
        )
    )

    X_validation, y_validation, metadata_validation = (
        _load_scaled_split(
            scaled_root,
            "validation",
        )
    )

    X_test, y_test, metadata_test = (
        _load_scaled_split(
            scaled_root,
            "test_normal",
        )
    )

    # Session-level split leakage guard.
    train_sessions = set(
        metadata_train[
            "session_id"
        ].astype(
            str
        )
    ) if "session_id" in metadata_train.columns else set()

    validation_sessions = set(
        metadata_validation[
            "session_id"
        ].astype(
            str
        )
    ) if "session_id" in metadata_validation.columns else set()

    test_sessions = set(
        metadata_test[
            "session_id"
        ].astype(
            str
        )
    ) if "session_id" in metadata_test.columns else set()

    if (
        train_sessions
        & validation_sessions
        or train_sessions
        & test_sessions
        or validation_sessions
        & test_sessions
    ):
        raise ValueError(
            "Session leakage: session_id aparece em mais de um split."
        )

    model = OneClassSVM(
        kernel=model_config[
            "kernel"
        ],
        gamma=model_config[
            "gamma"
        ],
        nu=float(
            model_config[
                "nu"
            ]
        ),
        shrinking=bool(
            model_config[
                "shrinking"
            ]
        ),
        cache_size=float(
            model_config[
                "cache_size"
            ]
        ),
    )

    started = time.perf_counter()

    model.fit(
        X_train[
            DESKTOP_FEATURES
        ]
    )

    fit_seconds = (
        time.perf_counter()
        - started
    )

    validation_scores = anomaly_score(
        model,
        X_validation[
            DESKTOP_FEATURES
        ],
    )

    calibration = calibrate_p95(
        validation_scores
    )

    threshold = calibration[
        "threshold"
    ]

    test_started = time.perf_counter()

    test_scores = anomaly_score(
        model,
        X_test[
            DESKTOP_FEATURES
        ],
    )

    test_inference_seconds = (
        time.perf_counter()
        - test_started
    )

    test_metrics = normal_only_metrics(
        test_scores,
        threshold,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    model_path = (
        output_dir
        / "one_class_svm_desktop_candidate_v1.joblib"
    )

    model_metadata_path = (
        output_dir
        / "one_class_svm_desktop_candidate_v1.json"
    )

    threshold_path = (
        output_dir
        / "threshold.json"
    )

    validation_scores_path = (
        output_dir
        / "validation_normal_scores.csv.gz"
    )

    test_scores_path = (
        output_dir
        / "test_normal_scores.csv.gz"
    )

    joblib.dump(
        model,
        model_path,
    )

    model_file_sha256 = (
        sha256_file(
            model_path
        )
    )

    pd.DataFrame({
        "anomaly_score":
            validation_scores,
        "is_anomaly":
            validation_scores
            > threshold,
    }).to_csv(
        validation_scores_path,
        index=False,
        compression="gzip",
    )

    pd.DataFrame({
        "anomaly_score":
            test_scores,
        "is_anomaly":
            test_scores
            > threshold,
    }).to_csv(
        test_scores_path,
        index=False,
        compression="gzip",
    )

    threshold_payload = {
        "schema_version":
            "desktop_threshold_v2",
        "feature_set_name":
            "desktop_candidate_v1",
        "features":
            DESKTOP_FEATURES,
        "source_split":
            "validation",
        "source_label":
            "normal_only",
        "rule":
            "P95 validation-normal anomaly score",
        "quantile":
            calibration[
                "quantile"
            ],
        "threshold":
            threshold,
        "prediction_rule":
            calibration[
                "prediction_rule"
            ],
        "observed_validation_fpr":
            calibration[
                "observed_validation_fpr"
            ],
        "attack_used_for_calibration":
            False,
        "split_digest":
            gate[
                "identity"
            ][
                "split_digest"
            ],
        "scientific_freeze_sha256":
            gate[
                "identity"
            ][
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            gate[
                "identity"
            ][
                "reference_file_sha256"
            ],
        "scaler_file_sha256":
            gate[
                "lineage"
            ][
                "scaler_file_sha256"
            ],
        "model_file_sha256":
            model_file_sha256,
        "artifact_lineage_file_sha256":
            gate[
                "artifact_lineage_file_sha256"
            ],
    }

    threshold_path.write_text(
        json.dumps(
            threshold_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    threshold_file_sha256 = (
        sha256_file(
            threshold_path
        )
    )

    model_metadata = {
        "schema_version":
            "desktop_ocsvm_model_v1",
        "algorithm":
            "OneClassSVM",
        "feature_set":
            DESKTOP_FEATURES,
        "split_digest":
            gate[
                "identity"
            ][
                "split_digest"
            ],
        "scientific_freeze_sha256":
            gate[
                "identity"
            ][
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            gate[
                "identity"
            ][
                "reference_file_sha256"
            ],
        "scaler_file_sha256":
            gate[
                "lineage"
            ][
                "scaler_file_sha256"
            ],
        "model_file_sha256":
            model_file_sha256,
        "threshold_file_sha256":
            threshold_file_sha256,
        "artifact_lineage_file_sha256":
            gate[
                "artifact_lineage_file_sha256"
            ],
        "configuration":
            model_config,
        "effective_gamma":
            float(
                model._gamma
            ),
        "fit_split":
            "model_train",
        "fit_rows":
            int(
                len(
                    X_train
                )
            ),
        "fit_sessions":
            sorted(
                train_sessions
            ),
        "validation_sessions":
            sorted(
                validation_sessions
            ),
        "test_normal_sessions":
            sorted(
                test_sessions
            ),
        "fit_seconds":
            float(
                fit_seconds
            ),
        "validation_calibration":
            threshold_payload,
        "test_normal":
            test_metrics,
        "test_inference_seconds_total":
            float(
                test_inference_seconds
            ),
        "test_inference_ms_per_row":
            float(
                (
                    test_inference_seconds
                    / len(
                        X_test
                    )
                )
                * 1000.0
            ),
        "attack_data_seen":
            False,
        "real_attack_evaluated":
            False,
        "synthetic_attack_used":
            False,
        "scientific_interpretation": (
            "At this stage only normal-data false-positive behavior is "
            "evaluated. Detection recall/F1 cannot be reported until a "
            "separate controlled real attack dataset is available."
        ),
    }

    model_metadata_path.write_text(
        json.dumps(
            model_metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "schema_version":
            "desktop_ocsvm_training_v2",
        "status":
            "trained_and_calibrated_normal_only",
        "model_trained":
            True,
        "threshold_calibrated":
            True,
        "test_normal_evaluated":
            True,
        "model_artifact_created":
            True,
        "model_path":
            str(
                model_path
            ),
        "threshold":
            threshold_payload,
        "split_digest":
            gate[
                "identity"
            ][
                "split_digest"
            ],
        "scientific_freeze_sha256":
            gate[
                "identity"
            ][
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            gate[
                "identity"
            ][
                "reference_file_sha256"
            ],
        "scaler_file_sha256":
            gate[
                "lineage"
            ][
                "scaler_file_sha256"
            ],
        "model_file_sha256":
            model_file_sha256,
        "threshold_file_sha256":
            threshold_file_sha256,
        "artifact_lineage_file_sha256":
            gate[
                "artifact_lineage_file_sha256"
            ],
        "test_normal":
            test_metrics,
        "fit_seconds":
            float(
                fit_seconds
            ),
        "test_inference_ms_per_row":
            model_metadata[
                "test_inference_ms_per_row"
            ],
        "real_attack_evaluated":
            False,
    }


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Treina/calibra o OCSVM desktop somente quando "
            "ML-ready real estiver disponível."
        )
    )

    parser.add_argument(
        "--scaled-root",
        default=(
            "data/processed/ml_ready/desktop_candidate_v1_scaled"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "ml/models/desktop_candidate_v1/ocsvm_v1"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = train_and_calibrate_desktop_ocsvm(
        args.scaled_root,
        args.output_dir,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    if result[
        "status"
    ].startswith(
        "blocked_"
    ):
        return 10

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
