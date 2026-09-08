from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from itertools import zip_longest
from pathlib import Path
import argparse
import io
import json
import shutil
import tempfile
import zipfile

import numpy as np
import pandas as pd

from ml.preprocessing.schema import CANONICAL_COLUMNS
from ml.preprocessing.wifi_utils import channel_to_frequency_mhz


SOURCE_DATASET = "zenodo_longterm_wifi"
ENVIRONMENT = "university_building_indoor"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S%f"


class DirectoryAccessor:
    def __init__(self, root: Path):
        self.root = find_dataset_root(root)

    def open_text(self, relative_path: str):
        return open(
            self.root / relative_path,
            "r",
            encoding="utf-8",
            newline="",
        )

    def exists(self, relative_path: str) -> bool:
        return (
            self.root / relative_path
        ).exists()

    def session_names(self, collection: str):
        folder = self.root / "data" / collection

        if not folder.exists():
            return []

        return sorted(
            p.name
            for p in folder.iterdir()
            if p.is_dir()
            and not p.name.startswith(".")
        )


class ZipAccessor:
    def __init__(self, zip_path: Path):
        self.zf = zipfile.ZipFile(
            zip_path,
            "r",
        )
        self.prefix = find_zip_prefix(
            self.zf
        )

    def close(self):
        self.zf.close()

    def _name(self, relative_path):
        return (
            f"{self.prefix}"
            f"{relative_path}"
        )

    def open_text(self, relative_path):
        raw = self.zf.open(
            self._name(relative_path),
            "r",
        )

        return io.TextIOWrapper(
            raw,
            encoding="utf-8",
            newline="",
        )

    def exists(self, relative_path):
        return (
            self._name(relative_path)
            in self.zf.namelist()
        )

    def session_names(self, collection):
        prefix = self._name(
            f"data/{collection}/"
        )

        sessions = set()

        for name in self.zf.namelist():
            if not name.startswith(prefix):
                continue

            rest = name[len(prefix):]

            if "/" not in rest:
                continue

            session = rest.split("/", 1)[0]

            if (
                session
                and not session.startswith(".")
            ):
                sessions.add(session)

        return sorted(sessions)


def find_dataset_root(path: Path):
    path = path.resolve()

    if (
        path / "data" / "site_surveys"
    ).exists():
        return path

    for child in path.iterdir():
        if (
            child.is_dir()
            and (
                child
                / "data"
                / "site_surveys"
            ).exists()
        ):
            return child

    raise FileNotFoundError(
        "Raiz do Long-term dataset "
        "não encontrada."
    )


def find_zip_prefix(zf):
    marker = "data/site_surveys/"

    for name in zf.namelist():
        index = name.find(marker)

        if index >= 0:
            return name[:index]

    raise FileNotFoundError(
        "O ZIP não contém o "
        "Long-term dataset."
    )


def zip_contains_dataset(path):
    with zipfile.ZipFile(
        path,
        "r",
    ) as zf:
        return any(
            "data/site_surveys/"
            in name
            for name in zf.namelist()
        )


@contextmanager
def open_accessor(input_path):
    input_path = Path(
        input_path
    ).resolve()

    if input_path.is_dir():
        yield DirectoryAccessor(
            input_path
        )
        return

    if not zipfile.is_zipfile(
        input_path
    ):
        raise ValueError(
            "A entrada deve ser "
            "diretório ou ZIP."
        )

    if zip_contains_dataset(
        input_path
    ):
        accessor = ZipAccessor(
            input_path
        )

        try:
            yield accessor
        finally:
            accessor.close()

        return

    # Suporta o ZIP externo do Zenodo
    # contendo UM_DSI_DB_v1.0.0_lite.zip.
    with zipfile.ZipFile(
        input_path,
        "r",
    ) as outer:
        candidates = [
            name
            for name in outer.namelist()
            if name.lower().endswith(
                ".zip"
            )
        ]

        if len(candidates) != 1:
            raise FileNotFoundError(
                "ZIP interno do dataset "
                "não identificado."
            )

        with tempfile.TemporaryDirectory(
            prefix="longterm_wifi_"
        ) as temp_dir:
            inner_path = (
                Path(temp_dir)
                / Path(
                    candidates[0]
                ).name
            )

            with (
                outer.open(
                    candidates[0],
                    "r",
                ) as source,
                open(
                    inner_path,
                    "wb",
                ) as destination,
            ):
                shutil.copyfileobj(
                    source,
                    destination,
                )

            accessor = ZipAccessor(
                inner_path
            )

            try:
                yield accessor
            finally:
                accessor.close()


def parse_timestamp(value):
    value = value.strip()

    if not value:
        return pd.NaT

    return pd.Timestamp(
        datetime.strptime(
            value,
            TIMESTAMP_FORMAT,
        )
    )


def parse_coordinates(value):
    parts = [
        item.strip()
        for item
        in value.strip().split(",")
    ]

    x = (
        float(parts[0])
        if len(parts) >= 1
        and parts[0]
        else np.nan
    )

    y = (
        float(parts[1])
        if len(parts) >= 2
        and parts[1]
        else np.nan
    )

    z = (
        float(parts[2])
        if len(parts) >= 3
        and parts[2]
        else np.nan
    )

    return x, y, z


def parse_ap_values(line):
    result = {}

    for token in line.strip().split(","):
        token = token.strip()

        if not token:
            continue

        ap_id, separator, value = (
            token.partition(":")
        )

        if (
            not separator
            or not ap_id
            or not value
        ):
            continue

        try:
            result[ap_id] = int(value)
        except ValueError:
            continue

    return result


def coordinate_key(
    x,
    y,
    z=None,
    include_z=True,
):
    if pd.isna(x) or pd.isna(y):
        return None

    if include_z:
        if pd.isna(z):
            return None

        return (
            round(float(x), 6),
            round(float(y), 6),
            round(float(z), 2),
        )

    return (
        round(float(x), 6),
        round(float(y), 6),
    )


def load_monitoring_device_index(
    accessor,
):
    relative_path = "data/mds_info.csv"

    if not accessor.exists(
        relative_path
    ):
        return {}

    result = {}

    with accessor.open_text(
        relative_path
    ) as file:
        for line in file:
            parts = line.strip().split(",")

            if len(parts) < 4:
                continue

            try:
                key = coordinate_key(
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                    include_z=True,
                )
            except ValueError:
                continue

            result[key] = parts[0]

    return result


def load_reference_point_index(
    accessor,
):
    relative_path = (
        "data/coords_info.csv"
    )

    if not accessor.exists(
        relative_path
    ):
        return {}

    result = {}

    with accessor.open_text(
        relative_path
    ) as file:
        for line in file:
            parts = line.strip().split(",")

            if len(parts) < 3:
                continue

            try:
                key = coordinate_key(
                    float(parts[1]),
                    float(parts[2]),
                    include_z=False,
                )
            except ValueError:
                continue

            result[key] = (
                f"rp_{parts[0]}"
            )

    return result


def empty_row():
    return {
        column: pd.NA
        for column in CANONICAL_COLUMNS
    }


class CsvChunkWriter:
    def __init__(self, output_path):
        self.output_path = output_path
        self.first = True

    def write(self, rows):
        df = pd.DataFrame(
            rows,
            columns=CANONICAL_COLUMNS,
        )

        df.to_csv(
            self.output_path,
            mode=(
                "w"
                if self.first
                else "a"
            ),
            header=self.first,
            index=False,
        )

        self.first = False

    def close(self):
        pass


class ParquetChunkWriter:
    def __init__(self, output_path):
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as error:
            raise RuntimeError(
                "Para gerar Parquet, instale "
                "as dependências com: "
                "pip install -r "
                "requirements-ml.txt"
            ) from error

        self.pa = pa
        self.pq = pq
        self.output_path = output_path
        self.writer = None

    def write(self, rows):
        df = pd.DataFrame(
            rows,
            columns=CANONICAL_COLUMNS,
        )

        table = self.pa.Table.from_pandas(
            df,
            preserve_index=False,
        )

        if self.writer is None:
            self.writer = (
                self.pq.ParquetWriter(
                    self.output_path,
                    table.schema,
                    compression="snappy",
                )
            )
        else:
            table = table.cast(
                self.writer.schema,
                safe=False,
            )

        self.writer.write_table(
            table
        )

    def close(self):
        if self.writer is not None:
            self.writer.close()


def create_writer(
    output_dir,
    output_format,
):
    if output_format == "csv":
        output_path = (
            output_dir
            / "longterm_all_normal.csv"
        )

        return (
            CsvChunkWriter(output_path),
            output_path,
        )

    output_path = (
        output_dir
        / "longterm_all_normal.parquet"
    )

    return (
        ParquetChunkWriter(
            output_path
        ),
        output_path,
    )


def process_session(
    accessor,
    collection,
    session_name,
    writer,
    chunk_size,
    md_index,
    rp_index,
    stats,
):
    base = (
        f"data/{collection}/"
        f"{session_name}"
    )

    files = {
        "timestamps": (
            f"{base}/timestamps.csv"
        ),
        "coordinates": (
            f"{base}/coordinates.csv"
        ),
        "rssis": (
            f"{base}/rssis.csv"
        ),
        "channels": (
            f"{base}/channels.csv"
        ),
    }

    missing = [
        path
        for path in files.values()
        if not accessor.exists(path)
    ]

    if missing:
        raise FileNotFoundError(
            "Arquivos ausentes: "
            + ", ".join(missing)
        )

    collection_mode = (
        "site_survey"
        if collection == "site_surveys"
        else "monitoring_device"
    )

    session_id = (
        f"{collection_mode}_"
        f"{session_name}"
    )

    session_start = None
    buffer = []

    with (
        accessor.open_text(
            files["timestamps"]
        ) as timestamps,
        accessor.open_text(
            files["coordinates"]
        ) as coordinates,
        accessor.open_text(
            files["rssis"]
        ) as rssis,
        accessor.open_text(
            files["channels"]
        ) as channels,
    ):
        rows = zip_longest(
            timestamps,
            coordinates,
            rssis,
            channels,
            fillvalue=None,
        )

        for (
            timestamp_line,
            coordinate_line,
            rssi_line,
            channel_line,
        ) in rows:
            if any(
                value is None
                for value in (
                    timestamp_line,
                    coordinate_line,
                    rssi_line,
                    channel_line,
                )
            ):
                raise ValueError(
                    "Arquivos da sessão possuem "
                    "quantidades de linhas "
                    "diferentes."
                )

            timestamp = parse_timestamp(
                timestamp_line
            )

            x, y, z = parse_coordinates(
                coordinate_line
            )

            if (
                session_start is None
                and not pd.isna(timestamp)
            ):
                session_start = timestamp

            elapsed_ms = (
                (
                    timestamp - session_start
                ).total_seconds()
                * 1000.0
                if (
                    session_start is not None
                    and not pd.isna(
                        timestamp
                    )
                )
                else np.nan
            )

            rssi_values = parse_ap_values(
                rssi_line
            )

            channel_values = (
                parse_ap_values(
                    channel_line
                )
            )

            if (
                collection_mode
                == "monitoring_device"
            ):
                collector_id = (
                    md_index.get(
                        coordinate_key(
                            x,
                            y,
                            z,
                            include_z=True,
                        )
                    )
                )

                location_id = (
                    f"monitor_{collector_id}"
                    if collector_id
                    else None
                )
            else:
                collector_id = None

                location_id = (
                    rp_index.get(
                        coordinate_key(
                            x,
                            y,
                            include_z=False,
                        )
                    )
                )

            stats["samples"] += 1

            if not pd.isna(timestamp):
                timestamp_text = (
                    timestamp.isoformat()
                )

                if (
                    stats["timestamp_min"]
                    is None
                    or timestamp_text
                    < stats["timestamp_min"]
                ):
                    stats["timestamp_min"] = (
                        timestamp_text
                    )

                if (
                    stats["timestamp_max"]
                    is None
                    or timestamp_text
                    > stats["timestamp_max"]
                ):
                    stats["timestamp_max"] = (
                        timestamp_text
                    )

            stats["unique_aps"].update(
                rssi_values.keys()
            )

            for (
                ap_id,
                rssi_dbm,
            ) in rssi_values.items():
                channel = (
                    channel_values.get(
                        ap_id
                    )
                )

                if channel is None:
                    stats[
                        "missing_channel"
                    ] += 1

                row = empty_row()

                row.update({
                    "source_dataset":
                        SOURCE_DATASET,
                    "session_id":
                        session_id,
                    "environment":
                        ENVIRONMENT,

                    "collection_mode":
                        collection_mode,
                    "collector_id":
                        collector_id,
                    "location_id":
                        location_id,
                    "position_x": x,
                    "position_y": y,
                    "position_z": z,

                    "observation_type":
                        "wifi_fingerprint_ap",

                    "timestamp":
                        timestamp,
                    "elapsed_ms":
                        elapsed_ms,

                    "ssid": pd.NA,
                    "bssid": pd.NA,
                    "ap_id": ap_id,

                    "rssi_dbm":
                        rssi_dbm,
                    "rssi_kind":
                        "wifi_scan_ap",
                    "rssi_all_frames_mean_dbm":
                        np.nan,

                    "channel":
                        channel,
                    "advertised_channel":
                        pd.NA,
                    "frequency_mhz":
                        channel_to_frequency_mhz(
                            channel
                        ),
                    "channel_width_mhz":
                        np.nan,
                    "channel_utilization_pct":
                        np.nan,
                    "channel_utilization_estimated":
                        pd.NA,

                    "beacon_interval_raw":
                        np.nan,
                    "beacon_interval_ms":
                        np.nan,
                    "beacon_interval_kind":
                        pd.NA,
                    "beacon_timestamp_us":
                        np.nan,
                    "beacon_count":
                        pd.NA,

                    "security_type":
                        pd.NA,
                    "privacy_enabled":
                        pd.NA,

                    "wifi_standard":
                        pd.NA,
                    "has_ht":
                        pd.NA,

                    "num_clients":
                        pd.NA,

                    "sequence_number":
                        pd.NA,
                    "frame_type":
                        pd.NA,

                    "vendor":
                        pd.NA,
                    "oui":
                        pd.NA,
                    "country_code":
                        pd.NA,

                    "is_hidden":
                        pd.NA,
                    "frame_length_bytes":
                        pd.NA,

                    "label": 0,
                    "attack_type":
                        pd.NA,
                    "is_synthetic":
                        False,
                })

                buffer.append(row)

                stats[
                    "observations"
                ] += 1

                if (
                    len(buffer)
                    >= chunk_size
                ):
                    writer.write(
                        buffer
                    )
                    buffer.clear()

    if buffer:
        writer.write(buffer)

    stats["sessions"] += 1


def normalize_longterm(
    input_path,
    output_dir,
    collection="all",
    chunk_size=100_000,
    output_format="parquet",
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    collections = {
        "all": [
            "site_surveys",
            "mon_devices",
        ],
        "site_surveys": [
            "site_surveys",
        ],
        "mon_devices": [
            "mon_devices",
        ],
    }[collection]

    writer, output_path = (
        create_writer(
            output_dir,
            output_format,
        )
    )

    summary_path = (
        output_dir
        / "longterm_summary.json"
    )

    stats = {
        "source_dataset":
            SOURCE_DATASET,
        "environment":
            ENVIRONMENT,
        "collections":
            collections,
        "sessions": 0,
        "samples": 0,
        "observations": 0,
        "missing_channel": 0,
        "timestamp_min": None,
        "timestamp_max": None,
        "unique_aps": set(),
    }

    try:
        with open_accessor(
            input_path
        ) as accessor:
            md_index = (
                load_monitoring_device_index(
                    accessor
                )
            )

            rp_index = (
                load_reference_point_index(
                    accessor
                )
            )

            for (
                dataset_collection
            ) in collections:
                sessions = (
                    accessor.session_names(
                        dataset_collection
                    )
                )

                if not sessions:
                    raise RuntimeError(
                        "Nenhuma sessão "
                        f"em {dataset_collection}."
                    )

                for session in sessions:
                    print(
                        "Normalizando "
                        f"{dataset_collection}/"
                        f"{session}..."
                    )

                    process_session(
                        accessor=accessor,
                        collection=(
                            dataset_collection
                        ),
                        session_name=session,
                        writer=writer,
                        chunk_size=chunk_size,
                        md_index=md_index,
                        rp_index=rp_index,
                        stats=stats,
                    )
    finally:
        writer.close()

    stats["unique_aps"] = len(
        stats["unique_aps"]
    )

    if stats["observations"] == 0:
        raise RuntimeError(
            "Nenhuma observação gerada."
        )

    with open(
        summary_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            stats,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        "Validação Long-term concluída."
    )
    print(
        f"Sessões: {stats['sessions']:,}"
    )
    print(
        "Amostras Wi-Fi: "
        f"{stats['samples']:,}"
    )
    print(
        "Observações AP: "
        f"{stats['observations']:,}"
    )
    print(
        "APs únicos: "
        f"{stats['unique_aps']:,}"
    )
    print(
        "Sem canal: "
        f"{stats['missing_channel']:,}"
    )
    print(f"Dados: {output_path}")
    print(f"Resumo: {summary_path}")

    return stats


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
        "--collection",
        choices=[
            "all",
            "site_surveys",
            "mon_devices",
        ],
        default="all",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
    )

    parser.add_argument(
        "--format",
        dest="output_format",
        choices=[
            "parquet",
            "csv",
        ],
        default="parquet",
        help=(
            "Parquet é o formato padrão. "
            "CSV é útil para depuração."
        ),
    )

    args = parser.parse_args()

    normalize_longterm(
        input_path=args.input,
        output_dir=args.output,
        collection=args.collection,
        chunk_size=args.chunk_size,
        output_format=(
            args.output_format
        ),
    )


if __name__ == "__main__":
    main()
