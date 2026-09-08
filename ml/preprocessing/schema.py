import pandas as pd


CANONICAL_COLUMNS = [
    "source_dataset",
    "session_id",
    "environment",

    "collection_mode",
    "collector_id",
    "location_id",
    "position_x",
    "position_y",
    "position_z",

    "observation_type",

    "timestamp",
    "elapsed_ms",

    "ssid",
    "bssid",
    "ap_id",

    "receiver_address",
    "transmitter_address",
    "mac_timestamp_raw",
    "addresses_anonymized",
    "ssid_anonymized",

    "rssi_dbm",
    "rssi_kind",
    "rssi_all_frames_mean_dbm",

    "channel",
    "advertised_channel",
    "frequency_mhz",
    "channel_width_mhz",
    "channel_utilization_pct",
    "channel_utilization_estimated",

    "beacon_interval_raw",
    "beacon_interval_ms",
    "configured_beacon_interval_ms",
    "measured_inter_beacon_ms",
    "beacon_interval_kind",
    "beacon_timestamp_us",
    "beacon_count",

    "security_type",
    "privacy_enabled",

    "wifi_standard",
    "has_ht",

    "num_clients",

    "sequence_number",

    "frame_type",

    "vendor",
    "oui",
    "country_code",

    "is_hidden",

    "frame_length_bytes",

    "label",
    "attack_type",
    "is_synthetic",
]


def ensure_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que todo normalizador retorne exatamente o schema canônico.

    Novas colunas podem ser adicionadas ao schema sem quebrar
    normalizadores antigos: campos indisponíveis ficam como pd.NA.
    """
    result = df.copy()

    for column in CANONICAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    return result[CANONICAL_COLUMNS]
