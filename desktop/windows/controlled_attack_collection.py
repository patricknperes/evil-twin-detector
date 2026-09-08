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

ALLOWED_SCENARIOS = {
    "controlled_evil_twin",
    "controlled_security_downgrade",
    "controlled_bssid_change",
    "controlled_channel_change",
    "controlled_tsf_reset_observation",
    "other_authorized_wifi_anomaly",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _safe_label(value: str) -> str:
    text = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    ).strip("-")

    if not text:
        raise ValueError("label vazio.")

    return text[:80]


def generate_attack_session_id(
    scenario: str,
) -> str:
    return (
        "win-attack-"
        + _safe_label(scenario).lower()
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


def _normalize_bssid(value: str) -> str:
    normalized = (
        value.strip()
        .lower()
        .replace(":", "")
        .replace("-", "")
        .replace(".", "")
    )

    if (
        len(normalized) != 12
        or any(
            character not in "0123456789abcdef"
            for character in normalized
        )
    ):
        raise ValueError(
            "target_bssid inválido."
        )

    return normalized


def collect_controlled_attack_session(
    *,
    scenario: str,
    environment: str,
    authorization_note: str,
    output_root: str | Path,
    scanner=None,
    scans: int = DEFAULT_SCANS,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    scan_wait_seconds: float = DEFAULT_SCAN_WAIT_SECONDS,
    interface_guid: str | None = None,
    target_bssid: str,
    include_identifiers: bool = False,
    session_id: str | None = None,
    sleep_fn=time.sleep,
) -> dict[str, object]:
    """
    Defensive measurement collector.

    This function does not create, configure, or control any rogue AP.
    It only records Native Wi-Fi observations while an already-authorized
    controlled experiment is active.
    """
    if scenario not in ALLOWED_SCENARIOS:
        raise ValueError(
            "scenario inválido. Use um cenário controlado conhecido."
        )

    if not authorization_note.strip():
        raise ValueError(
            "authorization_note é obrigatório."
        )

    if scans < 1:
        raise ValueError(
            "scans deve ser >= 1."
        )

    if interval_seconds < 0:
        raise ValueError(
            "interval_seconds deve ser >= 0."
        )

    target_bssid_normalized = _normalize_bssid(
        target_bssid
    )

    scanner = scanner or NativeWifiScanner()

    environment = _safe_label(
        environment
    )

    session_id = (
        session_id
        or generate_attack_session_id(
            scenario
        )
    )

    session_dir = (
        Path(
            output_root
        )
        / session_id
    )

    # Create-only raw data.
    session_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    scans_path = (
        session_dir
        / "scans.jsonl"
    )

    manifest_path = (
        session_dir
        / "manifest.json"
    )

    started = _utc_now()

    total_observations = 0
    target_observations = 0
    target_bssid_hash: str | None = None

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

            payload[
                "experiment_label"
            ] = 1

            payload[
                "attack_type"
            ] = scenario

            for (
                interface_scan,
                interface_payload,
            ) in zip(
                batch.interface_scans,
                payload["interfaces"],
            ):
                for (
                    result,
                    entry,
                ) in zip(
                    interface_scan.bss_entries,
                    interface_payload["bss_entries"],
                ):
                    observed_bssid = _normalize_bssid(
                        result.observation.bssid
                    )

                    is_attack_target = (
                        observed_bssid
                        == target_bssid_normalized
                    )

                    entry["observation_label"] = (
                        1
                        if is_attack_target
                        else 0
                    )

                    entry["is_attack_target"] = (
                        is_attack_target
                    )

                    if is_attack_target:
                        target_observations += 1

                        target_bssid_hash = str(
                            entry["bssid_hash"]
                        )

            total_observations += int(
                payload[
                    "total_bss_entries"
                ]
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

            if (
                scan_index < scans - 1
                and interval_seconds > 0
            ):
                sleep_fn(
                    interval_seconds
                )

    finished = _utc_now()

    if target_observations == 0:
        raise RuntimeError(
            "O BSSID alvo não foi observado durante "
            "a coleta controlada."
        )

    manifest = {
        "schema_version":
            "windows_controlled_attack_session_v2",
        "session_id":
            session_id,
        "label":
            1,
        "label_name":
            "controlled_attack",
        "attack_present":
            True,
        "attack_type":
            scenario,
        "attack_target": {
            "identifier_type":
                "bssid_hash",
            "bssid_hash":
                target_bssid_hash,
            "matched_observation_count":
                int(
                    target_observations
                ),
            "observation_label_field":
                "observation_label",
        },
        "authorization": {
            "authorized_controlled_experiment":
                True,
            "note":
                authorization_note.strip(),
            "collector_does_not_create_attack":
                True,
        },
        "environment":
            environment,
        "collection_purpose":
            "defensive_evaluation_only",
        "started_at_utc":
            started.isoformat(),
        "finished_at_utc":
            finished.isoformat(),
        "platform":
            platform.platform(),
        "python":
            sys.version.split()[0],
        "scanner": {
            "request_fresh_scan":
                True,
            "scan_wait_seconds":
                float(
                    scan_wait_seconds
                ),
            "interval_seconds_after_scan":
                float(
                    interval_seconds
                ),
            "requested_scan_count":
                int(
                    scans
                ),
            "interface_guid":
                interface_guid,
        },
        "privacy": {
            "identifiers_in_clear_text":
                bool(
                    include_identifiers
                ),
            "stable_sha256_identifiers_always_present":
                True,
            "coordinates_collected":
                False,
        },
        "files": {
            "scans_jsonl":
                scans_path.name,
            "scans_sha256":
                _sha256_file(
                    scans_path
                ),
        },
        "result": {
            "completed_scans":
                int(
                    scans
                ),
            "observations":
                int(
                    total_observations
                ),
        },
        "scientific_rules": [
            "Attack sessions are never used to fit scaler, normal reference, model, or threshold.",
            "Attack session_id is evaluation-only metadata.",
            "Collector only observes an already-authorized controlled experiment.",
            "Raw scans.jsonl is immutable after collection.",
            "No GPS or coordinates are collected.",
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
        "status":
            "ok",
        "session_dir":
            str(
                session_dir
            ),
        "manifest":
            manifest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Coleta observações defensivas durante um experimento Wi-Fi "
            "controlado e autorizado já em execução."
        )
    )

    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(
            ALLOWED_SCENARIOS
        ),
    )

    parser.add_argument(
        "--target-bssid",
        required=True,
        help=(
            "BSSID do AP usado como alvo "
            "no experimento controlado."
        ),
    )

    parser.add_argument(
        "--environment",
        required=True,
    )

    parser.add_argument(
        "--authorization-note",
        required=True,
        help=(
            "Nota curta confirmando que o experimento é autorizado/controlado."
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/raw/own/windows_attack"
        ),
    )

    parser.add_argument(
        "--scans",
        type=int,
        default=DEFAULT_SCANS,
    )

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

    parser.add_argument(
        "--interface-guid",
    )

    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    try:
        result = collect_controlled_attack_session(
            scenario=args.scenario,
            target_bssid=args.target_bssid,
            environment=args.environment,
            authorization_note=args.authorization_note,
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
                    "status":
                        "location_access_denied",
                    "error_code":
                        exc.code,
                    "function":
                        exc.function,
                    "message":
                        str(
                            exc
                        ),
                    "settings_uri":
                        LOCATION_SETTINGS_URI,
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
                    "status":
                        "unsupported_platform",
                    "message":
                        str(
                            exc
                        ),
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
                    "status":
                        "native_wifi_api_error",
                    "function":
                        exc.function,
                    "error_code":
                        exc.code,
                    "message":
                        str(
                            exc
                        ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        return 4


if __name__ == "__main__":
    raise SystemExit(
        main()
    )