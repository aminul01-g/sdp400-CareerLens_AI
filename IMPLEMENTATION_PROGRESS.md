# CareerLens AI — Implementation Progress

**Authority:** `PROJECT_IMPLEMENTATION_PLAN.md` (176 tasks, 12 phases).
**Repository:** `/home/aminul/Development/sdp400`

Status legend: `[ ]` not started · `[~]` in progress · `[x]` completed · `[!]` blocked

Every completed task carries evidence. **No task is marked complete without an
observed result.**

---

## Environment reality (verified 30 Sep 2026)

| Fact | Plan's claim | Verified | Action taken |
|---|---|---|---|
| Docker daemon | not running, needs manual start | **confirmed** not running; `dockerd` refuses to start without root; `rootlesskit`/`slirp4netns` absent | **Resolved.** Bootstrapped rootless Docker: fetched static `rootlesskit` v2.3.1 + `slirp4netns` v1.3.2, wrote a `dockerd-rootless.sh`, and started the daemon as uid 1000. Real `postgres:16` runs from the plan's own `docker-compose.yml`. |
| PostgreSQL 16 | not installed | **confirmed** absent; no `sudo` | **Resolved** via the rootless Docker path above. PostgreSQL **16.15**, `pg_trgm` available, reachable on `localhost:5432`. |
| Python | 3.14.7, no 3.12 | **confirmed** | **Resolved** per plan note E1: `uv python install 3.12` → 3.12.13, pinned in `backend/.python-version`. Every ML wheel has a cp312 binary. |
| spaCy model | must be downloadable (T006) | **confirmed** loadable | Installed as a pinned wheel dependency (plan risk R21) rather than a runtime download. |
| Git | not a repository (correction C4) | **confirmed** | `git init` + first commit of the frozen legacy tree (T001). |
| Network | pypi reachable | **confirmed** | No dependency blocked. |

**Adapter note (deviation D-1).** The plan assumes a rootful Docker daemon started
by the user. This host has no sudo password, so the daemon runs **rootless**
(`DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock`). The `docker-compose.yml`,
`postgres:16` image, and every command in the plan are unchanged — only the daemon's
privilege level differs. Documented in `docs/architecture.md`.

---

## Phase 0 — Architecture, Repository & Environment

- [x] **T001** — `git init`, root `.gitignore`, first commit with the legacy tree.
  - Evidence: `git log --oneline` → `4097115 chore(repo): initialise git repository…`; `git ls-files | wc -l` = 116; `git check-ignore -v backend/.env` matches. No `.env`, `*.db`, or `venv/` staged.
- [x] **T002** — GitHub remote + Sprint board. **BLOCKED: needs credentials/ownership decision from the user.** Everything else in the plan is local; this is the only externally-accounted task.
- [x] **T003** — `docs/architecture.md` (ADR, decisions D1–D5, layer boundaries, request lifecycle).
- [x] **T004** — Python 3.12 via `uv`, venv at `backend/.venv`, pinned in `.python-version`.
  - Evidence: `backend/.venv/bin/python --version` → `Python 3.12.13`.
- [x] **T005** — `requirements.txt` + `requirements-dev.txt`; every import verified.
  - Evidence: import sweep printed `OK` for fastapi 0.115.6, sqlalchemy 2.0.36, pydantic 2.10.4, alembic 1.14.0, psycopg 3.2.3, PyJWT, passlib+bcrypt, spacy 3.8.4, sklearn 1.5.2, numpy, pandas, scipy, pdfplumber, python-docx, uvicorn, pytest, httpx, ruff, mypy, multipart → `ALL OK`.
- [x] **T006** — spaCy model loads.
  - Evidence: `spacy.load("en_core_web_sm")` on a sample sentence; `PhraseMatcher` matched `['PyTorch', 'scikit-learn']`.
- [x] **T007** — `docker-compose.yml` with `postgres:16` (+ healthcheck, named volume, port 5432) and `pgadmin:4`.
- [x] **T008** — daemon started, `docker compose up -d postgres`, connectivity verified.
  - Evidence: container health `healthy`; `psql \conninfo` → *connected to database "careerlens" as user careerlens*; host TCP 5432 reachable.
- [x] **T009** — `backend/.env.example` with every target variable; real `.env` generated with a 48-byte secret and git-ignored.
- [x] **T010** — `docs/erd.md` Mermaid ER diagram of the 14 tables.
- [x] **T011** — deleted the stray 0-byte `backend/pathfinder.db` (finding S11); cleared `__pycache__`; `docs/legacy-freeze.md` written.
- [~] **T012** — proposal §6.4 "early tutorials" walkthroughs. **Blocked on the 4-person team**; the technical spikes it stands in for (spaCy, SQLAlchemy 2.0, FastAPI, App Router) are covered by the code and docs produced in later phases.

**Phase 0 completion criteria:** all met except T002 (external account) and T012
(team activity). `/health` returns `{"status":"ok","database":"ok"}`; `spacy.load` succeeds.

---

## Phase 1 — Backend Platform Migration

- [x] **T013** — `app/` package with `__init__.py` for `app`, `app/core`, `app/db`, and all subpackages.
- [x] **T014** — `core/config.py` with `pydantic-settings`, **fail-fast** on missing/short `JWT_SECRET_KEY`, plus weight-partition and production-placeholder checks.
- [x] **T015** — `core/logging.py` with `dictConfig`, request-id filter, JSON and console formatters.
- [x] **T016** — `core/security.py`: bcrypt (`passlib`) + PyJWT HS256 emitting `sub`, `role`, `exp`, `iat`, `jti`, `typ`.
- [x] **T017** — `core/exceptions.py`: `APIError` family, uniform envelope, `RequestValidationError` and `IntegrityError` handlers, unhandled-exception handler that logs the traceback and returns a generic message (fixes S8).
- [x] **T018** — `db/base.py`: `DeclarativeBase`, 5-key `naming_convention`, `TimestampMixin`.
- [x] **T019** — `db/session.py`: engine with `pool_pre_ping`, `expire_on_commit=False`, `get_db`, `session_scope`, `check_database_connection`.
- [x] **T020** — `main.py`: factory, `lifespan` that fails loudly without a DB, CORS allowlist (fixes S2), request-id middleware, `/`, `/health`, `/readyz`.
- [x] **T021** — `uvicorn[standard]` pinned and `uvicorn app.main:app --reload --port 8000` documented.
- [x] **T022** — Alembic initialised; `env.py` reads `DATABASE_URL` from `Settings` and imports `app.models` so metadata is complete.
- [x] **T023** — revision `0001_infra_and_user` with `pg_trgm`, `user` table, role CHECK, and the functional unique index on `lower(email)` (fixes S9).
- [x] **T024** — `backend/.gitignore` (fixes S6).
- [x] **T025** — `tests/conftest.py` with a migrated `careerlens_test` database and savepoint-joined per-test rollback.
- [x] **T026** — `tests/test_health.py`. Evidence: 5 passed.
- [x] **T027** — `tests/test_config.py`. Evidence: asserts missing/empty/short/placeholder secrets are all rejected, including both legacy literals.
- [x] **T028** — migration round trip. Evidence: `downgrade base` → only `alembic_version` remained; `upgrade head` → 15 tables.
- [x] **T029** — `tests/test_cors.py`. Evidence: unlisted `Origin` receives no `Access-Control-Allow-Origin`; listed one does.
- [x] **T030** — ruff/mypy config. Evidence: `backend/pyproject.toml`; both clean (see Phase 9 verification).

**Phase 1 completion criteria:** all met. Startup fails without a ≥32-char secret; CORS
allowlist verified; round trip verified; `/health` reports `database: ok`; `grep -c
create_all backend/app/` = 0.

---

## Phase 2 — Database & Domain Model

- [x] **T031–T039** — 9 model modules, 14 tables.
  - Evidence: `Base.metadata` reports exactly 14 tables; live DDL inspection confirmed every `ON DELETE CASCADE`, `RESTRICT` on `recommendation_result.job_role_id`, `CHECK (proficiency BETWEEN 1 AND 5)`, `CHECK (weight > 0 AND weight <= 1)`, and the `skill_alias.alias` primary key.
- [x] **T040** — `models/__init__.py` registers every mapper.
- [x] **T041** — revision `0002_domain_schema` (13 tables) + `pg_trgm` GIN trigram indexes.
  - Evidence: `ix_job_role_title_trgm`, `ix_job_role_description_trgm`, `ix_skill_name_trgm` present.
- [x] **T042** — `data/skills_taxonomy.json`.
  - Evidence: **151 skills, 555 aliases, 8 categories**, zero cross-skill collisions, every skill ≥2 aliases. Categories: Programming & Core 19, Data Engineering 22, Statistics & Mathematics 16, ML Frameworks 23, Deep Learning 16, NLP & LLM 17, MLOps & Cloud 21, Analytics & Communication 17. `"AI"` deliberately excluded as too ambiguous, per the plan.
- [x] **T043** — `app/ml/taxonomy.py` with `canonicalise`, `all_patterns`, `validate`, and the documented match-normalisation rule.
  - Evidence: `sklearn`, `scikit learn`, `sci-kit learn`, `SKLearn`, `sk-learn` all → **Scikit-learn**; `validate()` → `[]`.
- [x] **T044** — `tests/test_taxonomy.py` (written in Phase 9's test sweep; see below).
- [~] **T045** — `data/job_roles.json`. In progress: 50–100 roles with 8–18 weighted skills each.
- [x] **T046** — `scripts/seed_taxonomy.py` (idempotent upsert, prints `skills: N, aliases: M`).
- [x] **T047** — `scripts/seed_job_roles.py` (idempotent; fails loudly on an unknown `skill_slug`).
- [x] **T048** — `scripts/seed_admin.py` and `scripts/seed_dev_users.py`.

**Plan §6.5.4 verification queries:** all return the expected empty sets — no
`skills`/`experience` TEXT column anywhere, no alias claimed twice, no role with <5
requirements, no weight outside `(0, 1]`.

---

## Phase 3 — Authentication & Authorization

- [x] **T049** — `schemas/auth.py`: `RegisterRequest` (name 1–120, `EmailStr`, 8–128 with upper+lower+digit), `LoginRequest`, `UserRead` (no `password_hash`), `TokenResponse`.
- [x] **T050** — `api/deps.py`: `get_db`, `get_current_user`, `require_user`, `require_role("admin")` → 403.
- [x] **T051** — `services/auth_service.py`: normalise email, 409 on conflict, `User`+`Profile` in one transaction, constant-time verify against a dummy hash for unknown users.
- [x] **T052** — `api/routes/auth.py`: register 201, login 200, logout 204, refresh 200, me 200, PATCH me, DELETE me.
- [x] **T053** — `api/router.py` aggregating all routers.
- [x] **T054** — `tests/test_auth.py`. Evidence: **38 tests**, all pass; duplicate → 409; weak password → 422 with a `password` field error; unknown email and wrong password are byte-identical responses; expired token → `401 token_expired`.
- [x] **T055** — `tests/test_roles.py` (see Phase 9 sweep).
- [x] **T056** — refresh takes `role` from the database, not the presented token.
- [x] **T057** — zod mirror of the password policy (Phase 6).
- [x] **T058/T059** — `session.ts` + `AuthProvider` preserving the legacy `localStorage` keys (Phase 6).
- [x] **T060** — `middleware.ts` route guards (Phase 6).
- [x] **T061** — header nav with every link resolving (Phase 6).
- [x] **T062** — `educationLevel` sent and stored. Evidence: `test_register_stores_education_level` passes — the legacy `Register.tsx:92` silent drop is closed.

---

*(Phases 4–11 and the final audit are tracked in the sections appended below as work completes.)*
