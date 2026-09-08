from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from backend.packaging.runtime_manifest import (
    inspect_packaging_inputs,
)
from desktop.packaging.preflight import (
    inspect_desktop_packaging,
)
from desktop.implementation_freeze import (
    verify_implementation_snapshot,
)
from desktop.windows.artifact_lineage import (
    sha256_file,
    validate_runtime_artifact_chain,
    validate_scaled_artifact_lineage,
)
from desktop.windows.scientific_preflight import (
    run_scientific_preflight,
    verify_prepared_freeze_integrity,
)
from desktop.windows.generate_final_tcc_results import (
    inspect_generated_final_results,
)
from desktop.windows.train_desktop_ocsvm import (
    check_training_gate,
)


SCHEMA_VERSION = (
    "final_execution_readiness_v1"
)

ALLOWED_STATUSES = {
    "READY",
    "BLOCKED",
    "NOT_EXECUTED",
    "OPTIONAL",
}

REFERENCE_PATH = Path(
    "data/processed/desktop_candidate_v1/"
    "desktop_normal_reference.json"
)

SCALER_PATH = Path(
    "ml/models/preprocessing/"
    "desktop_candidate_v1_standard_scaler.joblib"
)

MODEL_PATH = Path(
    "ml/models/desktop_candidate_v1/ocsvm_v1/"
    "one_class_svm_desktop_candidate_v1.joblib"
)

THRESHOLD_PATH = Path(
    "ml/models/desktop_candidate_v1/ocsvm_v1/"
    "threshold.json"
)

SCALED_ROOT = Path(
    "data/processed/ml_ready/"
    "desktop_candidate_v1_scaled"
)

PREPARED_ROOT = Path(
    "data/processed/desktop_candidate_v1"
)

NORMAL_RAW_ROOT = Path(
    "data/raw/own/windows"
)

NORMAL_INTERIM_ROOT = Path(
    "data/interim/own/windows"
)

ATTACK_RAW_ROOT = Path(
    "data/raw/own/windows_attack"
)

ATTACK_INTERIM_ROOT = Path(
    "data/interim/own/windows_attack"
)

ATTACK_FEATURE_ROOT = Path(
    "data/processed/desktop_candidate_v1_attack"
)

FINAL_EVALUATION_ROOT = Path(
    "reports/desktop/final_evaluation_v1"
)

FRONTEND_ROOT = Path(
    "frontend"
)


def _read_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _relative(
    root: Path,
    path: Path,
) -> str:
    try:
        return str(
            path.resolve()
            .relative_to(
                root.resolve()
            )
        )
    except ValueError:
        return str(
            path
        )


def _stage(
    *,
    stage_id: str,
    category: str,
    title: str,
    status: str,
    implementation_ready: bool,
    blocking: bool,
    depends_on: list[str],
    next_action: str,
    command: str | None = None,
    evidence: dict[str, Any]
    | None = None,
    blockers: list[str]
    | None = None,
) -> dict[str, Any]:
    if (
        status
        not in ALLOWED_STATUSES
    ):
        raise ValueError(
            f"Unknown readiness status: {status}"
        )

    return {
        "id":
            stage_id,
        "category":
            category,
        "title":
            title,
        "status":
            status,
        "implementation_ready":
            implementation_ready,
        "blocking":
            blocking,
        "depends_on":
            depends_on,
        "next_action":
            next_action,
        "command":
            command,
        "blockers":
            blockers
            or [],
        "evidence":
            evidence
            or {},
    }


def _session_directories(
    root: Path,
    *,
    required_files: tuple[
        str,
        ...,
    ],
) -> list[Path]:
    if not root.exists():
        return []

    return sorted(
        folder
        for folder
        in root.iterdir()
        if (
            folder.is_dir()
            and all(
                (
                    folder
                    / filename
                ).exists()
                for filename
                in required_files
            )
        )
    )


def _normal_raw_sessions(
    root: Path,
) -> list[Path]:
    return _session_directories(
        root,
        required_files=(
            "manifest.json",
            "scans.jsonl",
        ),
    )


def _attack_raw_sessions(
    root: Path,
) -> list[Path]:
    return _session_directories(
        root,
        required_files=(
            "manifest.json",
            "scans.jsonl",
        ),
    )


def _attack_interim_sessions(
    root: Path,
) -> list[Path]:
    return _session_directories(
        root,
        required_files=(
            "import_manifest.json",
            "observations.csv.gz",
        ),
    )


def _load_validation_report(
    path: Path,
) -> (
    dict[str, Any]
    | None
):
    if not path.exists():
        return None

    try:
        return _read_json(
            path
        )
    except Exception:
        return None


def _read_final_evaluation(
    path: Path,
) -> (
    dict[str, Any]
    | None
):
    if not path.exists():
        return None

    try:
        payload = _read_json(
            path
        )
    except Exception:
        return None

    if (
        payload.get(
            "schema_version"
        )
        != "desktop_final_evaluation_v2"
    ):
        return None

    if (
        payload.get(
            "status"
        )
        != "executed_fixed_artifacts"
        or payload.get(
            "evaluation_executed"
        )
        is not True
        or payload.get(
            "artifacts_modified"
        )
        is not False
    ):
        return None

    return payload


def _attack_feature_state(
    *,
    project_root: Path,
    runtime_chain: dict[str, Any],
) -> dict[str, Any]:
    root = (
        project_root
        / ATTACK_FEATURE_ROOT
    )

    features_path = (
        root
        / "attack_features_eligible.csv.gz"
    )

    manifest_path = (
        root
        / "manifest.json"
    )

    if (
        not features_path.exists()
        or not manifest_path.exists()
    ):
        return {
            "ready":
                False,
            "status":
                "attack_features_missing",
            "features_exists":
                features_path.exists(),
            "manifest_exists":
                manifest_path.exists(),
        }

    try:
        manifest = _read_json(
            manifest_path
        )
    except Exception:
        return {
            "ready":
                False,
            "status":
                "attack_manifest_invalid",
        }

    if (
        manifest.get(
            "schema_version"
        )
        != "desktop_attack_feature_preparation_v3"
        or manifest.get(
            "status"
        )
        != "attack_features_ready"
        or manifest.get(
            "evaluation_only"
        )
        is not True
        or manifest.get(
            "normal_reference_updated"
        )
        is not False
        or manifest.get(
            "model_updated"
        )
        is not False
        or manifest.get(
            "threshold_updated"
        )
        is not False
    ):
        return {
            "ready":
                False,
            "status":
                "attack_manifest_semantics_invalid",
        }

    if not runtime_chain.get(
        "ready",
        False,
    ):
        return {
            "ready":
                False,
            "status":
                "runtime_chain_not_ready",
        }

    identity = (
        runtime_chain.get(
            "identity"
        )
        or {}
    )

    for field in (
        "split_digest",
        "scientific_freeze_sha256",
        "reference_file_sha256",
    ):
        if (
            manifest.get(
                field
            )
            != identity.get(
                field
            )
        ):
            return {
                "ready":
                    False,
                "status":
                    "attack_reference_identity_mismatch",
                "field":
                    field,
            }

    return {
        "ready":
            True,
        "status":
            "ready",
        "attack_sessions":
            int(
                manifest.get(
                    "attack_sessions",
                    0,
                )
            ),
        "eligible":
            int(
                manifest.get(
                    "eligible",
                    0,
                )
            ),
        "eligible_rate":
            float(
                manifest.get(
                    "eligible_rate",
                    0.0,
                )
            ),
        "manifest_sha256":
            sha256_file(
                manifest_path
            ),
        "features_sha256":
            sha256_file(
                features_path
            ),
    }


def _installer_candidates(
    root: Path,
) -> list[Path]:
    release = (
        root
        / FRONTEND_ROOT
        / "release"
    )

    if not release.exists():
        return []

    return sorted(
        path
        for path
        in release.rglob(
            "*.exe"
        )
        if (
            "setup"
            in path.name.lower()
        )
    )



def _desktop_integration_report(
    path: Path,
) -> (
    dict[str, Any]
    | None
):
    if not path.exists():
        return None

    try:
        payload = _read_json(
            path
        )
    except Exception:
        return None

    if (
        payload.get(
            "schema_version"
        )
        != "desktop_integration_step48_v1"
    ):
        return None

    return payload


def inspect_final_execution_readiness(
    project_root: str | Path,
    *,
    platform_name: str
    | None = None,
    validation_report_path:
        str
        | Path
        | None = None,
) -> dict[str, Any]:
    root = Path(
        project_root
    ).resolve()

    platform_name = (
        platform_name
        or sys.platform
    )

    is_windows = (
        platform_name
        == "win32"
    )

    validation_path = (
        Path(
            validation_report_path
        )
        if validation_report_path
        is not None
        else (
            root
            / "reports"
            / "desktop"
            / "implementation"
            / "implementation_review_step52.json"
        )
    )

    stages: list[
        dict[str, Any]
    ] = []

    # ------------------------------------------------------------
    # A. Implementation validation
    # ------------------------------------------------------------
    validation = (
        _load_validation_report(
            validation_path
        )
    )

    implementation_snapshot = (
        verify_implementation_snapshot(
            root,
            root
            / "reports"
            / "implementation"
            / "implementation_snapshot_step52.json",
        )
        if validation_report_path
        is None
        else {
            "ready":
                True,
            "status":
                "custom_validation_report",
        }
    )

    validation_ready = bool(
        validation
        and validation.get(
            "status"
        )
        == "passed"
        and int(
            validation.get(
                "python_tests_passed",
                0,
            )
        )
        > 0
        and validation.get(
            "typescript_parse"
        )
        == "passed"
        and validation.get(
            "electron_node_syntax"
        )
        == "passed"
        and validation.get(
            "material_ui_present"
        )
        is False
        and implementation_snapshot.get(
            "ready"
        )
        is True
        and (
            validation_report_path
            is not None
            or validation.get(
                "implementation_tree_sha256"
            )
            == implementation_snapshot.get(
                "current_tree_sha256"
            )
        )
    )

    stages.append(
        _stage(
            stage_id=(
                "implementation_validation"
            ),
            category=(
                "implementation"
            ),
            title=(
                "Código e contratos acumulados"
            ),
            status=(
                "READY"
                if validation_ready
                else "NOT_EXECUTED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[],
            next_action=(
                "Nenhuma; validação acumulada registrada."
                if validation_ready
                else (
                    "Executar pytest, parser TS/TSX e checks Node/Electron "
                    "e registrar implementation_review_step52.json com o mesmo digest do snapshot."
                )
            ),
            command=(
                "python -m pytest -q tests"
            ),
            evidence={
                "validation_report":
                    _relative(
                        root,
                        validation_path,
                    ),
                "python_tests_passed":
                    (
                        validation.get(
                            "python_tests_passed"
                        )
                        if validation
                        else None
                    ),
                "python_warnings":
                    (
                        validation.get(
                            "python_warnings"
                        )
                        if validation
                        else None
                    ),
                "implementation_snapshot_status":
                    implementation_snapshot.get(
                        "status"
                    ),
                "implementation_tree_sha256":
                    implementation_snapshot.get(
                        "current_tree_sha256"
                    ),
            },
        )
    )


    # ------------------------------------------------------------
    # B. Deterministic desktop integration scenarios
    # ------------------------------------------------------------
    integration_path = (
        root
        / "reports"
        / "desktop"
        / "desktop_integration_step48.json"
    )

    integration = (
        _desktop_integration_report(
            integration_path
        )
    )

    integration_ready = bool(
        integration
        and integration.get(
            "status"
        )
        == "passed"
        and integration.get(
            "backend",
            {},
        ).get(
            "status"
        )
        == "passed"
        and integration.get(
            "electron_scheduler",
            {},
        ).get(
            "status"
        )
        == "passed"
        and integration.get(
            "real_windows_native_wifi_executed"
        )
        is False
        and integration.get(
            "scientific_artifacts_mutated"
        )
        is False
    )

    stages.append(
        _stage(
            stage_id=(
                "desktop_integration_scenarios"
            ),
            category=(
                "implementation"
            ),
            title=(
                "Integração determinística do desktop"
            ),
            status=(
                "READY"
                if integration_ready
                else "NOT_EXECUTED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "implementation_validation"
            ],
            next_action=(
                "Cenários determinísticos backend/Electron passaram."
                if integration_ready
                else (
                    "Executar python -m desktop.integration.run_step48 "
                    "antes da validação real no Windows."
                )
            ),
            command=(
                "python -m desktop.integration.run_step48"
            ),
            blockers=(
                []
                if integration_ready
                else [
                    "desktop_integration_step48_not_passed"
                ]
            ),
            evidence={
                "report":
                    _relative(
                        root,
                        integration_path,
                    ),
                "backend_status": (
                    integration.get(
                        "backend",
                        {},
                    ).get(
                        "status"
                    )
                    if integration
                    else None
                ),
                "electron_scheduler_status": (
                    integration.get(
                        "electron_scheduler",
                        {},
                    ).get(
                        "status"
                    )
                    if integration
                    else None
                ),
                "real_windows_native_wifi_executed": (
                    integration.get(
                        "real_windows_native_wifi_executed"
                    )
                    if integration
                    else None
                ),
            },
        )
    )

    # ------------------------------------------------------------
    # C. Windows execution host
    # ------------------------------------------------------------
    stages.append(
        _stage(
            stage_id=(
                "windows_execution_host"
            ),
            category=(
                "environment"
            ),
            title=(
                "Host Windows para Native Wi-Fi e build final"
            ),
            status=(
                "READY"
                if is_windows
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "desktop_integration_scenarios"
            ],
            next_action=(
                "Host Windows disponível."
                if is_windows
                else (
                    "Executar a coleta, validação Native Wi-Fi, "
                    "PyInstaller e NSIS em Windows 10/11."
                )
            ),
            evidence={
                "current_platform":
                    platform_name,
                "windows_required":
                    True,
            },
            blockers=(
                []
                if is_windows
                else [
                    "current_host_is_not_windows"
                ]
            ),
        )
    )

    # ------------------------------------------------------------
    # C. Normal collection / scientific preflight
    # ------------------------------------------------------------
    normal_raw = (
        _normal_raw_sessions(
            root
            / NORMAL_RAW_ROOT
        )
    )

    preflight = (
        run_scientific_preflight(
            root
            / NORMAL_INTERIM_ROOT
        )
    )

    valid_sessions = int(
        preflight.get(
            "valid_session_count",
            0,
        )
    )

    normal_collection_ready = (
        len(
            normal_raw
        )
        >= 5
        and valid_sessions
        >= 5
    )

    stages.append(
        _stage(
            stage_id=(
                "windows_normal_collection"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Coleta normal própria no Windows"
            ),
            status=(
                "READY"
                if normal_collection_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "windows_execution_host"
            ],
            next_action=(
                "Sessões próprias suficientes estão disponíveis."
                if normal_collection_ready
                else (
                    "Coletar e importar pelo menos 5 sessões normais "
                    "runtime-ready em ambientes/sessões independentes."
                )
            ),
            command=(
                ".\\scripts\\collect_windows_normal_session.ps1"
            ),
            blockers=(
                []
                if normal_collection_ready
                else [
                    "minimum_five_valid_real_normal_sessions_missing"
                ]
            ),
            evidence={
                "raw_session_count":
                    len(
                        normal_raw
                    ),
                "valid_interim_session_count":
                    valid_sessions,
                "minimum_required":
                    5,
            },
        )
    )

    preflight_ready = (
        preflight.get(
            "status"
        )
        == "ready_for_split_freeze"
    )

    stages.append(
        _stage(
            stage_id=(
                "scientific_preflight"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Pré-flight científico das sessões normais"
            ),
            status=(
                "READY"
                if preflight_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "windows_normal_collection"
            ],
            next_action=(
                "Pré-flight pronto para freeze."
                if preflight_ready
                else (
                    "Resolver os bloqueios do desktop_scientific_preflight_v1 "
                    "antes de criar referência/split."
                )
            ),
            command=(
                "python -m desktop.windows.scientific_preflight"
            ),
            blockers=(
                []
                if preflight_ready
                else [
                    str(
                        preflight.get(
                            "status"
                        )
                    )
                ]
                + list(
                    preflight.get(
                        "global_blockers"
                    )
                    or []
                )
            ),
            evidence={
                "preflight_status":
                    preflight.get(
                        "status"
                    ),
                "valid_sessions":
                    valid_sessions,
                "invalid_sessions":
                    int(
                        preflight.get(
                            "invalid_session_count",
                            0,
                        )
                    ),
                "duplicate_content_groups":
                    len(
                        preflight.get(
                            "duplicate_content_groups"
                        )
                        or []
                    ),
                "temporal_overlap_pairs":
                    len(
                        preflight.get(
                            "temporal_overlap_pairs"
                        )
                        or []
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # D. Freeze / reference integrity
    # ------------------------------------------------------------
    freeze_integrity = (
        verify_prepared_freeze_integrity(
            root
            / PREPARED_ROOT
        )
    )

    freeze_ready = bool(
        freeze_integrity.get(
            "ready"
        )
    )

    stages.append(
        _stage(
            stage_id=(
                "frozen_split_reference"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Split + referência normal congelados"
            ),
            status=(
                "READY"
                if freeze_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "scientific_preflight"
            ],
            next_action=(
                "Freeze científico válido e imutável."
                if freeze_ready
                else (
                    "Executar prepare_desktop_reference depois do "
                    "pré-flight READY; não criar artefatos manualmente."
                )
            ),
            command=(
                "python -m desktop.windows.prepare_desktop_reference"
            ),
            blockers=(
                []
                if freeze_ready
                else [
                    str(
                        freeze_integrity.get(
                            "status"
                        )
                    )
                ]
            ),
            evidence={
                "integrity_status":
                    freeze_integrity.get(
                        "status"
                    ),
                "split_digest":
                    freeze_integrity.get(
                        "split_digest"
                    ),
                "scientific_freeze_sha256":
                    freeze_integrity.get(
                        "scientific_freeze_sha256"
                    ),
                "reference_file_sha256":
                    freeze_integrity.get(
                        "reference_file_sha256"
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # E. ML-ready + scaler lineage
    # ------------------------------------------------------------
    training_gate = (
        check_training_gate(
            root
            / SCALED_ROOT
        )
    )

    scaled_lineage = (
        validate_scaled_artifact_lineage(
            root
            / SCALED_ROOT
        )
    )

    ml_ready = bool(
        training_gate.get(
            "ready"
        )
        and scaled_lineage.get(
            "ready"
        )
    )

    stages.append(
        _stage(
            stage_id=(
                "ml_ready_scaler_lineage"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Matrizes ML-ready + StandardScaler + lineage"
            ),
            status=(
                "READY"
                if ml_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "frozen_split_reference"
            ],
            next_action=(
                "ML-ready e scaler estão ligados ao freeze."
                if ml_ready
                else (
                    "Executar prepare_desktop_ml somente depois do "
                    "freeze íntegro."
                )
            ),
            command=(
                "python -m desktop.windows.prepare_desktop_ml"
            ),
            blockers=(
                []
                if ml_ready
                else sorted({
                    str(
                        training_gate.get(
                            "status"
                        )
                    ),
                    str(
                        scaled_lineage.get(
                            "status"
                        )
                    ),
                })
            ),
            evidence={
                "training_gate":
                    training_gate.get(
                        "status"
                    ),
                "lineage_gate":
                    scaled_lineage.get(
                        "status"
                    ),
            },
        )
    )

    # ------------------------------------------------------------
    # F. OCSVM + threshold runtime chain
    # ------------------------------------------------------------
    runtime_chain = (
        validate_runtime_artifact_chain(
            reference_path=(
                root
                / REFERENCE_PATH
            ),
            scaler_path=(
                root
                / SCALER_PATH
            ),
            model_path=(
                root
                / MODEL_PATH
            ),
            threshold_path=(
                root
                / THRESHOLD_PATH
            ),
        )
    )

    runtime_ready = bool(
        runtime_chain.get(
            "ready"
        )
    )

    stages.append(
        _stage(
            stage_id=(
                "ocsvm_threshold_runtime_chain"
            ),
            category=(
                "scientific"
            ),
            title=(
                "OCSVM + threshold + cadeia dos 4 artefatos"
            ),
            status=(
                "READY"
                if runtime_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "ml_ready_scaler_lineage"
            ],
            next_action=(
                "Bundle científico de produção íntegro."
                if runtime_ready
                else (
                    "Executar train_desktop_ocsvm depois do ML-ready; "
                    "não misturar artefatos de freezes diferentes."
                )
            ),
            command=(
                "python -m desktop.windows.train_desktop_ocsvm"
            ),
            blockers=(
                []
                if runtime_ready
                else [
                    str(
                        runtime_chain.get(
                            "status"
                        )
                    )
                ]
            ),
            evidence={
                "runtime_chain_status":
                    runtime_chain.get(
                        "status"
                    ),
                "missing_artifacts":
                    runtime_chain.get(
                        "missing"
                    )
                    or [],
                "identity":
                    runtime_chain.get(
                        "identity"
                    ),
            },
        )
    )

        # ------------------------------------------------------------
    # G. Exploratory historical attack-context data
    #
    # NOTE:
    # The stage_id is intentionally kept for backwards compatibility
    # with configs, tests and release-preflight contracts.
    # These observations are NOT confirmed Evil Twin ground truth.
    # ------------------------------------------------------------
    attack_raw = (
        _attack_raw_sessions(
            root
            / ATTACK_RAW_ROOT
        )
    )

    attack_interim = (
        _attack_interim_sessions(
            root
            / ATTACK_INTERIM_ROOT
        )
    )

    attack_data_ready = (
        len(
            attack_raw
        )
        > 0
        and len(
            attack_interim
        )
        > 0
    )

    if attack_data_ready:
        attack_status = (
            "READY"
        )
        attack_blockers: list[
            str
        ] = []
        attack_action = (
            "Sessão exploratória histórica em contexto de ataque "
            "está disponível e importada. Ela não constitui "
            "ground truth confirmado de Evil Twin."
        )
    elif len(
        attack_raw
    ) > 0:
        attack_status = (
            "NOT_EXECUTED"
        )
        attack_blockers = [
            "exploratory_context_import_not_executed"
        ]
        attack_action = (
            "Importar a sessão exploratória histórica já coletada. "
            "Não classificá-la como ataque Evil Twin confirmado."
        )
    else:
        attack_status = (
            "NOT_EXECUTED"
        )
        attack_blockers = [
            "exploratory_attack_context_session_not_available"
        ]
        attack_action = (
            "Nenhuma sessão exploratória histórica em contexto de "
            "ataque está disponível. Não é necessário fabricar ou "
            "simular ground truth real para concluir a metodologia."
        )

    stages.append(
        _stage(
            stage_id=(
                "controlled_real_attack_data"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Sessão exploratória em contexto de ataque"
            ),
            status=(
                attack_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "ocsvm_threshold_runtime_chain"
            ],
            next_action=(
                attack_action
            ),
            command=(
                ".\\scripts\\collect_windows_controlled_attack.ps1"
                if not attack_data_ready
                else None
            ),
            blockers=(
                attack_blockers
            ),
            evidence={
                "raw_context_sessions":
                    len(
                        attack_raw
                    ),
                "imported_context_sessions":
                    len(
                        attack_interim
                    ),
                "evaluation_only":
                    True,
                "ground_truth_available":
                    False,
                "confirmed_evil_twin":
                    False,
                "scientific_role":
                    "exploratory_unverified_attack_context",
                "legacy_stage_id":
                    "controlled_real_attack_data",
            },
        )
    )

    # ------------------------------------------------------------
    # H. Exploratory context features bound to frozen reference
    #
    # The internal stage_id remains unchanged for compatibility.
    # These features must not be interpreted as real-attack labels.
    # ------------------------------------------------------------
    attack_features = (
        _attack_feature_state(
            project_root=root,
            runtime_chain=runtime_chain,
        )
    )

    attack_features_ready = bool(
        attack_features.get(
            "ready"
        )
    )

    if attack_features_ready:
        attack_feature_status = (
            "READY"
        )
        attack_feature_blockers = []
        attack_feature_action = (
            "Features da sessão exploratória estão vinculadas "
            "à referência congelada. Elas são utilizadas apenas "
            "como evidência exploratória, sem ground truth de ataque."
        )
    elif attack_data_ready and runtime_ready:
        attack_feature_status = (
            "NOT_EXECUTED"
        )
        attack_feature_blockers = [
            str(
                attack_features.get(
                    "status"
                )
            )
        ]
        attack_feature_action = (
            "Executar prepare_controlled_attack_features para derivar "
            "as features da sessão exploratória, sem tratá-las como "
            "features de ataque confirmado."
        )
    else:
        attack_feature_status = (
            "BLOCKED"
        )
        attack_feature_blockers = [
            str(
                attack_features.get(
                    "status"
                )
            )
        ]
        attack_feature_action = (
            "É necessário ter a cadeia congelada e a sessão "
            "exploratória importada antes de derivar suas features."
        )

    stages.append(
        _stage(
            stage_id=(
                "controlled_attack_features"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Features da sessão exploratória vinculadas ao freeze"
            ),
            status=(
                attack_feature_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "ocsvm_threshold_runtime_chain",
                "controlled_real_attack_data",
            ],
            next_action=(
                attack_feature_action
            ),
            command=(
                "python -m desktop.windows.prepare_controlled_attack_features"
            ),
            blockers=(
                attack_feature_blockers
            ),
            evidence={
                **attack_features,
                "ground_truth_available":
                    False,
                "confirmed_evil_twin":
                    False,
                "scientific_role":
                    "exploratory_feature_coverage",
                "legacy_stage_id":
                    "controlled_attack_features",
            },
        )
    )

    # ------------------------------------------------------------
    # I. Frozen-artifact evaluation source
    #
    # final_evaluation.json is retained as a legacy source artifact.
    # Its real-normal evidence remains useful, but its supervised
    # attack metrics are NOT accepted as final Evil Twin metrics.
    # ------------------------------------------------------------
    final_eval_path = (
        root
        / FINAL_EVALUATION_ROOT
        / "final_evaluation.json"
    )

    final_eval = (
        _read_final_evaluation(
            final_eval_path
        )
    )

    final_eval_ready = (
        final_eval
        is not None
    )

    upstream_final_ready = (
        runtime_ready
        and attack_features_ready
    )

    if final_eval_ready:
        final_eval_status = (
            "READY"
        )
        final_eval_blockers = []
        final_eval_action = (
            "Artefato de avaliação com a cadeia congelada está "
            "disponível. Evidências normais podem ser utilizadas; "
            "métricas supervisionadas de ataque presentes no arquivo "
            "legado não são aceitas como resultados finais."
        )
    elif upstream_final_ready:
        final_eval_status = (
            "NOT_EXECUTED"
        )
        final_eval_blockers = [
            "fixed_artifact_evaluation_source_not_executed"
        ]
        final_eval_action = (
            "Executar a avaliação com os artefatos congelados sem "
            "refit ou recalibração. Qualquer sessão não confirmada "
            "deve permanecer exploratória."
        )
    else:
        final_eval_status = (
            "BLOCKED"
        )
        final_eval_blockers = [
            "fixed_artifact_evaluation_source_prerequisites_missing"
        ]
        final_eval_action = (
            "Concluir a cadeia congelada e, quando utilizada, a "
            "preparação da sessão exploratória antes de produzir "
            "o artefato de avaliação."
        )

    legacy_metrics_present = bool(
        final_eval
        and final_eval.get(
            "metrics"
        )
    )

    test_normal_fpr_present = bool(
        final_eval
        and final_eval.get(
            "test_normal_fpr"
        )
        is not None
    )

    stages.append(
        _stage(
            stage_id=(
                "fixed_artifact_final_evaluation"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Evidências com artefatos científicos congelados"
            ),
            status=(
                final_eval_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "ocsvm_threshold_runtime_chain",
                "controlled_attack_features",
            ],
            next_action=(
                final_eval_action
            ),
            command=(
                "python -m desktop.windows.evaluate_frozen_desktop_model"
            ),
            blockers=(
                final_eval_blockers
            ),
            evidence={
                "report":
                    _relative(
                        root,
                        final_eval_path,
                    ),
                "evaluation_executed":
                    bool(
                        final_eval_ready
                    ),
                "test_normal_fpr_present":
                    test_normal_fpr_present,
                "legacy_supervised_metrics_present_in_source":
                    legacy_metrics_present,
                "legacy_supervised_metrics_accepted_for_final_claims":
                    False,
                "ground_truth_available_for_evil_twin":
                    False,
                "scientific_role":
                    "frozen_artifact_source_for_normal_and_exploratory_evidence",
            },
        )
    )

    # ------------------------------------------------------------
    # J. Final aggregated TCC results bundle
    # ------------------------------------------------------------
    final_results_output = (
        root
        / "reports"
        / "tcc"
        / "final_results_v1"
    )

    final_results_integrity = (
        inspect_generated_final_results(
            project_root=(
                root
            ),
            output_dir=(
                final_results_output
            ),
        )
    )

    final_results_ready = bool(
        final_results_integrity.get(
            "ready"
        )
    )

    if final_results_ready:
        final_results_status = (
            "READY"
        )
        final_results_blockers = []
        final_results_action = (
            "Bundle agregado do TCC já foi gerado e seus hashes são válidos."
        )
    elif final_eval_ready:
        final_results_status = (
            "NOT_EXECUTED"
        )
        final_results_blockers = [
            str(
                final_results_integrity.get(
                    "status"
                )
            )
        ]
        final_results_action = (
            "Executar generate_final_tcc_results sobre a avaliação final "
            "congelada e já executada."
        )
    else:
        final_results_status = (
            "BLOCKED"
        )
        final_results_blockers = [
            "fixed_artifact_final_evaluation_required",
            str(
                final_results_integrity.get(
                    "status"
                )
            ),
        ]
        final_results_action = (
            "Concluir a avaliação final com artefatos fixos antes de gerar "
            "tabelas e gráficos finais do TCC."
        )

    stages.append(
        _stage(
            stage_id=(
                "tcc_final_results_bundle"
            ),
            category=(
                "scientific"
            ),
            title=(
                "Bundle agregado de resultados finais do TCC"
            ),
            status=(
                final_results_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "fixed_artifact_final_evaluation"
            ],
            next_action=(
                final_results_action
            ),
            command=(
                ".\\scripts\\generate_final_tcc_results.ps1"
            ),
            blockers=(
                final_results_blockers
            ),
            evidence={
                "output":
                    _relative(
                        root,
                        final_results_output,
                    ),
                "integrity_status":
                    final_results_integrity.get(
                        "status"
                    ),
                "results_generated":
                    final_results_ready,
                "aggregate_only":
                    True,
            },
        )
    )

    # ------------------------------------------------------------
    # K. Frontend structural / npm validation
    # ------------------------------------------------------------
    desktop_packaging_structure = (
        inspect_desktop_packaging(
            root,
            require_frontend_dist=False,
            require_backend_exe=False,
        )
    )

    frontend_structure_ready = bool(
        desktop_packaging_structure.get(
            "structural_ready"
        )
    )

    stages.append(
        _stage(
            stage_id=(
                "frontend_source_packaging_contract"
            ),
            category=(
                "application"
            ),
            title=(
                "Contrato React/Electron/electron-builder"
            ),
            status=(
                "READY"
                if frontend_structure_ready
                else "BLOCKED"
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "implementation_validation"
            ],
            next_action=(
                "Contrato estrutural do frontend pronto."
                if frontend_structure_ready
                else (
                    "Corrigir o preflight estrutural do desktop "
                    "antes do build frontend."
                )
            ),
            command=(
                "python desktop/packaging/preflight.py "
                "--allow-missing-build-products"
            ),
            blockers=(
                []
                if frontend_structure_ready
                else [
                    "desktop_packaging_structure_invalid"
                ]
            ),
            evidence={
                "checks":
                    desktop_packaging_structure.get(
                        "checks"
                    )
                    or {},
            },
        )
    )

    frontend_validation_report_path = (
        root
        / "reports"
        / "frontend"
        / "frontend_toolchain_step47.json"
    )

    frontend_validation_report = (
        _load_validation_report(
            frontend_validation_report_path
        )
    )

    current_frontend_package_sha = (
        sha256_file(
            root
            / FRONTEND_ROOT
            / "package.json"
        )
        if (
            root
            / FRONTEND_ROOT
            / "package.json"
        ).exists()
        else None
    )

    frontend_dist = (
        root
        / FRONTEND_ROOT
        / "dist"
        / "index.html"
    )

    dependency_resolved_frontend_validated = bool(
        frontend_validation_report
        and frontend_validation_report.get(
            "status"
        ) == "PASSED"
        and frontend_validation_report.get(
            "package_json_sha256"
        ) == current_frontend_package_sha
        and frontend_dist.exists()
    )

    node_available = (
        shutil.which(
            "node"
        )
        is not None
    )

    npm_available = (
        shutil.which(
            "npm"
        )
        is not None
    )

    node_modules = (
        root
        / FRONTEND_ROOT
        / "node_modules"
    )

    npm_inputs_ready = (
        frontend_structure_ready
        and node_available
        and npm_available
    )

    frontend_build_ready = (
        dependency_resolved_frontend_validated
    )

    if frontend_build_ready:
        frontend_validation_status = (
            "READY"
        )
        frontend_blockers = []
        frontend_action = (
            "Frontend production dist já existe."
        )
    elif npm_inputs_ready:
        frontend_validation_status = (
            "NOT_EXECUTED"
        )
        frontend_blockers = [
            "npm_test_typecheck_build_not_executed"
        ]
        frontend_action = (
            "Executar npm install, npm test, npm run typecheck "
            "e npm run build:web."
        )
    else:
        frontend_validation_status = (
            "BLOCKED"
        )
        frontend_blockers = [
            "node_or_npm_or_frontend_structure_missing"
        ]
        frontend_action = (
            "Disponibilizar Node/npm e corrigir o contrato estrutural."
        )

    stages.append(
        _stage(
            stage_id=(
                "frontend_test_typecheck_build"
            ),
            category=(
                "application"
            ),
            title=(
                "Frontend: npm test + typecheck + Vite build"
            ),
            status=(
                frontend_validation_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "frontend_source_packaging_contract"
            ],
            next_action=(
                frontend_action
            ),
            command=(
                "cd frontend; npm install; npm test; "
                "npm run typecheck; npm run build:web"
            ),
            blockers=(
                frontend_blockers
            ),
            evidence={
                "node_available":
                    node_available,
                "npm_available":
                    npm_available,
                "node_modules_exists":
                    node_modules.exists(),
                "frontend_dist_exists":
                    frontend_dist.exists(),
                "dependency_resolved_validation_report":
                    _relative(
                        root,
                        frontend_validation_report_path,
                    ),
                "dependency_resolved_validation_status":
                    (
                        frontend_validation_report.get(
                            "status"
                        )
                        if frontend_validation_report
                        else None
                    ),
                "validation_matches_current_package":
                    dependency_resolved_frontend_validated,
            },
        )
    )

    # ------------------------------------------------------------
    # K. Renderer / Electron E2E
    # ------------------------------------------------------------
    renderer_e2e_report_path = (
        root
        / "reports"
        / "frontend"
        / "renderer_e2e_step49.json"
    )

    renderer_e2e_report = (
        _load_validation_report(
            renderer_e2e_report_path
        )
    )

    renderer_e2e_validated = bool(
        renderer_e2e_report
        and renderer_e2e_report.get(
            "status"
        )
        == "PASSED"
        and renderer_e2e_report.get(
            "executed"
        )
        is True
        and renderer_e2e_report.get(
            "passed"
        )
        is True
        and renderer_e2e_report.get(
            "package_json_sha256"
        )
        == current_frontend_package_sha
    )

    if renderer_e2e_validated:
        renderer_e2e_status = (
            "READY"
        )
        renderer_e2e_blockers = []
        renderer_e2e_action = (
            "Playwright/Electron E2E executado contra a versão atual do frontend."
        )
    elif (
        frontend_validation_status
        == "READY"
    ):
        renderer_e2e_status = (
            "NOT_EXECUTED"
        )
        renderer_e2e_blockers = [
            "renderer_electron_e2e_not_executed"
        ]
        renderer_e2e_action = (
            "Executar scripts/validate_renderer_e2e.ps1 "
            "ou npm run e2e."
        )
    else:
        renderer_e2e_status = (
            "BLOCKED"
        )
        renderer_e2e_blockers = [
            "dependency_resolved_frontend_validation_required"
        ]

        if renderer_e2e_report:
            renderer_e2e_blockers.append(
                str(
                    renderer_e2e_report.get(
                        "status"
                    )
                )
            )

        renderer_e2e_action = (
            "Concluir npm install + Vitest + typecheck + Vite build; "
            "depois executar o Playwright/Electron E2E."
        )

    stages.append(
        _stage(
            stage_id=(
                "renderer_electron_e2e"
            ),
            category=(
                "application"
            ),
            title=(
                "Renderer/Electron E2E com backend determinístico"
            ),
            status=(
                renderer_e2e_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "frontend_test_typecheck_build"
            ],
            next_action=(
                renderer_e2e_action
            ),
            command=(
                ".\\scripts\\validate_renderer_e2e.ps1"
            ),
            blockers=(
                renderer_e2e_blockers
            ),
            evidence={
                "report":
                    _relative(
                        root,
                        renderer_e2e_report_path,
                    ),
                "report_status": (
                    renderer_e2e_report.get(
                        "status"
                    )
                    if renderer_e2e_report
                    else None
                ),
                "executed": (
                    renderer_e2e_report.get(
                        "executed"
                    )
                    if renderer_e2e_report
                    else False
                ),
                "passed": (
                    renderer_e2e_report.get(
                        "passed"
                    )
                    if renderer_e2e_report
                    else False
                ),
                "matches_current_package":
                    renderer_e2e_validated,
                "real_native_wifi":
                    False,
                "real_scientific_artifacts":
                    False,
            },
        )
    )

    # ------------------------------------------------------------
    # L. Backend PyInstaller
    # ------------------------------------------------------------
    backend_packaging = (
        inspect_packaging_inputs(
            root
        )
    )

    pyinstaller_available = (
        importlib.util.find_spec(
            "PyInstaller"
        )
        is not None
    )

    backend_exe = (
        root
        / FRONTEND_ROOT
        / "resources"
        / "backend"
        / "evil-twin-backend.exe"
    )

    backend_build_prereqs = (
        is_windows
        and backend_packaging.get(
            "static_ready"
        )
        is True
        and backend_packaging.get(
            "scientific_ready"
        )
        is True
    )

    if backend_exe.exists():
        pyinstaller_status = (
            "READY"
        )
        pyinstaller_blockers = []
        pyinstaller_action = (
            "Backend PyInstaller já está materializado para o Electron."
        )
    elif backend_build_prereqs:
        pyinstaller_status = (
            "NOT_EXECUTED"
        )
        pyinstaller_blockers = [
            "pyinstaller_build_not_executed"
        ]
        pyinstaller_action = (
            "Executar build_backend_windows.ps1."
        )
    else:
        pyinstaller_status = (
            "BLOCKED"
        )
        pyinstaller_blockers = []

        if not is_windows:
            pyinstaller_blockers.append(
                "windows_host_required"
            )

        if not backend_packaging.get(
            "static_ready"
        ):
            pyinstaller_blockers.append(
                "backend_static_resources_missing"
            )

        if not backend_packaging.get(
            "scientific_ready"
        ):
            pyinstaller_blockers.append(
                "real_scientific_runtime_bundle_missing"
            )

        pyinstaller_action = (
            "Concluir o bundle científico real e executar o build em Windows."
        )

    stages.append(
        _stage(
            stage_id=(
                "backend_pyinstaller"
            ),
            category=(
                "packaging"
            ),
            title=(
                "Backend PyInstaller para produção"
            ),
            status=(
                pyinstaller_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "ocsvm_threshold_runtime_chain",
                "windows_execution_host",
                "renderer_electron_e2e",
            ],
            next_action=(
                pyinstaller_action
            ),
            command=(
                ".\\scripts\\build_backend_windows.ps1"
            ),
            blockers=(
                pyinstaller_blockers
            ),
            evidence={
                "static_ready":
                    backend_packaging.get(
                        "static_ready"
                    ),
                "scientific_ready":
                    backend_packaging.get(
                        "scientific_ready"
                    ),
                "pyinstaller_installed_on_current_host":
                    pyinstaller_available,
                "backend_exe_exists":
                    backend_exe.exists(),
            },
        )
    )

    # ------------------------------------------------------------
    # L. NSIS installer
    # ------------------------------------------------------------
    strict_packaging = (
        inspect_desktop_packaging(
            root
        )
    )

    installers = (
        _installer_candidates(
            root
        )
    )

    if installers:
        nsis_status = (
            "READY"
        )
        nsis_blockers = []
        nsis_action = (
            "Instalador NSIS materializado."
        )
    elif (
        is_windows
        and strict_packaging.get(
            "production_ready"
        )
    ):
        nsis_status = (
            "NOT_EXECUTED"
        )
        nsis_blockers = [
            "electron_builder_nsis_not_executed"
        ]
        nsis_action = (
            "Executar build_desktop_installer_windows.ps1."
        )
    else:
        nsis_status = (
            "BLOCKED"
        )
        nsis_blockers = []

        if not is_windows:
            nsis_blockers.append(
                "windows_host_required"
            )

        checks = (
            strict_packaging.get(
                "checks"
            )
            or {}
        )

        if not checks.get(
            "frontend_dist"
        ):
            nsis_blockers.append(
                "frontend_dist_missing"
            )

        if not checks.get(
            "backend_exe"
        ):
            nsis_blockers.append(
                "backend_exe_missing"
            )

        nsis_action = (
            "Concluir frontend dist e backend .exe; então executar "
            "o electron-builder/NSIS em Windows."
        )

    stages.append(
        _stage(
            stage_id=(
                "nsis_installer"
            ),
            category=(
                "packaging"
            ),
            title=(
                "Instalador Windows NSIS"
            ),
            status=(
                nsis_status
            ),
            implementation_ready=True,
            blocking=True,
            depends_on=[
                "frontend_test_typecheck_build",
                "backend_pyinstaller",
            ],
            next_action=(
                nsis_action
            ),
            command=(
                ".\\scripts\\build_desktop_installer_windows.ps1"
            ),
            blockers=(
                nsis_blockers
            ),
            evidence={
                "production_packaging_ready":
                    strict_packaging.get(
                        "production_ready"
                    ),
                "installer_count":
                    len(
                        installers
                    ),
                "installer_files": [
                    _relative(
                        root,
                        path,
                    )
                    for path
                    in installers
                ],
            },
        )
    )

    # ------------------------------------------------------------
    # M. Optional code signing
    # ------------------------------------------------------------
    stages.append(
        _stage(
            stage_id=(
                "windows_code_signing"
            ),
            category=(
                "packaging"
            ),
            title=(
                "Assinatura de código Windows"
            ),
            status=(
                "OPTIONAL"
            ),
            implementation_ready=True,
            blocking=False,
            depends_on=[
                "nsis_installer"
            ],
            next_action=(
                "Configurar certificado apenas se houver um certificado "
                "real para distribuição; não é requisito da validação científica."
            ),
            evidence={
                "configured":
                    False,
                "required_for_scientific_tcc_run":
                    False,
            },
        )
    )

    # ------------------------------------------------------------
    # Summary / dependency truth
    # ------------------------------------------------------------
    stage_by_id = {
        stage[
            "id"
        ]:
            stage
        for stage
        in stages
    }

    for stage in stages:
        dependencies_not_ready = [
            dependency
            for dependency
            in stage[
                "depends_on"
            ]
            if (
                stage_by_id[
                    dependency
                ][
                    "status"
                ]
                != "READY"
            )
        ]

        stage[
            "dependencies_not_ready"
        ] = (
            dependencies_not_ready
        )

    mandatory = [
        stage
        for stage
        in stages
        if stage[
            "blocking"
        ]
    ]

    blocking = [
        stage[
            "id"
        ]
        for stage
        in mandatory
        if stage[
            "status"
        ]
        == "BLOCKED"
    ]

    not_executed = [
        stage[
            "id"
        ]
        for stage
        in mandatory
        if stage[
            "status"
        ]
        == "NOT_EXECUTED"
    ]

    ready = [
        stage[
            "id"
        ]
        for stage
        in stages
        if stage[
            "status"
        ]
        == "READY"
    ]

    first_incomplete = next(
        (
            stage
            for stage
            in mandatory
            if stage[
                "status"
            ]
            != "READY"
        ),
        None,
    )

    final_complete = all(
        stage[
            "status"
        ]
        == "READY"
        for stage
        in mandatory
    )

    if final_complete:
        overall_status = (
            "COMPLETE"
        )
    elif blocking:
        overall_status = (
            "BLOCKED"
        )
    else:
        overall_status = (
            "READY_TO_EXECUTE_REMAINING_STEPS"
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "overall_status":
            overall_status,
        "final_pipeline_complete":
            final_complete,
        "current_platform":
            platform_name,
        "ready_stage_count":
            len(
                ready
            ),
        "mandatory_stage_count":
            len(
                mandatory
            ),
        "blocking_stage_ids":
            blocking,
        "not_executed_stage_ids":
            not_executed,
        "first_incomplete_stage": (
            {
                "id":
                    first_incomplete[
                        "id"
                    ],
                "title":
                    first_incomplete[
                        "title"
                    ],
                "status":
                    first_incomplete[
                        "status"
                    ],
                "next_action":
                    first_incomplete[
                        "next_action"
                    ],
            }
            if first_incomplete
            else None
        ),
        "scientific_execution_policy": {
            "real_data_only":
                True,
            "synthetic_attack_for_final_metrics":
                False,
            "attack_for_calibration":
                False,
            "fixed_artifact_final_evaluation":
                True,
            "no_silent_refit":
                True,
        },
        "stages":
            stages,
    }


def readiness_markdown(
    report: dict[
        str,
        Any,
    ],
) -> str:
    lines = [
        "# Final execution readiness",
        "",
        f"Overall: **{report['overall_status']}**",
        "",
        "| # | Etapa | Categoria | Estado | Próxima ação |",
        "|---:|---|---|---|---|",
    ]

    for index, stage in enumerate(
        report[
            "stages"
        ],
        start=1,
    ):
        action = str(
            stage[
                "next_action"
            ]
        ).replace(
            "|",
            "\\|",
        )

        lines.append(
            "| "
            + str(
                index
            )
            + " | "
            + str(
                stage[
                    "title"
                ]
            )
            + " | "
            + str(
                stage[
                    "category"
                ]
            )
            + " | **"
            + str(
                stage[
                    "status"
                ]
            )
            + "** | "
            + action
            + " |"
        )

    lines.extend([
        "",
        "## Bloqueios",
        "",
    ])

    if report[
        "blocking_stage_ids"
    ]:
        for stage_id in (
            report[
                "blocking_stage_ids"
            ]
        ):
            stage = next(
                item
                for item
                in report[
                    "stages"
                ]
                if item[
                    "id"
                ]
                == stage_id
            )

            lines.append(
                "- `"
                + stage_id
                + "`: "
                + ", ".join(
                    stage[
                        "blockers"
                    ]
                    or [
                        "prerequisite_not_ready"
                    ]
                )
            )
    else:
        lines.append(
            "- Nenhum."
        )

    lines.extend([
        "",
        "## Primeira ação",
        "",
    ])

    first = report.get(
        "first_incomplete_stage"
    )

    if first:
        lines.append(
            "**"
            + str(
                first[
                    "title"
                ]
            )
            + "** — "
            + str(
                first[
                    "next_action"
                ]
            )
        )
    else:
        lines.append(
            "Pipeline final completa."
        )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def save_readiness(
    report: dict[
        str,
        Any,
    ],
    *,
    json_path: str
    | Path,
    markdown_path: str
    | Path
    | None = None,
) -> None:
    json_path = Path(
        json_path
    )

    json_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    if markdown_path is not None:
        markdown_path = Path(
            markdown_path
        )

        markdown_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        markdown_path.write_text(
            readiness_markdown(
                report
            ),
            encoding="utf-8",
        )


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lista todos os gates científicos, de aplicação e de "
            "empacotamento antes da execução final do TCC."
        )
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--json-output",
        default=(
            "reports/desktop/"
            "final_execution_readiness_step46.json"
        ),
    )

    parser.add_argument(
        "--markdown-output",
        default=(
            "reports/desktop/"
            "final_execution_readiness_step46.md"
        ),
    )

    args = parser.parse_args(
        argv
    )

    report = (
        inspect_final_execution_readiness(
            args.project_root
        )
    )

    save_readiness(
        report,
        json_path=(
            args.json_output
        ),
        markdown_path=(
            args.markdown_output
        ),
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if report[
        "final_pipeline_complete"
    ]:
        return 0

    if report[
        "blocking_stage_ids"
    ]:
        return 8

    return 9


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
