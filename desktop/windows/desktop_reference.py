from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import numpy as np
import pandas as pd


DESKTOP_FEATURES = [
    "ssid_bssid_count",
    "bssid_changed",
    "security_changed",
    "security_strength_delta",
]


def _median(
    values,
):
    values = [
        float(
            value
        )
        for value in values
        if pd.notna(
            value
        )
    ]

    if not values:
        return None

    return float(
        np.median(
            values
        )
    )


def build_desktop_reference(
    reference_frame: pd.DataFrame,
) -> dict[str, object]:
    """
    Build a frozen known-network reference from reference sessions only.

    Raw SSID/BSSID are not required. Hashes generated at collection time are
    the identity keys.
    """
    required = {
        "ssid_hash",
        "bssid_hash",
        "security_type",
        "security_strength",
        "session_id",
    }

    missing = (
        required
        - set(
            reference_frame.columns
        )
    )

    if missing:
        raise ValueError(
            "Colunas ausentes: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    ssid_profiles = {}

    bssid_to_ssids = defaultdict(
        set
    )

    grouped = (
        reference_frame.dropna(
            subset=[
                "ssid_hash",
                "bssid_hash",
            ]
        )
        .groupby(
            "ssid_hash",
            dropna=False,
        )
    )

    for ssid_hash, group in grouped:
        bssids = sorted(
            set(
                str(
                    value
                )
                for value in group[
                    "bssid_hash"
                ].dropna()
            )
        )

        security_types = sorted(
            set(
                str(
                    value
                )
                for value in group[
                    "security_type"
                ].dropna()
            )
        )

        security_strength_median = (
            _median(
                group[
                    "security_strength"
                ].tolist()
            )
        )

        if not bssids:
            continue

        ssid_profiles[
            str(
                ssid_hash
            )
        ] = {
            "bssid_hashes":
                bssids,
            "bssid_count":
                len(
                    bssids
                ),
            "security_types":
                security_types,
            "security_strength_median":
                security_strength_median,
            "reference_rows":
                int(
                    len(
                        group
                    )
                ),
            "reference_sessions":
                sorted(
                    set(
                        str(
                            value
                        )
                        for value in group[
                            "session_id"
                        ].dropna()
                    )
                ),
        }

        for bssid_hash in bssids:
            bssid_to_ssids[
                bssid_hash
            ].add(
                str(
                    ssid_hash
                )
            )

    return {
        "schema_version":
            "desktop_normal_reference_v1",
        "status":
            "frozen",
        "ssid_profile_count":
            len(
                ssid_profiles
            ),
        "bssid_mapping_count":
            len(
                bssid_to_ssids
            ),
        "ssid_profiles":
            ssid_profiles,
        "bssid_to_ssids": {
            bssid:
                sorted(
                    ssids
                )
            for bssid, ssids
            in bssid_to_ssids.items()
        },
        "scientific_rules": [
            "Built from reference split only.",
            "Model train, validation and test do not update this reference.",
            "No clear SSID/BSSID stored.",
            "Unknown context is not automatically classified as attack.",
        ],
    }


def _resolve_context(
    row,
    reference,
):
    ssid_hash = row.get(
        "ssid_hash"
    )

    if (
        pd.notna(
            ssid_hash
        )
        and str(
            ssid_hash
        )
        in reference[
            "ssid_profiles"
        ]
    ):
        return (
            str(
                ssid_hash
            ),
            "ssid_hash",
        )

    bssid_hash = row.get(
        "bssid_hash"
    )

    if pd.isna(
        bssid_hash
    ):
        return (
            None,
            "unresolved",
        )

    candidates = (
        reference[
            "bssid_to_ssids"
        ].get(
            str(
                bssid_hash
            ),
            [],
        )
    )

    if len(
        candidates
    ) == 1:
        return (
            candidates[
                0
            ],
            "bssid_fallback",
        )

    return (
        None,
        "unresolved",
    )


def transform_desktop_features(
    frame: pd.DataFrame,
    reference: dict[str, object],
) -> pd.DataFrame:
    rows = []

    for _, row in frame.iterrows():
        context_ssid, resolution = (
            _resolve_context(
                row,
                reference,
            )
        )

        profile = (
            reference[
                "ssid_profiles"
            ].get(
                context_ssid
            )
            if context_ssid
            is not None
            else None
        )

        context_available = (
            profile
            is not None
        )

        if not context_available:
            rows.append({
                "context_ssid_hash":
                    context_ssid,
                "context_resolution":
                    resolution,
                "context_available":
                    False,
                "ssid_bssid_count":
                    np.nan,
                "bssid_changed":
                    np.nan,
                "security_changed":
                    np.nan,
                "security_strength_delta":
                    np.nan,
                "feature_complete":
                    False,
            })

            continue

        bssid_hash = (
            None
            if pd.isna(
                row.get(
                    "bssid_hash"
                )
            )
            else str(
                row.get(
                    "bssid_hash"
                )
            )
        )

        security_type = (
            None
            if pd.isna(
                row.get(
                    "security_type"
                )
            )
            else str(
                row.get(
                    "security_type"
                )
            )
        )

        security_strength = pd.to_numeric(
            pd.Series([
                row.get(
                    "security_strength"
                )
            ]),
            errors="coerce",
        ).iloc[
            0
        ]

        median_strength = (
            profile[
                "security_strength_median"
            ]
        )

        ssid_bssid_count = float(
            profile[
                "bssid_count"
            ]
        )

        bssid_changed = (
            np.nan
            if bssid_hash
            is None
            else float(
                bssid_hash
                not in set(
                    profile[
                        "bssid_hashes"
                    ]
                )
            )
        )

        security_changed = (
            np.nan
            if security_type
            is None
            else float(
                security_type
                not in set(
                    profile[
                        "security_types"
                    ]
                )
            )
        )

        security_strength_delta = (
            np.nan
            if (
                pd.isna(
                    security_strength
                )
                or median_strength
                is None
            )
            else float(
                security_strength
                - float(
                    median_strength
                )
            )
        )

        values = [
            ssid_bssid_count,
            bssid_changed,
            security_changed,
            security_strength_delta,
        ]

        feature_complete = all(
            pd.notna(
                value
            )
            for value in values
        )

        rows.append({
            "context_ssid_hash":
                context_ssid,
            "context_resolution":
                resolution,
            "context_available":
                True,
            "ssid_bssid_count":
                ssid_bssid_count,
            "bssid_changed":
                bssid_changed,
            "security_changed":
                security_changed,
            "security_strength_delta":
                security_strength_delta,
            "feature_complete":
                bool(
                    feature_complete
                ),
        })

    return pd.DataFrame(
        rows
    )


def save_reference(
    reference: dict[str, object],
    path: str | Path,
) -> None:
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            reference,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )