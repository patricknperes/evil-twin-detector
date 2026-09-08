from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from desktop.windows.prepare_desktop_reference import (
    prepare_desktop_reference,
)
from desktop.windows.scientific_preflight import (
    ScientificIntegrityError,
    freeze_or_validate_split_plan,
    run_scientific_preflight,
    sha256_file,
    verify_prepared_freeze_integrity,
)


def _hash(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def _write_session(
    root: Path,
    session_id: str,
    *,
    environment: str = "lab-a",
    captured_at: str = "2026-09-01T10:00:00Z",
    fingerprint_seed: str | None = None,
    include_clear_ssid: bool = False,
) -> Path:
    folder = (
        root
        / session_id
    )

    folder.mkdir(
        parents=True,
        exist_ok=False,
    )

    seed = (
        fingerprint_seed
        or session_id
    )

    frame = pd.DataFrame({
        "source_dataset":
            [
                "own_windows"
            ] * 3,
        "session_id":
            [
                session_id
            ] * 3,
        "environment":
            [
                environment
            ] * 3,
        "captured_at_utc":
            [
                captured_at
            ] * 3,
        "scan_index":
            [
                0,
                1,
                2,
            ],
        "interface_guid":
            [
                "GUID"
            ] * 3,
        "ssid_hash":
            [
                _hash(
                    "ssid-shared-normal-cohort"
                )
            ] * 3,
        "bssid_hash":
            [
                _hash(
                    f"bssid-{seed}"
                )
            ] * 3,
        "security_type":
            [
                "WPA2_OR_NEWER"
            ] * 3,
        "security_strength":
            [
                3
            ] * 3,

        # Novas colunas usadas pelas 7 features desktop.
        "ds_parameter_channel":
            [
                6,
                6,
                6,
            ],
        "beacon_interval_ms":
            [
                100.0,
                100.0,
                100.0,
            ],
        "ssid_not_broadcast":
            [
                False,
                False,
                False,
            ],

        "label":
            [
                0
            ] * 3,
        "attack_type":
            [
                None
            ] * 3,
        "is_synthetic":
            [
                False
            ] * 3,
    })

    if include_clear_ssid:
        frame[
            "ssid"
        ] = "clear-network"

    observations = (
        folder
        / "observations.csv.gz"
    )

    frame.to_csv(
        observations,
        index=False,
        compression="gzip",
    )

    manifest = {
        "schema_version":
            "own_windows_interim_import_v1",
        "session_id":
            session_id,
        "source_dataset":
            "own_windows",
        "source_scans_sha256":
            _hash(
                f"raw-{session_id}"
            ),
        "source_sha256_verified":
            True,
        "interim_observations_sha256":
            sha256_file(
                observations
            ),
        "runtime_ready":
            True,
        "rows":
            3,
        "scan_count":
            3,
        "label":
            0,
        "attack_present":
            False,
        "environment":
            environment,
    }

    (
        folder
        / "import_manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    return folder


def _five_sessions(
    root: Path,
) -> None:
    for index in range(
        5
    ):
        _write_session(
            root,
            f"session-{index}",
            captured_at=(
                f"2026-09-01T10:{index:02d}:00Z"
            ),
        )


def test_no_real_sessions_is_explicitly_blocked(
    tmp_path,
):
    result = (
        run_scientific_preflight(
            tmp_path
            / "interim"
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_no_real_sessions"
    )

    assert (
        result[
            "valid_session_count"
        ]
        == 0
    )


def test_clear_wifi_identifier_column_blocks_session(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _write_session(
        interim,
        "session-clear",
        include_clear_ssid=True,
    )

    result = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_invalid_sessions"
    )

    assert (
        "clear_wifi_identifier_columns_present"
        in result[
            "sessions"
        ][0][
            "blockers"
        ]
    )


def test_duplicate_observation_content_across_session_ids_blocks(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    # Same content apart from session_id/environment. raw-source hashes may
    # differ, but the canonical observation fingerprint catches the copy.
    _write_session(
        interim,
        "session-a",
        fingerprint_seed="same",
        captured_at="2026-09-01T10:00:00Z",
    )

    _write_session(
        interim,
        "session-b",
        fingerprint_seed="same",
        captured_at="2026-09-01T10:00:00Z",
    )

    result = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_duplicate_session_content"
    )

    assert len(
        result[
            "duplicate_content_groups"
        ]
    ) == 1


def test_environment_summary_and_temporal_overlap_warning(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _write_session(
        interim,
        "session-a",
        environment="home",
        captured_at="2026-09-01T10:00:00Z",
    )

    _write_session(
        interim,
        "session-b",
        environment="lab",
        captured_at="2026-09-01T10:00:00Z",
    )

    result = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        result[
            "environment_summary"
        ]
        == {
            "home":
                1,
            "lab":
                1,
        }
    )

    assert (
        "temporal_overlap_between_sessions"
        in result[
            "warnings"
        ]
    )


def test_mixed_normal_environments_block_desktop_candidate_freeze(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    for index in range(
        5
    ):
        _write_session(
            interim,
            f"session-{index}",
            environment=(
                "home"
                if index < 3
                else "lab"
            ),
            captured_at=(
                f"2026-09-01T10:{index:02d}:00Z"
            ),
        )

    result = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_mixed_normal_environments"
    )

    assert (
        "multiple_environments_in_desktop_candidate_v1_normal_cohort"
        in result[
            "global_blockers"
        ]
    )


def test_candidate_reference_coverage_blocks_non_overlapping_ssids(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    for index in range(
        5
    ):
        folder = _write_session(
            interim,
            f"session-{index}",
            captured_at=(
                f"2026-09-01T11:{index:02d}:00Z"
            ),
        )

        observations = (
            folder
            / "observations.csv.gz"
        )

        frame = pd.read_csv(
            observations
        )

        frame[
            "ssid_hash"
        ] = _hash(
            f"isolated-ssid-{index}"
        )

        frame.to_csv(
            observations,
            index=False,
            compression="gzip",
        )

        manifest_path = (
            folder
            / "import_manifest.json"
        )

        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        manifest[
            "interim_observations_sha256"
        ] = sha256_file(
            observations
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
            ),
            encoding="utf-8",
        )

    result = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        result[
            "status"
        ]
        == "blocked_candidate_reference_coverage"
    )

    assert (
        result[
            "candidate_reference_coverage"
        ][
            "ready"
        ]
        is False
    )


def test_ready_freeze_is_immutable_and_new_session_is_not_auto_assigned(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _five_sessions(
        interim
    )

    preflight = (
        run_scientific_preflight(
            interim
        )
    )

    assert (
        preflight[
            "status"
        ]
        == "ready_for_split_freeze"
    )

    plan_path = (
        tmp_path
        / "session_split_plan.json"
    )

    freeze_path = (
        tmp_path
        / "scientific_freeze.json"
    )

    first = (
        freeze_or_validate_split_plan(
            preflight[
                "_sessions_for_split"
            ],
            plan_path,
            freeze_path,
        )
    )

    assert (
        first[
            "new_freeze_created"
        ]
        is True
    )

    frozen_assignments = {
        item[
            "session_id"
        ]:
            item[
                "split"
            ]
        for item
        in first[
            "assignments"
        ]
    }

    _write_session(
        interim,
        "session-new",
        captured_at="2026-09-01T11:00:00Z",
    )

    second_preflight = (
        run_scientific_preflight(
            interim
        )
    )

    second = (
        freeze_or_validate_split_plan(
            second_preflight[
                "_sessions_for_split"
            ],
            plan_path,
            freeze_path,
        )
    )

    assert (
        second[
            "new_freeze_created"
        ]
        is False
    )

    assert (
        second[
            "unassigned_sessions_after_freeze"
        ]
        == [
            "session-new"
        ]
    )

    assert {
        item[
            "session_id"
        ]:
            item[
                "split"
            ]
        for item
        in second[
            "assignments"
        ]
    } == frozen_assignments


def test_mutating_frozen_source_data_fails(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _five_sessions(
        interim
    )

    preflight = (
        run_scientific_preflight(
            interim
        )
    )

    plan_path = (
        tmp_path
        / "session_split_plan.json"
    )

    freeze_path = (
        tmp_path
        / "scientific_freeze.json"
    )

    frozen = (
        freeze_or_validate_split_plan(
            preflight[
                "_sessions_for_split"
            ],
            plan_path,
            freeze_path,
        )
    )

    target_session = (
        frozen[
            "assignments"
        ][0][
            "session_id"
        ]
    )

    observations = (
        interim
        / target_session
        / "observations.csv.gz"
    )

    frame = pd.read_csv(
        observations
    )

    frame.loc[
        0,
        "security_strength"
    ] = 0

    frame.to_csv(
        observations,
        index=False,
        compression="gzip",
    )

    # Keep the import manifest internally self-consistent to make sure the
    # scientific freeze, not only the import SHA, catches the mutation.
    manifest_path = (
        interim
        / target_session
        / "import_manifest.json"
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest[
        "interim_observations_sha256"
    ] = sha256_file(
        observations
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    changed_preflight = (
        run_scientific_preflight(
            interim
        )
    )

    with pytest.raises(
        ScientificIntegrityError
    ):
        freeze_or_validate_split_plan(
            changed_preflight[
                "_sessions_for_split"
            ],
            plan_path,
            freeze_path,
        )


def test_mutating_frozen_split_plan_file_fails(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _five_sessions(
        interim
    )

    preflight = (
        run_scientific_preflight(
            interim
        )
    )

    plan_path = (
        tmp_path
        / "session_split_plan.json"
    )

    freeze_path = (
        tmp_path
        / "scientific_freeze.json"
    )

    freeze_or_validate_split_plan(
        preflight[
            "_sessions_for_split"
        ],
        plan_path,
        freeze_path,
    )

    plan = json.loads(
        plan_path.read_text(
            encoding="utf-8"
        )
    )

    plan[
        "assignments"
    ][0][
        "split"
    ] = "model_train"

    plan_path.write_text(
        json.dumps(
            plan,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ScientificIntegrityError
    ):
        freeze_or_validate_split_plan(
            preflight[
                "_sessions_for_split"
            ],
            plan_path,
            freeze_path,
        )


def test_reference_records_frozen_hash_chain_and_step20_gate_verifies_it(
    tmp_path,
):
    interim = (
        tmp_path
        / "interim"
    )

    _five_sessions(
        interim
    )

    output = (
        tmp_path
        / "processed"
    )

    result = (
        prepare_desktop_reference(
            interim,
            output,
        )
    )

    assert (
        result[
            "status"
        ]
        == "reference_and_features_ready_no_model_training"
    )

    assert (
        result[
            "split_digest"
        ]
    )

    assert (
        result[
            "scientific_freeze_sha256"
        ]
    )

    reference = json.loads(
        (
            output
            / "desktop_normal_reference.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        reference[
            "split_digest"
        ]
        == result[
            "split_digest"
        ]
    )

    assert (
        reference[
            "reference_source_hashes"
        ]
    )

    integrity = (
        verify_prepared_freeze_integrity(
            output
        )
    )

    assert (
        integrity[
            "ready"
        ]
        is True
    )

    # Reference mutation after preparation must block the ML gate.
    reference[
        "ssid_profile_count"
    ] = 999

    (
        output
        / "desktop_normal_reference.json"
    ).write_text(
        json.dumps(
            reference,
            indent=2,
        ),
        encoding="utf-8",
    )

    integrity_after = (
        verify_prepared_freeze_integrity(
            output
        )
    )

    assert (
        integrity_after[
            "ready"
        ]
        is False
    )
