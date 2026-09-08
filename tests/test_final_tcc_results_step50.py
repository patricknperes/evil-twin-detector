from __future__ import annotations

import json

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

from desktop.windows.generate_final_tcc_results import (
    AGGREGATE_OUTPUT_FILES,
    generate_final_tcc_results,
    inspect_final_evaluation_for_results,
    inspect_generated_final_results,
    sha256_file,
)


def _metrics(
    y_true,
    scores,
    threshold,
):
    predictions = (
        scores
        > threshold
    ).astype(
        int
    )

    matrix = confusion_matrix(
        y_true,
        predictions,
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
        in matrix.ravel()
    ]

    return {
        "accuracy":
            float(
                accuracy_score(
                    y_true,
                    predictions,
                )
            ),
        "precision":
            float(
                precision_score(
                    y_true,
                    predictions,
                    zero_division=0,
                )
            ),
        "recall":
            float(
                recall_score(
                    y_true,
                    predictions,
                    zero_division=0,
                )
            ),
        "f1":
            float(
                f1_score(
                    y_true,
                    predictions,
                    zero_division=0,
                )
            ),
        "roc_auc":
            float(
                roc_auc_score(
                    y_true,
                    scores,
                )
            ),
        "pr_auc":
            float(
                average_precision_score(
                    y_true,
                    scores,
                )
            ),
        "false_positive_rate":
            float(
                fp
                / (
                    fp
                    + tn
                )
            ),
        "false_negative_rate":
            float(
                fn
                / (
                    fn
                    + tp
                )
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


def _prepare_evaluation(
    tmp_path,
):
    project = (
        tmp_path
        / "project"
    )

    evaluation = (
        project
        / "reports"
        / "desktop"
        / "final_evaluation_v1"
    )

    evaluation.mkdir(
        parents=True
    )

    artifacts = {}

    for name in (
        "reference",
        "scaler",
        "model",
        "threshold",
    ):
        path = (
            project
            / "artifacts"
            / f"{name}.bin"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            (
                "step50-"
                + name
            ).encode(
                "utf-8"
            )
        )

        artifacts[
            name
        ] = path

    normal_scores = np.array([
        0.10,
        0.20,
        0.70,
        0.30,
    ])

    attack_scores = np.array([
        0.90,
        0.80,
        0.40,
        0.95,
    ])

    threshold = (
        0.60
    )

    normal = pd.DataFrame({
        "label": [
            0
        ] * 4,
        "anomaly_score":
            normal_scores,
        "prediction":
            (
                normal_scores
                > threshold
            ).astype(
                int
            ),
    })

    attack = pd.DataFrame({
        "source_dataset": [
            "own_windows_attack"
        ] * 4,
        "session_id": [
            "attack-a",
            "attack-a",
            "attack-b",
            "attack-b",
        ],
        "attack_type": [
            "controlled_evil_twin"
        ] * 4,
        "is_synthetic": [
            False
        ] * 4,
        "label": [
            1
        ] * 4,
        "anomaly_score":
            attack_scores,
        "prediction":
            (
                attack_scores
                > threshold
            ).astype(
                int
            ),
    })

    normal.to_csv(
        evaluation
        / "test_normal_scores.csv.gz",
        index=False,
        compression="gzip",
    )

    attack.to_csv(
        evaluation
        / "attack_scores.csv.gz",
        index=False,
        compression="gzip",
    )

    type_rows = []

    for attack_type, group in (
        attack.groupby(
            "attack_type"
        )
    ):
        values = group[
            "anomaly_score"
        ].to_numpy(
            dtype=float
        )

        detected = (
            values
            > threshold
        )

        type_rows.append({
            "attack_type":
                attack_type,
            "rows":
                len(
                    group
                ),
            "detected":
                int(
                    detected.sum()
                ),
            "recall":
                float(
                    detected.mean()
                ),
            "score_median":
                float(
                    np.median(
                        values
                    )
                ),
        })

    pd.DataFrame(
        type_rows
    ).to_csv(
        evaluation
        / "recall_by_attack_type.csv",
        index=False,
    )

    session_rows = []

    for session_id, group in (
        attack.groupby(
            "session_id"
        )
    ):
        values = group[
            "anomaly_score"
        ].to_numpy(
            dtype=float
        )

        detected = (
            values
            > threshold
        )

        session_rows.append({
            "session_id":
                session_id,
            "rows":
                len(
                    group
                ),
            "detected":
                int(
                    detected.sum()
                ),
            "recall":
                float(
                    detected.mean()
                ),
        })

    pd.DataFrame(
        session_rows
    ).to_csv(
        evaluation
        / "recall_by_attack_session.csv",
        index=False,
    )

    y_true = np.concatenate([
        np.zeros(
            len(
                normal_scores
            ),
            dtype=int,
        ),
        np.ones(
            len(
                attack_scores
            ),
            dtype=int,
        ),
    ])

    scores = np.concatenate([
        normal_scores,
        attack_scores,
    ])

    metrics = (
        _metrics(
            y_true,
            scores,
            threshold,
        )
    )

    artifact_hashes = {
        name:
            sha256_file(
                path
            )
        for name, path
        in artifacts.items()
    }

    payload = {
        "schema_version":
            "desktop_final_evaluation_v2",
        "status":
            "executed_fixed_artifacts",
        "evaluation_executed":
            True,
        "artifacts_modified":
            False,
        "frozen_artifacts": {
            name:
                str(
                    path
                )
            for name, path
            in artifacts.items()
        },
        "scientific_identity": {
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
            "reference_file_sha256":
                artifact_hashes[
                    "reference"
                ],
        },
        "artifact_hashes":
            artifact_hashes,
        "artifact_hashes_after":
            artifact_hashes,
        "features": [
            "ssid_bssid_count",
            "bssid_changed",
            "security_changed",
            "security_strength_delta",
        ],
        "threshold":
            threshold,
        "normal_rows":
            len(
                normal
            ),
        "attack_rows_eligible":
            len(
                attack
            ),
        "attack_coverage": {
            "rows":
                5,
            "eligible":
                4,
            "eligible_rate":
                0.8,
        },
        "metrics":
            metrics,
        "test_normal_fpr":
            float(
                (
                    normal_scores
                    > threshold
                ).mean()
            ),
        "attack_recall":
            float(
                (
                    attack_scores
                    > threshold
                ).mean()
            ),
        "timing": {
            "normal_inference_seconds_total":
                0.004,
            "normal_inference_ms_per_row":
                1.0,
            "attack_inference_seconds_total":
                0.008,
            "attack_inference_ms_per_row":
                2.0,
            "scope":
                "model inference only",
        },
    }

    (
        evaluation
        / "final_evaluation.json"
    ).write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Hypothetical stress-test fixture
    # ------------------------------------------------------------
    hypothetical_dir = (
        project
        / "data"
        / "processed"
        / "desktop_hypothetical_test_normal_v1_ocsvm"
    )

    hypothetical_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    hypothetical_predictions = pd.DataFrame({
        "scenario": [
            "hypothetical_control",
            "hypothetical_control",
            "hypothetical_control",
            "hypothetical_control",
            "hypothetical_new_bssid",
            "hypothetical_new_bssid",
            "hypothetical_new_bssid",
            "hypothetical_new_bssid",
        ],
        "anomaly_score": [
            0.10,
            0.20,
            0.30,
            0.40,
            0.90,
            0.80,
            0.95,
            0.85,
        ],
        "prediction": [
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
        ],
    })

    hypothetical_predictions_path = (
        hypothetical_dir
        / "hypothetical_ocsvm_predictions.csv.gz"
    )

    hypothetical_predictions.to_csv(
        hypothetical_predictions_path,
        index=False,
        compression="gzip",
    )

    hypothetical_payload = {
        "schema_version":
            "desktop_hypothetical_ocsvm_evaluation_v1",
        "status":
            "hypothetical_ocsvm_evaluation_ready",
        "created":
            True,
        "evaluation_type":
            "hypothetical_stress_test",
        "ground_truth_available":
            False,
        "independent_source_split":
            "test_normal",
        "source_session_ids": [
            "test-normal-a",
            "test-normal-b",
        ],
        "features": [
            "ssid_bssid_count",
            "bssid_changed",
            "security_changed",
            "security_strength_delta",
        ],
        "anomaly_score_definition":
            "-OCSVM.decision_function(X_scaled)",
        "prediction_rule":
            "anomaly_score > threshold",
        "threshold":
            threshold,
        "total_predictions":
            8,
        "total_anomaly_flags":
            4,
        "overall_threshold_exceedance_rate":
            0.5,
        "control_threshold_exceedance_rate":
            0.0,
        "scenario_results": {
            "hypothetical_control": {
                "rows":
                    4,
                "anomaly_count":
                    0,
                "normal_count":
                    4,
                "threshold_exceedance_rate":
                    0.0,
                "score_min":
                    0.10,
                "score_mean":
                    0.25,
                "score_median":
                    0.25,
                "score_p95":
                    0.40,
                "score_max":
                    0.40,
                "input_rows":
                    4,
                "eligible_rows":
                    4,
                "not_evaluable_rows":
                    0,
                "source_sessions": [
                    "test-normal-a",
                    "test-normal-b",
                ],
                "heuristic_expected_suspicion_levels": [
                    "normal_like",
                ],
                "interpretation":
                    "Control copy of independent test_normal baseline observations.",
            },
            "hypothetical_new_bssid": {
                "rows":
                    4,
                "anomaly_count":
                    4,
                "normal_count":
                    0,
                "threshold_exceedance_rate":
                    1.0,
                "score_min":
                    0.80,
                "score_mean":
                    0.875,
                "score_median":
                    0.875,
                "score_p95":
                    0.95,
                "score_max":
                    0.95,
                "input_rows":
                    4,
                "eligible_rows":
                    4,
                "not_evaluable_rows":
                    0,
                "source_sessions": [
                    "test-normal-a",
                    "test-normal-b",
                ],
                "heuristic_expected_suspicion_levels": [
                    "medium_suspicion",
                ],
                "threshold_exceedance_rate_delta_vs_control":
                    1.0,
            },
        },
        "split_digest":
            "a" * 64,
        "scientific_freeze_sha256":
            "b" * 64,
        "artifacts": {
            "reference":
                str(
                    artifacts[
                        "reference"
                    ]
                ),
            "reference_sha256":
                artifact_hashes[
                    "reference"
                ],
            "scaler":
                str(
                    artifacts[
                        "scaler"
                    ]
                ),
            "scaler_sha256":
                artifact_hashes[
                    "scaler"
                ],
            "model":
                str(
                    artifacts[
                        "model"
                    ]
                ),
            "model_sha256":
                artifact_hashes[
                    "model"
                ],
            "threshold":
                str(
                    artifacts[
                        "threshold"
                    ]
                ),
            "threshold_sha256":
                artifact_hashes[
                    "threshold"
                ],
        },
        "predictions_file":
            str(
                hypothetical_predictions_path
            ),
        "predictions_sha256":
            sha256_file(
                hypothetical_predictions_path
            ),
    }

    (
        hypothetical_dir
        / "evaluation.json"
    ).write_text(
        json.dumps(
            hypothetical_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        project,
        evaluation,
        artifacts,
    )


def test_missing_real_final_evaluation_is_blocked(
    tmp_path,
):
    result = (
        inspect_final_evaluation_for_results(
            project_root=(
                tmp_path
            ),
            evaluation_dir=(
                "reports/desktop/final_evaluation_v1"
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_final_evaluation_not_available"
    )

    assert (
        result[
            "results_generated"
        ]
        is False
    )


def test_generates_aggregate_final_results_from_fixed_evaluation(
    tmp_path,
):
    (
        project,
        evaluation,
        _,
    ) = _prepare_evaluation(
        tmp_path
    )

    output = (
        project
        / "reports"
        / "tcc"
        / "final_results_v1"
    )

    result = (
        generate_final_tcc_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
            output_dir=(
                output
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "generated_scientifically_separated_final_results"
    )

    assert (
        result[
            "results_generated"
        ]
        is True
    )

    for filename in (
        AGGREGATE_OUTPUT_FILES
    ):
        assert (
            output
            / filename
        ).exists()

    assert (
        output
        / "reproducibility_manifest.json"
    ).exists()

    assert not (
        output
        / "attack_scores.csv.gz"
    ).exists()

    assert not (
        output
        / "test_normal_scores.csv.gz"
    ).exists()

    integrity = (
        inspect_generated_final_results(
            project_root=(
                project
            ),
            output_dir=(
                output
            ),
        )
    )

    assert (
        integrity[
            "ready"
        ]
        is True
    )


def test_score_tampering_after_evaluation_is_blocked(
    tmp_path,
):
    (
        project,
        evaluation,
        _,
    ) = _prepare_evaluation(
        tmp_path
    )

    attack_path = (
        evaluation
        / "attack_scores.csv.gz"
    )

    attack = pd.read_csv(
        attack_path
    )

    attack.loc[
        0,
        "anomaly_score"
    ] = (
        0.0
    )

    attack.to_csv(
        attack_path,
        index=False,
        compression="gzip",
    )

    result = (
        inspect_final_evaluation_for_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_exploratory_score_prediction_threshold_mismatch"
    )


def test_frozen_artifact_mutation_is_blocked(
    tmp_path,
):
    (
        project,
        evaluation,
        artifacts,
    ) = _prepare_evaluation(
        tmp_path
    )

    artifacts[
        "model"
    ].write_bytes(
        b"mutated"
    )

    result = (
        inspect_final_evaluation_for_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_frozen_artifact_source_mismatch"
    )


def test_synthetic_attack_rows_are_rejected(
    tmp_path,
):
    (
        project,
        evaluation,
        _,
    ) = _prepare_evaluation(
        tmp_path
    )

    attack_path = (
        evaluation
        / "attack_scores.csv.gz"
    )

    attack = pd.read_csv(
        attack_path
    )

    attack[
        "is_synthetic"
    ] = True

    attack.to_csv(
        attack_path,
        index=False,
        compression="gzip",
    )

    result = (
        inspect_final_evaluation_for_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_synthetic_rows_in_exploratory_session"
    )


def test_generated_bundle_is_create_only(
    tmp_path,
):
    (
        project,
        evaluation,
        _,
    ) = _prepare_evaluation(
        tmp_path
    )

    output = (
        project
        / "reports"
        / "tcc"
        / "final_results_v1"
    )

    first = (
        generate_final_tcc_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
            output_dir=(
                output
            ),
        )
    )

    assert (
        first[
            "results_generated"
        ]
        is True
    )

    second = (
        generate_final_tcc_results(
            project_root=(
                project
            ),
            evaluation_dir=(
                evaluation
            ),
            output_dir=(
                output
            ),
        )
    )

    assert (
        second[
            "status"
        ]
        == "blocked_results_output_already_exists"
    )
