import math
from ml.features.local_admin_ablation import (
    bssid_local_admin_flag,
    bssid_multicast_flag,
)

def test_local_admin_bit():
    assert bssid_local_admin_flag(
        "00:11:22:33:44:55"
    ) == 0.0
    assert bssid_local_admin_flag(
        "02:11:22:33:44:55"
    ) == 1.0
    assert bssid_multicast_flag(
        "02:11:22:33:44:55"
    ) == 0.0

def test_group_bit_is_different():
    assert bssid_multicast_flag(
        "01:11:22:33:44:55"
    ) == 1.0
    assert bssid_local_admin_flag(
        "01:11:22:33:44:55"
    ) == 0.0

def test_invalid_bssid_is_nan():
    assert math.isnan(
        bssid_local_admin_flag("invalid")
    )
