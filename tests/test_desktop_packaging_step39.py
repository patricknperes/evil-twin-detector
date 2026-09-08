from __future__ import annotations

import json

from desktop.packaging.preflight import (
    inspect_desktop_packaging,
)


def test_desktop_packaging_structure_is_ready():
    from backend.runtime_paths import (
        resource_root,
    )

    report = (
        inspect_desktop_packaging(
            resource_root(),
            require_frontend_dist=False,
            require_backend_exe=False,
        )
    )

    assert (
        report[
            "structural_ready"
        ]
        is True
    )

    checks = report[
        "checks"
    ]

    assert (
        checks[
            "vite_relative_base"
        ]
        is True
    )

    assert (
        checks[
            "hash_router"
        ]
        is True
    )

    assert (
        checks[
            "nsis_x64_target"
        ]
        is True
    )

    assert (
        checks[
            "backend_extra_resource"
        ]
        is True
    )


def test_production_preflight_blocks_missing_build_products(
    tmp_path,
):
    from backend.runtime_paths import (
        resource_root,
    )

    source_root = resource_root()
    isolated_root = (
        tmp_path
        / "project"
    )

    required_files = [
        "frontend/package.json",
        "frontend/vite.config.ts",
        "frontend/src/App.tsx",
        "frontend/electron/main.cjs",
        "frontend/electron/preload.cjs",
        "frontend/electron/backend-manager.cjs",
    ]

    for relative in required_files:
        source = (
            source_root
            / relative
        )
        destination = (
            isolated_root
            / relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_bytes(
            source.read_bytes()
        )

    report = (
        inspect_desktop_packaging(
            isolated_root
        )
    )

    assert (
        report[
            "checks"
        ][
            "frontend_dist"
        ]
        is False
    )

    assert (
        report[
            "checks"
        ][
            "backend_exe"
        ]
        is False
    )

    assert (
        report[
            "production_ready"
        ]
        is False
    )


def test_nsis_preserves_user_database_on_uninstall():
    from backend.runtime_paths import (
        resource_root,
    )

    package = json.loads(
        (
            resource_root()
            / "frontend"
            / "package.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    nsis = (
        package[
            "build"
        ][
            "nsis"
        ]
    )

    assert (
        nsis[
            "deleteAppDataOnUninstall"
        ]
        is False
    )

    assert (
        nsis[
            "perMachine"
        ]
        is False
    )


def test_backend_is_declared_as_extra_resource():
    from backend.runtime_paths import (
        resource_root,
    )

    package = json.loads(
        (
            resource_root()
            / "frontend"
            / "package.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert {
        "from":
            "resources/backend/evil-twin-backend.exe",
        "to":
            "backend/evil-twin-backend.exe",
    } in (
        package[
            "build"
        ][
            "extraResources"
        ]
    )
