from desktop.validate_step16 import validate_step16


def test_windows_native_wifi_step16_contract():
    config = validate_step16()
    assert config["runtime_validation"]["actual_windows_scan_executed"] is False
    assert config["call_sequence"] == [
        "WlanOpenHandle",
        "WlanEnumInterfaces",
        "WlanScan",
        "WlanGetNetworkBssList",
        "WlanFreeMemory",
        "WlanCloseHandle",
    ]
