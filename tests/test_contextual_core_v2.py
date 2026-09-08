import pandas as pd
from ml.features.contextual_core_v2 import (
    CONTEXTUAL_CORE_V2_FEATURES,
    select_contextual_core_v2,
)


def test_contextual_core_v2_excludes_capture_channel():
    df=pd.DataFrame({
        "ssid_bssid_count":[1.0],
        "bssid_changed":[0.0],
        "channel_changed":[1.0],
        "security_changed":[0.0],
        "security_strength_delta":[0.0],
        "is_hidden":[0.0],
    })
    X=select_contextual_core_v2(df)
    assert list(X.columns) == CONTEXTUAL_CORE_V2_FEATURES
    assert "channel_changed" not in X.columns
