"""Application settings.

Every tunable is read from the environment (or a local ``.env``). The one
non-negotiable rule lives here: **the application refuses to start if
``JWT_SECRET_KEY`` is missing or shorter than 32 characters.**

That is the real fix for the legacy Flask app, which fell back to
``SECRET_KEY = 'dev-secret'`` and ``JWT_SECRET_KEY = 'jwt-secret'``
(``backend/app.py:19,22``). Swapping one weak default for another would leave the
same hole; failing loudly at import time means a misconfigured deployment is
caught before it serves a single request.
"""

from __future__ import annotations

import difflib
import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_ROOT / "data"

MIN_SECRET_LENGTH = 32

logger = logging.getLogger("app.core.config")

#: A process environment carries plenty of variables that are none of this app's
#: business -- PATH, RENDER, RAILWAY_ENVIRONMENT, PORT, HOSTNAME and so on. So
#: unknown names are ignored rather than rejected, which is what ``extra="ignore"``
#: is for. The cost of that leniency is that a typo in a variable this app *does*
#: read is silently swallowed and the default is used instead: set
#: ``JWT_EXPIRE_MINUTES`` and the token lifetime quietly stays at its default.
#: These prefixes narrow the search to names plausibly aimed at us.
_APP_ENV_PREFIXES = ("CAREERLENS_", "JWT_", "LLM_", "DATABASE_", "ADMIN_", "ALLOWED_", "CORS_")


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application -------------------------------------------------
    app_name: str = "careerlens-api"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api"

    # ---- Database ----------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://careerlens:careerlens_dev_password@localhost:5432/careerlens"
    )
    test_database_url: str = Field(
        default="postgresql+psycopg://careerlens:careerlens_dev_password@localhost:5432/careerlens_test"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # ---- Authentication ----------------------------------------------
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ---- CORS --------------------------------------------------------
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Uploads -----------------------------------------------------
    upload_dir: str = "./uploads"
    max_upload_mb: int = 5
    allowed_upload_extensions: str = ".pdf,.docx"
    allowed_upload_content_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # ---- Recommendation engine ---------------------------------------
    skill_coverage_weight: float = 0.60
    tfidf_weight: float = 0.40
    engine_version: str = "1.0.0"

    # ---- Optional LLM (proposal 4.2: the core must work without it) ---
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 20

    # ---- Seed admin account ------------------------------------------
    # Read ONLY by backend/scripts/seed_admin.py. The running application never
    # uses these, which is why they are grouped and documented here rather than
    # being read ad hoc from os.environ (which does not contain .env values).
    admin_email: str = ""
    admin_password: str = ""

    # ---- Logging -----------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("upload_dir")
    @classmethod
    def _resolve_upload_dir(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_ROOT / path).resolve())

    @model_validator(mode="after")
    def _warn_on_misspelt_env_vars(self) -> Settings:
        """Warn when an environment variable looks like a typo of a real setting.

        ``extra="ignore"`` is the right call for a platform that injects its own
        variables, but it makes a misspelt setting name indistinguishable from an
        unset one. That is a real deployment hazard: a typo in a CORS origin or a
        token lifetime is not a crash, it is a silent fallback to the default.

        This warns rather than raises, because the whole point of ignoring unknown
        names is to tolerate variables that are not ours. A warning in the boot log
        is enough to catch it, and a hard failure would break every platform that
        injects extras.
        """
        known = {name.upper() for name in type(self).model_fields}
        for name in sorted(os.environ):
            upper = name.upper()
            if upper in known or not upper.startswith(_APP_ENV_PREFIXES):
                continue
            match = difflib.get_close_matches(upper, known, n=1, cutoff=0.8)
            suggestion = match[0] if match else None
            logger.warning(
                "Environment variable %s is not read by this application%s.",
                upper,
                f"; did you mean {suggestion}?" if suggestion else "",
            )
        return self

    @model_validator(mode="after")
    def _validate_security(self) -> Settings:
        """Fail fast rather than run with a weak or missing signing key."""
        secret = self.jwt_secret_key.strip()
        if not secret:
            raise ValueError(
                "JWT_SECRET_KEY is not set. Copy backend/.env.example to backend/.env and "
                "generate a value of at least 32 characters, e.g. "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\"."
            )
        if len(secret) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY is {len(secret)} characters; at least {MIN_SECRET_LENGTH} "
                "are required. Generate one with "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\"."
            )
        if self.is_production and secret.startswith(("CHANGE_ME", "change-me")):
            raise ValueError("JWT_SECRET_KEY still holds the .env.example placeholder.")
        return self

    @model_validator(mode="after")
    def _validate_weights(self) -> Settings:
        total = self.skill_coverage_weight + self.tfidf_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "SKILL_COVERAGE_WEIGHT + TFIDF_WEIGHT must equal 1.0 "
                f"(got {self.skill_coverage_weight} + {self.tfidf_weight} = {total}). "
                "A compatibility score is only interpretable on a 0-1 scale if the "
                "two components partition that scale."
            )
        for name, value in (
            ("SKILL_COVERAGE_WEIGHT", self.skill_coverage_weight),
            ("TFIDF_WEIGHT", self.tfidf_weight),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]; got {value}.")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_list(self) -> tuple[str, ...]:
        return tuple(
            ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        )

    @property
    def allowed_content_type_list(self) -> tuple[str, ...]:
        return tuple(
            ct.strip() for ct in self.allowed_upload_content_types.split(",") if ct.strip()
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def skills_taxonomy_path(self) -> Path:
        return DATA_DIR / "skills_taxonomy.json"

    @property
    def job_roles_path(self) -> Path:
        return DATA_DIR / "job_roles.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (T014).

    ``lru_cache`` means the environment is parsed once per process, and tests can
    reset it with ``get_settings.cache_clear()``.
    """
    return Settings()
