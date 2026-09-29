# syntax=docker/dockerfile:1
#
# CareerLens AI — API image.
#
# Replaces the predecessor's Flask/gunicorn image, which pointed at app.py, a
# module that no longer exists. Two things about this file are deliberate:
#
# 1. The spaCy English model is NOT downloaded here. requirements.txt pins
#    en_core_web_sm as a direct wheel, so the model version is reproducible and
#    the build needs no network round trip after the wheel fetch. Running
#    `python -m spacy download` in the build step would resolve whatever version
#    is current that day, which is plan risk R21.
#
# 2. Migrations are NOT run at container start. Two replicas starting together
#    would race each other through alembic. Migrations are an explicit step:
#    `docker compose run --rm api alembic upgrade head`. render.yaml does run
#    them on boot, because Render gives one instance per web service; the
#    reasoning is written up in docs/deployment.md.

# ---- base ------------------------------------------------------------------ #
FROM python:3.12-slim AS base

# libpq5 is needed by psycopg's binary wheel at runtime. build-essential and
# git are build-only and deliberately dropped from the final stage.
RUN apt-get update \
 && apt-get install --no-install-recommends -y libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/careerlens


# ---- dependencies (cached independently of application code) --------------- #
FROM base AS deps
COPY requirements.txt ./
# --no-compile keeps .pyc out of the layer; PYTHONDONTWRITEBYTECODE means the
# runtime will not try to write them either, so the image stays smaller.
RUN pip install --no-compile -r requirements.txt


# ---- runtime --------------------------------------------------------------- #
FROM base AS runtime

# A non-root user with no login shell. An API that only needs to read its own
# code has no reason to be root, and a container escape should not start as root.
RUN groupadd --system --gid 1001 careerlens \
 && useradd --system --uid 1001 --gid careerlens --no-create-home --shell /usr/sbin/nologin careerlens

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Only what the process actually reads at runtime. Tests, the virtualenv, the
# legacy Flask tree and any .env are excluded by .dockerignore, and not named
# here, so they cannot enter the image even if that file is bypassed.
COPY --chown=careerlens:careerlens alembic.ini ./
COPY --chown=careerlens:careerlens alembic ./alembic
COPY --chown=careerlens:careerlens app ./app
COPY --chown=careerlens:careerlens data ./data
COPY --chown=careerlens:careerlens scripts ./scripts

# The upload directory has to exist and be writable before the non-root user
# starts. /srv/careerlens itself is root-owned, so the app cannot create this at
# runtime -- the CV upload route returned a 500 until this was added. Pre-creating
# it is the fix; the alternative, running as root, is not.
RUN mkdir -p /srv/careerlens/uploads && chown careerlens:careerlens /srv/careerlens/uploads

USER careerlens

# Declared so the directory survives a container replacement and can be backed by a
# named volume. An anonymous container filesystem would lose uploaded CVs on every
# deploy, and a CV is user data.
VOLUME ["/srv/careerlens/uploads"]

EXPOSE 8000

# The health check is a real readiness probe: /health fails when the database is
# unreachable, so Docker and Render both hold traffic off a container that cannot
# serve. Curl is installed above for exactly this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Two workers. The engine is CPU-bound (TF-IDF over 82 roles, PDF text
# extraction), so a single worker would leave a core idle under any real load.
# The container is the unit of horizontal scaling, not the worker count.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
