"""Database engine and session management (SQLAlchemy 2.0)."""

import logging
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BACKEND_DIR, get_settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    # Store every timestamp with its time zone (timestamptz on Postgres).
    type_annotation_map = {datetime: DateTime(timezone=True)}


def make_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        path = url.removeprefix("sqlite:///")
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # pragma: no cover - trivial
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Bring the database schema up to date by running migrations (Alembic).

    A database created by the pre-accounts version (tables but no migration
    history) can't be upgraded in place: a local SQLite demo file is moved aside
    as a backup and a fresh one is created; anything else stops startup rather
    than risk real data.
    """
    from alembic import command
    from alembic.config import Config

    from app import models  # noqa: F401  (register tables)

    tables = set(inspect(engine).get_table_names())
    if tables and "alembic_version" not in tables:
        db_path = engine.url.database if engine.url.get_backend_name() == "sqlite" else None
        if not db_path or db_path == ":memory:":
            raise RuntimeError("This database has tables but no migration history. Back it up and migrate it manually.")
        engine.dispose()  # close pooled connections so the file can be moved (Windows)
        backup = f"{db_path}.pre-accounts-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.bak"
        os.replace(db_path, backup)
        log.warning("Old-format demo database moved to %s; starting a fresh one.", backup)

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
