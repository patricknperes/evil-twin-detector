from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import io
import json
import tempfile
import zipfile

import pandas as pd


def _open_nested_zip(path: Path):
    """
    Retorna bytes do primeiro ZIP interno quando o arquivo fornecido
    for um pacote externo contendo um único ZIP.
    """
    with zipfile.ZipFile(path, "r") as outer:
        zip_members = [
            name for name in outer.namelist()
            if name.lower().endswith(".zip")
        ]

        if len(zip_members) != 1:
            return None

        return outer.read(zip_members[0])


def analyze_mendeley(path):
    path = Path(path)

    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()

        normal_frames = []
        sessions = {}

        for name in names:
            if (
                "/session_" in name
                and name.lower().endswith(".csv")
            ):
                df = pd.read_csv(
                    archive.open(name)
                )

                session_id = (
                    Path(name).parent.name
                )

                sessions[session_id] = len(df)
                normal_frames.append(df)

        if not normal_frames:
            raise RuntimeError(
                "Sessões Mendeley não encontradas."
            )

        normal = pd.concat(
            normal_frames,
            ignore_index=True,
        )

        rogue_candidates = [
            name for name in names
            if name.endswith(
                "rogue_processed.csv"
            )
        ]

        if not rogue_candidates:
            raise RuntimeError(
                "rogue_processed.csv não encontrado."
            )

        processed = pd.read_csv(
            archive.open(
                rogue_candidates[0]
            )
        )

    is_rogue = pd.to_numeric(
        processed["is_rogue"],
        errors="coerce",
    )

    attacks = processed[
        is_rogue == 1
    ].copy()

    rssi = pd.to_numeric(
        normal["RSSI"],
        errors="coerce",
    )

    channel = pd.to_numeric(
        normal["Channel"],
        errors="coerce",
    )

    beacon = pd.to_numeric(
        normal["BeaconInterval"],
        errors="coerce",
    )

    return {
        "dataset": "mendeley_rogue_ap",
        "normal_rows": int(len(normal)),
        "synthetic_attack_rows": int(
            len(attacks)
        ),
        "sessions": sessions,
        "columns": int(
            len(normal.columns)
        ),
        "unique_bssids": int(
            normal["BSSID"]
            .nunique(dropna=True)
        ),
        "unique_ssids": int(
            normal["SSID"]
            .nunique(dropna=True)
        ),
        "missing_ssid": int(
            normal["SSID"].isna().sum()
        ),
        "rssi_min_dbm": float(
            rssi.min()
        ),
        "rssi_max_dbm": float(
            rssi.max()
        ),
        "channel_min": int(
            channel.min()
        ),
        "channel_max": int(
            channel.max()
        ),
        "beacon_interval_unique": (
            sorted(
                float(v)
                for v in beacon
                .dropna()
                .unique()
            )
        ),
        "attack_types": {
            str(key): int(value)
            for key, value in (
                attacks["_rogue_type"]
                .value_counts()
                .to_dict()
                .items()
            )
        },
        "recommended_role": (
            "principal_normal_training_and_"
            "synthetic_attack_evaluation"
        ),
    }


def _load_v2i_dataframe(path):
    path = Path(path)

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    with zipfile.ZipFile(
        path,
        "r",
    ) as archive:
        candidates = [
            name for name
            in archive.namelist()
            if name.endswith(
                "wifi-exp-log-summary.csv"
            )
        ]

        if not candidates:
            raise RuntimeError(
                "wifi-exp-log-summary.csv "
                "não encontrado."
            )

        return pd.read_csv(
            archive.open(
                candidates[0]
            )
        )


def analyze_v2i(path):
    df = _load_v2i_dataframe(
        path
    )

    beacon_rssi = pd.to_numeric(
        df["meanBeaconRssi"],
        errors="coerce",
    ).mask(
        pd.to_numeric(
            df["meanBeaconRssi"],
            errors="coerce",
        ) == -100
    )

    inter_beacon = pd.to_numeric(
        df["meanInterBeaconTime"],
        errors="coerce",
    ).mask(
        pd.to_numeric(
            df["meanInterBeaconTime"],
            errors="coerce",
        ) == 1.0
    )

    standards = {}

    standard_names = {
        "n": "802.11n",
        "ac": "802.11ac",
        "ad": "802.11ad",
    }

    for raw_name, name in (
        standard_names.items()
    ):
        mask = (
            df["wifiType"]
            == raw_name
        )

        standards[name] = {
            "rows": int(mask.sum()),
            "valid_beacon_rssi": int(
                beacon_rssi[
                    mask
                ].notna().sum()
            ),
            "valid_beacon_interval": int(
                inter_beacon[
                    mask
                ].notna().sum()
            ),
            "valid_both": int(
                (
                    beacon_rssi[
                        mask
                    ].notna()
                    & inter_beacon[
                        mask
                    ].notna()
                ).sum()
            ),
        }

    frequencies = sorted(
        float(value)
        for value in pd.to_numeric(
            df["channelFreq"],
            errors="coerce",
        )
        .dropna()
        .unique()
    )

    client_values = sorted(
        int(value)
        for value in pd.to_numeric(
            df["nrClients"],
            errors="coerce",
        )
        .dropna()
        .unique()
    )

    return {
        "dataset": "zenodo_v2i",
        "rows": int(len(df)),
        "columns": int(
            len(df.columns)
        ),
        "traces": int(
            df["traceNr"]
            .nunique(dropna=True)
        ),
        "standards": standards,
        "frequencies_mhz": frequencies,
        "client_count_values": (
            client_values
        ),
        "beacon_profile_rows": (
            standards["802.11n"][
                "valid_both"
            ]
        ),
        "desktop_aux_rows": int(
            df[
                df["wifiType"].isin(
                    ["n", "ac"]
                )
            ].shape[0]
        ),
        "recommended_role": (
            "normal_training_beacon_profile_"
            "and_desktop_auxiliary"
        ),
    }


def _open_longterm_inner(path):
    path = Path(path)

    if not zipfile.is_zipfile(
        path
    ):
        raise ValueError(
            "Long-term deve ser fornecido "
            "como ZIP."
        )

    with zipfile.ZipFile(
        path,
        "r",
    ) as outer:
        names = outer.namelist()

        if any(
            "data/site_surveys/"
            in name
            for name in names
        ):
            return path.read_bytes()

        nested = [
            name for name in names
            if name.lower().endswith(
                ".zip"
            )
        ]

        if len(nested) != 1:
            raise RuntimeError(
                "ZIP interno Long-term "
                "não identificado."
            )

        return outer.read(
            nested[0]
        )


def _parse_ap_line(line):
    values = {}

    for token in (
        line.decode("utf-8")
        .strip()
        .split(",")
    ):
        if ":" not in token:
            continue

        ap_id, value = (
            token.split(":", 1)
        )

        try:
            values[ap_id] = int(value)
        except ValueError:
            continue

    return values


def analyze_longterm(path):
    inner_bytes = (
        _open_longterm_inner(
            path
        )
    )

    with zipfile.ZipFile(
        io.BytesIO(
            inner_bytes
        ),
        "r",
    ) as archive:
        names = archive.namelist()

        marker_index = None

        for name in names:
            marker = (
                "data/site_surveys/"
            )

            index = name.find(
                marker
            )

            if index >= 0:
                marker_index = index
                break

        if marker_index is None:
            raise RuntimeError(
                "Estrutura Long-term "
                "não encontrada."
            )

        prefix = (
            name[:marker_index]
        )

        collections = {}
        total_samples = 0
        total_observations = 0
        all_aps = set()
        missing_channel = 0

        rssi_min = None
        rssi_max = None
        timestamp_min = None
        timestamp_max = None
        channel_counter = Counter()

        for collection in (
            "site_surveys",
            "mon_devices",
        ):
            base = (
                f"{prefix}data/"
                f"{collection}/"
            )

            sessions = sorted({
                current[
                    len(base):
                ].split(
                    "/", 1
                )[0]
                for current in names
                if current.startswith(
                    base
                )
                and "/" in current[
                    len(base):
                ]
                and current[
                    len(base):
                ].split(
                    "/", 1
                )[0]
            })

            collection_samples = 0
            collection_observations = 0
            collection_aps = set()
            collection_missing = 0

            for session in sessions:
                rssi_path = (
                    f"{base}{session}/"
                    "rssis.csv"
                )
                channel_path = (
                    f"{base}{session}/"
                    "channels.csv"
                )
                timestamp_path = (
                    f"{base}{session}/"
                    "timestamps.csv"
                )

                if not all(
                    item in names
                    for item in (
                        rssi_path,
                        channel_path,
                        timestamp_path,
                    )
                ):
                    continue

                with (
                    archive.open(
                        rssi_path
                    ) as rssis,
                    archive.open(
                        channel_path
                    ) as channels,
                    archive.open(
                        timestamp_path
                    ) as timestamps,
                ):
                    for (
                        rssi_line,
                        channel_line,
                        timestamp_line,
                    ) in zip(
                        rssis,
                        channels,
                        timestamps,
                    ):
                        collection_samples += 1
                        total_samples += 1

                        rssi_values = (
                            _parse_ap_line(
                                rssi_line
                            )
                        )

                        channel_values = (
                            _parse_ap_line(
                                channel_line
                            )
                        )

                        count = len(
                            rssi_values
                        )

                        collection_observations += (
                            count
                        )
                        total_observations += (
                            count
                        )

                        collection_aps.update(
                            rssi_values.keys()
                        )
                        all_aps.update(
                            rssi_values.keys()
                        )

                        for (
                            ap_id,
                            rssi,
                        ) in (
                            rssi_values.items()
                        ):
                            if (
                                rssi_min is None
                                or rssi
                                < rssi_min
                            ):
                                rssi_min = rssi

                            if (
                                rssi_max is None
                                or rssi
                                > rssi_max
                            ):
                                rssi_max = rssi

                            channel = (
                                channel_values.get(
                                    ap_id
                                )
                            )

                            if channel is None:
                                collection_missing += 1
                                missing_channel += 1
                            else:
                                channel_counter[
                                    channel
                                ] += 1

                        timestamp = (
                            timestamp_line
                            .decode("utf-8")
                            .strip()
                        )

                        if timestamp:
                            if (
                                timestamp_min
                                is None
                                or timestamp
                                < timestamp_min
                            ):
                                timestamp_min = (
                                    timestamp
                                )

                            if (
                                timestamp_max
                                is None
                                or timestamp
                                > timestamp_max
                            ):
                                timestamp_max = (
                                    timestamp
                                )

            collections[
                collection
            ] = {
                "sessions": int(
                    len(sessions)
                ),
                "samples": int(
                    collection_samples
                ),
                "flattened_ap_observations":
                    int(
                        collection_observations
                    ),
                "unique_aps": int(
                    len(
                        collection_aps
                    )
                ),
                "missing_channel": int(
                    collection_missing
                ),
            }

    return {
        "dataset":
            "zenodo_longterm_wifi",
        "collections": collections,
        "samples": int(
            total_samples
        ),
        "flattened_ap_observations":
            int(
                total_observations
            ),
        "unique_aps": int(
            len(all_aps)
        ),
        "missing_channel": int(
            missing_channel
        ),
        "rssi_min_dbm": int(
            rssi_min
        ),
        "rssi_max_dbm": int(
            rssi_max
        ),
        "timestamp_min_raw":
            timestamp_min,
        "timestamp_max_raw":
            timestamp_max,
        "most_common_channels": [
            {
                "channel": int(
                    channel
                ),
                "observations": int(
                    count
                ),
            }
            for (
                channel,
                count,
            ) in channel_counter.most_common(
                15
            )
        ],
        "recommended_role": (
            "temporal_rssi_channel_"
            "robustness_evaluation"
        ),
    }


def _load_station_dataframe(path):
    path = Path(path)

    with zipfile.ZipFile(
        path,
        "r",
    ) as outer:
        names = outer.namelist()

        direct_csvs = [
            name for name in names
            if name.lower().endswith(
                ".csv"
            )
        ]

        if direct_csvs:
            frames = [
                pd.read_csv(
                    outer.open(name)
                )
                for name in direct_csvs
            ]

            return pd.concat(
                frames,
                ignore_index=True,
            )

        nested = [
            name for name in names
            if name.lower().endswith(
                ".zip"
            )
        ]

        if len(nested) != 1:
            raise RuntimeError(
                "datasets.zip não "
                "identificado."
            )

        nested_bytes = outer.read(
            nested[0]
        )

    with zipfile.ZipFile(
        io.BytesIO(
            nested_bytes
        ),
        "r",
    ) as inner:
        csvs = [
            name for name
            in inner.namelist()
            if name.lower().endswith(
                ".csv"
            )
        ]

        frames = [
            pd.read_csv(
                inner.open(name)
            )
            for name in csvs
        ]

    return pd.concat(
        frames,
        ignore_index=True,
    )


def analyze_station(path):
    df = _load_station_dataframe(
        path
    )

    types = (
        df["type"]
        .value_counts()
        .to_dict()
    )

    rssi = pd.to_numeric(
        df["rssi"],
        errors="coerce",
    )

    return {
        "dataset":
            "zenodo_station_management_frames",
        "frames": int(
            len(df)
        ),
        "frame_types": {
            str(key): int(value)
            for key, value
            in types.items()
        },
        "beacons": int(
            types.get(
                "Dot11Beacon",
                0,
            )
        ),
        "probe_responses": int(
            types.get(
                "Dot11ProbeResp",
                0,
            )
        ),
        "probe_requests": int(
            types.get(
                "Dot11ProbeReq",
                0,
            )
        ),
        "unique_transmitters": int(
            df["addr2"]
            .nunique(dropna=True)
        ),
        "unique_bssid_field_values": int(
            df["addr3"]
            .nunique(dropna=True)
        ),
        "unique_ssid_values": int(
            df["SSID"]
            .nunique(dropna=True)
        ),
        "rssi_min_dbm": float(
            rssi.min()
        ),
        "rssi_max_dbm": float(
            rssi.max()
        ),
        "recommended_role": (
            "crowded_public_environment_"
            "false_positive_robustness"
        ),
    }


def build_decisions(
    mendeley,
    v2i,
    longterm,
    station,
):
    return {
        "main_normal_training": [
            {
                "source":
                    "mendeley_rogue_ap",
                "profile":
                    "legitimate_real",
                "rows":
                    mendeley[
                        "normal_rows"
                    ],
                "reason":
                    "Base mais alinhada ao problema e com "
                    "RSSI, canal, beacon e segurança.",
            },
            {
                "source":
                    "zenodo_v2i",
                "profile":
                    "802.11n_beacon_profile",
                "rows":
                    v2i[
                        "beacon_profile_rows"
                    ],
                "reason":
                    "Perfil com RSSI de beacon e intervalo "
                    "de beacon simultaneamente válidos.",
            },
        ],
        "robustness_evaluation": [
            {
                "source":
                    "zenodo_longterm_wifi",
                "profile":
                    "temporal_rssi_channel",
                "observations":
                    longterm[
                        "flattened_ap_observations"
                    ],
                "reason":
                    "Grande diversidade temporal de RSSI "
                    "e canais; não possui segurança/beacon.",
            },
            {
                "source":
                    "zenodo_station_management_frames",
                "profile":
                    "beacons_and_ap_frames",
                "frames":
                    station["frames"],
                "reason":
                    "Ambiente público movimentado para "
                    "avaliar falsos positivos.",
            },
        ],
        "attack_evaluation": [
            {
                "source":
                    "mendeley_rogue_ap",
                "profile":
                    "synthetic_rogue",
                "rows":
                    mendeley[
                        "synthetic_attack_rows"
                    ],
                "reason":
                    "Manter fora do treinamento normal e "
                    "usar como teste auxiliar de ataque.",
            }
        ],
        "notes": [
            "Não concatenar todos os datasets indiscriminadamente.",
            "Separar treino/teste por sessão, fonte e ambiente.",
            "Não tratar valores sentinela do V2I como medições reais.",
            "802.11ad permanece auxiliar e não entra inicialmente no modelo desktop.",
            "Long-term deve ser usado por perfis compatíveis, principalmente RSSI/canal.",
            "Station é especialmente útil para medir falsos positivos em ambiente normal movimentado.",
        ],
    }


def render_markdown(report):
    m = report["datasets"][
        "mendeley"
    ]
    v = report["datasets"][
        "v2i"
    ]
    l = report["datasets"][
        "longterm"
    ]
    s = report["datasets"][
        "station"
    ]

    lines = [
        "# Relatório de Qualidade dos Datasets",
        "",
        "Fase 2 — Passo 8",
        "",
        "## Resumo executivo",
        "",
        "| Dataset | Volume validado | Papel recomendado |",
        "|---|---:|---|",
        (
            f"| Mendeley | {m['normal_rows']:,} normais + "
            f"{m['synthetic_attack_rows']:,} ataques sintéticos | "
            "Treino normal principal + teste auxiliar de ataque |"
        ),
        (
            f"| V2I | {v['rows']:,} linhas; "
            f"{v['beacon_profile_rows']:,} no perfil beacon 802.11n | "
            "Treino normal complementar |"
        ),
        (
            f"| Long-term | {l['samples']:,} scans / "
            f"{l['flattened_ap_observations']:,} observações AP | "
            "Robustez temporal RSSI/canal |"
        ),
        (
            f"| Station | {s['frames']:,} frames | "
            "Robustez e falsos positivos em ambiente público |"
        ),
        "",
        "## Mendeley",
        "",
        f"- Registros normais reais: **{m['normal_rows']:,}**.",
        f"- Ataques sintéticos separados: **{m['synthetic_attack_rows']:,}**.",
        f"- BSSIDs únicos nos dados normais: **{m['unique_bssids']:,}**.",
        f"- SSIDs ausentes: **{m['missing_ssid']:,}**.",
        f"- RSSI: **{m['rssi_min_dbm']:.0f} a {m['rssi_max_dbm']:.0f} dBm**.",
        f"- Canais: **{m['channel_min']} a {m['channel_max']}**.",
        (
            "- BeaconInterval normal possui "
            f"**{len(m['beacon_interval_unique'])} valor(es) distinto(s)**: "
            f"`{m['beacon_interval_unique']}`."
        ),
        "",
        "### Ataques sintéticos",
        "",
    ]

    for attack, count in (
        m["attack_types"].items()
    ):
        lines.append(
            f"- `{attack}`: {count:,}"
        )

    lines += [
        "",
        "## Wi-Fi V2I",
        "",
        f"- Total: **{v['rows']:,}** linhas.",
        f"- Traces: **{v['traces']}**.",
        f"- Perfil beacon 802.11n válido: **{v['beacon_profile_rows']:,}**.",
        f"- Perfil desktop auxiliar (n + ac): **{v['desktop_aux_rows']:,}**.",
        f"- Frequências encontradas: `{v['frequencies_mhz']}` MHz.",
        f"- Quantidades de clientes presentes: `{v['client_count_values']}`.",
        "",
        "| Padrão | Total | RSSI beacon válido | Intervalo válido | Ambos válidos |",
        "|---|---:|---:|---:|---:|",
    ]

    for standard, values in (
        v["standards"].items()
    ):
        lines.append(
            f"| {standard} | {values['rows']:,} | "
            f"{values['valid_beacon_rssi']:,} | "
            f"{values['valid_beacon_interval']:,} | "
            f"{values['valid_both']:,} |"
        )

    lines += [
        "",
        "## Continuous Long-term Wi-Fi",
        "",
        f"- Scans/fingerprints: **{l['samples']:,}**.",
        f"- Observações após expansão AP por linha: **{l['flattened_ap_observations']:,}**.",
        f"- APs anonimizados únicos: **{l['unique_aps']:,}**.",
        f"- RSSI: **{l['rssi_min_dbm']} a {l['rssi_max_dbm']} dBm**.",
        f"- Observações sem canal correspondente: **{l['missing_channel']:,}**.",
        f"- Período bruto: `{l['timestamp_min_raw']}` até `{l['timestamp_max_raw']}`.",
        "",
        "| Coleção | Sessões | Scans | Observações AP | APs únicos |",
        "|---|---:|---:|---:|---:|",
    ]

    for collection, values in (
        l["collections"].items()
    ):
        lines.append(
            f"| {collection} | {values['sessions']:,} | "
            f"{values['samples']:,} | "
            f"{values['flattened_ap_observations']:,} | "
            f"{values['unique_aps']:,} |"
        )

    lines += [
        "",
        "## Station / Management Frames",
        "",
        f"- Frames: **{s['frames']:,}**.",
        f"- Beacons: **{s['beacons']:,}**.",
        f"- Probe Responses: **{s['probe_responses']:,}**.",
        f"- Probe Requests: **{s['probe_requests']:,}**.",
        f"- RSSI: **{s['rssi_min_dbm']:.0f} a {s['rssi_max_dbm']:.0f} dBm**.",
        f"- Transmissores anonimizados distintos: **{s['unique_transmitters']:,}**.",
        "",
        "## Decisão para a próxima fase",
        "",
        "### Treino normal principal",
        "",
        "1. Mendeley legítimo real.",
        "2. V2I 802.11n com RSSI de beacon e intervalo de beacon válidos.",
        "3. Futuramente, dados próprios coletados pelo scanner Windows.",
        "",
        "### Robustez / generalização",
        "",
        "1. Long-term: RSSI + canal + variação temporal.",
        "2. Station: ambiente público movimentado e avaliação de falsos positivos.",
        "",
        "### Ataques",
        "",
        "1. Mendeley Rogue sintético fica separado do treino normal.",
        "2. Ataques Evil Twin próprios/controlados terão prioridade na avaliação final.",
        "",
        "## Regras metodológicas",
        "",
        "- Não concatenar as bases cegamente.",
        "- Preservar `source_dataset`, `session_id` e ambiente.",
        "- Separar treino e teste por sessão/fonte/ambiente.",
        "- Não inventar valores para features ausentes.",
        "- Não usar 802.11ad inicialmente no modelo desktop.",
        "- Comparar modelos por perfis de features realmente compatíveis.",
        "",
    ]

    return "\n".join(lines)


def generate_report(
    mendeley_path,
    v2i_path,
    longterm_path,
    station_path,
    output_dir,
):
    output_dir = Path(
        output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Analisando Mendeley...")
    mendeley = analyze_mendeley(
        mendeley_path
    )

    print("Analisando V2I...")
    v2i = analyze_v2i(
        v2i_path
    )

    print(
        "Analisando Long-term "
        "(streaming)..."
    )
    longterm = analyze_longterm(
        longterm_path
    )

    print("Analisando Station...")
    station = analyze_station(
        station_path
    )

    report = {
        "phase": "2",
        "step": "8",
        "datasets": {
            "mendeley": mendeley,
            "v2i": v2i,
            "longterm": longterm,
            "station": station,
        },
    }

    report["decisions"] = (
        build_decisions(
            mendeley,
            v2i,
            longterm,
            station,
        )
    )

    json_path = (
        output_dir
        / "data_quality_report.json"
    )

    md_path = (
        output_dir
        / "data_quality_report.md"
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md_path.write_text(
        render_markdown(
            report
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"JSON: {json_path}"
    )
    print(
        f"Markdown: {md_path}"
    )

    return report


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mendeley",
        required=True,
    )
    parser.add_argument(
        "--v2i",
        required=True,
    )
    parser.add_argument(
        "--longterm",
        required=True,
    )
    parser.add_argument(
        "--station",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    generate_report(
        mendeley_path=args.mendeley,
        v2i_path=args.v2i,
        longterm_path=args.longterm,
        station_path=args.station,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
