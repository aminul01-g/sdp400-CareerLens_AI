"""T027 — the application refuses to start without a strong ``JWT_SECRET_KEY``.

This is the real fix for security finding S7. The legacy Flask app fell back to
``SECRET_KEY = 'dev-secret'`` and ``JWT_SECRET_KEY = 'jwt-secret'``
(``backend/app.py:19,22``), so a misconfigured deployment looked perfectly healthy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import MIN_SECRET_LENGTH, Settings


def _env(monkeypatch: pytest.MonkeyPatch, secret: str | None) -> None:
    """Clear the relevant environment variables.

    ``_env_file=None`` is essential: without it, ``Settings`` still reads
    ``backend/.env``, which holds a *valid* generated secret, and the
    "missing secret" case would silently pass.
    """
    for key in ("JWT_SECRET_KEY", "ENVIRONMENT", "SKILL_COVERAGE_WEIGHT", "TFIDF_WEIGHT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "test")
    if secret is not None:
        monkeypatch.setenv("JWT_SECRET_KEY", secret)


def build(**overrides: object) -> Settings:
    """Construct Settings without the .env file, so only monkeypatched vars apply."""
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_missing_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, None)
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY is not set"):
        build()


def test_empty_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "   ")
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY is not set"):
        build()


def test_short_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "short-secret-too-short")
    with pytest.raises(ValidationError, match="at least 32 are required"):
        build()


def test_boundary_length_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "a" * MIN_SECRET_LENGTH)
    assert build().jwt_secret_key == "a" * MIN_SECRET_LENGTH


def test_generated_length_secret_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The documented generator produces a usable value."""
    import secrets

    _env(monkeypatch, secrets.token_urlsafe(48))
    assert len(build().jwt_secret_key) >= MIN_SECRET_LENGTH


def test_placeholder_secret_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """A long-but-obviously-placeholder secret is still a mistake in production."""
    _env(monkeypatch, "CHANGE_ME_" + "x" * 40)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValidationError, match="placeholder"):
        build()


def test_weak_legacy_defaults_would_be_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """The two literals the legacy app used as fallbacks are both rejected."""
    for legacy in ("dev-secret", "jwt-secret"):
        _env(monkeypatch, legacy)
        with pytest.raises(ValidationError):
            build()


def test_weights_must_sum_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A compatibility score is only interpretable on 0-1 if the components partition it."""
    _env(monkeypatch, "a" * MIN_SECRET_LENGTH)
    monkeypatch.setenv("SKILL_COVERAGE_WEIGHT", "0.6")
    monkeypatch.setenv("TFIDF_WEIGHT", "0.5")
    with pytest.raises(ValidationError, match="must equal 1.0"):
        build()


def test_weights_may_be_tuned(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "a" * MIN_SECRET_LENGTH)
    monkeypatch.setenv("SKILL_COVERAGE_WEIGHT", "0.7")
    monkeypatch.setenv("TFIDF_WEIGHT", "0.3")
    settings = build()
    assert settings.skill_coverage_weight == pytest.approx(0.7)
    assert settings.tfidf_weight == pytest.approx(0.3)


def test_allowed_origins_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "a" * MIN_SECRET_LENGTH)
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000, http://example.test ,")
    origins = build().allowed_origin_list
    assert origins == ["http://localhost:3000", "http://example.test"]


def test_upload_allowlists_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, "a" * MIN_SECRET_LENGTH)
    settings = build()
    assert ".pdf" in settings.allowed_extension_list
    assert ".docx" in settings.allowed_extension_list
    assert "application/pdf" in settings.allowed_content_type_list
    assert settings.max_upload_bytes == 5 * 1024 * 1024


# --------------------------------------------------------------------------- #
# misshapen environment variables
# --------------------------------------------------------------------------- #


@pytest.fixture
def config_warnings(monkeypatch):
    """Capture warnings emitted on the ``app.core.config`` logger directly.

    Deliberately not ``caplog``. ``app/core/logging.py`` sets ``propagate: False``
    on the whole ``app`` logger tree, so once any other test has called
    ``configure_logging()`` the records never reach the root handler -- which made
    these tests pass alone and fail in the full suite. Attaching a handler to the
    logger under test measures the thing being asserted and does not depend on
    which tests ran first.
    """
    import logging

    from app.core import config as config_module

    captured: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = Capture()
    logger = config_module.logger
    logger.addHandler(handler)
    previous_level = logger.level
    previous_disabled = logger.disabled
    logger.setLevel(logging.WARNING)
    # Force the logger live for the duration. A prior test may have left it
    # disabled -- a repeat dictConfig does exactly that to child loggers -- and
    # these tests assert what the validator emits, not what the ambient logging
    # configuration happens to be.
    logger.disabled = False
    try:
        yield captured
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled


def test_misspelt_env_var_warns_with_a_suggestion(monkeypatch, config_warnings) -> None:
    """A typo in a setting name must not be silently swallowed.

    ``extra="ignore"`` has to stay, because platforms inject their own variables.
    The price is that ``ALLOWED_ORIGIN`` (missing the S) looks exactly like an
    unset variable and the app quietly falls back to allowing no CORS origins.
    A boot-time warning is what turns that back into a visible problem.
    """
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://careerlens.example")
    Settings(jwt_secret_key="x" * 40)
    messages = " ".join(r.getMessage() for r in config_warnings)
    assert "ALLOWED_ORIGIN" in messages
    assert "ALLOWED_ORIGINS" in messages, "the warning must name the correct variable"


def test_env_vars_owned_by_other_tools_are_not_warned_about(monkeypatch, config_warnings) -> None:
    """A platform's own variables must not produce noise.

    Render, Vercel and the shell all inject names this app has never heard of.
    Warning about those would train everyone to ignore the log.
    """
    for name in ("PATH", "PORT", "RENDER", "RAILWAY_ENVIRONMENT", "HOSTNAME", "HOME"):
        monkeypatch.setenv(name, "something")
    Settings(jwt_secret_key="x" * 40)
    assert not config_warnings, [r.getMessage() for r in config_warnings]


def test_recognised_env_vars_never_warn(monkeypatch, config_warnings) -> None:
    """The check must not fire on variables that are correctly spelled."""
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    settings = Settings(jwt_secret_key="x" * 40)
    assert not config_warnings, [r.getMessage() for r in config_warnings]
    assert settings.access_token_expire_minutes == 60


def test_warning_never_prevents_startup(monkeypatch, config_warnings) -> None:
    """A near-miss must not stop the app from serving.

    The whole reason unknown names are tolerated is that platforms inject them.
    Turning a warning into an exception would break every deployment that sets
    anything this app did not anticipate.
    """
    monkeypatch.setenv("JWT_SECRET_KEY_TYPO", "whatever")
    settings = Settings(jwt_secret_key="x" * 40)
    assert settings.app_name
    assert config_warnings, "the warning is still expected, it just does not block boot"


def test_unrecognised_prefixed_var_warns_without_a_suggestion(monkeypatch, config_warnings) -> None:
    """A name with no close match still gets flagged, just without advice.

    Better to say "this is not read by us" than to stay quiet: the operator can
    then decide whether it mattered.
    """
    monkeypatch.setenv("CAREERLENS_MYSTERY_KNOB", "1")
    Settings(jwt_secret_key="x" * 40)
    messages = " ".join(r.getMessage() for r in config_warnings)
    assert "CAREERLENS_MYSTERY_KNOB" in messages
    assert "did you mean" not in messages


# --------------------------------------------------------------------------- #
# configure_logging must be idempotent
# --------------------------------------------------------------------------- #


def test_repeated_configure_logging_leaves_our_loggers_enabled() -> None:
    """Re-applying the logging config must not silence the app's own loggers.

    Regression test. ``dictConfig`` is a global, destructive operation, and this
    function was called once per app construction -- once per test, in practice.
    Repeat calls left ``app.core.config`` with ``disabled = True``, so the
    misspelt-environment-variable warnings stopped appearing and two tests that
    assert on them passed alone but failed in the full suite. Anything the app
    reports about its own configuration is worthless if a logger can be switched
    off as a side effect of configuring twice.
    """
    import logging

    from app.core.logging import configure_logging

    configure_logging()
    configure_logging()
    configure_logging()

    for name in ("app", "app.core.config", "app.core.logging", "app.main"):
        logger = logging.getLogger(name)
        assert not logger.disabled, f"logger {name} was disabled by repeat configuration"


def test_our_loggers_still_emit_after_repeat_configuration(monkeypatch) -> None:
    """The end-to-end guarantee: a warning still reaches the handler after repeats."""
    import logging

    from app.core.logging import configure_logging

    monkeypatch.setenv("CAREERLENS_MYSTERY_KNOB", "1")
    configure_logging()
    configure_logging()

    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    from app.core import config as config_module

    handler = Capture()
    config_module.logger.addHandler(handler)
    try:
        Settings(jwt_secret_key="x" * 40)
    finally:
        config_module.logger.removeHandler(handler)
    assert records, "the config warning was swallowed after repeat configure_logging()"
