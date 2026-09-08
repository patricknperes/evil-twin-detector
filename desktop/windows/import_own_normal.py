from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .runtime_validation import load_scan_jsonl, validate_scans


INTERIM_COLUMNS = [
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
    "label",
    "attack_type",
    "is_synthetic",
]


@dataclass(frozen=True)
class SessionImportResult:
    session_id: str
    rows: int
    scans: int
    runtime_ready: bool
    source_sha256_verified: bool
    output_dir: str

    def as_dict(self):
        return {
            "session_id": self.session_id,
            "rows": self.rows,
            "scans": self.scans,
            "runtime_ready": self.runtime_ready,
            "source_sha256_verified": self.source_sha256_verified,
            "output_dir": self.output_dir,
        }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def validate_source_session(
    session_dir: str | Path,
    *,
    require_runtime_ready: bool = True,
) -> dict:
    session_dir = Path(session_dir)

    scans_path = session_dir / "scans.jsonl"
    manifest_path = session_dir / "manifest.json"
    validation_path = session_dir / "runtime_validation.json"

    missing = [
        path.name
        for path in (
            scans_path,
            manifest_path,
            validation_path,
        )
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            f"{session_dir}: faltando "
            + ", ".join(missing)
        )

    manifest = _read_json(manifest_path)
    stored_validation = _read_json(validation_path)
    scans = load_scan_jsonl(scans_path)

    session_id = str(
        manifest.get(
            "session_id",
            ""
        )
    )

    if not session_id:
        raise ValueError(
            "manifest sem session_id."
        )

    if session_dir.name != session_id:
        raise ValueError(
            "session_id da pasta difere do manifest."
        )

    if int(
        manifest.get(
            "label",
            -1,
        )
    ) != 0:
        raise ValueError(
            "importador aceita somente label=0."
        )

    if bool(
        manifest.get(
            "attack_present",
            True,
        )
    ):
        raise ValueError(
            "attack_present precisa ser false."
        )

    expected_sha = (
        manifest.get(
            "files",
            {}
        )
        .get(
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

    if expected_sha != actual_sha:
        raise ValueError(
            "scans.jsonl falhou na validação SHA-256."
        )

    recalculated = validate_scans(
        scans
    )

    stored_ready = bool(
        stored_validation.get(
            "runtime_ready_for_own_normal_collection",
            False,
        )
    )

    recalculated_ready = bool(
        recalculated.get(
            "runtime_ready_for_own_normal_collection",
            False,
        )
    )

    if stored_ready != recalculated_ready:
        raise ValueError(
            "runtime_validation armazenado diverge da revalidação."
        )

    if int(
        stored_validation.get(
            "observation_count",
            -1,
        )
    ) != int(
        recalculated.get(
            "observation_count",
            -2,
        )
    ):
        raise ValueError(
            "observation_count diverge da revalidação."
        )

    if (
        require_runtime_ready
        and not recalculated_ready
    ):
        raise ValueError(
            "sessão não está runtime-ready."
        )

    return {
        "session_id": session_id,
        "manifest": manifest,
        "scans": scans,
        "validation": recalculated,
        "scans_sha256": actual_sha,
    }


def flatten_session(validated: dict) -> pd.DataFrame:
    session_id = validated[
        "session_id"
    ]

    manifest = validated[
        "manifest"
    ]

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
                        "own_windows",
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
                    "label":
                        0,
                    "attack_type":
                        None,
                    "is_synthetic":
                        False,
                })

    frame = pd.DataFrame(
        rows
    )

    for column in INTERIM_COLUMNS:
        if column not in frame.columns:
            frame[
                column
            ] = pd.NA

    frame = frame[
        INTERIM_COLUMNS
    ]

    if (
        not frame.empty
        and frame[
            "bssid_hash"
        ].isna().any()
    ):
        raise ValueError(
            "observação sem bssid_hash."
        )

    return frame


def import_session(
    session_dir: str | Path,
    output_root: str | Path,
    *,
    require_runtime_ready: bool = True,
) -> SessionImportResult:
    validated = validate_source_session(
        session_dir,
        require_runtime_ready=(
            require_runtime_ready
        ),
    )

    frame = flatten_session(
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

    observations_path = (
        output_dir
        / "observations.csv.gz"
    )

    frame.to_csv(
        observations_path,
        index=False,
        compression="gzip",
    )

    interim_observations_sha256 = (
        sha256_file(
            observations_path
        )
    )

    import_manifest = {
        "schema_version":
            "own_windows_interim_import_v1",
        "session_id":
            session_id,
        "source_dataset":
            "own_windows",
        "source_scans_sha256":
            validated[
                "scans_sha256"
            ],
        "source_sha256_verified":
            True,
        "interim_observations_sha256":
            interim_observations_sha256,
        "runtime_ready":
            validated[
                "validation"
            ][
                "runtime_ready_for_own_normal_collection"
            ],
        "rows":
            int(
                len(
                    frame
                )
            ),
        "scan_count":
            int(
                validated[
                    "validation"
                ][
                    "scan_count"
                ]
            ),
        "label":
            0,
        "attack_present":
            False,
        "identifiers_in_clear_text_in_interim":
            False,
        "grouping_key":
            "session_id",
        "model_ready":
            False,
        "reason_model_not_ready": (
            "Feature engineering requires a frozen normal reference."
        ),
        "columns":
            INTERIM_COLUMNS,
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

    return SessionImportResult(
        session_id=(
            session_id
        ),
        rows=int(
            len(
                frame
            )
        ),
        scans=int(
            import_manifest[
                "scan_count"
            ]
        ),
        runtime_ready=bool(
            import_manifest[
                "runtime_ready"
            ]
        ),
        source_sha256_verified=True,
        output_dir=str(
            output_dir
        ),
    )


def discover_session_dirs(
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


def validate_existing_import(
    session_dir: str | Path,
    output_root: str | Path,
    *,
    require_runtime_ready: bool = True,
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

    validated = validate_source_session(
        session_dir,
        require_runtime_ready=(
            require_runtime_ready
        ),
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
            f"{session_id}: import interim existente está incompleto."
        )

    import_manifest = _read_json(
        import_manifest_path
    )

    if (
        import_manifest.get(
            "source_scans_sha256"
        )
        != validated[
            "scans_sha256"
        ]
    ):
        raise ValueError(
            f"{session_id}: import interim existente pertence a outra fonte/hash."
        )

    actual_interim_sha = sha256_file(
        observations_path
    )

    if (
        import_manifest.get(
            "interim_observations_sha256"
        )
        != actual_interim_sha
    ):
        raise ValueError(
            f"{session_id}: observations.csv.gz existente foi modificado."
        )

    return {
        "session_id":
            session_id,
        "rows":
            int(
                import_manifest.get(
                    "rows",
                    0,
                )
            ),
        "scans":
            int(
                import_manifest.get(
                    "scan_count",
                    0,
                )
            ),
        "runtime_ready":
            bool(
                import_manifest.get(
                    "runtime_ready",
                    False,
                )
            ),
        "source_sha256_verified":
            True,
        "output_dir":
            str(
                output_dir
            ),
        "status":
            "already_imported_verified",
    }


def import_all_sessions(
    raw_root: str | Path,
    output_root: str | Path,
    *,
    require_runtime_ready: bool = True,
) -> dict:
    sessions = discover_session_dirs(
        raw_root
    )

    imported = []
    skipped_existing = []
    rejected = []

    for session_dir in sessions:
        try:
            existing = validate_existing_import(
                session_dir,
                output_root,
                require_runtime_ready=(
                    require_runtime_ready
                ),
            )

            if existing is not None:
                skipped_existing.append(
                    existing
                )
                continue

            result = import_session(
                session_dir,
                output_root,
                require_runtime_ready=(
                    require_runtime_ready
                ),
            )

            imported.append(
                result.as_dict()
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
            "own_windows_import_batch_v1",
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
                item[
                    "rows"
                ]
                for item in [
                    *imported,
                    *skipped_existing,
                ]
            ),
        "real_data_available":
            bool(
                imported
                or skipped_existing
            ),
        "imports":
            imported,
        "skipped_existing":
            skipped_existing,
        "rejections":
            rejected,
    }


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Importa sessões próprias normais do Windows para data/interim."
        )
    )

    parser.add_argument(
        "--raw-root",
        default=(
            "data/raw/own/windows"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "data/interim/own/windows"
        ),
    )

    parser.add_argument(
        "--allow-not-ready",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    result = import_all_sessions(
        args.raw_root,
        args.output_root,
        require_runtime_ready=(
            not args.allow_not_ready
        ),
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        7
        if result[
            "rejected_sessions"
        ]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
