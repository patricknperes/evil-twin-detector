from __future__ import annotations

import argparse
import json
from pathlib import Path


def inspect_desktop_packaging(
    project_root:
        str
        | Path,
    *,
    require_frontend_dist:
        bool = True,
    require_backend_exe:
        bool = True,
) -> dict[
    str,
    object,
]:
    root = Path(
        project_root
    ).resolve()

    frontend = (
        root
        / "frontend"
    )

    package_json = (
        frontend
        / "package.json"
    )

    vite_config = (
        frontend
        / "vite.config.ts"
    )

    app_tsx = (
        frontend
        / "src"
        / "App.tsx"
    )

    frontend_dist = (
        frontend
        / "dist"
        / "index.html"
    )

    backend_exe = (
        frontend
        / "resources"
        / "backend"
        / "evil-twin-backend.exe"
    )

    package = (
        json.loads(
            package_json.read_text(
                encoding="utf-8"
            )
        )
        if package_json.exists()
        else {}
    )

    build = package.get(
        "build",
        {}
    )

    extra_resources = (
        build.get(
            "extraResources",
            []
        )
    )

    backend_resource_declared = any(
        isinstance(
            item,
            dict,
        )
        and item.get(
            "from"
        )
        == "resources/backend/evil-twin-backend.exe"
        and item.get(
            "to"
        )
        == "backend/evil-twin-backend.exe"
        for item
        in extra_resources
    )

    vite_text = (
        vite_config.read_text(
            encoding="utf-8"
        )
        if vite_config.exists()
        else ""
    )

    app_text = (
        app_tsx.read_text(
            encoding="utf-8"
        )
        if app_tsx.exists()
        else ""
    )

    win_target = (
        build.get(
            "win",
            {}
        )
        .get(
            "target",
            []
        )
    )

    nsis_declared = any(
        isinstance(
            target,
            dict,
        )
        and target.get(
            "target"
        )
        == "nsis"
        and "x64"
        in target.get(
            "arch",
            []
        )
        for target
        in win_target
    )

    checks = {
        "package_json":
            package_json.exists(),
        "electron_main":
            (
                frontend
                / "electron"
                / "main.cjs"
            ).exists(),
        "electron_preload":
            (
                frontend
                / "electron"
                / "preload.cjs"
            ).exists(),
        "backend_manager":
            (
                frontend
                / "electron"
                / "backend-manager.cjs"
            ).exists(),
        "vite_relative_base":
            'base: "./"'
            in vite_text,
        "hash_router":
            (
                "createHashRouter"
                in app_text
                and "createBrowserRouter"
                not in app_text
            ),
        "electron_builder_config":
            bool(
                build
            ),
        "nsis_x64_target":
            nsis_declared,
        "backend_extra_resource":
            backend_resource_declared,
        "frontend_dist":
            frontend_dist.exists(),
        "backend_exe":
            backend_exe.exists(),
    }

    structural_keys = [
        "package_json",
        "electron_main",
        "electron_preload",
        "backend_manager",
        "vite_relative_base",
        "hash_router",
        "electron_builder_config",
        "nsis_x64_target",
        "backend_extra_resource",
    ]

    structural_ready = all(
        checks[
            key
        ]
        for key
        in structural_keys
    )

    production_ready = (
        structural_ready
        and (
            checks[
                "frontend_dist"
            ]
            or not require_frontend_dist
        )
        and (
            checks[
                "backend_exe"
            ]
            or not require_backend_exe
        )
    )

    return {
        "schema_version":
            "desktop_packaging_preflight_v1",
        "project_root":
            str(
                root
            ),
        "checks":
            checks,
        "structural_ready":
            structural_ready,
        "production_ready":
            production_ready,
        "required_for_installer": {
            "frontend_dist":
                require_frontend_dist,
            "backend_exe":
                require_backend_exe,
        },
    }


def main(
    argv:
        list[str]
        | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--project-root",
        default=".",
    )

    parser.add_argument(
        "--allow-missing-build-products",
        action="store_true",
    )

    parser.add_argument(
        "--json-output",
    )

    args = parser.parse_args(
        argv
    )

    report = (
        inspect_desktop_packaging(
            args.project_root,
            require_frontend_dist=(
                not args
                .allow_missing_build_products
            ),
            require_backend_exe=(
                not args
                .allow_missing_build_products
            ),
        )
    )

    if args.json_output:
        destination = Path(
            args.json_output
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if not report[
        "structural_ready"
    ]:
        return 2

    if not report[
        "production_ready"
    ]:
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
