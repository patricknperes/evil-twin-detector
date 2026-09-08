from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import argparse
import ast
import io
import json
import shutil
import tempfile
import zipfile

import numpy as np
import pandas as pd

from ml.preprocessing.schema import ensure_canonical_columns


SOURCE_DATASET = "zenodo_station_management_frames"
ENVIRONMENT = "public_train_station"

FRAME_TYPE_MAP = {
    "Dot11Beacon": "beacon",
    "Dot11ProbeReq": "probe_request",
    "Dot11ProbeResp": "probe_response",
}


def clean_ssid(value):
    """
    O CSV armazena SSIDs como representação textual de bytes,
    por exemplo: b'NETWORK_1' e b''.
    """
    if pd.isna(value):
        return pd.NA

    text = str(value).strip()

    if not text:
        return pd.NA

    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, bytes):
            decoded = parsed.decode(
                "utf-8",
                errors="replace",
            )
            return decoded if decoded else pd.NA
    except (ValueError, SyntaxError):
        pass

    return text


def normalize_mac(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip().lower()

    if not value:
        return pd.NA

    return value


def derive_bssid(frame_type, addr2, addr3):
    """
    Para Beacon e Probe Response, addr3 representa o BSSID
    na estrutura 802.11 usada por este dataset.

    Para Probe Request não forçamos um BSSID: esse frame pode ser
    wildcard/direcionado e os CSVs anonimizados não oferecem contexto
    suficiente para inferir com segurança um AP associado.
    """
    if frame_type in {
        "beacon",
        "probe_response",
    }:
        if pd.notna(addr3):
            return addr3

        if pd.notna(addr2):
            return addr2

    return pd.NA


def normalize_capture(
    df: pd.DataFrame,
    capture_id: str,
) -> pd.DataFrame:
    required = {
        "Timestamp",
        "type",
        "MAC_timestamp",
        "rssi",
        "addr1",
        "addr2",
        "addr3",
        "SSID",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(sorted(missing))
        )

    normalized = pd.DataFrame(index=df.index)

    normalized["source_dataset"] = SOURCE_DATASET
    normalized["session_id"] = capture_id
    normalized["environment"] = ENVIRONMENT

    normalized["collection_mode"] = "public_station_capture"
    normalized["collector_id"] = pd.NA
    normalized["location_id"] = "belgian_train_station"

    normalized["position_x"] = np.nan
    normalized["position_y"] = np.nan
    normalized["position_z"] = np.nan

    normalized["observation_type"] = "management_frame"

    timestamp_seconds = pd.to_numeric(
        df["Timestamp"],
        errors="coerce",
    )

    normalized["timestamp"] = pd.to_datetime(
        timestamp_seconds,
        unit="s",
        utc=True,
        errors="coerce",
    )

    first_timestamp = timestamp_seconds.min()

    normalized["elapsed_ms"] = (
        timestamp_seconds - first_timestamp
    ) * 1000.0

    normalized["ssid"] = (
        df["SSID"]
        .apply(clean_ssid)
        .astype("string")
    )

    receiver = (
        df["addr1"]
        .apply(normalize_mac)
        .astype("string")
    )

    transmitter = (
        df["addr2"]
        .apply(normalize_mac)
        .astype("string")
    )

    addr3 = (
        df["addr3"]
        .apply(normalize_mac)
        .astype("string")
    )

    frame_type = (
        df["type"]
        .map(FRAME_TYPE_MAP)
        .fillna(
            df["type"]
            .astype("string")
            .str.lower()
        )
        .astype("string")
    )

    normalized["receiver_address"] = receiver
    normalized["transmitter_address"] = transmitter

    normalized["mac_timestamp_raw"] = pd.to_numeric(
        df["MAC_timestamp"],
        errors="coerce",
    )

    # O README não documenta de forma suficiente a unidade
    # de MAC_timestamp; preservamos o valor bruto.
    normalized["addresses_anonymized"] = True
    normalized["ssid_anonymized"] = True

    bssid = [
        derive_bssid(ft, a2, a3)
        for ft, a2, a3
        in zip(
            frame_type,
            transmitter,
            addr3,
        )
    ]

    normalized["bssid"] = pd.Series(
        bssid,
        index=df.index,
        dtype="string",
    )

    # O identificador anonimizado do AP só é preenchido
    # quando o BSSID pode ser obtido com segurança.
    normalized["ap_id"] = normalized["bssid"]

    normalized["rssi_dbm"] = pd.to_numeric(
        df["rssi"],
        errors="coerce",
    )

    normalized["rssi_kind"] = "management_frame_signal"
    normalized["rssi_all_frames_mean_dbm"] = np.nan

    # O CSV não possui canal/frequência/segurança/beacon interval.
    normalized["channel"] = pd.NA
    normalized["advertised_channel"] = pd.NA
    normalized["frequency_mhz"] = np.nan
    normalized["channel_width_mhz"] = np.nan
    normalized["channel_utilization_pct"] = np.nan
    normalized["channel_utilization_estimated"] = pd.NA

    normalized["beacon_interval_raw"] = np.nan
    normalized["beacon_interval_ms"] = np.nan
    normalized["beacon_interval_kind"] = pd.NA
    normalized["beacon_timestamp_us"] = np.nan

    # Cada linha é um frame individual.
    normalized["beacon_count"] = (
        frame_type.eq("beacon")
        .astype("Int64")
    )

    normalized["security_type"] = pd.NA
    normalized["privacy_enabled"] = pd.NA
    normalized["wifi_standard"] = pd.NA
    normalized["has_ht"] = pd.NA
    normalized["num_clients"] = pd.NA
    normalized["sequence_number"] = pd.NA

    normalized["frame_type"] = frame_type

    normalized["vendor"] = pd.NA
    normalized["oui"] = pd.NA
    normalized["country_code"] = pd.NA
    normalized["is_hidden"] = pd.NA
    normalized["frame_length_bytes"] = pd.NA

    # Capturas de funcionamento normal em local público.
    normalized["label"] = 0
    normalized["attack_type"] = pd.NA
    normalized["is_synthetic"] = False

    return ensure_canonical_columns(
        normalized
    )


class DirectorySource:
    def __init__(self, root: Path):
        self.root = find_directory_root(root)

    def captures(self):
        result = []

        for capture_id in ("1", "2"):
            candidates = [
                self.root
                / capture_id
                / f"capture-{capture_id}.csv",
                self.root
                / "datasets"
                / capture_id
                / f"capture-{capture_id}.csv",
            ]

            for candidate in candidates:
                if candidate.exists():
                    result.append(
                        (
                            f"capture_{capture_id}",
                            candidate,
                        )
                    )
                    break

        return result

    def read_csv(self, source):
        return pd.read_csv(source)


class ZipSource:
    def __init__(self, path: Path):
        self.zf = zipfile.ZipFile(
            path,
            "r",
        )
        self.capture_names = (
            discover_capture_names(
                self.zf.namelist()
            )
        )

    def close(self):
        self.zf.close()

    def captures(self):
        return [
            (
                capture_id,
                archive_name,
            )
            for (
                capture_id,
                archive_name,
            ) in sorted(
                self.capture_names.items()
            )
        ]

    def read_csv(self, archive_name):
        with self.zf.open(
            archive_name,
            "r",
        ) as raw:
            return pd.read_csv(raw)


def find_directory_root(path: Path):
    path = path.resolve()

    if (
        path / "1" / "capture-1.csv"
    ).exists():
        return path

    if (
        path
        / "datasets"
        / "1"
        / "capture-1.csv"
    ).exists():
        return path / "datasets"

    for child in path.iterdir():
        if (
            child.is_dir()
            and (
                child
                / "1"
                / "capture-1.csv"
            ).exists()
        ):
            return child

    raise FileNotFoundError(
        "Não foi possível localizar "
        "capture-1.csv/capture-2.csv."
    )


def discover_capture_names(names):
    result = {}

    for capture_number in ("1", "2"):
        suffix = (
            f"{capture_number}/"
            f"capture-{capture_number}.csv"
        )

        for name in names:
            if name.endswith(suffix):
                result[
                    f"capture_{capture_number}"
                ] = name
                break

    return result


def zip_has_captures(path: Path):
    with zipfile.ZipFile(
        path,
        "r",
    ) as zf:
        return bool(
            discover_capture_names(
                zf.namelist()
            )
        )


@contextmanager
def open_source(input_path):
    """
    Aceita:
      - pasta extraída;
      - datasets.zip;
      - ZIP externo do Zenodo contendo datasets.zip.
    """
    input_path = Path(
        input_path
    ).resolve()

    if input_path.is_dir():
        yield DirectorySource(
            input_path
        )
        return

    if not zipfile.is_zipfile(
        input_path
    ):
        raise ValueError(
            "A entrada deve ser "
            "uma pasta ou arquivo ZIP."
        )

    if zip_has_captures(
        input_path
    ):
        source = ZipSource(
            input_path
        )

        try:
            yield source
        finally:
            source.close()

        return

    with zipfile.ZipFile(
        input_path,
        "r",
    ) as outer:
        nested_zips = [
            name
            for name in outer.namelist()
            if name.lower().endswith(
                ".zip"
            )
        ]

        if len(nested_zips) != 1:
            raise FileNotFoundError(
                "Não foi possível identificar "
                "datasets.zip dentro do pacote."
            )

        with tempfile.TemporaryDirectory(
            prefix="station_wifi_"
        ) as tmp:
            inner_path = (
                Path(tmp)
                / Path(
                    nested_zips[0]
                ).name
            )

            with (
                outer.open(
                    nested_zips[0],
                    "r",
                ) as source_file,
                open(
                    inner_path,
                    "wb",
                ) as destination,
            ):
                shutil.copyfileobj(
                    source_file,
                    destination,
                )

            source = ZipSource(
                inner_path
            )

            try:
                yield source
            finally:
                source.close()


def create_profiles(all_normal):
    beacons = all_normal[
        all_normal["frame_type"]
        == "beacon"
    ].copy()

    probe_responses = all_normal[
        all_normal["frame_type"]
        == "probe_response"
    ].copy()

    probe_requests = all_normal[
        all_normal["frame_type"]
        == "probe_request"
    ].copy()

    ap_frames = all_normal[
        all_normal["frame_type"].isin(
            [
                "beacon",
                "probe_response",
            ]
        )
    ].copy()

    return (
        beacons,
        probe_responses,
        probe_requests,
        ap_frames,
    )


def validate(
    all_normal,
    beacons,
    probe_responses,
    probe_requests,
):
    if len(all_normal) == 97290:
        # Quantidades documentadas pelo dataset.
        assert len(beacons) == 47676
        assert len(probe_responses) == 47236
        assert len(probe_requests) == 2378

    assert (
        all_normal["label"] == 0
    ).all()

    assert not (
        all_normal["is_synthetic"]
    ).any()

    # Não inferimos BSSID para Probe Requests.
    assert (
        probe_requests["bssid"]
        .isna()
        .all()
    )

    print(
        "Validação Station concluída."
    )
    print(
        f"Frames: {len(all_normal):,}"
    )
    print(
        f"Beacons: {len(beacons):,}"
    )
    print(
        "Probe Responses: "
        f"{len(probe_responses):,}"
    )
    print(
        "Probe Requests: "
        f"{len(probe_requests):,}"
    )


def save_frame(
    df,
    path_without_extension,
    output_format,
):
    if output_format == "csv":
        path = Path(
            f"{path_without_extension}.csv"
        )
        df.to_csv(
            path,
            index=False,
        )
        return path

    path = Path(
        f"{path_without_extension}.parquet"
    )

    try:
        df.to_parquet(
            path,
            index=False,
        )
    except ImportError as error:
        raise RuntimeError(
            "PyArrow não está instalado. "
            "Execute: pip install -r "
            "requirements-ml.txt"
        ) from error

    return path


def normalize_station(
    input_path,
    output_dir,
    output_format="parquet",
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    captures = []

    with open_source(
        input_path
    ) as source:
        source_captures = (
            source.captures()
        )

        if not source_captures:
            raise RuntimeError(
                "Nenhuma captura CSV "
                "foi encontrada."
            )

        for (
            capture_id,
            source_ref,
        ) in source_captures:
            print(
                f"Normalizando {capture_id}..."
            )

            raw = source.read_csv(
                source_ref
            )

            captures.append(
                normalize_capture(
                    raw,
                    capture_id,
                )
            )

    all_normal = pd.concat(
        captures,
        ignore_index=True,
    )

    (
        beacons,
        probe_responses,
        probe_requests,
        ap_frames,
    ) = create_profiles(
        all_normal
    )

    validate(
        all_normal,
        beacons,
        probe_responses,
        probe_requests,
    )

    outputs = {
        "all_normal": save_frame(
            all_normal,
            output_dir
            / "station_all_normal",
            output_format,
        ),
        "beacons": save_frame(
            beacons,
            output_dir
            / "station_beacons",
            output_format,
        ),
        "ap_frames": save_frame(
            ap_frames,
            output_dir
            / "station_ap_frames",
            output_format,
        ),
    }

    summary = {
        "source_dataset":
            SOURCE_DATASET,
        "environment":
            ENVIRONMENT,
        "frames":
            len(all_normal),
        "beacons":
            len(beacons),
        "probe_responses":
            len(probe_responses),
        "probe_requests":
            len(probe_requests),
        "ap_frames":
            len(ap_frames),
        "captures": (
            all_normal[
                "session_id"
            ]
            .value_counts()
            .sort_index()
            .to_dict()
        ),
        "rssi_min_dbm": (
            float(
                all_normal[
                    "rssi_dbm"
                ].min()
            )
        ),
        "rssi_max_dbm": (
            float(
                all_normal[
                    "rssi_dbm"
                ].max()
            )
        ),
    }

    summary_path = (
        output_dir
        / "station_summary.json"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        f"Resumo: {summary_path}"
    )

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--format",
        dest="output_format",
        choices=[
            "parquet",
            "csv",
        ],
        default="parquet",
    )

    args = parser.parse_args()

    normalize_station(
        input_path=args.input,
        output_dir=args.output,
        output_format=(
            args.output_format
        ),
    )


if __name__ == "__main__":
    main()
