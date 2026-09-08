from desktop.windows.runtime_validation import validate_scans


def _scan(index, tsf):
    return {
        "scan_index": index,
        "interfaces": [
            {
                "interface": {"guid": "G"},
                "bss_entries": [
                    {
                        "ssid_hash": "S",
                        "bssid_hash": "B",
                        "rssi_dbm": -50,
                        "beacon_interval_ms": 102.4,
                        "tsf_us": tsf,
                        "host_timestamp_100ns": tsf * 10,
                        "center_frequency_khz": 2437000,
                        "ie_blob_size": 10,
                        "ie_parser_truncated": False,
                        "ds_parameter_channel": 6,
                        "security_type": "WPA2_OR_NEWER",
                        "security_strength": 3,
                        "security_source": "rsn_ie",
                    }
                ],
            }
        ],
    }


def test_ready_and_tsf_monotonic():
    report = validate_scans([
        _scan(0, 1000),
        _scan(1, 2000),
        _scan(2, 3000),
    ])

    assert report["runtime_ready_for_own_normal_collection"] is True
    assert report["desktop_candidate_v1_observable_rate"] == 1.0
    assert report["tsf_continuity"]["nondecreasing_rate"] == 1.0


def test_tsf_regression_warning():
    report = validate_scans([
        _scan(0, 3000),
        _scan(1, 2000),
        _scan(2, 1000),
    ])

    assert report["tsf_continuity"]["decreasing_transitions"] == 2
    assert any(
        "TSF apresenta muitos retrocessos" in warning
        for warning in report["warnings"]
    )
