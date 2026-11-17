"""Migrations must produce exactly the schema the models describe, and an old
pre-accounts demo database must be preserved, not destroyed."""

import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db import Base, engine


def test_migrations_match_models():
    # fresh_db already ran `alembic upgrade head` on this database.
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"Models and migrations differ; run `alembic revision --autogenerate`: {diff}"


def test_legacy_sqlite_demo_database_is_backed_up_not_lost(tmp_path, monkeypatch):
    import app.db as db_module

    legacy = tmp_path / "tuition.db"
    con = sqlite3.connect(legacy)
    con.execute("CREATE TABLE students (id TEXT PRIMARY KEY, name TEXT)")
    con.execute("INSERT INTO students VALUES ('1', 'Old demo student')")
    con.commit()
    con.close()

    test_engine = create_engine(f"sqlite:///{legacy}")
    monkeypatch.setattr(db_module, "engine", test_engine)
    db_module.init_db()

    backups = list(tmp_path.glob("tuition.db.pre-accounts-*.bak"))
    assert len(backups) == 1
    assert sqlite3.connect(backups[0]).execute("SELECT name FROM students").fetchone() == ("Old demo student",)
    tables = {r[0] for r in sqlite3.connect(legacy).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"guardians", "students", "auth_sessions", "alembic_version"} <= tables
    test_engine.dispose()
