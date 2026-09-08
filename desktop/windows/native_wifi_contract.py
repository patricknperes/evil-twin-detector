from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .ie_parser import SecurityObservation, infer_security


BEACON_TU_MS: Final[float] = 1.024


@dataclass(frozen=True)
class NativeWifiBssObservation:
    """OS-independent contract for one Windows WLAN_BSS_ENTRY.

    A future ctypes adapter will populate this object from WlanGetNetworkBssList.
    Keeping the contract independent from ctypes lets feature logic and tests run
    on Linux/macOS CI as well as Windows.
    """

    ssid: bytes
    bssid: str
    rssi_dbm: int
    link_quality: int
    beacon_period_tu: int
    tsf_us: int
    host_timestamp_100ns: int
    capability_info: int
    center_frequency_khz: int
    ie_blob: bytes = b""

    @property
    def beacon_interval_ms(self) -> float:
        return float(self.beacon_period_tu) * BEACON_TU_MS

    @property
    def ssid_not_broadcast(self) -> bool:
        """Observable Windows condition, deliberately not named `is_hidden`.

        A zero-length SSID is observable, but the project does not equate it to
        the Mendeley `IsHidden` training feature without an explicit validation.
        """
        return len(self.ssid) == 0

    @property
    def security(self) -> SecurityObservation:
        return infer_security(
            capability_info=self.capability_info,
            ie_blob=self.ie_blob,
        )


WINDOWS_NATIVE_WIFI_FIELD_MAP = {
    "ssid": {
        "native_member": "WLAN_BSS_ENTRY.dot11Ssid",
        "availability": "direct",
    },
    "bssid": {
        "native_member": "WLAN_BSS_ENTRY.dot11Bssid",
        "availability": "direct",
    },
    "rssi_dbm": {
        "native_member": "WLAN_BSS_ENTRY.lRssi",
        "availability": "direct",
    },
    "link_quality": {
        "native_member": "WLAN_BSS_ENTRY.uLinkQuality",
        "availability": "direct",
    },
    "beacon_period_tu": {
        "native_member": "WLAN_BSS_ENTRY.usBeaconPeriod",
        "availability": "direct",
    },
    "tsf_us": {
        "native_member": "WLAN_BSS_ENTRY.ullTimestamp",
        "availability": "direct",
    },
    "host_timestamp_100ns": {
        "native_member": "WLAN_BSS_ENTRY.ullHostTimestamp",
        "availability": "direct",
    },
    "capability_info": {
        "native_member": "WLAN_BSS_ENTRY.usCapabilityInformation",
        "availability": "direct",
    },
    "center_frequency_khz": {
        "native_member": "WLAN_BSS_ENTRY.ulChCenterFrequency",
        "availability": "direct",
    },
    "ie_blob": {
        "native_member": "WLAN_BSS_ENTRY.ulIeOffset + ulIeSize",
        "availability": "direct_blob_requires_parser",
    },
}


NATIVE_WIFI_CALL_SEQUENCE = [
    "WlanOpenHandle",
    "WlanEnumInterfaces",
    "WlanScan",
    "WlanGetNetworkBssList",
    "WlanFreeMemory",
    "WlanCloseHandle",
]
