from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.runtime_paths import (
    resource_root,
)
from desktop.integration.backend_scenarios import (
    run_backend_integration_scenarios,
)
from desktop.integration.run_step48 import (
    run_step48_integration,
)


def test_backend_scenarios_pass_without_real_scientific_artifacts(
    tmp_path,
):
    report = (
        run_backend_integration_scenarios(
            tmp_path
        )
    )

    assert (
        report[
            "status"
        ]
        == "passed"
    )

    assert (
        report[
            "scenario_count"
        ]
        == 4
    )

    assert (
        report[
            "real_windows_native_wifi_used"
        ]
        is False
    )

    assert (
        report[
            "real_scientific_artifacts_used"
        ]
        is False
    )

    scenarios = {
        item[
            "id"
        ]:
            item
        for item
        in report[
            "scenarios"
        ]
    }

    assert (
        scenarios[
            "backend_online_model_not_ready"
        ][
            "status"
        ]
        == "PASSED"
    )

    manual = scenarios[
        "manual_scan_model_not_ready"
    ]

    assert (
        manual[
            "checks"
        ][
            "analysis_not_available"
        ]
        is True
    )

    assert (
        manual[
            "checks"
        ][
            "no_false_negative_decision"
        ]
        is True
    )


def test_node_electron_integration_uses_real_local_http_fetch():
    root = resource_root()

    result = subprocess.run(
        [
            "node",
            str(
                root
                / "frontend"
                / "tests"
                / "desktop_integration_step48.cjs"
            ),
        ],
        cwd=str(
            root
            / "frontend"
        ),
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert (
        result.returncode
        == 0
    ), (
        result.stdout
        + result.stderr
    )

    payload = json.loads(
        result.stdout
        .strip()
        .splitlines()[
            -1
        ]
    )

    assert (
        payload[
            "status"
        ]
        == "passed"
    )

    assert (
        payload[
            "scenarios"
        ][
            "backend_offline"
        ]
        is True
    )

    assert (
        payload[
            "scenarios"
        ][
            "backend_recovery"
        ]
        is True
    )

    assert (
        payload[
            "scenarios"
        ][
            "automatic_scan_real_http_fetch"
        ]
        is True
    )

    assert (
        payload[
            "os_notification_displayed"
        ]
        is False
    )


def test_combined_step48_report_passes(
    tmp_path,
):
    report = run_step48_integration(
        resource_root()
    )

    assert (
        report[
            "schema_version"
        ]
        == "desktop_integration_step48_v1"
    )

    assert (
        report[
            "status"
        ]
        == "passed"
    )

    assert (
        report[
            "real_windows_native_wifi_executed"
        ]
        is False
    )

    assert (
        report[
            "frontend_dependency_resolved_e2e_executed"
        ]
        is False
    )

    assert (
        report[
            "scientific_artifacts_mutated"
        ]
        is False
    )
