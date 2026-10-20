"""The database URL always names a driver that is installed.

SQLAlchemy reads the driver from the URL's scheme. A bare
``postgresql://`` means **psycopg2**, and psycopg2 is not a dependency of
this project — the driver here is psycopg3, spelled
``postgresql+psycopg://``.

Platforms hand out their connection strings in the bare form. Render's
internal URL is ``postgresql://user:pass@host/db``. So a deployment that
copied the platform's URL verbatim would start the application, and then
fail on the first query with ``ModuleNotFoundError: No module named
'psycopg2'`` — or, worse, fail the migration at boot and never serve a
request at all. That is not a hypothetical: it is what happened on the
first deploy to Render.

These tests pin the normalisation, in the settings object and in the
alembic environment, which reads the variable separately and would
otherwise bypass the settings validator entirely.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        # Already explicit: left alone.
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("postgresql+asyncpg://u@h/d", "postgresql+asyncpg://u@h/d"),
        # Not PostgreSQL: not our business.
        ("sqlite:///./local.db", "sqlite:///./local.db"),
    ],
)
def test_a_bare_postgres_url_gains_the_installed_driver(given: str, expected: str) -> None:
    assert Settings._normalise_database_url(given) == expected


def test_the_settings_validator_applies_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment variable reaches the application normalised."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    settings = Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "psycopg2" not in settings.database_url


def test_the_test_database_url_is_normalised_too(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "postgres://u:p@h/d")
    settings = Settings()
    assert settings.test_database_url.startswith("postgresql+psycopg://")


def test_the_alembic_environment_normalises_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """Alembic reads the variable itself, so it must normalise it too.

    ``alembic/env.py`` reads ``os.getenv("DATABASE_URL")`` directly rather
    than through the settings object, so the validator above does not
    cover it. The migration is the first thing that runs on a deploy: if
    the URL names the wrong driver, the service never starts, and the
    error is a stack trace about a missing module rather than a
    configuration message.
    """
    from pathlib import Path

    import app.core.config as config_module

    backend_root = Path(config_module.BACKEND_ROOT)
    env_path = backend_root / "alembic" / "env.py"
    source = env_path.read_text(encoding="utf-8")
    assert "_normalise_database_url" in source, (
        "alembic/env.py reads DATABASE_URL directly and must normalise it"
    )


def test_the_psycopg_driver_is_the_one_installed() -> None:
    """The driver the URL names has to be the driver in the requirements.

    A URL that names a driver nobody installed is a runtime error
    dressed up as a configuration one.
    """
    requirements = (
        Path(__file__).resolve().parents[1] / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert "psycopg[binary]" in requirements or "psycopg==" in requirements
    assert "psycopg2" not in requirements
