from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from ml.preprocessing.schema import CANONICAL_COLUMNS, ensure_canonical_columns
from ml.preprocessing.wifi_utils import channel_to_frequency_mhz


SOURCE_DATASET = "mendeley_rogue_ap"


def normalize_security(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip().upper()

    mapping = {
        "OPEN": "OPEN",
        "WEP": "WEP",
        "WPA": "WPA",
        "WPA2": "WPA2",
        "WPA3": "WPA3",
    }

    return mapping.get(value, "OTHER")


def normalize_base(
    df,
    session_id,
    label,
    attack_type=None,
    is_synthetic=False,
):
    normalized = pd.DataFrame(index=df.index)

    normalized["source_dataset"] = SOURCE_DATASET
    normalized["session_id"] = session_id
    normalized["environment"] = "unknown"

    normalized["collection_mode"] = "beacon_capture"
    normalized["collector_id"] = pd.NA
    normalized["location_id"] = pd.NA
    normalized["position_x"] = np.nan
    normalized["position_y"] = np.nan
    normalized["position_z"] = np.nan

    normalized["observation_type"] = "raw_beacon"

    normalized["timestamp"] = pd.NaT
    normalized["elapsed_ms"] = pd.to_numeric(
        df["Timestamp_ms"],
        errors="coerce",
    )

    normalized["ssid"] = df["SSID"].astype("string")
    normalized["bssid"] = df["BSSID"].astype("string")
    normalized["ap_id"] = pd.NA

    normalized["rssi_dbm"] = pd.to_numeric(
        df["RSSI"],
        errors="coerce",
    )
    normalized["rssi_kind"] = "single_beacon"
    normalized["rssi_all_frames_mean_dbm"] = np.nan

    normalized["channel"] = pd.to_numeric(
        df["Channel"],
        errors="coerce",
    ).astype("Int64")

    advertised_channel = pd.to_numeric(
        df["DSChannel"],
        errors="coerce",
    )
    advertised_channel = advertised_channel.where(
        advertised_channel > 0
    )
    normalized["advertised_channel"] = (
        advertised_channel.astype("Int64")
    )

    normalized["frequency_mhz"] = (
        normalized["channel"]
        .apply(channel_to_frequency_mhz)
    )

    channel_width = pd.to_numeric(
        df["HTChannelWidth"],
        errors="coerce",
    )

    normalized["channel_width_mhz"] = (
        channel_width
        .where(channel_width > 0)
        .astype("Int64")
    )

    normalized["channel_utilization_pct"] = np.nan
    normalized["channel_utilization_estimated"] = pd.NA

    beacon_interval = pd.to_numeric(
        df["BeaconInterval"],
        errors="coerce",
    )

    normalized["beacon_interval_raw"] = beacon_interval
    normalized["beacon_interval_ms"] = beacon_interval * 1.024
    normalized["configured_beacon_interval_ms"] = beacon_interval * 1.024
    normalized["measured_inter_beacon_ms"] = np.nan
    normalized["beacon_interval_kind"] = "configured_80211_tu"

    normalized["beacon_timestamp_us"] = pd.to_numeric(
        df["BeaconTimestamp"],
        errors="coerce",
    )

    normalized["beacon_count"] = 1

    normalized["security_type"] = (
        df["Encryption"]
        .apply(normalize_security)
        .astype("string")
    )

    normalized["privacy_enabled"] = (
        pd.to_numeric(
            df["Privacy"],
            errors="coerce",
        )
        .astype("boolean")
    )

    normalized["wifi_standard"] = pd.NA

    normalized["has_ht"] = (
        pd.to_numeric(
            df["HasHT"],
            errors="coerce",
        )
        .astype("boolean")
    )

    normalized["num_clients"] = pd.NA

    normalized["sequence_number"] = pd.to_numeric(
        df["SequenceNumber"],
        errors="coerce",
    ).astype("Int64")

    normalized["frame_type"] = "beacon"

    normalized["vendor"] = df["VendorName"].astype("string")
    normalized["oui"] = df["OUI"].astype("string")
    normalized["country_code"] = df["CountryCode"].astype("string")

    normalized["is_hidden"] = (
        pd.to_numeric(
            df["IsHidden"],
            errors="coerce",
        )
        .astype("boolean")
    )

    normalized["frame_length_bytes"] = pd.to_numeric(
        df["FrameLength"],
        errors="coerce",
    ).astype("Int64")

    normalized["label"] = label
    normalized["attack_type"] = attack_type
    normalized["is_synthetic"] = is_synthetic

    return ensure_canonical_columns(normalized)


def find_legitimate_csvs(dataset_dir: Path):
    candidates = []

    for session_dir in sorted(dataset_dir.glob("session_*")):
        for csv_path in sorted(session_dir.glob("*.csv")):
            candidates.append(
                (session_dir.name, csv_path)
            )

    return candidates


def normalize_legitimate(dataset_dir):
    frames = []

    for session_id, csv_path in find_legitimate_csvs(dataset_dir):
        df = pd.read_csv(csv_path)

        frames.append(
            normalize_base(
                df=df,
                session_id=session_id,
                label=0,
                attack_type=None,
                is_synthetic=False,
            )
        )

    if not frames:
        raise RuntimeError(
            "Nenhuma sessão legítima encontrada."
        )

    return pd.concat(
        frames,
        ignore_index=True,
    )


def locate_rogue_processed(dataset_dir: Path):
    candidates = list(
        dataset_dir.rglob("rogue_processed.csv")
    )

    if not candidates:
        raise FileNotFoundError(
            "rogue_processed.csv não encontrado."
        )

    return candidates[0]


def normalize_attacks(dataset_dir):
    csv_path = locate_rogue_processed(dataset_dir)
    df = pd.read_csv(csv_path)

    attacks = df[
        pd.to_numeric(
            df["is_rogue"],
            errors="coerce",
        ) == 1
    ].copy()

    attack_type = (
        attacks["_rogue_type"].astype("string")
        if "_rogue_type" in attacks.columns
        else pd.Series(
            "rogue",
            index=attacks.index,
            dtype="string",
        )
    )

    return normalize_base(
        df=attacks,
        session_id="synthetic_rogue",
        label=1,
        attack_type=attack_type,
        is_synthetic=True,
    )


def validate(normal_df, attack_df):
    assert set(
        normal_df["label"].dropna().unique()
    ) == {0}

    assert set(
        attack_df["label"].dropna().unique()
    ) == {1}

    print("Validação Mendeley concluída.")
    print(f"Normais: {len(normal_df):,}")
    print(
        f"Ataques sintéticos: {len(attack_df):,}"
    )


def main(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    normal_df = normalize_legitimate(input_dir)
    attack_df = normalize_attacks(input_dir)

    validate(normal_df, attack_df)

    normal_df.to_parquet(
        output_dir / "mendeley_normal.parquet",
        index=False,
    )

    attack_df.to_parquet(
        output_dir / "mendeley_attack.parquet",
        index=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    main(args.input, args.output)
