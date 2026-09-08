from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn


SCHEMA_VERSION = "tcc_final_results_bundle_v2"

SOURCE_EVALUATION_SCHEMA = "desktop_final_evaluation_v2"

HYPOTHETICAL_EVALUATION_SCHEMA = (
    "desktop_hypothetical_ocsvm_evaluation_v1"
)

HYPOTHETICAL_EVALUATION_STATUS = (
    "hypothetical_ocsvm_evaluation_ready"
)

DEFAULT_HYPOTHETICAL_EVALUATION = (
    "data/processed/"
    "desktop_hypothetical_test_normal_v1_ocsvm/"
    "evaluation.json"
)

REQUIRED_SOURCE_FILES = (
    "final_evaluation.json",
    "test_normal_scores.csv.gz",
    "attack_scores.csv.gz",
)

AGGREGATE_OUTPUT_FILES = (
    "metrics_summary.csv",
    "score_distribution.csv",
    "exploratory_session_summary.csv",
    "hypothetical_scenarios.csv",
    "timing_summary.csv",
    "score_distribution.png",
    "hypothetical_threshold_exceedance.png",
    "final_results_summary.md",
)

FLOAT_TOLERANCE = 1e-10


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _load_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )


def _relative_or_name(
    project_root: Path,
    path: Path,
) -> str:
    try:
        return str(
            path.resolve().relative_to(
                project_root.resolve()
            )
        )
    except ValueError:
        return path.name


def _resolve_artifact_path(
    project_root: Path,
    raw: str,
) -> Path:
    candidate = Path(raw)

    if candidate.is_absolute():
        return candidate

    return project_root / candidate


def _float_equal(
    left: Any,
    right: Any,
) -> bool:
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return False

    return bool(
        np.isclose(
            left_value,
            right_value,
            rtol=0.0,
            atol=FLOAT_TOLERANCE,
        )
    )


def _series_has_true(
    series: pd.Series,
) -> bool:
    if pd.api.types.is_bool_dtype(series):
        return bool(
            series.fillna(False).any()
        )

    normalized = (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return bool(
        normalized.isin(
            {
                "1",
                "true",
                "yes",
                "sim",
            }
        ).any()
    )


def inspect_final_evaluation_for_results(
    *,
    project_root: str | Path,
    evaluation_dir: str | Path,
    hypothetical_evaluation_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Valida as fontes do bundle final sem tratar a antiga
    sessão em contexto de ataque como ground truth de Evil Twin.
    """

    root = Path(
        project_root
    ).resolve()

    evaluation_dir = Path(
        evaluation_dir
    )

    if not evaluation_dir.is_absolute():
        evaluation_dir = (
            root
            / evaluation_dir
        )

    missing = {
        filename: str(
            evaluation_dir
            / filename
        )
        for filename
        in REQUIRED_SOURCE_FILES
        if not (
            evaluation_dir
            / filename
        ).exists()
    }

    if missing:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_final_evaluation_not_available",
            "ready":
                False,
            "results_generated":
                False,
            "missing":
                missing,
            "evaluation_dir":
                _relative_or_name(
                    root,
                    evaluation_dir,
                ),
        }

    evaluation_path = (
        evaluation_dir
        / "final_evaluation.json"
    )

    try:
        evaluation = _load_json(
            evaluation_path
        )
    except Exception as exc:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_final_evaluation_json_invalid",
            "ready":
                False,
            "results_generated":
                False,
            "reason":
                type(exc).__name__,
        }

    if (
        evaluation.get(
            "schema_version"
        )
        != SOURCE_EVALUATION_SCHEMA
        or evaluation.get(
            "status"
        )
        != "executed_fixed_artifacts"
        or evaluation.get(
            "evaluation_executed"
        )
        is not True
        or evaluation.get(
            "artifacts_modified"
        )
        is not False
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_final_evaluation_not_executed_fixed_artifacts",
            "ready":
                False,
            "results_generated":
                False,
        }

    artifact_hashes = (
        evaluation.get(
            "artifact_hashes"
        )
        or {}
    )

    artifact_hashes_after = (
        evaluation.get(
            "artifact_hashes_after"
        )
        or {}
    )

    if (
        artifact_hashes
        != artifact_hashes_after
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_frozen_artifact_hashes_changed_during_evaluation",
            "ready":
                False,
            "results_generated":
                False,
        }

    frozen_artifacts = (
        evaluation.get(
            "frozen_artifacts"
        )
        or {}
    )

    artifact_errors: list[str] = []

    for name in (
        "reference",
        "scaler",
        "model",
        "threshold",
    ):
        raw_path = (
            frozen_artifacts.get(
                name
            )
        )

        expected_hash = (
            artifact_hashes.get(
                name
            )
        )

        if (
            not isinstance(
                raw_path,
                str,
            )
            or not isinstance(
                expected_hash,
                str,
            )
        ):
            artifact_errors.append(
                f"{name}:metadata_missing"
            )
            continue

        artifact_path = (
            _resolve_artifact_path(
                root,
                raw_path,
            )
        )

        if not artifact_path.exists():
            artifact_errors.append(
                f"{name}:file_missing"
            )
            continue

        if (
            sha256_file(
                artifact_path
            )
            != expected_hash
        ):
            artifact_errors.append(
                f"{name}:sha256_mismatch"
            )

    if artifact_errors:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_frozen_artifact_source_mismatch",
            "ready":
                False,
            "results_generated":
                False,
            "artifact_errors":
                artifact_errors,
        }

    normal_path = (
        evaluation_dir
        / "test_normal_scores.csv.gz"
    )

    exploratory_path = (
        evaluation_dir
        / "attack_scores.csv.gz"
    )

    normal = pd.read_csv(
        normal_path
    )

    exploratory = pd.read_csv(
        exploratory_path
    )

    if normal.empty:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_normal_score_file_empty",
            "ready":
                False,
            "results_generated":
                False,
        }

    if exploratory.empty:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_exploratory_score_file_empty",
            "ready":
                False,
            "results_generated":
                False,
        }

    required_columns = {
        "anomaly_score",
        "prediction",
    }

    for name, frame in (
        (
            "test_normal_scores",
            normal,
        ),
        (
            "exploratory_attack_context_scores",
            exploratory,
        ),
    ):
        if not required_columns.issubset(
            frame.columns
        ):
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_score_file_schema_invalid",
                "ready":
                    False,
                "results_generated":
                    False,
                "score_file":
                    name,
                "missing_columns":
                    sorted(
                        required_columns
                        - set(
                            frame.columns
                        )
                    ),
            }

    if (
        "label"
        in normal.columns
    ):
        normal_labels = (
            pd.to_numeric(
                normal[
                    "label"
                ],
                errors="raise",
            )
            .to_numpy(
                dtype=int
            )
        )

        if not (
            normal_labels
            == 0
        ).all():
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_normal_test_labels_invalid",
                "ready":
                    False,
                "results_generated":
                    False,
            }

    if (
        "is_synthetic"
        in exploratory.columns
        and _series_has_true(
            exploratory[
                "is_synthetic"
            ]
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_synthetic_rows_in_exploratory_session",
            "ready":
                False,
            "results_generated":
                False,
        }

    normal_scores = (
        pd.to_numeric(
            normal[
                "anomaly_score"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=float
        )
    )

    exploratory_scores = (
        pd.to_numeric(
            exploratory[
                "anomaly_score"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=float
        )
    )

    if (
        not np.isfinite(
            normal_scores
        ).all()
        or not np.isfinite(
            exploratory_scores
        ).all()
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_non_finite_scores",
            "ready":
                False,
            "results_generated":
                False,
        }

    threshold = float(
        evaluation[
            "threshold"
        ]
    )

    if not np.isfinite(
        threshold
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_non_finite_threshold",
            "ready":
                False,
            "results_generated":
                False,
        }

    normal_predictions = (
        pd.to_numeric(
            normal[
                "prediction"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=int
        )
    )

    exploratory_predictions = (
        pd.to_numeric(
            exploratory[
                "prediction"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=int
        )
    )

    if not np.array_equal(
        normal_predictions,
        (
            normal_scores
            > threshold
        ).astype(
            int
        ),
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_normal_score_prediction_threshold_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if not np.array_equal(
        exploratory_predictions,
        (
            exploratory_scores
            > threshold
        ).astype(
            int
        ),
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_exploratory_score_prediction_threshold_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    normal_fpr = float(
        (
            normal_scores
            > threshold
        ).mean()
    )

    exploratory_threshold_exceedance_rate = (
        float(
            (
                exploratory_scores
                > threshold
            ).mean()
        )
    )

    mismatches: list[str] = []

    if not _float_equal(
        normal_fpr,
        evaluation.get(
            "test_normal_fpr"
        ),
    ):
        mismatches.append(
            "test_normal_fpr"
        )

    if (
        int(
            evaluation.get(
                "normal_rows",
                -1,
            )
        )
        != len(
            normal
        )
    ):
        mismatches.append(
            "normal_rows"
        )

    if (
        int(
            evaluation.get(
                "attack_rows_eligible",
                -1,
            )
        )
        != len(
            exploratory
        )
    ):
        mismatches.append(
            "exploratory_rows"
        )

    if mismatches:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_final_evaluation_source_mismatch",
            "ready":
                False,
            "results_generated":
                False,
            "mismatches":
                sorted(
                    set(
                        mismatches
                    )
                ),
        }

    if (
        hypothetical_evaluation_path
        is None
    ):
        hypothetical_path = (
            root
            / DEFAULT_HYPOTHETICAL_EVALUATION
        )
    else:
        hypothetical_path = Path(
            hypothetical_evaluation_path
        )

        if not hypothetical_path.is_absolute():
            hypothetical_path = (
                root
                / hypothetical_path
            )

    if not hypothetical_path.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_evaluation_not_available",
            "ready":
                False,
            "results_generated":
                False,
            "hypothetical_evaluation":
                _relative_or_name(
                    root,
                    hypothetical_path,
                ),
        }

    try:
        hypothetical = _load_json(
            hypothetical_path
        )
    except Exception as exc:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_evaluation_json_invalid",
            "ready":
                False,
            "results_generated":
                False,
            "reason":
                type(exc).__name__,
        }

    if (
        hypothetical.get(
            "schema_version"
        )
        != HYPOTHETICAL_EVALUATION_SCHEMA
        or hypothetical.get(
            "status"
        )
        != HYPOTHETICAL_EVALUATION_STATUS
        or hypothetical.get(
            "evaluation_type"
        )
        != "hypothetical_stress_test"
        or hypothetical.get(
            "ground_truth_available"
        )
        is not False
        or hypothetical.get(
            "independent_source_split"
        )
        != "test_normal"
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_evaluation_semantics_invalid",
            "ready":
                False,
            "results_generated":
                False,
        }

    identity = (
        evaluation.get(
            "scientific_identity"
        )
        or {}
    )

    if (
        hypothetical.get(
            "split_digest"
        )
        != identity.get(
            "split_digest"
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_split_digest_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if (
        hypothetical.get(
            "scientific_freeze_sha256"
        )
        != identity.get(
            "scientific_freeze_sha256"
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_scientific_freeze_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if (
        list(
            hypothetical.get(
                "features"
            )
            or []
        )
        != list(
            evaluation.get(
                "features"
            )
            or []
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_feature_set_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if not _float_equal(
        hypothetical.get(
            "threshold"
        ),
        threshold,
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_threshold_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    hypothetical_artifacts = (
        hypothetical.get(
            "artifacts"
        )
        or {}
    )

    expected_hashes = {
        "reference_sha256":
            artifact_hashes.get(
                "reference"
            ),
        "scaler_sha256":
            artifact_hashes.get(
                "scaler"
            ),
        "model_sha256":
            artifact_hashes.get(
                "model"
            ),
        "threshold_sha256":
            artifact_hashes.get(
                "threshold"
            ),
    }

    for field, expected in (
        expected_hashes.items()
    ):
        if (
            hypothetical_artifacts.get(
                field
            )
            != expected
        ):
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_hypothetical_artifact_hash_mismatch",
                "ready":
                    False,
                "results_generated":
                    False,
                "field":
                    field,
            }

    predictions_raw = (
        hypothetical.get(
            "predictions_file"
        )
    )

    predictions_hash = (
        hypothetical.get(
            "predictions_sha256"
        )
    )

    if (
        not isinstance(
            predictions_raw,
            str,
        )
        or not isinstance(
            predictions_hash,
            str,
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_predictions_metadata_missing",
            "ready":
                False,
            "results_generated":
                False,
        }

    predictions_path = (
        _resolve_artifact_path(
            root,
            predictions_raw,
        )
    )

    if not predictions_path.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_predictions_missing",
            "ready":
                False,
            "results_generated":
                False,
        }

    if (
        sha256_file(
            predictions_path
        )
        != predictions_hash
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_predictions_sha256_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    scenario_results = (
        hypothetical.get(
            "scenario_results"
        )
        or {}
    )

    if (
        "hypothetical_control"
        not in scenario_results
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_control_missing",
            "ready":
                False,
            "results_generated":
                False,
        }

    total_rows = 0
    total_flags = 0

    for (
        scenario_name,
        scenario,
    ) in scenario_results.items():
        rows = int(
            scenario.get(
                "rows",
                -1,
            )
        )

        anomaly_count = int(
            scenario.get(
                "anomaly_count",
                -1,
            )
        )

        rate = scenario.get(
            "threshold_exceedance_rate"
        )

        if (
            rows <= 0
            or anomaly_count < 0
            or anomaly_count > rows
            or rate is None
        ):
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_hypothetical_scenario_invalid",
                "ready":
                    False,
                "results_generated":
                    False,
                "scenario":
                    scenario_name,
            }

        expected_rate = (
            anomaly_count
            / rows
        )

        if not _float_equal(
            rate,
            expected_rate,
        ):
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_hypothetical_scenario_rate_mismatch",
                "ready":
                    False,
                "results_generated":
                    False,
                "scenario":
                    scenario_name,
            }

        total_rows += rows
        total_flags += anomaly_count

    if (
        total_rows
        != int(
            hypothetical.get(
                "total_predictions",
                -1,
            )
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_total_predictions_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if (
        total_flags
        != int(
            hypothetical.get(
                "total_anomaly_flags",
                -1,
            )
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_total_flags_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    if not _float_equal(
        hypothetical.get(
            "overall_threshold_exceedance_rate"
        ),
        total_flags
        / total_rows,
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_overall_rate_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    control = (
        scenario_results[
            "hypothetical_control"
        ]
    )

    if not _float_equal(
        control.get(
            "threshold_exceedance_rate"
        ),
        hypothetical.get(
            "control_threshold_exceedance_rate"
        ),
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_control_rate_mismatch",
            "ready":
                False,
            "results_generated":
                False,
        }

    source_hashes = {
        filename:
            sha256_file(
                evaluation_dir
                / filename
            )
        for filename
        in REQUIRED_SOURCE_FILES
    }

    source_hashes[
        "hypothetical_evaluation.json"
    ] = sha256_file(
        hypothetical_path
    )

    source_hashes[
        "hypothetical_ocsvm_predictions.csv.gz"
    ] = predictions_hash

    return {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            "ready_to_generate_scientifically_separated_final_results",
        "ready":
            True,
        "results_generated":
            False,
        "evaluation":
            evaluation,
        "normal":
            normal,
        "exploratory":
            exploratory,
        "hypothetical":
            hypothetical,
        "threshold":
            threshold,
        "test_normal_fpr":
            normal_fpr,
        "exploratory_threshold_exceedance_rate":
            exploratory_threshold_exceedance_rate,
        "source_hashes":
            source_hashes,
        "evaluation_dir":
            evaluation_dir,
        "project_root":
            root,
        "ground_truth_available_for_evil_twin":
            False,
        "legacy_supervised_metrics_ignored":
            True,
    }


def _metrics_table(
    gate: dict[str, Any],
) -> pd.DataFrame:
    evaluation = (
        gate[
            "evaluation"
        ]
    )

    hypothetical = (
        gate[
            "hypothetical"
        ]
    )

    coverage = (
        evaluation.get(
            "attack_coverage"
        )
        or {}
    )

    rows = [
        {
            "metric":
                "test_normal_fpr",
            "value":
                float(
                    gate[
                        "test_normal_fpr"
                    ]
                ),
            "scope":
                "independent_real_normal_test_only",
        },
        {
            "metric":
                "test_normal_rows",
            "value":
                float(
                    evaluation.get(
                        "normal_rows",
                        0,
                    )
                ),
            "scope":
                "independent_real_normal_test_only",
        },
        {
            "metric":
                "exploratory_context_threshold_exceedance_rate",
            "value":
                float(
                    gate[
                        "exploratory_threshold_exceedance_rate"
                    ]
                ),
            "scope":
                "unverified_attack_context_not_ground_truth",
        },
        {
            "metric":
                "hypothetical_overall_threshold_exceedance_rate",
            "value":
                float(
                    hypothetical[
                        "overall_threshold_exceedance_rate"
                    ]
                ),
            "scope":
                "hypothetical_stress_test_not_real_attack_recall",
        },
        {
            "metric":
                "hypothetical_control_threshold_exceedance_rate",
            "value":
                float(
                    hypothetical[
                        "control_threshold_exceedance_rate"
                    ]
                ),
            "scope":
                "hypothetical_control_from_test_normal",
        },
    ]

    if (
        coverage.get(
            "eligible_rate"
        )
        is not None
    ):
        rows.append({
            "metric":
                "exploratory_session_eligible_rate",
            "value":
                float(
                    coverage[
                        "eligible_rate"
                    ]
                ),
            "scope":
                "unverified_attack_context_feature_coverage_only",
        })

    return pd.DataFrame(
        rows
    )


def _score_distribution(
    *,
    normal_scores: np.ndarray,
    exploratory_scores: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    rows = []

    for (
        name,
        values,
        ground_truth_available,
    ) in (
        (
            "normal_test",
            normal_scores,
            True,
        ),
        (
            "unverified_attack_context_session",
            exploratory_scores,
            False,
        ),
    ):
        flags = (
            values
            > threshold
        )

        rows.append({
            "group":
                name,
            "rows":
                int(
                    len(
                        values
                    )
                ),
            "score_mean":
                float(
                    np.mean(
                        values
                    )
                ),
            "score_median":
                float(
                    np.median(
                        values
                    )
                ),
            "score_std":
                float(
                    np.std(
                        values
                    )
                ),
            "score_min":
                float(
                    np.min(
                        values
                    )
                ),
            "score_max":
                float(
                    np.max(
                        values
                    )
                ),
            "threshold":
                float(
                    threshold
                ),
            "threshold_exceedance_count":
                int(
                    flags.sum()
                ),
            "threshold_exceedance_rate":
                float(
                    flags.mean()
                ),
            "ground_truth_available":
                ground_truth_available,
        })

    return pd.DataFrame(
        rows
    )


def _exploratory_session_table(
    gate: dict[str, Any],
) -> pd.DataFrame:
    frame = (
        gate[
            "exploratory"
        ]
    )

    scores = (
        pd.to_numeric(
            frame[
                "anomaly_score"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=float
        )
    )

    threshold = float(
        gate[
            "threshold"
        ]
    )

    flags = (
        scores
        > threshold
    )

    return pd.DataFrame([
        {
            "group":
                "unverified_attack_context_session",
            "rows":
                int(
                    len(
                        scores
                    )
                ),
            "threshold_exceedance_count":
                int(
                    flags.sum()
                ),
            "threshold_exceedance_rate":
                float(
                    flags.mean()
                ),
            "score_min":
                float(
                    np.min(
                        scores
                    )
                ),
            "score_mean":
                float(
                    np.mean(
                        scores
                    )
                ),
            "score_median":
                float(
                    np.median(
                        scores
                    )
                ),
            "score_max":
                float(
                    np.max(
                        scores
                    )
                ),
            "ground_truth_available":
                False,
            "interpretation":
                "exploratory_observations_not_confirmed_evil_twin",
        }
    ])


def _hypothetical_scenarios_table(
    hypothetical: dict[str, Any],
) -> pd.DataFrame:
    rows = []

    scenario_results = (
        hypothetical.get(
            "scenario_results"
        )
        or {}
    )

    for (
        scenario_name,
        result,
    ) in sorted(
        scenario_results.items()
    ):
        expected_levels = (
            result.get(
                "heuristic_expected_suspicion_levels"
            )
            or []
        )

        delta = (
            result.get(
                "threshold_exceedance_rate_delta_vs_control"
            )
        )

        rows.append({
            "scenario":
                scenario_name,
            "rows":
                int(
                    result[
                        "rows"
                    ]
                ),
            "anomaly_count":
                int(
                    result[
                        "anomaly_count"
                    ]
                ),
            "normal_count":
                int(
                    result[
                        "normal_count"
                    ]
                ),
            "threshold_exceedance_rate":
                float(
                    result[
                        "threshold_exceedance_rate"
                    ]
                ),
            "threshold_exceedance_rate_delta_vs_control":
                (
                    float(
                        delta
                    )
                    if delta
                    is not None
                    else None
                ),
            "score_min":
                float(
                    result[
                        "score_min"
                    ]
                ),
            "score_mean":
                float(
                    result[
                        "score_mean"
                    ]
                ),
            "score_median":
                float(
                    result[
                        "score_median"
                    ]
                ),
            "score_p95":
                float(
                    result[
                        "score_p95"
                    ]
                ),
            "score_max":
                float(
                    result[
                        "score_max"
                    ]
                ),
            "ground_truth_available":
                False,
            "expected_suspicion_levels":
                ";".join(
                    str(
                        value
                    )
                    for value
                    in expected_levels
                ),
            "interpretation":
                "hypothetical_threshold_exceedance_not_real_attack_recall",
        })

    return pd.DataFrame(
        rows
    )


def _timing_table(
    evaluation: dict[str, Any],
) -> pd.DataFrame:
    timing = (
        evaluation.get(
            "timing"
        )
        or {}
    )

    mappings = (
        (
            "normal_inference_seconds_total",
            "normal_inference_seconds_total",
            "independent_real_normal_test",
        ),
        (
            "normal_inference_ms_per_row",
            "normal_inference_ms_per_row",
            "independent_real_normal_test",
        ),
        (
            "attack_inference_seconds_total",
            "exploratory_context_inference_seconds_total",
            "unverified_attack_context_session",
        ),
        (
            "attack_inference_ms_per_row",
            "exploratory_context_inference_ms_per_row",
            "unverified_attack_context_session",
        ),
    )

    rows = []

    for (
        source_field,
        output_field,
        scope,
    ) in mappings:
        value = (
            timing.get(
                source_field
            )
        )

        if value is None:
            continue

        rows.append({
            "metric":
                output_field,
            "value":
                float(
                    value
                ),
            "scope":
                scope,
            "measurement_scope":
                timing.get(
                    "scope",
                    "model inference only",
                ),
        })

    return pd.DataFrame(
        rows
    )


def _save_score_distribution_figure(
    *,
    normal_scores: np.ndarray,
    exploratory_scores: np.ndarray,
    threshold: float,
    path: Path,
) -> None:
    fig, ax = plt.subplots(
        figsize=(
            6,
            4.5,
        )
    )

    ax.hist(
        normal_scores,
        bins=20,
        alpha=0.6,
        label="Normal real (teste)",
    )

    ax.hist(
        exploratory_scores,
        bins=20,
        alpha=0.6,
        label="Sessão exploratória não confirmada",
    )

    ax.axvline(
        threshold,
        linestyle="--",
        label="Threshold congelado",
    )

    ax.set_xlabel(
        "Anomaly score"
    )

    ax.set_ylabel(
        "Frequência"
    )

    ax.set_title(
        "Distribuição dos scores — sem ground truth de ataque"
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def _save_hypothetical_figure(
    *,
    scenarios: pd.DataFrame,
    path: Path,
) -> None:
    ordered = (
        scenarios.sort_values(
            "scenario"
        )
        .reset_index(
            drop=True
        )
    )

    fig, ax = plt.subplots(
        figsize=(
            8,
            4.8,
        )
    )

    positions = np.arange(
        len(
            ordered
        )
    )

    ax.bar(
        positions,
        ordered[
            "threshold_exceedance_rate"
        ].to_numpy(
            dtype=float
        ),
    )

    ax.set_xticks(
        positions,
        labels=(
            ordered[
                "scenario"
            ].tolist()
        ),
        rotation=25,
        ha="right",
    )

    ax.set_ylim(
        0.0,
        1.05,
    )

    ax.set_ylabel(
        "Taxa de excedência do threshold"
    )

    ax.set_title(
        "Stress test hipotético — sensibilidade às perturbações"
    )

    fig.tight_layout()

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def _summary_markdown(
    *,
    gate: dict[str, Any],
    metrics_table: pd.DataFrame,
    hypothetical_table: pd.DataFrame,
) -> str:
    evaluation = (
        gate[
            "evaluation"
        ]
    )

    hypothetical = (
        gate[
            "hypothetical"
        ]
    )

    identity = (
        evaluation.get(
            "scientific_identity"
        )
        or {}
    )

    rows = [
        "# Resultados finais — desktop_candidate_v1",
        "",
        (
            "Este bundle separa os dados reais normais, a sessão "
            "exploratória não confirmada e o stress test hipotético."
        ),
        "",
        (
            "**Não há ground truth confirmado de Evil Twin nesta "
            "avaliação.**"
        ),
        "",
        "## Identidade científica",
        "",
        "```text",
        (
            "split_digest = "
            + str(
                identity.get(
                    "split_digest"
                )
            )
        ),
        (
            "scientific_freeze_sha256 = "
            + str(
                identity.get(
                    "scientific_freeze_sha256"
                )
            )
        ),
        (
            "reference_file_sha256 = "
            + str(
                identity.get(
                    "reference_file_sha256"
                )
            )
        ),
        "```",
        "",
        "## Métricas e taxas reportáveis",
        "",
        "| Métrica | Valor | Escopo |",
        "|---|---:|---|",
    ]

    for item in (
        metrics_table.itertuples(
            index=False
        )
    ):
        rows.append(
            (
                f"| {item.metric} | "
                f"{float(item.value):.6f} | "
                f"{item.scope} |"
            )
        )

    rows.extend([
        "",
        "## Dados reais normais",
        "",
        (
            "- Observações independentes: "
            + str(
                evaluation.get(
                    "normal_rows"
                )
            )
        ),
        (
            "- FPR no teste normal: "
            + (
                f"{float(gate['test_normal_fpr']):.6f}"
            )
        ),
        "",
        "## Sessão exploratória em contexto de ataque",
        "",
        (
            "- Observações elegíveis: "
            + str(
                evaluation.get(
                    "attack_rows_eligible"
                )
            )
        ),
        (
            "- Taxa de excedência do threshold: "
            + (
                f"{float(gate['exploratory_threshold_exceedance_rate']):.6f}"
            )
        ),
        (
            "- A sessão não é considerada confirmação de Evil Twin "
            "e não é usada como classe positiva real."
        ),
        (
            "- O `label=1` histórico é ignorado para cálculo de "
            "métricas supervisionadas."
        ),
        "",
        "## Stress test hipotético",
        "",
        (
            "- Tipo: "
            + str(
                hypothetical.get(
                    "evaluation_type"
                )
            )
        ),
        "- Ground truth disponível: não.",
        (
            "- Total de previsões: "
            + str(
                hypothetical.get(
                    "total_predictions"
                )
            )
        ),
        "",
        (
            "| Cenário | Linhas | Flags | "
            "Taxa de excedência | Δ vs controle |"
        ),
        "|---|---:|---:|---:|---:|",
    ])

    for item in (
        hypothetical_table.itertuples(
            index=False
        )
    ):
        delta = (
            ""
            if pd.isna(
                item.threshold_exceedance_rate_delta_vs_control
            )
            else (
                f"{float(item.threshold_exceedance_rate_delta_vs_control):.6f}"
            )
        )

        rows.append(
            (
                f"| {item.scenario} | "
                f"{int(item.rows)} | "
                f"{int(item.anomaly_count)} | "
                f"{float(item.threshold_exceedance_rate):.6f} | "
                f"{delta} |"
            )
        )

    rows.extend([
        "",
        "## Interpretação científica",
        "",
        (
            "- A taxa da sessão exploratória não deve ser "
            "interpretada como recall."
        ),
        (
            "- Os cenários hipotéticos medem sensibilidade do modelo "
            "a perturbações controladas."
        ),
        (
            "- Cenários hipotéticos ou sintéticos não constituem "
            "ataques confirmados."
        ),
        (
            "- Accuracy, precision, recall, F1, ROC-AUC, PR-AUC, "
            "FNR e matriz de confusão de Evil Twin não são reportados "
            "por ausência de ground truth real de ataque."
        ),
        (
            "- O threshold foi calibrado sem ataques e permanece "
            "congelado."
        ),
        (
            "- Reference, scaler, OCSVM e threshold permanecem "
            "inalterados."
        ),
        (
            "- Nenhum fit, refit ou recalibração é executado neste "
            "bundle."
        ),
        "",
    ])

    return "\n".join(
        rows
    )


def generate_final_tcc_results(
    *,
    project_root: str | Path,
    evaluation_dir: str | Path,
    output_dir: str | Path,
    hypothetical_evaluation_path: str | Path | None = None,
) -> dict[str, Any]:
    gate = (
        inspect_final_evaluation_for_results(
            project_root=(
                project_root
            ),
            evaluation_dir=(
                evaluation_dir
            ),
            hypothetical_evaluation_path=(
                hypothetical_evaluation_path
            ),
        )
    )

    if not gate[
        "ready"
    ]:
        return gate

    root = Path(
        project_root
    ).resolve()

    output_dir = Path(
        output_dir
    )

    if not output_dir.is_absolute():
        output_dir = (
            root
            / output_dir
        )

    if output_dir.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_results_output_already_exists",
            "ready":
                False,
            "results_generated":
                False,
            "output_dir":
                _relative_or_name(
                    root,
                    output_dir,
                ),
        }

    evaluation = (
        gate[
            "evaluation"
        ]
    )

    hypothetical = (
        gate[
            "hypothetical"
        ]
    )

    normal = (
        gate[
            "normal"
        ]
    )

    exploratory = (
        gate[
            "exploratory"
        ]
    )

    threshold = float(
        gate[
            "threshold"
        ]
    )

    normal_scores = (
        pd.to_numeric(
            normal[
                "anomaly_score"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=float
        )
    )

    exploratory_scores = (
        pd.to_numeric(
            exploratory[
                "anomaly_score"
            ],
            errors="raise",
        )
        .to_numpy(
            dtype=float
        )
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    metrics_table = (
        _metrics_table(
            gate
        )
    )

    metrics_table.to_csv(
        output_dir
        / "metrics_summary.csv",
        index=False,
    )

    distribution = (
        _score_distribution(
            normal_scores=(
                normal_scores
            ),
            exploratory_scores=(
                exploratory_scores
            ),
            threshold=(
                threshold
            ),
        )
    )

    distribution.to_csv(
        output_dir
        / "score_distribution.csv",
        index=False,
    )

    exploratory_table = (
        _exploratory_session_table(
            gate
        )
    )

    exploratory_table.to_csv(
        output_dir
        / "exploratory_session_summary.csv",
        index=False,
    )

    hypothetical_table = (
        _hypothetical_scenarios_table(
            hypothetical
        )
    )

    hypothetical_table.to_csv(
        output_dir
        / "hypothetical_scenarios.csv",
        index=False,
    )

    timing = (
        _timing_table(
            evaluation
        )
    )

    timing.to_csv(
        output_dir
        / "timing_summary.csv",
        index=False,
    )

    _save_score_distribution_figure(
        normal_scores=(
            normal_scores
        ),
        exploratory_scores=(
            exploratory_scores
        ),
        threshold=(
            threshold
        ),
        path=(
            output_dir
            / "score_distribution.png"
        ),
    )

    _save_hypothetical_figure(
        scenarios=(
            hypothetical_table
        ),
        path=(
            output_dir
            / "hypothetical_threshold_exceedance.png"
        ),
    )

    (
        output_dir
        / "final_results_summary.md"
    ).write_text(
        _summary_markdown(
            gate=(
                gate
            ),
            metrics_table=(
                metrics_table
            ),
            hypothetical_table=(
                hypothetical_table
            ),
        ),
        encoding="utf-8",
    )

    generated_hashes = {
        filename:
            sha256_file(
                output_dir
                / filename
            )
        for filename
        in AGGREGATE_OUTPUT_FILES
    }

    manifest = {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            "generated_scientifically_separated_final_results",
        "results_generated":
            True,
        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),
        "source_evaluation_schema":
            SOURCE_EVALUATION_SCHEMA,
        "hypothetical_evaluation_schema":
            HYPOTHETICAL_EVALUATION_SCHEMA,
        "scientific_identity":
            evaluation[
                "scientific_identity"
            ],
        "frozen_artifact_hashes":
            evaluation[
                "artifact_hashes"
            ],
        "source_file_sha256":
            gate[
                "source_hashes"
            ],
        "source_counts": {
            "normal_rows":
                int(
                    evaluation[
                        "normal_rows"
                    ]
                ),
            "exploratory_context_rows":
                int(
                    evaluation[
                        "attack_rows_eligible"
                    ]
                ),
            "exploratory_context_coverage":
                evaluation.get(
                    "attack_coverage"
                ),
            "hypothetical_predictions":
                int(
                    hypothetical[
                        "total_predictions"
                    ]
                ),
            "hypothetical_anomaly_flags":
                int(
                    hypothetical[
                        "total_anomaly_flags"
                    ]
                ),
        },
        "ground_truth": {
            "normal_test":
                True,
            "evil_twin_attack":
                False,
            "hypothetical_scenarios":
                False,
        },
        "reporting_policy": {
            "real_normal_fpr_reported":
                True,
            "exploratory_context_threshold_exceedance_reported":
                True,
            "hypothetical_threshold_exceedance_reported":
                True,
            "real_attack_accuracy_reported":
                False,
            "real_attack_precision_reported":
                False,
            "real_attack_recall_reported":
                False,
            "real_attack_f1_reported":
                False,
            "real_attack_roc_auc_reported":
                False,
            "real_attack_pr_auc_reported":
                False,
            "real_attack_confusion_matrix_reported":
                False,
        },
        "threshold":
            threshold,
        "feature_set":
            evaluation.get(
                "features"
            ),
        "aggregate_only":
            True,
        "privacy": {
            "row_level_score_files_copied":
                False,
            "hypothetical_row_level_predictions_copied":
                False,
            "clear_ssid_bssid_included":
                False,
            "wifi_hash_identifiers_included":
                False,
        },
        "scientific_guards": [
            (
                "Frozen artifact SHA-256 values must remain "
                "unchanged."
            ),
            (
                "Independent test_normal data is used to report "
                "normal false-positive rate."
            ),
            (
                "Historical attack-context observations are not "
                "accepted as confirmed Evil Twin ground truth."
            ),
            (
                "Legacy positive labels and attack-recall metrics "
                "are ignored for supervised attack evaluation."
            ),
            (
                "Hypothetical perturbations are reported only as "
                "threshold-exceedance and sensitivity results."
            ),
            (
                "Accuracy, precision, recall, F1, ROC-AUC, PR-AUC "
                "and attack confusion matrix are intentionally "
                "not generated."
            ),
            (
                "No model fitting, scaler fitting, threshold "
                "calibration or reference update occurs."
            ),
        ],
        "software": {
            "python":
                platform.python_version(),
            "numpy":
                np.__version__,
            "pandas":
                pd.__version__,
            "scikit_learn":
                sklearn.__version__,
            "matplotlib":
                matplotlib.__version__,
        },
        "generated_file_sha256":
            generated_hashes,
    }

    manifest_path = (
        output_dir
        / "reproducibility_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            "generated_scientifically_separated_final_results",
        "ready":
            True,
        "results_generated":
            True,
        "output_dir":
            _relative_or_name(
                root,
                output_dir,
            ),
        "manifest":
            _relative_or_name(
                root,
                manifest_path,
            ),
        "generated_files": [
            *AGGREGATE_OUTPUT_FILES,
            "reproducibility_manifest.json",
        ],
        "source_file_sha256":
            gate[
                "source_hashes"
            ],
        "scientific_identity":
            evaluation[
                "scientific_identity"
            ],
        "ground_truth_available_for_evil_twin":
            False,
    }


def inspect_generated_final_results(
    *,
    project_root: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    root = Path(
        project_root
    ).resolve()

    output_dir = Path(
        output_dir
    )

    if not output_dir.is_absolute():
        output_dir = (
            root
            / output_dir
        )

    manifest_path = (
        output_dir
        / "reproducibility_manifest.json"
    )

    if not manifest_path.exists():
        return {
            "ready":
                False,
            "status":
                "final_results_manifest_missing",
        }

    try:
        manifest = _load_json(
            manifest_path
        )
    except Exception:
        return {
            "ready":
                False,
            "status":
                "final_results_manifest_invalid",
        }

    if (
        manifest.get(
            "schema_version"
        )
        != SCHEMA_VERSION
        or manifest.get(
            "status"
        )
        != "generated_scientifically_separated_final_results"
        or manifest.get(
            "results_generated"
        )
        is not True
    ):
        return {
            "ready":
                False,
            "status":
                "final_results_manifest_semantics_invalid",
        }

    if (
        manifest.get(
            "aggregate_only"
        )
        is not True
    ):
        return {
            "ready":
                False,
            "status":
                "final_results_not_aggregate_only",
        }

    ground_truth = (
        manifest.get(
            "ground_truth"
        )
        or {}
    )

    if (
        ground_truth.get(
            "normal_test"
        )
        is not True
        or ground_truth.get(
            "evil_twin_attack"
        )
        is not False
        or ground_truth.get(
            "hypothetical_scenarios"
        )
        is not False
    ):
        return {
            "ready":
                False,
            "status":
                "final_results_ground_truth_contract_invalid",
        }

    reporting = (
        manifest.get(
            "reporting_policy"
        )
        or {}
    )

    forbidden_flags = (
        "real_attack_accuracy_reported",
        "real_attack_precision_reported",
        "real_attack_recall_reported",
        "real_attack_f1_reported",
        "real_attack_roc_auc_reported",
        "real_attack_pr_auc_reported",
        "real_attack_confusion_matrix_reported",
    )

    if any(
        reporting.get(
            field
        )
        is not False
        for field
        in forbidden_flags
    ):
        return {
            "ready":
                False,
            "status":
                "final_results_supervised_attack_metrics_present",
        }

    privacy = (
        manifest.get(
            "privacy"
        )
        or {}
    )

    if (
        privacy.get(
            "row_level_score_files_copied"
        )
        is not False
        or privacy.get(
            "hypothetical_row_level_predictions_copied"
        )
        is not False
        or privacy.get(
            "clear_ssid_bssid_included"
        )
        is not False
        or privacy.get(
            "wifi_hash_identifiers_included"
        )
        is not False
    ):
        return {
            "ready":
                False,
            "status":
                "final_results_privacy_contract_invalid",
        }

    forbidden_outputs = (
        "test_normal_scores.csv.gz",
        "attack_scores.csv.gz",
        "hypothetical_ocsvm_predictions.csv.gz",
        "confusion_matrix.csv",
        "roc_curve.csv",
        "precision_recall_curve.csv",
        "recall_by_attack_type.csv",
        "recall_by_attack_session.csv",
        "confusion_matrix.png",
        "roc_curve.png",
        "precision_recall_curve.png",
    )

    existing_forbidden = [
        filename
        for filename
        in forbidden_outputs
        if (
            output_dir
            / filename
        ).exists()
    ]

    if existing_forbidden:
        return {
            "ready":
                False,
            "status":
                "forbidden_supervised_or_row_level_output_present",
            "forbidden":
                existing_forbidden,
        }

    expected_hashes = (
        manifest.get(
            "generated_file_sha256"
        )
        or {}
    )

    missing = []
    mismatches = []

    for filename in (
        AGGREGATE_OUTPUT_FILES
    ):
        path = (
            output_dir
            / filename
        )

        if not path.exists():
            missing.append(
                filename
            )
            continue

        if (
            expected_hashes.get(
                filename
            )
            != sha256_file(
                path
            )
        ):
            mismatches.append(
                filename
            )

    if missing:
        return {
            "ready":
                False,
            "status":
                "final_results_outputs_missing",
            "missing":
                missing,
        }

    if mismatches:
        return {
            "ready":
                False,
            "status":
                "final_results_output_sha256_mismatch",
            "mismatches":
                mismatches,
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "manifest_sha256":
            sha256_file(
                manifest_path
            ),
        "scientific_identity":
            manifest.get(
                "scientific_identity"
            ),
        "ground_truth":
            ground_truth,
        "generated_files": [
            *AGGREGATE_OUTPUT_FILES,
            "reproducibility_manifest.json",
        ],
    }


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gera o bundle final do TCC separando dados normais reais, "
            "sessão exploratória sem ground truth e stress test hipotético."
        )
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--evaluation-dir",
        default=(
            "reports/desktop/"
            "final_evaluation_v1"
        ),
    )

    parser.add_argument(
        "--hypothetical-evaluation",
        default=(
            DEFAULT_HYPOTHETICAL_EVALUATION
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "reports/tcc/"
            "final_results_v1"
        ),
    )

    parser.add_argument(
        "--status-output",
        default=(
            "reports/desktop/"
            "final_results_step50.json"
        ),
    )

    parser.add_argument(
        "--preflight-only",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    if args.preflight_only:
        result = (
            inspect_final_evaluation_for_results(
                project_root=(
                    args.project_root
                ),
                evaluation_dir=(
                    args.evaluation_dir
                ),
                hypothetical_evaluation_path=(
                    args.hypothetical_evaluation
                ),
            )
        )
    else:
        result = (
            generate_final_tcc_results(
                project_root=(
                    args.project_root
                ),
                evaluation_dir=(
                    args.evaluation_dir
                ),
                output_dir=(
                    args.output_dir
                ),
                hypothetical_evaluation_path=(
                    args.hypothetical_evaluation
                ),
            )
        )

    serializable = {
        key:
            value
        for key, value
        in result.items()
        if key not in {
            "evaluation",
            "normal",
            "exploratory",
            "hypothetical",
            "project_root",
            "evaluation_dir",
        }
    }

    status_path = Path(
        args.status_output
    )

    if not status_path.is_absolute():
        status_path = (
            Path(
                args.project_root
            )
            / status_path
        )

    status_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    status_path.write_text(
        json.dumps(
            serializable,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            serializable,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        0
        if result.get(
            "ready"
        )
        is True
        else 8
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )