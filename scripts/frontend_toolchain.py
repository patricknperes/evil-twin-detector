from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "frontend_toolchain_validation_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _version(command: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    result = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or result.stderr.strip() or None


def _sanitize_failure(text: str) -> str:
    lowered = text.lower()
    if "eai_again" in lowered:
        return "registry_dns_unavailable_eai_again"
    if "enotfound" in lowered:
        return "registry_dns_unavailable_enotfound"
    if "etimedout" in lowered or "timeout" in lowered:
        return "registry_timeout"
    if "econnrefused" in lowered:
        return "registry_connection_refused"
    if "eresolve" in lowered:
        return "dependency_resolution_error"
    return "npm_command_failed"


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {
            "ok": False,
            "returncode": None,
            "reason": "command_not_found",
        }

    resolved_command = [
        executable,
        *command[1:],
    ]

    try:
        result = subprocess.run(
            resolved_command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": None,
            "reason": "command_timeout",
        }
    except OSError:
        return {
            "ok": False,
            "returncode": None,
            "reason": "command_start_failed",
        }

    output = (result.stdout + "\n" + result.stderr).strip()
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "reason": None if result.returncode == 0 else _sanitize_failure(output),
    }


def direct_dependency_state(frontend: Path) -> dict[str, Any]:
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    names = sorted({
        *package.get("dependencies", {}).keys(),
        *package.get("devDependencies", {}).keys(),
    })
    missing = [
        name
        for name in names
        if not (frontend / "node_modules" / name / "package.json").exists()
    ]
    return {
        "direct_dependency_count": len(names),
        "missing_direct_dependencies": missing,
        "all_direct_dependencies_installed": not missing,
    }


def inspect_frontend_toolchain(
    project_root: str | Path,
    *,
    probe_registry: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    frontend = root / "frontend"
    package_json = frontend / "package.json"
    package_lock = frontend / "package-lock.json"
    dist_index = frontend / "dist" / "index.html"

    node_version = _version("node")
    npm_version = _version("npm")

    dependency_state = (
        direct_dependency_state(frontend)
        if package_json.exists()
        else {
            "direct_dependency_count": 0,
            "missing_direct_dependencies": [],
            "all_direct_dependencies_installed": False,
        }
    )

    registry = {
        "probed": False,
        "reachable": None,
        "reason": None,
    }

    if probe_registry and npm_version:
        registry["probed"] = True
        probe = _run(
            [
                "npm",
                "ping",
                "--fetch-retries=0",
                "--fetch-timeout=5000",
            ],
            cwd=frontend,
            timeout=12,
        )
        registry["reachable"] = probe["ok"]
        registry["reason"] = probe["reason"]

    if not package_json.exists():
        status = "BLOCKED_FRONTEND_PACKAGE_MISSING"
    elif not node_version or not npm_version:
        status = "BLOCKED_NODE_OR_NPM_MISSING"
    elif dependency_state["all_direct_dependencies_installed"]:
        status = "READY_DEPENDENCIES_INSTALLED"
    elif registry["probed"] and registry["reachable"] is False:
        status = "BLOCKED_REGISTRY_UNREACHABLE"
    else:
        status = "NOT_EXECUTED_DEPENDENCY_INSTALL_REQUIRED"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "node_version": node_version,
        "npm_version": npm_version,
        "package_json_sha256": sha256_file(package_json) if package_json.exists() else None,
        "package_lock_present": package_lock.exists(),
        "package_lock_sha256": sha256_file(package_lock) if package_lock.exists() else None,
        "node_modules_present": (frontend / "node_modules").exists(),
        "dist_index_present": dist_index.exists(),
        "dependencies": dependency_state,
        "registry": registry,
    }


def validate_frontend(
    project_root: str | Path,
    *,
    install: bool,
    probe_registry: bool,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    frontend = root / "frontend"
    before = inspect_frontend_toolchain(root, probe_registry=probe_registry)

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "NOT_EXECUTED",
        "preflight": before,
        "install": {"executed": False, "passed": False, "reason": None},
        "vitest": {"executed": False, "passed": False},
        "typecheck": {"executed": False, "passed": False},
        "vite_build": {"executed": False, "passed": False},
    }

    if before["status"] in {
        "BLOCKED_FRONTEND_PACKAGE_MISSING",
        "BLOCKED_NODE_OR_NPM_MISSING",
    }:
        result["status"] = before["status"]
        return result

    dependencies_ready = before["dependencies"]["all_direct_dependencies_installed"]

    if not dependencies_ready:
        if not install:
            result["status"] = "NOT_EXECUTED_DEPENDENCY_INSTALL_REQUIRED"
            return result

        if before["registry"]["probed"] and before["registry"]["reachable"] is False:
            result["install"] = {
                "executed": False,
                "passed": False,
                "reason": before["registry"]["reason"],
            }
            result["status"] = "BLOCKED_REGISTRY_UNREACHABLE"
            return result

        result["install"]["executed"] = True
        install_result = _run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=frontend,
            timeout=300,
        )
        result["install"]["passed"] = install_result["ok"]
        result["install"]["reason"] = install_result["reason"]
        if not install_result["ok"]:
            result["status"] = "BLOCKED_NPM_INSTALL_FAILED"
            return result

    commands = [
        ("vitest", ["npm", "test"]),
        ("typecheck", ["npm", "run", "typecheck"]),
        ("vite_build", ["npm", "run", "build:web"]),
    ]

    for name, command in commands:
        result[name]["executed"] = True
        command_result = _run(command, cwd=frontend, timeout=180)
        result[name]["passed"] = command_result["ok"]
        if not command_result["ok"]:
            result[name]["reason"] = command_result["reason"]
            result["status"] = f"BLOCKED_{name.upper()}_FAILED"
            return result

    dist_index = frontend / "dist" / "index.html"
    if not dist_index.exists():
        result["status"] = "BLOCKED_VITE_DIST_MISSING"
        return result

    package_json = frontend / "package.json"
    package_lock = frontend / "package-lock.json"
    result.update({
        "status": "PASSED",
        "package_json_sha256": sha256_file(package_json),
        "package_lock_present": package_lock.exists(),
        "package_lock_sha256": sha256_file(package_lock) if package_lock.exists() else None,
        "dist_index_sha256": sha256_file(dist_index),
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="reports/frontend/frontend_toolchain_step47.json")
    parser.add_argument("--probe-registry", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)

    report = validate_frontend(
        args.project_root,
        install=args.install,
        probe_registry=args.probe_registry,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(args.project_root) / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if report["status"] == "PASSED" else 8


if __name__ == "__main__":
    raise SystemExit(main())
