from __future__ import annotations

import ctypes
import os
import sys
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Final, Iterable

from .native_wifi_contract import NativeWifiBssObservation


# ---------------------------------------------------------------------------
# Fixed-width Win32 types.
#
# Do not use ctypes.c_wchar in public Win32 structures here: wchar_t is
# 2 bytes on Windows but 4 bytes on many Unix hosts. Using UINT16 keeps the
# structure layout testable on non-Windows CI while matching WCHAR on Win32.
# ---------------------------------------------------------------------------
BYTE = ctypes.c_uint8
BOOLEAN = ctypes.c_uint8
USHORT = ctypes.c_uint16
WORD = ctypes.c_uint16
ULONG = ctypes.c_uint32
DWORD = ctypes.c_uint32
LONG = ctypes.c_int32
ULONGLONG = ctypes.c_uint64
BOOL = ctypes.c_int32
WCHAR16 = ctypes.c_uint16
HANDLE = ctypes.c_void_p
PVOID = ctypes.c_void_p

WLAN_MAX_NAME_LENGTH: Final[int] = 256
DOT11_SSID_MAX_LENGTH: Final[int] = 32
DOT11_RATE_SET_MAX_LENGTH: Final[int] = 126
DOT11_BSS_TYPE_ANY: Final[int] = 3
WLAN_API_VERSION_2_0: Final[int] = 2
ERROR_SUCCESS: Final[int] = 0
ERROR_ACCESS_DENIED: Final[int] = 5
ERROR_NOT_SUPPORTED: Final[int] = 50
ERROR_INVALID_PARAMETER: Final[int] = 87
ERROR_INVALID_HANDLE: Final[int] = 6
ERROR_SERVICE_NOT_ACTIVE: Final[int] = 1062
MAX_IE_BLOB_BYTES: Final[int] = 2324
MAX_BSS_ITEMS: Final[int] = 16384
MAX_BSS_LIST_BYTES: Final[int] = 16 * 1024 * 1024
MAX_WLAN_INTERFACES: Final[int] = 128
LOCATION_SETTINGS_URI: Final[str] = "ms-settings:privacy-location"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", BYTE * 8),
    ]


class DOT11_SSID(ctypes.Structure):
    _fields_ = [
        ("uSSIDLength", ULONG),
        ("ucSSID", BYTE * DOT11_SSID_MAX_LENGTH),
    ]


DOT11_MAC_ADDRESS = BYTE * 6


class WLAN_RATE_SET(ctypes.Structure):
    _fields_ = [
        ("uRateSetLength", ULONG),
        ("usRateSet", USHORT * DOT11_RATE_SET_MAX_LENGTH),
    ]


class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [
        ("InterfaceGuid", GUID),
        ("strInterfaceDescription", WCHAR16 * WLAN_MAX_NAME_LENGTH),
        ("isState", ctypes.c_int32),
    ]


class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [
        ("dwNumberOfItems", DWORD),
        ("dwIndex", DWORD),
        ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
    ]


class WLAN_BSS_ENTRY(ctypes.Structure):
    _fields_ = [
        ("dot11Ssid", DOT11_SSID),
        ("uPhyId", ULONG),
        ("dot11Bssid", DOT11_MAC_ADDRESS),
        ("dot11BssType", ctypes.c_int32),
        ("dot11BssPhyType", ctypes.c_int32),
        ("lRssi", LONG),
        ("uLinkQuality", ULONG),
        ("bInRegDomain", BOOLEAN),
        ("usBeaconPeriod", USHORT),
        ("ullTimestamp", ULONGLONG),
        ("ullHostTimestamp", ULONGLONG),
        ("usCapabilityInformation", USHORT),
        ("ulChCenterFrequency", ULONG),
        ("wlanRateSet", WLAN_RATE_SET),
        ("ulIeOffset", ULONG),
        ("ulIeSize", ULONG),
    ]


class WLAN_BSS_LIST(ctypes.Structure):
    _fields_ = [
        ("dwTotalSize", DWORD),
        ("dwNumberOfItems", DWORD),
        ("wlanBssEntries", WLAN_BSS_ENTRY * 1),
    ]


INTERFACE_STATE_NAMES: Final[dict[int, str]] = {
    0: "not_ready",
    1: "connected",
    2: "ad_hoc_network_formed",
    3: "disconnecting",
    4: "disconnected",
    5: "associating",
    6: "discovering",
    7: "authenticating",
}

BSS_TYPE_NAMES: Final[dict[int, str]] = {
    1: "infrastructure",
    2: "independent",
    3: "any",
}

PHY_TYPE_NAMES: Final[dict[int, str]] = {
    0: "unknown",
    1: "any",
    2: "fhss",
    3: "dsss",
    4: "irbaseband",
    5: "ofdm",
    6: "hrdsss",
    7: "erp",
    8: "ht",
    9: "vht",
    10: "dmg",
    11: "he",
    12: "eht",
}


class NativeWifiError(RuntimeError):
    """Base error for the Windows Native Wi-Fi adapter."""


class UnsupportedPlatformError(NativeWifiError):
    pass


class NativeWifiApiError(NativeWifiError):
    def __init__(self, function: str, code: int, message: str | None = None):
        self.function = function
        self.code = int(code)
        self.system_message = message or _format_error_message(self.code)
        super().__init__(
            f"{function} failed with Win32 error {self.code}: {self.system_message}"
        )


class LocationAccessDeniedError(NativeWifiApiError):
    settings_uri: str = LOCATION_SETTINGS_URI


class MalformedNativeWifiBuffer(NativeWifiError):
    pass


@dataclass(frozen=True)
class NativeWifiInterface:
    guid: str
    description: str
    state_code: int
    state: str
    _guid_struct: GUID

    def public_dict(self) -> dict[str, object]:
        return {
            "guid": self.guid,
            "description": self.description,
            "state_code": self.state_code,
            "state": self.state,
        }


@dataclass(frozen=True)
class NativeWifiBssNativeMetadata:
    phy_id: int
    bss_type_code: int
    bss_type: str
    phy_type_code: int
    phy_type: str
    in_reg_domain: bool
    supported_rates_mbps: tuple[float, ...]


@dataclass(frozen=True)
class NativeWifiBssResult:
    observation: NativeWifiBssObservation
    native: NativeWifiBssNativeMetadata


@dataclass(frozen=True)
class NativeWifiInterfaceScan:
    interface: NativeWifiInterface
    bss_entries: tuple[NativeWifiBssResult, ...]
    requested_fresh_scan: bool
    scan_wait_seconds: float
    wait_strategy: str


@dataclass(frozen=True)
class NativeWifiScanBatch:
    negotiated_api_version: int
    interface_scans: tuple[NativeWifiInterfaceScan, ...]

    @property
    def total_bss_entries(self) -> int:
        return sum(len(item.bss_entries) for item in self.interface_scans)


def _format_error_message(code: int) -> str:
    known = {
        ERROR_ACCESS_DENIED: "Access denied",
        ERROR_NOT_SUPPORTED: "Operation not supported",
        ERROR_INVALID_PARAMETER: "Invalid parameter",
        ERROR_INVALID_HANDLE: "Invalid handle",
        ERROR_SERVICE_NOT_ACTIVE: "WLAN AutoConfig service is not active",
    }
    if code in known:
        return known[code]
    if sys.platform == "win32":
        try:
            return ctypes.FormatError(code).strip()
        except Exception:
            pass
    return f"Win32 error {code}"


def _raise_for_status(function: str, status: int) -> None:
    if int(status) == ERROR_SUCCESS:
        return
    if int(status) == ERROR_ACCESS_DENIED:
        raise LocationAccessDeniedError(function, int(status))
    raise NativeWifiApiError(function, int(status))


def guid_to_string(guid: GUID) -> str:
    data4 = bytes(guid.Data4)
    return (
        f"{{{int(guid.Data1):08X}-{int(guid.Data2):04X}-{int(guid.Data3):04X}-"
        f"{data4[0]:02X}{data4[1]:02X}-"
        f"{''.join(f'{value:02X}' for value in data4[2:])}}}"
    )


def _decode_utf16_array(values: Iterable[int]) -> str:
    raw = b"".join(int(value).to_bytes(2, "little") for value in values)
    text = raw.decode("utf-16-le", errors="replace")
    return text.split("\x00", 1)[0]


def _ssid_bytes(value: DOT11_SSID) -> bytes:
    length = min(max(int(value.uSSIDLength), 0), DOT11_SSID_MAX_LENGTH)
    return bytes(value.ucSSID[:length])


def _bssid_string(value: DOT11_MAC_ADDRESS) -> str:
    return ":".join(f"{int(byte):02X}" for byte in value)


def _supported_rates_mbps(rate_set: WLAN_RATE_SET) -> tuple[float, ...]:
    # uRateSetLength is the number of bytes in the USHORT array according to
    # Microsoft documentation. Clamp to the physical array size.
    byte_length = min(max(int(rate_set.uRateSetLength), 0), 2 * DOT11_RATE_SET_MAX_LENGTH)
    item_count = min(byte_length // 2, DOT11_RATE_SET_MAX_LENGTH)
    return tuple(
        (int(rate_set.usRateSet[index]) & 0x7FFF) * 0.5
        for index in range(item_count)
    )


def _validate_bss_list_header(total_size: int, item_count: int) -> None:
    first_offset = WLAN_BSS_LIST.wlanBssEntries.offset
    fixed_bytes = first_offset + item_count * ctypes.sizeof(WLAN_BSS_ENTRY)

    if total_size < first_offset:
        raise MalformedNativeWifiBuffer(
            f"WLAN_BSS_LIST total size {total_size} is smaller than header {first_offset}."
        )
    if total_size > MAX_BSS_LIST_BYTES:
        raise MalformedNativeWifiBuffer(
            f"WLAN_BSS_LIST total size {total_size} exceeds safety limit."
        )
    if item_count > MAX_BSS_ITEMS:
        raise MalformedNativeWifiBuffer(
            f"WLAN_BSS_LIST item count {item_count} exceeds safety limit."
        )
    if fixed_bytes > total_size:
        raise MalformedNativeWifiBuffer(
            "WLAN_BSS_LIST fixed entry array exceeds dwTotalSize."
        )


def _extract_ie_blob(
    *,
    buffer_base: int,
    buffer_total_size: int,
    entry_address: int,
    entry: WLAN_BSS_ENTRY,
) -> bytes:
    size = int(entry.ulIeSize)
    offset = int(entry.ulIeOffset)

    if size == 0:
        return b""
    if size > MAX_IE_BLOB_BYTES:
        raise MalformedNativeWifiBuffer(
            f"IE blob size {size} exceeds documented maximum {MAX_IE_BLOB_BYTES}."
        )
    if offset < ctypes.sizeof(WLAN_BSS_ENTRY):
        raise MalformedNativeWifiBuffer(
            "IE blob offset points inside WLAN_BSS_ENTRY."
        )

    start = entry_address + offset
    end = start + size
    buffer_end = buffer_base + buffer_total_size

    if start < buffer_base or end > buffer_end or end < start:
        raise MalformedNativeWifiBuffer(
            "IE blob lies outside WLAN_BSS_LIST buffer bounds."
        )

    return ctypes.string_at(start, size)


def _entry_to_result(
    *,
    entry: WLAN_BSS_ENTRY,
    ie_blob: bytes,
) -> NativeWifiBssResult:
    observation = NativeWifiBssObservation(
        ssid=_ssid_bytes(entry.dot11Ssid),
        bssid=_bssid_string(entry.dot11Bssid),
        rssi_dbm=int(entry.lRssi),
        link_quality=int(entry.uLinkQuality),
        beacon_period_tu=int(entry.usBeaconPeriod),
        tsf_us=int(entry.ullTimestamp),
        host_timestamp_100ns=int(entry.ullHostTimestamp),
        capability_info=int(entry.usCapabilityInformation),
        center_frequency_khz=int(entry.ulChCenterFrequency),
        ie_blob=ie_blob,
    )

    native = NativeWifiBssNativeMetadata(
        phy_id=int(entry.uPhyId),
        bss_type_code=int(entry.dot11BssType),
        bss_type=BSS_TYPE_NAMES.get(int(entry.dot11BssType), "unknown"),
        phy_type_code=int(entry.dot11BssPhyType),
        phy_type=PHY_TYPE_NAMES.get(int(entry.dot11BssPhyType), "unknown"),
        in_reg_domain=bool(entry.bInRegDomain),
        supported_rates_mbps=_supported_rates_mbps(entry.wlanRateSet),
    )

    return NativeWifiBssResult(observation=observation, native=native)


def parse_bss_list_buffer(buffer: bytes | bytearray | memoryview) -> tuple[NativeWifiBssResult, ...]:
    """Parse a copied WLAN_BSS_LIST buffer.

    This pure helper is used by Linux/macOS CI tests. Production Windows code
    uses the same structure offsets on the native WlanGetNetworkBssList buffer.
    """
    raw = bytes(buffer)
    if len(raw) < WLAN_BSS_LIST.wlanBssEntries.offset:
        raise MalformedNativeWifiBuffer("Buffer is too short for WLAN_BSS_LIST header.")

    storage = ctypes.create_string_buffer(raw, len(raw))
    base = ctypes.addressof(storage)
    header = WLAN_BSS_LIST.from_address(base)
    total_size = int(header.dwTotalSize)
    item_count = int(header.dwNumberOfItems)

    if total_size > len(raw):
        raise MalformedNativeWifiBuffer(
            "dwTotalSize exceeds the copied buffer length."
        )
    _validate_bss_list_header(total_size, item_count)

    first_offset = WLAN_BSS_LIST.wlanBssEntries.offset
    stride = ctypes.sizeof(WLAN_BSS_ENTRY)
    results: list[NativeWifiBssResult] = []

    for index in range(item_count):
        entry_address = base + first_offset + index * stride
        entry = WLAN_BSS_ENTRY.from_address(entry_address)
        ie_blob = _extract_ie_blob(
            buffer_base=base,
            buffer_total_size=total_size,
            entry_address=entry_address,
            entry=entry,
        )
        results.append(_entry_to_result(entry=entry, ie_blob=ie_blob))

    return tuple(results)


class NativeWifiApi:
    """Thin ctypes binding to wlanapi.dll.

    Instantiation is deliberately Windows-only. Structure/layout helpers remain
    importable on non-Windows systems for unit testing.
    """

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise UnsupportedPlatformError(
                "Windows Native Wi-Fi API requires win32. "
                f"Current platform: {sys.platform}."
            )

        self._dll = ctypes.WinDLL("wlanapi.dll", use_last_error=True)
        self._bind()

    def _bind(self) -> None:
        dll = self._dll

        dll.WlanOpenHandle.argtypes = [
            DWORD,
            PVOID,
            ctypes.POINTER(DWORD),
            ctypes.POINTER(HANDLE),
        ]
        dll.WlanOpenHandle.restype = DWORD

        dll.WlanCloseHandle.argtypes = [HANDLE, PVOID]
        dll.WlanCloseHandle.restype = DWORD

        dll.WlanEnumInterfaces.argtypes = [
            HANDLE,
            PVOID,
            ctypes.POINTER(PVOID),
        ]
        dll.WlanEnumInterfaces.restype = DWORD

        dll.WlanScan.argtypes = [
            HANDLE,
            ctypes.POINTER(GUID),
            PVOID,
            PVOID,
            PVOID,
        ]
        dll.WlanScan.restype = DWORD

        dll.WlanGetNetworkBssList.argtypes = [
            HANDLE,
            ctypes.POINTER(GUID),
            PVOID,
            ctypes.c_int32,
            BOOL,
            PVOID,
            ctypes.POINTER(PVOID),
        ]
        dll.WlanGetNetworkBssList.restype = DWORD

        dll.WlanFreeMemory.argtypes = [PVOID]
        dll.WlanFreeMemory.restype = None

    def open_handle(self) -> tuple[HANDLE, int]:
        negotiated = DWORD()
        handle = HANDLE()
        status = self._dll.WlanOpenHandle(
            WLAN_API_VERSION_2_0,
            None,
            ctypes.byref(negotiated),
            ctypes.byref(handle),
        )
        _raise_for_status("WlanOpenHandle", status)
        return handle, int(negotiated.value)

    def close_handle(self, handle: HANDLE) -> None:
        status = self._dll.WlanCloseHandle(handle, None)
        _raise_for_status("WlanCloseHandle", status)

    def free_memory(self, pointer: PVOID) -> None:
        if pointer and pointer.value:
            self._dll.WlanFreeMemory(pointer)

    def enum_interfaces(self, handle: HANDLE) -> tuple[NativeWifiInterface, ...]:
        pointer = PVOID()
        status = self._dll.WlanEnumInterfaces(handle, None, ctypes.byref(pointer))
        _raise_for_status("WlanEnumInterfaces", status)

        try:
            if not pointer.value:
                return ()

            base = int(pointer.value)
            header = WLAN_INTERFACE_INFO_LIST.from_address(base)
            count = int(header.dwNumberOfItems)
            if count > MAX_WLAN_INTERFACES:
                raise MalformedNativeWifiBuffer(
                    f"Interface count {count} exceeds safety limit."
                )

            first_offset = WLAN_INTERFACE_INFO_LIST.InterfaceInfo.offset
            stride = ctypes.sizeof(WLAN_INTERFACE_INFO)
            result: list[NativeWifiInterface] = []

            for index in range(count):
                address = base + first_offset + index * stride
                native = WLAN_INTERFACE_INFO.from_address(address)
                guid_copy = GUID()
                ctypes.memmove(
                    ctypes.byref(guid_copy),
                    ctypes.byref(native.InterfaceGuid),
                    ctypes.sizeof(GUID),
                )
                state_code = int(native.isState)
                result.append(
                    NativeWifiInterface(
                        guid=guid_to_string(native.InterfaceGuid),
                        description=_decode_utf16_array(native.strInterfaceDescription),
                        state_code=state_code,
                        state=INTERFACE_STATE_NAMES.get(state_code, "unknown"),
                        _guid_struct=guid_copy,
                    )
                )

            return tuple(result)
        finally:
            self.free_memory(pointer)

    def request_scan(self, handle: HANDLE, interface: NativeWifiInterface) -> None:
        status = self._dll.WlanScan(
            handle,
            ctypes.byref(interface._guid_struct),
            None,
            None,
            None,
        )
        _raise_for_status("WlanScan", status)

    def get_bss_list(
        self,
        handle: HANDLE,
        interface: NativeWifiInterface,
    ) -> tuple[NativeWifiBssResult, ...]:
        pointer = PVOID()
        status = self._dll.WlanGetNetworkBssList(
            handle,
            ctypes.byref(interface._guid_struct),
            None,
            DOT11_BSS_TYPE_ANY,
            False,
            None,
            ctypes.byref(pointer),
        )
        _raise_for_status("WlanGetNetworkBssList", status)

        try:
            if not pointer.value:
                return ()

            base = int(pointer.value)
            header = WLAN_BSS_LIST.from_address(base)
            total_size = int(header.dwTotalSize)
            item_count = int(header.dwNumberOfItems)
            _validate_bss_list_header(total_size, item_count)

            first_offset = WLAN_BSS_LIST.wlanBssEntries.offset
            stride = ctypes.sizeof(WLAN_BSS_ENTRY)
            results: list[NativeWifiBssResult] = []

            for index in range(item_count):
                entry_address = base + first_offset + index * stride
                entry = WLAN_BSS_ENTRY.from_address(entry_address)
                ie_blob = _extract_ie_blob(
                    buffer_base=base,
                    buffer_total_size=total_size,
                    entry_address=entry_address,
                    entry=entry,
                )
                results.append(_entry_to_result(entry=entry, ie_blob=ie_blob))

            return tuple(results)
        finally:
            self.free_memory(pointer)


class NativeWifiSession(AbstractContextManager["NativeWifiSession"]):
    def __init__(self, api: NativeWifiApi | None = None) -> None:
        self.api = api or NativeWifiApi()
        self.handle: HANDLE | None = None
        self.negotiated_api_version: int | None = None

    def __enter__(self) -> "NativeWifiSession":
        handle, version = self.api.open_handle()
        self.handle = handle
        self.negotiated_api_version = version
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.handle is not None:
            try:
                self.api.close_handle(self.handle)
            finally:
                self.handle = None
        return False

    def require_handle(self) -> HANDLE:
        if self.handle is None:
            raise NativeWifiError("NativeWifiSession is not open.")
        return self.handle
