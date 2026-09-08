from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from .artifact_lineage import (
    sha256_file,
    write_scaled_artifact_lineage,
)
from .scientific_preflight import (
    verify_prepared_freeze_integrity,
)


DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]

SPLITS = [
    "model_train",
    "validation",
    "test_normal",
]

METADATA_COLUMNS = [
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
    "context_ssid_hash",
    "context_resolution",
    "context_available",
    "feature_complete",
    "label",
    "attack_type",
    "is_synthetic",
]


def _read_json(
    path: Path,
) -> dict[str, object]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _ensure_reference_ready(
    prepared_root: Path,
) -> dict[str, object]:
    manifest_path = (
        prepared_root
        / "preparation_manifest.json"
    )

    if not manifest_path.exists():
        return {
            "ready":
                False,
            "status":
                "blocked_reference_not_prepared",
            "reason": (
                "preparation_manifest.json does not exist. "
                "Run desktop.windows.prepare_desktop_reference first."
            ),
        }

    manifest = _read_json(
        manifest_path
    )

    if (
        manifest.get(
            "status"
        )
        != "reference_and_features_ready_no_model_training"
    ):
        return {
            "ready":
                False,
            "status":
                "blocked_reference_not_ready",
            "reason": (
                "Frozen reference/features are not ready. "
                f"Current status: {manifest.get('status')}"
            ),
            "reference_manifest":
                manifest,
        }

    if not bool(
        manifest.get(
            "reference_built",
            False,
        )
    ):
        return {
            "ready":
                False,
            "status":
                "blocked_reference_not_ready",
            "reason":
                "Reference manifest says reference_built=false.",
            "reference_manifest":
                manifest,
        }

    if not bool(
        manifest.get(
            "desktop_features_built",
            False,
        )
    ):
        return {
            "ready":
                False,
            "status":
                "blocked_features_not_ready",
            "reason":
                "Reference is present but desktop features were not built.",
            "reference_manifest":
                manifest,
        }

    integrity = (
        verify_prepared_freeze_integrity(
            prepared_root
        )
    )

    if not integrity[
        "ready"
    ]:
        return {
            "ready":
                False,
            "status":
                integrity[
                    "status"
                ],
            "reason": (
                "Scientific split/reference freeze integrity is not valid."
            ),
            "integrity":
                integrity,
            "reference_manifest":
                manifest,
        }

    return {
        "ready":
            True,
        "status":
            "ready",
        "reference_manifest":
            manifest,
        "integrity":
            integrity,
    }


def _load_split(
    prepared_root: Path,
    split: str,
) -> pd.DataFrame:
    path = (
        prepared_root
        / split
        / "desktop_features_eligible.csv.gz"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"{split}: arquivo elegível não encontrado: {path}"
        )

    frame = pd.read_csv(
        path
    )

    if frame.empty:
        raise ValueError(
            f"{split}: nenhuma observação elegível."
        )

    missing = [
        feature
        for feature in DESKTOP_FEATURES
        if feature not in frame.columns
    ]

    if missing:
        raise ValueError(
            f"{split}: features ausentes: "
            + ", ".join(
                missing
            )
        )

    return frame


def _make_bundle(
    frame: pd.DataFrame,
):
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
            "X contém NaN após filtragem eligible."
        )

    if "label" in frame.columns:
        y = pd.to_numeric(
            frame[
                "label"
            ],
            errors="raise",
        ).astype(
            int
        )
    else:
        y = pd.Series(
            np.zeros(
                len(
                    frame
                ),
                dtype=int,
            ),
            name="label",
        )

    if not (
        y
        == 0
    ).all():
        raise ValueError(
            "Desktop normal preparation recebeu label diferente de zero."
        )

    metadata = frame[
        [
            column
            for column in METADATA_COLUMNS
            if column in frame.columns
        ]
    ].copy()

    return (
        X,
        y.rename(
            "label"
        ),
        metadata,
    )


def prepare_desktop_ml(
    prepared_root: str | Path,
    ml_ready_root: str | Path,
    scaled_root: str | Path,
    preprocessing_model_dir: str | Path,
) -> dict[str, object]:
    prepared_root = Path(
        prepared_root
    )

    gate = _ensure_reference_ready(
        prepared_root
    )

    if not gate[
        "ready"
    ]:
        return {
            "schema_version":
                "desktop_candidate_v1_ml_preparation_v2",
            "status":
                gate[
                    "status"
                ],
            "reason":
                gate[
                    "reason"
                ],
            "ml_matrices_created":
                False,
            "scaler_fitted":
                False,
            "model_trained":
                False,
            "threshold_calibrated":
                False,
        }

    ml_ready_root = Path(
        ml_ready_root
    )

    scaled_root = Path(
        scaled_root
    )

    preprocessing_model_dir = Path(
        preprocessing_model_dir
    )

    # Create-only roots. This prevents silently mixing matrices from
    # different frozen split/reference plans.
    ml_ready_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    scaled_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    preprocessing_model_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    bundles = {}

    raw_frames = {}

    for split in SPLITS:
        frame = _load_split(
            prepared_root,
            split,
        )

        X, y, metadata = (
            _make_bundle(
                frame
            )
        )

        split_dir = (
            ml_ready_root
            / split
        )

        split_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        X.to_csv(
            split_dir
            / "X.csv.gz",
            index=False,
            compression="gzip",
        )

        y.to_frame().to_csv(
            split_dir
            / "y.csv.gz",
            index=False,
            compression="gzip",
        )

        metadata.to_csv(
            split_dir
            / "metadata.csv.gz",
            index=False,
            compression="gzip",
        )

        raw_frames[
            split
        ] = X

        bundles[
            split
        ] = {
            "rows":
                int(
                    len(
                        X
                    )
                ),
            "features":
                list(
                    X.columns
                ),
            "session_count":
                int(
                    metadata[
                        "session_id"
                    ].nunique()
                )
                if "session_id"
                in metadata.columns
                else None,
        }

    train_X = raw_frames[
        "model_train"
    ]

    # Train-only variance/constancy diagnostic. No feature is removed here.
    variance = {
        feature: {
            "unique":
                int(
                    train_X[
                        feature
                    ].nunique(
                        dropna=True
                    )
                ),
            "mean":
                float(
                    train_X[
                        feature
                    ].mean()
                ),
            "variance_population":
                float(
                    train_X[
                        feature
                    ].var(
                        ddof=0
                    )
                ),
        }
        for feature in DESKTOP_FEATURES
    }

    scaler = StandardScaler()

    scaler.fit(
        train_X[
            DESKTOP_FEATURES
        ]
    )

    scaler_path = (
        preprocessing_model_dir
        / "desktop_candidate_v1_standard_scaler.joblib"
    )

    scaler_json_path = (
        preprocessing_model_dir
        / "desktop_candidate_v1_standard_scaler.json"
    )

    joblib.dump(
        scaler,
        scaler_path,
    )

    scaler_metadata = {
        "schema_version":
            "desktop_candidate_v1_scaler_v1",
        "fit_split":
            "model_train",
        "fit_rows":
            int(
                len(
                    train_X
                )
            ),
        "features":
            DESKTOP_FEATURES,
        "reference_used_for_fit":
            False,
        "validation_used_for_fit":
            False,
        "test_used_for_fit":
            False,
        "mean": {
            feature:
                float(
                    value
                )
            for feature, value
            in zip(
                DESKTOP_FEATURES,
                scaler.mean_,
            )
        },
        "scale": {
            feature:
                float(
                    value
                )
            for feature, value
            in zip(
                DESKTOP_FEATURES,
                scaler.scale_,
            )
        },
        "train_variance":
            variance,
        "split_digest":
            gate[
                "integrity"
            ][
                "split_digest"
            ],
        "scientific_freeze_sha256":
            gate[
                "integrity"
            ][
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            gate[
                "integrity"
            ][
                "reference_file_sha256"
            ],
    }

    scaler_json_path.write_text(
        json.dumps(
            scaler_metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    for split in SPLITS:
        X = raw_frames[
            split
        ][
            DESKTOP_FEATURES
        ]

        scaled = pd.DataFrame(
            scaler.transform(
                X
            ),
            columns=DESKTOP_FEATURES,
        )

        split_dir = (
            scaled_root
            / split
        )

        split_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        scaled.to_csv(
            split_dir
            / "X.csv.gz",
            index=False,
            compression="gzip",
        )

        # Copy y/metadata logically, not by filesystem link.
        source_dir = (
            ml_ready_root
            / split
        )

        pd.read_csv(
            source_dir
            / "y.csv.gz"
        ).to_csv(
            split_dir
            / "y.csv.gz",
            index=False,
            compression="gzip",
        )

        pd.read_csv(
            source_dir
            / "metadata.csv.gz"
        ).to_csv(
            split_dir
            / "metadata.csv.gz",
            index=False,
            compression="gzip",
        )

    artifact_lineage = (
        write_scaled_artifact_lineage(
            scaled_root=(
                scaled_root
            ),
            scaler_path=(
                scaler_path
            ),
            scaler_metadata_path=(
                scaler_json_path
            ),
            identity={
                "split_digest":
                    gate[
                        "integrity"
                    ][
                        "split_digest"
                    ],
                "scientific_freeze_sha256":
                    gate[
                        "integrity"
                    ][
                        "scientific_freeze_sha256"
                    ],
                "reference_file_sha256":
                    gate[
                        "integrity"
                    ][
                        "reference_file_sha256"
                    ],
            },
            features=(
                DESKTOP_FEATURES
            ),
        )
    )

    # Sanity check: train standardized mean approximately zero.
    train_scaled = pd.DataFrame(
        scaler.transform(
            train_X[
                DESKTOP_FEATURES
            ]
        ),
        columns=DESKTOP_FEATURES,
    )

    scaled_train_mean = {
        feature:
            float(
                train_scaled[
                    feature
                ].mean()
            )
        for feature in DESKTOP_FEATURES
    }

    result = {
        "schema_version":
            "desktop_candidate_v1_ml_preparation_v2",
        "status":
            "ml_ready_and_scaler_ready_model_not_trained",
        "ml_matrices_created":
            True,
        "scaler_fitted":
            True,
        "model_trained":
            False,
        "threshold_calibrated":
            False,
        "features":
            DESKTOP_FEATURES,
        "bundles":
            bundles,
        "train_variance":
            variance,
        "scaled_train_mean":
            scaled_train_mean,
        "split_digest":
            gate[
                "integrity"
            ][
                "split_digest"
            ],
        "scientific_freeze_sha256":
            gate[
                "integrity"
            ][
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            gate[
                "integrity"
            ][
                "reference_file_sha256"
            ],
        "scaler_file_sha256":
            artifact_lineage[
                "scaler_file_sha256"
            ],
        "scaler_metadata_file_sha256":
            artifact_lineage[
                "scaler_metadata_file_sha256"
            ],
        "artifact_lineage_file_sha256":
            artifact_lineage[
                "artifact_lineage_file_sha256"
            ],
        "artifact_lineage":
            str(
                scaled_root
                / "artifact_lineage.json"
            ),
        "scaler_artifact":
            str(
                scaler_path
            ),
        "scientific_rules": [
            "Only model_train fits the scaler.",
            "Reference is excluded from X/model training.",
            "Validation/test never fit preprocessing.",
            "No OCSVM is trained in this preparation step.",
            "No threshold is calibrated in this preparation step.",
            "Attack data is not required or consumed here.",
            "Scaled X/y/metadata and scaler hashes are frozen in artifact_lineage.json.",
        ],
    }

    (
        ml_ready_root
        / "ml_preparation_manifest.json"
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
            "Gera matrizes ML e scaler do desktop_candidate_v1 "
            "sem treinar modelo."
        )
    )

    parser.add_argument(
        "--prepared-root",
        default=(
            "data/processed/desktop_candidate_v1"
        ),
    )

    parser.add_argument(
        "--ml-ready-root",
        default=(
            "data/processed/ml_ready/desktop_candidate_v1"
        ),
    )

    parser.add_argument(
        "--scaled-root",
        default=(
            "data/processed/ml_ready/desktop_candidate_v1_scaled"
        ),
    )

    parser.add_argument(
        "--preprocessing-model-dir",
        default=(
            "ml/models/preprocessing"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = prepare_desktop_ml(
        args.prepared_root,
        args.ml_ready_root,
        args.scaled_root,
        args.preprocessing_model_dir,
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
        return 9

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
