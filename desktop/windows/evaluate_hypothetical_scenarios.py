from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from desktop.final_readiness import (
    MODEL_PATH,
    REFERENCE_PATH,
    SCALER_PATH,
    THRESHOLD_PATH,
)

from .artifact_lineage import (
    sha256_file,
    validate_runtime_artifact_chain,
)

from .desktop_reference import (
    DESKTOP_FEATURES,
    transform_desktop_features,
)


SCHEMA_VERSION = (
    "desktop_hypothetical_ocsvm_evaluation_v1"
)

EXPECTED_INPUT_SCHEMA = (
    "desktop_hypothetical_scenarios_v1"
)


def _load_json(
    path: str | Path,
) -> dict[str, object]:
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo ausente: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _is_true(
    value: object,
) -> bool:
    if pd.isna(
        value
    ):
        return False

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        return bool(
            value
        )

    return (
        str(
            value
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "y",
        }
    )


def discover_scenario_files(
    input_root: str | Path,
) -> list[Path]:
    root = Path(
        input_root
    )

    if not root.exists():
        return []

    #
    # Procura somente:
    #
    # scenario/
    #   observations.csv.gz
    #
    # e ignora o arquivo combinado no root.
    #
    return sorted(
        path
        for path in root.glob(
            "*/observations.csv.gz"
        )
        if path.is_file()
    )


def _test_normal_sessions(
    split_plan: dict[str, object],
) -> set[str]:
    assignments = (
        split_plan.get(
            "assignments"
        )
        or []
    )

    result = set()

    for assignment in assignments:
        if (
            assignment.get(
                "split"
            )
            == "test_normal"
        ):
            result.add(
                str(
                    assignment[
                        "session_id"
                    ]
                )
            )

    return result


def _score_summary(
    scores: np.ndarray,
    is_anomaly: np.ndarray,
) -> dict[str, object]:
    if len(
        scores
    ) == 0:
        return {
            "rows":
                0,
            "anomaly_count":
                0,
            "normal_count":
                0,
            "threshold_exceedance_rate":
                0.0,
            "score_min":
                None,
            "score_mean":
                None,
            "score_median":
                None,
            "score_p95":
                None,
            "score_max":
                None,
        }

    anomaly_count = int(
        np.sum(
            is_anomaly
        )
    )

    return {
        "rows":
            int(
                len(
                    scores
                )
            ),
        "anomaly_count":
            anomaly_count,
        "normal_count":
            int(
                len(
                    scores
                )
                - anomaly_count
            ),
        "threshold_exceedance_rate":
            float(
                anomaly_count
                / len(
                    scores
                )
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
        "score_p95":
            float(
                np.quantile(
                    scores,
                    0.95,
                )
            ),
        "score_max":
            float(
                np.max(
                    scores
                )
            ),
    }


def evaluate_hypothetical_scenarios(
    input_root: str | Path,
    split_plan_path: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    input_root = Path(
        input_root
    )

    output_root = Path(
        output_root
    )

    split_plan_path = Path(
        split_plan_path
    )

    #
    # 1. Validar cadeia congelada de runtime.
    #
    runtime_chain = (
        validate_runtime_artifact_chain(
            reference_path=(
                REFERENCE_PATH
            ),
            scaler_path=(
                SCALER_PATH
            ),
            model_path=(
                MODEL_PATH
            ),
            threshold_path=(
                THRESHOLD_PATH
            ),
        )
    )

    if not runtime_chain.get(
        "ready"
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_runtime_artifact_chain_not_ready",
            "created":
                False,
            "runtime_chain":
                runtime_chain,
        }

    #
    # 2. Validar existência do input.
    #
    scenario_files = (
        discover_scenario_files(
            input_root
        )
    )

    if not scenario_files:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_data_missing",
            "created":
                False,
        }

    input_manifest_path = (
        input_root
        / "manifest.json"
    )

    if not input_manifest_path.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_hypothetical_manifest_missing",
            "created":
                False,
        }

    if output_root.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_output_already_exists",
            "created":
                False,
        }

    input_manifest = _load_json(
        input_manifest_path
    )

    if (
        input_manifest.get(
            "schema_version"
        )
        != EXPECTED_INPUT_SCHEMA
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_unexpected_input_schema",
            "created":
                False,
            "input_schema":
                input_manifest.get(
                    "schema_version"
                ),
        }

    if (
        input_manifest.get(
            "ground_truth_available"
        )
        is not False
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_ground_truth_contract_invalid",
            "created":
                False,
        }

    if (
        input_manifest.get(
            "generated_rows_are_synthetic"
        )
        is not True
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_synthetic_contract_invalid",
            "created":
                False,
        }

    #
    # 3. Validar split científico.
    #
    split_plan = _load_json(
        split_plan_path
    )

    test_normal_sessions = (
        _test_normal_sessions(
            split_plan
        )
    )

    if not test_normal_sessions:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_test_normal_split_missing",
            "created":
                False,
        }

    if (
        split_plan.get(
            "split_digest"
        )
        != input_manifest.get(
            "split_digest"
        )
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_input_split_digest_mismatch",
            "created":
                False,
        }

    #
    # 4. Carregar artefatos congelados.
    #
    reference = _load_json(
        REFERENCE_PATH
    )

    threshold_artifact = _load_json(
        THRESHOLD_PATH
    )

    threshold_features = (
        threshold_artifact.get(
            "features"
        )
    )

    if (
        threshold_features
        != DESKTOP_FEATURES
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_threshold_feature_contract_mismatch",
            "created":
                False,
            "expected_features":
                DESKTOP_FEATURES,
            "threshold_features":
                threshold_features,
        }

    if (
        threshold_artifact.get(
            "prediction_rule"
        )
        != "anomaly_score > threshold"
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_threshold_prediction_rule_mismatch",
            "created":
                False,
        }

    if (
        threshold_artifact.get(
            "attack_used_for_calibration"
        )
        is not False
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_threshold_attack_calibration_detected",
            "created":
                False,
        }

    threshold = float(
        threshold_artifact[
            "threshold"
        ]
    )

    scaler = joblib.load(
        SCALER_PATH
    )

    model = joblib.load(
        MODEL_PATH
    )

    #
    # 5. Avaliar cada cenário.
    #
    prediction_parts = []
    scenario_results = {}

    all_source_sessions = set()

    for observations_path in (
        scenario_files
    ):
        frame = pd.read_csv(
            observations_path
        )

        if frame.empty:
            continue

        required_columns = {
            "scenario_type",
            "source_session_id",
            "is_synthetic",
            "ssid_hash",
            "bssid_hash",
            "security_type",
            "security_strength",
        }

        missing = sorted(
            required_columns
            - set(
                frame.columns
            )
        )

        if missing:
            raise ValueError(
                f"{observations_path}: "
                "colunas obrigatórias ausentes: "
                f"{missing}"
            )

        #
        # Todos os dados avaliados aqui
        # precisam ser explicitamente sintéticos.
        #
        synthetic_mask = (
            frame[
                "is_synthetic"
            ].map(
                _is_true
            )
        )

        if not synthetic_mask.all():
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_non_synthetic_row_in_hypothetical_input",
                "created":
                    False,
                "file":
                    str(
                        observations_path
                    ),
            }

        source_sessions = {
            str(
                value
            )
            for value
            in frame[
                "source_session_id"
            ].dropna()
        }

        all_source_sessions.update(
            source_sessions
        )

        invalid_source_sessions = (
            source_sessions
            - test_normal_sessions
        )

        if invalid_source_sessions:
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_non_test_normal_source_detected",
                "created":
                    False,
                "file":
                    str(
                        observations_path
                    ),
                "invalid_source_sessions":
                    sorted(
                        invalid_source_sessions
                    ),
                "allowed_test_normal_sessions":
                    sorted(
                        test_normal_sessions
                    ),
            }

        #
        # Mesma transformação do runtime.
        #
        features = (
            transform_desktop_features(
                frame,
                reference,
            )
        )

        eligible_mask = (
            features[
                "context_available"
            ].astype(
                bool
            )
            & features[
                "feature_complete"
            ].astype(
                bool
            )
        )

        eligible_indices = (
            features.index[
                eligible_mask
            ]
        )

        eligible_features = (
            features.loc[
                eligible_indices,
                DESKTOP_FEATURES,
            ]
            .astype(
                float
            )
            .copy()
        )

        if eligible_features.empty:
            continue

        #
        # StandardScaler congelado.
        #
        scaled_array = scaler.transform(
            eligible_features
        )

        scaled = pd.DataFrame(
            scaled_array,
            columns=DESKTOP_FEATURES,
            index=eligible_features.index,
        )

        anomaly_scores = (
            -np.asarray(
                model.decision_function(
                    scaled
                ),
                dtype=float,
            ).reshape(
                -1
            )
        )

        is_anomaly = (
            anomaly_scores
            > threshold
        )

        scenario_type = str(
            frame[
                "scenario_type"
            ].iloc[
                0
            ]
        )

        if (
            frame[
                "scenario_type"
            ].nunique()
            != 1
        ):
            return {
                "schema_version":
                    SCHEMA_VERSION,
                "status":
                    "blocked_mixed_scenarios_in_file",
                "created":
                    False,
                "file":
                    str(
                        observations_path
                    ),
            }

        summary = _score_summary(
            anomaly_scores,
            is_anomaly,
        )

        summary[
            "input_rows"
        ] = int(
            len(
                frame
            )
        )

        summary[
            "eligible_rows"
        ] = int(
            len(
                eligible_features
            )
        )

        summary[
            "not_evaluable_rows"
        ] = int(
            len(
                frame
            )
            - len(
                eligible_features
            )
        )

        summary[
            "source_sessions"
        ] = sorted(
            source_sessions
        )

        if (
            "expected_suspicion_level"
            in frame.columns
        ):
            values = (
                frame[
                    "expected_suspicion_level"
                ]
                .dropna()
                .astype(
                    str
                )
                .unique()
                .tolist()
            )

            summary[
                "heuristic_expected_suspicion_levels"
            ] = sorted(
                values
            )

        scenario_results[
            scenario_type
        ] = summary

        #
        # Predictions linha a linha.
        #
        metadata_columns = [
            "scenario_type",
            "scenario_family",
            "expected_suspicion_level",
            "source_session_id",
            "source_scan_index",
            "source_row_index",
            "ssid_hash",
            "bssid_hash",
        ]

        prediction_frame = (
            frame.loc[
                eligible_indices,
                [
                    column
                    for column
                    in metadata_columns
                    if column
                    in frame.columns
                ],
            ]
            .reset_index(
                drop=True
            )
        )

        feature_output = (
            eligible_features
            .reset_index(
                drop=True
            )
        )

        prediction_frame = pd.concat(
            [
                prediction_frame,
                feature_output,
            ],
            axis=1,
        )

        prediction_frame[
            "anomaly_score"
        ] = anomaly_scores

        prediction_frame[
            "threshold"
        ] = threshold

        prediction_frame[
            "is_anomaly"
        ] = is_anomaly

        prediction_frame[
            "evaluation_type"
        ] = (
            "hypothetical_stress_test"
        )

        prediction_frame[
            "ground_truth_available"
        ] = False

        prediction_parts.append(
            prediction_frame
        )

    if not prediction_parts:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_no_eligible_hypothetical_rows",
            "created":
                False,
        }

    #
    # 6. Garantia final:
    # todos os sources são test_normal.
    #
    if not all_source_sessions.issubset(
        test_normal_sessions
    ):
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_source_split_validation_failed",
            "created":
                False,
        }

    predictions = pd.concat(
        prediction_parts,
        ignore_index=True,
    )

    #
    # 7. Comparação com o controle.
    #
    control_result = (
        scenario_results.get(
            "hypothetical_control"
        )
    )

    control_rate = None

    if control_result:
        control_rate = float(
            control_result[
                "threshold_exceedance_rate"
            ]
        )

        control_result[
            "interpretation"
        ] = (
            "Control copy of independent "
            "test_normal baseline observations."
        )

    for (
        scenario_type,
        summary,
    ) in scenario_results.items():
        if (
            control_rate
            is not None
            and scenario_type
            != "hypothetical_control"
        ):
            summary[
                "threshold_exceedance_rate_delta_vs_control"
            ] = float(
                summary[
                    "threshold_exceedance_rate"
                ]
                - control_rate
            )

    #
    # 8. Persistência.
    #
    output_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    predictions_path = (
        output_root
        / "hypothetical_ocsvm_predictions.csv.gz"
    )

    predictions.to_csv(
        predictions_path,
        index=False,
        compression="gzip",
    )

    result = {
        "schema_version":
            SCHEMA_VERSION,
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
        "source_session_ids":
            sorted(
                all_source_sessions
            ),
        "features":
            DESKTOP_FEATURES,
        "anomaly_score_definition":
            "-OCSVM.decision_function(X_scaled)",
        "prediction_rule":
            "anomaly_score > threshold",
        "threshold":
            threshold,
        "total_predictions":
            int(
                len(
                    predictions
                )
            ),
        "total_anomaly_flags":
            int(
                predictions[
                    "is_anomaly"
                ].sum()
            ),
        "overall_threshold_exceedance_rate":
            float(
                predictions[
                    "is_anomaly"
                ].mean()
            ),
        "control_threshold_exceedance_rate":
            control_rate,
        "scenario_results":
            scenario_results,
        "split_digest":
            split_plan.get(
                "split_digest"
            ),
        "scientific_freeze_sha256":
            reference.get(
                "scientific_freeze_sha256"
            ),
        "artifacts": {
            "reference":
                str(
                    REFERENCE_PATH
                ),
            "reference_sha256":
                sha256_file(
                    REFERENCE_PATH
                ),
            "scaler":
                str(
                    SCALER_PATH
                ),
            "scaler_sha256":
                sha256_file(
                    SCALER_PATH
                ),
            "model":
                str(
                    MODEL_PATH
                ),
            "model_sha256":
                sha256_file(
                    MODEL_PATH
                ),
            "threshold":
                str(
                    THRESHOLD_PATH
                ),
            "threshold_sha256":
                sha256_file(
                    THRESHOLD_PATH
                ),
        },
        "input_manifest_sha256":
            sha256_file(
                input_manifest_path
            ),
        "predictions_file":
            str(
                predictions_path
            ),
        "predictions_sha256":
            sha256_file(
                predictions_path
            ),
        "scientific_interpretation": {
            "allowed": [
                (
                    "Threshold exceedance rate "
                    "under controlled hypothetical "
                    "perturbations."
                ),
                (
                    "Sensitivity of the frozen "
                    "desktop_candidate_v1 to each "
                    "perturbation scenario."
                ),
                (
                    "Comparison between hypothetical "
                    "scenarios and the independent "
                    "test_normal control."
                ),
            ],
            "forbidden": [
                "Real Evil Twin recall.",
                "Real Evil Twin precision.",
                "Real Evil Twin F1-score.",
                "Real attack detection accuracy.",
                (
                    "Claim that synthetic "
                    "perturbations are confirmed "
                    "attacks."
                ),
            ],
        },
        "scientific_rules": [
            (
                "Only frozen reference, scaler, "
                "OCSVM and threshold are used."
            ),
            (
                "No fit, refit or threshold "
                "recalibration occurs."
            ),
            (
                "All hypothetical samples originate "
                "exclusively from frozen test_normal "
                "sessions."
            ),
            (
                "Generated perturbations remain "
                "synthetic and do not constitute "
                "attack ground truth."
            ),
            (
                "Reported scenario rates are "
                "threshold-exceedance rates, not "
                "real-attack recall."
            ),
        ],
    }

    report_path = (
        output_root
        / "evaluation.json"
    )

    report_path.write_text(
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
            "Avalia cenários hipotéticos "
            "derivados exclusivamente do "
            "test_normal usando o scaler, "
            "OCSVM e threshold congelados. "
            "Não produz métricas de ataques reais."
        )
    )

    parser.add_argument(
        "--input-root",
        default=(
            "data/processed/"
            "desktop_hypothetical_test_normal_v1"
        ),
    )

    parser.add_argument(
        "--split-plan",
        default=(
            "data/processed/"
            "desktop_candidate_v1/"
            "session_split_plan.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/processed/"
            "desktop_hypothetical_test_normal_v1_ocsvm"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = (
        evaluate_hypothetical_scenarios(
            input_root=(
                args.input_root
            ),
            split_plan_path=(
                args.split_plan
            ),
            output_root=(
                args.output_root
            ),
        )
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