from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _clean_bssid(value):
    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    return text or None


def hash_bssid(value):
    value = _clean_bssid(
        value
    )

    if value is None:
        return None

    return hashlib.sha256(
        (
            "bssid|"
            + value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def build_tsf_reference(
    reference_df,
):
    """
    Constrói histórico de TSF por:

        session_id + BSSID

    A sessão faz parte da chave porque TSF representa uptime do AP e pode
    reiniciar legitimamente entre sessões/coletas diferentes.

    Nenhum BSSID cru é persistido no artefato.
    """
    required = {
        "session_id",
        "bssid",
        "beacon_timestamp_us",
    }

    missing = (
        required
        - set(
            reference_df.columns
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

    frame = reference_df[
        [
            "session_id",
            "bssid",
            "beacon_timestamp_us",
        ]
    ].copy()

    frame[
        "bssid_hash"
    ] = frame[
        "bssid"
    ].map(
        hash_bssid
    )

    frame[
        "tsf_us"
    ] = pd.to_numeric(
        frame[
            "beacon_timestamp_us"
        ],
        errors="coerce",
    )

    frame = frame.dropna(
        subset=[
            "session_id",
            "bssid_hash",
            "tsf_us",
        ]
    )

    grouped = (
        frame.groupby(
            [
                "session_id",
                "bssid_hash",
            ],
            dropna=False,
        )[
            "tsf_us"
        ]
        .agg(
            [
                "count",
                "min",
                "max",
                "median",
            ]
        )
        .reset_index()
    )

    entries = {}

    for _, row in (
        grouped.iterrows()
    ):
        key = (
            str(
                row[
                    "session_id"
                ]
            )
            + "|"
            + str(
                row[
                    "bssid_hash"
                ]
            )
        )

        entries[
            key
        ] = {
            "session_id":
                str(
                    row[
                        "session_id"
                    ]
                ),
            "bssid_hash":
                str(
                    row[
                        "bssid_hash"
                    ]
                ),
            "count":
                int(
                    row[
                        "count"
                    ]
                ),
            "min_tsf_us":
                float(
                    row[
                        "min"
                    ]
                ),
            "max_tsf_us":
                float(
                    row[
                        "max"
                    ]
                ),
            "median_tsf_us":
                float(
                    row[
                        "median"
                    ]
                ),
        }

    return {
        "version":
            "1.0.0",
        "key":
            "session_id + sha256(bssid)",
        "semantics": (
            "TSF is AP uptime-like state; session scoping avoids treating "
            "legitimate resets between independent capture sessions as "
            "within-session monotonic violations."
        ),
        "entries":
            entries,
    }


def transform_tsf(
    df,
    reference,
    source_session_column="session_id",
):
    """
    Deriva TSF de forma causal usando somente o reference congelado.

    Primary ablation feature:

        tsf_reference_monotonic_violation = 1

    quando:

        current_tsf < max_tsf_seen_in_reference

    para o mesmo BSSID e mesma sessão de origem.

    Isso sinaliza reset/reboot/retrocesso em relação ao histórico,
    mas NÃO prova ataque.
    """
    rows = []

    entries = reference[
        "entries"
    ]

    for _, row in df.iterrows():
        session_id = row.get(
            source_session_column
        )

        bssid_hash = hash_bssid(
            row.get(
                "bssid"
            )
        )

        current_tsf = pd.to_numeric(
            pd.Series(
                [
                    row.get(
                        "beacon_timestamp_us"
                    )
                ]
            ),
            errors="coerce",
        ).iloc[0]

        key = None

        if (
            session_id is not None
            and not pd.isna(
                session_id
            )
            and bssid_hash
            is not None
        ):
            key = (
                str(
                    session_id
                )
                + "|"
                + bssid_hash
            )

        profile = (
            entries.get(
                key
            )
            if key
            else None
        )

        available = (
            profile is not None
            and pd.notna(
                current_tsf
            )
        )

        if available:
            ref_max = float(
                profile[
                    "max_tsf_us"
                ]
            )

            violation = float(
                float(
                    current_tsf
                )
                < ref_max
            )

            delta_ms = (
                float(
                    current_tsf
                )
                - ref_max
            ) / 1000.0

            log_ratio = (
                np.log1p(
                    float(
                        current_tsf
                    )
                )
                - np.log1p(
                    ref_max
                )
            )
        else:
            ref_max = np.nan
            violation = np.nan
            delta_ms = np.nan
            log_ratio = np.nan

        rows.append({
            "source_session_id":
                session_id,
            "bssid_hash":
                bssid_hash,
            "tsf_reference_available":
                bool(
                    available
                ),
            "tsf_reference_max_us":
                ref_max,
            "current_tsf_us":
                (
                    float(
                        current_tsf
                    )
                    if pd.notna(
                        current_tsf
                    )
                    else np.nan
                ),
            "tsf_reference_monotonic_violation":
                violation,
            "tsf_delta_from_reference_max_ms":
                delta_ms,
            "tsf_log_ratio_to_reference_max":
                float(
                    log_ratio
                )
                if pd.notna(
                    log_ratio
                )
                else np.nan,
        })

    return pd.DataFrame(
        rows
    )


def save_tsf_reference(
    reference,
    path,
):
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
