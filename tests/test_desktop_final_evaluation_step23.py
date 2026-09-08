import json

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from desktop.windows.artifact_lineage import (
    sha256_file,
    write_scaled_artifact_lineage,
)
from desktop.windows.evaluate_frozen_desktop_model import (
    evaluate_frozen_desktop_model,
)
from desktop.windows.train_desktop_ocsvm import (
    DESKTOP_FEATURES,
    calibrate_p95,
    anomaly_score,
)


def _prepare_fixture(
    tmp_path,
):
    train_raw = pd.DataFrame({
        "ssid_bssid_count": [
            1.0,
            1.2,
            1.4,
            1.6,
            1.8,
            2.0,
        ],
        "bssid_changed": [
            0.0
        ] * 6,
        "security_changed": [
            0.0
        ] * 6,
        "security_strength_delta": [
            0.0
        ] * 6,
    })

    validation_raw = pd.DataFrame({
        "ssid_bssid_count": [
            1.1,
            1.3,
            1.5,
            1.7,
        ],
        "bssid_changed": [
            0.0
        ] * 4,
        "security_changed": [
            0.0
        ] * 4,
        "security_strength_delta": [
            0.0
        ] * 4,
    })

    test_normal_raw = pd.DataFrame({
        "ssid_bssid_count": [
            1.15,
            1.45,
            1.75,
        ],
        "bssid_changed": [
            0.0
        ] * 3,
        "security_changed": [
            0.0
        ] * 3,
        "security_strength_delta": [
            0.0
        ] * 3,
    })

    attack_raw = pd.DataFrame({
        "ssid_bssid_count": [
            1.0,
            1.0,
            1.0,
        ],
        "bssid_changed": [
            1.0,
            1.0,
            1.0,
        ],
        "security_changed": [
            1.0,
            1.0,
            1.0,
        ],
        "security_strength_delta": [
            -3.0,
            -3.0,
            -3.0,
        ],
        "source_dataset": [
            "own_windows_attack"
        ] * 3,
        "session_id": [
            "attack-session"
        ] * 3,
        "attack_type": [
            "controlled_evil_twin"
        ] * 3,
        "label": [
            1
        ] * 3,
        "is_synthetic": [
            False
        ] * 3,
        "context_available": [
            True
        ] * 3,
        "feature_complete": [
            True
        ] * 3,
    })

    scaler = StandardScaler()
    scaler.fit(
        train_raw[
            DESKTOP_FEATURES
        ]
    )

    train_scaled = pd.DataFrame(
        scaler.transform(
            train_raw[
                DESKTOP_FEATURES
            ]
        ),
        columns=DESKTOP_FEATURES,
    )

    validation_scaled = pd.DataFrame(
        scaler.transform(
            validation_raw[
                DESKTOP_FEATURES
            ]
        ),
        columns=DESKTOP_FEATURES,
    )

    test_scaled = pd.DataFrame(
        scaler.transform(
            test_normal_raw[
                DESKTOP_FEATURES
            ]
        ),
        columns=DESKTOP_FEATURES,
    )

    model = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=0.05,
        shrinking=True,
        cache_size=512,
    )

    model.fit(
        train_scaled
    )

    val_scores = anomaly_score(
        model,
        validation_scaled,
    )

    calibration = calibrate_p95(
        val_scores
    )

    scaler_path = (
        tmp_path
        / "scaler.joblib"
    )

    model_path = (
        tmp_path
        / "model.joblib"
    )

    threshold_path = (
        tmp_path
        / "threshold.json"
    )

    reference_path = (
        tmp_path
        / "reference.json"
    )

    scaler_metadata_path = (
        tmp_path
        / "scaler.json"
    )

    joblib.dump(
        scaler,
        scaler_path,
    )

    joblib.dump(
        model,
        model_path,
    )

    split_digest = (
        "a"
        * 64
    )

    freeze_sha = (
        "b"
        * 64
    )

    reference_path.write_text(
        json.dumps({
            "schema_version":
                "desktop_normal_reference_v1",
            "status":
                "frozen",
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
        }),
        encoding="utf-8",
    )

    scaler_metadata_path.write_text(
        json.dumps({
            "schema_version":
                "desktop_candidate_v1_scaler_v1",
            "features":
                DESKTOP_FEATURES,
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
            "reference_file_sha256":
                sha256_file(
                    reference_path
                ),
        }),
        encoding="utf-8",
    )

    scaled_payloads = {
        "model_train":
            (
                train_scaled,
                "train-session",
            ),
        "validation":
            (
                validation_scaled,
                "validation-session",
            ),
        "test_normal":
            (
                test_scaled,
                "test-session",
            ),
    }

    for split, (
        values,
        session_id,
    ) in scaled_payloads.items():
        split_dir = (
            tmp_path
            / split
        )

        split_dir.mkdir()

        pd.DataFrame(
            values,
            columns=DESKTOP_FEATURES,
        ).to_csv(
            split_dir
            / "X.csv.gz",
            index=False,
            compression="gzip",
        )

        pd.DataFrame({
            "label": [
                0
            ]
            * len(
                values
            )
        }).to_csv(
            split_dir
            / "y.csv.gz",
            index=False,
            compression="gzip",
        )

        pd.DataFrame({
            "session_id": [
                session_id
            ]
            * len(
                values
            ),
            "source_dataset": [
                "own_windows"
            ]
            * len(
                values
            ),
        }).to_csv(
            split_dir
            / "metadata.csv.gz",
            index=False,
            compression="gzip",
        )

    test_dir = (
        tmp_path
        / "test_normal"
    )

    lineage = (
        write_scaled_artifact_lineage(
            scaled_root=(
                tmp_path
            ),
            scaler_path=(
                scaler_path
            ),
            scaler_metadata_path=(
                scaler_metadata_path
            ),
            identity={
                "split_digest":
                    split_digest,
                "scientific_freeze_sha256":
                    freeze_sha,
                "reference_file_sha256":
                    sha256_file(
                        reference_path
                    ),
            },
            features=(
                DESKTOP_FEATURES
            ),
        )
    )

    threshold_path.write_text(
        json.dumps({
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
            "threshold":
                calibration[
                    "threshold"
                ],
            "attack_used_for_calibration":
                False,
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
            "reference_file_sha256":
                sha256_file(
                    reference_path
                ),
            "scaler_file_sha256":
                sha256_file(
                    scaler_path
                ),
            "model_file_sha256":
                sha256_file(
                    model_path
                ),
            "artifact_lineage_file_sha256":
                lineage[
                    "artifact_lineage_file_sha256"
                ],
        }),
        encoding="utf-8",
    )

    attack_path = (
        tmp_path
        / "attack_features.csv.gz"
    )

    attack_raw.to_csv(
        attack_path,
        index=False,
        compression="gzip",
    )

    attack_manifest = (
        tmp_path
        / "attack_manifest.json"
    )

    attack_manifest.write_text(
        json.dumps({
            "rows":
                5,
            "eligible":
                3,
            "eligible_rate":
                0.6,
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
            "reference_file_sha256":
                sha256_file(
                    reference_path
                ),
        }),
        encoding="utf-8",
    )

    return {
        "reference":
            reference_path,
        "scaler":
            scaler_path,
        "model":
            model_path,
        "threshold":
            threshold_path,
        "test_normal":
            test_dir,
        "attack":
            attack_path,
        "attack_manifest":
            attack_manifest,
    }


def test_final_evaluation_blocks_missing_artifacts(
    tmp_path,
):
    result = evaluate_frozen_desktop_model(
        reference_path=(
            tmp_path
            / "missing-reference.json"
        ),
        scaler_path=(
            tmp_path
            / "missing-scaler.joblib"
        ),
        model_path=(
            tmp_path
            / "missing-model.joblib"
        ),
        threshold_path=(
            tmp_path
            / "missing-threshold.json"
        ),
        test_normal_dir=(
            tmp_path
            / "test"
        ),
        attack_features_path=(
            tmp_path
            / "attack.csv.gz"
        ),
        attack_manifest_path=(
            tmp_path
            / "attack-manifest.json"
        ),
        output_dir=(
            tmp_path
            / "out"
        ),
    )

    assert result[
        "status"
    ] == "blocked_final_evaluation_artifacts_missing"

    assert result[
        "evaluation_executed"
    ] is False

    assert result[
        "artifacts_modified"
    ] is False


def test_fixed_artifact_evaluation_runs(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    output = (
        tmp_path
        / "evaluation"
    )

    result = evaluate_frozen_desktop_model(
        reference_path=fixture[
            "reference"
        ],
        scaler_path=fixture[
            "scaler"
        ],
        model_path=fixture[
            "model"
        ],
        threshold_path=fixture[
            "threshold"
        ],
        test_normal_dir=fixture[
            "test_normal"
        ],
        attack_features_path=fixture[
            "attack"
        ],
        attack_manifest_path=fixture[
            "attack_manifest"
        ],
        output_dir=output,
    )

    assert result[
        "status"
    ] == "executed_fixed_artifacts"

    assert result[
        "evaluation_executed"
    ] is True

    assert result[
        "artifacts_modified"
    ] is False

    assert (
        result[
            "schema_version"
        ]
        == "desktop_final_evaluation_v2"
    )

    assert (
        result[
            "scientific_identity"
        ][
            "split_digest"
        ]
        == "a"
        * 64
    )

    assert (
        result[
            "artifact_hashes"
        ]
        == result[
            "artifact_hashes_after"
        ]
    )

    assert result[
        "attack_rows_eligible"
    ] == 3

    assert result[
        "attack_coverage"
    ][
        "eligible_rate"
    ] == 0.6

    metrics = result[
        "metrics"
    ]

    for key in [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
        "false_positive_rate",
        "false_negative_rate",
    ]:
        assert key in metrics

    assert (
        output
        / "final_evaluation.json"
    ).exists()

    assert (
        output
        / "attack_scores.csv.gz"
    ).exists()

    assert (
        output
        / "recall_by_attack_type.csv"
    ).exists()


def test_synthetic_attack_is_rejected(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    frame = pd.read_csv(
        fixture[
            "attack"
        ]
    )

    frame[
        "is_synthetic"
    ] = True

    frame.to_csv(
        fixture[
            "attack"
        ],
        index=False,
        compression="gzip",
    )

    try:
        evaluate_frozen_desktop_model(
            reference_path=fixture[
                "reference"
            ],
            scaler_path=fixture[
                "scaler"
            ],
            model_path=fixture[
                "model"
            ],
            threshold_path=fixture[
                "threshold"
            ],
            test_normal_dir=fixture[
                "test_normal"
            ],
            attack_features_path=fixture[
                "attack"
            ],
            attack_manifest_path=fixture[
                "attack_manifest"
            ],
            output_dir=(
                tmp_path
                / "out"
            ),
        )
    except ValueError as exc:
        assert "não aceita ataque sintético" in str(
            exc
        )
    else:
        raise AssertionError(
            "Synthetic attack deveria ser rejeitado."
        )


def test_threshold_that_used_attack_is_rejected(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    threshold = json.loads(
        fixture[
            "threshold"
        ].read_text(
            encoding="utf-8"
        )
    )

    threshold[
        "attack_used_for_calibration"
    ] = True

    fixture[
        "threshold"
    ].write_text(
        json.dumps(
            threshold
        ),
        encoding="utf-8",
    )

    result = evaluate_frozen_desktop_model(
        reference_path=fixture[
            "reference"
        ],
        scaler_path=fixture[
            "scaler"
        ],
        model_path=fixture[
            "model"
        ],
        threshold_path=fixture[
            "threshold"
        ],
        test_normal_dir=fixture[
            "test_normal"
        ],
        attack_features_path=fixture[
            "attack"
        ],
        attack_manifest_path=fixture[
            "attack_manifest"
        ],
        output_dir=(
            tmp_path
            / "out"
        ),
    )

    assert (
        result[
            "status"
        ]
        == "blocked_final_evaluation_artifact_chain_mismatch"
    )

    assert (
        result[
            "evaluation_executed"
        ]
        is False
    )




def test_final_evaluation_blocks_attack_features_from_other_reference(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    manifest = json.loads(
        fixture[
            "attack_manifest"
        ].read_text(
            encoding="utf-8"
        )
    )

    manifest[
        "reference_file_sha256"
    ] = (
        "f"
        * 64
    )

    fixture[
        "attack_manifest"
    ].write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    result = (
        evaluate_frozen_desktop_model(
            reference_path=fixture[
                "reference"
            ],
            scaler_path=fixture[
                "scaler"
            ],
            model_path=fixture[
                "model"
            ],
            threshold_path=fixture[
                "threshold"
            ],
            test_normal_dir=fixture[
                "test_normal"
            ],
            attack_features_path=fixture[
                "attack"
            ],
            attack_manifest_path=fixture[
                "attack_manifest"
            ],
            output_dir=(
                tmp_path
                / "out"
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_final_evaluation_attack_reference_mismatch"
    )

    assert (
        result[
            "evaluation_executed"
        ]
        is False
    )


def test_final_evaluation_blocks_mixed_scaler_artifact(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    fixture[
        "scaler"
    ].write_bytes(
        fixture[
            "scaler"
        ].read_bytes()
        + b"mutation"
    )

    result = (
        evaluate_frozen_desktop_model(
            reference_path=fixture[
                "reference"
            ],
            scaler_path=fixture[
                "scaler"
            ],
            model_path=fixture[
                "model"
            ],
            threshold_path=fixture[
                "threshold"
            ],
            test_normal_dir=fixture[
                "test_normal"
            ],
            attack_features_path=fixture[
                "attack"
            ],
            attack_manifest_path=fixture[
                "attack_manifest"
            ],
            output_dir=(
                tmp_path
                / "out"
            ),
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_final_evaluation_artifact_chain_mismatch"
    )

    assert (
        result[
            "evaluation_executed"
        ]
        is False
    )


def test_output_is_create_only(
    tmp_path,
):
    fixture = _prepare_fixture(
        tmp_path
    )

    output = (
        tmp_path
        / "evaluation"
    )

    evaluate_frozen_desktop_model(
        reference_path=fixture[
            "reference"
        ],
        scaler_path=fixture[
            "scaler"
        ],
        model_path=fixture[
            "model"
        ],
        threshold_path=fixture[
            "threshold"
        ],
        test_normal_dir=fixture[
            "test_normal"
        ],
        attack_features_path=fixture[
            "attack"
        ],
        attack_manifest_path=fixture[
            "attack_manifest"
        ],
        output_dir=output,
    )

    try:
        evaluate_frozen_desktop_model(
            reference_path=fixture[
                "reference"
            ],
            scaler_path=fixture[
                "scaler"
            ],
            model_path=fixture[
                "model"
            ],
            threshold_path=fixture[
                "threshold"
            ],
            test_normal_dir=fixture[
                "test_normal"
            ],
            attack_features_path=fixture[
                "attack"
            ],
            attack_manifest_path=fixture[
                "attack_manifest"
            ],
            output_dir=output,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "Evaluation output deveria ser create-only."
        )
