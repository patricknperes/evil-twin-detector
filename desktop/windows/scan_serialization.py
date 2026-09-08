from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone

from .ie_parser import extract_ds_parameter_channel, parse_information_elements


def hash_identifier(namespace: str, value: str | bytes) -> str:
    raw = (
        value.encode("utf-8", errors="replace")
        if isinstance(value, str)
        else bytes(value)
    )
    return hashlib.sha256(
        namespace.encode("utf-8") + b"|" + raw
    ).hexdigest()


def canonical_ssid_text(value: str | bytes) -> str:
    """Return the product/scientific canonical SSID text.

    Windows exposes SSID as arbitrary bytes. The product UI necessarily
    decodes those bytes to text. Hashing the same canonical text during raw
    collection and runtime inference prevents a training/runtime identity
    mismatch for non-UTF-8 SSIDs.
    """
    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return str(value)


def hash_ssid_identifier(value: str | bytes) -> str:
    return hash_identifier(
        "ssid",
        canonical_ssid_text(value),
    )


def serialize_bss_result(
    result,
    *,
    include_identifiers: bool = False,
) -> dict[str, object]:
    observation = result.observation
    security = observation.security
    parsed = parse_information_elements(observation.ie_blob)

    record = {
        # Hashes are always present so the same SSID/BSSID can be followed
        # across scans/sessions without persisting identifiers in clear text.
        "ssid_hash": (
            hash_ssid_identifier(observation.ssid)
            if observation.ssid
            else None
        ),
        "bssid_hash": hash_identifier("bssid", observation.bssid),
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
        "ds_parameter_channel": extract_ds_parameter_channel(
            observation.ie_blob
        ),
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

    if include_identifiers:
        record["ssid"] = observation.ssid.decode(
            "utf-8",
            errors="replace",
        )
        record["bssid"] = observation.bssid

    return record


def serialize_scan_batch(
    batch,
    *,
    scan_index: int,
    session_id: str,
    include_identifiers: bool = False,
    captured_at_utc: str | None = None,
) -> dict[str, object]:
    captured_at_utc = captured_at_utc or datetime.now(
        timezone.utc
    ).isoformat()

    interfaces = []

    for interface_scan in batch.interface_scans:
        entries = [
            serialize_bss_result(
                result,
                include_identifiers=include_identifiers,
            )
            for result in interface_scan.bss_entries
        ]

        interfaces.append({
            "interface": interface_scan.interface.public_dict(),
            "requested_fresh_scan": interface_scan.requested_fresh_scan,
            "scan_wait_seconds": interface_scan.scan_wait_seconds,
            "wait_strategy": interface_scan.wait_strategy,
            "bss_count": len(entries),
            "bss_entries": entries,
        })

    return {
        "schema_version": "windows_native_wifi_scan_v1",
        "session_id": session_id,
        "scan_index": int(scan_index),
        "captured_at_utc": captured_at_utc,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "negotiated_api_version": batch.negotiated_api_version,
        "interface_count": len(batch.interface_scans),
        "total_bss_entries": batch.total_bss_entries,
        "identifiers_in_clear_text": bool(include_identifiers),
        "interfaces": interfaces,
    }
