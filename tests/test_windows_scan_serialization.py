from desktop.windows.native_wifi_contract import NativeWifiBssObservation
from desktop.windows.scan_serialization import serialize_bss_result
from desktop.windows.wlanapi_ctypes import (
    NativeWifiBssNativeMetadata,
    NativeWifiBssResult,
)


def _result():
    return NativeWifiBssResult(
        observation=NativeWifiBssObservation(
            ssid=b"Rede",
            bssid="00:11:22:33:44:55",
            rssi_dbm=-50,
            link_quality=80,
            beacon_period_tu=100,
            tsf_us=123456,
            host_timestamp_100ns=999999,
            capability_info=0,
            center_frequency_khz=2437000,
            ie_blob=bytes([3, 1, 6]),
        ),
        native=NativeWifiBssNativeMetadata(
            phy_id=1,
            bss_type_code=1,
            bss_type="infrastructure",
            phy_type_code=7,
            phy_type="ht",
            in_reg_domain=True,
            supported_rates_mbps=(6.0,),
        ),
    )


def test_hashes_by_default():
    row = serialize_bss_result(_result())

    assert row["ssid_hash"]
    assert row["bssid_hash"]
    assert row["ds_parameter_channel"] == 6
    assert "ssid" not in row
    assert "bssid" not in row


def test_clear_identifiers_requires_flag():
    row = serialize_bss_result(
        _result(),
        include_identifiers=True,
    )

    assert row["ssid"] == "Rede"
    assert row["bssid"] == "00:11:22:33:44:55"
