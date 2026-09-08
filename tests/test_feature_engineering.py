import numpy as np
import pandas as pd

from ml.features.beacon_profiles import (
    build_mendeley_beacon_1s,
    build_v2i_beacon_1s,
    build_rssi_temporal_5s,
)


def test_mendeley_beacon_window():
    df = pd.DataFrame({
        "source_dataset":
            ["mendeley_rogue_ap"] * 4,
        "session_id":
            ["session_001"] * 4,
        "elapsed_ms":
            [100, 200, 1100, 1200],
        "bssid":
            ["aa:bb:cc:dd:ee:ff"] * 4,
        "rssi_dbm":
            [-60, -62, -65, -63],
        "channel":
            [6, 6, 6, 6],
        "advertised_channel":
            [6, 6, 6, 6],
        "configured_beacon_interval_ms":
            [102.4] * 4,
        "security_type":
            ["WPA2"] * 4,
        "label":
            [0] * 4,
        "attack_type":
            [pd.NA] * 4,
        "is_synthetic":
            [False] * 4,
    })

    result = (
        build_mendeley_beacon_1s(
            df
        )
    ).sort_values(
        "window_start_ms"
    )

    assert len(result) == 2

    first = result.iloc[0]

    assert first[
        "rssi_mean_dbm"
    ] == -61

    assert first[
        "beacon_count"
    ] == 2

    assert first[
        "observed_inter_beacon_ms"
    ] == 100

    assert first[
        "frequency_mhz"
    ] == 2437


def test_v2i_temporal_profile():
    df = pd.DataFrame({
        "source_dataset":
            ["zenodo_v2i"] * 5,
        "session_id":
            ["trace_302"] * 5,
        "elapsed_ms":
            [0, 1000, 2000, 3000, 4000],
        "ap_id":
            ["ap-n"] * 5,
        "rssi_dbm":
            [-50, -52, -51, -55, -54],
        "frequency_mhz":
            [2437] * 5,
        "channel":
            [6] * 5,
        "beacon_count":
            [8, 8, 9, 7, 8],
        "measured_inter_beacon_ms":
            [120, 121, 119, 130, 125],
        "wifi_standard":
            ["802.11n"] * 5,
        "label":
            [0] * 5,
        "attack_type":
            [pd.NA] * 5,
        "is_synthetic":
            [False] * 5,
    })

    beacon = (
        build_v2i_beacon_1s(
            df
        )
    )

    assert len(beacon) == 5

    temporal = (
        build_rssi_temporal_5s(
            beacon
        )
    )

    assert len(temporal) == 1

    row = temporal.iloc[0]

    assert row[
        "window_count"
    ] == 5

    assert np.isclose(
        row["rssi_mean_dbm"],
        -52.4,
    )

    assert row[
        "rssi_delta_db"
    ] == -4
