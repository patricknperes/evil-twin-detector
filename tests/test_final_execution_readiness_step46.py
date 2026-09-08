from __future__ import annotations

import json

import desktop.final_readiness as final_readiness_module

from backend.runtime_paths import (
    resource_root,
)
from desktop.final_readiness import (
    ALLOWED_STATUSES,
    inspect_final_execution_readiness,
    readiness_markdown,
)


EXPECTED_STAGE_IDS = [
    "implementation_validation",
    "desktop_integration_scenarios",
    "windows_execution_host",
    "windows_normal_collection",
    "scientific_preflight",
    "frozen_split_reference",
    "ml_ready_scaler_lineage",
    "ocsvm_threshold_runtime_chain",
    "controlled_real_attack_data",
    "controlled_attack_features",
    "fixed_artifact_final_evaluation",
    "tcc_final_results_bundle",
    "frontend_source_packaging_contract",
    "frontend_test_typecheck_build",
    "renderer_electron_e2e",
    "backend_pyinstaller",
    "nsis_installer",
    "windows_code_signing",
]


def _validation_file(
    tmp_path,
):
    path = (
        tmp_path
        / "validation.json"
    )

    path.write_text(
        json.dumps({
            "status":
                "passed",
            "python_tests_passed":
                1,
            "python_warnings":
                0,
            "typescript_parse":
                "passed",
            "electron_node_syntax":
                "passed",
            "material_ui_present":
                False,
        }),
        encoding="utf-8",
    )

    return path


def test_readiness_matrix_has_stable_order_and_unique_stage_ids(
    tmp_path,
):
    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="linux",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    ids = [
        stage[
            "id"
        ]
        for stage
        in report[
            "stages"
        ]
    ]

    assert (
        ids
        == EXPECTED_STAGE_IDS
    )

    assert (
        len(
            ids
        )
        == len(
            set(
                ids
            )
        )
    )


def test_every_stage_uses_declared_status_and_dependency(
    tmp_path,
):
    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="linux",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    known = {
        stage[
            "id"
        ]
        for stage
        in report[
            "stages"
        ]
    }

    for stage in (
        report[
            "stages"
        ]
    ):
        assert (
            stage[
                "status"
            ]
            in ALLOWED_STATUSES
        )

        for dependency in (
            stage[
                "depends_on"
            ]
        ):
            assert (
                dependency
                in known
            )


def test_non_windows_host_is_explicitly_blocked(
    tmp_path,
):
    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="linux",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    stage = next(
        item
        for item
        in report[
            "stages"
        ]
        if item[
            "id"
        ]
        == "windows_execution_host"
    )

    assert (
        stage[
            "status"
        ]
        == "BLOCKED"
    )

    assert (
        "current_host_is_not_windows"
        in stage[
            "blockers"
        ]
    )


def test_no_real_sessions_are_not_reported_as_executed(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        final_readiness_module,
        "_normal_raw_sessions",
        lambda path: [],
    )

    monkeypatch.setattr(
        final_readiness_module,
        "run_scientific_preflight",
        lambda path: {
            "status": "blocked_insufficient_valid_sessions",
            "valid_session_count": 0,
            "invalid_session_count": 0,
            "duplicate_content_groups": [],
            "temporal_overlap_pairs": [],
            "global_blockers": [
                "minimum_valid_sessions_not_met",
            ],
        },
    )

    monkeypatch.setattr(
        final_readiness_module,
        "validate_runtime_artifact_chain",
        lambda *args, **kwargs: {
            "ready": False,
            "status": "blocked_runtime_artifacts_missing",
            "missing": [
                "reference",
                "scaler",
                "model",
                "threshold",
            ],
            "identity": None,
        },
    )

    monkeypatch.setattr(
        final_readiness_module,
        "_read_final_evaluation",
        lambda path: None,
    )

    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="win32",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    stages = {
        stage[
            "id"
        ]:
            stage
        for stage
        in report[
            "stages"
        ]
    }

    assert (
        stages[
            "windows_normal_collection"
        ][
            "status"
        ]
        != "READY"
    )

    assert (
        stages[
            "scientific_preflight"
        ][
            "evidence"
        ][
            "valid_sessions"
        ]
        == 0
    )

    assert (
        stages[
            "ocsvm_threshold_runtime_chain"
        ][
            "status"
        ]
        == "BLOCKED"
    )

    assert (
        stages[
            "fixed_artifact_final_evaluation"
        ][
            "evidence"
        ][
            "evaluation_executed"
        ]
        is False
    )


def test_code_signing_is_optional_and_not_a_scientific_blocker(
    tmp_path,
):
    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="linux",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    stage = next(
        item
        for item
        in report[
            "stages"
        ]
        if item[
            "id"
        ]
        == "windows_code_signing"
    )

    assert (
        stage[
            "status"
        ]
        == "OPTIONAL"
    )

    assert (
        stage[
            "blocking"
        ]
        is False
    )


def test_markdown_contains_status_matrix_without_fake_metrics(
    tmp_path,
):
    report = (
        inspect_final_execution_readiness(
            resource_root(),
            platform_name="linux",
            validation_report_path=(
                _validation_file(
                    tmp_path
                )
            ),
        )
    )

    text = readiness_markdown(
        report
    )

    assert (
        "Final execution readiness"
        in text
    )

    assert (
        "Pré-flight científico"
        in text
    )

    assert (
        "Evidências com artefatos científicos congelados"
        in text
    )

    assert (
        "precision"
        not in text.lower()
    )

    assert (
        "recall"
        not in text.lower()
    )
