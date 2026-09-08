from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import (
    Counter,
    defaultdict,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any

import pandas as pd

from .desktop_split_plan import (
    DEFAULT_SEED,
    REQUIRED_SPLITS,
    make_split_plan,
    save_split_plan,
)
from .desktop_reference import (
    build_desktop_reference,
    transform_desktop_features,
)


SCHEMA_VERSION = (
    "desktop_scientific_preflight_v1"
)

FREEZE_SCHEMA_VERSION = (
    "desktop_scientific_freeze_v1"
)

MINIMUM_SESSIONS = 5
MIN_BSSID_HASH_COVERAGE = 0.99
MIN_CANDIDATE_COMPLETENESS = 0.70
MIN_REFERENCE_ELIGIBLE_RATE = 0.70
MAX_NORMAL_COHORT_ENVIRONMENTS = 1

HASH_RE = re.compile(
    r"^[0-9a-fA-F]{64}$"
)

FORBIDDEN_CLEAR_IDENTIFIER_COLUMNS = {
    "ssid",
    "bssid",
    "ssid_clear",
    "bssid_clear",
    "raw_ssid",
    "raw_bssid",
}

CANDIDATE_FIELDS = (
    "ssid_hash",
    "bssid_hash",
    "security_type",
    "security_strength",
)


class ScientificIntegrityError(
    RuntimeError
):
    pass


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open(
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


def canonical_json_sha256(
    value: Any,
) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def _json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _bool_value(
    value: Any,
) -> bool | None:
    if pd.isna(
        value
    ):
        return None

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        int,
    ):
        if value == 1:
            return True

        if value == 0:
            return False

    text = str(
        value
    ).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
    }:
        return False

    return None


def _is_missing_attack(
    value: Any,
) -> bool:
    if pd.isna(
        value
    ):
        return True

    return (
        str(
            value
        ).strip()
        == ""
    )


def _hash_values_valid(
    series: pd.Series,
) -> bool:
    for value in series.dropna():
        if not HASH_RE.fullmatch(
            str(
                value
            )
        ):
            return False

    return True


def _canonical_content_fingerprint(
    frame: pd.DataFrame,
) -> str:
    """
    Fingerprint the observation content while ignoring only the session label
    and environment metadata.

    This catches the common accidental case where the same captured session is
    copied to a new folder/session_id. captured_at_utc remains in the digest,
    so genuinely independent sessions with similar radio values do not collide
    merely because they saw the same APs.
    """
    excluded = {
        "session_id",
        "environment",
    }

    columns = sorted(
        column
        for column
        in frame.columns
        if column
        not in excluded
    )

    normalized_rows = []

    for row in frame[
        columns
    ].itertuples(
        index=False,
        name=None,
    ):
        normalized_rows.append([
            None
            if pd.isna(
                value
            )
            else str(
                value
            )
            for value
            in row
        ])

    normalized_rows.sort()

    return canonical_json_sha256({
        "columns":
            columns,
        "rows":
            normalized_rows,
    })


def _temporal_bounds(
    frame: pd.DataFrame,
) -> tuple[
    str | None,
    str | None,
]:
    if (
        "captured_at_utc"
        not in frame.columns
    ):
        return (
            None,
            None,
        )

    values = pd.to_datetime(
        frame[
            "captured_at_utc"
        ],
        errors="coerce",
        utc=True,
    ).dropna()

    if values.empty:
        return (
            None,
            None,
        )

    return (
        values.min()
        .isoformat(),
        values.max()
        .isoformat(),
    )


def inspect_interim_session(
    session_dir: str | Path,
) -> dict[str, Any]:
    folder = Path(
        session_dir
    )

    blockers: list[str] = []
    warnings: list[str] = []

    observations_path = (
        folder
        / "observations.csv.gz"
    )

    manifest_path = (
        folder
        / "import_manifest.json"
    )

    if not observations_path.exists():
        blockers.append(
            "observations_file_missing"
        )

    if not manifest_path.exists():
        blockers.append(
            "import_manifest_missing"
        )

    if blockers:
        return {
            "session_id":
                folder.name,
            "environment":
                None,
            "rows":
                0,
            "scan_count":
                0,
            "runtime_ready":
                False,
            "valid":
                False,
            "blockers":
                blockers,
            "warnings":
                warnings,
            "observations_path":
                str(
                    observations_path
                ),
            "manifest_path":
                str(
                    manifest_path
                ),
        }

    manifest = _json(
        manifest_path
    )

    manifest_session = str(
        manifest.get(
            "session_id",
            "",
        )
    )

    if not manifest_session:
        blockers.append(
            "manifest_session_id_missing"
        )

    if (
        manifest_session
        != folder.name
    ):
        blockers.append(
            "folder_manifest_session_mismatch"
        )

    if (
        manifest.get(
            "schema_version"
        )
        != "own_windows_interim_import_v1"
    ):
        blockers.append(
            "unexpected_import_schema"
        )

    if (
        manifest.get(
            "source_dataset"
        )
        != "own_windows"
    ):
        blockers.append(
            "manifest_source_dataset_not_own_windows"
        )

    if int(
        manifest.get(
            "label",
            -1,
        )
    ) != 0:
        blockers.append(
            "manifest_label_not_zero"
        )

    if bool(
        manifest.get(
            "attack_present",
            True,
        )
    ):
        blockers.append(
            "manifest_attack_present"
        )

    if not bool(
        manifest.get(
            "source_sha256_verified",
            False,
        )
    ):
        blockers.append(
            "source_sha256_not_verified"
        )

    if not bool(
        manifest.get(
            "runtime_ready",
            False,
        )
    ):
        blockers.append(
            "runtime_ready_false"
        )

    source_scans_sha256 = (
        manifest.get(
            "source_scans_sha256"
        )
    )

    if (
        not isinstance(
            source_scans_sha256,
            str,
        )
        or not HASH_RE.fullmatch(
            source_scans_sha256
        )
    ):
        blockers.append(
            "source_scans_sha256_invalid"
        )

    expected_observations_sha = (
        manifest.get(
            "interim_observations_sha256"
        )
    )

    actual_observations_sha = (
        sha256_file(
            observations_path
        )
    )

    if (
        not isinstance(
            expected_observations_sha,
            str,
        )
        or not HASH_RE.fullmatch(
            expected_observations_sha
        )
    ):
        blockers.append(
            "interim_observations_sha256_missing_or_invalid"
        )

    elif (
        expected_observations_sha
        != actual_observations_sha
    ):
        blockers.append(
            "interim_observations_sha256_mismatch"
        )

    frame = pd.read_csv(
        observations_path
    )

    rows = int(
        len(
            frame
        )
    )

    if rows == 0:
        blockers.append(
            "empty_session"
        )

    if int(
        manifest.get(
            "rows",
            -1,
        )
    ) != rows:
        blockers.append(
            "manifest_row_count_mismatch"
        )

    scan_count = int(
        manifest.get(
            "scan_count",
            0,
        )
    )

    if scan_count < 3:
        blockers.append(
            "scan_count_below_runtime_minimum"
        )

    forbidden_columns = sorted(
        FORBIDDEN_CLEAR_IDENTIFIER_COLUMNS
        & set(
            frame.columns
        )
    )

    if forbidden_columns:
        blockers.append(
            "clear_wifi_identifier_columns_present"
        )

    required_columns = {
        "source_dataset",
        "session_id",
        "environment",
        "ssid_hash",
        "bssid_hash",
        "security_type",
        "security_strength",
        "label",
        "attack_type",
        "is_synthetic",
    }

    missing_columns = sorted(
        required_columns
        - set(
            frame.columns
        )
    )

    if missing_columns:
        blockers.append(
            "required_interim_columns_missing"
        )

    if (
        "source_dataset"
        in frame.columns
        and not (
            frame[
                "source_dataset"
            ].astype(
                str
            )
            == "own_windows"
        ).all()
    ):
        blockers.append(
            "row_source_dataset_not_own_windows"
        )

    if (
        "session_id"
        in frame.columns
        and not (
            frame[
                "session_id"
            ].astype(
                str
            )
            == folder.name
        ).all()
    ):
        blockers.append(
            "row_session_id_mismatch"
        )

    if (
        "label"
        in frame.columns
    ):
        labels = pd.to_numeric(
            frame[
                "label"
            ],
            errors="coerce",
        )

        if (
            labels.isna().any()
            or not (
                labels
                == 0
            ).all()
        ):
            blockers.append(
                "row_label_not_zero"
            )

    if (
        "attack_type"
        in frame.columns
        and not frame[
            "attack_type"
        ].map(
            _is_missing_attack
        ).all()
    ):
        blockers.append(
            "row_attack_type_present"
        )

    if (
        "is_synthetic"
        in frame.columns
    ):
        synthetic_values = (
            frame[
                "is_synthetic"
            ].map(
                _bool_value
            )
        )

        if (
            synthetic_values.isna().any()
            or synthetic_values.any()
        ):
            blockers.append(
                "row_is_synthetic_not_false"
            )

    if (
        "ssid_hash"
        in frame.columns
        and not _hash_values_valid(
            frame[
                "ssid_hash"
            ]
        )
    ):
        blockers.append(
            "ssid_hash_not_sha256"
        )

    if (
        "bssid_hash"
        in frame.columns
        and not _hash_values_valid(
            frame[
                "bssid_hash"
            ]
        )
    ):
        blockers.append(
            "bssid_hash_not_sha256"
        )

    bssid_coverage = (
        float(
            frame[
                "bssid_hash"
            ].notna().mean()
        )
        if (
            rows
            and "bssid_hash"
            in frame.columns
        )
        else 0.0
    )

    if (
        bssid_coverage
        < MIN_BSSID_HASH_COVERAGE
    ):
        blockers.append(
            "bssid_hash_coverage_below_099"
        )

    candidate_completeness = (
        float(
            frame[
                list(
                    CANDIDATE_FIELDS
                )
            ].notna().all(
                axis=1
            ).mean()
        )
        if (
            rows
            and set(
                CANDIDATE_FIELDS
            ).issubset(
                frame.columns
            )
        )
        else 0.0
    )

    if (
        candidate_completeness
        < MIN_CANDIDATE_COMPLETENESS
    ):
        blockers.append(
            "desktop_candidate_completeness_below_070"
        )

    environments = []

    if (
        "environment"
        in frame.columns
    ):
        environments = sorted({
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

    manifest_environment = str(
        manifest.get(
            "environment",
            "",
        )
    ).strip()

    if not environments:
        blockers.append(
            "environment_missing"
        )

    elif len(
        environments
    ) != 1:
        blockers.append(
            "multiple_environments_in_session"
        )

    if (
        manifest_environment
        and environments
        and manifest_environment
        != environments[
            0
        ]
    ):
        blockers.append(
            "manifest_environment_mismatch"
        )

    environment = (
        environments[
            0
        ]
        if len(
            environments
        )
        == 1
        else (
            manifest_environment
            or None
        )
    )

    time_start, time_end = (
        _temporal_bounds(
            frame
        )
    )

    if (
        time_start is None
        or time_end is None
    ):
        warnings.append(
            "captured_at_utc_unavailable"
        )

    content_fingerprint = (
        _canonical_content_fingerprint(
            frame
        )
    )

    blockers = sorted(
        set(
            blockers
        )
    )

    warnings = sorted(
        set(
            warnings
        )
    )

    return {
        "session_id":
            folder.name,
        "environment":
            environment,
        "rows":
            rows,
        "scan_count":
            scan_count,
        "runtime_ready":
            bool(
                manifest.get(
                    "runtime_ready",
                    False,
                )
            ),
        "source_scans_sha256":
            source_scans_sha256,
        "observations_sha256":
            actual_observations_sha,
        "content_fingerprint":
            content_fingerprint,
        "bssid_hash_coverage":
            bssid_coverage,
        "desktop_candidate_completeness":
            candidate_completeness,
        "time_start_utc":
            time_start,
        "time_end_utc":
            time_end,
        "valid":
            not blockers,
        "blockers":
            blockers,
        "warnings":
            warnings,
        "observations_path":
            str(
                observations_path
            ),
        "manifest_path":
            str(
                manifest_path
            ),
    }


def _overlap_pairs(
    sessions: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, str]
]:
    parsed = []

    for item in sessions:
        start = pd.to_datetime(
            item.get(
                "time_start_utc"
            ),
            errors="coerce",
            utc=True,
        )

        end = pd.to_datetime(
            item.get(
                "time_end_utc"
            ),
            errors="coerce",
            utc=True,
        )

        if (
            pd.isna(
                start
            )
            or pd.isna(
                end
            )
        ):
            continue

        parsed.append(
            (
                str(
                    item[
                        "session_id"
                    ]
                ),
                start,
                end,
            )
        )

    pairs = []

    for index, (
        left_id,
        left_start,
        left_end,
    ) in enumerate(
        parsed
    ):
        for (
            right_id,
            right_start,
            right_end,
        ) in parsed[
            index
            + 1:
        ]:
            if (
                left_start
                <= right_end
                and right_start
                <= left_end
            ):
                pairs.append({
                    "session_a":
                        left_id,
                    "session_b":
                        right_id,
                })

    return pairs


def _public_session_summary(
    item: dict[str, Any],
) -> dict[str, Any]:
    return {
        key:
            value
        for key, value
        in item.items()
        if key not in {
            "observations_path",
            "manifest_path",
        }
    }


def _candidate_reference_coverage(
    sessions: list[
        dict[str, Any]
    ],
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Dry-run the deterministic split/reference before anything is frozen.

    The desktop feature contract needs a known SSID/BSSID/security context.
    This gate prevents committing an immutable split whose model-train,
    validation or test-normal rows would mostly become ineligible because the
    reference session did not observe the same network context.
    """
    plan = make_split_plan(
        sessions,
        seed=seed,
    )

    if plan.get(
        "status"
    ) != "ready":
        return {
            "ready":
                False,
            "status":
                "not_enough_sessions_for_candidate_reference",
            "split_status":
                plan.get(
                    "status"
                ),
            "coverage":
                {},
        }

    assignments = (
        plan[
            "assignments"
        ]
    )

    frames: dict[
        str,
        pd.DataFrame,
    ] = {}

    for item in assignments:
        session_id = str(
            item[
                "session_id"
            ]
        )

        frame = pd.read_csv(
            item[
                "observations_path"
            ]
        )

        frames[
            session_id
        ] = frame

    reference_parts = [
        frames[
            str(
                item[
                    "session_id"
                ]
            )
        ]
        for item in assignments
        if item[
            "split"
        ] == "reference"
    ]

    if not reference_parts:
        return {
            "ready":
                False,
            "status":
                "candidate_reference_missing",
            "coverage":
                {},
        }

    reference = build_desktop_reference(
        pd.concat(
            reference_parts,
            ignore_index=True,
        )
    )

    if int(
        reference.get(
            "ssid_profile_count",
            0,
        )
    ) == 0:
        return {
            "ready":
                False,
            "status":
                "candidate_reference_has_no_ssid_profiles",
            "coverage":
                {},
            "reference_session_ids": [
                str(
                    item[
                        "session_id"
                    ]
                )
                for item in assignments
                if item[
                    "split"
                ] == "reference"
            ],
        }

    coverage = {}

    for split in (
        "model_train",
        "validation",
        "test_normal",
    ):
        parts = [
            frames[
                str(
                    item[
                        "session_id"
                    ]
                )
            ]
            for item in assignments
            if item[
                "split"
            ] == split
        ]

        if not parts:
            coverage[
                split
            ] = {
                "rows":
                    0,
                "eligible":
                    0,
                "eligible_rate":
                    0.0,
            }
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

        eligible = (
            features[
                "context_available"
            ].astype(
                bool
            )
            & features[
                "feature_complete"
            ].astype(
                bool
            )
        )

        coverage[
            split
        ] = {
            "rows":
                int(
                    len(
                        features
                    )
                ),
            "eligible":
                int(
                    eligible.sum()
                ),
            "eligible_rate":
                float(
                    eligible.mean()
                )
                if len(
                    eligible
                )
                else 0.0,
        }

    below_threshold = [
        split
        for split, item
        in coverage.items()
        if float(
            item[
                "eligible_rate"
            ]
        ) < MIN_REFERENCE_ELIGIBLE_RATE
    ]

    return {
        "ready":
            not below_threshold,
        "status": (
            "ready"
            if not below_threshold
            else "candidate_reference_coverage_below_minimum"
        ),
        "minimum_eligible_rate":
            MIN_REFERENCE_ELIGIBLE_RATE,
        "reference_session_ids": [
            str(
                item[
                    "session_id"
                ]
            )
            for item in assignments
            if item[
                "split"
            ] == "reference"
        ],
        "coverage":
            coverage,
        "splits_below_minimum":
            below_threshold,
    }


def run_scientific_preflight(
    interim_root: str | Path,
) -> dict[str, Any]:
    root = Path(
        interim_root
    )

    folders = (
        sorted(
            folder
            for folder
            in root.iterdir()
            if folder.is_dir()
        )
        if root.exists()
        else []
    )

    sessions = [
        inspect_interim_session(
            folder
        )
        for folder in folders
    ]

    fingerprint_groups: dict[
        str,
        list[str],
    ] = defaultdict(
        list
    )

    for item in sessions:
        fingerprint = item.get(
            "content_fingerprint"
        )

        if fingerprint:
            fingerprint_groups[
                str(
                    fingerprint
                )
            ].append(
                str(
                    item[
                        "session_id"
                    ]
                )
            )

    duplicate_content_groups = [
        {
            "content_fingerprint":
                fingerprint,
            "session_ids":
                sorted(
                    session_ids
                ),
        }
        for fingerprint, session_ids
        in fingerprint_groups.items()
        if len(
            session_ids
        )
        > 1
    ]

    duplicate_ids = {
        session_id
        for group
        in duplicate_content_groups
        for session_id
        in group[
            "session_ids"
        ]
    }

    if duplicate_ids:
        for item in sessions:
            if (
                item[
                    "session_id"
                ]
                in duplicate_ids
            ):
                item[
                    "blockers"
                ] = sorted(
                    set(
                        item[
                            "blockers"
                        ]
                    )
                    | {
                        "duplicate_session_content"
                    }
                )

                item[
                    "valid"
                ] = False

    valid_sessions = [
        item
        for item in sessions
        if item[
            "valid"
        ]
    ]

    invalid_sessions = [
        item
        for item in sessions
        if not item[
            "valid"
        ]
    ]

    environment_summary = dict(
        sorted(
            Counter(
                str(
                    item.get(
                        "environment"
                    )
                    or "<missing>"
                )
                for item
                in valid_sessions
            ).items()
        )
    )

    cohort_environments = [
        environment
        for environment
        in environment_summary
        if environment
        != "<missing>"
    ]

    mixed_environment_cohort = (
        len(
            cohort_environments
        )
        > MAX_NORMAL_COHORT_ENVIRONMENTS
    )

    split_sessions = [
        {
            "session_id":
                item[
                    "session_id"
                ],
            "environment":
                item[
                    "environment"
                ],
            "observations_path":
                item[
                    "observations_path"
                ],
            "manifest_path":
                item[
                    "manifest_path"
                ],
            "rows":
                item[
                    "rows"
                ],
            "runtime_ready":
                True,
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
            "time_start_utc":
                item[
                    "time_start_utc"
                ],
            "time_end_utc":
                item[
                    "time_end_utc"
                ],
        }
        for item
        in valid_sessions
    ]

    candidate_reference_coverage = (
        _candidate_reference_coverage(
            split_sessions
        )
        if (
            len(
                valid_sessions
            )
            >= MINIMUM_SESSIONS
            and not mixed_environment_cohort
        )
        else {
            "ready":
                False,
            "status": (
                "mixed_environment_cohort"
                if mixed_environment_cohort
                else "not_enough_sessions_for_candidate_reference"
            ),
            "coverage":
                {},
        }
    )

    temporal_overlap = (
        _overlap_pairs(
            valid_sessions
        )
    )

    global_blockers = sorted({
        blocker
        for item
        in invalid_sessions
        for blocker
        in item[
            "blockers"
        ]
    })

    if mixed_environment_cohort:
        global_blockers.append(
            "multiple_environments_in_desktop_candidate_v1_normal_cohort"
        )

    if (
        len(
            valid_sessions
        )
        >= MINIMUM_SESSIONS
        and not mixed_environment_cohort
        and not candidate_reference_coverage[
            "ready"
        ]
    ):
        global_blockers.append(
            "candidate_reference_eligible_rate_below_070"
        )

    global_blockers = sorted(
        set(
            global_blockers
        )
    )

    warnings = []

    if temporal_overlap:
        warnings.append(
            "temporal_overlap_between_sessions"
        )

    if not sessions:
        status = (
            "blocked_no_real_sessions"
        )

    elif duplicate_content_groups:
        status = (
            "blocked_duplicate_session_content"
        )

    elif invalid_sessions:
        status = (
            "blocked_invalid_sessions"
        )

    elif len(
        valid_sessions
    ) < MINIMUM_SESSIONS:
        status = (
            "blocked_insufficient_valid_sessions"
        )

    elif mixed_environment_cohort:
        status = (
            "blocked_mixed_normal_environments"
        )

    elif not candidate_reference_coverage[
        "ready"
    ]:
        status = (
            "blocked_candidate_reference_coverage"
        )

    else:
        status = (
            "ready_for_split_freeze"
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            status,
        "minimum_required_sessions":
            MINIMUM_SESSIONS,
        "discovered_session_folders":
            len(
                sessions
            ),
        "valid_session_count":
            len(
                valid_sessions
            ),
        "invalid_session_count":
            len(
                invalid_sessions
            ),
        "duplicate_content_groups":
            duplicate_content_groups,
        "environment_summary":
            environment_summary,
        "normal_cohort_environment": (
            cohort_environments[
                0
            ]
            if len(
                cohort_environments
            )
            == 1
            else None
        ),
        "max_normal_cohort_environments":
            MAX_NORMAL_COHORT_ENVIRONMENTS,
        "candidate_reference_coverage":
            candidate_reference_coverage,
        "temporal_overlap_pairs":
            temporal_overlap,
        "global_blockers":
            global_blockers,
        "warnings":
            warnings,
        "sessions": [
            _public_session_summary(
                item
            )
            for item
            in sessions
        ],
        "_sessions_for_split":
            split_sessions,
    }


def public_preflight_report(
    report: dict[
        str,
        Any,
    ],
) -> dict[
    str,
    Any,
]:
    return {
        key:
            value
        for key, value
        in report.items()
        if not key.startswith(
            "_"
        )
    }


def save_preflight_report(
    report: dict[
        str,
        Any,
    ],
    path: str | Path,
) -> None:
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            public_preflight_report(
                report
            ),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _assignment_digest_payload(
    assignments: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    return sorted(
        [
            {
                "session_id":
                    str(
                        item[
                            "session_id"
                        ]
                    ),
                "split":
                    str(
                        item[
                            "split"
                        ]
                    ),
                "source_scans_sha256":
                    str(
                        item[
                            "source_scans_sha256"
                        ]
                    ),
                "observations_sha256":
                    str(
                        item[
                            "observations_sha256"
                        ]
                    ),
                "content_fingerprint":
                    str(
                        item[
                            "content_fingerprint"
                        ]
                    ),
            }
            for item
            in assignments
        ],
        key=lambda item:
            item[
                "session_id"
            ],
    )


def compute_split_digest(
    assignments: list[
        dict[str, Any]
    ],
) -> str:
    return canonical_json_sha256(
        _assignment_digest_payload(
            assignments
        )
    )


def _validate_split_disjoint(
    assignments: list[
        dict[str, Any]
    ],
) -> None:
    session_ids = [
        str(
            item[
                "session_id"
            ]
        )
        for item
        in assignments
    ]

    if len(
        session_ids
    ) != len(
        set(
            session_ids
        )
    ):
        raise ScientificIntegrityError(
            "Frozen split contains a session_id more than once."
        )

    invalid_splits = sorted({
        str(
            item.get(
                "split"
            )
        )
        for item
        in assignments
        if item.get(
            "split"
        )
        not in REQUIRED_SPLITS
    })

    if invalid_splits:
        raise ScientificIntegrityError(
            "Frozen split contains unknown split names: "
            + ", ".join(
                invalid_splits
            )
        )

    counts = {
        split:
            sum(
                1
                for item
                in assignments
                if item[
                    "split"
                ]
                == split
            )
        for split
        in REQUIRED_SPLITS
    }

    if (
        counts[
            "reference"
        ]
        != 1
        or counts[
            "model_train"
        ]
        < 2
        or counts[
            "validation"
        ]
        < 1
        or counts[
            "test_normal"
        ]
        < 1
    ):
        raise ScientificIntegrityError(
            "Frozen split no longer satisfies the minimum allocation."
        )


def _inventory_digest(
    sessions: list[
        dict[str, Any]
    ],
) -> str:
    return canonical_json_sha256(
        sorted(
            [
                {
                    "session_id":
                        item[
                            "session_id"
                        ],
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
                for item
                in sessions
            ],
            key=lambda item:
                item[
                    "session_id"
                ],
        )
    )


def freeze_or_validate_split_plan(
    sessions: list[
        dict[str, Any]
    ],
    plan_path: str | Path,
    freeze_path: str | Path,
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    plan_path = Path(
        plan_path
    )

    freeze_path = Path(
        freeze_path
    )

    current_by_id = {
        str(
            item[
                "session_id"
            ]
        ):
            item
        for item
        in sessions
    }

    existing_plan = (
        _json(
            plan_path
        )
        if plan_path.exists()
        else None
    )

    if (
        existing_plan
        and existing_plan.get(
            "status"
        )
        == "ready"
    ):
        if not freeze_path.exists():
            raise ScientificIntegrityError(
                "Ready split plan exists without scientific_freeze.json."
            )

        freeze = _json(
            freeze_path
        )

        plan_file_sha = (
            sha256_file(
                plan_path
            )
        )

        if (
            freeze.get(
                "split_plan_file_sha256"
            )
            != plan_file_sha
        ):
            raise ScientificIntegrityError(
                "Frozen split plan file changed after freeze."
            )

        assignments = (
            existing_plan.get(
                "assignments"
            )
            or []
        )

        _validate_split_disjoint(
            assignments
        )

        split_digest = (
            compute_split_digest(
                assignments
            )
        )

        if (
            existing_plan.get(
                "split_digest"
            )
            != split_digest
            or freeze.get(
                "split_digest"
            )
            != split_digest
        ):
            raise ScientificIntegrityError(
                "Frozen split digest mismatch."
            )

        assigned_ids = {
            str(
                item[
                    "session_id"
                ]
            )
            for item
            in assignments
        }

        missing_sessions = sorted(
            assigned_ids
            - set(
                current_by_id
            )
        )

        if missing_sessions:
            raise ScientificIntegrityError(
                "Frozen source session is missing: "
                + ", ".join(
                    missing_sessions
                )
            )

        frozen_sources = (
            freeze.get(
                "source_hashes"
            )
            or {}
        )

        for session_id in sorted(
            assigned_ids
        ):
            current = (
                current_by_id[
                    session_id
                ]
            )

            expected = (
                frozen_sources.get(
                    session_id
                )
            )

            if not expected:
                raise ScientificIntegrityError(
                    f"Frozen source hashes missing for {session_id}."
                )

            for key in (
                "source_scans_sha256",
                "observations_sha256",
                "content_fingerprint",
            ):
                if (
                    expected.get(
                        key
                    )
                    != current.get(
                        key
                    )
                ):
                    raise ScientificIntegrityError(
                        f"Frozen source mutation detected for {session_id}: {key}."
                    )

        unassigned = sorted(
            set(
                current_by_id
            )
            - assigned_ids
        )

        resolved_assignments = []

        for item in assignments:
            current = (
                current_by_id[
                    str(
                        item[
                            "session_id"
                        ]
                    )
                ]
            )

            resolved_assignments.append({
                **item,
                "observations_path":
                    current[
                        "observations_path"
                    ],
                "manifest_path":
                    current[
                        "manifest_path"
                    ],
            })

        return {
            "status":
                "ready_frozen",
            "new_freeze_created":
                False,
            "split_digest":
                split_digest,
            "split_plan_file_sha256":
                plan_file_sha,
            "scientific_freeze_sha256":
                sha256_file(
                    freeze_path
                ),
            "assignments":
                resolved_assignments,
            "unassigned_sessions_after_freeze":
                unassigned,
            "plan":
                existing_plan,
            "freeze":
                freeze,
        }

    if freeze_path.exists():
        raise ScientificIntegrityError(
            "scientific_freeze.json exists without a ready split plan."
        )

    plan = make_split_plan(
        sessions,
        seed=seed,
    )

    if (
        plan[
            "status"
        ]
        != "ready"
    ):
        plan[
            "schema_version"
        ] = (
            "desktop_session_split_plan_v2"
        )

        plan[
            "integrity_gate"
        ] = (
            SCHEMA_VERSION
        )

        save_split_plan(
            plan,
            plan_path,
        )

        return {
            "status":
                "blocked_insufficient_sessions",
            "new_freeze_created":
                False,
            "assignments":
                [],
            "unassigned_sessions_after_freeze":
                [],
            "plan":
                plan,
        }

    enriched = []

    for assignment in (
        plan[
            "assignments"
        ]
    ):
        current = (
            current_by_id[
                str(
                    assignment[
                        "session_id"
                    ]
                )
            ]
        )

        enriched.append({
            **assignment,
            "source_scans_sha256":
                current[
                    "source_scans_sha256"
                ],
            "observations_sha256":
                current[
                    "observations_sha256"
                ],
            "content_fingerprint":
                current[
                    "content_fingerprint"
                ],
            "time_start_utc":
                current[
                    "time_start_utc"
                ],
            "time_end_utc":
                current[
                    "time_end_utc"
                ],
        })

    _validate_split_disjoint(
        enriched
    )

    split_digest = (
        compute_split_digest(
            enriched
        )
    )

    plan[
        "schema_version"
    ] = (
        "desktop_session_split_plan_v2"
    )

    plan[
        "assignments"
    ] = enriched

    plan[
        "split_digest"
    ] = split_digest

    plan[
        "valid_session_inventory_digest_at_freeze"
    ] = _inventory_digest(
        sessions
    )

    plan[
        "frozen_at_utc"
    ] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    plan[
        "integrity_gate"
    ] = (
        SCHEMA_VERSION
    )

    save_split_plan(
        plan,
        plan_path,
    )

    plan_file_sha = (
        sha256_file(
            plan_path
        )
    )

    source_hashes = {
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
        for item
        in enriched
    }

    cohort_environments = sorted({
        str(
            item.get(
                "environment"
            )
        )
        for item
        in enriched
        if item.get(
            "environment"
        )
    })

    freeze = {
        "schema_version":
            FREEZE_SCHEMA_VERSION,
        "status":
            "frozen",
        "seed":
            int(
                seed
            ),
        "split_digest":
            split_digest,
        "split_plan_file_sha256":
            plan_file_sha,
        "frozen_session_ids":
            sorted(
                source_hashes
            ),
        "source_hashes":
            source_hashes,
        "normal_cohort_environments":
            cohort_environments,
        "normal_cohort_environment": (
            cohort_environments[
                0
            ]
            if len(
                cohort_environments
            )
            == 1
            else None
        ),
        "scientific_rules": [
            "Assigned source observations are immutable after freeze.",
            "A split assignment is immutable after freeze.",
            "New sessions after freeze are not assigned automatically.",
            "Reference/model-train/validation/test_normal remain session-disjoint.",
            "Changing the frozen protocol requires an explicit new version, not overwrite.",
        ],
    }

    freeze_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    freeze_path.write_text(
        json.dumps(
            freeze,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "status":
            "ready_frozen",
        "new_freeze_created":
            True,
        "split_digest":
            split_digest,
        "split_plan_file_sha256":
            plan_file_sha,
        "scientific_freeze_sha256":
            sha256_file(
                freeze_path
            ),
        "assignments":
            enriched,
        "unassigned_sessions_after_freeze":
            [],
        "plan":
            plan,
        "freeze":
            freeze,
    }


def verify_prepared_freeze_integrity(
    prepared_root: str | Path,
) -> dict[str, Any]:
    root = Path(
        prepared_root
    )

    required = {
        "plan":
            root
            / "session_split_plan.json",
        "freeze":
            root
            / "scientific_freeze.json",
        "reference":
            root
            / "desktop_normal_reference.json",
        "manifest":
            root
            / "preparation_manifest.json",
    }

    missing = [
        name
        for name, path
        in required.items()
        if not path.exists()
    ]

    if missing:
        return {
            "ready":
                False,
            "status":
                "blocked_scientific_freeze_missing",
            "missing":
                missing,
        }

    try:
        plan = _json(
            required[
                "plan"
            ]
        )

        freeze = _json(
            required[
                "freeze"
            ]
        )

        reference = _json(
            required[
                "reference"
            ]
        )

        manifest = _json(
            required[
                "manifest"
            ]
        )

        plan_sha = (
            sha256_file(
                required[
                    "plan"
                ]
            )
        )

        freeze_sha = (
            sha256_file(
                required[
                    "freeze"
                ]
            )
        )

        reference_sha = (
            sha256_file(
                required[
                    "reference"
                ]
            )
        )

        assignments = (
            plan.get(
                "assignments"
            )
            or []
        )

        _validate_split_disjoint(
            assignments
        )

        split_digest = (
            compute_split_digest(
                assignments
            )
        )

        checks = [
            (
                freeze.get(
                    "split_plan_file_sha256"
                )
                == plan_sha,
                "split_plan_file_sha256",
            ),
            (
                plan.get(
                    "split_digest"
                )
                == split_digest,
                "plan_split_digest",
            ),
            (
                freeze.get(
                    "split_digest"
                )
                == split_digest,
                "freeze_split_digest",
            ),
            (
                reference.get(
                    "split_digest"
                )
                == split_digest,
                "reference_split_digest",
            ),
            (
                manifest.get(
                    "split_digest"
                )
                == split_digest,
                "manifest_split_digest",
            ),
            (
                manifest.get(
                    "scientific_freeze_sha256"
                )
                == freeze_sha,
                "scientific_freeze_sha256",
            ),
            (
                manifest.get(
                    "reference_file_sha256"
                )
                == reference_sha,
                "reference_file_sha256",
            ),
        ]

        failed = [
            name
            for ok, name
            in checks
            if not ok
        ]

        if failed:
            return {
                "ready":
                    False,
                "status":
                    "blocked_scientific_freeze_integrity_mismatch",
                "failed_checks":
                    failed,
            }

        return {
            "ready":
                True,
            "status":
                "ready",
            "split_digest":
                split_digest,
            "scientific_freeze_sha256":
                freeze_sha,
            "reference_file_sha256":
                reference_sha,
        }

    except (
        ScientificIntegrityError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        return {
            "ready":
                False,
            "status":
                "blocked_scientific_freeze_integrity_mismatch",
            "reason":
                str(
                    exc
                ),
        }


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate real Windows normal sessions before the desktop "
            "reference/split freeze."
        )
    )

    parser.add_argument(
        "--interim-root",
        default=(
            "data/interim/own/windows"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "reports/desktop/"
            "desktop_scientific_preflight_step44.json"
        ),
    )

    args = parser.parse_args(
        argv
    )

    report = (
        run_scientific_preflight(
            args.interim_root
        )
    )

    save_preflight_report(
        report,
        args.output,
    )

    print(
        json.dumps(
            public_preflight_report(
                report
            ),
            indent=2,
            ensure_ascii=False,
        )
    )

    if (
        report[
            "status"
        ]
        == "ready_for_split_freeze"
    ):
        return 0

    if report[
        "status"
    ] in {
        "blocked_no_real_sessions",
        "blocked_insufficient_valid_sessions",
    }:
        return 8

    return 9


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
