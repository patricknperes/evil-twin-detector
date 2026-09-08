PROFILE_METADATA_COLUMNS = [
    "source_dataset",
    "session_id",
    "network_identity_id",
    "network_group_id",
    "window_start_ms",
    "label",
    "attack_type",
    "is_synthetic",
]

PROFILE_BEACON_1S_FEATURES = [
    "rssi_mean_dbm",
    "beacon_count",
    "observed_inter_beacon_ms",
    "frequency_mhz",
]

PROFILE_BEACON_1S_AUXILIARY = [
    "channel",
    "wifi_band",
    "configured_beacon_interval_ms",
    "security_type",
    "inter_beacon_sample_count",
]

PROFILE_RSSI_TEMPORAL_5S_FEATURES = [
    "rssi_mean_dbm",
    "rssi_std_db",
    "rssi_min_dbm",
    "rssi_max_dbm",
    "rssi_delta_db",
    "window_count",
]

FEATURE_PROFILES = {
    "PROFILE_BEACON_1S": {
        "metadata": PROFILE_METADATA_COLUMNS,
        "features": PROFILE_BEACON_1S_FEATURES,
        "auxiliary": PROFILE_BEACON_1S_AUXILIARY,
        "sources": [
            "mendeley_rogue_ap",
            "zenodo_v2i",
        ],
    },
    "PROFILE_RSSI_TEMPORAL_5S": {
        "metadata": PROFILE_METADATA_COLUMNS,
        "features": PROFILE_RSSI_TEMPORAL_5S_FEATURES,
        "auxiliary": [],
        "sources": [
            "mendeley_rogue_ap",
            "zenodo_v2i",
        ],
    },
}
