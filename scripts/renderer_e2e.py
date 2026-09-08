from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "renderer_electron_e2e_step49_v1"
)

REQUIRED_FILES = (
    "frontend/playwright.config.ts",
    "frontend/tsconfig.e2e.json",
    "frontend/e2e/desktop.e2e.ts",
    "frontend/e2e/support/fake-backend.ts",
)

REQUIRED_DEV_DEPENDENCIES = (
    "@playwright/test",
    "playwright",
    "electron",
)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
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


def source_digest(
    root: Path,
) -> str:
    digest = hashlib.sha256()

    for relative in sorted(
        REQUIRED_FILES
    ):
        path = (
            root
            / relative
        )

        digest.update(
            relative.encode(
                "utf-8"
            )
        )

        if path.exists():
            digest.update(
                path.read_bytes()
            )

    for relative in (
        "frontend/electron/main.cjs",
        "frontend/electron/preload.cjs",
    ):
        path = (
            root
            / relative
        )

        digest.update(
            relative.encode(
                "utf-8"
            )
        )

        if path.exists():
            digest.update(
                path.read_bytes()
            )

    return digest.hexdigest()


def inspect_renderer_e2e(
    project_root:
        str
        | Path,
) -> dict[
    str,
    Any,
]:
    root = Path(
        project_root
    ).resolve()

    frontend = (
        root
        / "frontend"
    )

    package_path = (
        frontend
        / "package.json"
    )

    package = (
        json.loads(
            package_path.read_text(
                encoding="utf-8"
            )
        )
        if package_path.exists()
        else {}
    )

    dev_dependencies = (
        package.get(
            "devDependencies",
            {}
        )
    )

    missing_source = [
        relative
        for relative
        in REQUIRED_FILES
        if not (
            root
            / relative
        ).exists()
    ]

    missing_declared_dependencies = [
        name
        for name
        in REQUIRED_DEV_DEPENDENCIES
        if name
        not in dev_dependencies
    ]

    missing_installed_dependencies = [
        name
        for name
        in REQUIRED_DEV_DEPENDENCIES
        if not (
            frontend
            / "node_modules"
            / name
            / "package.json"
        ).exists()
    ]

    source_ready = (
        not missing_source
        and not missing_declared_dependencies
    )

    dependencies_ready = (
        source_ready
        and not missing_installed_dependencies
    )

    if not package_path.exists():
        status = (
            "BLOCKED_FRONTEND_PACKAGE_MISSING"
        )
    elif not source_ready:
        status = (
            "BLOCKED_E2E_SOURCE_CONTRACT"
        )
    elif not shutil.which(
        "node"
    ) or not shutil.which(
        "npm"
    ):
        status = (
            "BLOCKED_NODE_OR_NPM_MISSING"
        )
    elif dependencies_ready:
        status = (
            "READY_TO_EXECUTE"
        )
    else:
        status = (
            "NOT_EXECUTED_DEPENDENCIES_REQUIRED"
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "status":
            status,
        "source_ready":
            source_ready,
        "dependencies_ready":
            dependencies_ready,
        "package_json_sha256": (
            sha256_file(
                package_path
            )
            if package_path.exists()
            else None
        ),
        "e2e_source_sha256":
            source_digest(
                root
            ),
        "missing_source_files":
            missing_source,
        "missing_declared_dependencies":
            missing_declared_dependencies,
        "missing_installed_dependencies":
            missing_installed_dependencies,
        "scenario_ids": [
            "navigation_model_not_ready",
            "scanner_unsupported_manual_scan",
            "manual_scan_model_not_ready_history",
            "automatic_scan_ipc_dashboard_refresh",
            "backend_disconnect_recovery_no_reload",
            "diagnostics_privacy_download",
        ],
        "real_windows_native_wifi_used":
            False,
        "real_scientific_artifacts_used":
            False,
        "os_notification_allowed":
            False,
    }


def run_renderer_e2e(
    project_root:
        str
        | Path,
    *,
    execute:
        bool,
) -> dict[
    str,
    Any,
]:
    root = Path(
        project_root
    ).resolve()

    frontend = (
        root
        / "frontend"
    )

    report = (
        inspect_renderer_e2e(
            root
        )
    )

    report.update({
        "executed":
            False,
        "passed":
            False,
        "returncode":
            None,
    })

    if not execute:
        return report

    if not report[
        "dependencies_ready"
    ]:
        return report

    npm_executable = shutil.which(
        "npm"
    )

    if not npm_executable:
        report[
            "status"
        ] = (
            "BLOCKED_NODE_OR_NPM_MISSING"
        )

        return report

    result = subprocess.run(
        [
            npm_executable,
            "run",
            "e2e",
        ],
        cwd=str(
            frontend
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )

    report[
        "executed"
    ] = True

    report[
        "returncode"
    ] = (
        result.returncode
    )

    report[
        "passed"
    ] = (
        result.returncode
        == 0
    )

    report[
        "status"
    ] = (
        "PASSED"
        if result.returncode
        == 0
        else "BLOCKED_PLAYWRIGHT_E2E_FAILED"
    )

    return report


def main(
    argv:
        list[str]
        | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--output",
        default=(
            "reports/frontend/"
            "renderer_e2e_step49.json"
        ),
    )

    parser.add_argument(
        "--run",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    report = (
        run_renderer_e2e(
            args.project_root,
            execute=(
                args.run
            ),
        )
    )

    output = Path(
        args.output
    )

    if not output.is_absolute():
        output = (
            Path(
                args.project_root
            )
            / output
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
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
        == "PASSED"
        else 8
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
