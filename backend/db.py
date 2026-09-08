from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .runtime_paths import database_path



def default_database_url() -> str:
    configured = os.environ.get(
        "EVIL_TWIN_DB_URL"
    )

    if configured:
        return configured

    return (
        "sqlite:///"
        + str(
            database_path()
        )
    )


def create_database_engine(
    database_url: str | None = None,
) -> Engine:
    url = database_url or default_database_url()

    kwargs = {
        "future": True,
    }

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {
            "check_same_thread": False,
        }

        # An in-memory SQLite DB is per connection unless a StaticPool is
        # used. This makes FastAPI/test sessions share one deterministic DB.
        if (
            url == "sqlite:///:memory:"
            or url == "sqlite://"
        ):
            kwargs["poolclass"] = StaticPool

    engine = create_engine(
        url,
        **kwargs,
    )

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_foreign_keys(
            dbapi_connection,
            connection_record,
        ):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine):
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


@contextmanager
def session_scope(session_factory):
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
