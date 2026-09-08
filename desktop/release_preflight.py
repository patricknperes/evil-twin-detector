from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from backend.packaging.runtime_manifest import (
    RUNTIME_ARTIFACTS,
    inspect_packaging_inputs,
)
from desktop.final_readiness import (
    inspect_final_execution_readiness,
)
from desktop.packaging.preflight import (
    inspect_desktop_packaging,
)


SCHEMA_VERSION = (
    "desktop_release_preflight_step51_v1"
)

RELEASE_INPUT_STAGE_IDS = (
    "implementation_validation",
    "desktop_integration_scenarios",
    "windows_execution_host",
    "windows_normal_collection",
    "scientific_preflight",
    "frozen_split_reference",
    "ml_ready_scaler_lineage",
    "ocsvm_threshold_runtime_chain",
    "controlled_real_attack_data",
    "controlled_attack_features",
    "fixed_artifact_final_evaluation",
    "tcc_final_results_bundle",
    "frontend_source_packaging_contract",
    "frontend_test_typecheck_build",
    "renderer_electron_e2e",
)

POST_BUILD_STAGE_IDS = (
    "backend_pyinstaller",
    "nsis_installer",
)


def sha256_file(
    path: str | Path,
) -> str:
    digest = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as handle:
        for block in iter(
            lambda:
                handle.read(
                    1024
                    * 1024
                ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def _load_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _release_installers(
    root: Path,
    *,
    package_version: str,
) -> list[Path]:
    release = (
        root
        / "frontend"
        / "release"
    )

    if not release.exists():
        return []

    exact_suffix = (
        f"-Setup-{package_version}-x64.exe"
    ).lower()

    return sorted(
        path
        for path
        in release.rglob(
            "*.exe"
        )
        if (
            "setup"
            in path.name.lower()
            and path.name.lower()
            .endswith(
                exact_suffix
            )
        )
    )


def evaluate_release_preflight(
    *,
    readiness: dict[str, Any],
    backend_packaging: dict[str, Any],
    desktop_packaging: dict[str, Any],
    target: str,
    installer_count: int = 0,
) -> dict[str, Any]:
    if target not in {
        "inputs",
        "installer",
        "verify",
    }:
        raise ValueError(
            f"Unknown release target: {target}"
        )

    stage_by_id = {
        stage[
            "id"
        ]:
            stage
        for stage
        in readiness.get(
            "stages",
            []
        )
    }

    required_stage_ids = list(
        RELEASE_INPUT_STAGE_IDS
    )

    if target == "verify":
        required_stage_ids.extend(
            POST_BUILD_STAGE_IDS
        )

    missing_stage_ids = [
        stage_id
        for stage_id
        in required_stage_ids
        if stage_id
        not in stage_by_id
    ]

    not_ready = [
        {
            "id":
                stage_id,
            "status":
                stage_by_id[
                    stage_id
                ][
                    "status"
                ],
        }
        for stage_id
        in required_stage_ids
        if (
            stage_id
            in stage_by_id
            and stage_by_id[
                stage_id
            ][
                "status"
            ]
            != "READY"
        )
    ]

    blockers: list[str] = []

    blockers.extend(
        (
            "missing_readiness_stage:"
            + stage_id
        )
        for stage_id
        in missing_stage_ids
    )

    blockers.extend(
        (
            "readiness_stage_not_ready:"
            + item[
                "id"
            ]
            + ":"
            + str(
                item[
                    "status"
                ]
            )
        )
        for item
        in not_ready
    )

    if (
        backend_packaging.get(
            "static_ready"
        )
        is not True
    ):
        blockers.append(
            "backend_static_packaging_not_ready"
        )

    if (
        backend_packaging.get(
            "scientific_ready"
        )
        is not True
    ):
        blockers.append(
            "backend_scientific_bundle_not_ready"
        )

    if (
        desktop_packaging.get(
            "structural_ready"
        )
        is not True
    ):
        blockers.append(
            "desktop_packaging_structure_not_ready"
        )

    if target in {
        "installer",
        "verify",
    }:
        if (
            desktop_packaging.get(
                "production_ready"
            )
            is not True
        ):
            blockers.append(
                "desktop_packaging_products_not_ready"
            )

    if (
        target
        == "verify"
        and installer_count
        != 1
    ):
        blockers.append(
            "expected_exactly_one_current_installer"
        )

    ready = (
        not blockers
    )

    if ready:
        if target == "inputs":
            status = (
                "READY_FOR_RELEASE_BUILD"
            )

        elif target == "installer":
            status = (
                "READY_FOR_INSTALLER_BUILD"
            )

        else:
            status = (
                "READY_FOR_DISTRIBUTION"
            )

    else:
        status = (
            "BLOCKED_RELEASE_PREFLIGHT"
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "target":
            target,
        "status":
            status,
        "ready":
            ready,
        "required_stage_ids":
            required_stage_ids,
        "missing_stage_ids":
            missing_stage_ids,
        "not_ready_stages":
            not_ready,
        "blockers":
            blockers,
        "backend_packaging": {
            "static_ready":
                backend_packaging.get(
                    "static_ready"
                ),
            "scientific_ready":
                backend_packaging.get(
                    "scientific_ready"
                ),
        },
        "desktop_packaging": {
            "structural_ready":
                desktop_packaging.get(
                    "structural_ready"
                ),
            "production_ready":
                desktop_packaging.get(
                    "production_ready"
                ),
        },
        "installer_count":
            installer_count,
    }


def inspect_release_preflight(
    project_root: str | Path,
    *,
    target: str = "inputs",
    platform_name: str | None = None,
) -> dict[str, Any]:
    root = Path(
        project_root
    ).resolve()

    readiness = (
        inspect_final_execution_readiness(
            root,
            platform_name=(
                platform_name
            ),
        )
    )

    backend_packaging = (
        inspect_packaging_inputs(
            root
        )
    )

    desktop_packaging = (
        inspect_desktop_packaging(
            root,
            require_frontend_dist=True,
            require_backend_exe=(
                target
                in {
                    "installer",
                    "verify",
                }
            ),
        )
    )

    package_path = (
        root
        / "frontend"
        / "package.json"
    )

    package = (
        _load_json(
            package_path
        )
        if package_path.exists()
        else {}
    )

    package_version = str(
        package.get(
            "version",
            "",
        )
    )

    installers = (
        _release_installers(
            root,
            package_version=(
                package_version
            ),
        )
        if (
            target
            == "verify"
            and package_version
        )
        else []
    )

    result = (
        evaluate_release_preflight(
            readiness=(
                readiness
            ),
            backend_packaging=(
                backend_packaging
            ),
            desktop_packaging=(
                desktop_packaging
            ),
            target=(
                target
            ),
            installer_count=(
                len(
                    installers
                )
            ),
        )
    )

    result.update({
        "project_root":
            str(
                root
            ),
        "current_platform":
            (
                platform_name
                or sys.platform
            ),
        "package_version":
            package_version,
        "installer_files": [
            str(
                path.relative_to(
                    root
                )
            )
            for path
            in installers
        ],
        "readiness_overall":
            readiness.get(
                "overall_status"
            ),
    })

    return result


def create_release_manifest(
    project_root: str | Path,
    *,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    if (
        preflight.get(
            "status"
        )
        != "READY_FOR_DISTRIBUTION"
    ):
        raise RuntimeError(
            "Release manifest requires READY_FOR_DISTRIBUTION."
        )

    root = Path(
        project_root
    ).resolve()

    installer_relative = (
        preflight[
            "installer_files"
        ][0]
    )

    installer_path = (
        root
        / installer_relative
    )

    backend_exe = (
        root
        / "frontend"
        / "resources"
        / "backend"
        / "evil-twin-backend.exe"
    )

    dist_index = (
        root
        / "frontend"
        / "dist"
        / "index.html"
    )

    package_path = (
        root
        / "frontend"
        / "package.json"
    )

    final_results_manifest = (
        root
        / "reports"
        / "tcc"
        / "final_results_v1"
        / "reproducibility_manifest.json"
    )

    result_identity = (
        _load_json(
            final_results_manifest
        ).get(
            "scientific_identity"
        )
    )

    scientific_hashes = {
        name:
            sha256_file(
                root
                / relative
            )
        for name, relative
        in RUNTIME_ARTIFACTS.items()
    }

    return {
        "schema_version":
            "desktop_release_manifest_v1",
        "status":
            "verified_release",
        "package_version":
            preflight[
                "package_version"
            ],
        "platform":
            "win32",
        "arch":
            "x64",
        "installer": {
            "path":
                installer_relative,
            "sha256":
                sha256_file(
                    installer_path
                ),
        },
        "backend_executable": {
            "path":
                str(
                    backend_exe
                    .relative_to(
                        root
                    )
                ),
            "sha256":
                sha256_file(
                    backend_exe
                ),
        },
        "frontend_dist": {
            "index_path":
                str(
                    dist_index
                    .relative_to(
                        root
                    )
                ),
            "index_sha256":
                sha256_file(
                    dist_index
                ),
        },
        "package_json_sha256":
            sha256_file(
                package_path
            ),
        "scientific_identity":
            result_identity,
        "scientific_runtime_artifact_sha256":
            scientific_hashes,
        "tcc_results_manifest": {
            "path":
                str(
                    final_results_manifest
                    .relative_to(
                        root
                    )
                ),
            "sha256":
                sha256_file(
                    final_results_manifest
                ),
        },
        "code_signing": {
            "required_for_tcc":
                False,
            "verified":
                False,
        },
    }


def main(
    argv: list[str]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Strict release preflight for the Windows desktop package."
        )
    )

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--target",
        choices=[
            "inputs",
            "installer",
            "verify",
        ],
        default="inputs",
    )

    parser.add_argument(
        "--json-output",
        default=(
            "reports/desktop/"
            "release_preflight_step51.json"
        ),
    )

    parser.add_argument(
        "--release-manifest-output",
        default=(
            "reports/release/"
            "release_manifest_step51.json"
        ),
    )

    args = parser.parse_args(
        argv
    )

    report = (
        inspect_release_preflight(
            args.project_root,
            target=(
                args.target
            ),
        )
    )

    output = Path(
        args.json_output
    )

    if not output.is_absolute():
        output = (
            Path(
                args.project_root
            )
            / output
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        args.target
        == "verify"
        and report[
            "ready"
        ]
    ):
        manifest = (
            create_release_manifest(
                args.project_root,
                preflight=(
                    report
                ),
            )
        )

        manifest_path = Path(
            args.release_manifest_output
        )

        if not manifest_path.is_absolute():
            manifest_path = (
                Path(
                    args.project_root
                )
                / manifest_path
            )

        manifest_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        report[
            "release_manifest"
        ] = str(
            manifest_path
        )

    output.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        0
        if report[
            "ready"
        ]
        else 8
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
