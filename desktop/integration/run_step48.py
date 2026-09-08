from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .backend_scenarios import (
    run_backend_integration_scenarios,
)


SCHEMA_VERSION = (
    "desktop_integration_step48_v1"
)


def _node_report(
    project_root: Path,
) -> dict[str, Any]:
    node = shutil.which(
        "node"
    )

    if node is None:
        return {
            "schema_version":
                "desktop_integration_electron_v1",
            "status":
                "not_executed",
            "reason":
                "node_not_available",
        }

    script = (
        project_root
        / "frontend"
        / "tests"
        / "desktop_integration_step48.cjs"
    )

    result = subprocess.run(
        [
            node,
            str(
                script
            ),
        ],
        cwd=str(
            project_root
            / "frontend"
        ),
        capture_output=True,
        text=True,
        timeout=45,
    )

    if result.returncode != 0:
        return {
            "schema_version":
                "desktop_integration_electron_v1",
            "status":
                "failed",
            "returncode":
                result.returncode,
            "stderr":
                result.stderr[-2000:],
        }

    lines = [
        line.strip()
        for line
        in result.stdout
        .splitlines()
        if line.strip()
    ]

    if not lines:
        return {
            "schema_version":
                "desktop_integration_electron_v1",
            "status":
                "failed",
            "reason":
                "empty_node_output",
        }

    try:
        return json.loads(
            lines[-1]
        )
    except json.JSONDecodeError:
        return {
            "schema_version":
                "desktop_integration_electron_v1",
            "status":
                "failed",
            "reason":
                "node_output_not_json",
            "stdout_tail":
                "\n".join(
                    lines[-10:]
                ),
        }


def run_step48_integration(
    project_root: str
    | Path,
) -> dict[str, Any]:
    root = Path(
        project_root
    ).resolve()

    workspace = (
        root
        / "reports"
        / "desktop"
        / ".step48_runtime"
    )

    if workspace.exists():
        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )

    workspace.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        backend = (
            run_backend_integration_scenarios(
                workspace
                / "backend"
            )
        )

        electron = (
            _node_report(
                root
            )
        )

        passed = (
            backend.get(
                "status"
            )
            == "passed"
            and electron.get(
                "status"
            )
            == "passed"
        )

        return {
            "schema_version":
                SCHEMA_VERSION,
            "status": (
                "passed"
                if passed
                else "failed"
            ),
            "backend":
                backend,
            "electron_scheduler":
                electron,
            "real_windows_native_wifi_executed":
                False,
            "real_scientific_bundle_loaded":
                False,
            "real_os_notification_displayed":
                False,
            "frontend_dependency_resolved_e2e_executed":
                False,
            "scientific_artifacts_mutated":
                False,
            "semantics": {
                "model_not_ready_is_not_normal":
                    True,
                "unsupported_scanner_is_explicit":
                    True,
                "location_denied_is_explicit":
                    True,
                "automatic_scan_recovery_tested_over_http":
                    True,
                "same_high_network_notification_deduplicated":
                    True,
            },
        }
    finally:
        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )


def save_report(
    report: dict[str, Any],
    path: str
    | Path,
) -> None:
    destination = Path(
        path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic desktop integration scenarios without "
            "real Windows Wi-Fi or scientific artifacts."
        )
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--output",
        default=(
            "reports/desktop/desktop_integration_step48.json"
        ),
    )

    args = parser.parse_args(
        argv
    )

    report = run_step48_integration(
        args.project_root
    )

    save_report(
        report,
        args.output,
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        0
        if report[
            "status"
        ]
        == "passed"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
