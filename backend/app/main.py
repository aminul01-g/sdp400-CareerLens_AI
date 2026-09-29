"""FastAPI application factory.

Wires configuration, logging, the database, CORS, the error envelope and every
domain router. Everything here is deliberately thin — a route belongs in
``app/api/routes/``, business logic in ``app/services/``, computation in
``app/ml/``, and none of those three import each other's concerns.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.db.session import check_database_connection, engine

logger = logging.getLogger("app.main")

DESCRIPTION = """
**CareerLens AI** — an AI-powered job and career recommendation system for
AI/ML roles.

### What this API does

1. **Authentication** — register, log in, refresh, and manage a session with
   JWT bearer tokens and `user` / `admin` roles.
2. **Profile CRUD** — headline, career goal, bio, links, education level.
3. **Skill management** — skills are chosen from a curated taxonomy of AI/ML
   skills (with aliases) and carry a proficiency from 1 to 5.
4. **Projects, education, certifications** — full CRUD, all ownership-scoped.
5. **CV analysis** — upload a PDF or DOCX, extract its text, detect skills with
   spaCy phrase matching, and let the user confirm the result before anything
   reaches their profile.
6. **Recommendation** — rank AI/ML job roles with an explainable compatibility
   score: `w1 * weighted skill coverage + w2 * TF-IDF cosine similarity`.
7. **Skill-gap analysis** — required skills of a target role minus the user's
   skills, ordered by importance weight.

### Design notes

* **No trained classifier.** The engine is unsupervised similarity plus
  rule-based weighting. There is no fitted model and no training data; this is a
  deliberate design choice, disclosed in `docs/evaluation_report.md`.
* **OCR is out of scope.** An image-only PDF returns `422` with a clear message
  rather than silently detecting zero skills.
* **The optional LLM learning path is off by default.** No core endpoint depends
  on it; with `LLM_ENABLED=false` it returns `503 feature_disabled`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    configure_logging()
    logger.info(
        "Starting %s v%s in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
        extra={"kind": "startup"},
    )
    if not check_database_connection():
        # Loud on purpose. A service that answers /health with 200 while unable
        # to reach its database is worse than one that refuses to start.
        raise RuntimeError(
            "Cannot reach the database. Check DATABASE_URL and that PostgreSQL is running."
        )
    logger.info("Database connection verified", extra={"kind": "startup"})
    yield
    engine.dispose()
    logger.info("Shutdown complete", extra={"kind": "shutdown"})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. A factory (rather than a module-level singleton) so
    tests can construct one with overridden settings."""
    settings = settings or get_settings()

    app = FastAPI(
        title="CareerLens AI API",
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "CareerLens AI — SDP400, BUBT"},
        license_info={"name": "Academic project"},
    )

    # S2 fix: an explicit allowlist. The legacy app called CORS(app) with no
    # allowlist at all (backend/app.py:18).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        """Attach a request id and a server-timing header to every response."""
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"], summary="Service banner")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get(
        "/health",
        tags=["meta"],
        summary="Liveness and database readiness",
        response_description="Service and database status",
    )
    async def health() -> dict[str, Any]:
        database_ok = check_database_connection()
        return {
            "status": "ok" if database_ok else "degraded",
            "service": settings.app_name,
            "version": settings.app_version,
            "database": "ok" if database_ok else "unavailable",
            "environment": settings.environment,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/readyz", tags=["meta"], summary="Readiness probe")
    async def readyz() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
