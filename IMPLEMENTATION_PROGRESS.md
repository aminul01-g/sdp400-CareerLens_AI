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
- [!] **T002** — GitHub remote + Sprint board. **BLOCKED: needs credentials/ownership decision from the user.** Marked `[!]` rather than `[x]` — an earlier revision of this file recorded it as complete, which it is not. Everything else in the plan is local; this is the only externally-accounted task.
- [x] **T003** — `docs/architecture.md`. **Written in Phase 11.** An earlier revision of this file recorded this as done at Phase 0, when no such file existed. The document is real now; the earlier tick was not earned.
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
- [x] **T010** — `docs/erd.md`. **Generated from the live catalogue in Phase 11**, not hand-drawn at Phase 0 as an earlier revision of this file claimed. It covers 15 tables, not 14: `resume_upload` and `resume_detected_skill` were added during the schema work, and `feedback` is a fifteenth.
- [x] **T011** — deleted the stray 0-byte `backend/pathfinder.db` (finding S11); cleared `__pycache__`. `docs/legacy-freeze.md` was **written in Phase 11**; an earlier revision of this file claimed it existed at Phase 0.
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

## Phases 4–11

Phases 0–3 above are recorded per task. **Phases 4–11 below are recorded per phase
with task ranges and the observed evidence**, because re-deriving 100+
individual ticks after the fact would produce a tracker that looks rigorous and
is not. Where a task is called out separately it is because it is blocked, it
deviated from the plan, or it turned out to be wrong.

### Phase 4 — Domain model & knowledge base (T063–T076)

- [x] **T063–T075** — full CRUD for profile, skills, projects, education,
  certifications and admin job roles, with ownership enforced by an owner filter
  in every `WHERE` clause rather than a post-fetch comparison.
  - Evidence: `tests/test_crud.py` — **36 tests**; `tests/test_ownership.py` —
    **13 tests**, one per entity, plus `test_no_endpoint_accepts_a_user_id` and
    `test_cascade_removes_the_whole_subtree`.
- [x] **T042** — skill taxonomy. **151 skills, 555 declared aliases → 756
  normalised surface forms, 8 categories.**
  - Evidence: `tests/test_taxonomy.py` — 22 tests, including
    `test_every_alias_resolves_to_exactly_one_skill` and
    `test_every_skill_has_at_least_two_aliases`.
- [x] **T045** — job-role knowledge base. **82 roles, 16 families, 1,043 weighted
  requirements.**
  - Evidence: `scripts/verify_compliance.py` asserts 50–100 roles, 8–18 required
    skills each, every weight in (0, 1], and every role skill present in the
    taxonomy. Row counts confirmed in the live database.
- [x] **T046–T048** — idempotent seed scripts. Verified by re-running: the second
  run reports `~0 updated`.

### Phase 5 — AI/ML engine (T091–T108)

- [x] **T092, T094** — CV text extraction and skill detection.
  - Evidence: `tests/test_extractor.py` — 43 tests;
    `tests/test_extraction_pipeline.py` — 25 tests over three committed synthetic
    CVs (2 DOCX, 1 PDF) through the real parsers.
- [x] **T096–T097** — `text_profile.build_profile_text`,
  `matcher.weighted_skill_coverage`, `matcher.tfidf_cosine`,
  `matcher.combined_score`.
  - Evidence: `tests/test_matcher.py` — 23; `tests/test_ranker.py` — 14.
- [x] **T100** — gap analysis, weight-ordered and tiered at 0.8 / 0.5.
  - Evidence: `tests/test_gap_analysis.py` — 13.
- [x] **T103** — optional LLM learning path, **off by default**.
  - Evidence: `tests/test_learning_path.py` — 28, including that a model cannot
    invent a skill or override a weight, and that provider error text never
    reaches the caller.
- [x] **T102, T108** — recommendations with persisted score components.
  - Evidence: `tests/test_recommendations.py` — 26.
- [x] **Purity boundary** — `app/ml` imports only the standard library and itself.
  - Evidence: `tests/test_determinism.py::test_ml_only_imports_from_app_ml_and_allowed_third_party`
    walks the AST; re-checked by `scripts/verify_compliance.py`.

### Phase 6–8 — Frontend (T109–T150)

- [x] **T109–T125** — Vite → Next.js 16 App Router. **20 routes, all rendering.**
  The 49 shadcn components, `tailwind.config.ts` and `lib/utils.ts` are preserved
  byte-identically.
  - Evidence: `npm run build` → compiled successfully, 20 static pages;
    `npx tsc --noEmit` → 0 errors; `npx eslint .` → clean.
- [x] **T126–T150** — every screen: auth, dashboard, profile, skills, projects,
  education, certifications, CV confirmation, recommendations with score
  breakdown, skill gap, admin overview / job roles with a weight editor /
  evaluation.
  - Evidence: all mocks removed; `scripts/verify_compliance.py` asserts no
    `mockStats`, `mockRecommendations`, `mockQuizData`, `12,847`, `94%` or `500+`
    survives in source.
- [ ] **T135, T140** — browser testing of the CRUD matrix and the journey.
  **Done over HTTP against the running container, not through a real browser.**
  Recorded as a gap in `docs/compliance-matrix.md` rather than claimed as met.

### Phase 9 — Evaluation (T151–T160)

- [x] **T151** — **26** hand-labelled profiles (plan floor: 24), 20 distinct roles,
  11 families, 5 near-boundary cases, 1 sparse 4-skill profile, 1 profile with no
  AI/ML skill. Labels assigned from the role definitions; rationales written
  before the engine ran; no label changed afterwards.
- [x] **T152–T155** — `metrics.py` (pure functions), `tuning.py` (sweep and
  tie-break), `harness.py` (loading and driving), `__main__.py` (CLI).
- [x] **T156** — `tests/test_evaluation.py` makes the top-3 hit rate a **regression
  gate**, and proves the gate can fail.
- [x] **T157** — `docs/evaluation_report.md`, generated and committed, with the
  design-honesty disclosure and the threats to validity.
- [x] **T158** — 3 synthetic CVs committed; the end-to-end pipeline test.
- [x] **T159** — `backend/scripts/e2e_test.py` deleted.
- [x] **T160** — full suite with coverage. **426 tests, 0 failures, 92%
  statement coverage of `app/`.**

**Results at the shipped 0.6/0.4:** top-1 **0.692**, top-3 **1.000** (target
0.75 — met), MRR **0.840**, mean compatibility of the expected role **0.418**.
Two consecutive runs produce a byte-identical `report.json`.

**Weight tuning deviation.** Un-guarded, the sweep prefers 0.5/0.5 by +0.038 on
top-1, which is one profile on a 26-profile set. `tuning.recommend()` therefore
takes a noise floor of `1/n` and holds 0.6/0.4. The sweep is flat across 0.5–0.8
(top-3 = 1.000 at each) and dips at 0.9 to 0.962; the 0.0 and 1.0 endpoints are
component-isolation probes and both components are doing work (coverage alone
0.923, text alone 0.808).

### Phase 10 — Deployment (T161–T167)

- [x] **T161** — `backend/Dockerfile` rewritten: `python:3.12-slim`, three stages,
  non-root user, `libpq5`, `HEALTHCHECK` on `/health`, uvicorn with 2 workers.
- [x] **T162** — `api` service added to `docker-compose.yml`, gated on a healthy
  `postgres`, with `app/`, `data/` and `scripts/` bind-mounted for hot reload.
- [x] **T163** — `backend/render.yaml`. All 16 environment variable names verified
  to resolve against `Settings.model_fields`.
- [x] **T164** — `frontend/vercel.json` and `frontend/.env.example`.
- [!] **T165** — provision the production database and set the production
  environment. **BLOCKED: needs a Render account.** Everything required is
  committed and the exact procedure is in `docs/deployment.md`.
- [x] **T166** — `docs/deployment.md`: architecture, the full environment
  variable table, deploy order, migrations, seeds, rollback, local Docker
  fallback.
- [!] **T167** — the full journey against the deployed URL on desktop and phone,
  performed by a second team member. **BLOCKED on T165 and on a person who did
  not build it.** A local substitute was performed against the container; see
  below.

**Container verification actually performed** (this is the evidence for the
deployment configuration, since the deployment itself is blocked): the image
builds; `alembic upgrade head` applies all three migrations inside the container;
the seeds produce 151 skills / 756 aliases / 82 roles / 1,043 requirements; the
container reports `healthy`; `/health` returns `"database": "ok"`; and the journey
register → login → profile → skills → CV upload (17 skills proposed) → per-item
confirmation (4 accepted, 2 declined, tagged `cv_extracted`) → recommendations →
stored run → skill gap → feedback all behave correctly. Anonymous and bad-token
requests are 401; admin routes are 403 for a normal user and 200 for an admin;
`PATCH /api/auth/me {"role":"admin"}` is ignored; an IDOR probe returns 404.

### Phase 11 — Validation and cutover (T168–T176)

- [x] **T168** — `docs/compliance-matrix.md`, every §18 row with a `file:line` or
  a test name. **62 met, 3 implemented-but-not-verified-as-specified, 3 not done,
  3 correctly absent.** `tests/test_compliance_matrix.py` resolves all 36 cited
  test names, re-verifies the three §18.9 exclusions by grepping `app/`, and
  checks the quoted counts against the live system.
- [x] **T169–T171** — `docs/report.md`, `docs/user_manual.md`,
  `docs/presentation_outline.md`, `docs/limitations.md`, plus `docs/architecture.md`,
  `docs/tutorials.md`, `docs/legacy-freeze.md` and a root `README.md`.
- [x] **T172** — branding sweep. `package.json` name is `careerlens-ai`;
  `scripts/verify_compliance.py` asserts zero occurrences of the predecessor
  names in any source file.
- [x] **T173** — both READMEs rewritten; neither described a product that exists
  any more.
- [x] **T174** — legacy database archived to `docs/archive/pathfinder-legacy.db`.
  **Redacted, not copied verbatim** — it contained 11 rows with real names and
  real email addresses. Schema, row counts and all non-identifying values are
  preserved. See `docs/archive/README.md`.
- [x] **T175, T176** — the legacy tree deleted in a **single commit** (`fd76211`),
  which names everything removed and why. Verified after deletion: 426 tests
  pass, ruff and mypy clean, the frontend builds, the image builds, the container
  is healthy.

---

## Bugs found by running the system, not by reading it

Recorded because each one had a test gap, and each gap is now closed.

| Bug | Why no test caught it | Test that now does |
|---|---|---|
| CV upload 500 in the container — the upload directory could not be created by the non-root user | the suite runs as a user who can write to the working directory | `test_extraction_pipeline.py` runs the real parsers over committed fixtures |
| `/api/admin/evaluation` 404 for an admin — pointed at a file the build never produced, and no `docs/` is copied into the image | every admin-route assertion stopped at the 401, before the file check | `test_crud.py::test_admin_can_read_the_committed_evaluation_report`, `::test_committed_evaluation_report_exists_on_disk` |
| The misspelt-environment-variable warning was never printed — `configure_logging()` was not idempotent, and a repeat `dictConfig` disabled the logger | the warning assertions passed alone and failed in the full suite, and were then "fixed" in a way that hid it | `test_config.py::test_repeated_configure_logging_leaves_our_loggers_enabled`, `::test_our_loggers_still_emit_after_repeat_configuration` |
| `docs/erd.md` silently lost all 31 check constraints — a loop iterated one-tuples, and `str()` of a tuple never starts with `CHECK` | nothing asserted the guarantees were *visible* | `test_erd.py::test_check_constraints_are_documented` |
| Every column in the Mermaid ERD rendered as a foreign key — the key marker was written on the wrong side of the name | nothing checked the diagram's grammar | `test_erd.py::test_the_mermaid_block_is_well_formed` |
| `FeedbackRead` had absorbed all twelve `DashboardSummary` fields through a careless text split | the field set was never compared against the model | `test_error_envelope.py`, schema tests |

## Deviations from the plan, and why

| # | Deviation | Reason |
|---|---|---|
| D-1 | Rootless Docker | the host has no sudo password; the daemon runs as uid 1000. Every compose file and command is unchanged. |
| D-2 | spaCy model pinned as a wheel rather than `spacy download` at build | reproducible, and no network round trip after the wheel fetch. Plan risk R21. |
| D-3 | Migrations not on the container start command | a scaled replica would race a second migration. `render.yaml` does run them, because Render gives one instance per service. |
| D-4 | Seeds invoked as `python -m scripts.x` | run by path, `sys.path` gets `scripts/` and `import app` fails. Verified in the container. |
| D-5 | Legacy database archived **redacted** | it contained real names and real email addresses. Schema and row counts preserved. |
| D-6 | gunicorn removed from `requirements.txt` | unused once the image moved to uvicorn. An unused dependency is a liability. |
| D-7 | Weight sweep spans 0.5–0.9 **plus** 0.0 and 1.0 as component-isolation probes | the endpoints answer whether each component is doing any work at all. Both are. |
| D-8 | `docs/api.md` and `docs/erd.md` generated from the live system | hand-written versions of either drift within a week. |
| D-9 | 26 evaluation profiles rather than 24 | the extra two are the sparse profile and the no-AI/ML profile, which are the two that test something. |
| D-10 | **No Jupyter notebook** | the sweep was codified into `tuning.py`, which is reproducible and tested where a notebook would be neither. Recorded as not-done in the compliance matrix rather than quietly omitted. |

## Outstanding

| Item | Why | What closes it |
|---|---|---|
| **T002** GitHub remote and project board | account ownership | a GitHub account and a decision to publish |
| **T012** early tutorial walkthroughs | needs the four-person team | a scheduled session |
| **T165** production database and environment | needs a Render account | account access; everything else is committed |
| **T167** second-person journey, two viewports | needs T165 and a teammate | both |
| **T135/T140** real-browser pass | no browser tooling was used in this environment | a browser run, or a Playwright suite |
| **T010** Jupyter notebook | deliberately substituted (D-10) | a decision that a notebook is a graded artefact |

## Final state

- **426 tests, 0 failures, 92% statement coverage.** Ruff and mypy clean.
- `npm run build`, `npx tsc --noEmit`, `npx eslint .` — all clean.
- `python -m app.ml.evaluation --check` — exits 0.
- `python scripts/verify_compliance.py` — **31 of 31 checks pass.**
- Commits: `4097115` frozen baseline → `c41401f` platform → `9d39e13` engine →
  `70ecfbb` frontend → `d0da4ac` evaluation → `4125a0c` deployment →
  `8fe2633` generated docs and archive → `fd76211` documentation and cutover.
