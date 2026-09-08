from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from ml.preprocessing.wifi_utils import channel_to_frequency_mhz


def _stable_group_id(*parts):
    raw = "|".join(
        "" if pd.isna(value)
        else str(value)
        for value in parts
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:20]


def wifi_band_from_frequency(
    frequency_mhz,
):
    if pd.isna(frequency_mhz):
        return pd.NA

    value = float(frequency_mhz)

    if 2400 <= value < 2500:
        return "2.4GHz"

    if 4900 <= value < 5925:
        return "5GHz"

    if 5925 <= value < 7125:
        return "6GHz"

    if 57000 <= value <= 71000:
        return "60GHz"

    return "OTHER"


def build_mendeley_beacon_1s(
    canonical,
):
    """
    Reduz Beacon individual do Mendeley para janela de 1 segundo.

    observed_inter_beacon_ms:
        diferença entre elapsed_ms de Beacons consecutivos do mesmo
        BSSID, sessão e tipo de ataque.

    configured_beacon_interval_ms:
        permanece separado; não é usado como equivalente ao
        meanInterBeaconTime do V2I.
    """
    df = canonical.copy()

    required = {
        "source_dataset",
        "session_id",
        "elapsed_ms",
        "bssid",
        "rssi_dbm",
        "channel",
        "advertised_channel",
        "label",
        "is_synthetic",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise ValueError(
            "Colunas Mendeley ausentes: "
            + ", ".join(
                sorted(missing)
            )
        )

    if "attack_type" not in df:
        df["attack_type"] = pd.NA

    df["_attack_group"] = (
        df["attack_type"]
        .astype("string")
        .fillna("")
    )

    df["_bssid_group"] = (
        df["bssid"]
        .astype("string")
        .fillna("__MISSING_BSSID__")
    )

    df["elapsed_ms"] = pd.to_numeric(
        df["elapsed_ms"],
        errors="coerce",
    )

    df["rssi_dbm"] = pd.to_numeric(
        df["rssi_dbm"],
        errors="coerce",
    )

    df["channel"] = pd.to_numeric(
        df["channel"],
        errors="coerce",
    )

    df["advertised_channel"] = (
        pd.to_numeric(
            df["advertised_channel"],
            errors="coerce",
        )
    )

    group_identity = [
        "source_dataset",
        "session_id",
        "_attack_group",
        "_bssid_group",
    ]

    df = df.sort_values(
        group_identity
        + ["elapsed_ms"]
    )

    df["_inter_beacon_ms"] = (
        df.groupby(
            group_identity,
            sort=False,
        )["elapsed_ms"]
        .diff()
    )

    df["_window_start_ms"] = (
        np.floor(
            df["elapsed_ms"]
            / 1000.0
        )
        * 1000.0
    )

    # Para representar o canal do AP, preferimos DSChannel quando válido.
    df["_ap_channel"] = (
        df["advertised_channel"]
        .where(
            df["advertised_channel"]
            > 0,
            df["channel"],
        )
    )

    configured_column = (
        "configured_beacon_interval_ms"
        if "configured_beacon_interval_ms"
        in df.columns
        else "beacon_interval_ms"
    )

    if configured_column not in df:
        df[configured_column] = np.nan

    if "security_type" not in df:
        df["security_type"] = pd.NA

    aggregate_keys = (
        group_identity
        + ["_window_start_ms"]
    )

    grouped = df.groupby(
        aggregate_keys,
        sort=False,
        dropna=False,
    )

    result = grouped.agg(
        rssi_mean_dbm=(
            "rssi_dbm",
            "mean",
        ),
        beacon_count=(
            "rssi_dbm",
            "size",
        ),
        observed_inter_beacon_ms=(
            "_inter_beacon_ms",
            "mean",
        ),
        inter_beacon_sample_count=(
            "_inter_beacon_ms",
            "count",
        ),
        channel=(
            "_ap_channel",
            "first",
        ),
        configured_beacon_interval_ms=(
            configured_column,
            "median",
        ),
        security_type=(
            "security_type",
            "first",
        ),
        label=(
            "label",
            "first",
        ),
        is_synthetic=(
            "is_synthetic",
            "first",
        ),
    ).reset_index()

    result = result[
        result["rssi_mean_dbm"]
        .notna()
    ].copy()

    result["frequency_mhz"] = (
        result["channel"]
        .apply(
            channel_to_frequency_mhz
        )
    )

    result["wifi_band"] = (
        result["frequency_mhz"]
        .apply(
            wifi_band_from_frequency
        )
    )

    result["network_identity_id"] = [
        _stable_group_id(
            source,
            bssid,
        )
        for (
            source,
            bssid,
        ) in zip(
            result["source_dataset"],
            result["_bssid_group"],
        )
    ]

    result["network_group_id"] = [
        _stable_group_id(
            source,
            session,
            attack,
            bssid,
        )
        for (
            source,
            session,
            attack,
            bssid,
        ) in zip(
            result["source_dataset"],
            result["session_id"],
            result["_attack_group"],
            result["_bssid_group"],
        )
    ]

    result["attack_type"] = (
        result["_attack_group"]
        .replace(
            "",
            pd.NA,
        )
    )

    result["window_start_ms"] = (
        result["_window_start_ms"]
    )

    columns = [
        "source_dataset",
        "session_id",
        "network_identity_id",
        "network_group_id",
        "window_start_ms",
        "label",
        "attack_type",
        "is_synthetic",
        "rssi_mean_dbm",
        "beacon_count",
        "observed_inter_beacon_ms",
        "inter_beacon_sample_count",
        "channel",
        "frequency_mhz",
        "wifi_band",
        "configured_beacon_interval_ms",
        "security_type",
    ]

    return result[
        columns
    ].reset_index(
        drop=True
    )


def build_v2i_beacon_1s(
    canonical,
):
    """
    V2I já é agregado por aproximadamente 1 segundo.

    Mantemos apenas 802.11n com RSSI de Beacon e
    meanInterBeaconTime válidos.
    """
    df = canonical.copy()

    required = {
        "source_dataset",
        "session_id",
        "elapsed_ms",
        "ap_id",
        "rssi_dbm",
        "frequency_mhz",
        "beacon_count",
        "label",
        "is_synthetic",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise ValueError(
            "Colunas V2I ausentes: "
            + ", ".join(
                sorted(missing)
            )
        )

    measured_column = (
        "measured_inter_beacon_ms"
        if "measured_inter_beacon_ms"
        in df.columns
        else "beacon_interval_ms"
    )

    if "wifi_standard" in df:
        df = df[
            df["wifi_standard"]
            == "802.11n"
        ].copy()

    df["_rssi"] = pd.to_numeric(
        df["rssi_dbm"],
        errors="coerce",
    )

    df["_inter"] = pd.to_numeric(
        df[measured_column],
        errors="coerce",
    )

    df = df[
        df["_rssi"].notna()
        & df["_inter"].notna()
    ].copy()

    elapsed = pd.to_numeric(
        df["elapsed_ms"],
        errors="coerce",
    )

    result = pd.DataFrame(
        index=df.index
    )

    result["source_dataset"] = (
        df["source_dataset"]
    )

    result["session_id"] = (
        df["session_id"]
    )

    result["network_identity_id"] = [
        _stable_group_id(
            source,
            ap_id,
        )
        for source, ap_id
        in zip(
            df["source_dataset"],
            df["ap_id"],
        )
    ]

    result["network_group_id"] = [
        _stable_group_id(
            source,
            session,
            ap_id,
        )
        for source, session, ap_id
        in zip(
            df["source_dataset"],
            df["session_id"],
            df["ap_id"],
        )
    ]

    result["window_start_ms"] = (
        np.floor(
            elapsed / 1000.0
        )
        * 1000.0
    )

    result["label"] = pd.to_numeric(
        df["label"],
        errors="coerce",
    )

    result["attack_type"] = (
        df["attack_type"]
        if "attack_type" in df
        else pd.NA
    )

    result["is_synthetic"] = (
        df["is_synthetic"]
    )

    result["rssi_mean_dbm"] = (
        df["_rssi"]
    )

    result["beacon_count"] = (
        pd.to_numeric(
            df["beacon_count"],
            errors="coerce",
        )
    )

    result[
        "observed_inter_beacon_ms"
    ] = df["_inter"]

    # nBeacons é uma boa indicação do número de observações
    # que participaram da média do V2I.
    result[
        "inter_beacon_sample_count"
    ] = pd.to_numeric(
        df["beacon_count"],
        errors="coerce",
    )

    result["channel"] = (
        pd.to_numeric(
            df["channel"],
            errors="coerce",
        )
        if "channel" in df
        else np.nan
    )

    result["frequency_mhz"] = (
        pd.to_numeric(
            df["frequency_mhz"],
            errors="coerce",
        )
    )

    result["wifi_band"] = (
        result["frequency_mhz"]
        .apply(
            wifi_band_from_frequency
        )
    )

    result[
        "configured_beacon_interval_ms"
    ] = np.nan

    result["security_type"] = pd.NA

    return result.reset_index(
        drop=True
    )


def build_rssi_temporal_5s(
    beacon_profile,
):
    """
    Agrega médias RSSI de janelas de ~1 segundo em blocos de 5 s.

    Implementação vetorizada para evitar milhares de loops Python.
    """
    df = beacon_profile.copy()

    required = {
        "source_dataset",
        "session_id",
        "network_identity_id",
        "network_identity_id",
        "network_group_id",
        "window_start_ms",
        "rssi_mean_dbm",
        "label",
        "is_synthetic",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise ValueError(
            "Colunas Beacon Profile ausentes: "
            + ", ".join(
                sorted(missing)
            )
        )

    if "attack_type" not in df:
        df["attack_type"] = pd.NA

    df["_attack_group"] = (
        df["attack_type"]
        .astype("string")
        .fillna("")
    )

    df["window_start_ms"] = (
        pd.to_numeric(
            df["window_start_ms"],
            errors="coerce",
        )
    )

    df["rssi_mean_dbm"] = (
        pd.to_numeric(
            df["rssi_mean_dbm"],
            errors="coerce",
        )
    )

    df = df[
        df["rssi_mean_dbm"]
        .notna()
    ].copy()

    df["_window_5s_ms"] = (
        np.floor(
            df["window_start_ms"]
            / 5000.0
        )
        * 5000.0
    )

    df = df.sort_values(
        [
            "source_dataset",
            "session_id",
            "network_identity_id",
            "network_group_id",
            "_attack_group",
            "_window_5s_ms",
            "window_start_ms",
        ]
    )

    keys = [
        "source_dataset",
        "session_id",
        "network_identity_id",
        "network_group_id",
        "_attack_group",
        "label",
        "is_synthetic",
        "_window_5s_ms",
    ]

    grouped = df.groupby(
        keys,
        sort=False,
        dropna=False,
    )

    base = grouped[
        "rssi_mean_dbm"
    ].agg(
        rssi_mean_dbm="mean",
        rssi_min_dbm="min",
        rssi_max_dbm="max",
        rssi_first_dbm="first",
        rssi_last_dbm="last",
        window_count="count",
    )

    squared = (
        df["rssi_mean_dbm"]
        ** 2
    )

    mean_square = (
        df.assign(
            _rssi_square=squared
        )
        .groupby(
            keys,
            sort=False,
            dropna=False,
        )["_rssi_square"]
        .mean()
    )

    base["rssi_std_db"] = np.sqrt(
        np.maximum(
            mean_square
            - base[
                "rssi_mean_dbm"
            ] ** 2,
            0.0,
        )
    )

    base["rssi_delta_db"] = (
        base["rssi_last_dbm"]
        - base["rssi_first_dbm"]
    )

    result = (
        base.reset_index()
    )

    result["attack_type"] = (
        result["_attack_group"]
        .replace(
            "",
            pd.NA,
        )
    )

    result["window_start_ms"] = (
        result["_window_5s_ms"]
    )

    columns = [
        "source_dataset",
        "session_id",
        "network_identity_id",
        "network_group_id",
        "window_start_ms",
        "label",
        "attack_type",
        "is_synthetic",
        "rssi_mean_dbm",
        "rssi_std_db",
        "rssi_min_dbm",
        "rssi_max_dbm",
        "rssi_delta_db",
        "window_count",
    ]

    return result[
        columns
    ].reset_index(
        drop=True
    )


def split_feature_columns(
    df,
    feature_columns,
):
    """
    Separa X dos metadados, evitando leakage por fonte/ID.
    """
    missing = (
        set(feature_columns)
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Features ausentes: "
            + ", ".join(
                sorted(missing)
            )
        )

    X = df[
        feature_columns
    ].copy()

    metadata_columns = [
        "source_dataset",
        "session_id",
        "network_identity_id",
        "network_group_id",
        "window_start_ms",
        "label",
        "attack_type",
        "is_synthetic",
    ]

    metadata = df[
        [
            column
            for column
            in metadata_columns
            if column in df
        ]
    ].copy()

    return X, metadata
