from __future__ import annotations

import hashlib
import json

from backend.model_status import (
    ModelArtifactStatusService,
)
from desktop.windows.artifact_lineage import (
    sha256_file,
    validate_runtime_artifact_chain,
)


FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]


def _write_runtime_bundle(
    root,
):
    reference = (
        root
        / "data/processed/desktop_candidate_v1/"
        "desktop_normal_reference.json"
    )

    scaler = (
        root
        / "ml/models/preprocessing/"
        "desktop_candidate_v1_standard_scaler.joblib"
    )

    model = (
        root
        / "ml/models/desktop_candidate_v1/ocsvm_v1/"
        "one_class_svm_desktop_candidate_v1.joblib"
    )

    threshold = (
        root
        / "ml/models/desktop_candidate_v1/ocsvm_v1/"
        "threshold.json"
    )

    for path in (
        reference,
        scaler,
        model,
        threshold,
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    reference.write_text(
        json.dumps({
            "schema_version":
                "desktop_normal_reference_v1",
            "status":
                "frozen",
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
        }),
        encoding="utf-8",
    )

    scaler.write_bytes(
        b"software-scaler"
    )

    model.write_bytes(
        b"software-model"
    )

    threshold.write_text(
        json.dumps({
            "schema_version":
                "desktop_threshold_v2",
            "feature_set_name":
                "desktop_candidate_v1",
            "features":
                FEATURES,
            "source_split":
                "validation",
            "source_label":
                "normal_only",
            "threshold":
                0.25,
            "attack_used_for_calibration":
                False,
            "split_digest":
                "a"
                * 64,
            "scientific_freeze_sha256":
                "b"
                * 64,
            "reference_file_sha256":
                sha256_file(
                    reference
                ),
            "scaler_file_sha256":
                sha256_file(
                    scaler
                ),
            "model_file_sha256":
                sha256_file(
                    model
                ),
            "artifact_lineage_file_sha256":
                "c"
                * 64,
        }),
        encoding="utf-8",
    )

    return {
        "reference":
            reference,
        "scaler":
            scaler,
        "model":
            model,
        "threshold":
            threshold,
    }


def test_runtime_chain_accepts_one_consistent_freeze(
    tmp_path,
):
    paths = _write_runtime_bundle(
        tmp_path
    )

    result = (
        validate_runtime_artifact_chain(
            reference_path=(
                paths[
                    "reference"
                ]
            ),
            scaler_path=(
                paths[
                    "scaler"
                ]
            ),
            model_path=(
                paths[
                    "model"
                ]
            ),
            threshold_path=(
                paths[
                    "threshold"
                ]
            ),
        )
    )

    assert (
        result[
            "ready"
        ]
        is True
    )

    assert (
        result[
            "identity"
        ][
            "split_digest"
        ]
        == "a"
        * 64
    )


def test_runtime_chain_rejects_model_binary_from_another_bundle(
    tmp_path,
):
    paths = _write_runtime_bundle(
        tmp_path
    )

    paths[
        "model"
    ].write_bytes(
        b"different-model-binary"
    )

    result = (
        validate_runtime_artifact_chain(
            reference_path=(
                paths[
                    "reference"
                ]
            ),
            scaler_path=(
                paths[
                    "scaler"
                ]
            ),
            model_path=(
                paths[
                    "model"
                ]
            ),
            threshold_path=(
                paths[
                    "threshold"
                ]
            ),
        )
    )

    assert (
        result[
            "ready"
        ]
        is False
    )

    assert (
        result[
            "status"
        ]
        == "blocked_artifact_chain_mismatch"
    )

    assert (
        "model_file_sha256_mismatch"
        in result[
            "errors"
        ]
    )


def test_runtime_chain_rejects_threshold_from_different_split_digest(
    tmp_path,
):
    paths = _write_runtime_bundle(
        tmp_path
    )

    threshold = json.loads(
        paths[
            "threshold"
        ].read_text(
            encoding="utf-8"
        )
    )

    threshold[
        "split_digest"
    ] = (
        "d"
        * 64
    )

    paths[
        "threshold"
    ].write_text(
        json.dumps(
            threshold
        ),
        encoding="utf-8",
    )

    result = (
        validate_runtime_artifact_chain(
            reference_path=(
                paths[
                    "reference"
                ]
            ),
            scaler_path=(
                paths[
                    "scaler"
                ]
            ),
            model_path=(
                paths[
                    "model"
                ]
            ),
            threshold_path=(
                paths[
                    "threshold"
                ]
            ),
        )
    )

    assert (
        result[
            "ready"
        ]
        is False
    )

    assert (
        "scientific_identity_mismatch:split_digest"
        in result[
            "errors"
        ]
    )


def test_model_status_distinguishes_present_files_from_valid_lineage(
    tmp_path,
):
    paths = _write_runtime_bundle(
        tmp_path
    )

    service = (
        ModelArtifactStatusService(
            project_root=(
                tmp_path
            )
        )
    )

    assert (
        service
        .get_status()
        .status
        == "ready"
    )

    paths[
        "scaler"
    ].write_bytes(
        b"mixed-scaler"
    )

    status = (
        service
        .get_status()
    )

    assert (
        status.status
        == "not_ready"
    )

    assert (
        "artifact_lineage_integrity"
        in status
        .missing_artifacts
    )

    assert (
        "scientific lineage"
        in status.message
    )


def test_threshold_hash_does_not_need_self_reference(
    tmp_path,
):
    paths = _write_runtime_bundle(
        tmp_path
    )

    payload = json.loads(
        paths[
            "threshold"
        ].read_text(
            encoding="utf-8"
        )
    )

    assert (
        "threshold_file_sha256"
        not in payload
    )

    assert len(
        hashlib.sha256(
            paths[
                "threshold"
            ].read_bytes()
        ).hexdigest()
    ) == 64
