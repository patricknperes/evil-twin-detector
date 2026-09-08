import ctypes

from desktop.windows.wlanapi_ctypes import (
    DOT11_SSID,
    WLAN_RATE_SET,
    WLAN_INTERFACE_INFO,
    WLAN_INTERFACE_INFO_LIST,
    WLAN_BSS_ENTRY,
    WLAN_BSS_LIST,
)


def test_fixed_win32_layout_is_stable_off_windows():
    assert ctypes.sizeof(DOT11_SSID) == 36
    assert ctypes.sizeof(WLAN_RATE_SET) == 256
    assert ctypes.sizeof(WLAN_BSS_ENTRY) == 360
    assert ctypes.sizeof(WLAN_INTERFACE_INFO) == 532
    assert WLAN_INTERFACE_INFO_LIST.InterfaceInfo.offset == 8
    assert WLAN_BSS_LIST.wlanBssEntries.offset == 8
