from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .ie_parser import extract_ds_parameter_channel, parse_information_elements
from .scanner import DEFAULT_SCAN_WAIT_SECONDS, NativeWifiScanner
from .scan_serialization import (
    hash_identifier,
    hash_ssid_identifier,
)
from .wlanapi_ctypes import (
    LOCATION_SETTINGS_URI,
    LocationAccessDeniedError,
    NativeWifiApiError,
    UnsupportedPlatformError,
)


def _safe_ssid_text(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _serialize_batch(batch, *, redact_identifiers: bool) -> dict[str, object]:
    interfaces: list[dict[str, object]] = []

    for interface_scan in batch.interface_scans:
        bss_entries: list[dict[str, object]] = []

        for result in interface_scan.bss_entries:
            observation = result.observation
            security = observation.security
            parsed = parse_information_elements(observation.ie_blob)

            if redact_identifiers:
                ssid_value = None
                bssid_value = None
                ssid_hash = hash_ssid_identifier(observation.ssid)
                bssid_hash = hash_identifier("bssid", observation.bssid)
            else:
                ssid_value = _safe_ssid_text(observation.ssid)
                bssid_value = observation.bssid
                ssid_hash = None
                bssid_hash = None

            bss_entries.append(
                {
                    "ssid": ssid_value,
                    "bssid": bssid_value,
                    "ssid_hash": ssid_hash,
                    "bssid_hash": bssid_hash,
                    "ssid_not_broadcast": observation.ssid_not_broadcast,
                    "rssi_dbm": observation.rssi_dbm,
                    "link_quality": observation.link_quality,
                    "beacon_period_tu": observation.beacon_period_tu,
                    "beacon_interval_ms": observation.beacon_interval_ms,
                    "tsf_us": observation.tsf_us,
                    "host_timestamp_100ns": observation.host_timestamp_100ns,
                    "capability_info": observation.capability_info,
                    "center_frequency_khz": observation.center_frequency_khz,
                    "ie_blob_size": len(observation.ie_blob),
                    "ie_parser_truncated": parsed.truncated,
                    "ds_parameter_channel": extract_ds_parameter_channel(observation.ie_blob),
                    "security_type": security.security_type,
                    "security_strength": security.strength,
                    "security_source": security.source,
                    "rsn_akm_types": list(security.rsn_akm_types),
                    "native": {
                        "phy_id": result.native.phy_id,
                        "bss_type_code": result.native.bss_type_code,
                        "bss_type": result.native.bss_type,
                        "phy_type_code": result.native.phy_type_code,
                        "phy_type": result.native.phy_type,
                        "in_reg_domain": result.native.in_reg_domain,
                        "supported_rates_mbps": list(result.native.supported_rates_mbps),
                    },
                }
            )

        interfaces.append(
            {
                "interface": interface_scan.interface.public_dict(),
                "requested_fresh_scan": interface_scan.requested_fresh_scan,
                "scan_wait_seconds": interface_scan.scan_wait_seconds,
                "wait_strategy": interface_scan.wait_strategy,
                "bss_count": len(bss_entries),
                "bss_entries": bss_entries,
            }
        )

    return {
        "status": "ok",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "negotiated_api_version": batch.negotiated_api_version,
        "interface_count": len(batch.interface_scans),
        "total_bss_entries": batch.total_bss_entries,
        "redacted_identifiers": redact_identifiers,
        "interfaces": interfaces,
    }


def _write_json(path: str | None, payload: dict[str, object]) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_diagnostic(
    *,
    request_fresh_scan: bool = True,
    scan_wait_seconds: float = DEFAULT_SCAN_WAIT_SECONDS,
    interface_guid: str | None = None,
    redact_identifiers: bool = False,
) -> tuple[int, dict[str, object]]:
    try:
        scanner = NativeWifiScanner()
        batch = scanner.scan_all(
            request_fresh_scan=request_fresh_scan,
            scan_wait_seconds=scan_wait_seconds,
            interface_guid=interface_guid,
        )
        return 0, _serialize_batch(batch, redact_identifiers=redact_identifiers)

    except LocationAccessDeniedError as exc:
        return 3, {
            "status": "location_access_denied",
            "error_code": exc.code,
            "function": exc.function,
            "message": str(exc),
            "settings_uri": LOCATION_SETTINGS_URI,
            "action": (
                "Grant precise location/Wi-Fi access to the desktop application "
                "in Windows Settings and retry."
            ),
        }
    except UnsupportedPlatformError as exc:
        return 2, {
            "status": "unsupported_platform",
            "message": str(exc),
            "platform": platform.platform(),
        }
    except NativeWifiApiError as exc:
        return 4, {
            "status": "native_wifi_api_error",
            "error_code": exc.code,
            "function": exc.function,
            "message": str(exc),
        }
    except Exception as exc:
        return 5, {
            "status": "unexpected_error",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico do scanner Windows Native Wi-Fi (wlanapi.dll)."
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Arquivo JSON para persistir o diagnóstico.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=DEFAULT_SCAN_WAIT_SECONDS,
        help="Espera após WlanScan. Padrão: 4.2 s.",
    )
    parser.add_argument(
        "--no-scan",
        action="store_true",
        help="Não chama WlanScan; lê apenas a lista BSS já disponível/cacheada.",
    )
    parser.add_argument(
        "--interface-guid",
        help="Limita o diagnóstico a um GUID retornado por WlanEnumInterfaces.",
    )
    parser.add_argument(
        "--redact-identifiers",
        action="store_true",
        help="Não grava SSID/BSSID em claro; grava hashes SHA-256 para diagnóstico.",
    )

    args = parser.parse_args(argv)

    code, payload = run_diagnostic(
        request_fresh_scan=not args.no_scan,
        scan_wait_seconds=args.wait_seconds,
        interface_guid=args.interface_guid,
        redact_identifiers=args.redact_identifiers,
    )

    _write_json(args.json_path, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
