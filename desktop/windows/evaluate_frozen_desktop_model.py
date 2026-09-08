from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .artifact_lineage import (
    sha256_file,
    validate_runtime_artifact_chain,
    validate_scaled_artifact_lineage,
)
from .train_desktop_ocsvm import (
    DESKTOP_FEATURES,
    anomaly_score,
)


def _load_json(
    path: str | Path,
) -> dict[str, object]:
    return json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8"
        )
    )


def _check_required_files(
    *,
    reference_path: Path,
    scaler_path: Path,
    model_path: Path,
    threshold_path: Path,
    test_normal_dir: Path,
    attack_features_path: Path,
    attack_manifest_path: Path | None,
) -> dict[str, object]:
    required = {
        "reference":
            reference_path,
        "scaler":
            scaler_path,
        "model":
            model_path,
        "threshold":
            threshold_path,
        "test_normal_X":
            test_normal_dir
            / "X.csv.gz",
        "test_normal_y":
            test_normal_dir
            / "y.csv.gz",
        "test_normal_metadata":
            test_normal_dir
            / "metadata.csv.gz",
        "attack_features":
            attack_features_path,
    }

    if attack_manifest_path is None:
        required[
            "attack_manifest"
        ] = Path(
            "__missing_attack_manifest__"
        )
    else:
        required[
            "attack_manifest"
        ] = (
            attack_manifest_path
        )

    missing = {
        name:
            str(
                path
            )
        for name, path
        in required.items()
        if not path.exists()
    }

    if missing:
        return {
            "ready":
                False,
            "status":
                "blocked_final_evaluation_artifacts_missing",
            "missing":
                missing,
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "missing":
            {},
    }


def _load_test_normal(
    test_normal_dir: Path,
):
    X = pd.read_csv(
        test_normal_dir
        / "X.csv.gz"
    )

    y = pd.read_csv(
        test_normal_dir
        / "y.csv.gz"
    )

    metadata = pd.read_csv(
        test_normal_dir
        / "metadata.csv.gz"
    )

    if list(
        X.columns
    ) != DESKTOP_FEATURES:
        raise ValueError(
            "test_normal feature order diverge do desktop_candidate_v1."
        )

    if (
        "label"
        not in y.columns
    ):
        raise ValueError(
            "test_normal y sem coluna label."
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
            "test_normal contém label != 0."
        )

    if (
        len(
            X
        )
        != len(
            labels
        )
        or len(
            X
        )
        != len(
            metadata
        )
    ):
        raise ValueError(
            "test_normal X/y/metadata com tamanhos diferentes."
        )

    if not np.isfinite(
        X.to_numpy(
            dtype=float
        )
    ).all():
        raise ValueError(
            "test_normal X contém valor não-finito."
        )

    return (
        X,
        labels,
        metadata,
    )


def _load_attack_features(
    attack_features_path: Path,
):
    frame = pd.read_csv(
        attack_features_path
    )

    if frame.empty:
        raise ValueError(
            "attack_features_eligible vazio."
        )

    missing = [
        feature
        for feature in DESKTOP_FEATURES
        if feature
        not in frame.columns
    ]

    if missing:
        raise ValueError(
            "Attack features ausentes: "
            + ", ".join(
                missing
            )
        )

    if (
        "label"
        not in frame.columns
    ):
        raise ValueError(
            "Attack features sem label."
        )

    labels = pd.to_numeric(
        frame[
            "label"
        ],
        errors="raise",
    ).astype(
        int
    )

    if not (
        labels
        == 1
    ).all():
        raise ValueError(
            "Attack features contém label != 1."
        )

    if (
        "is_synthetic"
        in frame.columns
        and frame[
            "is_synthetic"
        ].astype(
            bool
        ).any()
    ):
        raise ValueError(
            "Avaliação final desktop não aceita ataque sintético."
        )

    X = (
        frame[
            DESKTOP_FEATURES
        ]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .copy()
    )

    if X.isna().any().any():
        raise ValueError(
            "Attack X contém NaN."
        )

    if not np.isfinite(
        X.to_numpy(
            dtype=float
        )
    ).all():
        raise ValueError(
            "Attack X contém valor não-finito."
        )

    metadata_columns = [
        "source_dataset",
        "session_id",
        "environment",
        "captured_at_utc",
        "scan_index",
        "interface_guid",
        "ssid_hash",
        "bssid_hash",
        "security_type",
        "security_strength",
        "attack_type",
        "is_synthetic",
        "context_resolution",
        "context_available",
        "feature_complete",
    ]

    metadata = frame[
        [
            column
            for column
            in metadata_columns
            if column
            in frame.columns
        ]
    ].copy()

    return (
        X,
        labels,
        metadata,
        frame,
    )


def _binary_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    y_pred = (
        scores
        > threshold
    ).astype(
        int
    )

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=[
            0,
            1,
        ],
    )

    tn, fp, fn, tp = [
        int(
            value
        )
        for value
        in cm.ravel()
    ]

    precision = float(
        precision_score(
            y_true,
            y_pred,
            zero_division=0,
        )
    )

    recall = float(
        recall_score(
            y_true,
            y_pred,
            zero_division=0,
        )
    )

    f1 = float(
        f1_score(
            y_true,
            y_pred,
            zero_division=0,
        )
    )

    accuracy = float(
        accuracy_score(
            y_true,
            y_pred,
        )
    )

    roc_auc = float(
        roc_auc_score(
            y_true,
            scores,
        )
    )

    pr_auc = float(
        average_precision_score(
            y_true,
            scores,
        )
    )

    fpr = (
        fp
        / (
            fp
            + tn
        )
        if (
            fp
            + tn
        )
        else 0.0
    )

    fnr = (
        fn
        / (
            fn
            + tp
        )
        if (
            fn
            + tp
        )
        else 0.0
    )

    return {
        "accuracy":
            accuracy,
        "precision":
            precision,
        "recall":
            recall,
        "f1":
            f1,
        "roc_auc":
            roc_auc,
        "pr_auc":
            pr_auc,
        "false_positive_rate":
            float(
                fpr
            ),
        "false_negative_rate":
            float(
                fnr
            ),
        "confusion_matrix": {
            "tn":
                tn,
            "fp":
                fp,
            "fn":
                fn,
            "tp":
                tp,
        },
    }


def _per_attack_type(
    metadata: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
) -> list[dict[str, object]]:
    if (
        "attack_type"
        not in metadata.columns
    ):
        return []

    attack_types = (
        metadata[
            "attack_type"
        ]
        .fillna(
            "unknown"
        )
        .astype(
            str
        )
    )

    rows = []

    for attack_type in sorted(
        attack_types.unique()
    ):
        mask = (
            attack_types
            == attack_type
        ).to_numpy()

        selected = scores[
            mask
        ]

        rows.append({
            "attack_type":
                attack_type,
            "rows":
                int(
                    len(
                        selected
                    )
                ),
            "detected":
                int(
                    (
                        selected
                        > threshold
                    ).sum()
                ),
            "recall":
                float(
                    (
                        selected
                        > threshold
                    ).mean()
                )
                if len(
                    selected
                )
                else 0.0,
            "score_median":
                float(
                    np.median(
                        selected
                    )
                )
                if len(
                    selected
                )
                else None,
        })

    return rows


def _per_attack_session(
    metadata: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
) -> list[dict[str, object]]:
    if (
        "session_id"
        not in metadata.columns
    ):
        return []

    sessions = (
        metadata[
            "session_id"
        ]
        .fillna(
            "unknown"
        )
        .astype(
            str
        )
    )

    rows = []

    for session_id in sorted(
        sessions.unique()
    ):
        mask = (
            sessions
            == session_id
        ).to_numpy()

        selected = scores[
            mask
        ]

        rows.append({
            "session_id":
                session_id,
            "rows":
                int(
                    len(
                        selected
                    )
                ),
            "detected":
                int(
                    (
                        selected
                        > threshold
                    ).sum()
                ),
            "recall":
                float(
                    (
                        selected
                        > threshold
                    ).mean()
                )
                if len(
                    selected
                )
                else 0.0,
        })

    return rows


def evaluate_frozen_desktop_model(
    *,
    reference_path: str | Path,
    scaler_path: str | Path,
    model_path: str | Path,
    threshold_path: str | Path,
    test_normal_dir: str | Path,
    attack_features_path: str | Path,
    output_dir: str | Path,
    attack_manifest_path: str | Path
    | None = None,
) -> dict[str, object]:
    reference_path = Path(
        reference_path
    )

    scaler_path = Path(
        scaler_path
    )

    model_path = Path(
        model_path
    )

    threshold_path = Path(
        threshold_path
    )

    test_normal_dir = Path(
        test_normal_dir
    )

    attack_features_path = Path(
        attack_features_path
    )

    attack_manifest_path = (
        Path(
            attack_manifest_path
        )
        if attack_manifest_path
        is not None
        else None
    )

    output_dir = Path(
        output_dir
    )

    gate = _check_required_files(
        reference_path=reference_path,
        scaler_path=scaler_path,
        model_path=model_path,
        threshold_path=threshold_path,
        test_normal_dir=test_normal_dir,
        attack_features_path=attack_features_path,
        attack_manifest_path=attack_manifest_path,
    )

    if not gate[
        "ready"
    ]:
        return {
            "schema_version":
                "desktop_final_evaluation_v2",
            "status":
                gate[
                    "status"
                ],
            "missing":
                gate[
                    "missing"
                ],
            "evaluation_executed":
                False,
            "artifacts_modified":
                False,
        }

    scaled_lineage = (
        validate_scaled_artifact_lineage(
            test_normal_dir.parent
        )
    )

    if not scaled_lineage[
        "ready"
    ]:
        return {
            "schema_version":
                "desktop_final_evaluation_v2",
            "status":
                "blocked_final_evaluation_artifact_lineage_mismatch",
            "evaluation_executed":
                False,
            "artifacts_modified":
                False,
            "lineage_status":
                scaled_lineage[
                    "status"
                ],
            "lineage_errors":
                scaled_lineage.get(
                    "errors",
                    [],
                ),
        }

    artifact_chain = (
        validate_runtime_artifact_chain(
            reference_path=(
                reference_path
            ),
            scaler_path=(
                scaler_path
            ),
            model_path=(
                model_path
            ),
            threshold_path=(
                threshold_path
            ),
        )
    )

    if not artifact_chain[
        "ready"
    ]:
        return {
            "schema_version":
                "desktop_final_evaluation_v2",
            "status":
                "blocked_final_evaluation_artifact_chain_mismatch",
            "evaluation_executed":
                False,
            "artifacts_modified":
                False,
            "artifact_chain_status":
                artifact_chain[
                    "status"
                ],
            "artifact_chain_errors":
                artifact_chain.get(
                    "errors",
                    [],
                ),
        }

    identity_mismatch = [
        field
        for field in (
            "split_digest",
            "scientific_freeze_sha256",
            "reference_file_sha256",
        )
        if (
            scaled_lineage[
                "identity"
            ][
                field
            ]
            != artifact_chain[
                "identity"
            ][
                field
            ]
        )
    ]

    lineage_hash_matches = (
        scaled_lineage[
            "artifact_lineage_file_sha256"
        ]
        == artifact_chain[
            "artifact_lineage_file_sha256"
        ]
    )

    scaler_hash_matches = (
        scaled_lineage[
            "lineage"
        ][
            "scaler_file_sha256"
        ]
        == artifact_chain[
            "actual_hashes"
        ][
            "scaler"
        ]
    )

    if (
        identity_mismatch
        or not lineage_hash_matches
        or not scaler_hash_matches
    ):
        errors = [
            *[
                f"scientific_identity_mismatch:{field}"
                for field in identity_mismatch
            ],
        ]

        if not lineage_hash_matches:
            errors.append(
                "artifact_lineage_file_sha256_mismatch"
            )

        if not scaler_hash_matches:
            errors.append(
                "scaled_data_scaler_sha256_mismatch"
            )

        return {
            "schema_version":
                "desktop_final_evaluation_v2",
            "status":
                "blocked_final_evaluation_mixed_freeze_artifacts",
            "evaluation_executed":
                False,
            "artifacts_modified":
                False,
            "artifact_chain_errors":
                errors,
        }

    attack_manifest = _load_json(
        attack_manifest_path
    )

    attack_lineage_errors = []

    for field in (
        "split_digest",
        "scientific_freeze_sha256",
        "reference_file_sha256",
    ):
        if (
            attack_manifest.get(
                field
            )
            != artifact_chain[
                "identity"
            ][
                field
            ]
        ):
            attack_lineage_errors.append(
                f"attack_manifest_identity_mismatch:{field}"
            )

    if attack_lineage_errors:
        return {
            "schema_version":
                "desktop_final_evaluation_v2",
            "status":
                "blocked_final_evaluation_attack_reference_mismatch",
            "evaluation_executed":
                False,
            "artifacts_modified":
                False,
            "artifact_chain_errors":
                attack_lineage_errors,
        }

    frozen_hashes_before = dict(
        artifact_chain[
            "actual_hashes"
        ]
    )

    scaler = joblib.load(
        scaler_path
    )

    model = joblib.load(
        model_path
    )

    threshold_payload = _load_json(
        threshold_path
    )

    threshold = float(
        threshold_payload[
            "threshold"
        ]
    )

    if bool(
        threshold_payload.get(
            "attack_used_for_calibration",
            False,
        )
    ):
        raise ValueError(
            "Threshold inválido: attack_used_for_calibration=true."
        )

    X_normal, y_normal, metadata_normal = (
        _load_test_normal(
            test_normal_dir
        )
    )

    (
        X_attack_raw,
        y_attack,
        metadata_attack,
        attack_frame,
    ) = _load_attack_features(
        attack_features_path
    )

    # Attack raw contextual features are transformed using the already
    # fitted scaler. fit/partial_fit is never called here.
    attack_scaled = pd.DataFrame(
        scaler.transform(
            X_attack_raw[
                DESKTOP_FEATURES
            ]
        ),
        columns=DESKTOP_FEATURES,
    )

    normal_started = (
        time.perf_counter()
    )

    normal_scores = anomaly_score(
        model,
        X_normal[
            DESKTOP_FEATURES
        ],
    )

    normal_seconds = (
        time.perf_counter()
        - normal_started
    )

    attack_started = (
        time.perf_counter()
    )

    attack_scores = anomaly_score(
        model,
        attack_scaled[
            DESKTOP_FEATURES
        ],
    )

    attack_seconds = (
        time.perf_counter()
        - attack_started
    )

    y_true = np.concatenate([
        y_normal.to_numpy(
            dtype=int
        ),
        y_attack.to_numpy(
            dtype=int
        ),
    ])

    all_scores = np.concatenate([
        normal_scores,
        attack_scores,
    ])

    metrics = _binary_metrics(
        y_true,
        all_scores,
        threshold,
    )

    normal_fpr = float(
        (
            normal_scores
            > threshold
        ).mean()
    )

    attack_recall = float(
        (
            attack_scores
            > threshold
        ).mean()
    )

    per_type = _per_attack_type(
        metadata_attack,
        attack_scores,
        threshold,
    )

    per_session = _per_attack_session(
        metadata_attack,
        attack_scores,
        threshold,
    )

    coverage = None

    if (
        attack_manifest
        is not None
    ):
        coverage = {
            "rows":
                int(
                    attack_manifest.get(
                        "rows",
                        len(
                            attack_frame
                        ),
                    )
                ),
            "eligible":
                int(
                    attack_manifest.get(
                        "eligible",
                        len(
                            attack_frame
                        ),
                    )
                ),
            "eligible_rate":
                float(
                    attack_manifest.get(
                        "eligible_rate",
                        1.0,
                    )
                ),
        }

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    pd.DataFrame({
        "label":
            y_normal.to_numpy(
                dtype=int
            ),
        "anomaly_score":
            normal_scores,
        "prediction":
            (
                normal_scores
                > threshold
            ).astype(
                int
            ),
    }).to_csv(
        output_dir
        / "test_normal_scores.csv.gz",
        index=False,
        compression="gzip",
    )

    attack_output = (
        metadata_attack.reset_index(
            drop=True
        )
        .copy()
    )

    attack_output[
        "label"
    ] = y_attack.to_numpy(
        dtype=int
    )

    attack_output[
        "anomaly_score"
    ] = attack_scores

    attack_output[
        "prediction"
    ] = (
        attack_scores
        > threshold
    ).astype(
        int
    )

    attack_output.to_csv(
        output_dir
        / "attack_scores.csv.gz",
        index=False,
        compression="gzip",
    )

    pd.DataFrame(
        per_type
    ).to_csv(
        output_dir
        / "recall_by_attack_type.csv",
        index=False,
    )

    pd.DataFrame(
        per_session
    ).to_csv(
        output_dir
        / "recall_by_attack_session.csv",
        index=False,
    )

    result = {
        "schema_version":
            "desktop_final_evaluation_v2",
        "status":
            "executed_fixed_artifacts",
        "evaluation_executed":
            True,
        "artifacts_modified":
            False,
        "frozen_artifacts": {
            "reference":
                str(
                    reference_path
                ),
            "scaler":
                str(
                    scaler_path
                ),
            "model":
                str(
                    model_path
                ),
            "threshold":
                str(
                    threshold_path
                ),
        },
        "scientific_identity":
            artifact_chain[
                "identity"
            ],
        "artifact_hashes":
            frozen_hashes_before,
        "artifact_lineage_file_sha256":
            artifact_chain[
                "artifact_lineage_file_sha256"
            ],
        "features":
            DESKTOP_FEATURES,
        "threshold":
            threshold,
        "normal_rows":
            int(
                len(
                    normal_scores
                )
            ),
        "attack_rows_eligible":
            int(
                len(
                    attack_scores
                )
            ),
        "attack_coverage":
            coverage,
        "attack_reference_identity": {
            "split_digest":
                attack_manifest[
                    "split_digest"
                ],
            "scientific_freeze_sha256":
                attack_manifest[
                    "scientific_freeze_sha256"
                ],
            "reference_file_sha256":
                attack_manifest[
                    "reference_file_sha256"
                ],
        },
        "metrics":
            metrics,
        "test_normal_fpr":
            normal_fpr,
        "attack_recall":
            attack_recall,
        "per_attack_type":
            per_type,
        "per_attack_session":
            per_session,
        "timing": {
            "normal_inference_seconds_total":
                float(
                    normal_seconds
                ),
            "normal_inference_ms_per_row":
                float(
                    normal_seconds
                    / len(
                        normal_scores
                    )
                    * 1000.0
                ),
            "attack_inference_seconds_total":
                float(
                    attack_seconds
                ),
            "attack_inference_ms_per_row":
                float(
                    attack_seconds
                    / len(
                        attack_scores
                    )
                    * 1000.0
                ),
            "scope":
                "model inference only",
        },
        "scientific_guards": [
            "Scaler is loaded frozen; no fit/partial_fit occurs.",
            "Model is loaded frozen; no fit occurs.",
            "Threshold is loaded frozen; no recalibration occurs.",
            "Attack data is real/control label=1 and synthetic data is rejected.",
            "Normal test remains independent from validation calibration.",
            "Reference/scaler/model/threshold must share one scientific freeze identity.",
            "Scaled test_normal must match the same artifact_lineage.json used for training.",
        ],
    }

    frozen_hashes_after = {
        "reference":
            sha256_file(
                reference_path
            ),
        "scaler":
            sha256_file(
                scaler_path
            ),
        "model":
            sha256_file(
                model_path
            ),
        "threshold":
            sha256_file(
                threshold_path
            ),
    }

    if (
        frozen_hashes_after
        != frozen_hashes_before
    ):
        raise RuntimeError(
            "Frozen scientific artifacts changed during final evaluation."
        )

    result[
        "artifact_hashes_after"
    ] = frozen_hashes_after

    (
        output_dir
        / "final_evaluation.json"
    ).write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return result


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Avalia o desktop_candidate_v1 usando somente artefatos "
            "já congelados."
        )
    )

    parser.add_argument(
        "--reference",
        default=(
            "data/processed/desktop_candidate_v1/"
            "desktop_normal_reference.json"
        ),
    )

    parser.add_argument(
        "--scaler",
        default=(
            "ml/models/preprocessing/"
            "desktop_candidate_v1_standard_scaler.joblib"
        ),
    )

    parser.add_argument(
        "--model",
        default=(
            "ml/models/desktop_candidate_v1/ocsvm_v1/"
            "one_class_svm_desktop_candidate_v1.joblib"
        ),
    )

    parser.add_argument(
        "--threshold",
        default=(
            "ml/models/desktop_candidate_v1/ocsvm_v1/"
            "threshold.json"
        ),
    )

    parser.add_argument(
        "--test-normal-dir",
        default=(
            "data/processed/ml_ready/"
            "desktop_candidate_v1_scaled/test_normal"
        ),
    )

    parser.add_argument(
        "--attack-features",
        default=(
            "data/processed/desktop_candidate_v1_attack/"
            "attack_features_eligible.csv.gz"
        ),
    )

    parser.add_argument(
        "--attack-manifest",
        default=(
            "data/processed/desktop_candidate_v1_attack/"
            "manifest.json"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "reports/desktop/final_evaluation_v1"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = evaluate_frozen_desktop_model(
        reference_path=args.reference,
        scaler_path=args.scaler,
        model_path=args.model,
        threshold_path=args.threshold,
        test_normal_dir=args.test_normal_dir,
        attack_features_path=args.attack_features,
        attack_manifest_path=args.attack_manifest,
        output_dir=args.output_dir,
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
        return 13

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
