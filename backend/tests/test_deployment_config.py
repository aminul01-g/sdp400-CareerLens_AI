"""The deployment configuration, checked against the settings it configures.

A configuration file that names a variable the application does not read is a
silent failure: the deployment starts, the setting is ignored, and the
behaviour is whatever the default happens to be. The reverse is worse — a
setting the application reads but the deployment never sets.

The check is mechanical: every variable name in ``backend/.env.example`` and
every ``envVars`` key in ``backend/render.yaml`` must resolve to a field of
``Settings``. A typo in either file fails here rather than in production.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = BACKEND_ROOT / ".env.example"
RENDER_YAML = BACKEND_ROOT / "render.yaml"

#: A variable in a .env file is ``NAME=value``. The name is everything before
#: the first ``=``.
_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")

#: A Render environment variable is declared as ``- key: NAME``.
_RENDER_KEY = re.compile(r"^\s*-\s*key:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")


def _settings_names() -> set[str]:
    return {name.upper() for name in Settings.model_fields}


def _env_example_names() -> list[str]:
    names: list[str] = []
    for raw in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if match:
            names.append(match.group(1))
    return names


def _render_yaml_keys() -> list[str]:
    keys: list[str] = []
    for raw in RENDER_YAML.read_text(encoding="utf-8").splitlines():
        match = _RENDER_KEY.match(raw)
        if match:
            keys.append(match.group(1))
    return keys


def test_the_env_example_names_real_settings() -> None:
    names = _env_example_names()
    assert names, "the .env.example file declares no variables"
    unknown = [name for name in names if name.upper() not in _settings_names()]
    assert not unknown, f".env.example names settings that do not exist: {unknown}"


def test_the_render_blueprint_names_real_settings() -> None:
    keys = _render_yaml_keys()
    assert keys, "render.yaml declares no environment variables"
    unknown = [key for key in keys if key.upper() not in _settings_names()]
    assert not unknown, f"render.yaml names settings that do not exist: {unknown}"


def test_the_rate_limit_backend_is_configured_for_the_shared_limiter() -> None:
    """The shipped deployment must use the shared limit.

    The container runs uvicorn with two workers, so the in-process backend
    would give the caller twice the intended allowance.
    """
    assert "RATE_LIMIT_BACKEND" in _render_yaml_keys()
    assert "RATE_LIMIT_BACKEND" in _env_example_names()


def test_the_smtp_transport_is_configured_for_certificate_verification() -> None:
    """STARTTLS without verification is encrypted but unauthenticated."""
    assert "SMTP_TLS_VERIFY" in _env_example_names()


@pytest.mark.parametrize("name", ["rate_limit_backend", "smtp_tls_verify", "smtp_ca_file"])
def test_the_new_settings_exist(name: str) -> None:
    assert name in Settings.model_fields


def test_the_rate_limit_backend_default_is_the_shared_one() -> None:
    assert Settings.model_fields["rate_limit_backend"].default == "postgres"


def test_the_smtp_verification_default_is_on() -> None:
    assert Settings.model_fields["smtp_tls_verify"].default is True
