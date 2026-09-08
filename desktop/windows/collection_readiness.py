from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from desktop.implementation_freeze import verify_implementation_snapshot

from .scanner import DEFAULT_SCAN_WAIT_SECONDS, NativeWifiScanner
from .wlanapi_ctypes import (
    LOCATION_SETTINGS_URI,
    LocationAccessDeniedError,
    NativeWifiApiError,
    UnsupportedPlatformError,
)


SCHEMA_VERSION = "windows_collection_readiness_step52_v1"
MIN_FREE_BYTES = 512 * 1024 * 1024
REQUIRED_MODULES = (
    "numpy",
    "pandas",
    "sklearn",
    "joblib",
)


def _session_dirs(root: Path, required: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        folder
        for folder in root.iterdir()
        if folder.is_dir()
        and all((folder / name).exists() for name in required)
    )


def inspect_collection_readiness(
    project_root: str | Path,
    *,
    platform_name: str | None = None,
    probe_native_wifi: bool = False,
    scanner=None,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    platform_name = platform_name or sys.platform

    snapshot = verify_implementation_snapshot(
        root,
        root / "reports/implementation/implementation_snapshot_step52.json",
    )

    missing_modules = [
        name
        for name in REQUIRED_MODULES
        if importlib.util.find_spec(name) is None
    ]

    raw_root = root / "data/raw/own/windows"
    interim_root = root / "data/interim/own/windows"
    prepared_root = root / "data/processed/desktop_candidate_v1"

    raw_sessions = _session_dirs(raw_root, ("manifest.json", "scans.jsonl"))
    interim_sessions = _session_dirs(
        interim_root,
        ("import_manifest.json", "observations.csv.gz"),
    )

    freeze_exists = (prepared_root / "scientific_freeze.json").exists()
    reference_exists = (prepared_root / "desktop_normal_reference.json").exists()

    disk = shutil.disk_usage(root)
    disk_ready = disk.free >= MIN_FREE_BYTES

    blockers: list[str] = []
    warnings: list[str] = []

    if platform_name != "win32":
        blockers.append("windows_host_required")

    if not snapshot.get("ready"):
        blockers.append("implementation_snapshot_mismatch")

    if missing_modules:
        blockers.append("required_python_modules_missing")

    if not disk_ready:
        blockers.append("insufficient_free_disk_space")

    if freeze_exists or reference_exists:
        blockers.append("desktop_candidate_v1_already_frozen")

    if interim_sessions and len(interim_sessions) != len(raw_sessions):
        warnings.append("raw_and_interim_session_counts_differ")

    scanner_probe: dict[str, Any] = {
        "requested": probe_native_wifi,
        "executed": False,
        "ready": False,
        "status": "not_requested",
    }

    if platform_name == "win32" and probe_native_wifi:
        try:
            scanner = scanner or NativeWifiScanner()
            batch = scanner.scan_all(
                request_fresh_scan=True,
                scan_wait_seconds=DEFAULT_SCAN_WAIT_SECONDS,
                interface_guid=None,
            )
            interface_count = len(batch.interface_scans)
            total_bss_entries = batch.total_bss_entries
            scanner_probe = {
                "requested": True,
                "executed": True,
                "ready": interface_count > 0,
                "status": "ready" if interface_count > 0 else "no_wifi_interfaces",
                "interface_count": interface_count,
                "total_bss_entries": total_bss_entries,
                "identifiers_recorded": False,
            }
            if interface_count == 0:
                blockers.append("native_wifi_interface_missing")
            if total_bss_entries == 0:
                warnings.append("native_wifi_probe_observed_zero_networks")
        except LocationAccessDeniedError as exc:
            scanner_probe = {
                "requested": True,
                "executed": True,
                "ready": False,
                "status": "location_access_denied",
                "error_code": exc.code,
                "settings_uri": LOCATION_SETTINGS_URI,
            }
            blockers.append("windows_location_access_denied")
        except UnsupportedPlatformError:
            scanner_probe = {
                "requested": True,
                "executed": True,
                "ready": False,
                "status": "unsupported_platform",
            }
            blockers.append("native_wifi_unsupported_platform")
        except NativeWifiApiError as exc:
            scanner_probe = {
                "requested": True,
                "executed": True,
                "ready": False,
                "status": "native_wifi_api_error",
                "function": exc.function,
                "error_code": exc.code,
            }
            blockers.append("native_wifi_api_error")

    elif platform_name == "win32" and not probe_native_wifi:
        warnings.append("native_wifi_probe_not_executed")

    ready = not blockers and (
        scanner_probe.get("ready") is True
        if probe_native_wifi
        else True
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "READY_FOR_NORMAL_COLLECTION" if ready else "BLOCKED_COLLECTION_READINESS",
        "ready": ready,
        "platform": platform_name,
        "implementation_snapshot": snapshot,
        "python": {
            "version": sys.version.split()[0],
            "required_modules": list(REQUIRED_MODULES),
            "missing_modules": missing_modules,
        },
        "disk": {
            "free_bytes": disk.free,
            "minimum_free_bytes": MIN_FREE_BYTES,
            "ready": disk_ready,
        },
        "existing_data": {
            "raw_normal_sessions": len(raw_sessions),
            "interim_normal_sessions": len(interim_sessions),
            "scientific_freeze_exists": freeze_exists,
            "normal_reference_exists": reference_exists,
        },
        "scanner_probe": scanner_probe,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "collection_protocol": {
            "minimum_sessions": 5,
            "recommended_sessions": 9,
            "default_scans_per_session": 30,
            "default_interval_seconds": 6.0,
            "default_scan_wait_seconds": DEFAULT_SCAN_WAIT_SECONDS,
            "normal_cohort_environment_count": 1,
            "identifiers_in_clear_text": False,
            "attack_active_during_normal_collection": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--probe-native-wifi", action="store_true")
    parser.add_argument(
        "--output",
        default="reports/desktop/windows_collection_readiness_step52.json",
    )
    args = parser.parse_args(argv)

    result = inspect_collection_readiness(
        args.project_root,
        probe_native_wifi=args.probe_native_wifi,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = Path(args.project_root) / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ready"] else 8


if __name__ == "__main__":
    raise SystemExit(main())
