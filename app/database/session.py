"""SQLite engine/session setup for Project Monitor's own database.

This database only ever stores Project Monitor's metadata about projects
(paths, detected type, process/monitoring state). It never touches files
inside a monitored project.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.paths import DATABASE_PATH, ensure_app_dirs
from app.database.base import Base

_engine = None
_SessionFactory: sessionmaker | None = None


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        ensure_app_dirs()
        path = db_path or str(DATABASE_PATH)
        _engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
            # The UI thread reads while the monitoring/discovery threads
            # write to the same file; WAL lets readers and writers work
            # concurrently instead of blocking on SQLite's default
            # rollback-journal locking, and busy_timeout makes a writer
            # wait out a lock instead of failing immediately.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return _engine


def init_db(db_path: str | None = None) -> None:
    """Create all tables. Safe to call repeatedly."""
    # Import models so they register on Base.metadata before create_all.
    from app.models import project  # noqa: F401

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    global _SessionFactory
    _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_session_factory() -> sessionmaker:
    if _SessionFactory is None:
        init_db()
    assert _SessionFactory is not None
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
