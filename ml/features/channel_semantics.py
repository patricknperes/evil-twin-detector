from __future__ import annotations

from collections import defaultdict
import hashlib

import numpy as np
import pandas as pd


def _clean_ssid(value):
    if pd.isna(value):
        return None

    text = str(
        value
    ).strip()

    return (
        text
        if text
        else None
    )


def _clean_bssid(value):
    if pd.isna(value):
        return None

    text = str(
        value
    ).strip().upper()

    return (
        text
        if text
        else None
    )


def _hash(
    namespace,
    value,
):
    if value is None:
        return None

    return hashlib.sha256(
        (
            f"{namespace}|{value}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def hash_ssid(value):
    return _hash(
        "ssid",
        _clean_ssid(
            value
        ),
    )


def hash_bssid(value):
    return _hash(
        "bssid",
        _clean_bssid(
            value
        ),
    )


def numeric_channel(
    value,
):
    parsed = pd.to_numeric(
        pd.Series([
            value
        ]),
        errors="coerce",
    ).iloc[0]

    if pd.isna(
        parsed
    ):
        return None

    return int(
        parsed
    )


def valid_advertised_channel(
    value,
):
    channel = numeric_channel(
        value
    )

    if (
        channel is None
        or channel <= 0
    ):
        return None

    return channel


def capture_advertised_mismatch(
    capture_channel,
    advertised_channel,
):
    """
    Compares capture/scanner channel with valid advertised AP channel.

    Important:
    - advertised_channel <= 0 is treated as unavailable, not a mismatch.
    - This feature is a diagnostic/quality signal, not an attack label.
    """
    capture = numeric_channel(
        capture_channel
    )

    advertised = (
        valid_advertised_channel(
            advertised_channel
        )
    )

    if (
        capture is None
        or advertised is None
    ):
        return np.nan

    return float(
        capture
        != advertised
    )


def build_advertised_channel_reference(
    reference_df,
):
    """
    Builds an SSID-context reference using only advertised_channel.

    Capture/scanner Channel is deliberately ignored.
    """
    channels_by_ssid = defaultdict(
        set
    )

    bssid_to_ssids = defaultdict(
        set
    )

    for _, row in (
        reference_df.iterrows()
    ):
        ssid_hash = hash_ssid(
            row.get(
                "ssid"
            )
        )

        bssid_hash = hash_bssid(
            row.get(
                "bssid"
            )
        )

        if ssid_hash is None:
            continue

        if bssid_hash is not None:
            bssid_to_ssids[
                bssid_hash
            ].add(
                ssid_hash
            )

        advertised = (
            valid_advertised_channel(
                row.get(
                    "advertised_channel"
                )
            )
        )

        if advertised is not None:
            channels_by_ssid[
                ssid_hash
            ].add(
                advertised
            )

    # Missing SSID may still resolve via a previously-known BSSID.
    for _, row in (
        reference_df.iterrows()
    ):
        if hash_ssid(
            row.get(
                "ssid"
            )
        ) is not None:
            continue

        bssid_hash = hash_bssid(
            row.get(
                "bssid"
            )
        )

        if bssid_hash is None:
            continue

        candidates = (
            bssid_to_ssids.get(
                bssid_hash,
                set(),
            )
        )

        if len(
            candidates
        ) != 1:
            continue

        ssid_hash = next(
            iter(
                candidates
            )
        )

        advertised = (
            valid_advertised_channel(
                row.get(
                    "advertised_channel"
                )
            )
        )

        if advertised is not None:
            channels_by_ssid[
                ssid_hash
            ].add(
                advertised
            )

    return {
        "version":
            "1.0.0",
        "channel_semantics":
            "advertised AP channel only",
        "channels_by_ssid": {
            key: sorted(
                value
            )
            for key, value
            in channels_by_ssid.items()
        },
        "bssid_to_ssids": {
            key: sorted(
                value
            )
            for key, value
            in bssid_to_ssids.items()
        },
    }


def resolve_ssid_context(
    row,
    reference,
):
    ssid_hash = hash_ssid(
        row.get(
            "ssid"
        )
    )

    if (
        ssid_hash is not None
        and ssid_hash
        in reference[
            "channels_by_ssid"
        ]
    ):
        return ssid_hash

    bssid_hash = hash_bssid(
        row.get(
            "bssid"
        )
    )

    if bssid_hash is None:
        return None

    candidates = (
        reference[
            "bssid_to_ssids"
        ].get(
            bssid_hash,
            [],
        )
    )

    if len(
        candidates
    ) == 1:
        return candidates[
            0
        ]

    return None


def advertised_channel_changed(
    row,
    reference,
):
    """
    Contextual feature based on the AP-advertised channel.

    1 means:
        current advertised channel was not observed in the frozen
        normal SSID context.

    Missing/invalid advertised channel => NaN.
    """
    ssid_hash = (
        resolve_ssid_context(
            row,
            reference,
        )
    )

    if ssid_hash is None:
        return np.nan

    known = set(
        reference[
            "channels_by_ssid"
        ].get(
            ssid_hash,
            [],
        )
    )

    if not known:
        return np.nan

    current = (
        valid_advertised_channel(
            row.get(
                "advertised_channel"
            )
        )
    )

    if current is None:
        return np.nan

    return float(
        current
        not in known
    )


def transform_channel_semantics(
    df,
    advertised_reference,
):
    rows = []

    for _, row in (
        df.iterrows()
    ):
        rows.append({
            "capture_channel":
                numeric_channel(
                    row.get(
                        "channel"
                    )
                ),
            "advertised_channel":
                valid_advertised_channel(
                    row.get(
                        "advertised_channel"
                    )
                ),
            "capture_advertised_mismatch":
                capture_advertised_mismatch(
                    row.get(
                        "channel"
                    ),
                    row.get(
                        "advertised_channel"
                    ),
                ),
            "advertised_channel_changed":
                advertised_channel_changed(
                    row,
                    advertised_reference,
                ),
        })

    return pd.DataFrame(
        rows
    )
