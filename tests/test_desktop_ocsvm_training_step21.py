import json

import joblib
import numpy as np
import pandas as pd

from desktop.windows.artifact_lineage import (
    sha256_file,
)
from desktop.windows.train_desktop_ocsvm import (
    DESKTOP_FEATURES,
    calibrate_p95,
    check_training_gate,
    train_and_calibrate_desktop_ocsvm,
)


def _write_split(
    root,
    split,
    X,
    session_id,
):
    folder = (
        root
        / split
    )

    folder.mkdir(
        parents=True
    )

    frame = pd.DataFrame(
        X,
        columns=DESKTOP_FEATURES,
    )

    frame.to_csv(
        folder
        / "X.csv.gz",
        index=False,
        compression="gzip",
    )

    pd.DataFrame({
        "label":
            [0]
            * len(
                frame
            )
    }).to_csv(
        folder
        / "y.csv.gz",
        index=False,
        compression="gzip",
    )

    pd.DataFrame({
        "session_id":
            [session_id]
            * len(
                frame
            ),
        "source_dataset":
            ["own_windows"]
            * len(
                frame
            ),
    }).to_csv(
        folder
        / "metadata.csv.gz",
        index=False,
        compression="gzip",
    )


def _fixture(
    root,
):
    # Already-scaled-like synthetic values. This is software validation only.
    train = [
        [-1.0, 0.0, 0.0, 0.0],
        [-0.5, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.5, 0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
    ]

    validation = [
        [-0.8, 0.0, 0.0, 0.0],
        [-0.3, 0.0, 0.0, 0.0],
        [0.2, 0.0, 0.0, 0.0],
        [0.7, 0.0, 0.0, 0.0],
    ]

    test = [
        [-0.7, 0.0, 0.0, 0.0],
        [0.1, 0.0, 0.0, 0.0],
        [0.6, 0.0, 0.0, 0.0],
    ]

    _write_split(
        root,
        "model_train",
        train,
        "train-session",
    )

    _write_split(
        root,
        "validation",
        validation,
        "validation-session",
    )

    _write_split(
        root,
        "test_normal",
        test,
        "test-session",
    )


    identity_hash = (
        "a"
        * 64
    )

    split_hashes = {}

    for split in (
        "model_train",
        "validation",
        "test_normal",
    ):
        split_hashes[
            split
        ] = {
            filename:
                sha256_file(
                    root
                    / split
                    / filename
                )
            for filename in (
                "X.csv.gz",
                "y.csv.gz",
                "metadata.csv.gz",
            )
        }

    (
        root
        / "artifact_lineage.json"
    ).write_text(
        json.dumps({
            "schema_version":
                "desktop_artifact_lineage_v1",
            "feature_set_name":
                "desktop_candidate_v1",
            "features":
                DESKTOP_FEATURES,
            "split_digest":
                identity_hash,
            "scientific_freeze_sha256":
                "b"
                * 64,
            "reference_file_sha256":
                "c"
                * 64,
            "scaler_file_sha256":
                "d"
                * 64,
            "scaler_metadata_file_sha256":
                "e"
                * 64,
            "scaled_split_hashes":
                split_hashes,
        }),
        encoding="utf-8",
    )


def test_gate_blocks_missing_real_ml_data(
    tmp_path,
):
    gate = check_training_gate(
        tmp_path
        / "missing"
    )

    assert gate[
        "ready"
    ] is False

    assert gate[
        "status"
    ] == "blocked_ml_ready_data_missing"


def test_calibration_p95_is_validation_only_rule():
    scores = np.array([
        0.0,
        1.0,
        2.0,
        3.0,
        100.0,
    ])

    result = calibrate_p95(
        scores
    )

    assert result[
        "quantile"
    ] == 0.95

    assert result[
        "threshold"
    ] == float(
        np.quantile(
            scores,
            0.95,
        )
    )

    assert result[
        "prediction_rule"
    ] == "anomaly_score > threshold"


def test_train_and_calibrate_synthetic_fixture(
    tmp_path,
):
    scaled = (
        tmp_path
        / "scaled"
    )

    _fixture(
        scaled
    )

    output = (
        tmp_path
        / "model"
    )

    result = (
        train_and_calibrate_desktop_ocsvm(
            scaled,
            output,
        )
    )

    assert result[
        "status"
    ] == "trained_and_calibrated_normal_only"

    assert result[
        "model_trained"
    ] is True

    assert result[
        "threshold_calibrated"
    ] is True

    assert result[
        "real_attack_evaluated"
    ] is False

    assert (
        output
        / "one_class_svm_desktop_candidate_v1.joblib"
    ).exists()

    assert (
        output
        / "threshold.json"
    ).exists()

    model_metadata = json.loads(
        (
            output
            / "one_class_svm_desktop_candidate_v1.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert model_metadata[
        "attack_data_seen"
    ] is False

    assert model_metadata[
        "real_attack_evaluated"
    ] is False

    assert model_metadata[
        "fit_sessions"
    ] == [
        "train-session"
    ]


    threshold = json.loads(
        (
            output
            / "threshold.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        threshold[
            "schema_version"
        ]
        == "desktop_threshold_v2"
    )

    assert (
        threshold[
            "split_digest"
        ]
        == "a"
        * 64
    )

    assert len(
        threshold[
            "model_file_sha256"
        ]
    ) == 64

    assert (
        model_metadata[
            "split_digest"
        ]
        == threshold[
            "split_digest"
        ]
    )



def test_training_gate_blocks_scaled_matrix_mutation(
    tmp_path,
):
    scaled = (
        tmp_path
        / "scaled"
    )

    _fixture(
        scaled
    )

    X_path = (
        scaled
        / "validation"
        / "X.csv.gz"
    )

    frame = pd.read_csv(
        X_path
    )

    frame.loc[
        0,
        DESKTOP_FEATURES[
            0
        ]
    ] = 999.0

    frame.to_csv(
        X_path,
        index=False,
        compression="gzip",
    )

    gate = check_training_gate(
        scaled
    )

    assert (
        gate[
            "ready"
        ]
        is False
    )

    assert (
        gate[
            "status"
        ]
        == "blocked_artifact_lineage_mismatch"
    )


def test_session_leakage_is_rejected(
    tmp_path,
):
    scaled = (
        tmp_path
        / "scaled"
    )

    _fixture(
        scaled
    )

    validation_metadata = pd.read_csv(
        scaled
        / "validation"
        / "metadata.csv.gz"
    )

    validation_metadata[
        "session_id"
    ] = "train-session"

    validation_metadata.to_csv(
        scaled
        / "validation"
        / "metadata.csv.gz",
        index=False,
        compression="gzip",
    )

    lineage_path = (
        scaled
        / "artifact_lineage.json"
    )

    lineage = json.loads(
        lineage_path.read_text(
            encoding="utf-8"
        )
    )

    lineage[
        "scaled_split_hashes"
    ][
        "validation"
    ][
        "metadata.csv.gz"
    ] = sha256_file(
        scaled
        / "validation"
        / "metadata.csv.gz"
    )

    lineage_path.write_text(
        json.dumps(
            lineage
        ),
        encoding="utf-8",
    )

    try:
        train_and_calibrate_desktop_ocsvm(
            scaled,
            tmp_path
            / "model",
        )
    except ValueError as exc:
        assert "Session leakage" in str(
            exc
        )
    else:
        raise AssertionError(
            "Session leakage deveria ser rejeitado."
        )


def test_output_model_dir_is_create_only(
    tmp_path,
):
    scaled = (
        tmp_path
        / "scaled"
    )

    _fixture(
        scaled
    )

    output = (
        tmp_path
        / "model"
    )

    train_and_calibrate_desktop_ocsvm(
        scaled,
        output,
    )

    try:
        train_and_calibrate_desktop_ocsvm(
            scaled,
            output,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "Model output deveria ser create-only."
        )
