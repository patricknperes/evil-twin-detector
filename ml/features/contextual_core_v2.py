from __future__ import annotations

import pandas as pd

CONTEXTUAL_CORE_V2_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
    "is_hidden",
]

DEPRECATED_V1_FEATURES = [
    "channel_changed",
]


def select_contextual_core_v2(df):
    """Return the clean Track-E v2 model matrix.

    `channel_changed` is intentionally excluded because the v1 implementation
    used capture/scanner `Channel`, not AP-advertised `DSChannel`.
    """
    missing = [
        column
        for column in CONTEXTUAL_CORE_V2_FEATURES
        if column not in df.columns
    ]
    if missing:
        raise ValueError(
            "Missing contextual_core_v2 features: " + ", ".join(missing)
        )
    X = df[CONTEXTUAL_CORE_V2_FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    ).copy()
    if X.isna().any().any():
        raise ValueError("contextual_core_v2 contains NaN.")
    return X
