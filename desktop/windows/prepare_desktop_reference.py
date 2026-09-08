from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .desktop_reference import (
    DESKTOP_FEATURES,
    build_desktop_reference,
    save_reference,
    transform_desktop_features,
)
from .scientific_preflight import (
    ScientificIntegrityError,
    freeze_or_validate_split_plan,
    run_scientific_preflight,
    save_preflight_report,
    sha256_file,
)


def prepare_desktop_reference(
    interim_root: str | Path,
    output_root: str | Path,
    *,
    seed: int = 20260831,
) -> dict[str, object]:
    output_root = Path(
        output_root
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    preflight = (
        run_scientific_preflight(
            interim_root
        )
    )

    save_preflight_report(
        preflight,
        output_root
        / "scientific_preflight.json",
    )

    if (
        preflight[
            "status"
        ]
        != "ready_for_split_freeze"
    ):
        # A previously frozen plan is still allowed to validate if the only
        # difference is that additional valid sessions appeared later.
        existing_plan_path = (
            output_root
            / "session_split_plan.json"
        )

        existing_plan_ready = False

        if existing_plan_path.exists():
            try:
                existing_plan_ready = (
                    json.loads(
                        existing_plan_path
                        .read_text(
                            encoding="utf-8"
                        )
                    ).get(
                        "status"
                    )
                    == "ready"
                )
            except Exception:
                existing_plan_ready = False

        if not existing_plan_ready:
            from .desktop_split_plan import (
                make_split_plan,
                save_split_plan,
            )

            blocked_plan = (
                make_split_plan(
                    preflight[
                        "_sessions_for_split"
                    ],
                    seed=seed,
                )
            )

            blocked_plan[
                "schema_version"
            ] = (
                "desktop_session_split_plan_v2"
            )

            blocked_plan[
                "integrity_gate"
            ] = (
                "desktop_scientific_preflight_v1"
            )

            save_split_plan(
                blocked_plan,
                existing_plan_path,
            )

            result = {
                "schema_version":
                    "desktop_reference_preparation_v2",
                "status":
                    preflight[
                        "status"
                    ],
                "valid_sessions":
                    int(
                        preflight[
                            "valid_session_count"
                        ]
                    ),
                "minimum_required_sessions":
                    int(
                        preflight[
                            "minimum_required_sessions"
                        ]
                    ),
                "reference_built":
                    False,
                "desktop_features_built":
                    False,
                "model_training_started":
                    False,
                "scientific_preflight":
                    preflight[
                        "status"
                    ],
            }

            (
                output_root
                / "preparation_manifest.json"
            ).write_text(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            return result

    freeze_result = (
        freeze_or_validate_split_plan(
            preflight[
                "_sessions_for_split"
            ],
            output_root
            / "session_split_plan.json",
            output_root
            / "scientific_freeze.json",
            seed=seed,
        )
    )

    assignments = (
        freeze_result[
            "assignments"
        ]
    )

    frames = {}

    for assignment in assignments:
        session_id = str(
            assignment[
                "session_id"
            ]
        )

        frame = pd.read_csv(
            assignment[
                "observations_path"
            ]
        )

        frame[
            "_split"
        ] = assignment[
            "split"
        ]

        frames[
            session_id
        ] = frame

    reference_parts = [
        frame
        for frame in frames.values()
        if (
            frame[
                "_split"
            ].iloc[
                0
            ]
            == "reference"
        )
    ]

    reference_frame = pd.concat(
        reference_parts,
        ignore_index=True,
    )

    reference = build_desktop_reference(
        reference_frame
    )

    cohort_environments = sorted({
        str(
            item.get(
                "environment"
            )
        )
        for item
        in assignments
        if item.get(
            "environment"
        )
    })

    reference[
        "normal_cohort_environments"
    ] = cohort_environments

    reference[
        "normal_cohort_environment"
    ] = (
        cohort_environments[
            0
        ]
        if len(
            cohort_environments
        )
        == 1
        else None
    )

    reference[
        "reference_session_ids"
    ] = [
        item[
            "session_id"
        ]
        for item in assignments
        if item[
            "split"
        ] == "reference"
    ]

    reference[
        "reference_source_hashes"
    ] = {
        str(
            item[
                "session_id"
            ]
        ): {
            "source_scans_sha256":
                item[
                    "source_scans_sha256"
                ],
            "observations_sha256":
                item[
                    "observations_sha256"
                ],
            "content_fingerprint":
                item[
                    "content_fingerprint"
                ],
        }
        for item in assignments
        if item[
            "split"
        ] == "reference"
    }

    reference[
        "split_digest"
    ] = (
        freeze_result[
            "split_digest"
        ]
    )

    reference[
        "scientific_freeze_sha256"
    ] = (
        freeze_result[
            "scientific_freeze_sha256"
        ]
    )

    reference_path = (
        output_root
        / "desktop_normal_reference.json"
    )

    save_reference(
        reference,
        reference_path,
    )

    reference_file_sha256 = (
        sha256_file(
            reference_path
        )
    )

    coverage = {}

    for split in (
        "model_train",
        "validation",
        "test_normal",
    ):
        parts = [
            frame
            for frame in frames.values()
            if (
                frame[
                    "_split"
                ].iloc[
                    0
                ]
                == split
            )
        ]

        if not parts:
            continue

        source = pd.concat(
            parts,
            ignore_index=True,
        )

        features = (
            transform_desktop_features(
                source,
                reference,
            )
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
            "label",
            "attack_type",
            "is_synthetic",
        ]

        metadata = source[
            [
                column
                for column
                in metadata_columns
                if column
                in source.columns
            ]
        ].reset_index(
            drop=True
        )

        combined = pd.concat(
            [
                metadata,
                features.reset_index(
                    drop=True
                ),
            ],
            axis=1,
        )

        split_dir = (
            output_root
            / split
        )

        split_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        combined.to_csv(
            split_dir
            / "desktop_features_all.csv.gz",
            index=False,
            compression="gzip",
        )

        eligible = combined[
            combined[
                "context_available"
            ].astype(
                bool
            )
            & combined[
                "feature_complete"
            ].astype(
                bool
            )
        ].copy()

        eligible.to_csv(
            split_dir
            / "desktop_features_eligible.csv.gz",
            index=False,
            compression="gzip",
        )

        coverage[
            split
        ] = {
            "rows":
                int(
                    len(
                        combined
                    )
                ),
            "eligible":
                int(
                    len(
                        eligible
                    )
                ),
            "eligible_rate":
                float(
                    len(
                        eligible
                    )
                    / len(
                        combined
                    )
                )
                if len(
                    combined
                )
                else 0.0,
            "context_unavailable":
                int(
                    (
                        ~combined[
                            "context_available"
                        ].astype(
                            bool
                        )
                    ).sum()
                ),
        }

    result = {
        "schema_version":
            "desktop_reference_preparation_v2",
        "status":
            "reference_and_features_ready_no_model_training",
        "reference_built":
            True,
        "desktop_features_built":
            True,
        "model_training_started":
            False,
        "desktop_features":
            DESKTOP_FEATURES,
        "reference_session_ids":
            reference[
                "reference_session_ids"
            ],
        "ssid_profile_count":
            reference[
                "ssid_profile_count"
            ],
        "normal_cohort_environment":
            reference[
                "normal_cohort_environment"
            ],
        "normal_cohort_environments":
            reference[
                "normal_cohort_environments"
            ],
        "split_digest":
            freeze_result[
                "split_digest"
            ],
        "split_plan_file_sha256":
            freeze_result[
                "split_plan_file_sha256"
            ],
        "scientific_freeze_sha256":
            freeze_result[
                "scientific_freeze_sha256"
            ],
        "reference_file_sha256":
            reference_file_sha256,
        "reference_source_hashes":
            reference[
                "reference_source_hashes"
            ],
        "unassigned_sessions_after_freeze":
            freeze_result[
                "unassigned_sessions_after_freeze"
            ],
        "new_freeze_created":
            freeze_result[
                "new_freeze_created"
            ],
        "coverage":
            coverage,
        "scientific_rules": [
            "Reference split only builds the historical reference.",
            "Reference observations are excluded from anomaly-model training.",
            "Validation/test do not update reference.",
            "Unknown context stays unknown rather than becoming attack.",
            "No model/scaler/threshold created in this step.",
            "Frozen source hashes must remain unchanged after split freeze.",
            "New sessions after freeze are not silently assigned.",
        ],
    }

    (
        output_root
        / "preparation_manifest.json"
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
            "Planeja split por sessão, congela referência desktop e "
            "deriva features, sem treinar modelo."
        )
    )

    parser.add_argument(
        "--interim-root",
        default=(
            "data/interim/own/windows"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/processed/desktop_candidate_v1"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=20260831,
    )

    args = parser.parse_args(
        argv
    )

    result = prepare_desktop_reference(
        args.interim_root,
        args.output_root,
        seed=args.seed,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        8
        if str(
            result[
                "status"
            ]
        ).startswith(
            "blocked_"
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
