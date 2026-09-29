"""Engine, session factory, and the per-request ``get_db`` dependency.

``expire_on_commit=False`` matters here: without it SQLAlchemy expires every
attribute on commit, so a service that commits and then reads an attribute
outside the session's transaction triggers a refresh — and, in an async or
closed-session context, a lazy-load failure.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger("app.db")


def _engine_kwargs(database_url: str) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "echo": get_settings().db_echo,
        "future": True,
        # Recycle below the typical 1-hour proxy idle timeout so a long-running
        # API never hands a dead connection to a request.
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if database_url.startswith("postgresql"):
        kwargs["pool_size"] = get_settings().db_pool_size
        kwargs["max_overflow"] = get_settings().db_max_overflow
    return kwargs


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build a new engine for the given URL (defaults to ``Settings.database_url``)."""
    url = database_url or get_settings().database_url
    return create_engine(url, **_engine_kwargs(url))


engine: Engine = create_db_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding one session per request.

    Rolls back on any exception so a failed request never leaves a half-written
    transaction open, and always closes the session.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional scope for scripts and background work."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """Round-trip a trivial query. Used by ``GET /health`` and startup."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover - depends on a live database
        logger.error("Database health check failed: %s", exc, extra={"kind": "db_health"})
        return False
