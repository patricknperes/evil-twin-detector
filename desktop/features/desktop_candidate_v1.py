from __future__ import annotations

from dataclasses import dataclass
import hashlib
import statistics
from typing import Iterable

from desktop.windows.native_wifi_contract import NativeWifiBssObservation


DESKTOP_CANDIDATE_V1_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]

EXCLUDED_CORE_V2_FEATURES = {
    "is_hidden": (
        "Windows exposes zero-length/non-broadcast SSID observations, but the "
        "project has not established that this is semantically equivalent to "
        "the Mendeley IsHidden feature. Use ssid_not_broadcast as metadata "
        "until retraining/validation."
    )
}


@dataclass(frozen=True)
class DesktopSsidProfile:
    ssid_hash: str
    bssids: frozenset[str]
    security_types: frozenset[str]
    security_strengths: tuple[int, ...]


@dataclass(frozen=True)
class DesktopReference:
    profiles: dict[str, DesktopSsidProfile]
    bssid_to_ssids: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class DesktopCandidateResult:
    context_available: bool
    context_resolution: str
    features: dict[str, float]
    metadata: dict[str, object]


def hash_ssid(ssid: bytes) -> str | None:
    if not ssid:
        return None
    return hashlib.sha256(b"ssid|" + ssid).hexdigest()


def normalize_bssid(bssid: str) -> str:
    return bssid.strip().upper()


def build_desktop_reference(
    observations: Iterable[NativeWifiBssObservation],
) -> DesktopReference:
    raw_profiles: dict[str, dict[str, object]] = {}
    bssid_to_ssids: dict[str, set[str]] = {}

    for observation in observations:
        ssid_hash = hash_ssid(observation.ssid)
        if ssid_hash is None:
            # Unknown/non-broadcast SSID is not a stable logical identity.
            continue

        bssid = normalize_bssid(observation.bssid)
        security = observation.security

        profile = raw_profiles.setdefault(
            ssid_hash,
            {
                "bssids": set(),
                "security_types": set(),
                "security_strengths": [],
            },
        )
        profile["bssids"].add(bssid)
        profile["security_types"].add(security.security_type)
        profile["security_strengths"].append(security.strength)

        bssid_to_ssids.setdefault(bssid, set()).add(ssid_hash)

    profiles = {
        ssid_hash: DesktopSsidProfile(
            ssid_hash=ssid_hash,
            bssids=frozenset(values["bssids"]),
            security_types=frozenset(values["security_types"]),
            security_strengths=tuple(values["security_strengths"]),
        )
        for ssid_hash, values in raw_profiles.items()
    }

    return DesktopReference(
        profiles=profiles,
        bssid_to_ssids={
            bssid: tuple(sorted(ssids))
            for bssid, ssids in bssid_to_ssids.items()
        },
    )


def _resolve_profile(
    observation: NativeWifiBssObservation,
    reference: DesktopReference,
) -> tuple[DesktopSsidProfile | None, str]:
    ssid_hash = hash_ssid(observation.ssid)
    if ssid_hash is not None and ssid_hash in reference.profiles:
        return reference.profiles[ssid_hash], "ssid"

    bssid = normalize_bssid(observation.bssid)
    candidates = reference.bssid_to_ssids.get(bssid, ())
    if len(candidates) == 1:
        return reference.profiles[candidates[0]], "bssid_fallback"

    return None, "unresolved"


def compute_desktop_candidate_v1(
    observation: NativeWifiBssObservation,
    reference: DesktopReference,
) -> DesktopCandidateResult:
    profile, resolution = _resolve_profile(observation, reference)
    security = observation.security

    metadata = {
        "bssid": normalize_bssid(observation.bssid),
        "ssid_hash": hash_ssid(observation.ssid),
        "ssid_not_broadcast": observation.ssid_not_broadcast,
        "security_type": security.security_type,
        "security_source": security.source,
        "rssi_dbm": observation.rssi_dbm,
        "beacon_interval_ms": observation.beacon_interval_ms,
        "tsf_us": observation.tsf_us,
        "center_frequency_khz": observation.center_frequency_khz,
    }

    if profile is None:
        return DesktopCandidateResult(
            context_available=False,
            context_resolution=resolution,
            features={},
            metadata=metadata,
        )

    bssid = normalize_bssid(observation.bssid)
    median_strength = statistics.median(profile.security_strengths)

    features = {
        "ssid_bssid_count": float(len(profile.bssids)),
        "bssid_changed": float(bssid not in profile.bssids),
        "security_changed": float(
            security.security_type not in profile.security_types
        ),
        "security_strength_delta": float(
            security.strength - median_strength
        ),
    }

    return DesktopCandidateResult(
        context_available=True,
        context_resolution=resolution,
        features=features,
        metadata=metadata,
    )
