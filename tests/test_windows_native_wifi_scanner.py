from desktop.windows.scanner import NativeWifiScanner
from desktop.windows.wlanapi_ctypes import (
    GUID,
    NativeWifiInterface,
    NativeWifiBssResult,
    NativeWifiBssNativeMetadata,
)
from desktop.windows.native_wifi_contract import NativeWifiBssObservation


class FakeApi:
    def __init__(self):
        self.scan_calls = 0
        self.free_calls = 0
        self.close_calls = 0

    def open_handle(self):
        return object(), 2

    def close_handle(self, handle):
        self.close_calls += 1

    def enum_interfaces(self, handle):
        return (
            NativeWifiInterface(
                guid="{00000000-0000-0000-0000-000000000001}",
                description="Wi-Fi",
                state_code=4,
                state="disconnected",
                _guid_struct=GUID(),
            ),
        )

    def request_scan(self, handle, interface):
        self.scan_calls += 1

    def get_bss_list(self, handle, interface):
        return (
            NativeWifiBssResult(
                observation=NativeWifiBssObservation(
                    ssid=b"Lab",
                    bssid="00:11:22:33:44:55",
                    rssi_dbm=-60,
                    link_quality=75,
                    beacon_period_tu=100,
                    tsf_us=1000,
                    host_timestamp_100ns=2000,
                    capability_info=0,
                    center_frequency_khz=2412000,
                    ie_blob=b"",
                ),
                native=NativeWifiBssNativeMetadata(
                    phy_id=1,
                    bss_type_code=1,
                    bss_type="infrastructure",
                    phy_type_code=8,
                    phy_type="ht",
                    in_reg_domain=True,
                    supported_rates_mbps=(),
                ),
            ),
        )


def test_scanner_requests_scan_waits_and_reads_bss_list():
    api = FakeApi()
    waits = []
    scanner = NativeWifiScanner(api=api, sleep_fn=waits.append)

    batch = scanner.scan_all(scan_wait_seconds=4.2)

    assert batch.negotiated_api_version == 2
    assert batch.total_bss_entries == 1
    assert api.scan_calls == 1
    assert api.close_calls == 1
    assert waits == [4.2]
    assert batch.interface_scans[0].bss_entries[0].observation.ssid == b"Lab"
