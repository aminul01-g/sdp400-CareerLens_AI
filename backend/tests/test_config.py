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
