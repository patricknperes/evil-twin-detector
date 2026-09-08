import pandas as pd

from ml.features.tsf_ablation import (
    build_tsf_reference,
    transform_tsf,
)


def test_tsf_reference_monotonic_violation():
    reference_df = pd.DataFrame({
        "session_id": [
            "s1",
            "s1",
        ],
        "bssid": [
            "00:11:22:33:44:55",
            "00:11:22:33:44:55",
        ],
        "beacon_timestamp_us": [
            1000,
            2000,
        ],
    })

    reference = build_tsf_reference(
        reference_df
    )

    current = pd.DataFrame({
        "session_id": [
            "s1",
            "s1",
        ],
        "bssid": [
            "00:11:22:33:44:55",
            "00:11:22:33:44:55",
        ],
        "beacon_timestamp_us": [
            3000,
            500,
        ],
    })

    result = transform_tsf(
        current,
        reference,
    )

    assert (
        result[
            "tsf_reference_monotonic_violation"
        ].tolist()
        == [
            0.0,
            1.0,
        ]
    )


def test_tsf_reference_is_session_scoped():
    reference_df = pd.DataFrame({
        "session_id": [
            "s1",
            "s2",
        ],
        "bssid": [
            "00:11:22:33:44:55",
            "00:11:22:33:44:55",
        ],
        "beacon_timestamp_us": [
            100000,
            1000,
        ],
    })

    reference = build_tsf_reference(
        reference_df
    )

    current = pd.DataFrame({
        "session_id": [
            "s2"
        ],
        "bssid": [
            "00:11:22:33:44:55"
        ],
        "beacon_timestamp_us": [
            2000
        ],
    })

    result = transform_tsf(
        current,
        reference,
    )

    # Compared only with s2 max=1000, so no violation.
    assert (
        result[
            "tsf_reference_monotonic_violation"
        ].iloc[0]
        == 0.0
    )
