import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from desktop.windows.prepare_desktop_ml import (
    DESKTOP_FEATURES,
    prepare_desktop_ml,
)


def _write_prepared_dataset(
    root,
):
    root.mkdir(
        parents=True
    )

    source_hash = hashlib.sha256(
        b"source"
    ).hexdigest()

    assignment = {
        "session_id":
            "reference",
        "split":
            "reference",
        "source_scans_sha256":
            source_hash,
        "observations_sha256":
            source_hash,
        "content_fingerprint":
            source_hash,
    }

    train_assignment_a = {
        **assignment,
        "session_id":
            "train-a",
        "split":
            "model_train",
    }

    train_assignment_b = {
        **assignment,
        "session_id":
            "train-b",
        "split":
            "model_train",
    }

    validation_assignment = {
        **assignment,
        "session_id":
            "validation",
        "split":
            "validation",
    }

    test_assignment = {
        **assignment,
        "session_id":
            "test",
        "split":
            "test_normal",
    }

    assignments = [
        assignment,
        train_assignment_a,
        train_assignment_b,
        validation_assignment,
        test_assignment,
    ]

    from desktop.windows.scientific_preflight import (
        compute_split_digest,
    )

    split_digest = (
        compute_split_digest(
            assignments
        )
    )

    plan = {
        "status":
            "ready",
        "assignments":
            assignments,
        "split_digest":
            split_digest,
    }

    plan_path = (
        root
        / "session_split_plan.json"
    )

    plan_path.write_text(
        json.dumps(
            plan,
            indent=2,
        ),
        encoding="utf-8",
    )

    plan_sha = hashlib.sha256(
        plan_path.read_bytes()
    ).hexdigest()

    freeze = {
        "status":
            "frozen",
        "split_digest":
            split_digest,
        "split_plan_file_sha256":
            plan_sha,
    }

    freeze_path = (
        root
        / "scientific_freeze.json"
    )

    freeze_path.write_text(
        json.dumps(
            freeze,
            indent=2,
        ),
        encoding="utf-8",
    )

    freeze_sha = hashlib.sha256(
        freeze_path.read_bytes()
    ).hexdigest()

    reference = {
        "status":
            "frozen",
        "split_digest":
            split_digest,
    }

    reference_path = (
        root
        / "desktop_normal_reference.json"
    )

    reference_path.write_text(
        json.dumps(
            reference,
            indent=2,
        ),
        encoding="utf-8",
    )

    reference_sha = hashlib.sha256(
        reference_path.read_bytes()
    ).hexdigest()

    (
        root
        / "preparation_manifest.json"
    ).write_text(
        json.dumps({
            "status":
                "reference_and_features_ready_no_model_training",
            "reference_built":
                True,
            "desktop_features_built":
                True,
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
            "reference_file_sha256":
                reference_sha,
        }),
        encoding="utf-8",
    )

    payloads = {
        "model_train": pd.DataFrame({
            "source_dataset": [
                "own_windows"
            ] * 4,
            "session_id": [
                "train-a",
                "train-a",
                "train-b",
                "train-b",
            ],
            "ssid_bssid_count": [
                1,
                2,
                1,
                2,
            ],
            "bssid_changed": [
                0,
                0,
                0,
                0,
            ],
            "security_changed": [
                0,
                0,
                0,
                0,
            ],
            "security_strength_delta": [
                0,
                0,
                0,
                0,
            ],
            "context_available": [
                True
            ] * 4,
            "feature_complete": [
                True
            ] * 4,
            "label": [
                0
            ] * 4,
        }),
        "validation": pd.DataFrame({
            "source_dataset": [
                "own_windows"
            ] * 2,
            "session_id": [
                "validation",
                "validation",
            ],
            "ssid_bssid_count": [
                100,
                100,
            ],
            "bssid_changed": [
                1,
                1,
            ],
            "security_changed": [
                1,
                1,
            ],
            "security_strength_delta": [
                -3,
                -3,
            ],
            "context_available": [
                True,
                True,
            ],
            "feature_complete": [
                True,
                True,
            ],
            "label": [
                0,
                0,
            ],
        }),
        "test_normal": pd.DataFrame({
            "source_dataset": [
                "own_windows"
            ],
            "session_id": [
                "test"
            ],
            "ssid_bssid_count": [
                1
            ],
            "bssid_changed": [
                0
            ],
            "security_changed": [
                0
            ],
            "security_strength_delta": [
                0
            ],
            "context_available": [
                True
            ],
            "feature_complete": [
                True
            ],
            "label": [
                0
            ],
        }),
    }

    for split, frame in payloads.items():
        folder = (
            root
            / split
        )

        folder.mkdir(
            parents=True
        )

        frame.to_csv(
            folder
            / "desktop_features_eligible.csv.gz",
            index=False,
            compression="gzip",
        )


def test_prepare_ml_blocked_when_reference_not_ready(
    tmp_path,
):
    prepared = (
        tmp_path
        / "prepared"
    )

    prepared.mkdir()

    (
        prepared
        / "preparation_manifest.json"
    ).write_text(
        json.dumps({
            "status":
                "blocked_insufficient_real_sessions",
            "reference_built":
                False,
            "desktop_features_built":
                False,
        }),
        encoding="utf-8",
    )

    result = prepare_desktop_ml(
        prepared,
        tmp_path
        / "ml",
        tmp_path
        / "scaled",
        tmp_path
        / "models",
    )

    assert result[
        "status"
    ] == "blocked_reference_not_ready"

    assert result[
        "scaler_fitted"
    ] is False

    assert result[
        "model_trained"
    ] is False


def test_scaler_fits_model_train_only(
    tmp_path,
):
    prepared = (
        tmp_path
        / "prepared"
    )

    _write_prepared_dataset(
        prepared
    )

    ml = (
        tmp_path
        / "ml"
    )

    scaled = (
        tmp_path
        / "scaled"
    )

    models = (
        tmp_path
        / "models"
    )

    result = prepare_desktop_ml(
        prepared,
        ml,
        scaled,
        models,
    )

    assert result[
        "status"
    ] == "ml_ready_and_scaler_ready_model_not_trained"

    assert result[
        "model_trained"
    ] is False

    assert result[
        "threshold_calibrated"
    ] is False

    scaler = joblib.load(
        models
        / "desktop_candidate_v1_standard_scaler.joblib"
    )

    # model_train ssid_bssid_count is [1,2,1,2], mean = 1.5.
    # Validation has absurd 100s precisely to verify it did NOT affect fit.
    assert scaler.mean_[
        0
    ] == 1.5

    assert list(
        pd.read_csv(
            ml
            / "model_train"
            / "X.csv.gz"
        ).columns
    ) == DESKTOP_FEATURES

    scaled_train = pd.read_csv(
        scaled
        / "model_train"
        / "X.csv.gz"
    )

    assert abs(
        scaled_train[
            "ssid_bssid_count"
        ].mean()
    ) < 1e-12


def test_constant_event_features_preserved(
    tmp_path,
):
    prepared = (
        tmp_path
        / "prepared"
    )

    _write_prepared_dataset(
        prepared
    )

    result = prepare_desktop_ml(
        prepared,
        tmp_path
        / "ml",
        tmp_path
        / "scaled",
        tmp_path
        / "models",
    )

    variance = result[
        "train_variance"
    ]

    assert variance[
        "bssid_changed"
    ][
        "unique"
    ] == 1

    assert variance[
        "security_changed"
    ][
        "unique"
    ] == 1

    # Semantics are preserved rather than auto-dropping event dimensions.
    assert "bssid_changed" in result[
        "features"
    ]

    assert "security_changed" in result[
        "features"
    ]


def test_ml_ready_output_is_create_only(
    tmp_path,
):
    prepared = (
        tmp_path
        / "prepared"
    )

    _write_prepared_dataset(
        prepared
    )

    ml = tmp_path / "ml"
    scaled = tmp_path / "scaled"
    models = tmp_path / "models"

    prepare_desktop_ml(
        prepared,
        ml,
        scaled,
        models,
    )

    try:
        prepare_desktop_ml(
            prepared,
            ml,
            scaled,
            models,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "ML-ready root deveria ser create-only."
        )
