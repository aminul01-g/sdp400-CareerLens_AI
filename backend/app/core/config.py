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
from ipaddress import IPv4Network, IPv6Network, ip_network
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: The union of the two network classes, for annotations. ``ip_network`` is the
#: *constructor*; these are the *types* it returns.
IPNetwork = IPv4Network | IPv6Network

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
_APP_ENV_PREFIXES = (
    "CAREERLENS_",
    "JWT_",
    "LLM_",
    "GROQ_",
    "DATABASE_",
    "ADMIN_",
    "ALLOWED_",
    "CORS_",
    "RATE_LIMIT_",
    "SMTP_",
    "MAIL_",
)


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    #: Cache for :attr:`trusted_proxy_networks`, keyed on the raw setting
    #: string. ``None`` means "not parsed yet"; a pydantic model field would
    #: be validated as configuration, so this is a private attribute rather
    #: than a declared field.
    _trusted_proxy_networks: tuple[str, list[IPNetwork]] | None = None

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

    # ---- Email ---------------------------------------------------------
    # When SMTP_HOST is empty the mail falls back to the file transport, which
    # writes the message to MAIL_DIR and logs the path. That is what makes the
    # verification and password-reset flows exercisable end to end without a
    # mail provider.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    # Whether the SMTP server's certificate is verified. On by default, and it
    # is what makes STARTTLS worth having: without it the connection is
    # encrypted but the server is not authenticated, which is a worse position
    # than no encryption because it looks secure. Turn it off only against a
    # server with a self-signed certificate, and only in a test.
    smtp_tls_verify: bool = True
    # A PEM bundle to trust instead of the system store. Needed when the mail
    # provider uses a private certificate authority.
    smtp_ca_file: str = ""
    mail_from: str = "no-reply@careerlens.dev"
    mail_from_name: str = "CareerLens AI"
    # "file" or "console". Ignored when SMTP_HOST is set.
    mail_transport: str = "file"
    mail_dir: str = "./mailbox"
    # Whether an unverified address may sign in. Off by default: a product
    # that locks out a user who has not clicked a link reads as broken, and
    # the audit trail records the unverified addresses either way.
    require_email_verification: bool = False
    # How long the two kinds of token stay valid.
    email_verification_ttl_minutes: int = 1440
    password_reset_ttl_minutes: int = 30
    # The public base URL, used to build the links in the emails.
    public_base_url: str = "http://localhost:3000"

    # ---- The feedback prior ---------------------------------------------
    # How much the community prior may move a score, as a fraction. 0.10 means
    # a role everybody dismissed loses at most 10% of its score — it is still
    # shown, still ranked and still explained. Set to 0 to switch the prior off.
    feedback_prior_strength: float = 0.10
    # How many observations a role needs before its prior is used at all.
    # Below this the prior is exactly zero: three users' opinions are noise.
    feedback_prior_min_samples: int = 5

    # ---- Rate limiting ------------------------------------------------
    # The limit is shared by every worker and every replica. The counters live
    # in the database, not in a process's memory, because the shipped image
    # runs uvicorn with two workers and a per-process counter would have given
    # the caller twice the allowance configured here. "memory" selects the
    # in-process limiter, which is what the test suite runs against.
    rate_limit_enabled: bool = True
    rate_limit_backend: str = "postgres"
    # Authentication: sign-in, registration and password reset.
    rate_limit_auth_requests: int = 10
    rate_limit_auth_window_seconds: int = 60
    # Generation: running the recommendation engine.
    rate_limit_generate_requests: int = 30
    rate_limit_generate_window_seconds: int = 60
    # Upload: CV submission.
    rate_limit_upload_requests: int = 10
    rate_limit_upload_window_seconds: int = 300
    # AI: every call that reaches the external model provider. The window is
    # deliberately longer than the others. A mentor conversation is a
    # multi-turn exchange, and a learner following a roadmap may regenerate it
    # a few times, so a per-minute cap would punish the exact behaviour the
    # feature exists to encourage. The cap still exists because every one of
    # these calls costs money.
    rate_limit_ai_requests: int = 20
    rate_limit_ai_window_seconds: int = 300
    # Networks whose ``X-Forwarded-For`` header may be believed, as a
    # comma-separated list of CIDR blocks or bare addresses. Empty — the
    # default — means believe none of them.
    #
    # ``X-Forwarded-For`` is client-supplied. A server that believes it
    # unconditionally lets any caller mint a fresh identity per request,
    # which is exactly what a rate limiter exists to prevent: the limit
    # protects the password endpoints from guessing, and a forged header
    # turns a 10-per-minute cap into an unlimited one. Only a proxy whose
    # address is in this list is allowed to speak for its client.
    #
    # Render and Vercel both terminate TLS in front of the service, so the
    # peer address on a deployed instance is the platform's proxy, not the
    # user's. Set this to the platform's published egress ranges there. Left
    # empty in development, where the peer *is* the client.
    trusted_proxy_cidrs: str = ""

    # ---- Groq (the AI layer) ------------------------------------------
    # The AI layer is an *enhancement*. Nothing in the core — CV processing,
    # career matching, skill-gap analysis — reads any of these, and every AI
    # route returns a clean 503 when they are unset. That is the whole
    # contract, and it is why the defaults below are empty strings rather
    # than a key that might exist somewhere.
    #
    # ``groq_enabled`` defaults to true so that setting ``GROQ_API_KEY`` and
    # ``GROQ_MODEL`` is genuinely all a deployment has to do. It does not by
    # itself switch anything on: :attr:`groq_is_configured` also requires a
    # key, so an unconfigured deployment still answers 503.
    groq_enabled: bool = True
    # The default is empty, and it must stay empty. A key pasted into this
    # file would be committed to the repository and published with the code.
    # The key belongs in the environment: `backend/.env` locally, and the
    # deployment's encrypted environment variables in production.
    # `scripts/verify_compliance.py` fails the build if a key ever appears
    # in a tracked file.
    groq_api_key: str = ""
    # ``openai/gpt-oss-120b`` is a Groq *production* model and one of the four
    # that support strict-mode structured outputs, so the provider constrains
    # decoding to the JSON schema and the output cannot drift from it.
    # ``openai/gpt-oss-20b`` is the cheaper, faster alternative with the same
    # structured-output support.
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_timeout_seconds: int = 45
    # How many *extra* attempts a transient provider failure gets. Bounded on
    # purpose: an unbounded retry loop against a paid API is a denial of
    # wallet, and the user's request should fail fast and visibly rather than
    # hang.
    groq_max_retries: int = 1

    # ---- Deprecated LLM settings --------------------------------------
    # The first AI experiment used a generic OpenAI-compatible endpoint. It
    # still works and the learning-path endpoint still honours it, but Groq is
    # the supported provider now: :mod:`app.core.config` resolves
    # ``GROQ_*`` first and falls back to these only when a ``GROQ_*`` value is
    # absent. New deployments should set ``GROQ_*`` and leave these alone.
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
    @field_validator("database_url", "test_database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        """Make sure the URL names a driver that is actually installed.

        SQLAlchemy reads the driver from the URL's scheme. A bare
        ``postgresql://`` means **psycopg2**, which is not a dependency of
        this project — the driver here is psycopg3, spelled
        ``postgresql+psycopg://``. Platforms hand out their connection
        strings in the bare form: Render's internal URL is
        ``postgresql://user:pass@host/db``, and so are several others.

        Left alone, the application starts, and the first query fails with
        ``ModuleNotFoundError: No module named 'psycopg2'`` — or, worse,
        the migrations fail at boot and the service never comes up. Adding
        the driver here means a URL from any platform works, and the
        development default keeps its explicit spelling either way.
        """
        for scheme in ("postgresql://", "postgres://"):
            if value.startswith(scheme):
                return "postgresql+psycopg://" + value[len(scheme):]
        return value

    @field_validator("upload_dir")
    @classmethod
    def _resolve_upload_dir(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_ROOT / path).resolve())

    @field_validator("mail_dir")
    @classmethod
    def _resolve_mail_dir(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_ROOT / path).resolve())

    @field_validator("rate_limit_backend")
    @classmethod
    def _validate_rate_limit_backend(cls, value: str) -> str:
        allowed = {"postgres", "memory"}
        backend = value.strip().lower()
        if backend not in allowed:
            raise ValueError(
                f"RATE_LIMIT_BACKEND must be one of {sorted(allowed)}; got {value!r}. "
                "'postgres' shares the limit across every worker and replica; "
                "'memory' keeps it inside one process."
            )
        return backend

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
    def trusted_proxy_networks(self) -> list[IPNetwork]:
        """The networks whose ``X-Forwarded-For`` header may be believed.

        Parsed once per distinct value and cached, so the hot path does not
        re-parse a string on every request. A malformed entry is skipped
        rather than raising: a typo in a deployment variable should not stop
        the API from booting, and skipping it is the safe direction — an
        unparseable proxy is not a trusted proxy.

        The cache is keyed on the raw string, so a copied or updated
        settings object re-parses rather than returning a stale answer.
        """
        raw = self.trusted_proxy_cidrs
        cached = self._trusted_proxy_networks
        if cached is not None and cached[0] == raw:
            return cached[1]
        networks: list[IPNetwork] = []
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                networks.append(ip_network(entry, strict=False))
            except ValueError:
                logger.warning("Ignoring unparseable trusted proxy entry", extra={"kind": "config"})
        self._trusted_proxy_networks = (raw, networks)
        return networks

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

    @property
    def learning_resources_path(self) -> Path:
        return DATA_DIR / "learning_resources.json"

    @property
    def groq_is_configured(self) -> bool:
        """Whether the AI layer can actually reach the provider.

        A key is required, not merely requested. The flag alone is not enough:
        a deployment that sets ``GROQ_ENABLED=true`` and forgets the key would
        otherwise fail at the first request with a provider error instead of
        the clean, actionable 503 the rest of the system expects.
        """
        return bool(self.groq_enabled and self.provider_api_key.strip())

    @property
    def provider_api_key(self) -> str:
        """The API key to use, preferring ``GROQ_API_KEY``.

        The legacy ``LLM_API_KEY`` is still honoured so that an existing
        deployment does not break the moment this version is deployed; a
        ``GROQ_*`` value always wins.
        """
        return (self.groq_api_key.strip() or self.llm_api_key.strip())

    @property
    def provider_model(self) -> str:
        return (self.groq_model.strip() or self.llm_model.strip() or "openai/gpt-oss-120b")

    @property
    def provider_base_url(self) -> str:
        return (self.groq_base_url.strip() or self.llm_base_url.strip())

    @property
    def provider_timeout_seconds(self) -> int:
        return self.groq_timeout_seconds or self.llm_timeout_seconds or 45


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (T014).

    ``lru_cache`` means the environment is parsed once per process, and tests can
    reset it with ``get_settings.cache_clear()``.
    """
    return Settings()
