# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_submodules,
)

from backend.packaging.runtime_manifest import (
    REQUIRED_STATIC_RESOURCES,
    RUNTIME_ARTIFACTS,
)


project_root = Path(
    SPECPATH
).resolve().parents[1]

datas = []

for relative in (
    REQUIRED_STATIC_RESOURCES.values()
):
    source = (
        project_root
        / relative
    )

    if source.is_dir():
        datas.append(
            (
                str(source),
                str(relative),
            )
        )
    else:
        datas.append(
            (
                str(source),
                str(relative.parent),
            )
        )

for relative in (
    RUNTIME_ARTIFACTS.values()
):
    source = (
        project_root
        / relative
    )

    if source.exists():
        datas.append(
            (
                str(source),
                str(relative.parent),
            )
        )

hiddenimports = (
    collect_submodules(
        "uvicorn"
    )
    + collect_submodules(
        "sklearn"
    )
)

a = Analysis(
    [
        str(
            project_root
            / "backend"
            / "packaged_entry.py"
        )
    ],
    pathex=[
        str(project_root)
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "torch",
        "pytest",
        "pyarrow",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(
    a.pure
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="evil-twin-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
