from __future__ import annotations

import numpy as np
import pandas as pd


RSSI_MIN_DBM = -110.0
RSSI_MAX_DBM = 0.0


def add_beacon_quality_flags(df):
    result = df.copy()

    rssi = pd.to_numeric(
        result["rssi_mean_dbm"],
        errors="coerce",
    )

    frequency = pd.to_numeric(
        result["frequency_mhz"],
        errors="coerce",
    )

    beacon_count = pd.to_numeric(
        result["beacon_count"],
        errors="coerce",
    )

    inter = pd.to_numeric(
        result["observed_inter_beacon_ms"],
        errors="coerce",
    )

    result["q_rssi_plausible"] = (
        rssi.between(
            RSSI_MIN_DBM,
            RSSI_MAX_DBM,
            inclusive="both",
        )
    )

    result["q_frequency_present"] = (
        frequency.notna()
        & (frequency > 0)
    )

    result["q_beacon_count_positive"] = (
        beacon_count.notna()
        & (beacon_count >= 1)
    )

    # Essa flag indica apenas validade básica.
    # Não define que a feature seja comparável entre fontes.
    result["q_inter_beacon_positive"] = (
        inter.notna()
        & (inter > 0)
    )

    result["q_beacon_core"] = (
        result["q_rssi_plausible"]
        & result["q_frequency_present"]
        & result[
            "q_beacon_count_positive"
        ]
    )

    return result


def add_temporal_quality_flags(df):
    result = df.copy()

    mean = pd.to_numeric(
        result["rssi_mean_dbm"],
        errors="coerce",
    )
    minimum = pd.to_numeric(
        result["rssi_min_dbm"],
        errors="coerce",
    )
    maximum = pd.to_numeric(
        result["rssi_max_dbm"],
        errors="coerce",
    )
    std = pd.to_numeric(
        result["rssi_std_db"],
        errors="coerce",
    )
    delta = pd.to_numeric(
        result["rssi_delta_db"],
        errors="coerce",
    )
    count = pd.to_numeric(
        result["window_count"],
        errors="coerce",
    )

    result["q_rssi_plausible"] = (
        mean.between(
            RSSI_MIN_DBM,
            RSSI_MAX_DBM,
            inclusive="both",
        )
        & minimum.between(
            RSSI_MIN_DBM,
            RSSI_MAX_DBM,
            inclusive="both",
        )
        & maximum.between(
            RSSI_MIN_DBM,
            RSSI_MAX_DBM,
            inclusive="both",
        )
    )

    result["q_temporal_complete"] = (
        std.notna()
        & delta.notna()
        & count.notna()
    )

    result["q_window_has_multiple_samples"] = (
        count >= 2
    )

    result["q_temporal_basic"] = (
        result["q_rssi_plausible"]
        & result["q_temporal_complete"]
        & (count >= 1)
    )

    # Perfil recomendado para o primeiro experimento temporal:
    # exige pelo menos duas janelas de ~1 s dentro do bloco de 5 s.
    result["q_temporal_rich"] = (
        result["q_temporal_basic"]
        & result[
            "q_window_has_multiple_samples"
        ]
    )

    return result


def filter_temporal_rich(df):
    flagged = add_temporal_quality_flags(
        df
    )

    return flagged[
        flagged["q_temporal_rich"]
    ].copy()


def quality_summary(df, flag_columns):
    summary = {
        "rows": int(len(df)),
    }

    for column in flag_columns:
        if column not in df:
            continue

        values = (
            df[column]
            .fillna(False)
            .astype(bool)
        )

        summary[column] = {
            "pass": int(
                values.sum()
            ),
            "fail": int(
                (~values).sum()
            ),
            "pass_rate": float(
                values.mean()
            ),
        }

    return summary
