from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from ml.preprocessing.schema import CANONICAL_COLUMNS, ensure_canonical_columns


SOURCE_DATASET = "zenodo_v2i"

WIFI_STANDARD_MAP = {
    "n": "802.11n",
    "ac": "802.11ac",
    "ad": "802.11ad",
}

CHANNEL_MAP = {
    "n": 6,
    "ac": 40,
    # 60.480 MHz corresponde ao canal 2 em 802.11ad.
    "ad": 2,
}


def normalize_v2i(df: pd.DataFrame) -> pd.DataFrame:
    normalized = pd.DataFrame(index=df.index)

    normalized["source_dataset"] = SOURCE_DATASET
    normalized["session_id"] = (
        "trace_" + df["traceNr"].astype(str)
    )
    normalized["environment"] = "vehicular_residential"

    normalized["collection_mode"] = "vehicular_experiment"

    if "receiverId" in df.columns:
        normalized["collector_id"] = (
            df["receiverId"].astype("string")
        )
    else:
        normalized["collector_id"] = pd.NA

    normalized["location_id"] = pd.NA
    normalized["position_x"] = np.nan
    normalized["position_y"] = np.nan
    normalized["position_z"] = np.nan

    normalized["observation_type"] = "aggregate_1s"

    systime = pd.to_numeric(
        df["systime"],
        errors="coerce",
    )

    normalized["timestamp"] = pd.to_datetime(
        systime,
        unit="s",
        errors="coerce",
    )

    start_by_trace = (
        systime
        .groupby(df["traceNr"])
        .transform("min")
    )

    normalized["elapsed_ms"] = (
        (systime - start_by_trace) * 1000
    )

    normalized["ssid"] = pd.NA
    normalized["bssid"] = pd.NA
    normalized["ap_id"] = df["senderId"].astype("string")

    beacon_rssi = pd.to_numeric(
        df["meanBeaconRssi"],
        errors="coerce",
    ).mask(
        pd.to_numeric(
            df["meanBeaconRssi"],
            errors="coerce",
        ) == -100
    )

    normalized["rssi_dbm"] = beacon_rssi
    normalized["rssi_kind"] = "mean_beacon_1s"

    normalized["rssi_all_frames_mean_dbm"] = (
        pd.to_numeric(
            df["rssiMean"],
            errors="coerce",
        )
    )

    normalized["channel"] = (
        df["wifiType"]
        .map(CHANNEL_MAP)
        .astype("Int64")
    )

    normalized["advertised_channel"] = pd.NA

    normalized["frequency_mhz"] = pd.to_numeric(
        df["channelFreq"],
        errors="coerce",
    )

    normalized["channel_width_mhz"] = pd.to_numeric(
        df["channelBw"],
        errors="coerce",
    )

    channel_util = pd.to_numeric(
        df["channelUtil"],
        errors="coerce",
    ).mask(
        pd.to_numeric(
            df["channelUtil"],
            errors="coerce",
        ) < 0
    )

    normalized["channel_utilization_pct"] = channel_util

    trace_40x = (
        df["traceNr"]
        .astype(str)
        .str.startswith("4")
    )

    n_or_ac = df["wifiType"].isin(["n", "ac"])

    normalized["channel_utilization_estimated"] = (
        trace_40x & n_or_ac
    )

    inter_beacon_seconds = pd.to_numeric(
        df["meanInterBeaconTime"],
        errors="coerce",
    ).mask(
        pd.to_numeric(
            df["meanInterBeaconTime"],
            errors="coerce",
        ) == 1.0
    )

    normalized["beacon_interval_raw"] = (
        inter_beacon_seconds
    )
    normalized["beacon_interval_ms"] = (
        inter_beacon_seconds * 1000
    )
    normalized["configured_beacon_interval_ms"] = np.nan
    normalized["measured_inter_beacon_ms"] = (
        inter_beacon_seconds * 1000
    )
    normalized["beacon_interval_kind"] = (
        "measured_mean_interarrival"
    )

    normalized["beacon_timestamp_us"] = np.nan

    normalized["beacon_count"] = (
        pd.to_numeric(
            df["nBeacons"],
            errors="coerce",
        )
        .astype("Int64")
    )

    normalized["security_type"] = pd.NA
    normalized["privacy_enabled"] = pd.NA

    normalized["wifi_standard"] = (
        df["wifiType"]
        .map(WIFI_STANDARD_MAP)
        .astype("string")
    )

    normalized["has_ht"] = pd.NA

    normalized["num_clients"] = (
        pd.to_numeric(
            df["nrClients"],
            errors="coerce",
        )
        .astype("Int64")
    )

    normalized["sequence_number"] = pd.NA
    normalized["frame_type"] = pd.NA

    normalized["vendor"] = pd.NA
    normalized["oui"] = pd.NA
    normalized["country_code"] = pd.NA

    normalized["is_hidden"] = pd.NA
    normalized["frame_length_bytes"] = pd.NA

    normalized["label"] = 0
    normalized["attack_type"] = pd.NA
    normalized["is_synthetic"] = False

    return ensure_canonical_columns(normalized)


def create_profiles(df):
    all_normal = df.copy()

    beacon_profile = df[
        (df["wifi_standard"] == "802.11n")
        & df["rssi_dbm"].notna()
        & df["beacon_interval_ms"].notna()
    ].copy()

    desktop_aux = df[
        df["wifi_standard"].isin(
            ["802.11n", "802.11ac"]
        )
    ].copy()

    ad_aux = df[
        df["wifi_standard"] == "802.11ad"
    ].copy()

    return (
        all_normal,
        beacon_profile,
        desktop_aux,
        ad_aux,
    )


def validate(
    all_normal,
    beacon_profile,
    desktop_aux,
    ad_aux,
):
    assert (all_normal["label"] == 0).all()
    assert not all_normal["is_synthetic"].any()

    print("Validação V2I concluída.")
    print(f"Total: {len(all_normal):,}")
    print(
        f"Beacon profile: {len(beacon_profile):,}"
    )
    print(
        f"Desktop auxiliar: {len(desktop_aux):,}"
    )
    print(
        f"802.11ad auxiliar: {len(ad_aux):,}"
    )


def main(input_file, output_dir):
    input_file = Path(input_file)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(input_file)
    normalized = normalize_v2i(df)

    (
        all_normal,
        beacon_profile,
        desktop_aux,
        ad_aux,
    ) = create_profiles(normalized)

    validate(
        all_normal,
        beacon_profile,
        desktop_aux,
        ad_aux,
    )

    all_normal.to_parquet(
        output_dir / "v2i_all_normal.parquet",
        index=False,
    )
    beacon_profile.to_parquet(
        output_dir / "v2i_beacon_profile.parquet",
        index=False,
    )
    desktop_aux.to_parquet(
        output_dir / "v2i_desktop_aux.parquet",
        index=False,
    )
    ad_aux.to_parquet(
        output_dir / "v2i_80211ad_aux.parquet",
        index=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    main(args.input, args.output)
