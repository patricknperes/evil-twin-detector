from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "EvilTwinDetector"


def is_frozen() -> bool:
    return bool(
        getattr(
            sys,
            "frozen",
            False,
        )
    )


def resource_root() -> Path:
    """
    Read-only resource root.

    Development:
        repository root

    PyInstaller:
        temporary extraction root (sys._MEIPASS)
    """
    override = os.environ.get(
        "EVIL_TWIN_RESOURCE_ROOT"
    )

    if override:
        return Path(
            override
        ).expanduser().resolve()

    frozen_root = getattr(
        sys,
        "_MEIPASS",
        None,
    )

    if frozen_root:
        return Path(
            frozen_root
        ).resolve()

    return Path(
        __file__
    ).resolve().parents[1]


def user_data_root() -> Path:
    """
    Writable application data directory.
    """
    override = os.environ.get(
        "EVIL_TWIN_APP_DATA_DIR"
    )

    if override:
        root = Path(
            override
        ).expanduser()

    elif sys.platform == "win32":
        local_app_data = (
            os.environ.get(
                "LOCALAPPDATA"
            )
            or os.environ.get(
                "APPDATA"
            )
        )

        if local_app_data:
            root = (
                Path(
                    local_app_data
                )
                / APP_DIR_NAME
            )
        else:
            root = (
                Path.home()
                / "AppData"
                / "Local"
                / APP_DIR_NAME
            )

    elif sys.platform == "darwin":
        root = (
            Path.home()
            / "Library"
            / "Application Support"
            / APP_DIR_NAME
        )

    else:
        xdg = os.environ.get(
            "XDG_DATA_HOME"
        )

        root = (
            Path(
                xdg
            )
            / APP_DIR_NAME
            if xdg
            else (
                Path.home()
                / ".local"
                / "share"
                / APP_DIR_NAME
            )
        )

    root = root.resolve()

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return root


def database_path() -> Path:
    return (
        user_data_root()
        / "evil_twin_detector.db"
    )


def alembic_ini_path() -> Path:
    return (
        resource_root()
        / "alembic.ini"
    )


def migrations_path() -> Path:
    return (
        resource_root()
        / "backend"
        / "migrations"
    )


def runtime_artifact_paths() -> dict[str, Path]:
    root = resource_root()

    return {
        "reference": (
            root
            / "data"
            / "processed"
            / "desktop_candidate_v1"
            / "desktop_normal_reference.json"
        ),
        "scaler": (
            root
            / "ml"
            / "models"
            / "preprocessing"
            / "desktop_candidate_v1_standard_scaler.joblib"
        ),
        "model": (
            root
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "one_class_svm_desktop_candidate_v1.joblib"
        ),
        "threshold": (
            root
            / "ml"
            / "models"
            / "desktop_candidate_v1"
            / "ocsvm_v1"
            / "threshold.json"
        ),
    }
