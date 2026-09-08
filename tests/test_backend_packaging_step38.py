from __future__ import annotations

from sqlalchemy import (
    create_engine,
    inspect,
)

from backend.db import (
    default_database_url,
)
from backend.migrations_runner import (
    upgrade_database,
)
from backend.model_status import (
    ModelArtifactStatusService,
)
from backend.packaging.runtime_manifest import (
    inspect_packaging_inputs,
)
from backend.runtime_paths import (
    database_path,
    resource_root,
    runtime_artifact_paths,
    user_data_root,
)


def test_runtime_resource_root_is_repository_in_development():
    root = resource_root()

    assert (
        root
        / "backend"
        / "app.py"
    ).exists()

    assert (
        root
        / "alembic.ini"
    ).exists()


def test_app_data_directory_can_be_overridden(
    tmp_path,
    monkeypatch,
):
    destination = (
        tmp_path
        / "product-data"
    )

    monkeypatch.delenv(
        "EVIL_TWIN_DB_URL",
        raising=False,
    )

    monkeypatch.setenv(
        "EVIL_TWIN_APP_DATA_DIR",
        str(
            destination
        ),
    )

    assert (
        user_data_root()
        == destination.resolve()
    )

    assert (
        database_path()
        == (
            destination.resolve()
            / "evil_twin_detector.db"
        )
    )

    assert (
        default_database_url()
        == (
            "sqlite:///"
            + str(
                destination.resolve()
                / "evil_twin_detector.db"
            )
        )
    )


def test_model_status_default_uses_runtime_resource_contract():
    expected = (
        runtime_artifact_paths()
    )

    service = (
        ModelArtifactStatusService()
    )

    assert (
        service.paths()
        == expected
    )


def test_programmatic_migration_runner_upgrades_exact_file_database(
    tmp_path,
):
    database = (
        tmp_path
        / "packaged.db"
    )

    url = (
        "sqlite:///"
        + str(
            database
        )
    )

    assert (
        upgrade_database(
            database_url=url
        )
        == "upgraded"
    )

    engine = create_engine(
        url
    )

    tables = set(
        inspect(
            engine
        ).get_table_names()
    )

    assert {
        "scan_session",
        "network_observation",
        "network_features",
        "detection",
        "model_version",
        "application_settings",
        "alembic_version",
    }.issubset(
        tables
    )


def test_programmatic_migration_restores_parent_db_environment(
    tmp_path,
    monkeypatch,
):
    parent_url = (
        "sqlite:///:memory:"
    )

    monkeypatch.setenv(
        "EVIL_TWIN_DB_URL",
        parent_url,
    )

    target = (
        "sqlite:///"
        + str(
            tmp_path
            / "target.db"
        )
    )

    assert (
        upgrade_database(
            database_url=target
        )
        == "upgraded"
    )

    assert (
        default_database_url()
        == parent_url
    )


def test_in_memory_migration_is_skipped():
    assert (
        upgrade_database(
            database_url=(
                "sqlite:///:memory:"
            )
        )
        == "skipped_in_memory"
    )


def test_packaging_manifest_static_resources_are_ready():
    report = (
        inspect_packaging_inputs(
            resource_root()
        )
    )

    assert (
        report[
            "static_ready"
        ]
        is True
    )

    assert set(
        report[
            "scientific_artifacts"
        ]
    ) == {
        "reference",
        "scaler",
        "model",
        "threshold",
    }


def test_pyinstaller_and_electron_resource_contracts_exist():
    root = resource_root()

    assert (
        root
        / "backend"
        / "packaging"
        / "evil-twin-backend.spec"
    ).exists()

    assert (
        root
        / "scripts"
        / "build_backend_windows.ps1"
    ).exists()

    assert (
        root
        / "frontend"
        / "resources"
        / "backend"
        / ".gitkeep"
    ).exists()
