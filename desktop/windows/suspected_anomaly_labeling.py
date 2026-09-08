from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .artifact_lineage import sha256_file
from .desktop_reference import (
    DESKTOP_FEATURES,
    transform_desktop_features,
)


SCHEMA_VERSION = (
    "desktop_suspected_anomaly_labeling_v2"
)

REQUIRED_DERIVED_COLUMNS = {
    "context_available",
    "feature_complete",
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
}

SUSPICION_LEVELS = [
    "normal_like",
    "low_suspicion",
    "medium_suspicion",
    "high_suspicion",
]


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


def _suspicion_level(
    score: int,
) -> str:
    if score <= 0:
        return "normal_like"

    if score == 1:
        return "low_suspicion"

    if score <= 3:
        return "medium_suspicion"

    return "high_suspicion"


def _derive_suspected_labels(
    frame: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    missing = sorted(
        REQUIRED_DERIVED_COLUMNS
        - set(
            features.columns
        )
    )

    if missing:
        raise ValueError(
            "Features obrigatórias ausentes: "
            f"{missing}"
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
        "is_synthetic",
    ]

    metadata = frame[
        [
            column
            for column in metadata_columns
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

    combined[
        "suspected_label"
    ] = pd.Series(
        pd.NA,
        index=combined.index,
        dtype="Int64",
    )

    combined[
        "suspicion_score"
    ] = pd.Series(
        pd.NA,
        index=combined.index,
        dtype="Int64",
    )

    combined[
        "suspicion_level"
    ] = "not_evaluable"

    combined[
        "hypothesis_type"
    ] = "not_evaluable"

    combined[
        "heuristic_reasons"
    ] = ""

    combined[
        "context_notes"
    ] = ""

    combined[
        "label_source"
    ] = "heuristic_exploratory_v2"

    combined[
        "ground_truth_available"
    ] = False

    for index in combined.index[
        eligible_mask
    ]:
        row = combined.loc[
            index
        ]

        bssid_changed = (
            int(
                pd.to_numeric(
                    row[
                        "bssid_changed"
                    ],
                    errors="raise",
                )
            )
            != 0
        )

        security_changed = (
            int(
                pd.to_numeric(
                    row[
                        "security_changed"
                    ],
                    errors="raise",
                )
            )
            != 0
        )

        security_delta = float(
            pd.to_numeric(
                row[
                    "security_strength_delta"
                ],
                errors="raise",
            )
        )

        weaker_security = (
            security_delta < 0
        )

        ssid_bssid_count = int(
            pd.to_numeric(
                row[
                    "ssid_bssid_count"
                ],
                errors="raise",
            )
        )

        multiple_known_bssids = (
            ssid_bssid_count > 1
        )

        reasons = []
        context_notes = []
        score = 0

        #
        # Novo BSSID para um SSID conhecido.
        #
        # É um sinal compatível com uma hipótese
        # de Evil Twin, porém não confirma ataque.
        #
        if bssid_changed:
            reasons.append(
                "new_bssid_for_known_ssid"
            )

            score += 2

        #
        # Mudança no perfil de segurança em
        # relação à referência normal congelada.
        #
        if security_changed:
            reasons.append(
                "security_profile_changed"
            )

            score += 2

        #
        # Segurança numericamente inferior
        # à mediana observada na referência.
        #
        if weaker_security:
            reasons.append(
                "security_strength_lower_than_reference"
            )

            score += 1

        #
        # IMPORTANTE:
        #
        # vários BSSIDs já conhecidos para o mesmo
        # SSID NÃO são considerados anomalia.
        #
        # Isso pode acontecer normalmente em:
        #
        # - redes mesh;
        # - vários access points;
        # - ambientes corporativos;
        # - redes com múltiplas bandas.
        #
        # Guardamos apenas como informação
        # contextual.
        #
        if multiple_known_bssids:
            context_notes.append(
                "known_ssid_has_multiple_reference_bssids"
            )

        level = _suspicion_level(
            score
        )

        #
        # Mantido por compatibilidade com a saída
        # anterior.
        #
        # suspected_label = 1 significa somente:
        #
        # "há pelo menos um sinal heurístico".
        #
        # NÃO significa:
        #
        # "ataque confirmado".
        #
        suspected = int(
            score > 0
        )

        if (
            bssid_changed
            and security_changed
            and weaker_security
        ):
            hypothesis = (
                "possible_evil_twin_"
                "with_security_downgrade"
            )

        elif (
            bssid_changed
            and security_changed
        ):
            hypothesis = (
                "possible_evil_twin_"
                "with_security_change"
            )

        elif bssid_changed:
            hypothesis = (
                "possible_evil_twin_"
                "new_bssid"
            )

        elif (
            security_changed
            and weaker_security
        ):
            hypothesis = (
                "security_profile_anomaly_"
                "with_downgrade"
            )

        elif security_changed:
            hypothesis = (
                "security_profile_anomaly"
            )

        elif weaker_security:
            hypothesis = (
                "weaker_security_observation"
            )

        else:
            hypothesis = (
                "no_evil_twin_hypothesis"
            )

        combined.at[
            index,
            "suspected_label",
        ] = suspected

        combined.at[
            index,
            "suspicion_score",
        ] = score

        combined.at[
            index,
            "suspicion_level",
        ] = level

        combined.at[
            index,
            "hypothesis_type",
        ] = hypothesis

        combined.at[
            index,
            "heuristic_reasons",
        ] = "|".join(
            reasons
        )

        combined.at[
            index,
            "context_notes",
        ] = "|".join(
            context_notes
        )

    return combined


def _level_counts(
    frame: pd.DataFrame,
) -> dict[str, int]:
    counts = {}

    for level in SUSPICION_LEVELS:
        counts[
            level
        ] = int(
            (
                frame[
                    "suspicion_level"
                ]
                == level
            ).sum()
        )

    return counts


def _write_csv(
    frame: pd.DataFrame,
    path: Path,
) -> None:
    frame.to_csv(
        path,
        index=False,
        compression="gzip",
    )


def prepare_suspected_anomalies(
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
            "files":
                0,
            "created":
                False,
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
                SCHEMA_VERSION,
            "status":
                "blocked_frozen_reference_lineage_missing",
            "files":
                len(
                    observation_files
                ),
            "created":
                False,
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

    all_parts = []
    file_summary = []

    for path in observation_files:
        frame = pd.read_csv(
            path
        )

        if frame.empty:
            continue

        features = (
            transform_desktop_features(
                frame,
                reference,
            )
        )

        combined = (
            _derive_suspected_labels(
                frame,
                features,
            )
        )

        combined[
            "source_file"
        ] = str(
            path
        )

        all_parts.append(
            combined
        )

        eligible = combined[
            combined[
                "suspected_label"
            ].notna()
        ].copy()

        suspected = eligible[
            eligible[
                "suspected_label"
            ].astype(
                int
            )
            == 1
        ].copy()

        file_summary.append({
            "file":
                str(
                    path
                ),
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
            "not_evaluable":
                int(
                    len(
                        combined
                    )
                    - len(
                        eligible
                    )
                ),
            "suspected":
                int(
                    len(
                        suspected
                    )
                ),
            "level_counts":
                _level_counts(
                    eligible
                ),
        })

    if not all_parts:
        return {
            "schema_version":
                SCHEMA_VERSION,
            "status":
                "blocked_no_rows",
            "created":
                False,
        }

    all_rows = pd.concat(
        all_parts,
        ignore_index=True,
    )

    eligible = all_rows[
        all_rows[
            "suspected_label"
        ].notna()
    ].copy()

    suspected = eligible[
        eligible[
            "suspected_label"
        ].astype(
            int
        )
        == 1
    ].copy()

    non_suspected = eligible[
        eligible[
            "suspected_label"
        ].astype(
            int
        )
        == 0
    ].copy()

    normal_like = eligible[
        eligible[
            "suspicion_level"
        ]
        == "normal_like"
    ].copy()

    low_suspicion = eligible[
        eligible[
            "suspicion_level"
        ]
        == "low_suspicion"
    ].copy()

    medium_suspicion = eligible[
        eligible[
            "suspicion_level"
        ]
        == "medium_suspicion"
    ].copy()

    high_suspicion = eligible[
        eligible[
            "suspicion_level"
        ]
        == "high_suspicion"
    ].copy()

    output_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    _write_csv(
        all_rows,
        output_root
        / "suspected_observations_all.csv.gz",
    )

    _write_csv(
        eligible,
        output_root
        / "suspected_observations_eligible.csv.gz",
    )

    _write_csv(
        suspected,
        output_root
        / "suspected_observations_only.csv.gz",
    )

    _write_csv(
        normal_like,
        output_root
        / "observations_normal_like.csv.gz",
    )

    _write_csv(
        low_suspicion,
        output_root
        / "observations_low_suspicion.csv.gz",
    )

    _write_csv(
        medium_suspicion,
        output_root
        / "observations_medium_suspicion.csv.gz",
    )

    _write_csv(
        high_suspicion,
        output_root
        / "observations_high_suspicion.csv.gz",
    )

    level_counts = _level_counts(
        eligible
    )

    result = {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            "suspected_anomaly_labels_ready",
        "evaluation_type":
            "exploratory",
        "ground_truth_available":
            False,
        "label_source":
            "heuristic_exploratory_v2",
        "created":
            True,
        "rows":
            int(
                len(
                    all_rows
                )
            ),
        "eligible":
            int(
                len(
                    eligible
                )
            ),
        "not_evaluable":
            int(
                len(
                    all_rows
                )
                - len(
                    eligible
                )
            ),
        "suspected":
            int(
                len(
                    suspected
                )
            ),
        "non_suspected":
            int(
                len(
                    non_suspected
                )
            ),
        "suspected_rate":
            (
                float(
                    len(
                        suspected
                    )
                    / len(
                        eligible
                    )
                )
                if len(
                    eligible
                )
                else 0.0
            ),
        "suspicion_levels":
            level_counts,
        "heuristic_definition": {
            "score_rules": {
                "new_bssid_for_known_ssid":
                    2,
                "security_profile_changed":
                    2,
                "security_strength_lower_than_reference":
                    1,
                "multiple_known_reference_bssids":
                    0,
            },
            "level_rules": {
                "normal_like":
                    "score = 0",
                "low_suspicion":
                    "score = 1",
                "medium_suspicion":
                    "score between 2 and 3",
                "high_suspicion":
                    "score >= 4",
            },
            "suspected_label_1": (
                "score > 0; exploratory heuristic "
                "signal only"
            ),
            "suspected_label_0": (
                "score = 0 for an eligible "
                "observation"
            ),
            "multiple_bssid_note": (
                "multiple BSSIDs already present in "
                "the frozen reference are contextual "
                "information only and do not increase "
                "the suspicion score"
            ),
            "important_limitation": (
                "All labels and suspicion levels are "
                "heuristic exploratory outputs. They "
                "are not confirmed Evil Twin attacks "
                "and must not be reported as attack "
                "ground truth."
            ),
        },
        "features":
            DESKTOP_FEATURES,
        "split_digest":
            split_digest,
        "scientific_freeze_sha256":
            scientific_freeze_sha256,
        "reference_file_sha256":
            sha256_file(
                reference_path
            ),
        "output_files": {
            "all":
                "suspected_observations_all.csv.gz",
            "eligible":
                "suspected_observations_eligible.csv.gz",
            "suspected":
                "suspected_observations_only.csv.gz",
            "normal_like":
                "observations_normal_like.csv.gz",
            "low_suspicion":
                "observations_low_suspicion.csv.gz",
            "medium_suspicion":
                "observations_medium_suspicion.csv.gz",
            "high_suspicion":
                "observations_high_suspicion.csv.gz",
            "manifest":
                "manifest.json",
        },
        "scientific_rules": [
            (
                "The frozen desktop reference is read-only "
                "and is never updated by this pipeline."
            ),
            (
                "The frozen scaler, OCSVM and threshold "
                "are not modified or recalibrated."
            ),
            (
                "Unknown or incomplete context remains "
                "not_evaluable."
            ),
            (
                "Multiple BSSIDs already known in the "
                "reference are not considered anomalous "
                "by themselves."
            ),
            (
                "Heuristic outputs are exploratory "
                "pseudo-labels, not attack ground truth."
            ),
            (
                "No precision, recall or F1 against real "
                "attacks may be claimed from these "
                "pseudo-labels alone."
            ),
        ],
        "files":
            file_summary,
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
            "Aplica pseudo-rótulos heurísticos "
            "e níveis de suspeita para avaliação "
            "exploratória de possíveis anomalias "
            "Wi-Fi. Os resultados não representam "
            "ground truth de ataque."
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
            "desktop_candidate_v1_suspected_v2"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = (
        prepare_suspected_anomalies(
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