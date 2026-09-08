from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from .db import default_database_url
from .runtime_paths import (
    alembic_ini_path,
    migrations_path,
)


def upgrade_database(
    *,
    database_url:
        str
        | None = None,
    ini_path:
        str
        | Path
        | None = None,
    script_location:
        str
        | Path
        | None = None,
) -> str:
    url = (
        database_url
        or default_database_url()
    )

    if url in {
        "sqlite:///:memory:",
        "sqlite://",
    }:
        return (
            "skipped_in_memory"
        )

    config_path = Path(
        ini_path
        or alembic_ini_path()
    )

    migrations = Path(
        script_location
        or migrations_path()
    )

    if not config_path.exists():
        raise FileNotFoundError(
            "Alembic configuration not found: "
            + str(
                config_path
            )
        )

    if not migrations.exists():
        raise FileNotFoundError(
            "Alembic migrations not found: "
            + str(
                migrations
            )
        )

    alembic = Config(
        str(
            config_path
        )
    )

    alembic.set_main_option(
        "script_location",
        str(
            migrations
        )
    )

    alembic.set_main_option(
        "sqlalchemy.url",
        url.replace(
            "%",
            "%%",
        )
    )

    # backend/migrations/env.py supports EVIL_TWIN_DB_URL for CLI use.
    # During a programmatic packaged migration we temporarily force that
    # variable to the exact URL requested here, so an unrelated parent
    # environment cannot redirect Alembic to another database.
    previous = os.environ.get(
        "EVIL_TWIN_DB_URL"
    )

    os.environ[
        "EVIL_TWIN_DB_URL"
    ] = url

    try:
        command.upgrade(
            alembic,
            "head",
        )
    finally:
        if previous is None:
            os.environ.pop(
                "EVIL_TWIN_DB_URL",
                None,
            )
        else:
            os.environ[
                "EVIL_TWIN_DB_URL"
            ] = previous

    return "upgraded"
