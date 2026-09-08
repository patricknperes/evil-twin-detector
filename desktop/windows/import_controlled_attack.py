from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .runtime_validation import load_scan_jsonl


ATTACK_INTERIM_COLUMNS = [
    "source_dataset",
    "session_id",
    "environment",
    "collection_mode",
    "observation_type",
    "captured_at_utc",
    "scan_index",
    "interface_guid",
    "ssid_hash",
    "bssid_hash",
    "ssid_not_broadcast",
    "rssi_dbm",
    "link_quality",
    "beacon_interval_ms",
    "tsf_us",
    "host_timestamp_100ns",
    "center_frequency_khz",
    "ds_parameter_channel",
    "security_type",
    "security_strength",
    "security_source",
    "ie_blob_size",
    "ie_parser_truncated",
    "phy_id",
    "bss_type",
    "phy_type",
    "in_reg_domain",
    "session_label",
    "label",
    "is_attack_target",
    "attack_type",
    "is_synthetic",
]


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def _read_json(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_attack_source_session(
    session_dir: str | Path,
) -> dict[str, object]:
    session_dir = Path(
        session_dir
    )

    scans_path = (
        session_dir
        / "scans.jsonl"
    )

    manifest_path = (
        session_dir
        / "manifest.json"
    )

    if (
        not scans_path.exists()
        or not manifest_path.exists()
    ):
        raise FileNotFoundError(
            "Sessão de ataque precisa de "
            "scans.jsonl e manifest.json."
        )

    manifest = _read_json(
        manifest_path
    )

    session_id = str(
        manifest.get(
            "session_id",
            "",
        )
    )

    if not session_id:
        raise ValueError(
            "manifest sem session_id."
        )

    if (
        session_dir.name
        != session_id
    ):
        raise ValueError(
            "session_id da pasta difere "
            "do manifest."
        )

    if int(
        manifest.get(
            "label",
            -1,
        )
    ) != 1:
        raise ValueError(
            "sessão de ataque precisa "
            "de label=1."
        )

    if not bool(
        manifest.get(
            "attack_present",
            False,
        )
    ):
        raise ValueError(
            "attack_present precisa "
            "ser true."
        )

    authorization = manifest.get(
        "authorization",
        {},
    )

    if not bool(
        authorization.get(
            "authorized_controlled_experiment",
            False,
        )
    ):
        raise ValueError(
            "sessão sem marcação de experimento "
            "autorizado/controlado."
        )

    attack_type = str(
        manifest.get(
            "attack_type",
            "",
        )
    )

    if not attack_type:
        raise ValueError(
            "attack_type ausente."
        )

    attack_target = manifest.get(
        "attack_target",
        {},
    )

    if not isinstance(
        attack_target,
        dict,
    ):
        raise ValueError(
            "manifest com attack_target inválido."
        )

    if (
        attack_target.get(
            "identifier_type"
        )
        != "bssid_hash"
    ):
        raise ValueError(
            "attack_target.identifier_type "
            "precisa ser bssid_hash."
        )

    target_bssid_hash = attack_target.get(
        "bssid_hash"
    )

    if not target_bssid_hash:
        raise ValueError(
            "manifest sem "
            "attack_target.bssid_hash."
        )

    matched_observation_count = (
        attack_target.get(
            "matched_observation_count"
        )
    )

    if matched_observation_count is None:
        raise ValueError(
            "manifest sem "
            "attack_target."
            "matched_observation_count."
        )

    try:
        matched_observation_count = int(
            matched_observation_count
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "matched_observation_count inválido."
        ) from exc

    if matched_observation_count < 1:
        raise ValueError(
            "matched_observation_count "
            "precisa ser >= 1."
        )

    expected_sha = (
        manifest.get(
            "files",
            {},
        ).get(
            "scans_sha256"
        )
    )

    if not expected_sha:
        raise ValueError(
            "manifest sem scans_sha256."
        )

    actual_sha = sha256_file(
        scans_path
    )

    if (
        actual_sha
        != expected_sha
    ):
        raise ValueError(
            "scans.jsonl falhou na "
            "validação SHA-256."
        )

    scans = load_scan_jsonl(
        scans_path
    )

    return {
        "session_id":
            session_id,
        "manifest":
            manifest,
        "attack_type":
            attack_type,
        "target_bssid_hash":
            str(
                target_bssid_hash
            ),
        "matched_observation_count":
            matched_observation_count,
        "scans":
            scans,
        "scans_sha256":
            actual_sha,
    }


def flatten_attack_session(
    validated: dict[str, object],
) -> pd.DataFrame:
    manifest = validated[
        "manifest"
    ]

    session_id = validated[
        "session_id"
    ]

    attack_type = validated[
        "attack_type"
    ]

    target_bssid_hash = str(
        validated[
            "target_bssid_hash"
        ]
    )

    matched_observation_count = int(
        validated[
            "matched_observation_count"
        ]
    )

    environment = manifest.get(
        "environment",
        "",
    )

    rows = []

    for scan in validated[
        "scans"
    ]:
        scan_index = int(
            scan.get(
                "scan_index",
                -1,
            )
        )

        captured_at_utc = scan.get(
            "captured_at_utc"
        )

        for interface in scan.get(
            "interfaces",
            [],
        ):
            interface_guid = (
                interface.get(
                    "interface",
                    {},
                ).get(
                    "guid"
                )
            )

            for observation in interface.get(
                "bss_entries",
                [],
            ):
                native = observation.get(
                    "native",
                    {},
                )

                rows.append({
                    "source_dataset":
                        "own_windows_attack",
                    "session_id":
                        session_id,
                    "environment":
                        environment,
                    "collection_mode":
                        "windows_native_wifi_scan",
                    "observation_type":
                        "windows_bss_scan",
                    "captured_at_utc":
                        captured_at_utc,
                    "scan_index":
                        scan_index,
                    "interface_guid":
                        interface_guid,
                    "ssid_hash":
                        observation.get(
                            "ssid_hash"
                        ),
                    "bssid_hash":
                        observation.get(
                            "bssid_hash"
                        ),
                    "ssid_not_broadcast":
                        observation.get(
                            "ssid_not_broadcast"
                        ),
                    "rssi_dbm":
                        observation.get(
                            "rssi_dbm"
                        ),
                    "link_quality":
                        observation.get(
                            "link_quality"
                        ),
                    "beacon_interval_ms":
                        observation.get(
                            "beacon_interval_ms"
                        ),
                    "tsf_us":
                        observation.get(
                            "tsf_us"
                        ),
                    "host_timestamp_100ns":
                        observation.get(
                            "host_timestamp_100ns"
                        ),
                    "center_frequency_khz":
                        observation.get(
                            "center_frequency_khz"
                        ),
                    "ds_parameter_channel":
                        observation.get(
                            "ds_parameter_channel"
                        ),
                    "security_type":
                        observation.get(
                            "security_type"
                        ),
                    "security_strength":
                        observation.get(
                            "security_strength"
                        ),
                    "security_source":
                        observation.get(
                            "security_source"
                        ),
                    "ie_blob_size":
                        observation.get(
                            "ie_blob_size"
                        ),
                    "ie_parser_truncated":
                        observation.get(
                            "ie_parser_truncated"
                        ),
                    "phy_id":
                        native.get(
                            "phy_id"
                        ),
                    "bss_type":
                        native.get(
                            "bss_type"
                        ),
                    "phy_type":
                        native.get(
                            "phy_type"
                        ),
                    "in_reg_domain":
                        native.get(
                            "in_reg_domain"
                        ),

                    # Session-level label:
                    # this session contains a controlled attack.
                    "session_label":
                        1,

                    # Observation-level label:
                    # only the identified target AP is attack=1.
                    "label":
                        int(
                            observation.get(
                                "observation_label",
                                -1,
                            )
                        ),

                    "is_attack_target":
                        bool(
                            observation.get(
                                "is_attack_target",
                                False,
                            )
                        ),

                    "attack_type":
                        attack_type,
                    "is_synthetic":
                        False,
                })

    frame = pd.DataFrame(
        rows
    )

    for column in ATTACK_INTERIM_COLUMNS:
        if column not in frame.columns:
            frame[
                column
            ] = pd.NA

    frame = frame[
        ATTACK_INTERIM_COLUMNS
    ]

    if not frame.empty:
        # Old attack sessions without observation_label must not
        # silently become valid evaluation data.
        if not frame[
            "label"
        ].isin(
            [0, 1]
        ).all():
            raise ValueError(
                "observation_label ausente "
                "ou inválido."
            )

        if not (
            frame[
                "session_label"
            ]
            == 1
        ).all():
            raise AssertionError(
                "session_label inconsistente."
            )

        expected_target = (
            frame[
                "is_attack_target"
            ].astype(bool)
        )

        actual_label = (
            frame[
                "label"
            ].astype(int)
        )

        if not (
            actual_label
            == expected_target.astype(int)
        ).all():
            raise AssertionError(
                "label e is_attack_target "
                "inconsistentes."
            )

        if frame[
            "bssid_hash"
        ].isna().any():
            raise ValueError(
                "observação sem bssid_hash."
            )

        attack_rows = frame[
            frame[
                "label"
            ].astype(int)
            == 1
        ]

        if attack_rows.empty:
            raise ValueError(
                "Sessão de ataque sem "
                "observação do BSSID alvo."
            )

        if not (
            attack_rows[
                "bssid_hash"
            ].astype(str)
            == target_bssid_hash
        ).all():
            raise AssertionError(
                "Observação marcada como ataque "
                "não corresponde ao BSSID alvo."
            )

        if (
            len(
                attack_rows
            )
            != matched_observation_count
        ):
            raise AssertionError(
                "Contagem de observações do "
                "BSSID alvo difere do manifest."
            )

        non_attack_rows = frame[
            frame[
                "label"
            ].astype(int)
            == 0
        ]

        if (
            not non_attack_rows.empty
            and (
                non_attack_rows[
                    "bssid_hash"
                ].astype(str)
                == target_bssid_hash
            ).any()
        ):
            raise AssertionError(
                "BSSID alvo encontrado em linha "
                "marcada como normal."
            )

    return frame


def import_attack_session(
    session_dir: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    validated = validate_attack_source_session(
        session_dir
    )

    frame = flatten_attack_session(
        validated
    )

    session_id = validated[
        "session_id"
    ]

    output_dir = (
        Path(
            output_root
        )
        / session_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    frame.to_csv(
        output_dir
        / "observations.csv.gz",
        index=False,
        compression="gzip",
    )

    attack_rows = int(
        (
            frame[
                "label"
            ].astype(int)
            == 1
        ).sum()
    )

    normal_rows = int(
        (
            frame[
                "label"
            ].astype(int)
            == 0
        ).sum()
    )

    import_manifest = {
        "schema_version":
            "own_windows_attack_interim_v2",
        "session_id":
            session_id,
        "source_dataset":
            "own_windows_attack",
        "attack_type":
            validated[
                "attack_type"
            ],
        "source_sha256":
            validated[
                "scans_sha256"
            ],
        "source_sha256_verified":
            True,
        "rows":
            int(
                len(
                    frame
                )
            ),
        # Session-level label.
        "label":
            1,
        "label_semantics":
            "session_contains_controlled_attack",
        "observation_label_semantics":
            (
                "1 only for observations matching "
                "the controlled attack target BSSID; "
                "0 for other observed BSS entries"
            ),
        "attack_present":
            True,
        "attack_target": {
            "identifier_type":
                "bssid_hash",
            "bssid_hash":
                validated[
                    "target_bssid_hash"
                ],
            "matched_observation_count":
                int(
                    validated[
                        "matched_observation_count"
                    ]
                ),
        },
        "observation_counts": {
            "attack":
                attack_rows,
            "normal":
                normal_rows,
        },
        "is_synthetic":
            False,
        "identifiers_in_clear_text_in_interim":
            False,
        "evaluation_only":
            True,
        "forbidden_uses": [
            "normal reference construction",
            "scaler fit",
            "OCSVM fit",
            "threshold calibration",
        ],
    }

    (
        output_dir
        / "import_manifest.json"
    ).write_text(
        json.dumps(
            import_manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "status":
            "ok",
        "session_id":
            session_id,
        "rows":
            int(
                len(
                    frame
                )
            ),
        "attack_rows":
            attack_rows,
        "normal_rows":
            normal_rows,
        "attack_type":
            validated[
                "attack_type"
            ],
        "output_dir":
            str(
                output_dir
            ),
    }


def discover_attack_sessions(
    raw_root: str | Path,
) -> list[Path]:
    root = Path(
        raw_root
    )

    if not root.exists():
        return []

    return sorted(
        path
        for path in root.iterdir()
        if (
            path.is_dir()
            and (
                path
                / "manifest.json"
            ).exists()
        )
    )


def validate_existing_attack_import(
    session_dir: str | Path,
    output_root: str | Path,
) -> dict[str, object] | None:
    session_dir = Path(
        session_dir
    )

    manifest = _read_json(
        session_dir
        / "manifest.json"
    )

    session_id = str(
        manifest.get(
            "session_id",
            "",
        )
    )

    if not session_id:
        return None

    output_dir = (
        Path(
            output_root
        )
        / session_id
    )

    if not output_dir.exists():
        return None

    validated = validate_attack_source_session(
        session_dir
    )

    import_manifest_path = (
        output_dir
        / "import_manifest.json"
    )

    observations_path = (
        output_dir
        / "observations.csv.gz"
    )

    if (
        not import_manifest_path.exists()
        or not observations_path.exists()
    ):
        raise ValueError(
            f"{session_id}: import de ataque "
            "existente está incompleto."
        )

    import_manifest = _read_json(
        import_manifest_path
    )

    if (
        import_manifest.get(
            "schema_version"
        )
        != "own_windows_attack_interim_v2"
    ):
        raise ValueError(
            f"{session_id}: import existente usa "
            "schema antigo/incompatível; "
            "reimporte a sessão."
        )

    if (
        import_manifest.get(
            "source_sha256"
        )
        != validated[
            "scans_sha256"
        ]
    ):
        raise ValueError(
            f"{session_id}: import de ataque "
            "existente pertence a outra "
            "fonte/hash."
        )

    expected_target_hash = str(
        validated[
            "target_bssid_hash"
        ]
    )

    imported_target = (
        import_manifest.get(
            "attack_target",
            {},
        ).get(
            "bssid_hash"
        )
    )

    if (
        imported_target
        != expected_target_hash
    ):
        raise ValueError(
            f"{session_id}: BSSID alvo do import "
            "existente difere da fonte."
        )

    expected_target_count = int(
        validated[
            "matched_observation_count"
        ]
    )

    imported_target_count = int(
        import_manifest.get(
            "attack_target",
            {},
        ).get(
            "matched_observation_count",
            -1,
        )
    )

    if (
        imported_target_count
        != expected_target_count
    ):
        raise ValueError(
            f"{session_id}: contagem do BSSID "
            "alvo do import existente difere "
            "da fonte."
        )

    return {
        "status":
            "already_imported_verified",
        "session_id":
            session_id,
        "rows":
            int(
                import_manifest.get(
                    "rows",
                    0,
                )
            ),
        "attack_rows":
            int(
                import_manifest.get(
                    "observation_counts",
                    {},
                ).get(
                    "attack",
                    0,
                )
            ),
        "normal_rows":
            int(
                import_manifest.get(
                    "observation_counts",
                    {},
                ).get(
                    "normal",
                    0,
                )
            ),
        "attack_type":
            import_manifest.get(
                "attack_type"
            ),
        "output_dir":
            str(
                output_dir
            ),
    }


def import_all_attack_sessions(
    raw_root: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    sessions = discover_attack_sessions(
        raw_root
    )

    imported = []
    skipped_existing = []
    rejected = []

    for session_dir in sessions:
        try:
            existing = validate_existing_attack_import(
                session_dir,
                output_root,
            )

            if existing is not None:
                skipped_existing.append(
                    existing
                )
                continue

            imported.append(
                import_attack_session(
                    session_dir,
                    output_root,
                )
            )

        except Exception as exc:
            rejected.append({
                "session_dir":
                    str(
                        session_dir
                    ),
                "error":
                    str(
                        exc
                    ),
            })

    return {
        "schema_version":
            "own_windows_attack_import_batch_v2",
        "discovered_sessions":
            len(
                sessions
            ),
        "imported_sessions":
            len(
                imported
            ),
        "skipped_existing_sessions":
            len(
                skipped_existing
            ),
        "rejected_sessions":
            len(
                rejected
            ),
        "total_rows":
            sum(
                int(
                    item[
                        "rows"
                    ]
                )
                for item in [
                    *imported,
                    *skipped_existing,
                ]
            ),
        "total_attack_rows":
            sum(
                int(
                    item.get(
                        "attack_rows",
                        0,
                    )
                )
                for item in [
                    *imported,
                    *skipped_existing,
                ]
            ),
        "total_normal_rows":
            sum(
                int(
                    item.get(
                        "normal_rows",
                        0,
                    )
                )
                for item in [
                    *imported,
                    *skipped_existing,
                ]
            ),
        "imports":
            imported,
        "skipped_existing":
            skipped_existing,
        "rejections":
            rejected,
        "real_attack_data_available":
            bool(
                imported
                or skipped_existing
            ),
    }


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Importa sessões defensivas "
            "de ataque controlado para "
            "data/interim."
        )
    )

    parser.add_argument(
        "--raw-root",
        default=(
            "data/raw/own/windows_attack"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/interim/own/windows_attack"
        ),
    )

    args = parser.parse_args(
        argv
    )

    result = import_all_attack_sessions(
        args.raw_root,
        args.output_root,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        11
        if result[
            "rejected_sessions"
        ]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )