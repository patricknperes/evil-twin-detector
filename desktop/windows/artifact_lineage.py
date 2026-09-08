from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "desktop_artifact_lineage_v1"

SCIENTIFIC_IDENTITY_FIELDS = (
    "split_digest",
    "scientific_freeze_sha256",
    "reference_file_sha256",
)

DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]

SCALED_SPLITS = (
    "model_train",
    "validation",
    "test_normal",
)

SCALED_FILES = (
    "X.csv.gz",
    "y.csv.gz",
    "metadata.csv.gz",
)

HASH_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(
        path
    ).open(
        "rb"
    ) as handle:
        for block in iter(
            lambda:
                handle.read(
                    1024
                    * 1024
                ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def _read_json(
    path: str | Path,
) -> dict[str, Any]:
    return json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8"
        )
    )


def _valid_sha256(
    value: object,
) -> bool:
    return bool(
        isinstance(
            value,
            str,
        )
        and HASH_RE.fullmatch(
            value
        )
    )


def scientific_identity(
    mapping: dict[str, Any],
    *,
    source: str,
) -> dict[str, str]:
    identity = {}

    for field in (
        SCIENTIFIC_IDENTITY_FIELDS
    ):
        value = mapping.get(
            field
        )

        if not _valid_sha256(
            value
        ):
            raise ValueError(
                f"{source}: invalid or missing {field}."
            )

        identity[
            field
        ] = str(
            value
        )

    return identity


def _same_identity(
    left: dict[str, str],
    right: dict[str, str],
) -> list[str]:
    return [
        field
        for field
        in SCIENTIFIC_IDENTITY_FIELDS
        if left[
            field
        ]
        != right[
            field
        ]
    ]


def write_scaled_artifact_lineage(
    *,
    scaled_root: str | Path,
    scaler_path: str | Path,
    scaler_metadata_path: str | Path,
    identity: dict[str, str],
    features: list[str] | None = None,
) -> dict[str, Any]:
    root = Path(
        scaled_root
    )

    scaler = Path(
        scaler_path
    )

    scaler_metadata = Path(
        scaler_metadata_path
    )

    if not scaler.exists():
        raise FileNotFoundError(
            "Scaler artifact does not exist."
        )

    if not scaler_metadata.exists():
        raise FileNotFoundError(
            "Scaler metadata does not exist."
        )

    normalized_identity = (
        scientific_identity(
            identity,
            source=(
                "scaled_artifact_lineage"
            ),
        )
    )

    split_hashes: dict[
        str,
        dict[str, str],
    ] = {}

    for split in (
        SCALED_SPLITS
    ):
        split_hashes[
            split
        ] = {}

        for filename in (
            SCALED_FILES
        ):
            path = (
                root
                / split
                / filename
            )

            if not path.exists():
                raise FileNotFoundError(
                    f"Scaled lineage source missing: {path}"
                )

            split_hashes[
                split
            ][
                filename
            ] = sha256_file(
                path
            )

    payload = {
        "schema_version":
            SCHEMA_VERSION,
        "feature_set_name":
            "desktop_candidate_v1",
        "features":
            list(
                features
                or DESKTOP_FEATURES
            ),
        **normalized_identity,
        "scaler_file_sha256":
            sha256_file(
                scaler
            ),
        "scaler_metadata_file_sha256":
            sha256_file(
                scaler_metadata
            ),
        "scaled_split_hashes":
            split_hashes,
    }

    path = (
        root
        / "artifact_lineage.json"
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        **payload,
        "artifact_lineage_file_sha256":
            sha256_file(
                path
            ),
    }


def validate_scaled_artifact_lineage(
    scaled_root: str | Path,
) -> dict[str, Any]:
    root = Path(
        scaled_root
    )

    lineage_path = (
        root
        / "artifact_lineage.json"
    )

    if not lineage_path.exists():
        return {
            "ready":
                False,
            "status":
                "blocked_artifact_lineage_missing",
            "errors": [
                "artifact_lineage.json_missing"
            ],
        }

    try:
        payload = _read_json(
            lineage_path
        )
    except Exception as exc:
        return {
            "ready":
                False,
            "status":
                "blocked_artifact_lineage_invalid",
            "errors": [
                "artifact_lineage_json_invalid"
            ],
            "reason":
                str(
                    exc
                ),
        }

    errors: list[str] = []

    if (
        payload.get(
            "schema_version"
        )
        != SCHEMA_VERSION
    ):
        errors.append(
            "artifact_lineage_schema_invalid"
        )

    if (
        payload.get(
            "feature_set_name"
        )
        != "desktop_candidate_v1"
    ):
        errors.append(
            "feature_set_name_invalid"
        )

    if list(
        payload.get(
            "features"
        )
        or []
    ) != DESKTOP_FEATURES:
        errors.append(
            "feature_order_invalid"
        )

    try:
        identity = scientific_identity(
            payload,
            source=(
                "artifact_lineage"
            ),
        )
    except ValueError as exc:
        identity = None
        errors.append(
            str(
                exc
            )
        )

    for field in (
        "scaler_file_sha256",
        "scaler_metadata_file_sha256",
    ):
        if not _valid_sha256(
            payload.get(
                field
            )
        ):
            errors.append(
                f"{field}_invalid"
            )

    expected_hashes = (
        payload.get(
            "scaled_split_hashes"
        )
        or {}
    )

    for split in (
        SCALED_SPLITS
    ):
        split_expected = (
            expected_hashes.get(
                split
            )
            or {}
        )

        for filename in (
            SCALED_FILES
        ):
            path = (
                root
                / split
                / filename
            )

            expected = (
                split_expected.get(
                    filename
                )
            )

            if not path.exists():
                errors.append(
                    f"{split}/{filename}_missing"
                )
                continue

            if not _valid_sha256(
                expected
            ):
                errors.append(
                    f"{split}/{filename}_hash_missing"
                )
                continue

            actual = sha256_file(
                path
            )

            if actual != expected:
                errors.append(
                    f"{split}/{filename}_hash_mismatch"
                )

    if errors:
        return {
            "ready":
                False,
            "status":
                "blocked_artifact_lineage_mismatch",
            "errors":
                sorted(
                    set(
                        errors
                    )
                ),
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "identity":
            identity,
        "lineage":
            payload,
        "artifact_lineage_file_sha256":
            sha256_file(
                lineage_path
            ),
        "errors":
            [],
    }


def validate_runtime_artifact_chain(
    *,
    reference_path: str | Path,
    scaler_path: str | Path,
    model_path: str | Path,
    threshold_path: str | Path,
) -> dict[str, Any]:
    paths = {
        "reference":
            Path(
                reference_path
            ),
        "scaler":
            Path(
                scaler_path
            ),
        "model":
            Path(
                model_path
            ),
        "threshold":
            Path(
                threshold_path
            ),
    }

    missing = [
        name
        for name, path
        in paths.items()
        if not path.exists()
    ]

    if missing:
        return {
            "ready":
                False,
            "status":
                "blocked_artifacts_missing",
            "missing":
                missing,
            "errors":
                [],
        }

    try:
        reference = _read_json(
            paths[
                "reference"
            ]
        )

        threshold = _read_json(
            paths[
                "threshold"
            ]
        )
    except Exception as exc:
        return {
            "ready":
                False,
            "status":
                "blocked_artifact_chain_invalid",
            "missing":
                [],
            "errors": [
                "json_metadata_invalid"
            ],
            "reason":
                str(
                    exc
                ),
        }

    errors: list[str] = []

    if (
        reference.get(
            "schema_version"
        )
        != "desktop_normal_reference_v1"
    ):
        errors.append(
            "reference_schema_invalid"
        )

    if (
        threshold.get(
            "schema_version"
        )
        != "desktop_threshold_v2"
    ):
        errors.append(
            "threshold_schema_invalid"
        )

    if (
        threshold.get(
            "feature_set_name"
        )
        != "desktop_candidate_v1"
    ):
        errors.append(
            "threshold_feature_set_name_invalid"
        )

    if list(
        threshold.get(
            "features"
        )
        or []
    ) != DESKTOP_FEATURES:
        errors.append(
            "threshold_feature_order_invalid"
        )

    if bool(
        threshold.get(
            "attack_used_for_calibration",
            True,
        )
    ):
        errors.append(
            "threshold_attack_used_for_calibration"
        )

    if (
        threshold.get(
            "source_split"
        )
        != "validation"
    ):
        errors.append(
            "threshold_source_split_invalid"
        )

    if (
        threshold.get(
            "source_label"
        )
        != "normal_only"
    ):
        errors.append(
            "threshold_source_label_invalid"
        )

    reference_identity = {}

    for field in (
        "split_digest",
        "scientific_freeze_sha256",
    ):
        value = reference.get(
            field
        )

        if not _valid_sha256(
            value
        ):
            errors.append(
                f"reference:{field}_invalid_or_missing"
            )
        else:
            reference_identity[
                field
            ] = str(
                value
            )

    try:
        threshold_identity = (
            scientific_identity(
                threshold,
                source=(
                    "threshold"
                ),
            )
        )
    except ValueError as exc:
        threshold_identity = None
        errors.append(
            str(
                exc
            )
        )

    if threshold_identity:
        for field in (
            "split_digest",
            "scientific_freeze_sha256",
        ):
            if (
                reference_identity.get(
                    field
                )
                != threshold_identity[
                    field
                ]
            ):
                errors.append(
                    f"scientific_identity_mismatch:{field}"
                )

    actual_hashes = {
        name:
            sha256_file(
                path
            )
        for name, path
        in paths.items()
    }

    expected_hash_fields = {
        "reference":
            "reference_file_sha256",
        "scaler":
            "scaler_file_sha256",
        "model":
            "model_file_sha256",
    }

    for artifact, field in (
        expected_hash_fields.items()
    ):
        expected = threshold.get(
            field
        )

        if not _valid_sha256(
            expected
        ):
            errors.append(
                f"{field}_invalid"
            )
            continue

        if (
            actual_hashes[
                artifact
            ]
            != expected
        ):
            errors.append(
                f"{artifact}_file_sha256_mismatch"
            )

    artifact_lineage_sha = threshold.get(
        "artifact_lineage_file_sha256"
    )

    if not _valid_sha256(
        artifact_lineage_sha
    ):
        errors.append(
            "artifact_lineage_file_sha256_invalid"
        )

    if errors:
        return {
            "ready":
                False,
            "status":
                "blocked_artifact_chain_mismatch",
            "missing":
                [],
            "errors":
                sorted(
                    set(
                        errors
                    )
                ),
            "actual_hashes":
                actual_hashes,
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "missing":
            [],
        "errors":
            [],
        "identity":
            threshold_identity,
        "actual_hashes":
            actual_hashes,
        "artifact_lineage_file_sha256":
            str(
                artifact_lineage_sha
            ),
        "threshold":
            threshold,
        "reference":
            reference,
    }
