import ctypes

import pytest

from desktop.windows.wlanapi_ctypes import (
    WLAN_BSS_ENTRY,
    WLAN_BSS_LIST,
    MalformedNativeWifiBuffer,
    parse_bss_list_buffer,
)


def _build_one_entry_buffer(*, ie_blob=b"\x00\x04Test\x03\x01\x06"):
    first_offset = WLAN_BSS_LIST.wlanBssEntries.offset
    entry_size = ctypes.sizeof(WLAN_BSS_ENTRY)
    ie_start = first_offset + entry_size
    total_size = ie_start + len(ie_blob)
    storage = ctypes.create_string_buffer(total_size)

    header = WLAN_BSS_LIST.from_buffer(storage)
    header.dwTotalSize = total_size
    header.dwNumberOfItems = 1

    entry = WLAN_BSS_ENTRY.from_buffer(storage, first_offset)
    entry.dot11Ssid.uSSIDLength = 4
    for index, value in enumerate(b"Test"):
        entry.dot11Ssid.ucSSID[index] = value
    for index, value in enumerate(bytes.fromhex("001122334455")):
        entry.dot11Bssid[index] = value

    entry.uPhyId = 7
    entry.dot11BssType = 1
    entry.dot11BssPhyType = 8
    entry.lRssi = -52
    entry.uLinkQuality = 82
    entry.bInRegDomain = 1
    entry.usBeaconPeriod = 100
    entry.ullTimestamp = 123456789
    entry.ullHostTimestamp = 987654321
    entry.usCapabilityInformation = 1 << 4
    entry.ulChCenterFrequency = 2437000
    entry.ulIeOffset = entry_size
    entry.ulIeSize = len(ie_blob)

    ctypes.memmove(ctypes.addressof(storage) + ie_start, ie_blob, len(ie_blob))
    return bytes(storage)


def test_parse_bss_list_buffer_to_project_contract():
    result = parse_bss_list_buffer(_build_one_entry_buffer())
    assert len(result) == 1
    item = result[0]
    assert item.observation.ssid == b"Test"
    assert item.observation.bssid == "00:11:22:33:44:55"
    assert item.observation.rssi_dbm == -52
    assert item.observation.beacon_interval_ms == 102.4
    assert item.observation.center_frequency_khz == 2437000
    assert item.observation.ie_blob == b"\x00\x04Test\x03\x01\x06"
    assert item.native.phy_id == 7
    assert item.native.phy_type == "ht"


def test_rejects_ie_that_points_outside_buffer():
    raw = bytearray(_build_one_entry_buffer())
    first_offset = WLAN_BSS_LIST.wlanBssEntries.offset
    storage = ctypes.create_string_buffer(bytes(raw), len(raw))
    entry = WLAN_BSS_ENTRY.from_buffer(storage, first_offset)
    entry.ulIeOffset = ctypes.sizeof(WLAN_BSS_ENTRY)
    entry.ulIeSize = 2324
    corrupted = bytes(storage)

    with pytest.raises(MalformedNativeWifiBuffer):
        parse_bss_list_buffer(corrupted)
