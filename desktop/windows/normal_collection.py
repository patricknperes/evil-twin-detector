from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .runtime_validation import validate_scan_file
from .scan_serialization import serialize_scan_batch
from .scanner import DEFAULT_SCAN_WAIT_SECONDS, NativeWifiScanner
from .wlanapi_ctypes import (
    LOCATION_SETTINGS_URI,
    LocationAccessDeniedError,
    NativeWifiApiError,
    UnsupportedPlatformError,
)


DEFAULT_SCANS = 30
DEFAULT_INTERVAL_SECONDS = 6.0


def _utc_now():
    return datetime.now(timezone.utc)


def _safe_label(value: str) -> str:
    text = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    ).strip("-")

    if not text:
        raise ValueError("environment label vazio.")

    return text[:80]


def generate_session_id(environment: str) -> str:
    return (
        "win-normal-"
        + _safe_label(environment).lower()
        + "-"
        + _utc_now().strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + secrets.token_hex(3)
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def collect_normal_session(
    *,
    environment: str,
    output_root: str | Path,
    scanner=None,
    scans: int = DEFAULT_SCANS,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    scan_wait_seconds: float = DEFAULT_SCAN_WAIT_SECONDS,
    interface_guid: str | None = None,
    include_identifiers: bool = False,
    session_id: str | None = None,
    sleep_fn=time.sleep,
) -> dict[str, object]:
    if scans < 1:
        raise ValueError("scans deve ser >= 1.")

    if interval_seconds < 0:
        raise ValueError("interval_seconds deve ser >= 0.")

    scanner = scanner or NativeWifiScanner()
    environment = _safe_label(environment)
    session_id = session_id or generate_session_id(environment)

    session_dir = Path(output_root) / session_id

    # Create-only by design. Old own-raw sessions are never overwritten.
    session_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    scans_path = session_dir / "scans.jsonl"
    manifest_path = session_dir / "manifest.json"
    validation_path = session_dir / "runtime_validation.json"

    started = _utc_now()
    total_observations = 0

    with scans_path.open(
        "x",
        encoding="utf-8",
        newline="\n",
    ) as output:
        for scan_index in range(scans):
            batch = scanner.scan_all(
                request_fresh_scan=True,
                scan_wait_seconds=scan_wait_seconds,
                interface_guid=interface_guid,
            )

            payload = serialize_scan_batch(
                batch,
                scan_index=scan_index,
                session_id=session_id,
                include_identifiers=include_identifiers,
            )

            total_observations += int(
                payload["total_bss_entries"]
            )

            output.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

            output.flush()

            if scan_index < scans - 1 and interval_seconds:
                sleep_fn(interval_seconds)

    finished = _utc_now()
    validation = validate_scan_file(scans_path)

    validation_path.write_text(
        json.dumps(
            validation,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "windows_own_normal_session_v1",
        "session_id": session_id,
        "label": 0,
        "label_name": "normal",
        "attack_present": False,
        "collection_purpose": (
            "own_normal_windows_runtime_and_training_candidate"
        ),
        "environment": environment,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "scanner": {
            "request_fresh_scan": True,
            "scan_wait_seconds": float(scan_wait_seconds),
            "interval_seconds_after_scan": float(interval_seconds),
            "requested_scan_count": int(scans),
            "interface_guid": interface_guid,
        },
        "privacy": {
            "identifiers_in_clear_text": bool(include_identifiers),
            "stable_sha256_identifiers_always_present": True,
            "coordinates_collected": False,
        },
        "files": {
            "scans_jsonl": scans_path.name,
            "runtime_validation_json": validation_path.name,
            "scans_sha256": _sha256_file(scans_path),
        },
        "result": {
            "completed_scans": int(validation["scan_count"]),
            "observations": int(total_observations),
            "runtime_ready_for_own_normal_collection": validation[
                "runtime_ready_for_own_normal_collection"
            ],
        },
        "scientific_rules": [
            "Normal-only session; no intentionally active attack.",
            "Group/split by session_id, never random rows from this session.",
            "scans.jsonl is immutable after collection.",
            "Coordinates are not collected/model features.",
            "TSF/channel availability does not automatically promote them.",
        ],
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "session_dir": str(session_dir),
        "manifest": manifest,
        "runtime_validation": validation,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Coleta uma sessão normal própria com Windows Native Wi-Fi."
        )
    )
    parser.add_argument("--environment", required=True)
    parser.add_argument(
        "--output-root",
        default="data/raw/own/windows",
    )
    parser.add_argument("--scans", type=int, default=DEFAULT_SCANS)
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=DEFAULT_SCAN_WAIT_SECONDS,
    )
    parser.add_argument("--interface-guid")
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )

    args = parser.parse_args(argv)

    try:
        result = collect_normal_session(
            environment=args.environment,
            output_root=args.output_root,
            scans=args.scans,
            interval_seconds=args.interval_seconds,
            scan_wait_seconds=args.wait_seconds,
            interface_guid=args.interface_guid,
            include_identifiers=args.include_identifiers,
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    except LocationAccessDeniedError as exc:
        print(
            json.dumps(
                {
                    "status": "location_access_denied",
                    "error_code": exc.code,
                    "function": exc.function,
                    "message": str(exc),
                    "settings_uri": LOCATION_SETTINGS_URI,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 3

    except UnsupportedPlatformError as exc:
        print(
            json.dumps(
                {
                    "status": "unsupported_platform",
                    "message": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    except NativeWifiApiError as exc:
        print(
            json.dumps(
                {
                    "status": "native_wifi_api_error",
                    "function": exc.function,
                    "error_code": exc.code,
                    "message": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
