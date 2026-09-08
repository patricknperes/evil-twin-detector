from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .artifact_lineage import (
    sha256_file,
)
from .desktop_reference import (
    DESKTOP_FEATURES,
    transform_desktop_features,
)


MIN_ATTACK_ELIGIBLE_RATE = 0.70
MIN_ATTACK_TARGET_ELIGIBLE_RATE = 0.70


def _load_reference(
    path: str | Path,
) -> dict[str, object]:
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Frozen reference ausente: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def discover_attack_interim_sessions(
    interim_root: str | Path,
) -> list[Path]:
    root = Path(
        interim_root
    )

    if not root.exists():
        return []

    return sorted(
        folder
        for folder in root.iterdir()
        if (
            folder.is_dir()
            and (
                folder
                / "observations.csv.gz"
            ).exists()
        )
    )


def prepare_attack_features(
    interim_attack_root: str | Path,
    frozen_reference_path: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    reference_path = Path(
        frozen_reference_path
    )

    sessions = discover_attack_interim_sessions(
        interim_attack_root
    )

    if not reference_path.exists():
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_frozen_reference_missing",
            "attack_sessions":
                len(
                    sessions
                ),
            "features_created":
                False,
            "reason":
                "Real frozen normal desktop reference has not been materialized.",
        }

    if not sessions:
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_attack_data_missing",
            "attack_sessions":
                0,
            "features_created":
                False,
            "reason":
                "No real controlled attack session has been imported.",
        }

    reference = _load_reference(
        reference_path
    )

    split_digest = reference.get(
        "split_digest"
    )

    scientific_freeze_sha256 = (
        reference.get(
            "scientific_freeze_sha256"
        )
    )

    if (
        not isinstance(
            split_digest,
            str,
        )
        or len(
            split_digest
        )
        != 64
        or not isinstance(
            scientific_freeze_sha256,
            str,
        )
        or len(
            scientific_freeze_sha256
        )
        != 64
    ):
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_frozen_reference_lineage_missing",
            "attack_sessions":
                len(
                    sessions
                ),
            "features_created":
                False,
            "reason": (
                "Frozen normal reference does not carry the scientific "
                "split/freeze identity required for final evaluation."
            ),
        }

    reference_file_sha256 = (
        sha256_file(
            reference_path
        )
    )

    output_root = Path(
        output_root
    )

    if output_root.exists():
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_attack_feature_output_already_exists",
            "attack_sessions":
                len(
                    sessions
                ),
            "features_created":
                False,
        }

    normal_cohort_environment = (
        reference.get(
            "normal_cohort_environment"
        )
    )

    if not isinstance(
        normal_cohort_environment,
        str,
    ) or not normal_cohort_environment:
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_normal_cohort_environment_missing",
            "attack_sessions":
                len(
                    sessions
                ),
            "features_created":
                False,
        }

    all_parts = []
    session_summary = []

    for folder in sessions:
        frame = pd.read_csv(
            folder
            / "observations.csv.gz"
        )

        required_columns = {
            "label",
            "session_label",
            "is_attack_target",
            "is_synthetic",
            "source_dataset",
            "environment",
            "attack_type",
            "bssid_hash",
        }

        missing_columns = sorted(
            required_columns
            - set(
                frame.columns
            )
        )

        if missing_columns:
            raise ValueError(
                f"{folder.name}: colunas obrigatórias "
                f"ausentes: {missing_columns}."
            )

        labels = pd.to_numeric(
            frame[
                "label"
            ],
            errors="raise",
        ).astype(int)

        if not labels.isin(
            [0, 1]
        ).all():
            raise ValueError(
                f"{folder.name}: label precisa ser 0 ou 1."
            )

        session_labels = pd.to_numeric(
            frame[
                "session_label"
            ],
            errors="raise",
        ).astype(int)

        if not (
            session_labels
            == 1
        ).all():
            raise ValueError(
                f"{folder.name}: session_label precisa ser 1."
            )

        attack_target_flags = (
            frame[
                "is_attack_target"
            ].astype(bool)
        )

        if not (
            labels
            == attack_target_flags.astype(int)
        ).all():
            raise ValueError(
                f"{folder.name}: label e "
                "is_attack_target são inconsistentes."
            )

        attack_rows = int(
            (
                labels
                == 1
            ).sum()
        )

        normal_rows = int(
            (
                labels
                == 0
            ).sum()
        )

        if attack_rows == 0:
            raise ValueError(
                f"{folder.name}: sessão sem observação "
                "do BSSID alvo."
            )

        if (
            frame[
                "bssid_hash"
            ].isna().any()
        ):
            raise ValueError(
                f"{folder.name}: observação sem bssid_hash."
            )

        attack_bssids = (
            frame.loc[
                labels == 1,
                "bssid_hash",
            ]
            .astype(str)
            .unique()
        )

        if len(
            attack_bssids
        ) != 1:
            raise ValueError(
                f"{folder.name}: observações de ataque "
                "precisam corresponder a exatamente "
                "um BSSID alvo."
            )

        if (
            frame[
                "is_synthetic"
            ].astype(
                bool
            ).any()
        ):
            raise ValueError(
                f"{folder.name}: ataque final precisa "
                "ser real/is_synthetic=false."
            )

        if not (
            frame[
                "source_dataset"
            ].astype(
                str
            )
            == "own_windows_attack"
        ).all():
            raise ValueError(
                f"{folder.name}: source_dataset precisa "
                "ser own_windows_attack."
            )

        attack_environments = sorted({
            str(
                value
            ).strip()
            for value
            in frame[
                "environment"
            ].dropna()
            if str(
                value
            ).strip()
        })

        if attack_environments != [
            normal_cohort_environment
        ]:
            return {
                "schema_version":
                    "desktop_attack_feature_preparation_v4",
                "status":
                    "blocked_attack_environment_mismatch",
                "attack_sessions":
                    len(
                        sessions
                    ),
                "features_created":
                    False,
                "normal_cohort_environment":
                    normal_cohort_environment,
                "attack_environments":
                    attack_environments,
                "session_id":
                    folder.name,
            }

        if (
            frame[
                "attack_type"
            ].isna().any()
        ):
            raise ValueError(
                f"{folder.name}: attack_type é obrigatório."
            )

        features = transform_desktop_features(
            frame,
            reference,
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
            "session_label",
            "label",
            "is_attack_target",
            "attack_type",
            "is_synthetic",
        ]

        metadata = frame[
            [
                column
                for column
                in metadata_columns
                if column in frame.columns
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

        eligible_mask = (
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
        )

        session_eligible = combined[
            eligible_mask
        ]

        session_attack_mask = (
            pd.to_numeric(
                combined[
                    "label"
                ],
                errors="raise",
            ).astype(int)
            == 1
        )

        session_normal_mask = (
            pd.to_numeric(
                combined[
                    "label"
                ],
                errors="raise",
            ).astype(int)
            == 0
        )

        eligible_attack = int(
            (
                eligible_mask
                & session_attack_mask
            ).sum()
        )

        eligible_normal = int(
            (
                eligible_mask
                & session_normal_mask
            ).sum()
        )

        attack_target_eligible_rate = (
            float(
                eligible_attack
                / attack_rows
            )
            if attack_rows
            else 0.0
        )

        all_parts.append(
            combined
        )

        session_summary.append({
            "session_id":
                folder.name,
            "rows":
                int(
                    len(
                        combined
                    )
                ),
            "attack_rows":
                attack_rows,
            "normal_rows":
                normal_rows,
            "target_bssid_hash":
                str(
                    attack_bssids[
                        0
                    ]
                ),
            "context_available":
                int(
                    combined[
                        "context_available"
                    ].astype(
                        bool
                    ).sum()
                ),
            "eligible":
                int(
                    len(
                        session_eligible
                    )
                ),
            "eligible_attack":
                eligible_attack,
            "eligible_normal":
                eligible_normal,
            "attack_target_eligible_rate":
                attack_target_eligible_rate,
        })

    all_rows = pd.concat(
        all_parts,
        ignore_index=True,
    )

    eligible_mask = (
        all_rows[
            "context_available"
        ].astype(
            bool
        )
        & all_rows[
            "feature_complete"
        ].astype(
            bool
        )
    )

    eligible = all_rows[
        eligible_mask
    ].copy()

    all_labels = pd.to_numeric(
        all_rows[
            "label"
        ],
        errors="raise",
    ).astype(int)

    eligible_labels = pd.to_numeric(
        eligible[
            "label"
        ],
        errors="raise",
    ).astype(int)

    attack_rows_total = int(
        (
            all_labels
            == 1
        ).sum()
    )

    normal_rows_total = int(
        (
            all_labels
            == 0
        ).sum()
    )

    eligible_attack_rows = int(
        (
            eligible_labels
            == 1
        ).sum()
    )

    eligible_normal_rows = int(
        (
            eligible_labels
            == 0
        ).sum()
    )

    eligible_rate = (
        float(
            len(
                eligible
            )
            / len(
                all_rows
            )
        )
        if len(
            all_rows
        )
        else 0.0
    )

    attack_target_eligible_rate = (
        float(
            eligible_attack_rows
            / attack_rows_total
        )
        if attack_rows_total
        else 0.0
    )

    if (
        len(
            all_rows
        )
        == 0
        or len(
            eligible
        )
        == 0
        or eligible_rate
        < MIN_ATTACK_ELIGIBLE_RATE
    ):
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_attack_feature_coverage_below_minimum",
            "attack_sessions":
                len(
                    sessions
                ),
            "rows":
                int(
                    len(
                        all_rows
                    )
                ),
            "attack_rows":
                attack_rows_total,
            "normal_rows":
                normal_rows_total,
            "eligible":
                int(
                    len(
                        eligible
                    )
                ),
            "eligible_attack":
                eligible_attack_rows,
            "eligible_normal":
                eligible_normal_rows,
            "eligible_rate":
                eligible_rate,
            "minimum_eligible_rate":
                MIN_ATTACK_ELIGIBLE_RATE,
            "attack_target_eligible_rate":
                attack_target_eligible_rate,
            "minimum_attack_target_eligible_rate":
                MIN_ATTACK_TARGET_ELIGIBLE_RATE,
            "features_created":
                False,
            "normal_cohort_environment":
                normal_cohort_environment,
            "sessions":
                session_summary,
        }

    if (
        attack_rows_total == 0
        or eligible_attack_rows == 0
        or attack_target_eligible_rate
        < MIN_ATTACK_TARGET_ELIGIBLE_RATE
    ):
        return {
            "schema_version":
                "desktop_attack_feature_preparation_v4",
            "status":
                "blocked_attack_target_feature_coverage_below_minimum",
            "attack_sessions":
                len(
                    sessions
                ),
            "rows":
                int(
                    len(
                        all_rows
                    )
                ),
            "attack_rows":
                attack_rows_total,
            "normal_rows":
                normal_rows_total,
            "eligible":
                int(
                    len(
                        eligible
                    )
                ),
            "eligible_attack":
                eligible_attack_rows,
            "eligible_normal":
                eligible_normal_rows,
            "eligible_rate":
                eligible_rate,
            "minimum_eligible_rate":
                MIN_ATTACK_ELIGIBLE_RATE,
            "attack_target_eligible_rate":
                attack_target_eligible_rate,
            "minimum_attack_target_eligible_rate":
                MIN_ATTACK_TARGET_ELIGIBLE_RATE,
            "features_created":
                False,
            "normal_cohort_environment":
                normal_cohort_environment,
            "sessions":
                session_summary,
            "reason": (
                "Controlled attack target observations do not have "
                "enough eligible frozen-reference features for "
                "scientific evaluation."
            ),
        }

    output_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    all_rows.to_csv(
        output_root
        / "attack_features_all.csv.gz",
        index=False,
        compression="gzip",
    )

    eligible.to_csv(
        output_root
        / "attack_features_eligible.csv.gz",
        index=False,
        compression="gzip",
    )

    result = {
        "schema_version":
            "desktop_attack_feature_preparation_v4",
        "status":
            "attack_features_ready",
        "attack_sessions":
            len(
                sessions
            ),
        "rows":
            int(
                len(
                    all_rows
                )
            ),
        "attack_rows":
            attack_rows_total,
        "normal_rows":
            normal_rows_total,
        "eligible":
            int(
                len(
                    eligible
                )
            ),
        "eligible_attack":
            eligible_attack_rows,
        "eligible_normal":
            eligible_normal_rows,
        "eligible_rate":
            eligible_rate,
        "minimum_eligible_rate":
            MIN_ATTACK_ELIGIBLE_RATE,
        "attack_target_eligible_rate":
            attack_target_eligible_rate,
        "minimum_attack_target_eligible_rate":
            MIN_ATTACK_TARGET_ELIGIBLE_RATE,
        "normal_cohort_environment":
            normal_cohort_environment,
        "features":
            DESKTOP_FEATURES,
        "split_digest":
            split_digest,
        "scientific_freeze_sha256":
            scientific_freeze_sha256,
        "reference_file_sha256":
            reference_file_sha256,
        "sessions":
            session_summary,
        "label_semantics": {
            "session_label":
                "1 means the session contains a controlled attack",
            "label":
                "1 only for the controlled attack target BSSID; 0 otherwise",
            "is_attack_target":
                "boolean equivalent of the observation-level label",
        },
        "evaluation_only":
            True,
        "normal_reference_updated":
            False,
        "model_updated":
            False,
        "threshold_updated":
            False,
    }

    (
        output_root
        / "manifest.json"
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
            "Deriva features de ataque real usando "
            "referência normal congelada."
        )
    )

    parser.add_argument(
        "--interim-attack-root",
        default=(
            "data/interim/own/windows_attack"
        ),
    )

    parser.add_argument(
        "--frozen-reference",
        default=(
            "data/processed/desktop_candidate_v1/"
            "desktop_normal_reference.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/processed/desktop_candidate_v1_attack"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = prepare_attack_features(
        args.interim_attack_root,
        args.frozen_reference,
        args.output_root,
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
        return 12

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )