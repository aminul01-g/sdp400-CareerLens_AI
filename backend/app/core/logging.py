"""Structured logging with request correlation.

Replaces the ad-hoc ``app.logger.setLevel(...)`` in the legacy ``app.py:17``.
Two things are added rather than removed: a ``request_id`` injected by middleware
and threaded through the log context, and an optional JSON formatter for
platforms that ingest logs as events.
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
# The default is an empty *tuple*, not an empty dict: a ContextVar default is
# created once and shared by every request, so a mutable default would be a
# process-wide data leak waiting to happen.
extra_context: ContextVar[tuple[tuple[str, Any], ...]] = ContextVar(
    "extra_context", default=()
)


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class ContextFilter(logging.Filter):
    """Attach the ambient structured context to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in extra_context.get():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable single line for local development."""

    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.now(UTC).strftime("%H:%M:%S")
        base = f"{stamp} {record.levelname:<7} [{getattr(record, 'request_id', '-')}] {record.name}: {record.getMessage()}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


_LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": RequestIdFilter},
        "context": {"()": ContextFilter},
    },
    "formatters": {
        "console": {
            "()": ConsoleFormatter,
        },
        "json": {
            "()": JsonFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["request_id", "context"],
            "stream": sys.stdout,
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "app": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        # SQLAlchemy engine echo would log every statement; only when asked.
        "sqlalchemy.engine": {"level": "WARNING", "handlers": ["console"], "propagate": False},
    },
}


_configured = False


def configure_logging() -> None:
    """Install the logging configuration. Idempotent.

    Idempotence is a correctness requirement, not an optimisation. ``dictConfig``
    is a *global, destructive* operation: it re-applies itself to every logger in
    the process and rewrites state for all of them. Applying it once per request
    or once per test does not merely waste time, it corrupts the logger tree --
    module loggers such as ``app.core.config`` were left with ``disabled = True``
    after a repeat call, which silently swallowed the startup warnings this
    project relies on to surface a misspelt environment variable.

    The second half of the function re-enables the ``app`` tree for the same
    reason. Our module loggers are children of the named ``app`` logger, so
    whether stdlib's bookkeeping treats them as in-scope depends on the exact set
    of loggers that happened to exist at the time. Our own diagnostics must not
    depend on that, so they are asserted explicitly.
    """
    global _configured
    settings = get_settings()

    if not _configured:
        config = dict(_LOGGING_CONFIG)
        # Deep-copy the nested mapping. The previous shallow copy meant
        # `config["loggers"]["app"] = ...` mutated the module-level constant, so a
        # second call saw the first call's result as its own starting point.
        config["loggers"] = {k: dict(v) for k, v in _LOGGING_CONFIG["loggers"].items()}
        if settings.log_json:
            config["handlers"] = {
                **config["handlers"],
                "console": {
                    **config["handlers"]["console"],
                    "formatter": "json",
                    "stream": sys.stdout,
                },
            }
        config["root"] = {"level": settings.log_level.upper(), "handlers": ["console"]}
        config["loggers"]["app"] = {
            "level": settings.log_level.upper(),
            "handlers": ["console"],
            "propagate": False,
        }
        logging.config.dictConfig(config)
        _configured = True

    # Idempotent, so a level change between calls is still honoured.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(settings.log_level.upper())
    for name in list(logging.root.manager.loggerDict):
        if name == "app" or name.startswith("app."):
            candidate = logging.root.manager.loggerDict[name]
            if isinstance(candidate, logging.Logger):
                candidate.disabled = False
    app_logger.debug("Logging configured (level=%s)", settings.log_level)


def reset_logging_for_tests() -> None:
    """Forget that logging was configured, so the next call re-applies it."""
    global _configured
    _configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the ``app`` hierarchy."""
    if name.startswith("app"):
        return logging.getLogger(name)
    return logging.getLogger(f"app.{name}")
