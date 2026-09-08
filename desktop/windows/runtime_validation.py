from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import mean


def load_scan_jsonl(path: str | Path) -> list[dict[str, object]]:
    scans = []

    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue

            try:
                scans.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON inválido na linha {line_number}: {exc}"
                ) from exc

    return scans


def flatten_observations(
    scans: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []

    for scan in scans:
        scan_index = int(scan.get("scan_index", -1))
        captured_at = scan.get("captured_at_utc")

        for interface in scan.get("interfaces", []):
            interface_info = interface.get("interface", {})

            for observation in interface.get("bss_entries", []):
                row = dict(observation)
                row["_scan_index"] = scan_index
                row["_captured_at_utc"] = captured_at
                row["_interface_guid"] = interface_info.get("guid")
                rows.append(row)

    return rows


def _coverage(rows, field, predicate=lambda value: value is not None):
    if not rows:
        return 0.0

    valid = 0

    for row in rows:
        try:
            valid += int(bool(predicate(row.get(field))))
        except Exception:
            pass

    return valid / len(rows)


def _numeric_summary(rows, field):
    values = []

    for row in rows:
        value = row.get(field)

        if value is None or isinstance(value, bool):
            continue

        try:
            number = float(value)
        except (TypeError, ValueError):
            continue

        if math.isfinite(number):
            values.append(number)

    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
        }

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
    }


def _tsf_continuity(rows):
    by_bssid = defaultdict(list)

    for row in rows:
        bssid_hash = row.get("bssid_hash")
        tsf = row.get("tsf_us")

        if not bssid_hash or tsf is None:
            continue

        try:
            tsf = int(tsf)
        except (TypeError, ValueError):
            continue

        by_bssid[bssid_hash].append(
            (
                int(row.get("_scan_index", -1)),
                tsf,
            )
        )

    transitions = 0
    nondecreasing = 0
    decreasing = 0
    repeated = 0

    for values in by_bssid.values():
        values = sorted(values)

        if len(values) >= 2:
            repeated += 1

        for (_, previous), (__, current) in zip(values, values[1:]):
            transitions += 1

            if current >= previous:
                nondecreasing += 1
            else:
                decreasing += 1

    return {
        "unique_bssids_with_tsf": len(by_bssid),
        "repeated_bssids_with_tsf": repeated,
        "transitions": transitions,
        "nondecreasing_transitions": nondecreasing,
        "decreasing_transitions": decreasing,
        "nondecreasing_rate": (
            nondecreasing / transitions
            if transitions
            else None
        ),
    }


def validate_scans(
    scans: list[dict[str, object]],
) -> dict[str, object]:
    rows = flatten_observations(scans)

    scan_count = len(scans)
    observation_count = len(rows)

    unique_bssids = {
        row.get("bssid_hash")
        for row in rows
        if row.get("bssid_hash")
    }

    counts = Counter(
        row.get("bssid_hash")
        for row in rows
        if row.get("bssid_hash")
    )

    repeated_bssids = {
        key
        for key, count in counts.items()
        if count >= 2
    }

    contextual_identity_rows = 0
    candidate_rows = 0

    for row in rows:
        if row.get("ssid_hash") and row.get("bssid_hash"):
            contextual_identity_rows += 1

            if (
                row.get("security_type") is not None
                and row.get("security_strength") is not None
            ):
                candidate_rows += 1

    security_types = Counter(
        str(row["security_type"])
        for row in rows
        if row.get("security_type") is not None
    )

    security_sources = Counter(
        str(row["security_source"])
        for row in rows
        if row.get("security_source") is not None
    )

    coverage = {
        "ssid_hash": _coverage(rows, "ssid_hash"),
        "bssid_hash": _coverage(rows, "bssid_hash"),
        "security_type": _coverage(rows, "security_type"),
        "security_strength": _coverage(rows, "security_strength"),
        "rssi_dbm": _coverage(rows, "rssi_dbm"),
        "beacon_interval_positive": _coverage(
            rows,
            "beacon_interval_ms",
            lambda value: value is not None and float(value) > 0,
        ),
        "tsf_positive": _coverage(
            rows,
            "tsf_us",
            lambda value: value is not None and int(value) > 0,
        ),
        "host_timestamp_positive": _coverage(
            rows,
            "host_timestamp_100ns",
            lambda value: value is not None and int(value) > 0,
        ),
        "center_frequency_positive": _coverage(
            rows,
            "center_frequency_khz",
            lambda value: value is not None and int(value) > 0,
        ),
        "ie_blob_nonempty": _coverage(
            rows,
            "ie_blob_size",
            lambda value: value is not None and int(value) > 0,
        ),
        "ie_parser_not_truncated": _coverage(
            rows,
            "ie_parser_truncated",
            lambda value: value is False,
        ),
        "ds_parameter_channel": _coverage(
            rows,
            "ds_parameter_channel",
        ),
    }

    tsf_continuity = _tsf_continuity(rows)

    observable_rate = (
        candidate_rows / observation_count
        if observation_count
        else 0.0
    )

    warnings = []

    if scan_count < 3:
        warnings.append(
            "Poucos scans: faça pelo menos 3 para validar continuidade temporal."
        )

    if observation_count == 0:
        warnings.append("Nenhuma BSS foi observada.")

    if coverage["bssid_hash"] < 0.99:
        warnings.append(
            "BSSID não está disponível de forma consistente."
        )

    if observation_count and observable_rate < 0.70:
        warnings.append(
            "Menos de 70% das observações possuem identidade contextual "
            "SSID+BSSID e segurança utilizáveis."
        )

    if coverage["ie_blob_nonempty"] < 0.50:
        warnings.append(
            "IE blob está ausente em mais da metade das observações; "
            "valide o comportamento do driver."
        )

    if coverage["tsf_positive"] < 0.50:
        warnings.append(
            "TSF está ausente/zero em mais da metade das observações; "
            "mantenha TSF apenas como sinal opcional."
        )

    if (
        tsf_continuity["transitions"]
        and tsf_continuity["nondecreasing_rate"] is not None
        and tsf_continuity["nondecreasing_rate"] < 0.90
    ):
        warnings.append(
            "TSF apresenta muitos retrocessos entre scans do mesmo BSSID; "
            "não use monotonicidade sem investigar o driver/AP."
        )

    ready = bool(
        scan_count >= 3
        and observation_count > 0
        and coverage["bssid_hash"] >= 0.99
        and observable_rate >= 0.70
    )

    return {
        "schema_version": "windows_runtime_validation_v1",
        "scan_count": scan_count,
        "observation_count": observation_count,
        "unique_bssids": len(unique_bssids),
        "repeated_bssids": len(repeated_bssids),
        "candidate_context_identity_rows": contextual_identity_rows,
        "desktop_candidate_v1_observable_rows": candidate_rows,
        "desktop_candidate_v1_observable_rate": observable_rate,
        "coverage": coverage,
        "numeric_summary": {
            "rssi_dbm": _numeric_summary(rows, "rssi_dbm"),
            "beacon_interval_ms": _numeric_summary(
                rows,
                "beacon_interval_ms",
            ),
            "tsf_us": _numeric_summary(rows, "tsf_us"),
            "center_frequency_khz": _numeric_summary(
                rows,
                "center_frequency_khz",
            ),
        },
        "security_types": dict(security_types),
        "security_sources": dict(security_sources),
        "tsf_continuity": tsf_continuity,
        "runtime_ready_for_own_normal_collection": ready,
        "warnings": warnings,
        "interpretation": {
            "desktop_candidate_v1": (
                "SSID/BSSID identity plus per-BSS security are the hard "
                "requirements for the four-feature desktop candidate."
            ),
            "optional_fields": (
                "RSSI, Beacon Interval, TSF and channel diagnostics do not "
                "block the current desktop candidate."
            ),
            "tsf": (
                "Successful TSF observability does not promote TSF from "
                "ablation-only."
            ),
        },
    }


def validate_scan_file(path: str | Path) -> dict[str, object]:
    return validate_scans(load_scan_jsonl(path))
