from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .artifact_lineage import sha256_file
from .desktop_reference import (
    transform_desktop_features,
)


SCHEMA_VERSION = (
    "desktop_hypothetical_scenarios_v1"
)

SOURCE_DATASET = (
    "own_windows_hypothetical"
)


SECURITY_CANDIDATES = [
    (
        "OPEN",
        0.0,
    ),
    (
        "LEGACY_PRIVACY",
        1.0,
    ),
    (
        "WPA2_OR_NEWER",
        3.0,
    ),
]


SCENARIOS = {
    "hypothetical_control": {
        "scenario_family":
            "control_copy",
        "expected_suspicion_level":
            "normal_like",
        "expected_signals": [],
        "notes": (
            "Synthetic copy without feature "
            "perturbation. Used as a control."
        ),
    },

    "hypothetical_new_bssid": {
        "scenario_family":
            "hypothetical_evil_twin",
        "expected_suspicion_level":
            "medium_suspicion",
        "expected_signals": [
            "new_bssid_for_known_ssid",
        ],
        "notes": (
            "Changes only the BSSID hash while "
            "preserving the known SSID and "
            "security profile."
        ),
    },

    "ablation_weaker_security_only": {
        "scenario_family":
            "feature_ablation",
        "expected_suspicion_level":
            "low_suspicion",
        "expected_signals": [
            (
                "security_strength_lower_"
                "than_reference"
            ),
        ],
        "notes": (
            "Feature-isolation ablation. "
            "It is not presented as a realistic "
            "attack scenario."
        ),
    },

    (
        "hypothetical_new_bssid_"
        "security_change"
    ): {
        "scenario_family":
            "hypothetical_evil_twin",
        "expected_suspicion_level":
            "high_suspicion",
        "expected_signals": [
            "new_bssid_for_known_ssid",
            "security_profile_changed",
        ],
        "notes": (
            "Changes BSSID and security type. "
            "Security strength is held at the "
            "reference median to isolate the "
            "security_changed feature."
        ),
    },

    (
        "hypothetical_new_bssid_"
        "security_downgrade"
    ): {
        "scenario_family":
            "hypothetical_evil_twin",
        "expected_suspicion_level":
            "high_suspicion",
        "expected_signals": [
            "new_bssid_for_known_ssid",
            "security_profile_changed",
            (
                "security_strength_lower_"
                "than_reference"
            ),
        ],
        "notes": (
            "Changes BSSID and chooses a lower "
            "security candidate when one is "
            "available."
        ),
    },
}


def _load_reference(
    path: str | Path,
) -> dict[str, object]:
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            "Frozen reference ausente: "
            f"{path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def discover_observation_files(
    input_root: str | Path,
) -> list[Path]:
    root = Path(
        input_root
    )

    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob(
            "observations.csv.gz"
        )
        if path.is_file()
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


def _baseline_mask(
    features: pd.DataFrame,
) -> pd.Series:
    context_available = (
        features[
            "context_available"
        ].astype(
            bool
        )
    )

    feature_complete = (
        features[
            "feature_complete"
        ].astype(
            bool
        )
    )

    direct_ssid_context = (
        features[
            "context_resolution"
        ]
        == "ssid_hash"
    )

    bssid_changed = (
        pd.to_numeric(
            features[
                "bssid_changed"
            ],
            errors="coerce",
        )
    )

    security_changed = (
        pd.to_numeric(
            features[
                "security_changed"
            ],
            errors="coerce",
        )
    )

    security_delta = (
        pd.to_numeric(
            features[
                "security_strength_delta"
            ],
            errors="coerce",
        )
    )

    return (
        context_available
        & feature_complete
        & direct_ssid_context
        & bssid_changed.eq(
            0
        )
        & security_changed.eq(
            0
        )
        & security_delta.abs().le(
            1e-9
        )
    )


def _synthetic_bssid_hash(
    *,
    ssid_hash: str,
    source_bssid_hash: str,
    scenario_type: str,
    source_session_id: str,
    source_scan_index: object,
    known_bssids: set[str],
) -> str:
    salt = 0

    while True:
        payload = (
            "desktop-hypothetical-bssid|"
            f"{scenario_type}|"
            f"{ssid_hash}|"
            f"{source_bssid_hash}|"
            f"{source_session_id}|"
            f"{source_scan_index}|"
            f"{salt}"
        )

        candidate = hashlib.sha256(
            payload.encode(
                "utf-8"
            )
        ).hexdigest()

        if (
            candidate
            not in known_bssids
        ):
            return candidate

        salt += 1


def _different_security_type(
    reference_types: set[str],
) -> str | None:
    for (
        security_type,
        _,
    ) in SECURITY_CANDIDATES:
        if (
            security_type
            not in reference_types
        ):
            return security_type

    return None


def _lower_security_candidate(
    *,
    reference_types: set[str],
    reference_strength: float,
) -> tuple[str, float] | None:
    candidates = [
        (
            security_type,
            strength,
        )
        for (
            security_type,
            strength,
        ) in SECURITY_CANDIDATES
        if (
            security_type
            not in reference_types
            and strength
            < reference_strength
        )
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[
            1
        ],
    )


def _prepare_base_row(
    *,
    row: pd.Series,
    source_file: Path,
    source_row_index: int,
    scenario_type: str,
) -> dict[str, object]:
    generated = (
        row.to_dict()
    )

    source_session_id = str(
        row.get(
            "session_id",
            "unknown",
        )
    )

    source_scan_index = (
        row.get(
            "scan_index",
            source_row_index,
        )
    )

    generated[
        "source_dataset"
    ] = SOURCE_DATASET

    generated[
        "source_session_id"
    ] = source_session_id

    generated[
        "source_scan_index"
    ] = source_scan_index

    generated[
        "source_file"
    ] = str(
        source_file
    )

    generated[
        "source_row_index"
    ] = int(
        source_row_index
    )

    generated[
        "scenario_type"
    ] = scenario_type

    generated[
        "scenario_family"
    ] = SCENARIOS[
        scenario_type
    ][
        "scenario_family"
    ]

    generated[
        "scenario_notes"
    ] = SCENARIOS[
        scenario_type
    ][
        "notes"
    ]

    generated[
        "evaluation_type"
    ] = (
        "hypothetical_stress_test"
    )

    generated[
        "ground_truth_available"
    ] = False

    generated[
        "is_synthetic"
    ] = True

    generated[
        "expected_suspicion_level"
    ] = SCENARIOS[
        scenario_type
    ][
        "expected_suspicion_level"
    ]

    generated[
        "hypothetical_expected_signals"
    ] = "|".join(
        SCENARIOS[
            scenario_type
        ][
            "expected_signals"
        ]
    )

    generated[
        "session_id"
    ] = (
        "hypothetical-"
        f"{scenario_type}-"
        f"{source_session_id}"
    )

    #
    # Nenhum dado hipotético recebe
    # ground truth binário de ataque.
    #
    if (
        "label"
        in generated
    ):
        generated[
            "label"
        ] = pd.NA

    if (
        "session_label"
        in generated
    ):
        generated[
            "session_label"
        ] = pd.NA

    if (
        "is_attack_target"
        in generated
    ):
        generated[
            "is_attack_target"
        ] = pd.NA

    if (
        "attack_type"
        in generated
    ):
        generated[
            "attack_type"
        ] = pd.NA

    return generated


def _build_scenarios_for_row(
    *,
    row: pd.Series,
    source_file: Path,
    source_row_index: int,
    reference: dict[str, object],
) -> list[dict[str, object]]:
    ssid_hash = str(
        row[
            "ssid_hash"
        ]
    )

    source_bssid_hash = str(
        row[
            "bssid_hash"
        ]
    )

    profile = reference[
        "ssid_profiles"
    ].get(
        ssid_hash
    )

    if profile is None:
        return []

    known_bssids = {
        str(
            value
        )
        for value in profile.get(
            "bssid_hashes",
            [],
        )
    }

    reference_types = {
        str(
            value
        )
        for value in profile.get(
            "security_types",
            [],
        )
    }

    reference_strength_raw = (
        profile.get(
            "security_strength_median"
        )
    )

    if (
        reference_strength_raw
        is None
    ):
        return []

    reference_strength = float(
        reference_strength_raw
    )

    source_session_id = str(
        row.get(
            "session_id",
            "unknown",
        )
    )

    source_scan_index = (
        row.get(
            "scan_index",
            source_row_index,
        )
    )

    generated_rows = []

    #
    # 1. Controle sem alteração.
    #
    control = (
        _prepare_base_row(
            row=row,
            source_file=source_file,
            source_row_index=(
                source_row_index
            ),
            scenario_type=(
                "hypothetical_control"
            ),
        )
    )

    generated_rows.append(
        control
    )

    #
    # 2. Somente BSSID novo.
    #
    scenario_new_bssid = (
        _prepare_base_row(
            row=row,
            source_file=source_file,
            source_row_index=(
                source_row_index
            ),
            scenario_type=(
                "hypothetical_new_bssid"
            ),
        )
    )

    scenario_new_bssid[
        "bssid_hash"
    ] = _synthetic_bssid_hash(
        ssid_hash=ssid_hash,
        source_bssid_hash=(
            source_bssid_hash
        ),
        scenario_type=(
            "hypothetical_new_bssid"
        ),
        source_session_id=(
            source_session_id
        ),
        source_scan_index=(
            source_scan_index
        ),
        known_bssids=(
            known_bssids
        ),
    )

    generated_rows.append(
        scenario_new_bssid
    )

    #
    # 3. Ablation:
    # apenas security_strength_delta < 0.
    #
    if (
        reference_strength
        > 0
    ):
        weaker = (
            _prepare_base_row(
                row=row,
                source_file=source_file,
                source_row_index=(
                    source_row_index
                ),
                scenario_type=(
                    "ablation_weaker_"
                    "security_only"
                ),
            )
        )

        weaker[
            "security_strength"
        ] = max(
            0.0,
            (
                reference_strength
                - 1.0
            ),
        )

        generated_rows.append(
            weaker
        )

    #
    # 4. Novo BSSID + tipo de
    # segurança diferente.
    #
    different_security = (
        _different_security_type(
            reference_types
        )
    )

    if (
        different_security
        is not None
    ):
        scenario_type = (
            "hypothetical_new_bssid_"
            "security_change"
        )

        security_change = (
            _prepare_base_row(
                row=row,
                source_file=source_file,
                source_row_index=(
                    source_row_index
                ),
                scenario_type=(
                    scenario_type
                ),
            )
        )

        security_change[
            "bssid_hash"
        ] = _synthetic_bssid_hash(
            ssid_hash=(
                ssid_hash
            ),
            source_bssid_hash=(
                source_bssid_hash
            ),
            scenario_type=(
                scenario_type
            ),
            source_session_id=(
                source_session_id
            ),
            source_scan_index=(
                source_scan_index
            ),
            known_bssids=(
                known_bssids
            ),
        )

        security_change[
            "security_type"
        ] = different_security

        #
        # Mantém o valor da referência
        # para isolar security_changed.
        #
        security_change[
            "security_strength"
        ] = reference_strength

        generated_rows.append(
            security_change
        )

    #
    # 5. Novo BSSID + downgrade
    # de segurança.
    #
    downgrade = (
        _lower_security_candidate(
            reference_types=(
                reference_types
            ),
            reference_strength=(
                reference_strength
            ),
        )
    )

    if (
        downgrade
        is not None
    ):
        (
            downgrade_type,
            downgrade_strength,
        ) = downgrade

        scenario_type = (
            "hypothetical_new_bssid_"
            "security_downgrade"
        )

        security_downgrade = (
            _prepare_base_row(
                row=row,
                source_file=source_file,
                source_row_index=(
                    source_row_index
                ),
                scenario_type=(
                    scenario_type
                ),
            )
        )

        security_downgrade[
            "bssid_hash"
        ] = _synthetic_bssid_hash(
            ssid_hash=(
                ssid_hash
            ),
            source_bssid_hash=(
                source_bssid_hash
            ),
            scenario_type=(
                scenario_type
            ),
            source_session_id=(
                source_session_id
            ),
            source_scan_index=(
                source_scan_index
            ),
            known_bssids=(
                known_bssids
            ),
        )

        security_downgrade[
            "security_type"
        ] = downgrade_type

        security_downgrade[
            "security_strength"
        ] = downgrade_strength

        generated_rows.append(
            security_downgrade
        )

    return generated_rows


def _feature_summary(
    frame: pd.DataFrame,
    reference: dict[str, object],
) -> dict[str, int]:
    if frame.empty:
        return {
            "rows":
                0,
            "feature_complete":
                0,
            "bssid_changed":
                0,
            "security_changed":
                0,
            "weaker_security":
                0,
        }

    features = (
        transform_desktop_features(
            frame,
            reference,
        )
    )

    bssid_changed = (
        pd.to_numeric(
            features[
                "bssid_changed"
            ],
            errors="coerce",
        )
    )

    security_changed = (
        pd.to_numeric(
            features[
                "security_changed"
            ],
            errors="coerce",
        )
    )

    security_delta = (
        pd.to_numeric(
            features[
                "security_strength_delta"
            ],
            errors="coerce",
        )
    )

    return {
        "rows":
            int(
                len(
                    frame
                )
            ),
        "feature_complete":
            int(
                features[
                    "feature_complete"
                ].astype(
                    bool
                ).sum()
            ),
        "bssid_changed":
            int(
                bssid_changed
                .fillna(
                    0
                )
                .ne(
                    0
                )
                .sum()
            ),
        "security_changed":
            int(
                security_changed
                .fillna(
                    0
                )
                .ne(
                    0
                )
                .sum()
            ),
        "weaker_security":
            int(
                security_delta
                .lt(
                    0
                )
                .sum()
            ),
    }


def generate_hypothetical_scenarios(
    input_root: str | Path,
    frozen_reference_path: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    reference_path = Path(
        frozen_reference_path
    )

    observation_files = (
        discover_observation_files(
            input_root
        )
    )

    if not observation_files:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_observation_data_missing",
            "created":
                False,
            "files":
                0,
        }

    reference = _load_reference(
        reference_path
    )

    split_digest = (
        reference.get(
            "split_digest"
        )
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
                SCHEMA_VERSION,
            "status": (
                "blocked_frozen_reference_"
                "lineage_missing"
            ),
            "created":
                False,
            "files":
                len(
                    observation_files
                ),
        }

    output_root = Path(
        output_root
    )

    if output_root.exists():
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_output_already_exists",
            "created":
                False,
        }

    generated_rows = []
    source_summary = []

    for path in observation_files:
        frame = pd.read_csv(
            path
        )

        if frame.empty:
            continue

        required_columns = {
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
                f"{path}: colunas obrigatórias "
                f"ausentes: {missing}."
            )

        #
        # Não reutiliza dados já sintéticos.
        #
        if (
            "is_synthetic"
            in frame.columns
        ):
            non_synthetic = ~frame[
                "is_synthetic"
            ].map(
                _is_true
            )

            frame = frame[
                non_synthetic
            ].copy()

        if frame.empty:
            continue

        #
        # Reset importante para manter
        # frame e features alinhados.
        #
        frame = (
            frame.reset_index(
                drop=True
            )
        )

        features = (
            transform_desktop_features(
                frame,
                reference,
            )
        )

        baseline_mask = (
            _baseline_mask(
                features
            )
        )

        baseline_indices = list(
            frame.index[
                baseline_mask
            ]
        )

        generated_before = (
            len(
                generated_rows
            )
        )

        for source_row_index in (
            baseline_indices
        ):
            row = frame.loc[
                source_row_index
            ]

            generated_rows.extend(
                _build_scenarios_for_row(
                    row=row,
                    source_file=path,
                    source_row_index=(
                        int(
                            source_row_index
                        )
                    ),
                    reference=(
                        reference
                    ),
                )
            )

        source_summary.append({
            "file":
                str(
                    path
                ),
            "source_sha256":
                sha256_file(
                    path
                ),
            "rows":
                int(
                    len(
                        frame
                    )
                ),
            "baseline_rows":
                int(
                    len(
                        baseline_indices
                    )
                ),
            "generated_rows":
                int(
                    len(
                        generated_rows
                    )
                    - generated_before
                ),
        })

    if not generated_rows:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_no_baseline_rows",
            "created":
                False,
            "source_files":
                source_summary,
        }

    all_generated = (
        pd.DataFrame(
            generated_rows
        )
    )

    output_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    combined_path = (
        output_root
        / (
            "all_hypothetical_"
            "observations.csv.gz"
        )
    )

    all_generated.to_csv(
        combined_path,
        index=False,
        compression="gzip",
    )

    scenario_summary = {}

    for scenario_type in SCENARIOS:
        scenario_frame = (
            all_generated[
                all_generated[
                    "scenario_type"
                ]
                == scenario_type
            ].copy()
        )

        if scenario_frame.empty:
            scenario_summary[
                scenario_type
            ] = {
                "rows":
                    0,
                "created":
                    False,
            }

            continue

        scenario_dir = (
            output_root
            / scenario_type
        )

        scenario_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        observations_path = (
            scenario_dir
            / "observations.csv.gz"
        )

        scenario_frame.to_csv(
            observations_path,
            index=False,
            compression="gzip",
        )

        feature_summary = (
            _feature_summary(
                scenario_frame,
                reference,
            )
        )

        scenario_manifest = {
            "schema_version": (
                "desktop_hypothetical_"
                "scenario_v1"
            ),
            "scenario_type":
                scenario_type,
            "scenario_family":
                SCENARIOS[
                    scenario_type
                ][
                    "scenario_family"
                ],
            "evaluation_type":
                "hypothetical_stress_test",
            "ground_truth_available":
                False,
            "is_synthetic":
                True,
            "rows":
                int(
                    len(
                        scenario_frame
                    )
                ),
            "expected_suspicion_level":
                SCENARIOS[
                    scenario_type
                ][
                    "expected_suspicion_level"
                ],
            "expected_signals":
                SCENARIOS[
                    scenario_type
                ][
                    "expected_signals"
                ],
            "scenario_notes":
                SCENARIOS[
                    scenario_type
                ][
                    "notes"
                ],
            "observed_feature_summary":
                feature_summary,
            "observations_sha256":
                sha256_file(
                    observations_path
                ),
            "forbidden_claims": [
                "confirmed attack",
                "real Evil Twin ground truth",
                "real-attack precision",
                "real-attack recall",
                "real-attack F1",
            ],
        }

        (
            scenario_dir
            / "manifest.json"
        ).write_text(
            json.dumps(
                scenario_manifest,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        scenario_summary[
            scenario_type
        ] = {
            "rows":
                int(
                    len(
                        scenario_frame
                    )
                ),
            "created":
                True,
            "output":
                str(
                    observations_path
                ),
            "observed_feature_summary":
                feature_summary,
        }

    manifest = {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            "hypothetical_scenarios_ready",
        "created":
            True,
        "evaluation_type":
            "hypothetical_stress_test",
        "ground_truth_available":
            False,
        "source_rows_are_real_observations":
            True,
        "generated_rows_are_synthetic":
            True,
        "baseline_selection_rule": (
            "context_available=true, "
            "feature_complete=true, "
            "context_resolution=ssid_hash, "
            "bssid_changed=0, "
            "security_changed=0, "
            "security_strength_delta=0"
        ),
        "generated_rows":
            int(
                len(
                    all_generated
                )
            ),
        "scenario_counts": {
            scenario_type:
                int(
                    (
                        all_generated[
                            "scenario_type"
                        ]
                        == scenario_type
                    ).sum()
                )
            for scenario_type
            in SCENARIOS
        },
        "split_digest":
            split_digest,
        "scientific_freeze_sha256":
            scientific_freeze_sha256,
        "reference_file_sha256":
            sha256_file(
                reference_path
            ),
        "combined_output":
            str(
                combined_path
            ),
        "combined_output_sha256":
            sha256_file(
                combined_path
            ),
        "scenarios":
            scenario_summary,
        "source_files":
            source_summary,
        "scientific_rules": [
            (
                "The frozen normal reference "
                "is read-only and is not modified."
            ),
            (
                "Scaler, OCSVM and threshold "
                "are not fitted or recalibrated."
            ),
            (
                "Only real observations that are "
                "normal-like relative to the frozen "
                "reference are used as baselines."
            ),
            (
                "Generated rows are synthetic "
                "hypothetical stress cases."
            ),
            (
                "No generated row receives a binary "
                "attack ground-truth label."
            ),
            (
                "The weaker-security-only scenario "
                "is an isolated feature ablation, "
                "not a claim about a realistic attack."
            ),
            (
                "Results may describe system "
                "sensitivity to controlled "
                "hypothetical perturbations, "
                "not real-attack detection "
                "performance."
            ),
        ],
    }

    (
        output_root
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return manifest


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gera cenários sintéticos e "
            "hipotéticos a partir de observações "
            "reais normal-like para stress test "
            "exploratório. Os dados gerados não "
            "são ground truth de ataque."
        )
    )

    parser.add_argument(
        "--input-root",
        required=True,
    )

    parser.add_argument(
        "--frozen-reference",
        default=(
            "data/processed/"
            "desktop_candidate_v1/"
            "desktop_normal_reference.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/processed/"
            "desktop_hypothetical_scenarios_v1"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = (
        generate_hypothetical_scenarios(
            args.input_root,
            args.frozen_reference,
            args.output_root,
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