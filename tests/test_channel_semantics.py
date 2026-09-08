import math

import pandas as pd

from ml.features.channel_semantics import (
    capture_advertised_mismatch,
    build_advertised_channel_reference,
    advertised_channel_changed,
)


def test_mismatch_requires_valid_advertised_channel():
    assert (
        capture_advertised_mismatch(
            6,
            6,
        )
        == 0.0
    )

    assert (
        capture_advertised_mismatch(
            1,
            6,
        )
        == 1.0
    )

    assert math.isnan(
        capture_advertised_mismatch(
            1,
            0,
        )
    )


def test_advertised_reference_ignores_capture_channel():
    reference = pd.DataFrame({
        "ssid": [
            "Rede",
            "Rede",
        ],
        "bssid": [
            "00:11:22:33:44:55",
            "00:11:22:33:44:55",
        ],
        "channel": [
            1,
            11,
        ],
        "advertised_channel": [
            6,
            6,
        ],
    })

    result = (
        build_advertised_channel_reference(
            reference
        )
    )

    values = list(
        result[
            "channels_by_ssid"
        ].values()
    )

    assert values == [
        [6]
    ]


def test_advertised_channel_changed():
    reference = pd.DataFrame({
        "ssid": [
            "Rede"
        ],
        "bssid": [
            "00:11:22:33:44:55"
        ],
        "advertised_channel": [
            6
        ],
    })

    state = (
        build_advertised_channel_reference(
            reference
        )
    )

    same = pd.Series({
        "ssid":
            "Rede",
        "bssid":
            "00:11:22:33:44:55",
        "advertised_channel":
            6,
    })

    changed = pd.Series({
        "ssid":
            "Rede",
        "bssid":
            "00:11:22:33:44:99",
        "advertised_channel":
            11,
    })

    assert (
        advertised_channel_changed(
            same,
            state,
        )
        == 0.0
    )

    assert (
        advertised_channel_changed(
            changed,
            state,
        )
        == 1.0
    )
