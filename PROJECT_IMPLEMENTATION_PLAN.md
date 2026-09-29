# CareerLens AI — Implementation Plan

**Project:** CareerLens AI — An AI-Powered Job & Career Recommendation System
**Course:** SDP400 — Software Development Project, BUBT
**Supervisor:** Md. Masudul Islam, Assistant Professor, Dept. of CSE
**Plan date:** 29 September 2026
**Repository:** `/home/aminul/Development/sdp400`
**Source of truth:** `CareerLens_AI_Project_Proposal.docx` + `PROJECT_CODEBASE_ALIGNMENT_ANALYSIS.md`

> **What this document is.** A dependency-aware engineering execution plan. It answers: what to
> build, in what order, which existing code survives, which is replaced, which files are created or
> modified, how the four layers connect, and how every proposal requirement is verified as met.
>
> It is written to be executed top-to-bottom in a coding agent without re-deriving the architecture.
> Every file path below was verified against the live repository on 29 September 2026.

---

## Table of Contents

| § | Section |
|---|---------|
| 0 | Verified Repository State & Corrections to the Analysis |
| 1 | Executive Summary |
| 2 | Current → Target Architecture |
| 3 | Migration Strategy |
| 4 | Implementation Phases |
| 5 | Detailed Task Breakdown |
| 6 | Database Implementation Plan |
| 7 | Backend API Plan |
| 8 | CRUD Plan |
| 9 | AI/ML Implementation Plan |
| 10 | AI Evaluation Plan |
| 11 | Frontend Implementation Plan |
| 12 | User Journey |
| 13 | Admin Journey |
| 14 | File-Level Implementation Map |
| 15 | Dependency Graph |
| 16 | Six-Sprint Development Plan |
| 17 | Risk Management |
| 18 | Proposal Compliance Matrix |
| 19 | Definition of Done |
| 20 | Recommended Development Order |
| 21 | Final Implementation Checklist |

---

## 0. Verified Repository State & Corrections to the Analysis

The alignment analysis is treated as the foundation, not as infallible. Every structural claim in
this plan was re-verified by direct inspection on 29 September 2026. Four material corrections
and eight environment facts are recorded here so no downstream task inherits a bad assumption.

### 0.1 Corrections to `PROJECT_CODEBASE_ALIGNMENT_ANALYSIS.md`

| # | Analysis claim | Verified reality | Impact on this plan |
|---|---|---|---|
| C1 | §5.1: "`Header.tsx` contains **no links** to `/dashboard`, `/quiz`, or `/recommendations` — only `/login` and `/register`" | **Incorrect.** `Header.tsx:44-49` defines `userNavLinks` = Dashboard, Quiz, Recommendations, Feedback; `:57` selects it when `isAuthenticated`; `:76` and `:146` render it in desktop and mobile menus. | The defect is narrower and different: `App.tsx:28` passes only `isAuthenticated` and `userEmail`, **never `isAdmin`**, so `adminNavLinks` (`Header.tsx:51-55`) is unreachable. Additionally `Header.tsx:101,106,170,179` navigate to `/profile`, `/admin`, `/admin/analytics`, `/admin/questions` — **none of which are routes** (`App.tsx:75-123`), so the authenticated user menu contains four dead links. The plan rewrites nav, it does not "add" it. |
| C2 | §1.2 / §14.1: "46 components in `frontend/src/components/ui/`" | **49 files** in `src/components/ui/`. | Minor. Reuse count corrected. No structural change. |
| C3 | §3.4: "duplicate database file… `backend/pathfinder.db` (0 bytes)" | Confirmed present and 0 bytes. `backend/instance/pathfinder.db` is 32 KB and live. | Delete in Phase 0. |
| C4 | Implicit throughout: repo is under version control | **The repository is not a git repository.** `git status` → `fatal: not a git repository (or any parent up to mount point /)`. `frontend/.gitignore` exists; there is no root `.gitignore` and no `.git`. | **`git init` is task T001 and blocks everything.** Six-sprint agile work (§5 of the proposal) requires a shared backlog and history, and §8 of the proposal assumes a repository. Without this, the deletion tasks in Phase 11 are unrecoverable. |

### 0.2 Verified environment facts (probed 29 September 2026)

| Fact | Value | Consequence for the plan |
|---|---|---|
| Python | `3.14.7` at `/usr/bin/python3`; **no** `python3.12`/`python3.13` on PATH; no `pyenv`, no `conda` | System Python is not the target interpreter. See E1. |
| Package resolver | `uv` present at `/home/aminul/.local/bin/uv` | Provides the version-pinned interpreter and venv in T004. |
| PostgreSQL | **Not installed.** No `psql`, `pg_ctl`, `postgres`, no `/usr/lib/postgresql`. | Must be provisioned. See E2. |
| Root access | uid 1000, `sudo -n true` → "a password is required" | Cannot `apt install postgresql`. See E2. |
| Docker | CLI at `/usr/bin/docker`; Compose v5.5.0 present; **daemon not running** (`dial unix /var/run/docker.sock: no such file or directory`) | Compose is the chosen path but requires a manual daemon start. See E2/R1. |
| pgAdmin | Not installed | Runs as a second Compose service. |
| Node | `v26.7.0`, `npm 12.0.2`, `bun` on PATH | Meets Next.js 16 requirement `node >= 20.9`. |
| Network | `pypi.org` reachable (HTTP 200) | Dependency installation is not blocked. |
| ML wheel coverage | `spacy 3.8.16` → cp310–**cp314**; `thinc 8.3.9`–`8.3.13` → cp310–**cp314**; `thinc 9.0.0+` → **cp39–cp312 only**; `scikit-learn 1.9.1` → cp311–cp315 | See E1. |
| Installed stack | `requirements.txt` = Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Admin, APScheduler, requests, python-dotenv, gunicorn, flask-cors. No ML, no PDF/DOCX, no pytest, no Pydantic. | All ML/API/test dependencies are greenfield. |

### 0.3 Reusable assets (re-verified, with the exact reason each survives)

| Asset | Location | Why it survives the migration |
|---|---|---|
| shadcn/ui kit — 49 components | `frontend/src/components/ui/` | Plain React + Radix + Tailwind. No Vite, no React Router, no `import.meta.env`. Imports resolve only through the `@/` alias, which Next.js supports natively. |
| `cn()` helper | `frontend/src/lib/utils.ts` | `clsx` + `tailwind-merge`; framework-agnostic. |
| Tailwind design system | `frontend/src/index.css:1-136`, `frontend/tailwind.config.ts` | CSS custom-property tokens. **Already Next.js-ready:** `tailwind.config.ts` `content` globs include `"./app/**/*.{ts,tsx}"` and `"./pages/**/*.{ts,tsx}"` alongside `"./src/**/*.{ts,tsx}"`. The Next.js `app/` directory is already in the content scanner, so **the Tailwind config needs no content edits** — only the stylesheet import moves. |
| API error-enrichment pattern | `frontend/src/api/client.ts:20-29` | Throws an `Error` with `.status` and `.body` attached. Correct shape; ported into the typed client. |
| React Query provider | installed (`package.json:42`), mounted at `App.tsx:70` | Already a dependency and already wrapped. Server-state fetching needs no new library. |
| `recharts` | `package.json:57` | Installed; used for the admin evaluation view. |
| `zod`, `react-hook-form`, `@hookform/resolvers` | `package.json:41,61,14` | Installed; used for client-side form validation mirroring the Pydantic schemas. |
| Auth domain logic | `backend/auth.py:13-17,31-32,42-43` | Hashing + token issuance semantics port directly. Only the framework wrapper changes. |
| Feedback validation pattern | `backend/guidance.py:107-128` | Aggregated error list is the right shape; re-expressed as Pydantic field errors. |
| Upload mechanics | `backend/guidance.py:17-20` | UUID-prefixed filename + configured upload folder. The storage step works; only processing is missing. |

### 0.4 Assets that are discarded

| Asset | Location | Reason |
|---|---|---|
| All Flask runtime | `backend/app.py`, `auth.py`, `guidance.py`, `extensions.py`, `admin.py`, `tasks.py`, `utils.py`, `models.py` | Framework replaced wholesale. **Frozen, not deleted, until T176** (cutover). |
| Flask-Admin panel | `backend/admin.py:40-54` | Mounted with no `is_accessible` override at `app.py:27` → `/admin/` is publicly reachable and lists `user.email` and `user.password_hash`. The proposal requires an *in-app* admin panel (§6.3 "one panel"), which Flask-Admin is not. Removed at cutover. |
| APScheduler job | `backend/tasks.py:1-17` | Out of proposal scope. Removed. |
| LLM recommendation path | `backend/guidance.py:45-61` | Violates proposal §4.2 — makes an LLM load-bearing, is a self-described placeholder, defaults to a hardcoded string (`:48`), and leaks provider error text to the client (`:59`). Replaced by the deterministic engine. |
| Career quiz | `frontend/src/pages/Quiz.tsx` (372 lines) | Proposal §4.1 lists nine modules; a quiz is not one. Data is hardcoded (`Quiz.tsx:21`) and submission only navigates (`:194`). Removed. |
| Mock statistics | `Dashboard.tsx:70-75` (`totalUsers: "12,847"`, `successRate: "94%"`) and `Recommendations.tsx:24-…` | Fabricated product data. Replaced with real aggregates. |
| Feedback + analytics endpoints | `backend/guidance.py:73-148` | Not in proposal §4.1. The feedback **UI** is cheap to keep and harmless; the analytics event table is dropped. Decision recorded in §14. |

---

## 1. Executive Summary

### 1.1 The situation in one paragraph

The repository contains **Pathfinder**, a Flask + SQLite + Vite career-quiz application, with
approximately 468 lines of backend application code, 10 routes, 6 models, and **zero** update or
delete operations. The proposal defines **CareerLens AI** on FastAPI + PostgreSQL + Next.js with
scikit-learn + spaCy. The two stacks share no runtime, no data model, and no API contract. The
present code is a competent starter skeleton, not a partial implementation of the proposal.

### 1.2 What must be true when this plan is finished

1. A user can register, build a normalized profile (skills with proficiency, projects, education,
   certifications), optionally upload a PDF/DOCX CV, and receive a **ranked list of AI/ML job
   roles with an explainable compatibility percentage** and a **skill-gap report ordered by
   importance weight**.
2. The ranking is produced by **weighted skill coverage + TF-IDF cosine similarity** — transparent,
   deterministic, CPU-only, no external API. No trained classifier, exactly as proposal §4.2 states.
3. An administrator maintains the knowledge base — job roles, their required skills, and their
   importance weights — through a real in-app panel with full CRUD.
4. Every CRUD operation required by proposal §4.1 is reachable **from the web UI**, not just the API.
5. The engine is validated on **24 hand-labelled profiles** with a reproducible harness and a
   committed report.
6. The whole system is deployed: frontend, API, and a real PostgreSQL database.

### 1.3 The five decisions that determine the schedule

| # | Decision | Resolution | Consequence if deferred |
|---|---|---|---|
| D1 | Stack mismatch | **Option A — conform to the proposal.** Replace Flask→FastAPI, SQLite→PostgreSQL, Vite→Next.js. | Blocks the schema design, which blocks the ML layer, which blocks everything. |
| D2 | Frontend scope | **Full Next.js rewrite.** Keep the 49 shadcn components, Tailwind theme, and React Query. | Proposal §7.2 says "React / Next.js"; §4.3 requires a deployed web app. Staying on Vite contradicts the submitted document. |
| D3 | PostgreSQL | **Docker Compose** (`postgres:16` + `pgadmin:4`), user starts the daemon once. | Verified: nothing else is installable without a sudo password. Blocks Sprint 1 entirely. |
| D4 | Legacy code | **Freeze, then delete at cutover** (T176). | Deleting early loses the auth logic and form validation as reference. |
| D5 | Python interpreter | **Pin 3.12** via `uv` for the backend venv. | See E1 below. |

### 1.4 Environment note E1 — why Python 3.12 and not the system 3.14

`spacy 3.8.16` publishes cp314 wheels, and `thinc 8.3.9`–`8.3.13` also publish cp314 wheels — but
`thinc 9.0.0` and later publish **cp39–cp312 only**. spaCy 3.8.16 declares `thinc >=8.3.4,<9.3.0`, and
`thinc 9.1.1` sits inside that range, so a fresh resolver on Python 3.14 will prefer the newest
satisfied version and attempt to build `thinc 9.1.1` **from source** — a multi-minute Rust/Cython
compile that commonly fails on first run. Pinning the interpreter to 3.12 removes the entire class
of problem: every wheel in the stack (spaCy, thinc 8.3.x, scikit-learn, numpy, pandas, psycopg)
publishes cp312 binaries. Task T004 does this; it is not optional polish.

### 1.5 Effort and critical path

The proposal budgets **516 man-hours across 5 stages and 4 members** (§8) — about 129 hours per
member over 12 weeks, ~11 hours per member per week. §16 of this plan maps that onto the proposal's
own six two-week sprints (§5) without adding scope.

**Critical path (cannot be parallelized):**

```text
git init + environment  →  normalized schema  →  auth  →  CRUD APIs
        →  taxonomy + job KB  →  matcher + gap  →  recommendation API
        →  frontend integration  →  evaluation  →  deployment
```

Everything else (marketing pages, education CRUD, certifications UI, feedback, docs) is
parallelisable and can be absorbed by whichever pair is free.

**Highest-leverage sequencing insight:** the schema decision blocks the most work — the ML layer,
every CRUD router, the admin panel, and the recommendation UI all fork off it. Resolve §6 completely
before writing any router.

### 1.6 What this plan deliberately does not do

- **No trained classifier.** Proposal §4.2 explicitly declines it for lack of labelled data and
  requires that the choice be disclosed. This plan implements the specified unsupervised + rule-based
  engine and says so in the report.
- **No RAG chatbot, no embeddings, no OCR.** Proposal §4.4 and §11 place these in Future Works.
- **No employer accounts, applications, chat, or payments.** Proposal §4.4 out of scope.
- **LLM stays optional** (`ml/learning_path.py`), behind a feature flag, off the critical path, and
  never a dependency of any core endpoint. Proposal §4.2: "The core features work without it."
- **No new frontend state library.** React Query is already installed and already mounted.

---

## 2. Current → Target Architecture

### 2.1 Current architecture (verified)

```text
User
  ↓
Vite SPA — frontend/src, dev port 8080 (vite.config.ts)
  ├─ main.tsx:1-5 → App.tsx
  ├─ App.tsx:23   QueryClient created; :70 QueryClientProvider mounted
  ├─ App.tsx:74-124 BrowserRouter, 10 routes, NO guards
  ├─ App.tsx:26-34 PublicLayout  ─┐
  ├─ App.tsx:37-45 AuthenticatedLayout ─┴─ byte-for-byte identical
  └─ api/client.ts:3-29  fetch() wrapper, token from localStorage
  ↓  fetch → import.meta.env.VITE_API_BASE_URL
       .env           → http://127.0.0.1:5001
       .env.development → http://localhost:5000        ← the two disagree
Flask app — backend/app.py, port 5000 (app.py:60)
  ├─ :18  CORS(app)              — no origins allowlist
  ├─ :19  SECRET_KEY 'dev-secret'      — weak fallback
  ├─ :20  DATABASE_URL sqlite:///./pathfinder.db
  ├─ :22  JWT_SECRET_KEY 'jwt-secret'  — weak fallback
  ├─ :27  admin.init_app(app)     — NO is_accessible → /admin/ is public
  ├─ :42  auth_bp     → auth.py:8,34,45
  ├─ :43  guidance_bp → guidance.py:9,31,39,73(×2),93,151
  ├─ :46  db.create_all()  — never ALTERs; schema change = data loss
  └─ :49  APScheduler → tasks.py:4-9 → print() to stdout
```

### 2.2 Target architecture

```text
                            ┌──────────────────────┐
                            │       User           │
                            └──────────┬───────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │  Next.js 16 (App Router, RSC +      │
                    │  client components) — frontend/       │
                    │  • route groups (public)/(app)/(admin)│
                    │  • route guards via middleware.ts     │
                    │  • TanStack Query for server state    │
                    │  • 49 shadcn/ui components (unchanged)│
                    └───────────────┬──────────────────────┘
                                    │
                          REST /api/* + JWT Bearer
                                    │
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  FastAPI — backend/app/                │
                    │  api/routes/*  (thin, HTTP only)       │
                    │  api/deps.py    (get_current_user,     │
                    │                  require_role("admin"))│
                    │  schemas/*      (Pydantic v2)          │
                    │  services/*     (orchestration)        │
                    │  ml/*           (extractor, matcher,   │
                    │                  gap_analysis, ranker) │
                    └───────┬──────────────────────┬────────┘
                            │                      │
            ┌───────────────┘                      └──────────────┐
            ▼                                                     ▼
  ┌───────────────────────────┐                     ┌──────────────────────────┐
  │  PostgreSQL 16            │                     │  AI/ML layer (CPU-only)  │
  │  ─────────────────────    │                     │  ──────────────────────  │
  │  user                     │                     │  data/skills_taxonomy    │
  │  profile                  │                     │    ≈150 skills + aliases │
  │  skill        ─┐          │                     │  data/job_roles.json     │
  │  skill_alias  │          │                     │    50–100 roles + weights│
  │  user_skill  ─┘          │                     │  ml/text_loader          │
  │  project                 │                     │    PDF/DOCX → text       │
  │  education_record        │                     │  ml/extractor            │
  │  certification           │                     │    spaCy PhraseMatcher    │
  │  resume_upload           │                     │  ml/matcher              │
  │  resume_detected_skill   │                     │    weighted coverage     │
  │  job_role       ─┐       │                     │    + TF-IDF cosine       │
  │  job_role_skill ─┘       │                     │  ml/gap_analysis         │
  │  recommendation_run   ─┐ │                     │    required − present    │
  │  recommendation_result ─┘│                     │  ml/ranker               │
  └───────────────────────────┘                     │  ml/evaluation/*         │
                                                    └──────────────────────────┘
```

### 2.3 Layer contracts

The four layers communicate through exactly three boundaries. Nothing crosses them directly.

| Boundary | Contract | Enforced by |
|---|---|---|
| Browser → API | JSON over HTTPS; `Authorization: Bearer <jwt>`; error envelope `{detail, errors[]}` | Pydantic response models; `api/deps.py` |
| API → Database | SQLAlchemy 2.0 ORM `Session`; unit of work per request | `app/db/session.py` dependency |
| API → ML | Pure functions over plain Python dataclasses. **The ML layer never imports SQLAlchemy or FastAPI.** | Type signatures in `app/ml/types.py` |

**The third boundary is the important one.** `app/ml/*` takes dataclasses and returns dataclasses.
That is what makes the engine testable without a database, deterministic enough to evaluate, and
replaceable without touching routes. The existing codebase violates this — `guidance.py:39-71`
builds a prompt, makes an HTTP call, parses a response, catches exceptions, and persists to the
database inside a single route handler.

### 2.4 Request lifecycle (target), end to end

```text
POST /api/recommendations  (Bearer <jwt>)
 1. api/deps.get_current_user      → decode JWT, load User, 401 if absent/invalid
 2. api/deps.require_user          → 403 if suspended
 3. schemas.RecommendationRequest  → Pydantic validation, 422 on failure
 4. services.recommendation_service.generate(user_id)
      a. load Profile, UserSkill[], Project[], EducationRecord[]  (1 query set)
      b. load active JobRole[] + JobRoleSkill[]                    (1 query set)
      c. build profile_text from (a)
      d. ml.ranker.rank(profile_text, user_skill_ids, roles)       ← pure
      e. persist RecommendationRun + RecommendationResult rows
 5. return schemas.RankedRecommendationResponse
```

Steps 4a–4b are the only database access. Step 4d is pure computation. Step 4e is the only write.
This split is what makes T104 (matcher unit test) and T151 (evaluation harness) possible without
booting the API.

---

## 3. Migration Strategy

### 3.1 Principles

Three rules govern every migration decision below.

1. **The proposal wins.** Where the existing code and proposal §7.2 disagree, proposal §7.2 wins.
   The submitted document is the grading artifact.
2. **Never rewrite for its own sake.** A rewrite is justified only when the existing artifact
   cannot satisfy the requirement under the target stack. This is why 49 shadcn components, the
   Tailwind theme, and `cn()` survive untouched while all eight Flask modules do not.
3. **Strangler, not big-bang.** The new stack is built alongside the old one. The old one stays
   runnable until the new one passes the CRUD demo. Nothing is deleted before it is replaced
   (D4).

### 3.2 Backend: Flask → FastAPI → SQLAlchemy → Pydantic → PostgreSQL

```text
BEFORE                                  AFTER
──────────────────────────────          ──────────────────────────────
Flask                    app.py         uvicorn + FastAPI   app/main.py
Flask-SQLAlchemy   flask_sqlalchemy    SQLAlchemy 2.0      app/db/session.py
                                           (DeclarativeBase, Session)
Flask-JWT-Extended flask_jwt_extended   PyJWT               app/core/security.py
flask-jwt_extended @jwt_required()      FastAPI Depends    app/api/deps.py
None                     —              Pydantic v2         app/schemas/*.py
blueprint_bp  auth.py, guidance.py      APIRouter           app/api/routes/*.py
inline logic  guidance.py:39-71         service layer       app/services/*.py
None                     —              pure ML layer       app/ml/*.py
db.create_all()  app.py:46              Alembic             backend/alembic/
sqlite:///./pathfinder.db               postgresql+psycopg  app/core/config.py
werkzeug hashing                        passlib[bcrypt]     app/core/security.py
Flask-Admin      admin.py               FastAPI admin API   app/api/routes/admin.py
                                          + Next.js UI       frontend/app/(admin)/jobs/
APScheduler      tasks.py               — removed
```

#### 3.2.1 Step-by-step

| Step | Action | Detail |
|---|---|---|
| B1 | Create `backend/app/` package | The legacy flat modules stay at `backend/*.py` and keep working. `app/` is imported as `app.main:app`. |
| B2 | Settings via `pydantic-settings` | `app/core/config.py` reads `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `UPLOAD_DIR`, `ALLOWED_ORIGINS`, `SKILL_COVERAGE_WEIGHT`, `TFIDF_WEIGHT`, `LLM_ENABLED`. **Fail fast at import if `JWT_SECRET_KEY` is missing or shorter than 32 chars** — fixes S7 (`app.py:19,22` weak fallbacks) properly rather than by replacing one default with another. |
| B3 | SQLAlchemy 2.0 | `DeclarativeBase`, `Mapped[]` / `mapped_column()` typed annotations, `sessionmaker` with `expire_on_commit=False`. A FastAPI `get_db` dependency yields a session per request and rolls back on exception. |
| B4 | Alembic from day one | `app.py:46` `db.create_all()` is the root cause of "schema change = drop the database = lose all 11 users". Alembic is initialized in Phase 1, before the first domain table exists, so no table is ever created outside a revision. |
| B5 | Pydantic v2 everywhere | Separate `*Create` / `*Update` / `*Read` models. `*Update` fields are `Optional[...] = None` so PATCH-style partial updates work; the router distinguishes "absent" from "explicit null" via `model_fields_set`. Error envelope: FastAPI's default `422` with `detail[]`, plus a custom handler that adds a `code`. |
| B6 | `APIRouter` per domain | One file per domain under `app/api/routes/`, each with `prefix=` and `tags=`. Routers contain HTTP concerns only: auth dependency, schema validation, service call, status code. No business logic. |
| B7 | Auth rewrite | PyJWT HS256, explicit `exp`/`iat`/`sub`/`role` claims, `ACCESS_TOKEN_EXPIRE_MINUTES` default 1440. `require_role("admin")` replaces the one-off inline check at `guidance.py:157-163` and covers every admin route. |
| B8 | PostgreSQL retarget | Only the URL changes; the ORM layer is already database-agnostic. PostgreSQL additionally *enforces* the FKs SQLite never enforced (fixes S10) and gives real `NUMERIC(3,2)` weights and `TIMESTAMPTZ`. |
| B9 | CORS restricted | Fixes S2 (`app.py:18` `CORS(app)` with no allowlist). Origins come from `ALLOWED_ORIGINS`, defaulting to `http://localhost:3000`. |
| B10 | Error envelope | `app/core/exceptions.py`: one `APIError` base, handlers for `APIError`, `RequestValidationError`, and `IntegrityError` → `409`. No raw exception text ever reaches a response (fixes S8, `guidance.py:59`). |

#### 3.2.2 What is ported vs. reimplemented

| Legacy code | Disposition | Note |
|---|---|---|
| `auth.py:13-17` `set_password`/`check_password` | **Reimplemented** on `passlib[bcrypt]` | Werkzeug's PBKDF2 is fine but not portable to FastAPI's ecosystem; bcrypt is the proposal-compatible choice. |
| `auth.py:31,42` token issuance | **Reimplemented** on PyJWT | Adds `exp`, `role`, `sub` claims. `create_access_token(identity=str(u.id))` sets no expiry (`auth.py:31`). |
| `auth.py:16` email uniqueness check | **Kept, plus normalization** | Fixes S9: `email.strip().lower()` before the check, and a functional unique index on `lower(email)`. |
| `guidance.py:17-20` upload storage | **Ported** | UUID prefix, configured folder. Gains extension + content-type allowlisting (fixes S3 — `utils.py:1-4` `allowed_file()` exists but is never imported). |
| `guidance.py:107-128` feedback validation | **Converted to Pydantic** | Same rules, declarative instead of imperative. |
| `guidance.py:45-61` LLM path | **Deleted** | Violates proposal §4.2. Replaced by `app/ml/ranker.py`. |
| `models.py:5-20` `User` | **Reimplemented, same shape** | Adds `is_active`, `ON DELETE CASCADE` on all children, functional unique index on `lower(email)`. |
| `models.py:22-29` `Profile` | **Reimplemented** | `skills`, `education`, `experience` TEXT columns are **removed entirely**, not deprecated. |

### 3.3 Frontend: Vite + React Router → Next.js + React + TypeScript

#### 3.3.1 What moves, what is kept, what is discarded

| Category | Items | Action |
|---|---|---|
| **Kept byte-identical** | `src/components/ui/*` (49 files), `src/lib/utils.ts`, `src/hooks/use-mobile.tsx`, `src/hooks/use-toast.ts`, `src/index.css`, `tailwind.config.ts`, `postcss.config.js`, `components.json` (flip `"rsc": true`) | Copied into the new tree without edits. |
| **Kept, lightly edited** | `src/components/layout/Header.tsx`, `Footer.tsx` | `react-router-dom` `Link`/`useNavigate`/`useLocation` → `next/link` + `usePathname` + `useRouter`. Nav link targets corrected (C1). |
| **Rewritten (data layer only)** | `Dashboard.tsx`, `Recommendations.tsx` | Shell and Tailwind markup preserved; `mockRecommendations`/`mockStats` replaced with React Query hooks. |
| **Ported as route files** | `Login.tsx`, `Register.tsx`, `Feedback.tsx`, `About.tsx`, `Features.tsx`, `Landing.tsx`, `NotFound.tsx` | Body preserved; routing and API call site changed. `Register.tsx:92` drops `educationLevel` — the new `/register` sends it. |
| **Deleted** | `Quiz.tsx` (372 lines), `Index.tsx` (17 lines — a routing shim), `App.tsx`, `main.tsx`, `App.css`, `vite.config.ts`, `index.html`, `vite-env.d.ts`, `.env`, `.env.development` | Not in proposal §4.1, or superseded by Next.js conventions. |
| **Replaced** | `src/api/client.ts` | Typed per-domain modules under `src/lib/api/`. Preserves the `request()` error-enrichment pattern (`:20-29`). |

#### 3.3.2 How the API base URL changes

`client.ts:1` reads `import.meta.env.VITE_API_BASE_URL`, a Vite-only construct that does not exist
in Next.js. It is replaced by `process.env.NEXT_PUBLIC_API_URL` in a single module
(`src/lib/api/config.ts`), with `NEXT_PUBLIC_` inlined at build time. **The current `.env` /
`.env.development` conflict (ports 5001 vs 5000) is resolved by having exactly one
`.env.example` and one documented local port (8000).**

#### 3.3.3 How authentication UX is preserved

The current flow stores `token` and `user` in `localStorage` (`Login.tsx:54-55`,
`Register.tsx:97-98`, `Header.tsx:32-36`) and revalidates via `api.me()` at `App.tsx:56-66`. That
UX is **preserved exactly** in the client bundle:

- `src/lib/auth/session.ts` — `getToken()`, `setSession()`, `clearSession()` wrapping the same two
  `localStorage` keys, so the migration is behaviour-preserving.
- `src/components/providers/AuthProvider.tsx` — mounts once inside the root layout, revalidates
  with `GET /api/auth/me` on load, exposes `{user, isLoading, isAuthenticated, isAdmin, logout}`.
- `src/components/providers/QueryProvider.tsx` — the `QueryClientProvider` currently at
  `App.tsx:70`, moved into a client provider so server components can stay server components.
- `src/middleware.ts` — the missing route guard. `/dashboard`, `/profile`, `/skills`, `/projects`,
  `/education`, `/certifications`, `/resume`, `/recommendations`, `/skill-gap` redirect to `/login`
  without a token; `/admin/*` redirects to `/dashboard` unless `user.role === "admin"`. This
  fixes the absence of any `<Navigate>` guard noted at `App.tsx:75-123`.

**Known accepted trade-off:** JWT in `localStorage` is readable by any XSS payload. The stronger
pattern is an `httpOnly` cookie. The proposal only requires "token-based sessions" (§7.5), and the
existing UX already stores the token client-side, so this plan keeps it — and records it as a
documented limitation rather than silently shipping a weaker claim. If time allows in Sprint 6,
`python-jose`-signed cookies are a drop-in upgrade since the server already issues signed claims.

#### 3.3.4 Why not "hybrid" or "keep Vite"

- **Keep Vite** contradicts proposal §7.2 and §4.3.
- **Hybrid** (Next.js shell + Vite SPA) adds a second build system, two dev servers, and a proxy for
  no functional gain, since the route count is small and the pages are already React.

### 3.4 Migration sequence (order matters)

```text
 1. git init + root .gitignore          ← nothing else is safe to do first (C4)
 2. Start Docker daemon                  ← unblocks PostgreSQL
 3. docker compose up -d postgres pgadmin
 4. Build backend/app/ skeleton + health endpoint    (Phase 1)
 5. Alembic revision 1 → infra + user                (Phase 1)
 6. Full domain schema, revision 2                   (Phase 2)  ← SCHEMA DECISION
 7. Seed taxonomy + job roles                        (Phase 2)
 8. Auth, then CRUD routers                          (Phases 3-4)
 9. ML layer against the seeded DB                   (Phase 5)
10. Scaffold Next.js, migrate preserved components   (Phase 6)
11. Wire pages to real endpoints                     (Phase 7)
12. Recommendation + skill-gap UX                    (Phase 8)
13. Evaluation + tests                               (Phase 9)
14. Deploy                                          (Phase 10)
15. Delete legacy Flask/Vite                         (Phase 11, T176)
```

Steps 1–2 are environment, 3–7 are the backend foundation, 8–9 are the product core, 10–12 are the
presentation layer, 13–15 are hardening and cleanup.

### 3.5 Data migration

**There is no data migration, deliberately.** The live SQLite database holds 11 users, 11 profiles
(9 of them empty), 6 `guidance_session` rows containing the identical hardcoded string, 6 events,
and 2 feedback entries. None of it is CareerLens data — the profiles hold
`'python,sql,ml'` in a comma-separated TEXT column, which has no equivalent in the normalized
schema, and the `guidance_session` rows are the placeholder string from `guidance.py:48`.

Attempting to transform that would produce fake CareerLens data and violate the "no fabricated
data" rule. Instead:

- The SQLite file is **archived**, not migrated: `backend/instance/pathfinder.db` →
  `docs/archive/pathfinder-legacy.db` at cutover, with a note explaining why it was not converted.
- `backend/pathfinder.db` (0 bytes, stray) is deleted in Phase 0.
- Any *real* users who register on the Flask app during the transition are re-registered on
  FastAPI. The team has 4 members and no external users; this is a non-issue that must be stated in
  the report rather than silently ignored.

### 3.6 What "the migration is done" means

| Check | Evidence |
|---|---|
| No Flask import remains in the served app | `grep -rn "^from flask\|^import flask" backend/app/` → empty |
| No Vite remains | `frontend/vite.config.ts` deleted; `vite`, `@vitejs/plugin-react-swc` removed from `package.json` |
| No `db.create_all()` in production paths | Only in `tests/conftest.py` |
| No mock data in served pages | `grep -rn "mockRecommendations\|mockStats\|mockQuizData" frontend/src` → empty |
| No unauthenticated admin surface | `backend/app/` contains no Flask-Admin equivalent; `/api/admin/*` all require `role == "admin"` |
| All P0 security findings closed | S1, S2, S3, S4, S5, S6 — see §17 |

---

## 4. Implementation Phases

Twelve phases, ordered strictly by dependency. Each phase states its objective, why it sits at that
position, its prerequisites, the concrete work, the files it touches, and the criterion that closes
it. **Do not begin a phase until the previous phase's completion criteria are met** — the ordering
is load-bearing, not cosmetic.

### Phase 0 — Architecture, Repository & Environment

**Objective.** Establish a version-controlled repository, a reproducible Python 3.12 environment
with the full ML dependency set, a running PostgreSQL 16 with pgAdmin, and a written architecture
decision record. Produce a running `GET /health` on FastAPI against an empty database.

**Why here.** Nothing else is safe to do first. The repository is not under version control (C4),
so every subsequent deletion is unrecoverable. The environment has three verified blockers — no
PostgreSQL, no sudo, a stopped Docker daemon (E2) — and a Python-version trap (E1). Discovering any
of these in Sprint 3 would cost a sprint.

**Prerequisites.** Docker Desktop installed (verified: CLI present, daemon not running). Supervisor
sign-off on the stack decision D1 (proposal conformance).

**Tasks.** T001–T012.

**Files to create.**
```
.gitignore                                     # root — MISSING today
docker-compose.yml                             # postgres:16 + pgadmin:4
backend/.env.example                           # exists but documents Flask; replace contents
backend/requirements-dev.txt                   # pytest, ruff, mypy
docs/architecture.md                           # ADR: stack, layers, decisions D1-D5
docs/erd.md                                    # Mermaid ER diagram of §6
```

**Files to modify.** `backend/.env.example` (Flask keys → target keys). `frontend/tsconfig.app.json`
(deferred to Phase 6 — leave alone now).

**Files to remove/deprecate.** `backend/pathfinder.db` (0 bytes, stray). `backend/__pycache__/`.
Mark the eight legacy Flask modules and 11 Vite pages **frozen** — do not edit, do not delete.

**Expected output.** `git log` shows a first commit containing the untouched legacy app. `docker
compose ps` shows `postgres` and `pgadmin` healthy. `uvicorn app.main:app` serves
`{"status":"ok","service":"careerlens-api","database":"ok"}` on `GET /health`. `python -c "import
spacy, sklearn, pdfplumber, docx"` succeeds.

**Completion criteria.**
- [ ] `git init` done; first commit contains the full legacy tree; `.gitignore` excludes `.env`, `*.db`, `venv/`, `__pycache__/`, `node_modules/`, `.next/`, `uploads/`
- [ ] `docker compose up -d` starts `postgres:16` and `pgadmin:4`; `psql` reaches the database
- [ ] `uv venv --python 3.12 backend/.venv` created; all target packages importable
- [ ] `GET /health` returns 200 with a database round-trip
- [ ] `docs/architecture.md` and `docs/erd.md` committed
- [ ] `spacy.load("en_core_web_sm")` succeeds (proves the model is downloadable — R6)

**Depends on.** Nothing. **Blocks everything.**

---

### Phase 1 — Backend Platform Migration

**Objective.** Stand up the FastAPI application skeleton: settings, structured logging, SQLAlchemy
2.0 session management, the `get_db` dependency, CORS restricted to an allowlist, the error
envelope, and Alembic. Ship Alembic revision 1 creating infrastructure + `user`.

**Why here.** Every domain table, every router, and the ML layer's persistence bridge assume a
working session factory and migration toolchain. `app.py:46` `db.create_all()` creates missing
tables but never alters existing ones — the current schema can only be changed by deleting the file
and losing all 11 users. Alembic must exist before the first domain table is written.

**Prerequisites.** Phase 0 complete.

**Tasks.** T013–T030.

**Files to create.**
```
backend/app/__init__.py
backend/app/main.py                     # FastAPI factory, lifespan, router registration
backend/app/core/__init__.py
backend/app/core/config.py              # pydantic-settings; fail-fast on weak/missing secret
backend/app/core/logging.py             # structured logging
backend/app/core/exceptions.py          # APIError + handlers; error envelope
backend/app/core/security.py            # bcrypt hash/verify, PyJWT encode/decode
backend/app/db/__init__.py
backend/app/db/base.py                  # DeclarativeBase, naming_convention, TimestampMixin
backend/app/db/session.py               # engine, SessionLocal, get_db
backend/alembic.ini
backend/alembic/env.py
backend/alembic/script.py.mako
backend/alembic/versions/0001_infra_and_user.py
backend/tests/__init__.py
backend/tests/conftest.py               # TestClient, per-test transactional rollback
backend/pytest.ini  (or [tool.pytest] in pyproject)
```

**Files to modify.** `backend/requirements.txt` (replace Flask set with the target set — see
T017 for the exact list).

**Files to remove/deprecate.** None yet — Flask modules stay frozen until T176.

**Expected output.** `GET /` returns `{"service":"careerlens-api","version":"…","docs":"/docs"}`.
`GET /health` pings the database. `GET /docs` renders the OpenAPI UI. `alembic upgrade head` creates
`user` and `alembic_version`; `alembic downgrade base` removes them cleanly.

**Completion criteria.**
- [ ] `app.main:app` starts with `uvicorn app.main:app --reload` and no warnings
- [ ] Startup **fails loudly** when `JWT_SECRET_KEY` is absent or < 32 characters
- [ ] `CORS` allowlist comes from `ALLOWED_ORIGINS`; an unlisted `Origin` receives no `Access-Control-Allow-Origin`
- [ ] `alembic upgrade head` then `downgrade base` then `upgrade head` succeeds on a clean database
- [ ] A test in `tests/test_health.py` asserts `/health` returns 200 and `"database": "ok"`
- [ ] `grep -c "create_all" backend/app/` returns 0

**Depends on.** Phase 0. **Blocks Phases 2–5.**

---

### Phase 2 — Database & Domain Model

**Objective.** Design and implement the normalized schema, write Alembic revision 2, and load the
seed knowledge base: ≈150 skills with aliases and 50–100 job roles with weighted required skills.
**This is the single most important phase** — it unblocks the ML layer, every CRUD router, the admin
panel, and the recommendation UI.

**Why here.** The current `profile.skills = 'python,sql,ml'` column (`models.py:26`) is
architecturally incapable of supporting three separate proposal requirements: per-skill proficiency
(§4.1), per-role importance weights (§4.2), and set-difference gap analysis (§4.2). Every one of
those needs normalized rows. The ML engine's `user_skill` and `job_role_skill` reads cannot be
written until these tables exist.

**Prerequisites.** Phase 1 complete. Design work is parallel: taxonomy curation (2-person task per
proposal §10, M1+M4) proceeds while the schema is written.

**Tasks.** T031–T048.

**Files to create.**
```
backend/app/models/__init__.py
backend/app/models/user.py              # User
backend/app/models/profile.py           # Profile  (skills/education/experience REMOVED)
backend/app/models/skill.py             # Skill, SkillAlias
backend/app/models/user_skill.py        # UserSkill
backend/app/models/project.py           # Project
backend/app/models/education.py         # EducationRecord, Certification
backend/app/models/job.py               # JobRole, JobRoleSkill
backend/app/models/resume.py            # ResumeUpload, ResumeDetectedSkill
backend/app/models/recommendation.py    # RecommendationRun, RecommendationResult
backend/alembic/versions/0002_domain_schema.py
backend/data/skills_taxonomy.json       # ≈150 skills, category, aliases   (T035)
backend/data/job_roles.json             # 50–100 roles, description, weighted skills (T037)
backend/scripts/seed_taxonomy.py        # idempotent upsert of skills + aliases
backend/scripts/seed_job_roles.py       # idempotent upsert of roles + weights
backend/scripts/seed_admin.py           # one admin user from env vars
backend/scripts/seed_dev_users.py       # 2–3 demo users for manual QA (T046)
```

**Files to modify.** None in code (models are new files). `backend/.env.example` gains
`POSTGRES_*` and `ADMIN_EMAIL`/`ADMIN_PASSWORD`.

**Files to remove/deprecate.** The `profile.skills`, `profile.education`, `profile.experience`
columns are **dropped in revision 2** — they are not carried forward in any form. The legacy
`models.py` still defines them, but it is frozen and is deleted at T176.

**Expected output.** `alembic upgrade head` produces 14 tables. `python -m scripts.seed_taxonomy`
prints `skills: 152, aliases: 431`. `python -m scripts.seed_job_roles` prints `roles: 60,
role_skills: 1187`. Both scripts are idempotent — running twice changes nothing.

**Completion criteria.**
- [ ] `psql \d` shows all 14 tables with FK constraints **enforced** (PostgreSQL enforces them; SQLite did not — S10)
- [ ] `ON DELETE CASCADE` present on every child FK; deleting a `user` removes its profile, skills, projects, education, certifications, uploads, and recommendations in one statement
- [ ] `skill_alias.alias` is the primary key; `EXPLAIN` on an alias lookup shows an index scan
- [ ] `job_role_skill.weight` is `NUMERIC(3,2)` with `CHECK (weight > 0 AND weight <= 1)`
- [ ] `user_skill.proficiency` is `SMALLINT` with `CHECK (proficiency BETWEEN 1 AND 5)`
- [ ] No column named `skills`, `education`, or `experience` of type `TEXT` exists on `profile`
- [ ] Seed scripts are idempotent (verified by running twice and diffing row counts)
- [ ] `docs/erd.md` matches the implemented schema exactly

**Depends on.** Phase 1. **Blocks Phases 3, 4, 5, 8.**

---

### Phase 3 — Authentication & Authorization

**Objective.** Deliver register, login, logout, `me`, refresh, and enforced User/Admin roles, with
a `require_role` dependency applied to every protected route and client-side route guards on the
frontend.

**Why here.** Every subsequent endpoint needs an identity to scope data to, and every
"my profile / my skills" query needs an ownership check. Doing this before the CRUD routers means
the ownership pattern (`obj.user_id == current_user.id`) is established once and reused, instead of
being retrofitted — and retrofitted ownership checks are exactly how the IDOR at `guidance.py:31`
happened.

**Prerequisites.** Phase 2 (the `user` table exists from revision 1; Phase 2 adds the rest).

**Tasks.** T049–T062.

**Files to create.**
```
backend/app/schemas/__init__.py
backend/app/schemas/auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserRead
backend/app/api/__init__.py
backend/app/api/deps.py                 # get_db, get_current_user, require_user, require_role
backend/app/api/router.py               # aggregates all domain routers
backend/app/api/routes/__init__.py
backend/app/api/routes/auth.py
backend/app/services/__init__.py
backend/app/services/auth_service.py
backend/tests/test_auth.py
frontend/src/lib/auth/session.ts        # Phase 6/7; listed here for the contract
```

**Files to modify.** `backend/app/main.py` (register the router).

**Files to remove/deprecate.** Legacy `backend/auth.py` gains a deprecation comment; deletion at
T176.

**Expected output.** `POST /api/auth/register` → `201 {user, access_token, token_type, expires_in}`.
`POST /api/auth/login` → same shape. `POST /api/auth/logout` → `204` (clears the client session;
documents the stateless-token trade-off in the docstring). `GET /api/auth/me` → `200 {user}`.
`GET /api/admin/ping` → `200` for admin, `403` for user, `401` for anonymous.

**Completion criteria.**
- [ ] Registration validates name (1–120), email (RFC-ish regex), password (≥ 8 chars, upper +
       lower + digit) — server-side, matching the client policy already at `Register.tsx:59-63`,
       which the current `auth.py:14-15` presence-only check does not enforce
- [ ] Email is stored and matched lowercased and trimmed; `A@B.com` and `a@b.com` cannot both register (S9)
- [ ] Duplicate email returns `409`, not `400` (current `auth.py:17` returns 400)
- [ ] Tokens carry `sub`, `role`, `exp`, `iat`; an expired token returns `401 token_expired`
- [ ] `require_role("admin")` returns `403` (not `500`) for an authenticated non-admin
- [ ] Passwords are bcrypt; `password_hash` never appears in any response schema
- [ ] `tests/test_auth.py` covers: register, duplicate email, weak password, login, wrong password,
       `me` with/without token, admin guard, token expiry

**Depends on.** Phase 2. **Blocks Phases 4, 7, 8.**

---

### Phase 4 — CRUD APIs

**Objective.** Full CRUD for profile, skills, projects, education, certifications, and admin job
roles, with ownership enforcement, Pydantic validation, and correct status codes.

**Why here.** Proposal §4.1 requires Create/Read/Update/Delete on five entities. The current
backend has **zero** `PUT`/`PATCH`/`DELETE` routes across all eight modules. The CRUD layer also
populates the data the ML engine needs, so it must be live and seeded with realistic content before
the engine can be evaluated.

**Prerequisites.** Phase 3.

**Tasks.** T063–T090.

**Files to create.**
```
backend/app/schemas/profile.py          # ProfileCreate/Update/Read
backend/app/schemas/skill.py            # UserSkillCreate/Update/Read, SkillRead, TaxonomySearch
backend/app/schemas/project.py
backend/app/schemas/education.py        # EducationRecord*, Certification*
backend/app/schemas/job.py              # JobRoleCreate/Update/Read, JobRoleSkillIn, SkillWeight
backend/app/api/routes/profile.py
backend/app/api/routes/skills.py
backend/app/api/routes/projects.py
backend/app/api/routes/education.py
backend/app/api/routes/certifications.py
backend/app/api/routes/jobs.py          # public read + admin write
backend/app/services/profile_service.py
backend/app/services/skill_service.py
backend/app/services/project_service.py
backend/app/services/education_service.py
backend/app/services/job_service.py
backend/tests/test_profile_crud.py
backend/tests/test_skills_crud.py
backend/tests/test_projects_crud.py
backend/tests/test_education_crud.py
backend/tests/test_jobs_crud.py
backend/tests/test_ownership.py         # cross-user access must 404/403
```

**Files to modify.** `backend/app/api/router.py`.

**Files to remove/deprecate.** None. `guidance.py`'s handlers are superseded but stay frozen.

**Expected output.** The full CRUD matrix in §8 is green — every cell demonstrated by a passing
test and reachable from the UI built in Phase 7.

**Completion criteria.**
- [ ] Every entity in §8 has C, R, U, D implemented, tested, and returning 2xx
- [ ] Ownership: `GET/PATCH/DELETE /api/projects/{id}` for another user's project returns `404`
       (not `403` — a `403` confirms the row exists, which is itself an information leak)
- [ ] `POST /api/skills` accepts only `skill_id` values present in the taxonomy; unknown → `422`
- [ ] `PATCH /api/skills/{skill_id}` updates `proficiency` and `source`; `DELETE` removes the row
- [ ] Bulk confirmation: `POST /api/skills/confirm` upserts a list of CV-detected skills in one
       transaction and is idempotent
- [ ] `PUT /api/admin/jobs/{id}/skills` replaces the role's weighted skill set atomically — a
       partial failure leaves the previous set intact
- [ ] `DELETE /api/admin/jobs/{id}` cascades to `job_role_skill` and to stored `recommendation_result`
       rows (either cascade or soft-delete with `is_active = false`; the choice is recorded in §6.4)
- [ ] `tests/test_ownership.py` proves user A cannot read, update, or delete user B's project,
       education record, certification, or skill
- [ ] `grep -rn "jwt_required(optional=True)" backend/app/` returns nothing — every write requires
       auth (S4)

**Depends on.** Phase 3. **Blocks Phase 5 evaluation realism and Phase 7.**

---

### Phase 5 — AI/ML Engine

**Objective.** Build the complete deterministic engine: taxonomy loader, text extraction, spaCy
skill extraction, weighted skill coverage, TF-IDF cosine similarity, skill-gap analysis, and the
ranker. Expose it through the recommendation and skill-gap APIs.

**Why here.** This is the project's defining contribution and the largest single block of work
(proposal §8 budgets 128 man-hours for Stage 2 alone). It needs the taxonomy (Phase 2), the user's
confirmed skills (Phase 4), and the job knowledge base (Phase 2). Building it earlier would mean
guessing the schema; later would leave no time to iterate on weights before evaluation.

**Prerequisites.** Phases 2 and 4 complete and seeded with realistic content.

**Tasks.** T091–T108.

**Files to create.** See §9 for the complete listing — `backend/app/ml/{types,taxonomy,text_loader,
extractor,text_profile,matcher,gap_analysis,ranker,learning_path}.py`, `backend/app/ml/evaluation/*`,
`backend/app/schemas/recommendation.py`, `backend/app/api/routes/recommendations.py`,
`backend/app/api/routes/skill_gap.py`, `backend/app/api/routes/cv.py`,
`backend/app/services/recommendation_service.py`, `backend/app/services/cv_service.py`.

**Files to modify.** `backend/app/api/router.py`.

**Files to remove/deprecate.** The LLM path in `guidance.py:45-61` is deleted at T176 along with the
rest of the legacy module; its replacement (`learning_path.py`) is flag-gated and off by default.

**Expected output.** `POST /api/cv/upload` returns extracted text length and a list of detected
skills. `POST /api/recommendations` returns a ranked, explainable list. `GET /api/skill-gap/{role_id}`
returns matched and missing skills ordered by weight. The engine runs in well under 2 seconds for
60 roles on a laptop CPU.

**Completion criteria.**
- [ ] `ml/` imports **no** SQLAlchemy and **no** FastAPI symbol — verified by
      `grep -rn "sqlalchemy\|fastapi" backend/app/ml/` returning empty
- [ ] Alias resolution: `sklearn`, `scikit learn`, `sci-kit learn`, `SKLearn` all resolve to
      `Scikit-learn`
- [ ] Coverage ∈ [0, 1] and cosine ∈ [0, 1]; `compatibility = w₁·coverage + w₂·cosine` ∈ [0, 1] for
      every role, asserted in a test
- [ ] Two runs over identical input produce byte-identical output (determinism test)
- [ ] A role with zero matching skills scores 0 and is ranked last, not dropped
- [ ] Every recommended role carries `matched_skills[]` and `missing_skills[]` with per-skill
      weights — the explainability requirement from proposal §2
- [ ] `GET /health` still reports the DB as `ok`; the engine adds no new runtime failure modes
- [ ] Scanned/image-only PDF returns `422` with a clear "OCR is not supported" message rather than
      silently returning zero skills (proposal §11 states OCR is out of scope)

**Depends on.** Phases 2, 4. **Blocks Phases 8, 9.**

---

### Phase 6 — Frontend Migration to Next.js

**Objective.** Replace the Vite SPA with a Next.js 16 App Router application, preserving the 49
shadcn components, the Tailwind theme, and React Query; add `middleware.ts` route guards and role-aware
navigation.

**Why here.** Building UI against a moving API produces rework. By this point every endpoint the UI
touches is stable, so the migration is a mechanical port with a known contract. Doing it before the
API stabilizes would mean rewriting components twice.

**Prerequisites.** Phase 4 complete (the screens' contracts are frozen). Phase 5 in progress is fine.

**Tasks.** T109–T125.

**Files to create.**
```
frontend/app/layout.tsx                 # root layout, fonts, global CSS, providers
frontend/app/globals.css                # moved from src/index.css, unchanged content
frontend/app/(public)/layout.tsx        # Header + Footer
frontend/app/(public)/page.tsx          # landing (from Landing.tsx)
frontend/app/(public)/about/page.tsx
frontend/app/(public)/features/page.tsx
frontend/app/(public)/login/page.tsx
frontend/app/(public)/register/page.tsx
frontend/app/(public)/feedback/page.tsx
frontend/app/(app)/layout.tsx           # guarded shell
frontend/app/(app)/dashboard/page.tsx
frontend/app/(app)/profile/page.tsx
frontend/app/(app)/skills/page.tsx
frontend/app/(app)/projects/page.tsx
frontend/app/(app)/education/page.tsx
frontend/app/(app)/certifications/page.tsx
frontend/app/(app)/resume/page.tsx
frontend/app/(app)/recommendations/page.tsx
frontend/app/(app)/recommendations/[id]/page.tsx
frontend/app/(app)/skill-gap/page.tsx
frontend/app/(admin)/layout.tsx          # admin guard
frontend/app/(admin)/admin/page.tsx
frontend/app/(admin)/admin/jobs/page.tsx
frontend/app/(admin)/admin/jobs/[id]/page.tsx
frontend/app/(admin)/admin/evaluation/page.tsx
frontend/app/not-found.tsx
frontend/src/middleware.ts              # route guards
frontend/src/components/providers/{AuthProvider,QueryProvider,ThemeProvider}.tsx
frontend/src/components/layout/{Header,Footer}.tsx     # ported, nav corrected
frontend/src/lib/api/{config,client,auth,profile,skills,projects,education,certifications,
                       jobs,recommendations,cv,admin}.ts
frontend/src/lib/hooks/{use-profile,use-skills,use-projects,use-education,use-certifications,
                        use-jobs,use-recommendations,use-cv,use-dashboard}.ts
frontend/src/lib/schemas.ts             # zod mirrors of the Pydantic models
frontend/src/features/{profile,skills,projects,education,certifications,recommendations,
                       skill-gap,admin}/{components,schemas}.ts(x)
frontend/.env.example
frontend/next.config.ts
frontend/postcss.config.js              # kept
```

**Files to modify.** `frontend/package.json` (swap Vite for Next.js; add `zustand` only if truly
needed — prefer React Query). `frontend/components.json` (`"rsc": true`). `frontend/tsconfig.json`
(Next.js requires `"jsx": "preserve"`, `plugins: [{name: "next"}]`, `moduleResolution: "bundler"`).

**Files to remove/deprecate.** `frontend/vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx`,
`src/App.css`, `src/vite-env.d.ts`, `src/pages/**` (all 11, after porting their bodies),
`frontend/.env`, `frontend/.env.development`, `frontend/bun.lockb`.

**Expected output.** `npm run dev` serves the app on `:3000`. Every listed route renders. Anonymous
visitors to `/dashboard` are redirected to `/login`. A `user`-role visitor to `/admin/jobs` is
redirected to `/dashboard`. An `admin` sees the admin nav.

**Completion criteria.**
- [ ] `npm run build` succeeds with zero TypeScript errors
- [ ] `npm run lint` clean
- [ ] `src/components/ui/*` has 49 files and **zero** diffs versus the originals
- [ ] No `react-router-dom` import remains; no `vite` in `package.json`
- [ ] The authenticated nav in the header links to Dashboard, Profile, Skills, Projects, Education,
       Certifications, Resume, Recommendations, Skill Gap, Feedback, Sign out — and **every one of
       those routes exists** (fixes C1's four dead links)
- [ ] Admin nav appears only for `role === "admin"`
- [ ] `tailwind.config.ts` needed no `content` edits (its globs already include `./app/**`)
- [ ] Every screen has an explicit loading, empty, and error state
- [ ] Layout is responsive at 375 px, 768 px, and 1280 px

**Depends on.** Phase 4. **Blocks Phase 7.**

---

### Phase 7 — Frontend Integration

**Objective.** Wire every screen to real endpoints via React Query. Delete all mock data. Make every
CRUD operation in §8 demonstrable through the UI.

**Why here.** Phase 6 produced structure; Phase 7 produces function. Separating them means the
structural port can be verified (build passes, routes render) independently of API correctness, so a
failing query is unambiguously a backend problem.

**Prerequisites.** Phases 4, 5, 6 complete.

**Tasks.** T126–T140.

**Files to create.** Feature components under `frontend/src/features/*/components/`
(`ProfileForm`, `SkillPicker`, `SkillList`, `ProjectForm`, `ProjectCard`, `EducationForm`,
`CertificationForm`, `CvDropzone`, `DetectedSkillsPanel`, `RecommendationCard`, `ScoreBreakdown`,
`GapTable`, `JobRoleForm`, `SkillWeightEditor`, `EvalChart`).
`frontend/src/components/shared/{Loading,EmptyState,ErrorState,ConfirmDialog,PageHeader}.tsx`.

**Files to modify.** Every page under `frontend/app/**/page.tsx`.

**Files to remove/deprecate.** `mockRecommendations` (`Dashboard.tsx:37`, `Recommendations.tsx:24`),
`mockStats` (`Dashboard.tsx:70-75`), `mockUser` (`Dashboard.tsx:22-27`), `mockQuizStatus`
(`Dashboard.tsx:29-33`). All of these are deleted, not left behind.

**Expected output.** A logged-in user can perform every create/edit/delete operation listed in §8
by clicking, and the change survives a page refresh — because it is in PostgreSQL, not `useState`.
The current `Recommendations.tsx:168` `useState(mockRecommendations[0])` and
`Recommendations.tsx:169` `savedCareers` pattern is gone.

**Completion criteria.**
- [ ] `grep -rn "mock\|12,847\|94%" frontend/src frontend/app` returns nothing application-facing
- [ ] Profile: create, view, edit, delete — all four verifiable in the browser
- [ ] Skills: add from taxonomy search, change proficiency (1–5), remove — all verifiable
- [ ] Projects: add, edit, delete — all verifiable
- [ ] Education and certifications: add, edit, delete — all verifiable
- [ ] Admin jobs: create role, assign weighted skills, edit, delete — all verifiable
- [ ] Every destructive action is confirmed by a dialog (the `AlertDialog` component already exists in the kit)
- [ ] Every form shows server-side field errors returned by Pydantic, keyed to the field
- [ ] Optimistic updates are **not** used for deletes; the list refetches after mutation
- [ ] A manual end-to-end pass of §12 completes with zero console errors

**Depends on.** Phases 4, 5, 6. **Blocks Phases 8, 9.**

---

### Phase 8 — Recommendation & Skill-Gap UX

**Objective.** Build the two screens that constitute the product's payoff: the ranked
recommendations view with explainable scores, and the skill-gap report with a prioritized learning
path.

**Why here.** The data exists after Phase 5, but the *explanation* is the differentiator versus
LinkedIn/Jobscan/Bdjobs (proposal §3.4: "Explains why a role matches — CareerLens: Yes, matched and
missing skills"). It deserves its own phase and its own review attention.

**Prerequisites.** Phases 5 and 7.

**Tasks.** T141–T150.

**Files to create.** `ScoreBreakdown.tsx` (coverage vs. TF-IDF contribution bars), `GapTable.tsx`
(matched / missing with weight-ordered tiers), `LearningPathCard.tsx`,
`frontend/app/(app)/skill-gap/page.tsx`, `frontend/app/(app)/recommendations/[id]/page.tsx`.

**Files to modify.** `frontend/app/(app)/recommendations/page.tsx`, `frontend/app/(app)/dashboard/page.tsx`.

**Files to remove/deprecate.** None.

**Expected output.** `/recommendations` shows ranked roles with a compatibility percentage that
decomposes into its two components on click. `/skill-gap?role={id}` shows a weighted, ordered gap.

**Completion criteria.**
- [ ] Each role card shows: title, family, compatibility %, and the top matched and top missing skills
- [ ] Clicking a card opens a breakdown showing `skill_coverage`, `tfidf_similarity`, and the weights used
- [ ] `/recommendations/[id]` renders a persisted run from the database, not a re-computation
- [ ] `/skill-gap` orders missing skills strictly by descending importance weight
- [ ] Tiers are visually distinguished: `weight ≥ 0.8` critical, `0.5–0.8` important, `< 0.5` desirable
- [ ] An empty profile (0 skills) produces a helpful empty state with a link to `/skills`, not a
       zero-percent list
- [ ] `recharts` (already installed, `package.json:57`) renders the admin evaluation chart

**Depends on.** Phases 5, 7. **Blocks Phase 9 sign-off.**

---

### Phase 9 — Testing & AI Evaluation

**Objective.** Complete the pytest suite, run the 24-profile evaluation harness, tune the 60/40
weights, and commit the evaluation report.

**Why here.** Proposal §2 requires validation on at least 20 hand-labelled profiles and §4.3 lists
an "evaluation summary" as a deliverable. It must run after the engine and the knowledge base are
both final, because tuning weights against a changing job set produces meaningless numbers. Testing
in this phase rather than throughout is a deliberate trade: the team has 4 members and 516 hours,
and a dedicated QA pair is allocated in proposal §10 (M4 + M2 for unit/API tests, M3 + M4 for
integration, M1 + M4 for AI validation).

**Prerequisites.** Phases 4, 5, 7, 8 complete.

**Tasks.** T151–T160.

**Files to create.**
```
backend/ml/evaluation/labelled_profiles.jsonl     # 24 labelled profiles (T152)
backend/app/ml/evaluation/__init__.py
backend/app/ml/evaluation/harness.py              # runs the engine, computes metrics
backend/app/ml/evaluation/metrics.py              # top-1, top-3, MRR, per-component means
backend/app/ml/evaluation/tuning.py               # weight sweep
backend/app/ml/evaluation/__main__.py             # python -m app.ml.evaluation
backend/app/ml/evaluation/sample_cvs/             # 3 consented/anonymised text CVs
backend/tests/test_taxonomy.py
backend/tests/test_extractor.py
backend/tests/test_matcher.py
backend/tests/test_gap_analysis.py
backend/tests/test_ranker.py
backend/tests/test_determinism.py
backend/tests/test_cv_endpoints.py
backend/tests/test_recommendation_endpoints.py
backend/tests/test_evaluation.py                 # asserts the top-3 target is met
docs/evaluation_report.md
```

**Files to modify.** `backend/app/core/config.py` (final tuned weights). `backend/requirements-dev.txt`.

**Files to remove/deprecate.** `backend/scripts/e2e_test.py` (ad-hoc script against
`127.0.0.1:5001`, superseded by pytest).

**Expected output.** `pytest` green. `python -m app.ml.evaluation` prints a metrics table and writes
`docs/evaluation_report.md` with top-1 accuracy, top-3 hit rate, MRR, and the weight sweep.

**Completion criteria.**
- [ ] `pytest` passes with ≥ 60 tests, 0 failures
- [ ] 24 labelled profiles in `labelled_profiles.jsonl`, each with `expected_role` and a stated
       labelling rationale
- [ ] Top-3 hit rate ≥ 0.75; top-1 accuracy reported honestly whatever it is
- [ ] Two consecutive harness runs on unchanged data produce **identical** metrics
- [ ] The weight sweep reports metrics at 0.5/0.5, 0.6/0.4, 0.7/0.3, 0.8/0.2, 0.9/0.1; the chosen
       values are justified in the report, whether or not 0.6/0.4 wins
- [ ] `tests/test_evaluation.py` fails if top-3 drops below target — the metric is a regression gate
- [ ] `docs/evaluation_report.md` states plainly that no trained classifier was used, and why
       (proposal §4.2 mandates this disclosure)

**Depends on.** Phases 5, 7, 8. **Blocks Phase 10 sign-off.**

---

### Phase 10 — Deployment

**Objective.** Deploy the API and database to Render/Railway, the frontend to Vercel, with
environment variables, migrations run against the production database, and CORS pinned to the real
frontend origin.

**Why here.** Deployment cannot be tested until the app is feature-complete, and deploying early
means redeploying on every subsequent commit. This phase also covers the proposal §6.4 mitigation
"keep a local Docker/compose setup as a backup for the final demo".

**Prerequisites.** Phases 9 complete and the full Definition of Done (§19) met on `main`.

**Tasks.** T161–T167.

**Files to create.**
```
backend/Dockerfile              # REPLACE: uvicorn, python:3.12-slim, non-root user
docker-compose.yml              # add `api` service; postgres + pgadmin stay
backend/render.yaml             # or railway.json
frontend/vercel.json
frontend/.env.example           # NEXT_PUBLIC_API_URL
docs/deployment.md              # exact steps, env var table, rollback procedure
```

**Files to modify.** `backend/.env.example`. `backend/requirements.txt` (add `gunicorn` if the
platform requires it; the current `Dockerfile:7` uses it).

**Files to remove/deprecate.** None.

**Expected output.** A public HTTPS URL for the frontend and a public HTTPS API base. Registering on
the deployed frontend, uploading a CV, and receiving ranked recommendations works end to end.

**Completion criteria.**
- [ ] `alembic upgrade head` has been run against the production database
- [ ] Secrets are set in the platform's environment, never committed; `.gitignore` covers `.env*`
- [ ] Production `ALLOWED_ORIGINS` contains only the deployed frontend origin
- [ ] `JWT_SECRET_KEY` in production is a generated 48+ character value
- [ ] The deployed app serves `/health` and `/docs`
- [ ] The full user journey (§12) has been executed against the **deployed** URL by a second team
       member, on a phone viewport and a desktop viewport
- [ ] Local `docker compose up` still works as the offline demo fallback (proposal §6.4)

**Depends on.** Phase 9. **Blocks Phase 11.**

---

### Phase 11 — Final Academic & Project Validation

**Objective.** Verify every proposal clause, write the report/user manual/presentation, and delete
the legacy Flask + Vite codebase in a single auditable commit.

**Why here.** The deletions are the only irreversible operation in the entire plan, so they happen
after the new system has demonstrably passed the CRUD demo. Nothing is deleted while it is still the
only thing running.

**Prerequisites.** Phase 10 complete.

**Tasks.** T168–T176.

**Files to create.**
```
docs/report.md                  # final report: method, design honesty clause, limitations
docs/user_manual.md             # proposal §4.3 deliverable
docs/presentation_outline.md    # proposal §4.3 deliverable
docs/limitations.md             # proposal §11 — must be rewritten for CareerLens
```

**Files to modify.** `frontend/README.md` (currently unmodified Lovable boilerplate),
`backend/README.md` (currently titled "Pathfinder AI Guide - Flask Backend (starter)" — describes a
product that no longer exists), `frontend/package.json:2` (still `"vite_react_shadcn_ts"`).

**Files to remove/deprecate.** The entire legacy tree, in one commit:
```
backend/app.py, backend/auth.py, backend/guidance.py, backend/extensions.py,
backend/admin.py, backend/tasks.py, backend/utils.py, backend/models.py,
backend/pathfinder.db, backend/instance/, backend/scripts/{create_feedback_table,e2e_test,
    inspect_db,post_feedback_test,show_feedbacks}.py,
frontend/vite.config.ts, frontend/index.html, frontend/src/App.tsx, frontend/src/main.tsx,
frontend/src/App.css, frontend/src/vite-env.d.ts, frontend/src/pages/,
frontend/src/api/, frontend/.env, frontend/.env.development
```
`backend/instance/pathfinder.db` is **archived** to `docs/archive/pathfinder-legacy.db` with a
README explaining why it was not migrated (§3.5), not silently dropped.

**Expected output.** The §18 compliance matrix is fully ticked, the report is submitted, and the
repository contains only CareerLens AI.

**Completion criteria.**
- [ ] Every row of §18 reads ✅ with a `file:line` or test name as evidence
- [ ] Product name is "CareerLens AI" everywhere: zero occurrences of "Pathfinder" and zero of
       "CareerGuide AI" in any source file (currently `app.py:53`, `extensions.py:8`,
       `Header.tsx:69`, `Register.tsx:101`, `Login.tsx:93`, `Feedback.tsx:74`,
       `Landing.tsx:44,138,203`, `About.tsx:77`, `Footer.tsx:44,126`, both READMEs,
       `package.json:2`)
- [ ] The report contains the §4.2 design-honesty disclosure verbatim in intent: unsupervised
       similarity + rule-based weighting, no trained classifier, because no large labelled dataset exists
- [ ] The limitations section matches the actual system's limitations (proposal §11 already does
       this for CareerLens; the current codebase's §11 text describes Pathfinder and must be replaced)
- [ ] Legacy deletion is a single commit whose message names what was removed and why
- [ ] The final report, user manual, and presentation are committed

**Depends on.** Phase 10. **Final phase.**

---

## 5. Detailed Task Breakdown

Every task is independently assignable to at most two members (proposal §10, §10 work-distribution
rule). Priority: **P0** = blocks other tasks or is a proposal requirement; **P1** = required before
the sprint ends; **P2** = valuable, deferrable to a later sprint.

### Phase 0 — Architecture, Repository & Environment

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T001 | 0 | Initialise the git repository, add a root `.gitignore` covering `.env`, `.env.*`, `*.db`, `venv/`, `.venv/`, `__pycache__/`, `node_modules/`, `.next/`, `uploads/`, `.pytest_cache/`, and make the first commit containing the unmodified legacy tree | Infra | `.gitignore` | — | P0 | Low |
| T002 | 0 | Create the GitHub remote, push `main`, create the Sprint 1–6 project board matching proposal §5 | Infra | GitHub Projects | T001 | P0 | Low |
| T003 | 0 | Write `docs/architecture.md` — an ADR recording decisions D1–D5, the three layer boundaries from §2.3, and the request lifecycle from §2.4 | Docs | `docs/architecture.md` | T001 | P0 | Low |
| T004 | 0 | Install Python 3.12 via `uv python install 3.12`, create `backend/.venv`, and pin the runtime in `backend/.python-version` (E1 — avoids the thinc 9.x source build) | Env | `backend/.python-version` | T001 | P0 | Low |
| T005 | 0 | Write `backend/requirements.txt` with the target dependency set and `backend/requirements-dev.txt` with `pytest`, `pytest-cov`, `httpx`, `ruff`, `mypy`; install into `.venv` and verify every import | Env | `backend/requirements.txt`, `backend/requirements-dev.txt` | T004 | P0 | Low |
| T006 | 0 | Download and verify the spaCy model: `python -m spacy download en_core_web_sm`, then confirm `spacy.load("en_core_web_sm")` runs on a sample sentence | AI/ML | — | T005 | P0 | Low |
| T007 | 0 | Write `docker-compose.yml` defining `postgres:16` (healthcheck, named volume, port 5432) and `pgadmin:4` (port 5050) | DB | `docker-compose.yml` | T001 | P0 | Low |
| T008 | 0 | Start the Docker daemon, run `docker compose up -d postgres pgadmin`, and verify connectivity with `docker compose exec postgres psql -U careerlens -d careerlens -c '\conninfo'` | DB | — | T007 | P0 | Low |
| T009 | 0 | Write `backend/.env.example` with `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `ALLOWED_ORIGINS`, `SKILL_COVERAGE_WEIGHT`, `TFIDF_WEIGHT`, `LLM_ENABLED`, `LLM_API_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Env | `backend/.env.example` | T001 | P0 | Low |
| T010 | 0 | Create `docs/erd.md` with a Mermaid `erDiagram` covering all 14 tables from §6 | Docs | `docs/erd.md` | T001 | P0 | Medium |
| T011 | 0 | Delete the stray 0-byte `backend/pathfinder.db` and clear `backend/__pycache__/`; mark the 8 legacy Flask modules and 11 Vite pages frozen in a `docs/legacy-freeze.md` note | Infra | `backend/pathfinder.db` (delete) | T001 | P0 | Low |
| T012 | 0 | Run the proposal §6.4 mitigation "early tutorials" — each pair completes a FastAPI, SQLAlchemy 2.0, spaCy, and Next.js App Router tutorial and posts a 5-minute walkthrough in the shared doc | Team | `docs/tutorials.md` | T002 | P1 | Low |

### Phase 1 — Backend Platform Migration

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T013 | 1 | Create the `backend/app/` package with `__init__.py` files for `app`, `app/core`, `app/db` | Backend | `backend/app/**/__init__.py` | T005 | P0 | Low |
| T014 | 1 | Implement `app/core/config.py` with a `pydantic-settings` `Settings` class: `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`, typed fields, and a `model_validator` that raises if `JWT_SECRET_KEY` is missing or shorter than 32 characters | Backend | `app/core/config.py` | T013 | P0 | Medium |
| T015 | 1 | Implement `app/core/logging.py` — a single `logging.config.dictConfig` with a request-id filter, replacing the ad-hoc `app.logger.setLevel` at `app.py:17` | Backend | `app/core/logging.py` | T013 | P1 | Low |
| T016 | 1 | Implement `app/core/security.py` — `hash_password`/`verify_password` on `passlib[bcrypt]`, and `create_access_token`/`decode_access_token` on PyJWT HS256 emitting `sub`, `role`, `exp`, `iat`, `jti` | Backend | `app/core/security.py` | T014 | P0 | Medium |
| T017 | 1 | Implement `app/core/exceptions.py` — an `APIError` base with `status_code` and `code`, subclasses (`NotFoundError`, `ConflictError`, `ForbiddenError`, `UnprocessableError`), and handlers that render the envelope `{"error":{"code","message","errors":[{"field","message"}]}`, plus a `RequestValidationError` handler and an `IntegrityError` → `409` handler | Backend | `app/core/exceptions.py` | T014 | P0 | Medium |
| T018 | 1 | Implement `app/db/base.py` — `DeclarativeBase`, a `naming_convention` dict for deterministic constraint names, and a `TimestampMixin` supplying `created_at`/`updated_at` as `TIMESTAMPTZ` with `server_default=func.now()` | DB | `app/db/base.py` | T013 | P0 | Medium |
| T019 | 1 | Implement `app/db/session.py` — `create_engine` with `pool_pre_ping=True`, a `SessionLocal` sessionmaker with `expire_on_commit=False`, and `get_db()` as a FastAPI dependency that yields a session and rolls back on exception | DB | `app/db/session.py` | T018, T008 | P0 | Medium |
| T020 | 1 | Implement `app/main.py` — the FastAPI app factory with a `lifespan` handler that verifies the DB connection, restricted `CORSMiddleware` reading `ALLOWED_ORIGINS` (fixes S2 at `app.py:18`), exception handlers from T017, and `GET /` plus `GET /health` | Backend | `app/main.py` | T016, T017, T019 | P0 | Medium |
| T021 | 1 | Add `uvicorn[standard]` to the dev requirements and document `uvicorn app.main:app --reload --port 8000` | Env | `backend/requirements-dev.txt` | T020 | P0 | Low |
| T022 | 1 | Initialise Alembic: `alembic init`, configure `alembic/env.py` to import `app.db.base` metadata and read `DATABASE_URL` from `Settings`, and set `target_metadata` | DB | `backend/alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` | T019 | P0 | Medium |
| T023 | 1 | Write migration `0001_infra_and_user.py` creating `user` and `alembic_version` — `id`, `name VARCHAR(120)`, `email VARCHAR(320) NOT NULL`, `password_hash VARCHAR(255) NOT NULL`, `role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin'))`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`, `updated_at`, plus a functional unique index on `lower(email)` | DB | `alembic/versions/0001_infra_and_user.py` | T022 | P0 | Medium |
| T024 | 1 | Add `backend/.gitignore` covering `.env`, `*.db`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `uploads/` (fixes S6 — no backend ignore file exists today) | Infra | `backend/.gitignore` | T001 | P0 | Low |
| T025 | 1 | Set up `backend/tests/conftest.py` — a `TestClient` fixture, an engine bound to a `careerlens_test` database, a `db_session` fixture that wraps each test in a transaction and rolls back, and a `sample_user` / `sample_admin` fixture | Testing | `backend/tests/conftest.py`, `backend/pytest.ini` | T020 | P0 | Medium |
| T026 | 1 | Write `backend/tests/test_health.py` asserting `GET /` returns the service banner and `GET /health` returns `200` with `"database": "ok"` | Testing | `backend/tests/test_health.py` | T025 | P0 | Low |
| T027 | 1 | Write `backend/tests/test_config.py` asserting the app refuses to start with a missing or short `JWT_SECRET_KEY` | Testing | `backend/tests/test_config.py` | T020 | P1 | Low |
| T028 | 1 | Verify the migration round-trip: `alembic upgrade head` → `downgrade base` → `upgrade head` on a clean database, and confirm no table exists outside a revision | DB | — | T023 | P0 | Low |
| T029 | 1 | Verify CORS: a request with an unlisted `Origin` receives no `Access-Control-Allow-Origin`; a listed one does | Testing | `backend/tests/test_cors.py` | T020 | P1 | Low |
| T030 | 1 | Add `ruff` and `mypy` configuration and make both clean on the Phase 1 files | Quality | `backend/pyproject.toml` | T020 | P1 | Low |

### Phase 2 — Database & Domain Model

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T031 | 2 | Implement `app/models/user.py` — `User` with `Mapped[]` typing, `role` as an `Enum('user','admin')`, `is_active`, and relationships to every child with `cascade="all, delete-orphan"` and `passive_deletes=True` | DB | `app/models/user.py` | T018 | P0 | Medium |
| T032 | 2 | Implement `app/models/profile.py` — `Profile` 1:1 with `user` via a unique FK. Fields: `headline VARCHAR(200)`, `career_goal TEXT`, `bio TEXT`, `location VARCHAR(120)`, `links JSONB` (github/linkedin/portfolio), `years_experience SMALLINT`, `preferred_role_family VARCHAR(80)`. **`skills`, `education`, `experience` columns are not created** | DB | `app/models/profile.py` | T031 | P0 | Medium |
| T033 | 2 | Implement `app/models/skill.py` — `Skill(id, name VARCHAR(120) UNIQUE NOT NULL, slug VARCHAR(120) UNIQUE NOT NULL, category VARCHAR(60) NOT NULL, description TEXT)` and `SkillAlias(alias VARCHAR(120) PRIMARY KEY, skill_id FK→skill ON DELETE CASCADE)` | DB | `app/models/skill.py` | T031 | P0 | Medium |
| T034 | 2 | Implement `app/models/user_skill.py` — `UserSkill` with composite PK `(user_id, skill_id)`, `proficiency SMALLINT NOT NULL DEFAULT 3 CHECK (proficiency BETWEEN 1 AND 5)`, `source VARCHAR(20) NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','cv_extracted'))`, `years_used NUMERIC(3,1)`, `confirmed BOOLEAN NOT NULL DEFAULT true` | DB | `app/models/user_skill.py` | T033 | P0 | Medium |
| T035 | 2 | Implement `app/models/project.py` — `Project(user_id FK, title VARCHAR(160) NOT NULL, description TEXT NOT NULL, tech_stack JSONB NOT NULL DEFAULT '[]', role VARCHAR(120), start_date, end_date, repo_url, is_public BOOLEAN)` with an index on `(user_id)` | DB | `app/models/project.py` | T031 | P0 | Medium |
| T036 | 2 | Implement `app/models/education.py` — `EducationRecord(user_id FK, institution VARCHAR(180) NOT NULL, degree VARCHAR(120) NOT NULL, field_of_study VARCHAR(120), start_year SMALLINT, end_year SMALLINT, grade VARCHAR(40))` and `Certification(user_id FK, name VARCHAR(160) NOT NULL, issuer VARCHAR(160) NOT NULL, issued_on DATE, expires_on DATE, credential_url VARCHAR(400))`, both indexed on `(user_id)` | DB | `app/models/education.py` | T031 | P0 | Medium |
| T037 | 2 | Implement `app/models/job.py` — `JobRole(id, title VARCHAR(140) UNIQUE NOT NULL, slug VARCHAR(140) UNIQUE NOT NULL, family VARCHAR(80) NOT NULL, seniority VARCHAR(40), description TEXT NOT NULL, responsibilities JSONB, is_active BOOLEAN NOT NULL DEFAULT true, created_at, updated_at)` and `JobRoleSkill(job_role_id FK ON DELETE CASCADE, skill_id FK ON DELETE CASCADE, weight NUMERIC(3,2) NOT NULL CHECK (weight > 0 AND weight <= 1), PRIMARY KEY (job_role_id, skill_id))` with an index on `skill_id` for reverse lookup | DB | `app/models/job.py` | T033 | P0 | Medium |
| T038 | 2 | Implement `app/models/resume.py` — `ResumeUpload(id, user_id FK ON DELETE CASCADE, original_filename, stored_filename, content_type, size_bytes, extracted_text TEXT, status VARCHAR(20) CHECK (status IN ('uploaded','extracted','confirmed','failed')), error_message, created_at)` and `ResumeDetectedSkill(resume_upload_id FK ON DELETE CASCADE, skill_id FK ON DELETE CASCADE, surface_form VARCHAR(120), match_start INT, match_end INT, occurrence_count INT, accepted BOOLEAN NOT NULL DEFAULT false, PRIMARY KEY (resume_upload_id, skill_id))` | DB | `app/models/resume.py` | T033 | P0 | Medium |
| T039 | 2 | Implement `app/models/recommendation.py` — `RecommendationRun(id, user_id FK ON DELETE CASCADE, profile_snapshot JSONB, coverage_weight NUMERIC(3,2), tfidf_weight NUMERIC(3,2), engine_version VARCHAR(20), created_at)` and `RecommendationResult(id, run_id FK ON DELETE CASCADE, job_role_id FK ON DELETE RESTRICT, rank INT, compatibility_score NUMERIC(5,4), skill_coverage NUMERIC(6,5), tfidf_similarity NUMERIC(6,5), matched_skill_ids JSONB, missing_skill_ids JSONB, PRIMARY KEY (run_id, job_role_id))` with an index on `(run_id, rank)` | DB | `app/models/recommendation.py` | T037 | P0 | Medium |
| T040 | 2 | Wire `app/models/__init__.py` so importing it registers every mapper, and confirm `Base.metadata` reflects 14 tables | DB | `app/models/__init__.py` | T031–T039 | P0 | Medium |
| T041 | 2 | Write migration `0002_domain_schema.py` generating all domain tables, constraints, and indexes; include an explicit `op.execute` creating the `pg_trgm` extension and a GIN index on `job_role.title` and `job_role.description` for search | DB | `alembic/versions/0002_domain_schema.py` | T040 | P0 | High |
| T042 | 2 | Curation: author `backend/data/skills_taxonomy.json` with ≈150 AI/ML skills, each `{name, slug, category, description, aliases[]}` across 8 categories (Programming & Core, Data Engineering, ML Frameworks, Deep Learning, NLP & LLM, MLOps & Cloud, MLOps & Tooling, Analytics & Communication). Alias examples: `Scikit-learn ← {sklearn, scikit learn, sci-kit learn, SKLearn, sk-learn}`; `TensorFlow ← {tensorflow, tf, tensor-flow}`; `PyTorch ← {pytorch, torch, py-torch}`; `Jupyter ← {jupyter, jupyter notebook, ipython}` | AI/ML | `backend/data/skills_taxonomy.json` | T010 | P0 | High |
| T043 | 2 | Write `app/ml/taxonomy.py` — load the JSON once at import, build `{lowercased_alias_or_name: SkillEntry}` and `{slug: SkillEntry}` indexes, expose `canonicalise(term) -> SkillEntry \| None`, `all_patterns() -> list[str]`, and `validate()` that asserts no alias collides across two different skills | AI/ML | `app/ml/taxonomy.py` | T042 | P0 | Medium |
| T044 | 2 | Write `backend/tests/test_taxonomy.py` — ≥150 skills load, every alias resolves to exactly one skill, no alias is claimed by two skills, `canonicalise("sklearn") == canonicalise("Scikit-learn")` | Testing | `backend/tests/test_taxonomy.py` | T043 | P0 | Medium |
| T045 | 2 | Curation: author `backend/data/job_roles.json` with 50–100 AI/ML roles, each `{title, slug, family, seniority, description, responsibilities[], skills:[{skill_slug, weight}]}` with 8–18 weighted skills per role and weights in `[0.3, 1.0]` summing to ≈ 1.0 per role | AI/ML | `backend/data/job_roles.json` | T042 | P0 | High |
| T046 | 2 | Write `backend/scripts/seed_taxonomy.py` — idempotent upsert of skills then aliases; print `skills: N, aliases: M` | DB | `backend/scripts/seed_taxonomy.py` | T041, T043 | P0 | Medium |
| T047 | 2 | Write `backend/scripts/seed_job_roles.py` — idempotent upsert of roles then their weighted skill sets; validate that every `skill_slug` exists in the taxonomy and fail loudly otherwise; print `roles: N, role_skills: M` | DB | `backend/scripts/seed_job_roles.py` | T046 | P0 | Medium |
| T048 | 2 | Write `backend/scripts/seed_admin.py` (creates the admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD`) and `seed_dev_users.py` (creates 2–3 demo users with realistic skills, projects, and education so manual QA has data); both idempotent | DB | `backend/scripts/seed_admin.py`, `seed_dev_users.py` | T047 | P1 | Medium |

### Phase 3 — Authentication & Authorization

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T049 | 3 | Implement `app/schemas/auth.py` — `RegisterRequest(name 1–120, email EmailStr, password 8–128 with upper+lower+digit validator)`, `LoginRequest`, `UserRead` (never includes `password_hash`), `TokenResponse(user, access_token, token_type='bearer', expires_in)` | Backend | `app/schemas/auth.py` | T016 | P0 | Medium |
| T050 | 3 | Implement `app/api/deps.py` — `get_db` re-export, `get_current_user` (decode token, load `User`, 401 on missing/invalid/expired or `is_active = false`), `require_user`, and `require_role("admin")` returning 403 for an authenticated non-admin. This replaces the single inline check at `guidance.py:157-163` | Backend | `app/api/deps.py` | T016, T019 | P0 | Medium |
| T051 | 3 | Implement `app/services/auth_service.py` — `register_user` (normalise email, 409 on conflict, create `User` + empty `Profile` in one transaction), `authenticate` (constant-time verify, 401 with an identical message for unknown-user and wrong-password), and `build_token_response` | Backend | `app/services/auth_service.py` | T050 | P0 | Medium |
| T052 | 3 | Implement `app/api/routes/auth.py` — `POST /api/auth/register` (201), `POST /api/auth/login` (200), `POST /api/auth/logout` (204), `POST /api/auth/refresh` (200), `GET /api/auth/me` (200) | Backend | `app/api/routes/auth.py` | T051 | P0 | Medium |
| T053 | 3 | Implement `app/api/router.py` aggregating all routers under a `/api` prefix and register it in `app/main.py` | Backend | `app/api/router.py`, `app/main.py` | T052 | P0 | Low |
| T054 | 3 | Write `backend/tests/test_auth.py` — register success, duplicate email → 409, weak password → 422, malformed email → 422, login success, wrong password → 401, unknown email → 401 with the same message, `me` without token → 401, `me` with expired token → 401 | Testing | `backend/tests/test_auth.py` | T052 | P0 | Medium |
| T055 | 3 | Write `backend/tests/test_roles.py` — a `require_role('admin')` probe route proves 200 for admin, 403 for user, 401 for anonymous; asserts `password_hash` never appears in any response body | Testing | `backend/tests/test_roles.py` | T054 | P0 | Medium |
| T056 | 3 | Implement `POST /api/auth/refresh` — issue a new token for a still-valid subject, preserving `role` from the database rather than the old token | Backend | `app/api/routes/auth.py` | T052 | P1 | Low |
| T057 | 3 | Port the client-side password policy from `Register.tsx:59-63` to `frontend/src/lib/schemas.ts` as a zod schema so client and server enforce the same rule | Frontend | `frontend/src/lib/schemas.ts` | T049 | P1 | Low |
| T058 | 3 | Build `frontend/src/lib/auth/session.ts` and `frontend/src/components/providers/AuthProvider.tsx`, preserving the existing `localStorage` keys (`token`, `user`) from `Login.tsx:54-55` and `Register.tsx:97-98` | Frontend | `frontend/src/lib/auth/session.ts`, `providers/AuthProvider.tsx` | T052 | P0 | Medium |
| T059 | 3 | Port the `handleLogout` behaviour at `Header.tsx:32-36` into `AuthProvider.logout()`, adding the `POST /api/auth/logout` call before clearing state | Frontend | `providers/AuthProvider.tsx` | T058 | P0 | Low |
| T060 | 3 | Write `frontend/src/middleware.ts` — redirect unauthenticated users away from `/dashboard`, `/profile`, `/skills`, `/projects`, `/education`, `/certifications`, `/resume`, `/recommendations`, `/skill-gap`; redirect non-admins away from `/admin/*`; preserve the attempted path for post-login redirect | Frontend | `frontend/src/middleware.ts` | T058 | P0 | Medium |
| T061 | 3 | Write `frontend/src/components/layout/Header.tsx` with links that all resolve: Dashboard, Profile, Skills, Projects, Education, Certifications, Resume, Recommendations, Skill Gap, Feedback, Sign out; plus an admin group. Corrects the four dead links at `Header.tsx:101,106,170,179` (correction C1) | Frontend | `frontend/src/components/layout/Header.tsx` | T059 | P0 | Medium |
| T062 | 3 | Port `Register.tsx` so `educationLevel` is actually sent — fixing the silent data loss at `Register.tsx:92` — and route it to `Profile.preferred_role_family` or a dedicated `profile.education_level` field | Frontend | `app/(public)/register/page.tsx`, `app/schemas/profile.py` | T057, T032 | P0 | Medium |

### Phase 4 — CRUD APIs

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T063 | 4 | Implement `app/schemas/profile.py` — `ProfileCreate`, `ProfileUpdate` (all-optional, distinguishes absent from null), `ProfileRead` including nested `skills_count`, `projects_count`, `education_count`, `certifications_count` | Backend | `app/schemas/profile.py` | T032 | P0 | Medium |
| T064 | 4 | Implement `app/services/profile_service.py` — `get_or_create`, `get`, `update`, `delete` (deletes the `Profile` only, leaving the `User` and its auth intact, so a user can rebuild without re-registering) | Backend | `app/services/profile_service.py` | T063 | P0 | Medium |
| T065 | 4 | Implement `app/api/routes/profile.py` — `POST /api/profile` 201, `GET /api/profile` 200, `PATCH /api/profile` 200, `DELETE /api/profile` 204. All scoped to the current user; no path parameter, so no IDOR is possible by construction | Backend | `app/api/routes/profile.py` | T064 | P0 | Medium |
| T066 | 4 | Implement `app/schemas/skill.py` — `SkillRead`, `UserSkillCreate(skill_id, proficiency, years_used?)`, `UserSkillUpdate(proficiency?, years_used?, confirmed?)`, `UserSkillRead`, `DetectedSkillConfirm(skills: list[{skill_id, accepted, proficiency?}])`, `ConfirmResult(added, updated, skipped)` | Backend | `app/schemas/skill.py` | T034 | P0 | Medium |
| T067 | 4 | Implement `app/services/skill_service.py` — `list_user_skills` (joined with `skill` for name/category), `add_skill` (422 if `skill_id` is not in the taxonomy, 409 if already present), `update_skill`, `remove_skill`, `search_taxonomy(q, category, limit, offset)`, and `confirm_detected_skills` (bulk upsert, idempotent, sets `source='cv_extracted'` and `confirmed=true`) | Backend | `app/services/skill_service.py` | T066 | P0 | High |
| T068 | 4 | Implement `app/api/routes/skills.py` — `GET /api/skills` (my skills), `POST /api/skills` 201, `PATCH /api/skills/{skill_id}` 200, `DELETE /api/skills/{skill_id}` 204, `GET /api/skills/taxonomy?q=&category=&limit=&offset=` 200, `POST /api/skills/confirm` 200 | Backend | `app/api/routes/skills.py` | T067 | P0 | High |
| T069 | 4 | Implement `app/schemas/project.py` and `app/services/project_service.py` — CRUD plus a `tech_stack` validator that canonicalises each entry through `ml.taxonomy.canonicalise` so `"sklearn"` in a project is stored as the `Scikit-learn` slug | Backend | `app/schemas/project.py`, `app/services/project_service.py` | T035, T043 | P0 | Medium |
| T070 | 4 | Implement `app/api/routes/projects.py` — `GET /api/projects`, `POST /api/projects` 201, `GET /api/projects/{id}`, `PATCH /api/projects/{id}`, `DELETE /api/projects/{id}` 204, all with an ownership filter | Backend | `app/api/routes/projects.py` | T069 | P0 | Medium |
| T071 | 4 | Implement `app/schemas/education.py` and `app/services/education_service.py` — CRUD for `EducationRecord` and `Certification`, with `end_year >= start_year` and `expires_on > issued_on` validators | Backend | `app/schemas/education.py`, `app/services/education_service.py` | T036 | P0 | Medium |
| T072 | 4 | Implement `app/api/routes/education.py` and `app/api/routes/certifications.py` — full CRUD on both, with ownership filters | Backend | `app/api/routes/education.py`, `app/api/routes/certifications.py` | T071 | P0 | Medium |
| T073 | 4 | Implement `app/schemas/job.py` — `JobRoleCreate(title, family, seniority, description, responsibilities[], skills[{skill_id, weight}])`, `JobRoleUpdate` (all-optional), `JobRoleRead` (includes `skills[{skill_id, skill_name, weight}]`), `JobRoleSummary` (public read, no weights) | Backend | `app/schemas/job.py` | T037 | P0 | Medium |
| T074 | 4 | Implement `app/services/job_service.py` — `list_active`, `get`, `create`, `update`, `delete`, `replace_skills` (single transaction: delete existing `job_role_skill` then insert the new set; a validation failure aborts before the delete), and `families()` for the filter dropdown | Backend | `app/services/job_service.py` | T073 | P0 | High |
| T075 | 4 | Implement `app/api/routes/jobs.py` — public read: `GET /api/jobs`, `GET /api/jobs/families`, `GET /api/jobs/{id}`. Admin write: `POST /api/jobs`, `PATCH /api/jobs/{id}`, `DELETE /api/jobs/{id}`, `PUT /api/jobs/{id}/skills` — each behind `require_role("admin")` | Backend | `app/api/routes/jobs.py` | T074 | P0 | High |
| T076 | 4 | Write `backend/tests/test_profile_crud.py` — full C/R/U/D plus delete-then-404 | Testing | `backend/tests/test_profile_crud.py` | T065 | P0 | Medium |
| T077 | 4 | Write `backend/tests/test_skills_crud.py` — add, update proficiency, remove, duplicate → 409, unknown skill → 422, taxonomy search paging, and bulk confirm idempotency | Testing | `backend/tests/test_skills_crud.py` | T068 | P0 | Medium |
| T078 | 4 | Write `backend/tests/test_projects_crud.py` and `backend/tests/test_education_crud.py` — full C/R/U/D, tech-stack canonicalisation, and year-range validation | Testing | `backend/tests/test_projects_crud.py`, `test_education_crud.py` | T070, T072 | P0 | Medium |
| T079 | 4 | Write `backend/tests/test_jobs_crud.py` — admin create/update/delete, `replace_skills` atomicity, family filter, and a non-admin receiving 403 on every write | Testing | `backend/tests/test_jobs_crud.py` | T075 | P0 | Medium |
| T080 | 4 | Write `backend/tests/test_ownership.py` — user A cannot read/update/delete user B's project, education record, certification, or skill; every case returns 404 (not 403) to avoid confirming row existence | Testing | `backend/tests/test_ownership.py` | T070, T072 | P0 | Medium |
| T081 | 4 | Verify cascade behaviour in a test: deleting a `user` removes `profile`, `user_skill`, `project`, `education_record`, `certification`, `resume_upload`, `resume_detected_skill`, `recommendation_run`, and `recommendation_result` in a single statement | Testing | `backend/tests/test_cascade.py` | T041 | P0 | Medium |
| T082 | 4 | Add `GET /api/dashboard/summary` returning real aggregates — skill count, project count, education count, certification count, latest run timestamp, top role — replacing the fabricated `mockStats` at `Dashboard.tsx:70-75` | Backend | `app/api/routes/dashboard.py`, `app/schemas/dashboard.py` | T065, T068 | P0 | Medium |
| T083 | 4 | Add `GET /api/dashboard/completeness` returning a 0–100 profile-completeness score derived from real field presence, so the dashboard progress bar is not fabricated | Backend | `app/api/routes/dashboard.py` | T082 | P1 | Low |
| T084 | 4 | Implement a shared pagination helper — a Pydantic generic `Page[T]` with `total`, `page`, `page_size`, `items`, a `page_params` dependency clamping `page_size` to 1–100, and `ORDER BY created_at DESC, id DESC` so paging is stable | Backend | `app/schemas/pagination.py`, `app/api/deps.py` | T073 | P0 | Medium |
| T085 | 4 | Apply `Page[T]` to every list endpoint (`/skills`, `/projects`, `/education`, `/certifications`, `/jobs`, `/admin/jobs`, `/admin/users`, `/recommendations/runs`) so no endpoint returns an unbounded result set | Backend | all list routers | T084 | P0 | Medium |
| T086 | 4 | Write `backend/tests/test_error_envelope.py` — assert that a validation failure returns `422` with `{error:{code, message, errors:[{field, message}]}}` and that **no response body anywhere contains a Python exception message, a traceback, or a SQL string** | Testing | `backend/tests/test_error_envelope.py` | T017 | P0 | Medium |
| T087 | 4 | Write `backend/tests/test_pagination.py` — page through a 25-row collection and assert no row is duplicated or skipped across pages, and that `page_size > 100` is clamped | Testing | `backend/tests/test_pagination.py` | T085 | P0 | Medium |
| T088 | 4 | Configure OpenAPI metadata (title `CareerLens AI API`, version, description, per-router `tags` with summaries) and export a committed `docs/api.md` reference so the API is documented without hand-maintenance | Docs | `app/main.py`, `docs/api.md` | T075 | P1 | Low |
| T089 | 4 | Write `backend/tests/test_list_scoping.py` — seed two users, give each distinct skills/projects/education/certifications/uploads, then assert that **every** user-scoped list endpoint returns only the caller's rows. T080 covers single-resource access; this covers the list filters, which is where a missing `user_id` predicate would hide | Testing | `backend/tests/test_list_scoping.py` | T085, T080 | P0 | Medium |
| T090 | 4 | Write `backend/tests/test_route_contracts.py` — walk `app.openapi()`, and for every path+method assert the route is reachable and that any path parameter named `id` sits behind an ownership-scoped query. A route added without a contract test fails here | Testing | `backend/tests/test_route_contracts.py` | T088 | P1 | Medium |

### Phase 5 — AI/ML Engine

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T091 | 5 | Define `app/ml/types.py` — frozen dataclasses `ProfileSnapshot`, `SkillRef(skill_id, name, slug, category)`, `UserSkillFact(skill_id, proficiency)`, `RoleSpec(job_role_id, title, family, description, required_skills: dict[skill_id, float])`, `RoleScore`, `GapReport`. **This is the ML layer's public contract and it must not import SQLAlchemy or FastAPI** | AI/ML | `app/ml/types.py` | T040 | P0 | Medium |
| T092 | 5 | Implement `app/ml/text_loader.py` — `extract_text(path, content_type)` dispatching to `pdfplumber` (PDF) and `python-docx` (DOCX), with a 5 MB size guard, an empty-text check, and a `ScannedDocumentError` raised when a PDF yields under 50 characters so the route can return a clear "OCR is not supported" message (proposal §11) | AI/ML | `app/ml/text_loader.py` | T005 | P0 | Medium |
| T093 | 5 | Write `backend/tests/test_text_loader.py` — build a PDF and a DOCX fixture in-test, assert text extraction, assert oversize rejection, assert `ScannedDocumentError` for a textless PDF | Testing | `backend/tests/test_text_loader.py` | T092 | P0 | Medium |
| T094 | 5 | Implement `app/ml/extractor.py` — normalise text (collapse whitespace, strip bullets and separators), build a spaCy `PhraseMatcher` from `taxonomy.all_patterns()` with `PhraseMatcher.ATTRS \| {"ORTH": {}}` and `NORM` case-insensitive matching, then map each match back to its `skill_id` via the alias index. Return `DetectedSkill(skill_id, canonical_name, surface_form, count, start, end)`, de-duplicated and sorted by descending `count` | AI/ML | `app/ml/extractor.py` | T043, T092 | P0 | High |
| T095 | 5 | Write `backend/tests/test_extractor.py` — a synthetic CV text fixture asserting that `sklearn`, `PyTorch`, `pandas`, `SQL`, `Docker`, `TensorFlow`, and `spaCy` are all detected; that `Java` does not match inside `JavaScript`; that `Go` does not match inside `MongoDB`; and that the same text yields identical output on two runs | Testing | `backend/tests/test_extractor.py` | T094 | P0 | High |
| T096 | 5 | Implement `app/ml/text_profile.py` — build `ProfileSnapshot.profile_text` from confirmed skills, project titles/descriptions/tech stacks, education, and the profile headline/goal. This text is the TF-IDF input | AI/ML | `app/ml/text_profile.py` | T091 | P0 | Medium |
| T097 | 5 | Implement `app/ml/matcher.py` — `weighted_skill_coverage(user_skill_ids_with_proficiency, required_skills) -> float` using `Σ(role_weight × proficiency_factor) / Σ(role_weight)` where `proficiency_factor = (proficiency - 1) / 4`; and `tfidf_cosine(profile_text, role_specs) -> list[float]` that **fits `TfidfVectorizer` per call** on `[profile_text] + [role.description for role in role_specs]` with `ngram_range=(1,2)`, `sublinear_tf=True`, `min_df=1`, and returns cosine similarity against the first row | AI/ML | `app/ml/matcher.py` | T096 | P0 | High |
| T098 | 5 | Write `backend/tests/test_matcher.py` — coverage of 1.0 for an exact superset, 0.0 for no overlap, a hand-computed intermediate value, bounds assertions on 200 random-ish inputs, and monotonicity (adding a skill never lowers coverage) | Testing | `backend/tests/test_matcher.py` | T097 | P0 | High |
| T099 | 5 | Write `backend/tests/test_determinism.py` — run the full ranker twice on the same snapshot and assert deep equality of the serialised result; this is the gate that makes Phase 9's evaluation reproducible | Testing | `backend/tests/test_determinism.py` | T097 | P0 | Medium |
| T100 | 5 | Implement `app/ml/gap_analysis.py` — `analyse(user_skills, role_spec) -> GapReport` returning `matched: list[(skill_id, weight, proficiency)]`, `missing: list[(skill_id, weight)]` sorted by descending weight, plus `coverage` and a `tier_of(weight)` helper (`critical ≥ 0.8`, `important ≥ 0.5`, else `desirable`) | AI/ML | `app/ml/gap_analysis.py` | T091 | P0 | Medium |
| T101 | 5 | Write `backend/tests/test_gap_analysis.py` — `required − present` correctness, ordering by descending weight, tier boundaries at exactly 0.8 and 0.5, and the empty-user case | Testing | `backend/tests/test_gap_analysis.py` | T100 | P0 | Medium |
| T102 | 5 | Implement `app/ml/ranker.py` — `rank(profile_snapshot, role_specs, coverage_weight, tfidf_weight, top_n) -> list[RoleScore]`, computing both components per role, combining as `w₁·coverage + w₂·cosine`, sorting by `(-score, job_role_id)` for a **total order** so ties are deterministic, and returning per-role matched/missing skill ids for explainability | AI/ML | `app/ml/ranker.py` | T097, T100 | P0 | High |
| T103 | 5 | Implement `app/ml/learning_path.py` — an **optional**, `LLM_ENABLED=False`-gated module that takes an already-computed `GapReport` and formats a short learning path. It must import nothing outside `app/ml/types.py` and the stdlib until the flag is on, and it must never be on the path of `POST /api/recommendations` | AI/ML | `app/ml/learning_path.py` | T102 | P2 | Medium |
| T104 | 5 | Implement `app/schemas/recommendation.py` — `RecommendationRequest(limit=10, role_family?, min_score?)`, `SkillContribution(skill_id, name, weight, proficiency?)`, `RoleRecommendation(job_role_id, title, family, seniority, rank, compatibility_pct, skill_coverage, tfidf_similarity, matched_skills[], missing_skills[])`, `RecommendationResponse(run_id, engine_version, weights{coverage, tfidf}, generated_at, results[], total_candidates)` | Backend | `app/schemas/recommendation.py` | T102 | P0 | Medium |
| T105 | 5 | Implement `app/services/recommendation_service.py` — the DB↔ML bridge: load `Profile` + `UserSkill` + `Project` + `EducationRecord` in one query set; load active `JobRole` + `JobRoleSkill` in one; build `ProfileSnapshot`; call `ml.ranker.rank`; persist `RecommendationRun` + `RecommendationResult`; return the response. **This is the only module that touches both SQLAlchemy and `ml/`** | Backend | `app/services/recommendation_service.py` | T104 | P0 | High |
| T106 | 5 | Implement `app/schemas/gap.py` and `GET /api/skill-gap/{job_role_id}` returning matched, missing-with-weights, tiers, and the optional learning path when enabled | Backend | `app/schemas/gap.py`, `app/api/routes/skill_gap.py` | T105 | P0 | Medium |
| T107 | 5 | Implement `app/services/cv_service.py` and `app/api/routes/cv.py` — `POST /api/cv/upload` (auth required, allowlist `.pdf`/`.docx` by extension **and** content type, size guard, store to `UPLOAD_DIR/{uuid}{ext}`, extract text, run the extractor, persist `ResumeUpload(status='extracted')` + `ResumeDetectedSkill` rows, return `detected_skills[]` unconfirmed); `GET /api/cv/{id}` (own only, fixes the IDOR at `guidance.py:31`); `DELETE /api/cv/{id}`; `GET /api/cv/{id}/text` | Backend | `app/services/cv_service.py`, `app/api/routes/cv.py`, `app/schemas/cv.py` | T094, T068 | P0 | High |
| T108 | 5 | Implement `app/api/routes/recommendations.py` — `POST /api/recommendations` 201 returning the ranked response, `GET /api/recommendations/runs` (paged history), `GET /api/recommendations/runs/{id}` (a persisted run, used by `/recommendations/[id]`) | Backend | `app/api/routes/recommendations.py` | T105 | P0 | Medium |

### Phase 6 — Frontend Migration to Next.js

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T109 | 6 | Scaffold `create-next-app` in a temp directory and move the result over `frontend/`, preserving `src/components/ui`, `src/lib/utils.ts`, `src/hooks`, `src/index.css`, `tailwind.config.ts`, `postcss.config.js`, and `components.json` | Frontend | `frontend/**` | T058 | P0 | Medium |
| T110 | 6 | Update `frontend/components.json` to `"rsc": true` and re-run the shadcn CLI to confirm no component needs regeneration | Frontend | `frontend/components.json` | T109 | P0 | Low |
| T111 | 6 | Move `src/index.css` to `app/globals.css` and import it in `app/layout.tsx`; verify `tailwind.config.ts` requires **no** `content` change (its globs already include `./app/**`) | Frontend | `app/globals.css`, `app/layout.tsx` | T109 | P0 | Low |
| T112 | 6 | Create `app/layout.tsx` (metadata `CareerLens AI`, fonts, `<Providers>`), `src/components/providers/{QueryProvider,ThemeProvider}.tsx`, and keep `AuthProvider` from T058 | Frontend | `app/layout.tsx`, `providers/*.tsx` | T109, T058 | P0 | Medium |
| T113 | 6 | Create `app/(public)/layout.tsx` with `Header` + `Footer`; port `Header.tsx` to `next/link` + `usePathname` + `useRouter`, preserving its `isAuthenticated`/`isAdmin`/`userEmail` props and its mobile menu | Frontend | `app/(public)/layout.tsx`, `components/layout/Header.tsx` | T112 | P0 | Medium |
| T114 | 6 | Port `Footer.tsx` to `next/link` and change every "CareerGuide AI" string to "CareerLens AI" (`Footer.tsx:44,126`) | Frontend | `components/layout/Footer.tsx` | T113 | P0 | Low |
| T115 | 6 | Port `Landing.tsx` → `app/(public)/page.tsx`, `About.tsx` → `about/page.tsx`, `Features.tsx` → `features/page.tsx`, `NotFound.tsx` → `app/not-found.tsx`, changing all "CareerGuide AI" copy (`Landing.tsx:44,138,203`, `About.tsx:77`) | Frontend | `app/(public)/**/page.tsx` | T113 | P0 | Medium |
| T116 | 6 | Port `Login.tsx` → `app/(public)/login/page.tsx` as a client component; wire to `useAuth().login`; use `useSearchParams` to honour the post-login redirect that `src/middleware.ts` records | Frontend | `app/(public)/login/page.tsx` | T113, T059 | P0 | Medium |
| T117 | 6 | Port `Register.tsx` → `app/(public)/register/page.tsx`, including the T062 fix so `educationLevel` is sent, and preserve the strong client-side policy at `Register.tsx:59-63` | Frontend | `app/(public)/register/page.tsx` | T116, T062 | P0 | Medium |
| T118 | 6 | Create the guarded `app/(app)/layout.tsx` — server component that redirects to `/login` when there is no session, rendering `Header`, a sidebar, and the content slot | Frontend | `app/(app)/layout.tsx` | T112, T060 | P0 | Medium |
| T119 | 6 | Create the guarded `app/(admin)/layout.tsx` redirecting non-admins to `/dashboard` | Frontend | `app/(admin)/layout.tsx` | T118 | P0 | Low |
| T120 | 6 | Create `src/lib/api/config.ts` (`NEXT_PUBLIC_API_URL`, default `http://localhost:8000`) and `src/lib/api/client.ts` — a typed `request<T>()` preserving the error-enrichment pattern from `client.ts:20-29`, plus `apiFetch`, `apiUpload` (FormData), and a `ApiError` class carrying `status` and `body` | Frontend | `src/lib/api/{config,client}.ts` | T109 | P0 | Medium |
| T121 | 6 | Create per-domain API modules: `auth.ts`, `profile.ts`, `skills.ts`, `projects.ts`, `education.ts`, `certifications.ts`, `jobs.ts`, `recommendations.ts`, `cv.ts`, `admin.ts`, each exporting typed functions matching §7 exactly | Frontend | `src/lib/api/*.ts` | T120 | P0 | Medium |
| T122 | 6 | Create `src/lib/schemas.ts` — zod mirrors of the Pydantic request models for client-side validation with server-field-error mapping | Frontend | `src/lib/schemas.ts` | T120 | P0 | Medium |
| T123 | 6 | Create the shared UI states: `Loading` (skeletons), `EmptyState`, `ErrorState` (with retry), `ConfirmDialog` (wrapping the existing `AlertDialog`), `PageHeader` | Frontend | `src/components/shared/*.tsx` | T112 | P0 | Medium |
| T124 | 6 | Create React Query hook modules under `src/lib/hooks/` for profile, skills, projects, education, certifications, jobs, recommendations, CV, and dashboard summary, with correct `queryKey` arrays and invalidation on mutation | Frontend | `src/lib/hooks/*.ts` | T121 | P0 | Medium |
| T125 | 6 | Delete the Vite surface: `vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/App.css`, `src/vite-env.d.ts`, `src/pages/**`, `src/api/`, `.env`, `.env.development`, `bun.lockb`; remove `vite`, `@vitejs/plugin-react-swc`, `react-router-dom` from `package.json`; verify `npm run build` and `npm run lint` are clean | Frontend | `frontend/**` | T114–T124 | P0 | High |

### Phase 7 — Frontend Integration

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T126 | 7 | Build `app/(app)/dashboard/page.tsx` — real aggregates from `GET /api/dashboard/summary` and `GET /api/dashboard/completeness`, plus onboarding checklist links. Delete `mockUser` (`Dashboard.tsx:22-27`), `mockQuizStatus` (`:29-33`), `mockRecommendations` (`:37`), `mockStats` (`:70-75`) and the `setTimeout` loading simulation (`:83-86`) | Frontend | `app/(app)/dashboard/page.tsx` | T124 | P0 | High |
| T127 | 7 | Build `src/features/profile/{ProfileForm.tsx,schemas.ts}` and `app/(app)/profile/page.tsx` — create, read, edit, and delete the profile, with field-level server errors and a delete confirmation that states exactly what will be removed | Frontend | `features/profile/**`, `app/(app)/profile/page.tsx` | T126, T065 | P0 | High |
| T128 | 7 | Build `src/features/skills/{SkillPicker,SkillList,DetectedSkillsPanel}.tsx` and `app/(app)/skills/page.tsx` — taxonomy search with debounce, add skill, change proficiency 1–5, remove skill, and the CV-detected confirmation panel | Frontend | `features/skills/**`, `app/(app)/skills/page.tsx` | T126, T068 | P0 | High |
| T129 | 7 | Build `src/features/projects/{ProjectForm,ProjectCard}.tsx` and `app/(app)/projects/page.tsx` — full C/R/U/D with a tech-stack tag input that offers taxonomy suggestions | Frontend | `features/projects/**`, `app/(app)/projects/page.tsx` | T126, T070 | P0 | High |
| T130 | 7 | Build `src/features/education/{EducationForm,CertificationForm}.tsx` and `app/(app)/education/page.tsx` + `app/(app)/certifications/page.tsx` — full C/R/U/D for both entities | Frontend | `features/education/**`, `app/(app)/education/page.tsx`, `certifications/page.tsx` | T126, T072 | P0 | Medium |
| T131 | 7 | Build `app/(app)/resume/page.tsx` — `CvDropzone` with drag-and-drop, client-side 5 MB and extension pre-check, upload progress, the loading and error states, and the `DetectedSkillsPanel` feeding `POST /api/skills/confirm` then navigating to `/skills` | Frontend | `app/(app)/resume/page.tsx`, `features/cv/*` | T128, T107 | P0 | High |
| T132 | 7 | Port `Feedback.tsx` → `app/(public)/feedback/page.tsx`, preserving its payload shape, and decide whether to keep the endpoint — retained as a thin in-app feature, but its `Event` analytics table is not recreated | Frontend | `app/(public)/feedback/page.tsx` | T113 | P2 | Low |
| T133 | 7 | Build `src/features/admin/{JobRoleForm,SkillWeightEditor,JobRoleTable}.tsx` and `app/(admin)/admin/jobs/page.tsx` + `[id]/page.tsx` — create a role, add/remove required skills, set each importance weight with a slider and numeric input, edit, and delete | Frontend | `features/admin/**`, `app/(admin)/admin/jobs/**` | T126, T075 | P0 | High |
| T134 | 7 | Build `app/(admin)/admin/page.tsx` — an admin overview: role count, family distribution, most-required skills, total users, and recent recommendation runs | Frontend | `app/(admin)/admin/page.tsx` | T133 | P1 | Medium |
| T135 | 7 | Verify every CRUD cell in §8 is reachable by clicking: walk the matrix in a browser and record a screenshot per cell | Frontend | — | T127–T133 | P0 | Medium |
| T136 | 7 | Add global error handling: a React Query `onError` that surfaces an `ApiError` body as a toast, and a `not-found` boundary per segment | Frontend | `src/components/providers/QueryProvider.tsx`, `app/**/error.tsx` | T124 | P1 | Medium |
| T137 | 7 | Verify responsive behaviour at 375 px, 768 px, and 1280 px for every page, fixing overflow and collapsed tables | Frontend | all pages | T126–T134 | P0 | Medium |
| T138 | 7 | Verify keyboard navigation and visible focus rings across forms and dialogs | Frontend | all pages | T135 | P1 | Low |
| T139 | 7 | Run `npm run build` and `npm run lint`; fix every error and warning | Frontend | — | T135 | P0 | Low |
| T140 | 7 | Execute the §12 user journey end to end in a browser with the network panel open; confirm zero console errors and zero unexpected 4xx/5xx | Testing | — | T139 | P0 | Medium |

### Phase 8 — Recommendation & Skill-Gap UX

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T141 | 8 | Build `app/(app)/recommendations/page.tsx` — a `useMutation` on `POST /api/recommendations` triggered by a "Generate recommendations" action (never on mount, so no wasted computation), then `RecommendationCard` per role showing title, family, rank, compatibility %, and the top 3 matched and missing skills | Frontend | `app/(app)/recommendations/page.tsx`, `features/recommendations/*` | T108, T126 | P0 | High |
| T142 | 8 | Build `ScoreBreakdown.tsx` — two labelled progress bars for `skill_coverage` and `tfidf_similarity`, the weights used, and the formula `w₁·coverage + w₂·cosine` rendered literally, so a user can see exactly how the percentage was produced | Frontend | `features/recommendations/ScoreBreakdown.tsx` | T141 | P0 | Medium |
| T143 | 8 | Build `app/(app)/recommendations/[id]/page.tsx` — render a **persisted** run from `GET /api/recommendations/runs/{id}` (not a recomputation), with the role detail, full matched and missing lists, and a link into the skill-gap view | Frontend | `app/(app)/recommendations/[id]/page.tsx` | T141 | P0 | Medium |
| T144 | 8 | Build `app/(app)/skill-gap/page.tsx` — a role selector (searchable, grouped by family), the target role's coverage percentage, a `GapTable` of matched and missing skills with each importance weight and its tier badge | Frontend | `app/(app)/skill-gap/page.tsx`, `features/skill-gap/*` | T106, T141 | P0 | High |
| T145 | 8 | Build `LearningPathCard.tsx` — renders the optional LLM learning path when `LLM_ENABLED` is on and the run carries one, and shows a clear "not enabled" state otherwise, so the core flow never depends on it | Frontend | `features/skill-gap/LearningPathCard.tsx` | T144 | P2 | Low |
| T146 | 8 | Add an empty-state path: a user with zero confirmed skills sees a call to action to `/skills` or `/resume` instead of a list of 0 % roles | Frontend | `app/(app)/recommendations/page.tsx` | T141 | P0 | Low |
| T147 | 8 | Add run history: a list of past runs with their timestamps and top role, linking to `/recommendations/[id]` | Frontend | `features/recommendations/RunHistory.tsx` | T143 | P1 | Low |
| T148 | 8 | Build `app/(admin)/admin/evaluation/page.tsx` — renders the committed `docs/evaluation_report.md` metrics as a `recharts` figure (top-1 accuracy, top-3 hit rate, MRR) and the weight-sweep table | Frontend | `app/(admin)/admin/evaluation/page.tsx` | T160, T133 | P1 | Medium |
| T149 | 8 | Verify recommendation latency: `POST /api/recommendations` for a 25-skill profile against 60 roles returns in under 2 seconds on a laptop CPU (proposal §7.5 "within a few seconds") | Testing | — | T141 | P0 | Low |
| T150 | 8 | Verify explainability: for a randomly chosen run, confirm that `matched_skills ∪ missing_skills` equals the role's full required-skill set and that the two partition it without overlap | Testing | `backend/tests/test_explainability.py` | T141 | P0 | Medium |

### Phase 9 — Testing & AI Evaluation

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T151 | 9 | Design and author `app/ml/evaluation/labelled_profiles.jsonl` with 24 profiles, each `{id, name, skills[{skill_slug, proficiency}], projects[], education[], expected_role, expected_family, rationale}`. Cover 10–12 role families with 2 profiles each, deliberately including 3 near-boundary cases where a secondary role is also plausible, and record the rationale for each label | AI/ML | `app/ml/evaluation/labelled_profiles.jsonl` | T102, T045 | P0 | High |
| T152 | 9 | Implement `app/ml/evaluation/metrics.py` — `top1_accuracy`, `top3_hit_rate`, `mean_reciprocal_rank`, `mean_compatibility_of_expected`, and per-component means, all pure functions over `(labels, predictions)` | AI/ML | `app/ml/evaluation/metrics.py` | T151 | P0 | Medium |
| T153 | 9 | Implement `app/ml/evaluation/harness.py` — load the labels, build a `ProfileSnapshot` per profile, run `ml.ranker.rank` against the live job knowledge base (or a JSON snapshot for reproducibility), and compute the metrics | AI/ML | `app/ml/evaluation/harness.py` | T152 | P0 | High |
| T154 | 9 | Implement `app/ml/evaluation/tuning.py` — sweep `SKILL_COVERAGE_WEIGHT` over `[0.5, 0.6, 0.7, 0.8, 0.9]` with the complement as the TF-IDF weight, print a metrics table per weight, and recommend the best top-3 hit rate with ties broken toward the proposal's 0.6 | AI/ML | `app/ml/evaluation/tuning.py` | T153 | P0 | Medium |
| T155 | 9 | Implement `app/ml/evaluation/__main__.py` — `python -m app.ml.evaluation` prints the metrics table, writes `docs/evaluation_report.md`, and exits non-zero if the top-3 target is missed | AI/ML | `app/ml/evaluation/__main__.py` | T154 | P0 | Medium |
| T156 | 9 | Write `backend/tests/test_evaluation.py` — runs the harness in-process and asserts top-3 hit rate ≥ 0.75, making the metric a **regression gate** rather than a one-time number | Testing | `backend/tests/test_evaluation.py` | T155 | P0 | Medium |
| T157 | 9 | Write `docs/evaluation_report.md` — labelled-profile methodology, per-profile predictions, the metrics table, the weight sweep with the chosen values justified, the design-honesty disclosure (no trained classifier, per proposal §4.2), and the threats to validity | Docs | `docs/evaluation_report.md` | T155 | P0 | Medium |
| T158 | 9 | Add 3 consented or fully anonymised sample CVs under `app/ml/evaluation/sample_cvs/` plus `backend/tests/fixtures/`, and add a `test_extraction_pipeline.py` that runs the full PDF/DOCX → text → extract pipeline end to end | Testing | `app/ml/evaluation/sample_cvs/`, `backend/tests/fixtures/`, `test_extraction_pipeline.py` | T094 | P0 | Medium |
| T159 | 9 | Delete the ad-hoc `backend/scripts/e2e_test.py` (hardcoded to `127.0.0.1:5001`) and confirm the full suite is `pytest`-only | Infra | `backend/scripts/e2e_test.py` (delete) | T156 | P0 | Low |
| T160 | 9 | Run the complete suite: `pytest --cov=app --cov-report=term-missing`, confirm ≥ 60 tests and 0 failures, and record the coverage figure in the report | Testing | — | T156, T159 | P0 | Medium |

### Phase 10 — Deployment

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T161 | 10 | Rewrite `backend/Dockerfile` on `python:3.12-slim` — install `requirements.txt`, `python -m spacy download en_core_web_sm` in the build step, create a non-root user, expose 8000, and `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` (replacing gunicorn at `Dockerfile:7`) | Infra | `backend/Dockerfile` | T160 | P0 | Medium |
| T162 | 10 | Add an `api` service to `docker-compose.yml` building from `backend/Dockerfile`, depending on a healthy `postgres`, and mounting `./backend/app` and `./backend/data` for hot reload | Infra | `docker-compose.yml` | T161 | P0 | Medium |
| T163 | 10 | Create `backend/render.yaml` — a web service running `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`, with a `healthCheckPath: /health` | Infra | `backend/render.yaml` | T162 | P0 | Medium |
| T164 | 10 | Create `frontend/vercel.json` and `frontend/.env.example` with `NEXT_PUBLIC_API_URL`, and confirm the Next.js build succeeds with the production API URL injected | Infra | `frontend/vercel.json`, `frontend/.env.example` | T139 | P0 | Low |
| T165 | 10 | Provision the production PostgreSQL instance, set every production environment variable (`DATABASE_URL`, a generated 48+ char `JWT_SECRET_KEY`, `ALLOWED_ORIGINS` set to the deployed frontend origin, `LLM_ENABLED=false`), and run `alembic upgrade head` then the seed scripts against it | Infra | Platform dashboard | T163 | P0 | Medium |
| T166 | 10 | Write `docs/deployment.md` — architecture diagram, the full environment variable table, the exact deploy order, the `alembic` command, the seed commands, the rollback procedure, and the local Docker fallback for the demo (proposal §6.4) | Docs | `docs/deployment.md` | T165 | P0 | Medium |
| T167 | 10 | Execute the full §12 journey against the deployed URL on desktop and phone viewports, performed by a member who did not build the feature | Testing | — | T165 | P0 | Medium |

### Phase 11 — Final Academic & Project Validation

| ID | Phase | Task | Layer | Files | Dep | Pri | Complexity |
|---|---|---|---|---|---|---|---|
| T168 | 11 | Walk the §18 compliance matrix end to end, attaching a `file:line` or test name to every row; any row without evidence is a bug, not a documentation gap | Docs | `PROJECT_IMPLEMENTATION_PLAN.md` §18 | T167 | P0 | Medium |
| T169 | 11 | Write `docs/report.md` — problem, requirements, architecture, the nine-module CRUD table, the ML method with the §4.2 design-honesty disclosure, the evaluation results, the risks, and the future works from proposal §11 | Docs | `docs/report.md` | T168 | P0 | High |
| T170 | 11 | Write `docs/user_manual.md` — registration through to the skill-gap report, admin job management, and troubleshooting | Docs | `docs/user_manual.md` | T168 | P1 | Medium |
| T171 | 11 | Write `docs/presentation_outline.md` and `docs/limitations.md` (rewriting the proposal §11 limitations to match the shipped system) | Docs | `docs/presentation_outline.md`, `docs/limitations.md` | T168 | P1 | Medium |
| T172 | 11 | Branding sweep — replace every "Pathfinder" (`app.py:53`, `extensions.py:8`, `backend/README.md`) and "CareerGuide AI" (`Header.tsx:69`, `Register.tsx:101`, `Login.tsx:93`, `Feedback.tsx:74`, `Landing.tsx:44,138,203`, `About.tsx:77`, `Footer.tsx:44,126`) with "CareerLens AI", and set `frontend/package.json:2` from `vite_react_shadcn_ts` to `careerlens-ai` | Frontend + Backend | all copy files | T168 | P0 | Low |
| T173 | 11 | Rewrite `backend/README.md` (currently "Pathfinder AI Guide - Flask Backend (starter)") and replace `frontend/README.md` (unmodified Lovable boilerplate) with accurate setup, run, test, and deploy instructions | Docs | `backend/README.md`, `frontend/README.md` | T172 | P0 | Medium |
| T174 | 11 | Archive `backend/instance/pathfinder.db` to `docs/archive/pathfinder-legacy.db` with a `docs/archive/README.md` explaining why it was not migrated (§3.5) | Infra | `docs/archive/*` | T001 | P1 | Low |
| T175 | 11 | Delete the legacy tree: the 8 Flask modules, `backend/instance/`, `backend/pathfinder.db`, the 6 obsolete scripts, and the 6 remaining Vite/legacy frontend artifacts listed in §14 | Infra | see §14 | T174 | P0 | Low |
| T176 | 11 | Commit the deletions as a single commit whose message names what was removed and why; verify `git log --stat` and confirm the working tree still builds, tests, and runs after deletion | Infra | — | T175 | P0 | Low |

**Task count: 176.** P0: 154 · P1: 19 · P2: 3. Complexity: Low 43 · Medium 107 · High 26.
Critical-path tasks (no path to completion without them):
T001 → T004 → T005 → T008 → T018 → T019 → T022 → T031 → T034 → T037 → T041 → T042 → T045 → T050 → T052 →
T065–T075 → T091 → T094 → T097 → T102 → T105 → T108 → T120 → T126–T131 → T141 → T151 → T155 → T161 → T165.

---

## 6. Database Implementation Plan

### 6.1 Entity inventory

14 tables. Every one is justified by a proposal clause; nothing is included "for completeness".

| # | Table | Proposal justification | Phase |
|---|---|---|---|
| 1 | `user` | §4.1 Authentication — User/Admin roles | 1 (rev 1) |
| 2 | `profile` | §4.1 User profile CRUD | 2 |
| 3 | `skill` | §4.2 "curated taxonomy of about 150 AI/ML skills"; §4.1 "chosen from a taxonomy" | 2 |
| 4 | `skill_alias` | §4.2 "with aliases (for example 'sklearn' to Scikit-learn)" | 2 |
| 5 | `user_skill` | §4.1 "update (proficiency level)"; §4.2 weighted coverage; §4.2 gap analysis | 2 |
| 6 | `project` | §4.1 Project management CRUD | 2 |
| 7 | `education_record` | §4.1 Education CRUD | 2 |
| 8 | `certification` | §4.1 "Add, edit and delete degrees and certifications" | 2 |
| 9 | `job_role` | §4.1 Job management (Admin); §2 "Administrators manage the job listings" | 2 |
| 10 | `job_role_skill` | §4.1 "with required skills and importance weights"; §4.2 coverage + gap ranking | 2 |
| 11 | `resume_upload` | §4.1 AI resume analysis (Create, Read) | 2 |
| 12 | `resume_detected_skill` | §4.1 "show detected skills for user confirmation" | 2 |
| 13 | `recommendation_run` | §4.3 evaluation; run history for `/recommendations/[id]` | 2 |
| 14 | `recommendation_result` | §2 "compatibility percentage"; per-role score, matched and missing skills | 2 |

**Deliberately not carried forward:** `guidance_session` (held the hardcoded string from
`guidance.py:48` for all 6 of its rows), `event` (analytics, not in §4.1), `upload` (replaced by
`resume_upload` with real processing), `feedback` (retained only as a UI feature, not a core table —
see §14).

### 6.2 Entity specifications

#### 6.2.1 `user`

| Aspect | Specification |
|---|---|
| Purpose | Authentication identity and authorization role |
| PK | `id BIGSERIAL` |
| Important fields | `name VARCHAR(120) NOT NULL`, `email VARCHAR(320) NOT NULL`, `password_hash VARCHAR(255) NOT NULL`, `role VARCHAR(20) NOT NULL DEFAULT 'user'`, `is_active BOOLEAN NOT NULL DEFAULT true`, `last_login_at TIMESTAMPTZ`, `created_at`, `updated_at` |
| FKs | — |
| Relationships | 1:1 `profile`; 1:N `user_skill`, `project`, `education_record`, `certification`, `resume_upload`, `recommendation_run` |
| Constraints | `CHECK (role IN ('user','admin'))`; **functional unique index on `lower(email)`** — fixes S9, where `auth.py:16` compares raw strings so `A@B.com` and `a@b.com` become two accounts |
| Indexes | `uq_user_email_lower` (unique, on `lower(email)`); `ix_user_role` |
| Delete behavior | `ON DELETE CASCADE` on every child FK. Deleting a user removes the whole subtree in one statement (test T081) |
| CRUD required | Create (register), Read (`me`, admin list). Update: **not required** by §4.1; `PATCH /api/auth/me` is added anyway as a P2 because password change is a reasonable expectation |

#### 6.2.2 `profile`

| Aspect | Specification |
|---|---|
| Purpose | User-facing narrative data: headline, career goal, links |
| PK | `id BIGSERIAL` |
| Important fields | `user_id BIGINT NOT NULL UNIQUE`, `headline VARCHAR(200)`, `career_goal TEXT`, `bio TEXT`, `location VARCHAR(120)`, `links JSONB NOT NULL DEFAULT '{}'`, `years_experience SMALLINT CHECK (years_experience BETWEEN 0 AND 60)`, `preferred_role_family VARCHAR(80)` |
| FKs | `user_id → user.id ON DELETE CASCADE` |
| Relationships | 1:1 `user`; has no direct children — skills, projects, and education hang off `user_id` directly so each has a uniform ownership check |
| Constraints | `UNIQUE (user_id)` enforces 1:1 |
| Indexes | implicit on `user_id` via the unique constraint |
| Delete behavior | `DELETE /api/profile` deletes this row only; the `user` and its auth survive so a user can rebuild without re-registering. Skills/projects/education are **not** deleted, because the proposal treats them as separate modules with their own delete |
| CRUD required | **Full C/R/U/D** — §4.1 |
| ⚠ Removed | `skills TEXT`, `education TEXT`, `experience TEXT` — the current `models.py:26-28` columns. **Dropped, not migrated.** See §6.5. |

#### 6.2.3 `skill`

| Aspect | Specification |
|---|---|
| Purpose | The curated ≈150-skill AI/ML taxonomy — the canonical vocabulary |
| PK | `id BIGSERIAL` |
| Important fields | `name VARCHAR(120) NOT NULL` (display, e.g. "Scikit-learn"), `slug VARCHAR(120) NOT NULL` (stable key, e.g. `scikit-learn`), `category VARCHAR(60) NOT NULL`, `description TEXT` |
| FKs | — |
| Relationships | 1:N `skill_alias`, `user_skill`, `job_role_skill`, `resume_detected_skill` |
| Constraints | `UNIQUE (name)`, `UNIQUE (slug)`; `CHECK (category IN (...8 values...))` |
| Indexes | `uq_skill_name`, `uq_skill_slug`, `ix_skill_category` |
| Delete behavior | `RESTRICT` by default (a taxonomy entry in use should not vanish). Admin deletion is therefore a two-step: deactivate, then delete once unreferenced |
| CRUD required | **Admin** create/update/delete (taxonomy maintenance is implied by §7.3 and by §2's "no controlled knowledge base" problem statement). User-facing: **read only** (search + browse), per §4.1 "chosen from a taxonomy" |

#### 6.2.4 `skill_alias`

| Aspect | Specification |
|---|---|
| Purpose | Maps every surface form of a skill to its canonical entry |
| PK | `alias VARCHAR(120)` (lowercased) |
| Important fields | `skill_id BIGINT NOT NULL`, `created_at` |
| FKs | `alias → ` nothing; `skill_id → skill.id ON DELETE CASCADE` |
| Relationships | N:1 `skill` |
| Constraints | Uniqueness enforced structurally by the PK. **A `validate()` step in `ml/taxonomy.py` (T043) asserts at load time that no alias maps to two different skills** — the exact failure mode the proposal names with "sklearn → Scikit-learn" |
| Indexes | PK index (this *is* the hot path — the spaCy matcher's post-processing resolves every match to a `skill_id` in one lookup) |
| Delete behavior | Cascade from `skill` |
| CRUD required | Read (indirect, through taxonomy search). Admin create/delete for alias maintenance |

> **Why `alias` is the primary key.** The alignment analysis proposed exactly this. It is correct for
> a concrete reason: the extractor's inner loop is "map this matched string to a skill". Making the
> lookup column the key turns that into a single indexed hash probe instead of a table scan with a
> `WHERE alias = ...` over a non-unique column. At 150 skills × ~3 aliases = ~450 rows the
> performance argument is negligible; the *correctness* argument is the real one — a PK makes a
> duplicate alias impossible at the storage layer rather than by convention.

#### 6.2.5 `user_skill`

| Aspect | Specification |
|---|---|
| Purpose | A confirmed skill a user holds, with proficiency and provenance. **This is the replacement for `profile.skills`.** |
| PK | composite `(user_id, skill_id)` |
| Important fields | `proficiency SMALLINT NOT NULL DEFAULT 3`, `source VARCHAR(20) NOT NULL DEFAULT 'manual'`, `years_used NUMERIC(3,1)`, `confirmed BOOLEAN NOT NULL DEFAULT true`, `created_at`, `updated_at` |
| FKs | `user_id → user.id ON DELETE CASCADE`; `skill_id → skill.id ON DELETE CASCADE` |
| Relationships | N:1 `user`, N:1 `skill` |
| Constraints | `CHECK (proficiency BETWEEN 1 AND 5)`; `CHECK (source IN ('manual','cv_extracted'))` |
| Indexes | PK `(user_id, skill_id)`; `ix_user_skill_skill` on `skill_id` for the admin "most-required skills" view |
| Delete behavior | Cascade from both parents. `DELETE /api/skills/{skill_id}` removes one row |
| CRUD required | **Full C/R/U/D** — §4.1 "Add, update (proficiency level) and remove skills" |
| Design note | `source` records whether a skill was typed by hand or accepted from a CV, and `confirmed` separates "extracted" from "user-confirmed". Together they implement §4.1's "show detected skills for user confirmation" **as data**, not just as UI state, and let the evaluation report state how many of the 24 labelled profiles used the CV path |

#### 6.2.6 `project`

| Aspect | Specification |
|---|---|
| Purpose | A project the user has built — a first-class signal in the profile text |
| PK | `id BIGSERIAL` |
| Important fields | `user_id`, `title VARCHAR(160) NOT NULL`, `description TEXT NOT NULL`, `tech_stack JSONB NOT NULL DEFAULT '[]'` (array of taxonomy slugs), `role VARCHAR(120)`, `start_date DATE`, `end_date DATE`, `repo_url VARCHAR(400)`, `is_public BOOLEAN NOT NULL DEFAULT true` |
| FKs | `user_id → user.id ON DELETE CASCADE` |
| Relationships | N:1 `user` |
| Constraints | `CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)` |
| Indexes | `ix_project_user` on `user_id` |
| Delete behavior | Cascade from `user` |
| CRUD required | **Full C/R/U/D** — §4.1 |
| Design note | `tech_stack` stores **canonical slugs**, not free text. `project_service.create` runs every entry through `ml.taxonomy.canonicalise` and rejects or drops unrecognised ones (T069). This is what stops `"sklearn"` and `"Scikit-learn"` becoming two different facts about the same project |

#### 6.2.7 `education_record`

| Aspect | Specification |
|---|---|
| Purpose | Degrees held |
| PK | `id BIGSERIAL` |
| Important fields | `user_id`, `institution VARCHAR(180) NOT NULL`, `degree VARCHAR(120) NOT NULL`, `field_of_study VARCHAR(120)`, `start_year SMALLINT`, `end_year SMALLINT`, `grade VARCHAR(40)` |
| FKs | `user_id → user.id ON DELETE CASCADE` |
| Relationships | N:1 `user` |
| Constraints | `CHECK (end_year IS NULL OR start_year IS NULL OR end_year >= start_year)`; `CHECK (start_year BETWEEN 1950 AND 2100)` |
| Indexes | `ix_education_user` on `user_id` |
| Delete behavior | Cascade from `user` |
| CRUD required | **Full C/R/U/D** — §4.1 |

#### 6.2.8 `certification`

| Aspect | Specification |
|---|---|
| Purpose | Professional certifications. Kept as a **separate table**, not a `kind` column on `education_record`, because a certification has an issuer and a credential URL and a degree does not — forcing both into one table produces nullable columns for every consumer. §4.1 names them together but they are different concepts. |
| PK | `id BIGSERIAL` |
| Important fields | `user_id`, `name VARCHAR(160) NOT NULL`, `issuer VARCHAR(160) NOT NULL`, `issued_on DATE`, `expires_on DATE`, `credential_url VARCHAR(400)` |
| FKs | `user_id → user.id ON DELETE CASCADE` |
| Relationships | N:1 `user` |
| Constraints | `CHECK (expires_on IS NULL OR issued_on IS NULL OR expires_on > issued_on)` |
| Indexes | `ix_certification_user` on `user_id` |
| Delete behavior | Cascade from `user` |
| CRUD required | **Full C/R/U/D** — §4.1 |

#### 6.2.9 `job_role`

| Aspect | Specification |
|---|---|
| Purpose | The knowledge base entry: an AI/ML role a user can be matched against |
| PK | `id BIGSERIAL` |
| Important fields | `title VARCHAR(140) NOT NULL`, `slug VARCHAR(140) NOT NULL`, `family VARCHAR(80) NOT NULL` (e.g. "AI Engineer", "ML Engineer", "Data Scientist", "MLOps Engineer", "NLP Engineer"), `seniority VARCHAR(40)`, `description TEXT NOT NULL` (the TF-IDF corpus document), `responsibilities JSONB`, `is_active BOOLEAN NOT NULL DEFAULT true`, `created_at`, `updated_at` |
| FKs | — |
| Relationships | 1:N `job_role_skill`; referenced by `recommendation_result` |
| Constraints | `UNIQUE (title)`, `UNIQUE (slug)`, `CHECK (family <> '')`, `CHECK (description <> '')` — a role with no description cannot be TF-IDF-matched and must not be creatable |
| Indexes | `uq_job_role_title`, `uq_job_role_slug`, `ix_job_role_family`, `ix_job_role_active (is_active)`; GIN trigram indexes on `title` and `description` via `pg_trgm` for admin search |
| Delete behavior | **Soft by default.** `is_active = false` hides a role from new recommendations while preserving historic `recommendation_result` rows. `DELETE` is permitted and cascades to `job_role_skill`; `recommendation_result.job_role_id` is `ON DELETE RESTRICT`, so the service returns `409 conflict_role_in_use` and the admin is told to deactivate instead. Rationale: destroying a user's recommendation history because an admin removed a role is a worse outcome than an orphaned title |
| CRUD required | **Full C/R/U/D** — §4.1, admin only. Read is public (a user must be able to browse roles) |

#### 6.2.10 `job_role_skill`

| Aspect | Specification |
|---|---|
| Purpose | A required skill for a role, with its importance weight. **The single most important table in the schema.** |
| PK | composite `(job_role_id, skill_id)` |
| Important fields | `weight NUMERIC(3,2) NOT NULL` |
| FKs | `job_role_id → job_role.id ON DELETE CASCADE`; `skill_id → skill.id ON DELETE CASCADE` |
| Relationships | N:1 `job_role`, N:1 `skill` |
| Constraints | `CHECK (weight > 0 AND weight <= 1)` — the scale is (0, 1]; zero-weight would mean "listed but irrelevant" which is not expressible in the data model and should simply be omitted |
| Indexes | PK `(job_role_id, skill_id)`; `ix_jrs_skill` on `skill_id` for "which roles need this skill" |
| Delete behavior | Cascade from either parent |
| CRUD required | **Full C/R/U/D** via `PUT /api/admin/jobs/{id}/skills` (atomic full replace) and via the admin role editor. §4.1 requires it explicitly: "job roles with required skills and importance weights" |
| Design note | This is exactly the structure a comma-separated `TEXT` column cannot express. Weights are **per (role, skill)**, so the same skill legitimately has different importance in different roles — `Docker` is 0.9 for MLOps Engineer and 0.3 for Data Analyst. A flat string has nowhere to put that. See §6.5 |

#### 6.2.11 `resume_upload`

| Aspect | Specification |
|---|---|
| Purpose | A stored CV and the outcome of processing it |
| PK | `id BIGSERIAL` |
| Important fields | `user_id`, `original_filename VARCHAR(255) NOT NULL`, `stored_filename VARCHAR(255) NOT NULL` (UUID + extension — preserves the working pattern at `guidance.py:18`), `content_type VARCHAR(100) NOT NULL`, `size_bytes INTEGER NOT NULL`, `extracted_text TEXT`, `status VARCHAR(20) NOT NULL DEFAULT 'uploaded'`, `error_message TEXT`, `created_at` |
| FKs | `user_id → user.id ON DELETE CASCADE` (**NOT NULL** — fixes S4, where `@jwt_required(optional=True)` at `guidance.py:10` let anonymous callers write rows with `user_id = NULL`, permanently unattributable) |
| Relationships | N:1 `user`; 1:N `resume_detected_skill` |
| Constraints | `CHECK (status IN ('uploaded','extracted','confirmed','failed'))`; `CHECK (size_bytes <= 5242880)` (5 MB) |
| Indexes | `ix_resume_user (user_id, created_at DESC)` |
| Delete behavior | Cascade from `user`; the physical file is removed by the service layer in the same operation. §6.4 risk mitigation requires "allow deletion of files and profile" |
| CRUD required | Create, Read (§4.1). Delete is added for the privacy requirement |

#### 6.2.12 `resume_detected_skill`

| Aspect | Specification |
|---|---|
| Purpose | Skills found in a CV, **staged before user confirmation.** Kept separate from `user_skill` so an unconfirmed extraction can never influence a recommendation. |
| PK | composite `(resume_upload_id, skill_id)` |
| Important fields | `surface_form VARCHAR(120) NOT NULL` (what literally appeared, e.g. `"sklearn"`), `match_start INTEGER`, `match_end INTEGER`, `occurrence_count INTEGER NOT NULL DEFAULT 1`, `accepted BOOLEAN NOT NULL DEFAULT false` |
| FKs | `resume_upload_id → resume_upload.id ON DELETE CASCADE`; `skill_id → skill.id ON DELETE CASCADE` |
| Relationships | N:1 `resume_upload`, N:1 `skill` |
| Constraints | `CHECK (occurrence_count > 0)` |
| Indexes | PK; `ix_rds_accepted` on `(resume_upload_id, accepted)` |
| Delete behavior | Cascade from either parent |
| CRUD required | Create, Read (§4.1). Update is `POST /api/skills/confirm` setting `accepted` and inserting into `user_skill` — the confirmation step, not a blind update |
| Design note | This table is the direct database expression of §4.1's "show detected skills for user confirmation" and §6.4's "let users confirm/edit detected skills". The engine reads `user_skill`; it never reads `resume_detected_skill`. That separation is what makes "no fabricated data in production flows" checkable |

#### 6.2.13 `recommendation_run`

| Aspect | Specification |
|---|---|
| Purpose | One execution of the engine for one user |
| PK | `id BIGSERIAL` |
| Important fields | `user_id`, `profile_snapshot JSONB NOT NULL` (skills, projects, education at the moment of the run), `coverage_weight NUMERIC(3,2) NOT NULL`, `tfidf_weight NUMERIC(3,2) NOT NULL`, `engine_version VARCHAR(20) NOT NULL`, `candidate_count INTEGER NOT NULL`, `duration_ms INTEGER`, `created_at` |
| FKs | `user_id → user.id ON DELETE CASCADE` |
| Relationships | N:1 `user`; 1:N `recommendation_result` |
| Constraints | `CHECK (coverage_weight >= 0 AND tfidf_weight >= 0 AND coverage_weight + tfidf_weight = 1)` |
| Indexes | `ix_run_user (user_id, created_at DESC)` |
| Delete behavior | Cascade from `user` |
| CRUD required | Create, Read. No update or delete — a run is an immutable record. The alternative (mutable results) makes the evaluation report unverifiable |

#### 6.2.14 `recommendation_result`

| Aspect | Specification |
|---|---|
| Purpose | One role's score within one run, with the evidence behind it |
| PK | composite `(run_id, job_role_id)` |
| Important fields | `rank INTEGER NOT NULL`, `compatibility_score NUMERIC(5,4) NOT NULL`, `skill_coverage NUMERIC(6,5) NOT NULL`, `tfidf_similarity NUMERIC(6,5) NOT NULL`, `matched_skill_ids JSONB NOT NULL`, `missing_skill_ids JSONB NOT NULL` |
| FKs | `run_id → recommendation_run.id ON DELETE CASCADE`; `job_role_id → job_role.id ON DELETE RESTRICT` |
| Relationships | N:1 `recommendation_run`, N:1 `job_role` |
| Constraints | `CHECK (compatibility_score BETWEEN 0 AND 1)`; `CHECK (skill_coverage BETWEEN 0 AND 1)`; `CHECK (tfidf_similarity BETWEEN 0 AND 1)`; `UNIQUE (run_id, rank)` |
| Indexes | PK; `uq_result_rank (run_id, rank)` |
| Delete behavior | Cascade from the run. `RESTRICT` from the role (see §6.2.9) |
| CRUD required | Create, Read |
| Design note | `matched_skill_ids` and `missing_skill_ids` as ID arrays rather than denormalised text means a stored run renders its skill names by joining `skill` — so renaming a skill updates historical explanations for free. It also lets the explainability test (T150) assert that the two arrays partition the role's required set, which is a real correctness check |

### 6.3 Constraint naming convention

`app/db/base.py` fixes a `naming_convention` so Alembic autogenerate produces stable constraint
names and downgrades work:

```python
convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

Without this, PostgreSQL auto-names check constraints `skill_proficiency_check`, `skill_proficiency_check1`,
`skill_proficiency_check2` — and the third autogenerate run produces spurious diffs.

### 6.4 Deletion semantics summary

| Parent | Child | Rule | Reason |
|---|---|---|---|
| `user` | `profile` | CASCADE | Profile is meaningless without its owner |
| `user` | `user_skill`, `project`, `education_record`, `certification`, `resume_upload`, `recommendation_run` | CASCADE | §4.1 requires delete operations; orphan rows are never useful. The current schema declares these FKs but SQLite never enforces them (S10), so a deleted `user` today leaves orphans |
| `skill` | `skill_alias` | CASCADE | An alias without its skill is meaningless |
| `skill` | `user_skill` | CASCADE | A user's skill row pointing at a deleted taxonomy entry is corrupt |
| `skill` | `job_role_skill` | CASCADE | Same |
| `job_role` | `job_role_skill` | CASCADE | The role's requirement set goes with it |
| `job_role` | `recommendation_result` | **RESTRICT** | Preserve recommendation history; return `409` and suggest soft-delete |
| `resume_upload` | `resume_detected_skill` | CASCADE | Staged extractions die with their CV |
| `recommendation_run` | `recommendation_result` | CASCADE | Results die with the run |
| `profile` (explicit delete) | — | row only | Deleting a profile must not log the user out |

### 6.5 Replacing `profile.skills = "python,sql,ml"`

This is the change the plan is most careful about, because the current design blocks **three**
proposal requirements simultaneously.

#### 6.5.1 Why the current column cannot work

```python
# backend/models.py:22-29 — the current design
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    headline = db.Column(db.String(256))
    skills = db.Column(db.Text)          # ← "python,sql,ml"
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
```

Three independent failures in one column:

| # | Requirement blocked | Why the column cannot express it |
|---|---|---|
| 1 | §4.1 "update (**proficiency level**)" | There is no per-skill row. `"python,sql,ml"` has three tokens and zero places to store three different proficiency values. `UPDATE profile SET skills='python,4'` is not a valid representation. |
| 2 | §4.2 "weighted skill-coverage" | Importance is **per (role, skill)**. `Docker` is 0.9 for MLOps Engineer and 0.3 for Data Analyst. A single flat list belongs to a user, not to a role-skill pair, so it has nowhere to put a role-specific weight. |
| 3 | §4.2 "required skills of the target role **minus** the user's skills" | Set difference requires canonical identifiers. `"sklearn"` and `"Scikit-learn"` are different strings, so a user who wrote `sklearn` appears to be missing `Scikit-learn` — a false gap that directly undermines the feature. This is precisely the alias problem §4.2 names. |

#### 6.5.2 The replacement

```sql
-- before (dropped in migration 0002)
ALTER TABLE profile DROP COLUMN skills;
ALTER TABLE profile DROP COLUMN education;
ALTER TABLE profile DROP COLUMN experience;

-- after
CREATE TABLE skill (
  id          BIGSERIAL PRIMARY KEY,
  name        VARCHAR(120) NOT NULL UNIQUE,
  slug        VARCHAR(120) NOT NULL UNIQUE,
  category    VARCHAR(60)  NOT NULL,
  description TEXT
);

CREATE TABLE skill_alias (
  alias    VARCHAR(120) PRIMARY KEY,              -- indexed by construction
  skill_id BIGINT NOT NULL REFERENCES skill(id) ON DELETE CASCADE
);

CREATE TABLE user_skill (
  user_id     BIGINT  NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  skill_id    BIGINT  NOT NULL REFERENCES skill(id)  ON DELETE CASCADE,
  proficiency SMALLINT NOT NULL DEFAULT 3,
  source      VARCHAR(20) NOT NULL DEFAULT 'manual',
  years_used  NUMERIC(3,1),
  confirmed   BOOLEAN  NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, skill_id),
  CONSTRAINT ck_user_skill_proficiency CHECK (proficiency BETWEEN 1 AND 5),
  CONSTRAINT ck_user_skill_source      CHECK (source IN ('manual','cv_extracted'))
);

CREATE TABLE job_role_skill (
  job_role_id BIGINT      NOT NULL REFERENCES job_role(id) ON DELETE CASCADE,
  skill_id    BIGINT      NOT NULL REFERENCES skill(id)     ON DELETE CASCADE,
  weight      NUMERIC(3,2) NOT NULL,
  PRIMARY KEY (job_role_id, skill_id),
  CONSTRAINT ck_jrs_weight CHECK (weight > 0 AND weight <= 1)
);
```

#### 6.5.3 Migration procedure for the 11 existing rows

**Decision: do not migrate the data.** The 11 SQLite profiles hold `'python,sql,ml'` and `'Sample headline'`.
Converting them would create CareerLens records asserting that seeded users have exactly three
skills and no projects, education, or certifications — fabricated data in a graded submission,
which the task rules prohibit and which would also skew the evaluation baseline.

Procedure instead:

1. **Archive** `backend/instance/pathfinder.db` → `docs/archive/pathfinder-legacy.db` (T174).
2. **Do not** import any row into PostgreSQL.
3. Document the decision in `docs/report.md` under "Migration": *"The predecessor application
   (Pathfinder, Flask + SQLite) held no CareerLens data — its 11 profiles contained only a
   placeholder skill string and a placeholder headline, and its 6 recommendation rows all stored
   the same hardcoded placeholder response. A data migration was therefore neither possible nor
   meaningful. The PostgreSQL database is initialised from seed data only."*
4. If any real user registers during the transition, they re-register. With 4 team members and no
   external users this is a non-issue — but it is **stated**, not assumed away.

#### 6.5.4 Verification queries

Run after migration 0002 + seeding, and record the output in the report:

```sql
-- 1. No denormalized skill blob survives anywhere
SELECT table_name, column_name FROM information_schema.columns
 WHERE table_schema='public' AND column_name IN ('skills','metadata_json','result_json');

-- 2. Aliases are unambiguous
SELECT alias, COUNT(DISTINCT skill_id) FROM skill_alias GROUP BY alias HAVING COUNT(DISTINCT skill_id) > 1;
-- expect 0 rows

-- 3. Every role has a usable requirement set
SELECT r.title, COUNT(s.skill_id) AS required
  FROM job_role r LEFT JOIN job_role_skill s ON s.job_role_id = r.id
 WHERE r.is_active GROUP BY r.title HAVING COUNT(s.skill_id) < 5;
-- expect 0 rows

-- 4. Weights are in range
SELECT * FROM job_role_skill WHERE weight <= 0 OR weight > 1;
-- expect 0 rows

-- 5. Cascades actually work
BEGIN;
DELETE FROM "user" WHERE email = 'cascade_test@example.com';
SELECT COUNT(*) FROM user_skill WHERE user_id NOT IN (SELECT id FROM "user");
ROLLBACK;
-- expect 0
```

### 6.6 Migration sequence

| Revision | Tables | Phase | Gate |
|---|---|---|---|
| `0001_infra_and_user` | `user` | 1 | App boots, `/health` green, round-trip downgrade verified (T028) |
| `0002_domain_schema` | `profile`, `skill`, `skill_alias`, `user_skill`, `project`, `education_record`, `certification`, `job_role`, `job_role_skill`, `resume_upload`, `resume_detected_skill`, `recommendation_run`, `recommendation_result` | 2 | All §6.5.4 queries return the expected empty sets |
| `0003_pg_trgm_indexes` (optional) | GIN indexes on `job_role.title`, `job_role.description` | 2 | `EXPLAIN` shows an index scan for admin search |

**Rules that apply to every future migration.** Never use `Base.metadata.create_all()` outside
`tests/conftest.py`. Never edit an applied revision — add a new one. Every migration must have a
tested `downgrade()`. `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` runs in
CI (or at minimum in the Phase 9 checklist) so a broken downgrade is caught before it reaches
production.

---

## 7. Backend API Plan

All endpoints are prefixed `/api`. Authentication is `Authorization: Bearer <jwt>`. The error
envelope is uniform (T017):

```json
{ "error": { "code": "validation_error", "message": "…", "errors": [{ "field": "email", "message": "…" }] } }
```

### 7.1 `/api/auth/*`

| Method | Path | Auth | Role | Request | Response | DB operation | Service | Validation | Errors |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/auth/register` | No | — | `{name, email, password}` | `201 {user, access_token, token_type, expires_in}` | INSERT `user` + INSERT `profile` in one transaction | `auth_service.register_user` | name 1–120; `EmailStr`; password 8–128 with upper+lower+digit | `409` email exists; `422` invalid body |
| POST | `/auth/login` | No | — | `{email, password}` | `200 {user, access_token, token_type, expires_in}` | SELECT `user` | `auth_service.authenticate` | `EmailStr`; password non-empty | `401` invalid credentials (identical message for unknown user and wrong password) |
| POST | `/auth/logout` | Yes | any | — | `204` | — (client clears the token) | — | — | `401` no token |
| POST | `/auth/refresh` | Yes | any | — | `200 {user, access_token, …}` | SELECT `user` | `auth_service.build_token_response` | — | `401` expired/invalid |
| GET | `/auth/me` | Yes | any | — | `200 {user}` | SELECT `user` | — | — | `401` |
| PATCH | `/auth/me` | Yes | any | `{name?, password?, current_password?}` | `200 {user}` | UPDATE `user` | `auth_service.update_me` | password change requires `current_password` | `401`; `422` |

> `/auth/logout` returning `204` without server state is honest, not a stub: the token is stateless.
> The docstring states this, and the report records it under security limitations. The alternative —
> a server-side token blacklist — requires a Redis dependency that the proposal does not list, so it
> is rejected on scope grounds.

### 7.2 `/api/profile/*`

| Method | Path | Auth | Role | Request | Response | DB operation | Validation | Errors |
|---|---|---|---|---|---|---|---|---|
| POST | `/profile` | Yes | any | `ProfileCreate` | `201 ProfileRead` | INSERT `profile` (get-or-create) | headline ≤ 200; `years_experience` 0–60; `links` validated as URL strings | `422` |
| GET | `/profile` | Yes | any | — | `200 ProfileRead` (with counts) | SELECT | — | — |
| PATCH | `/profile` | Yes | any | `ProfileUpdate` (all optional) | `200 ProfileRead` | UPDATE | partial; distinguishes absent from null | `422` |
| DELETE | `/profile` | Yes | any | — | `204` | DELETE `profile` | — | `404` if none |

No path parameter → no IDOR is possible by construction. The current code has no profile endpoint
of any kind, so this is entirely new.

### 7.3 `/api/skills/*`

| Method | Path | Auth | Role | Request | Response | DB operation | Validation | Errors |
|---|---|---|---|---|---|---|---|---|
| GET | `/skills` | Yes | any | `?source=&category=` | `200 UserSkillRead[]` | SELECT join `user_skill`+`skill` | — | — |
| POST | `/skills` | Yes | any | `{skill_id, proficiency?, years_used?}` | `201 UserSkillRead` | INSERT | `skill_id` must exist in taxonomy; `proficiency` 1–5 | `409` already present; `422` |
| PATCH | `/skills/{skill_id}` | Yes | any | `{proficiency?, years_used?, confirmed?}` | `200 UserSkillRead` | UPDATE **scoped to `user_id`** | 1–5 | `404` not owned / not present |
| DELETE | `/skills/{skill_id}` | Yes | any | — | `204` | DELETE scoped to `user_id` | — | `404` |
| GET | `/skills/taxonomy` | Yes | any | `?q=&category=&limit=20&offset=0` | `200 {total, items[{id,name,slug,category,description}]}` | SELECT `skill` with trigram/prefix search | `limit` 1–100 | `422` |
| POST | `/skills/confirm` | Yes | any | `{skills:[{skill_id, accepted, proficiency?}]}` | `200 {added, updated, skipped, rejected[]}` | Bulk UPSERT `user_skill` (`source='cv_extracted'`, `confirmed=true`) + UPDATE `resume_detected_skill.accepted` — one transaction | unknown `skill_id` → rejected, not fatal | `200` with a partial result (per-item, not whole-request) |

`POST /skills/confirm` is the endpoint that implements §4.1's "show detected skills for user
confirmation". It is **idempotent** — confirming twice changes nothing, so a double-click or a
refresh is harmless.

### 7.4 `/api/projects/*`, `/api/education/*`, `/api/certifications/*`

Identical CRUD shape for all three. Only the validators differ.

| Method | Path | Auth | Request | Response | DB op | Validation | Errors |
|---|---|---|---|---|---|---|---|
| GET | `/projects` | Yes | `?page=&page_size=` | `200 {total, items[]}` | SELECT scoped to `user_id` | — | — |
| POST | `/projects` | Yes | `{title, description, tech_stack[], role?, start_date?, end_date?, repo_url?}` | `201 ProjectRead` | INSERT | title ≤ 160; description 1–5000; each `tech_stack` entry canonicalised via `taxonomy.canonicalise`; `end_date >= start_date`; `repo_url` is a URL | `422` |
| GET | `/projects/{id}` | Yes | — | `200 ProjectRead` | SELECT + ownership | — | `404` |
| PATCH | `/projects/{id}` | Yes | partial | `200 ProjectRead` | UPDATE + ownership | as above | `404`, `422` |
| DELETE | `/projects/{id}` | Yes | — | `204` | DELETE + ownership | — | `404` |
| GET/POST | `/education` | Yes | list / create | `200`/`201` | as above | institution, degree required; `end_year >= start_year`; years 1950–2100 | `404`, `422` |
| GET/PATCH/DELETE | `/education/{id}` | Yes | — | `200`/`204` | ownership | as above | `404` |
| GET/POST | `/certifications` | Yes | list / create | `200`/`201` | as above | name, issuer required; `expires_on > issued_on` | `404`, `422` |
| GET/PATCH/DELETE | `/certifications/{id}` | Yes | — | `200`/`204` | ownership | as above | `404` |

Every `{id}` route is scoped by `WHERE id = :id AND user_id = :current_user` — never
`session.get(Model, id)` followed by a Python-side check. The current `guidance.py:31` does
`Upload.query.get(upload_id)` with no auth and no ownership: a textbook IDOR, and the reason this
rule is stated explicitly.

### 7.5 `/api/jobs/*`

Read is public (role browsing); write is admin-only. The split is enforced by mounting two routers
on the same prefix.

**Public**

| Method | Path | Auth | Request | Response | DB op | Errors |
|---|---|---|---|---|---|---|
| GET | `/jobs` | Optional | `?family=&q=&is_active=&page=&page_size=` | `200 {total, items[JobRoleSummary]}` | SELECT active roles | `422` |
| GET | `/jobs/families` | Optional | — | `200 [{family, count}]` | SELECT GROUP BY | — |
| GET | `/jobs/{id}` | Optional | — | `200 JobRoleRead` (includes weighted skills) | SELECT | `404` |

**Admin** — every row requires `role == "admin"`, enforced by `require_role("admin")`, returning
`403` for an authenticated non-admin and `401` for anonymous.

| Method | Path | Request | Response | DB operation | Validation | Errors |
|---|---|---|---|---|---|---|
| POST | `/admin/jobs` | `{title, family, seniority?, description, responsibilities[], skills[{skill_id, weight}]}` | `201 JobRoleRead` | INSERT `job_role` + bulk INSERT `job_role_skill`, one transaction | slug auto-derived; title unique; description non-empty; ≥ 1 skill; each weight in (0, 1] | `409` title exists; `422` |
| PATCH | `/admin/jobs/{id}` | partial (role fields only) | `200 JobRoleRead` | UPDATE | as above | `404`, `409`, `422` |
| PUT | `/admin/jobs/{id}/skills` | `[{skill_id, weight}]` (full replacement) | `200 JobRoleRead` | DELETE existing + INSERT new, **one transaction** | non-empty; weights valid; no duplicate `skill_id` | `404`, `422`; the previous set survives any failure |
| DELETE | `/admin/jobs/{id}` | — | `204` | DELETE; cascades to `job_role_skill` | — | `404`; `409 conflict_role_in_use` if referenced by `recommendation_result` |
| GET | `/admin/jobs` | `?q=&family=&is_active=&page=` | `200 {total, items}` | SELECT incl. inactive | — | — |
| GET | `/admin/taxonomy` | `?q=&category=` | `200 {total, items}` | SELECT `skill` | — | — |
| POST | `/admin/taxonomy` | `{name, category, description?, aliases[]}` | `201 SkillRead` | INSERT `skill` + `skill_alias` | name/slug unique; **no alias already claimed by another skill** | `409`; `422` |
| PATCH | `/admin/taxonomy/{skill_id}` | partial | `200 SkillRead` | UPDATE | — | `404`, `409` |
| DELETE | `/admin/taxonomy/{skill_id}` | — | `204` | DELETE; cascades | — | `404`; `409` if referenced |
| GET | `/admin/overview` | — | `200 {role_count, families[], top_skills[], user_count, run_count, latest_run_at}` | Aggregates | — | — |

### 7.6 `/api/cv/*`

| Method | Path | Auth | Role | Request | Response | DB op | Service | Validation | Errors |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/cv/upload` | **Yes** | any | `multipart/form-data`, field `file` | `201 {resume_upload_id, status, filename, size_bytes, text_length, detected_skills[{skill_id, canonical_name, surface_form, occurrence_count}], already_confirmed[]}` | INSERT `resume_upload` + bulk INSERT `resume_detected_skill` | `cv_service.upload_and_extract` | auth **required** (fixes S4); extension in `.pdf`/`.docx` **and** content-type in `application/pdf` / `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (fixes S3 — `utils.py:1-4` `allowed_file()` exists but was never imported); ≤ 5 MB; non-empty text | `400` no file; `415` wrong type; `413` too large; `422` scanned PDF (OCR unsupported, per proposal §11); `500` extraction failure (logged, generic message — fixes S8) |
| GET | `/cv` | Yes | any | — | `200 ResumeUploadRead[]` | SELECT scoped to `user_id` | — | — | `401` |
| GET | `/cv/{id}` | Yes | any | — | `200 ResumeUploadRead` (incl. `detected_skills`) | SELECT + **ownership** | — | — | `404` (fixes S5 IDOR) |
| GET | `/cv/{id}/text` | Yes | any | — | `200 {text}` | SELECT + ownership | — | — | `404` |
| DELETE | `/cv/{id}` | Yes | any | — | `204` | DELETE row + unlink file | — | — | `404` |

Extraction happens **on upload**; persistence to `user_skill` happens **only on confirmation**
(`POST /api/skills/confirm`). This ordering is what §4.1 requires and it means a failed extraction
never contaminates the user's profile.

### 7.7 `/api/recommendations/*`

| Method | Path | Auth | Role | Request | Response | DB operation | Service | Errors |
|---|---|---|---|---|---|---|---|---|
| POST | `/recommendations` | Yes | any | `{limit=10, role_family?, min_score?}` | `201 {run_id, engine_version, weights{skill_coverage, tfidf_similarity}, generated_at, total_candidates, results[RoleRecommendation]}` | SELECT profile+skills+projects+education; SELECT roles+weights; INSERT `recommendation_run`; INSERT N × `recommendation_result` | `recommendation_service.generate` | `limit` 1–50 | `409 profile_incomplete` when the user has 0 confirmed skills (a helpful error beats a list of 0 % roles); `422` |
| GET | `/recommendations/runs` | Yes | any | `?page=&page_size=` | `200 {total, items[{id, created_at, top_role, compatibility, total_candidates}]}` | SELECT + ownership | — | `401` |
| GET | `/recommendations/runs/{id}` | Yes | any | — | `200` full run detail, **from the database** | SELECT + ownership | — | `404` |

`RoleRecommendation`:
```json
{
  "rank": 1,
  "job_role_id": 12,
  "title": "AI Engineer",
  "family": "AI Engineer",
  "seniority": "Mid",
  "compatibility_pct": 91,
  "skill_coverage": 0.88,
  "tfidf_similarity": 0.62,
  "matched_skills": [{ "skill_id": 3, "name": "Python", "weight": 1.0, "proficiency": 4 }],
  "missing_skills": [{ "skill_id": 41, "name": "Docker", "weight": 0.9 }]
}
```

The `components` decomposition is not decoration — it is the direct implementation of proposal §2's
"explain each score with matched skills" and §3.4's "Explains why a role matches: matched and
missing skills", and it is the differentiator the competitor table claims over LinkedIn, Jobscan,
and Bdjobs.

**Execution steps** (the task's example, mapped to code):

1. Load normalised user data — `recommendation_service._load_user_snapshot`
2. Load active job roles — `recommendation_service._load_role_specs`
3. Calculate weighted skill coverage — `ml.matcher.weighted_skill_coverage`
4. Calculate TF-IDF similarity — `ml.matcher.tfidf_cosine`
5. Combine scores — `ml.ranker.rank` with `0.6 / 0.4` from `Settings`
6. Rank roles — sort by `(-compatibility, job_role_id)` for a total order
7. Return explainable results — `RankedRecommendationResponse`

### 7.8 `/api/skill-gap/*`

| Method | Path | Auth | Role | Request | Response | DB op | Service | Errors |
|---|---|---|---|---|---|---|---|---|
| GET | `/skill-gap/{job_role_id}` | Yes | any | — | `200 {job_role, coverage_pct, matched[{skill_id,name,weight,proficiency}], missing[{skill_id,name,weight,tier}], tiers{critical,important,desirable}, learning_path?}` | SELECT role + weights; SELECT user skills | `recommendation_service.analyse_gap` | `404` role not found or inactive; `401` |
| POST | `/skill-gap/{job_role_id}/learning-path` | Yes | any | — | `200 {steps[]}` | none | `ml.learning_path` | `503` when `LLM_ENABLED=false` — **a distinct, honest status, not a silent empty response** |

The `503` is deliberate. The proposal requires the core to work without the LLM; making the optional
feature return a distinct status proves the core path is genuinely independent of it.

### 7.9 `/api/admin/*`

| Method | Path | Auth | Role | Purpose |
|---|---|---|---|---|
| GET | `/admin/overview` | Yes | admin | Counts and distributions for the admin dashboard |
| GET | `/admin/users` | Yes | admin | Paged user list (never returns `password_hash`) |
| PATCH | `/admin/users/{id}/role` | Yes | admin | Promote/demote; an admin cannot demote themselves, preventing lockout |
| GET/POST/PATCH/DELETE | `/admin/jobs…`, `/admin/taxonomy…` | Yes | admin | §7.5 |
| GET | `/admin/evaluation` | Yes | admin | The committed evaluation report, parsed and returned as JSON for the admin chart |
| GET | `/admin/feedback` | Yes | admin | Retained from `guidance.py:151-187`; adds pagination and a real role guard instead of the inline one |

> **Replaces Flask-Admin.** `backend/admin.py:40-54` registers six `ModelView`s and
> `app.py:27` mounts them with **no `is_accessible` override**, so `/admin/` is publicly reachable
> and lists `user.email` and `user.password_hash` to anonymous visitors (finding S1, critical).
> Flask-Admin is removed at T175. Until then it stays in the frozen legacy tree and **must not be
> mounted** by the new app.

### 7.10 `/api/dashboard/*` and `/api/feedback`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/dashboard/summary` | Yes | Real counts: skills, projects, education, certifications, uploads, latest run, top role. **Replaces `mockStats` at `Dashboard.tsx:70-75`** |
| GET | `/dashboard/completeness` | Yes | 0–100 profile-completeness score from real field presence, plus the list of missing steps. Replaces the fabricated `averageCompletion: "18 minutes"` and `successRate: "94%"` |
| POST | `/feedback` | Yes (was optional) | Retained. Validation from `guidance.py:107-128`, re-expressed as Pydantic. **Auth is now required** — S4 |

### 7.11 Endpoint summary

| Domain | Endpoints | Auth required | Admin only |
|---|---|---|---|
| `/auth` | 6 | 3 | 0 |
| `/profile` | 4 | 4 | 0 |
| `/skills` | 6 | 6 | 0 |
| `/projects` | 5 | 5 | 0 |
| `/education` | 5 | 5 | 0 |
| `/certifications` | 5 | 5 | 0 |
| `/jobs` (public) | 3 | 0 (optional) | — |
| `/jobs` + `/taxonomy` (admin) | 9 | 9 | 9 |
| `/cv` | 5 | 5 | 0 |
| `/recommendations` | 3 | 3 | 0 |
| `/skill-gap` | 2 | 2 | 0 |
| `/dashboard` | 2 | 2 | 0 |
| `/admin` | 5 | 5 | 5 |
| `/feedback` | 1 | 1 | 0 |
| **Total** | **61** | **55** | **14** |

Compare with the current backend: **10 routes, 0 with update or delete, 4 accepting
unauthenticated writes.**

---

## 8. CRUD Plan

### 8.1 CRUD matrix

`C` create · `R` read · `U` update · `D` delete. The **UI** column names the screen that performs
the operation; a cell is only ✓ when both the endpoint and the screen exist.

| Entity | C | R | U | D | Backend | Frontend screen | DB operation | Validation | Authorization |
|---|---|---|---|---|---|---|---|---|---|
| **Profile** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/profile` | `/profile` | INSERT / SELECT / UPDATE / DELETE on `profile` | headline ≤ 200, years 0–60, links are URLs | owner only (no ID param, so IDOR is structurally impossible) |
| **Skills** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/skills`, `POST /api/skills/confirm` | `/skills`, `/resume` | INSERT / SELECT+join / UPDATE / DELETE on `user_skill` | `skill_id` must exist; proficiency 1–5; source enum | owner only (`WHERE user_id = current`) |
| **Projects** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/projects[/{id}]` | `/projects` | INSERT / SELECT / UPDATE / DELETE on `project` | title ≤ 160, description 1–5000, tech stack canonicalised, date order | owner only |
| **Education** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/education[/{id}]` | `/education` | on `education_record` | institution + degree required, year order, year range | owner only |
| **Certifications** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/certifications[/{id}]` | `/certifications` | on `certification` | name + issuer required, `expires > issued` | owner only |
| **Job Roles** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/admin/jobs[/{id}]`, `PUT /api/admin/jobs/{id}/skills` | `/admin/jobs`, `/admin/jobs/[id]` | INSERT/UPDATE/DELETE on `job_role` + bulk on `job_role_skill` | title unique, description non-empty, ≥ 1 skill, weight in (0,1] | **admin only** for C/U/D; public read |
| **Skill taxonomy** | ✓ | ✓ | ✓ | ✓ | `POST/GET/PATCH/DELETE /api/admin/taxonomy[/{skill_id}]` | `/admin/taxonomy` (P1) | on `skill` + `skill_alias` | name/slug unique, no alias collision | **admin only** |
| **User** | ✓ | ✓ | ✓* | ✓ | `POST /auth/register`, `GET/PATCH /auth/me`, `DELETE /auth/me` | `/profile` (delete account) | on `user` | password change requires `current_password` | self only; demote-self blocked |
| **Resume upload** | ✓ | ✓ | — | ✓ | `POST/GET/DELETE /api/cv[/{id}]` | `/resume` | INSERT / SELECT+ownership / DELETE row + unlink | type allowlist, ≤ 5 MB, non-empty text | owner only (**fixes the S5 IDOR at `guidance.py:31`**) |
| **Detected skills** | ✓ | ✓ | ✓ | ✓ | staged on upload; `accepted` via `POST /skills/confirm` | `/resume` panel | INSERT / SELECT / UPDATE / cascade DELETE | `skill_id` must exist | owner only |
| **Recommendation run** | ✓ | ✓ | — | — | `POST /recommendations`, `GET /recommendations/runs[/{id}]` | `/recommendations`, `/recommendations/[id]` | INSERT / SELECT+ownership | — | owner only; immutable by design |
| **Recommendation result** | ✓ | ✓ | — | — | created with the run | `/recommendations/[id]`, `/skill-gap` | bulk INSERT / SELECT | scores in [0, 1] | via the run |

`*` `PATCH /auth/me` for name/password is **beyond** the proposal's stated `Create, Read` for
Authentication. It is included because a system with a delete button and no password change is
obviously incomplete to any user, and it costs one endpoint. The compliance matrix (§18) records it
as an addition, not a proposal requirement.

### 8.2 CRUD demonstrability requirements

Proposal §4.1 requires CRUD; the course requires it to be demonstrable. A backend endpoint that no
screen reaches is not demonstrable. Therefore, for every ✓ in §8.1:

1. A screen exists under `app/(app)/` or `app/(admin)/` and is linked from `Header.tsx`.
2. The operation is reachable in ≤ 2 clicks from that screen.
3. The change is visible after a full page refresh — proof it reached PostgreSQL, not `useState`.
   This is the specific failure mode the current `Recommendations.tsx:169` `savedCareers` state
   represents, and it must not recur.
4. `backend/tests/test_ownership.py` proves user A cannot perform the operation on user B's row.
5. T135 walks the matrix in a browser and captures a screenshot per cell as report evidence.

### 8.3 Authorization rules, consolidated

| Rule | Implementation | Replaces |
|---|---|---|
| Every write requires a valid token | `get_current_user` as a route dependency | `@jwt_required(optional=True)` at `guidance.py:10,40,73,94` (S4) |
| Every read of user-owned data is scoped by `user_id` in the query | `WHERE id = :id AND user_id = :uid` | `Upload.query.get(upload_id)` at `guidance.py:31` (S5) |
| Non-owners get `404`, never `403` | The query returns no row | — |
| Every admin route requires `role == "admin"` | `require_role("admin")` dependency | the single inline check at `guidance.py:157-163` |
| The auth check runs before the resource lookup | Dependency ordering in `app/api/deps.py` | — |
| No endpoint accepts a `user_id` from the client | The user id always comes from the token | — |
| An admin cannot demote themselves | Check in the role-update service | prevents lockout |
| `password_hash` is never in a response schema | `UserRead` omits it | `user.to_dict()` at `models.py:19-20` already omits it — that part is correct and is preserved |

### 8.4 Status-code contract

| Situation | Status | Body |
|---|---|---|
| Created | `201` | resource |
| Read / updated | `200` | resource |
| Deleted, logged out | `204` | empty |
| No token / invalid / expired token | `401` | `{error:{code:"unauthorized", …}}` |
| Authenticated but wrong role | `403` | `{error:{code:"forbidden", …}}` |
| Missing, or owned by someone else | `404` | `{error:{code:"not_found", …}}` |
| Unique violation (email, role title, duplicate skill) | `409` | `{error:{code:"conflict", …}}` |
| Body fails validation | `422` | `{error:{code:"validation_error", errors:[{field,message}]}}` |
| Wrong file type | `415` | `{error:{code:"unsupported_media_type", …}}` |
| File too large | `413` | `{error:{code:"payload_too_large", …}}` |
| Optional feature disabled (LLM off) | `503` | `{error:{code:"feature_disabled", …}}` |
| Unhandled | `500` | `{error:{code:"internal_error"}}` — **never the exception text** (S8) |

---

## 9. AI/ML Implementation Plan

### 9.1 What the proposal specifies, verbatim in intent

| §4.2 clause | Implementation | Module |
|---|---|---|
| "text is extracted from the CV, cleaned, then matched against a curated taxonomy of about 150 AI/ML skills with aliases (for example 'sklearn' to Scikit-learn) using **spaCy phrase matching**. Users confirm or edit the result." | `text_loader` → normalise → spaCy `PhraseMatcher` over canonical names + aliases → staged results → user confirmation | `app/ml/text_loader.py`, `app/ml/extractor.py` |
| "each user is represented by skills, projects and education. The score combines a **weighted skill-coverage score** with **TF-IDF cosine similarity** between the profile text and each job description, both computed with scikit-learn. The initial weights (about 60% / 40%) will be tuned on the labelled sample profiles." | Coverage from `user_skill` ∩ `job_role_skill` weighted by `weight`; cosine from a per-call `TfidfVectorizer`; combined `0.6/0.4` from `Settings`, tuned in Phase 9 | `app/ml/matcher.py`, `app/ml/ranker.py` |
| "Skill-gap analysis: required skills of the target role **minus** the user's skills, ranked by their importance weight for that role." | Set difference then sort by descending `weight` | `app/ml/gap_analysis.py` |
| "Optional LLM component: if time permits, an LLM API turns the gap list into a short learning path. **The core features work without it.**" | Flag-gated module, off the critical path, reachable only via a dedicated endpoint that returns `503` when disabled | `app/ml/learning_path.py` |
| "Because no large labelled dataset of matches is available, the engine uses **unsupervised similarity and rule-based weighting instead of a trained classifier**. This is stated openly as a design choice in the report." | No classifier, no fitted model, no training data. Disclosed in `docs/report.md` and `docs/evaluation_report.md` | — |

**What this plan explicitly does not build:** a trained classifier (proposal §4.2 declines it),
sentence embeddings or semantic matching (proposal §11 future work), a RAG chatbot (§4.4 out of
scope), OCR (§11 limitation), Bangla or multi-language support (§11 limitation).

### 9.2 Module architecture and the dependency rule

```text
  app/ml/types.py            ← pure dataclasses; the contract. No SQLAlchemy, no FastAPI.
        │
        ├── taxonomy.py       ← loads data/skills_taxonomy.json; alias → skill resolution
        ├── text_loader.py    ← PDF/DOCX → plain text
        ├── extractor.py      ← text → DetectedSkill[]  (spaCy PhraseMatcher)
        ├── text_profile.py   ← Profile + skills + projects + education → profile_text
        ├── matcher.py        ← weighted_skill_coverage(), tfidf_cosine()
        ├── gap_analysis.py   ← required − present, ranked by weight
        ├── ranker.py         ← orchestration + combination + ranking + explainability
        ├── learning_path.py  ← OPTIONAL. Flag-gated. Imports nothing else.
        └── evaluation/       ← metrics.py, harness.py, tuning.py, __main__.py
```

**The rule, enforced by test T030/`grep`:** `grep -rn "sqlalchemy\|fastapi" backend/app/ml/` must
return **nothing**. The ML layer receives plain dataclasses and returns plain dataclasses. This is
what makes:

- the engine unit-testable with no database (`test_matcher.py`, `test_extractor.py`, …),
- the evaluation harness runnable as `python -m app.ml.evaluation` with no HTTP server,
- determinism testable (T099),
- the engine replaceable without touching a single route.

The current codebase violates this: `guidance.py:39-71` builds a prompt, calls an external API,
parses the response, catches exceptions, and persists to the database inside one handler.

### 9.3 Skill taxonomy

#### 9.3.1 Format — `backend/data/skills_taxonomy.json`

```json
{
  "version": "1.0.0",
  "updated_at": "2026-10-15",
  "skills": [
    {
      "name": "Scikit-learn",
      "slug": "scikit-learn",
      "category": "ML Frameworks",
      "description": "Python machine-learning library providing classical regression, classification, clustering, and model-selection tools.",
      "aliases": ["sklearn", "scikit learn", "sci-kit learn", "sk-learn", "sklearn library", "scikit"]
    },
    {
      "name": "PyTorch",
      "slug": "pytorch",
      "category": "Deep Learning",
      "description": "Tensor-based deep-learning framework with autograd and GPU support.",
      "aliases": ["torch", "pytorch", "py torch", "py-torch"]
    }
  ]
}
```

#### 9.3.2 Categories (8, ≈150 skills total)

| # | Category | Count | Representative skills |
|---|---|---|---|
| 1 | Programming & Core | 18 | Python, JavaScript, TypeScript, Java, C++, C, C#, Go, Rust, R, Bash, Git, GitHub, GitLab, Linux, OOP, Data Structures, Algorithms |
| 2 | Data Engineering | 20 | SQL, PostgreSQL, MySQL, MongoDB, Redis, Apache Spark, Apache Hadoop, Apache Kafka, Airflow, dbt, ETL, Data Warehousing, Data Modeling, Pandas, NumPy, Polars, Parquet, Excel, Data Cleaning, Data Visualization |
| 3 | Statistics & Mathematics | 14 | Statistics, Probability, Linear Algebra, Calculus, Hypothesis Testing, A/B Testing, Regression Analysis, Time Series Analysis, Bayesian Statistics, Sampling, Feature Engineering, Outlier Detection, Correlation, Descriptive Statistics |
| 4 | ML Frameworks | 18 | Scikit-learn, XGBoost, LightGBM, CatBoost, TensorFlow, Keras, PyTorch, JAX, statsmodels, SHAP, Optuna, MLflow, Weights & Biases, H2O.ai, AutoML, Model Selection, Cross-validation, Ensemble Methods |
| 5 | Deep Learning | 14 | Neural Networks, CNN, RNN, LSTM, GAN, Transformers, Attention Mechanism, Transfer Learning, Embeddings, Computer Vision, Object Detection, NLP, Reinforcement Learning, Self-Supervised Learning |
| 6 | NLP & LLM | 16 | spaCy, NLTK, Hugging Face, Transformers, BERT, GPT, LLaMA, LangChain, LlamaIndex, Prompt Engineering, RAG, Vector Databases, FAISS, Pinecone, Tokenization, Named Entity Recognition |
| 7 | MLOps & Cloud | 18 | Docker, Kubernetes, Terraform, AWS, Azure, GCP, EC2, S3, Lambda, SageMaker, CI/CD, GitHub Actions, Jenkins, Ansible, Helm, Prometheus, Grafana, Serverless |
| 8 | Analytics & Communication | 16 | Matplotlib, Seaborn, Plotly, Power BI, Tableau, Streamlit, Flask, FastAPI, Django, REST APIs, SQLAlchemy, PyTorch Lightning, Communication, Technical Writing, Data Storytelling, Agile |

**Total: 134.** Top up to ~150 with 16 additional real entries during curation (T042) — the proposal
says "about 150", so 145–155 satisfies it. Each skill needs ≥ 2 aliases; the alias-bearing entries
must include at minimum the ones the proposal names (`sklearn`) plus the common ones that break
naive matching (`tf`, `torch`, `k8s`, `psql`, `np`, `pd`, `llm`, `ai` is deliberately excluded as
too ambiguous).

#### 9.3.3 `ml/taxonomy.py` API

```python
@dataclass(frozen=True, slots=True)
class SkillEntry:
    skill_id: int          # assigned at seed time; the JSON stores slug, the DB supplies id
    slug: str
    name: str
    category: str
    description: str
    aliases: tuple[str, ...]

def load() -> Taxonomy
def canonicalise(term: str) -> SkillEntry | None      # "sklearn" → Scikit-learn
def all_patterns() -> list[str]                       # for the PhraseMatcher
def validate() -> list[str]                           # returns collision problems; empty = OK
```

`validate()` asserts at import time that no lowercased alias or name is claimed by two different
skills. It runs once at startup and raises on collision, because a silent collision means one
skill can never be detected.

**Match normalisation rule** (applies to both `canonicalise` and the extractor): lowercase, strip
surrounding whitespace and trailing punctuation, collapse internal whitespace, and treat `-`, `_`,
and `.` as equivalent. This is what makes `sci-kit learn`, `sci_kit_learn`, and `Scikit-learn` one
entry rather than three.

### 9.4 CV processing pipeline

```text
  POST /api/cv/upload  (auth required, 5 MB, .pdf/.docx allowlist)
        │
        ▼
  cv_service.upload_and_extract
        │
        ├─ 1. validate extension AND content type          (fixes S3)
        ├─ 2. store to UPLOAD_DIR/{uuid4}.{ext}            (preserves guidance.py:18)
        ├─ 3. INSERT resume_upload (status='uploaded')
        │
        ▼
  ml.text_loader.extract_text(path, content_type)
        │
        ├─ PDF  → pdfplumber page.extract_text() joined
        ├─ DOCX → docx.Document().paragraphs + tables
        ├─ raise ScannedDocumentError if len(text) < 50   (proposal §11: no OCR)
        └─ UPDATE resume_upload (status='extracted', extracted_text, size_bytes)
        │
        ▼
  ml.extractor.extract_skills(text)
        │
        ├─ normalise whitespace, strip bullets/separators
        ├─ PhraseMatcher over taxonomy.all_patterns(), case-insensitive
        ├─ map each match → skill_id via the alias index
        ├─ de-duplicate by skill_id, count occurrences, sort desc by count
        └─ INSERT N × resume_detected_skill (accepted = false)   ← STAGED, not user_skill
        │
        ▼
  201 { resume_upload_id, status, text_length, detected_skills[], already_confirmed[] }
        │
        │   user reviews in the DetectedSkillsPanel
        ▼
  POST /api/skills/confirm  { skills: [{skill_id, accepted, proficiency?}] }
        │
        ├─ for each accepted: UPSERT user_skill (source='cv_extracted', confirmed=true)
        ├─ UPDATE resume_detected_skill SET accepted = …
        └─ UPDATE resume_upload SET status = 'confirmed'
```

**Why the staging table exists.** If detection wrote straight to `user_skill`, a false positive
would silently inflate a user's coverage score and a false negative would silently deflate it,
with no record that the value was never confirmed. Staging makes "every skill in `user_skill` is
user-confirmed" an invariant that can be asserted in a test — and that invariant is what allows the
report to say, truthfully, that no unverified extraction influences any recommendation.

### 9.5 Matching engine

#### 9.5.1 Input — the profile text

`ml/text_profile.py` builds one document per user:

```text
{headline} {career_goal} {skill names} {skill names} {project titles} {project descriptions}
{project tech-stack names} {degree} {field_of_study} {institution} {certification names}
```

Skill names are repeated (once for the confirmed list, once weighted by proficiency) so that
TF-IDF reflects strength, not just presence. This is a deliberate, documented design choice: the
alternative — deduplicating — makes a 5/5 in TensorFlow and a 1/1 in TensorFlow indistinguishable to
the vectorizer, which is wrong for a job-matching signal.

#### 9.5.2 Weighted skill coverage

```python
def weighted_skill_coverage(
    user_skills: Mapping[int, int],      # skill_id → proficiency (1..5)
    required: Mapping[int, float],       # skill_id → importance weight (0, 1]
) -> float:
    if not required:
        return 0.0
    numerator   = sum(w * PROFICIENCY_FACTOR[p] for s, w in required.items()
                      if (p := user_skills.get(s)) is not None)
    denominator = sum(required.values())
    return numerator / denominator

PROFICIENCY_FACTOR = {1: 0.00, 2: 0.25, 3: 0.50, 4: 0.75, 5: 1.00}   # = (p-1)/4
```

Properties, each covered by `test_matcher.py`:

| Property | Assertion |
|---|---|
| Bounds | `0.0 ≤ result ≤ 1.0` for 200 randomised inputs |
| Superset | A user holding every required skill at proficiency 5 scores exactly `1.0` |
| Empty | No overlap scores exactly `0.0` |
| Monotonic | Adding a skill never lowers the score |
| Proficiency monotone | Raising a proficiency from 2 to 5 never lowers the score |
| Partial | A hand-computed value matches to 6 decimal places |
| Weight sensitivity | A role whose required skills are all weight 1.0 behaves identically to one where the same skills carry 0.5 — coverage is **scale-invariant**, which is correct, because only the *relative* importance of a role's requirements matters |

**Why `PROFICIENCY_FACTOR = (p-1)/4` and not `p/5`.** It makes a proficiency-1 skill contribute
nothing. A user who has "heard of" a technology should not receive partial credit for it against a
role that requires working command of it, and (p−1)/4 expresses that. It also guarantees the
superset case reaches exactly 1.0, so compatibility percentages stay interpretable on a 0–100
scale.

#### 9.5.3 TF-IDF cosine similarity

```python
def tfidf_cosine(profile_text: str, role_specs: Sequence[RoleSpec]) -> list[float]:
    if not profile_text.strip() or not role_specs:
        return [0.0] * len(role_specs)
    corpus = [profile_text] + [spec.description for spec in role_specs]
    vectorizer = TfidfVectorizer(
        lowercase=True, stop_words="english",
        ngram_range=(1, 2), sublinear_tf=True, min_df=1,
    )
    matrix = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(matrix[0], matrix[1:])
    return [float(min(max(s, 0.0), 1.0)) for s in sims[0]]   # clamp float noise
```

**Four decisions, each with a reason:**

1. **Fit the vectorizer per call, not once at startup.** Precomputing an IDF table over the job
   corpus and then only *transforming* the profile is faster, but it leaks the job descriptions'
   vocabulary into the profile's representation, and it means the profile's score depends on which
   other roles happen to be active. Fitting per call makes the profile row independent of the
   candidate set. At 61 documents this costs single-digit milliseconds.
2. **`ngram_range=(1, 2)`.** Unigrams alone cannot distinguish "machine learning" from "learning
   machine"; bigrams capture multi-word skill names that survive into the description text.
3. **`sublinear_tf=True`.** A CV that says "Python" 40 times should not outrank one that mentions
   four technologies once. Sublinear TF damps repetition.
4. **Clamp to [0, 1].** `cosine_similarity` can return `-1e-17` from floating-point noise, and a
   negative cosine feeding a percentage display is a visible bug.

#### 9.5.4 Combination and ranking

```python
compatibility = SKILL_COVERAGE_WEIGHT * coverage + TFIDF_WEIGHT * cosine
# Settings defaults: 0.60 / 0.40  — proposal §4.2 "about 60% / 40%"
```

```python
ranked = sorted(scores, key=lambda s: (-s.compatibility, s.job_role_id))
#           ↑ total order — the job_role_id tiebreak makes the output deterministic
```

The `job_role_id` tiebreak is not cosmetic. Many roles will score identically (for example two
roles with identical required-skill sets and similar descriptions), and without a total order
Python's `sorted` is stable but the *input* order then determines the result, which varies with
database row order. T099 asserts byte-identical output across runs; the tiebreak is what makes that
assertion hold.

#### 9.5.5 Worked example

The proposal §2 gives an illustrative example: "a user with Python, SQL, Scikit-learn, LangChain
and PyTorch may see AI Engineer 91%, ML Engineer 84% and Junior Data Scientist 76%". That text
explicitly says *"These figures illustrate the expected output format, not measured results."*
Reproducing those exact numbers by tuning weights to match them would be fabricating results, so
this plan does not do it. What the implementation must produce is the same **format**, and the
report must present the **measured** numbers.

Worked arithmetic for format illustration only:

```text
AI Engineer required:  Python 1.00, SQL 0.80, scikit-learn 0.90, PyTorch 0.85,
                       LangChain 0.60, Docker 0.70, FastAPI 0.50, AWS 0.55, Git 0.40
                       Σw = 6.30

User:  Python 5, SQL 4, scikit-learn 4, LangChain 3, PyTorch 4   (and 8 more skills)

covered  = 1.00(1.00) + 0.80(0.75) + 0.90(0.75) + 0.85(0.75) + 0.60(0.50) = 3.875
coverage = 3.875 / 6.30 = 0.615

assume tfidf_similarity = 0.72
compatibility = 0.60(0.615) + 0.40(0.72) = 0.369 + 0.288 = 0.657 → 66%
```

66 % against a 100 %-coverage role is arithmetically correct. A user holding 5 of 9 requirements
should **not** see 91 %. The illustrative 91 % in proposal §2 presupposes a profile matching most of
the role's requirements. This arithmetic is included so the team does not "fix" the engine to
reproduce a number that the proposal itself labels as illustrative.

### 9.6 Skill-gap analysis

```python
def analyse(user_skills: Mapping[int, int], role: RoleSpec) -> GapReport:
    matched = [(s, w, user_skills[s]) for s, w in role.required_skills.items() if s in user_skills]
    missing = sorted(
        ((s, w) for s, w in role.required_skills.items() if s not in user_skills),
        key=lambda t: (-t[1], t[0]),          # descending weight, id tiebreak
    )
    return GapReport(
        coverage=weighted_skill_coverage(user_skills, role.required_skills),
        matched=matched, missing=missing,
    )

def tier_of(weight: float) -> str:
    return "critical" if weight >= 0.8 else "important" if weight >= 0.5 else "desirable"
```

Tiers are the UI's reading aid, not an extra computation: they are a pure function of the weight
that already exists in `job_role_skill`, so they cannot drift from the ranking order.

The gap report reads `user_skill` **only** — never `resume_detected_skill`. An unconfirmed
extraction therefore cannot appear as a matched skill, and cannot suppress a genuine gap.

### 9.7 The optional LLM

**Constraints that make this genuinely optional, not optional-in-practice:**

| Constraint | Enforcement |
|---|---|
| Default off | `LLM_ENABLED: bool = False` in `Settings` |
| No core endpoint imports it | `recommendation_service` and `ranker` never reference `learning_path`; verified by grep in T103's review |
| Reachable only via its own endpoint | `POST /api/skill-gap/{id}/learning-path`, which returns `503 feature_disabled` when the flag is off |
| Input is already-computed | It receives a `GapReport` dataclass. It does **not** compute anything, so it cannot influence a score even when enabled |
| No key required to boot | Startup does not validate the key when `LLM_ENABLED` is false |
| Degraded on failure | A provider error returns `502` with a generic message and is logged server-side only. The core gap report is unaffected |
| Out of the critical path in the sprint plan | P2 in §5, P3 in the proposal's own risk posture |

**Task T103 is P2, not P0.** If it is not built, nothing else in this plan changes and the
compliance matrix records it as "not built — declared optional". That is the correct outcome per
proposal §4.2 and §6.4 ("Keep LLM optional, freeze scope after Sprint 2").

**Superseded code:** the LLM path at `guidance.py:45-61` is being removed entirely, because it
violates the proposal in three ways at once — it makes an external API load-bearing, its default
response is a hardcoded string (`:48`), and it returns provider error text to the client (`:59`).

### 9.8 Reproducibility

| Property | How it is guaranteed |
|---|---|
| Determinism | No RNG anywhere in `ml/`. `TfidfVectorizer` is a closed-form transform. The `(-score, job_role_id)` sort key is a total order. Asserted by T099 |
| Vocabulary stability | `TfidfVectorizer` is fit and discarded within one call; nothing is cached between requests |
| Taxonomy versioning | `skills_taxonomy.json` carries `version` and `updated_at`; `recommendation_run` records `engine_version`, so a past run can be traced to the taxonomy that produced it |
| Weight provenance | `recommendation_run` stores `coverage_weight` and `tfidf_weight` actually used, so a run generated before tuning is still explicable |
| Profile provenance | `recommendation_run.profile_snapshot` stores the exact skills/projects/education the run saw |
| Evaluation reproducibility | The harness reads the same JSONL and the same job knowledge base, so two runs on unchanged data produce identical metrics. Asserted by the harness's own determinism check |

### 9.9 Performance budget

| Operation | Target | Basis |
|---|---|---|
| Taxonomy load | < 50 ms, once per process | 150 JSON objects |
| spaCy PhraseMatcher build | < 500 ms, once per process | ~600 patterns |
| Skill extraction, 3-page CV | < 1.5 s | PhraseMatcher over ~3 000 tokens |
| TF-IDF fit + transform, 61 docs | < 100 ms | sklearn sparse |
| Coverage, 60 roles | < 20 ms | pure arithmetic |
| **Total `POST /api/recommendations`** | **< 2 s** | proposal §7.5: "within a few seconds" |
| `GET /api/skills/taxonomy?q=` | < 300 ms | indexed, 150 rows |
| `POST /api/cv/upload` (5 MB PDF) | < 4 s | dominated by pdfplumber |

All CPU-only. No GPU, no network call, no model download at request time — consistent with proposal
§6.1 and §7.1.

### 9.10 Testing strategy for the ML layer

| Test | File | What it proves |
|---|---|---|
| Alias resolution | `test_taxonomy.py` | ≥ 150 skills load; every alias resolves uniquely; no collisions; case/separator variants collapse |
| Text extraction | `test_text_loader.py` | PDF and DOCX both extract; oversize rejected; textless PDF raises `ScannedDocumentError` |
| Skill detection | `test_extractor.py` | Known CV fixture detects the right skills; **`Java` does not match inside `JavaScript`**; **`Go` does not match inside `MongoDB`**; repeated runs identical |
| Coverage maths | `test_matcher.py` | Bounds, superset = 1.0, disjoint = 0.0, hand-computed partial, monotonicity, scale invariance |
| Cosine maths | `test_matcher.py` | Self-similarity = 1.0; identical text = 1.0; disjoint text < 0.1; no negative output |
| Gap analysis | `test_gap_analysis.py` | `required − present` correctness; strict descending weight order; tier boundaries at exactly 0.8 and 0.5; empty user |
| Ranking | `test_ranker.py` | Combination formula; total-order tiebreak; `limit` respected; zero-score roles present but last |
| Determinism | `test_determinism.py` | Two full ranker runs deep-equal |
| Engine independence | `tests/test_ml_isolation.py` | `grep`-equivalent assertion that `app/ml/` imports no SQLAlchemy/FastAPI symbol |
| End-to-end extraction | `test_extraction_pipeline.py` | Sample CV → text → skills, for both formats |
| Explainability | `test_explainability.py` | `matched ∪ missing` equals the role's required set; the two are disjoint |
| Evaluation gate | `test_evaluation.py` | Top-3 hit rate ≥ 0.75 — a regression, not a snapshot, fails CI |

The Java-in-JavaScript and Go-in-MongoDB cases are the most valuable tests in this list. They are
the concrete failure mode that makes a naive keyword matcher look competent in a demo and useless in
production, and they are exactly what a curated taxonomy buys over a substring search.

---

## 10. AI Evaluation Plan

### 10.1 Why this phase exists

Proposal §2: *"Validate the matching engine on at least 20 hand-labelled sample profiles and report
the results (target: the expected role appears in the top 3 for most profiles)."*
Proposal §4.3 lists an *"ML module (skill extraction, matching, gap analysis) **with an evaluation
summary**"* as a deliverable. §8 budgets 16 man-hours for it (task 2.6).

The target "most profiles" is operationalised as **top-3 hit rate ≥ 0.75**.

**What is being measured is explicitly not a trained classifier.** There is no held-out test set in
the machine-learning sense, no training, and no fitted model. The engine is a deterministic function
of the job knowledge base. So the evaluation measures *ranking behaviour of a rule-based system
against human labels* — a legitimate and honest evaluation, provided the report describes it that way
rather than dressing it up as supervised learning.

### 10.2 Where the code lives

```text
backend/app/ml/evaluation/
├── __init__.py
├── __main__.py              # python -m app.ml.evaluation
├── metrics.py               # pure functions: top1, top3, mrr, component means
├── harness.py               # labels → ProfileSnapshot → ml.ranker.rank → metrics
├── tuning.py                # weight sweep
├── labelled_profiles.jsonl  # 24 hand-labelled profiles
├── report.py                # renders docs/evaluation_report.md
└── sample_cvs/              # 3 consented / anonymised sample CVs
```

Run: `python -m app.ml.evaluation` → prints a table, writes `docs/evaluation_report.md`, exits
non-zero if the target is missed. No HTTP server, no test fixtures beyond the JSONL — because `ml/`
has no framework dependency (§9.2).

### 10.3 Sample profile construction

**24 profiles, not 20.** The proposal requires 20+; 24 gives margin for one mislabelled profile and
still satisfies "at least 20". Proposal §7.4 assigns task 2.6 to M1 + M4, and §7.3 requires that
*"only consented or anonymised samples will be used"* — so the profiles are **constructed
synthetically from role definitions**, not harvested from real people.

Each line in `labelled_profiles.jsonl`:

```json
{
  "id": "P07",
  "name": "Backend-leaning data engineer",
  "skills": [
    { "skill_slug": "python", "proficiency": 5 },
    { "skill_slug": "sql", "proficiency": 5 },
    { "skill_slug": "postgresql", "proficiency": 4 },
    { "skill_slug": "apache-spark", "proficiency": 4 },
    { "skill_slug": "pandas", "proficiency": 4 }
  ],
  "projects": [
    { "title": "Real-time analytics pipeline",
      "description": "Built a streaming ETL job with Spark and Kafka processing 2M events per day, stored in PostgreSQL.",
      "tech_stack": ["python", "apache-spark", "apache-kafka", "postgresql"] }
  ],
  "education": [{ "degree": "BSc", "field_of_study": "Computer Science", "institution": "Example University" }],
  "expected_role": "data-engineer",
  "expected_family": "Data Engineering",
  "rationale": "Heavy SQL + Spark + pipeline project; no model-training or deployment skills, which rules out ML Engineer and MLOps Engineer."
}
```

**Construction rules that make the evaluation meaningful rather than circular:**

| Rule | Reason |
|---|---|
| Every profile's `expected_role` must exist in `job_roles.json` | Otherwise the metric is meaningless |
| `expected_role` is assigned by **reading the role's required-skill set and weights**, not by intuition | Labelling must not depend on whether the engine agrees |
| `rationale` is written **before** running the engine, and the file is committed | Post-hoc relabelling to match predictions is the single most common way an evaluation becomes worthless |
| 2 profiles per family across 10–12 families | Guarantees breadth, not depth in one family |
| **3 deliberately near-boundary profiles** where a second role is genuinely plausible (e.g. a Python/SQL/Docker profile that could be Data Analyst or MLOps Engineer) | Without boundary cases, top-3 hit rate is trivially high and proves nothing |
| **2 profiles with sparse skill sets** (4–6 skills) | Tests the empty/thin-profile path |
| **2 profiles whose skills came from the CV pipeline** | Exercises the extraction path in the evaluation and lets the report state how many labelled profiles used it |
| Profiles deliberately omit some required skills | A profile that matches 100 % of a role's requirements is not realistic; a real user is always learning |
| Names are descriptive, not personal | No real CV data is used, satisfying §7.3 |

### 10.4 Metrics

| Metric | Definition | Why it is reported |
|---|---|---|
| **Top-1 accuracy** | `expected_role` is rank 1 | The strictest measure; reported honestly whatever it is |
| **Top-3 hit rate** | `expected_role` is in ranks 1–3 | The proposal's stated target |
| **MRR** | `1/rank` of the expected role, 0 if absent in top-10 | Rewards correct ranking even when rank 1 is missed |
| **Top-5 hit rate** | In ranks 1–5 | Shows headroom above the target |
| **Mean compatibility of expected role** | Average score assigned to the correct role | Detects systematic under- or over-scoring |
| **Mean skill coverage of expected role** | Average coverage for the correct role | Isolates whether the coverage component is the weak link |
| **Mean TF-IDF similarity of expected role** | Average cosine for the correct role | Same, for the text component |
| **Per-family breakdown** | Metrics grouped by `expected_family` | Reveals which role families the engine handles poorly |
| **Weight sensitivity** | All metrics at each swept weight | Justifies the chosen 0.6/0.4 |

```python
def top_k_hit_rate(labels, predictions, k=3) -> float:
    hits = sum(1 for lab, preds in zip(labels, predictions)
               if any(p.job_role_id == lab.expected_role for p in preds[:k]))
    return hits / len(labels)

def mean_reciprocal_rank(labels, predictions) -> float:
    total = 0.0
    for lab, preds in zip(labels, predictions):
        for i, p in enumerate(preds, start=1):
            if p.job_role_id == lab.expected_role:
                total += 1.0 / i
                break
    return total / len(labels)
```

### 10.5 Weight evaluation — how 60/40 is justified

The proposal says weights start "about 60% / 40%" and "will be tuned on the labelled sample
profiles". The sweep:

| `SKILL_COVERAGE_WEIGHT` | `TFIDF_WEIGHT` | Top-1 | Top-3 | MRR |
|---|---|---|---|---|
| 0.50 | 0.50 | *measured* | *measured* | *measured* |
| **0.60** | **0.40** | *measured* | *measured* | *measured* |
| 0.70 | 0.30 | *measured* | *measured* | *measured* |
| 0.80 | 0.20 | *measured* | *measured* | *measured* |
| 0.90 | 0.10 | *measured* | *measured* | *measured* |

Selection rule, fixed **before** the sweep is run: take the weight with the highest top-3 hit rate;
on a tie, take the one closest to 0.6; on a further tie, take 0.6/0.4 and say so.

**Three honest outcomes are all acceptable, and the report must not spin any of them:**

- **0.6 wins** → "the proposal's initial weighting is supported by the data". Strongest result.
- **A different weight wins** → adopt it, state the delta, and note the proposal's "about 60/40"
  was an initial guess that evaluation refined. This is the system working as intended.
- **All weights land within noise of each other** → report that the weighting is not the binding
  constraint and that the taxonomy and job dataset quality dominate. This is a *finding*, and
  §6.4's "Limited or low-quality job data" risk is exactly about this.

Pre-committing the selection rule matters: picking the weight after seeing results and reporting
only the winner would make the evaluation a search for a good number rather than a measurement.

### 10.6 Determinism and reproducibility

| Requirement | Implementation |
|---|---|
| Two runs, identical output | The harness computes metrics twice and asserts equality before printing. Any drift is a hard failure |
| Frozen inputs | `labelled_profiles.jsonl` and `job_roles.json` are version-controlled with a `version` field; the report records both versions |
| Recorded environment | The report records Python version, `scikit-learn` version, `spaCy` version, OS, and CPU |
| Recorded command | `python -m app.ml.evaluation --profiles <path> --roles <path> --out docs/evaluation_report.md` — the report includes the exact command so the result can be regenerated |
| Stable job set | The harness reads `data/job_roles.json` (the seed file), not the live database, so a stray admin edit cannot change a published result. A `--from-db` flag exists for convenience but the report is always generated from the file |
| Regression gate | `test_evaluation.py` fails if top-3 drops below 0.75 |

### 10.7 Secondary evaluation — skill extraction

The proposal validates the *matching engine*, but extraction quality feeds it directly and §6.4 lists
"Skill extraction misses or wrongly detects skills" as a Medium risk. So a small extraction
evaluation runs alongside:

| Measure | Method | Expectation |
|---|---|---|
| Precision | Of detected skills, how many are genuinely in the CV? | Manual review of 3 sample CVs |
| Recall | Of skills a human annotator marks, how many were detected? | Human-annotated skill list per sample CV |
| False-positive guard | Does `Java` fire inside `JavaScript`? Does `Go` inside `MongoDB`? | Zero, asserted in `test_extractor.py` |
| Alias robustness | Do all 5 surface forms of Scikit-learn resolve identically? | Yes, asserted in `test_taxonomy.py` |
| User-confirmation rate | Accepted / (accepted + rejected) on the sample CVs | Reported; a low rate indicates taxonomy or matcher weakness |

This is reported as a qualitative table with a sample size of 3, **clearly labelled as indicative
rather than statistically significant**. Claiming more from three documents would be exactly the
kind of overstatement the proposal's own §4.2 honesty clause warns against.

### 10.8 Threats to validity — stated in the report

| # | Threat | Mitigation / disclosure |
|---|---|---|
| V1 | **Small sample.** 24 profiles is not statistically significant. | Report exact counts, not just percentages. State that results indicate behaviour, not a confidence interval. No p-values are claimed — none would be meaningful at n = 24 |
| V2 | **Labels are self-authored.** The same team that built the roles labelled the profiles. | Each label carries a written `rationale` committed before evaluation. The report discloses that label authorship and role authorship are not independent |
| V3 | **The job dataset is small** (50–100 roles). | Disclosed as a proposal limitation (§11) and §6.4's High risk. A 60-role candidate set makes top-3 relatively easy to achieve; the report states the raw rank distribution, not just top-3 |
| V4 | **Weights were tuned on the same 24 profiles** used to report. | The report states this explicitly. With n = 24 a held-out split is not meaningful; instead the sweep table shows every weight's score, so a reader can see the sensitivity rather than a single tuned number |
| V5 | **Profiles are synthetic**, built from role definitions. | Disclosed. A synthetic profile is often "cleaner" than a real one. §7.3's consent requirement is satisfied precisely because no real CVs were used |
| V6 | **English-language only.** | Disclosed; proposal §11 already lists it |
| V7 | **TF-IDF similarity is lexical.** A profile that says "PyTorch" and a role that says "torch" do not match. | Disclosed. Embeddings are proposal §11 future work, correctly deferred |
| V8 | **The engine has no notion of seniority.** | Disclosed as a current limitation |

### 10.9 Documented output — `docs/evaluation_report.md`

1. Executive summary — top-1, top-3, MRR, and the chosen weights, in one table
2. Method — what was measured, what was not, and the explicit statement that **no trained classifier
   was used** because no large labelled dataset exists (proposal §4.2)
3. Dataset — the 24 profiles, their expected roles, and their labelling rationale
4. Environment — Python, scikit-learn, spaCy versions; OS; CPU
5. Reproduction — the exact command
6. Results — the full per-profile table: expected role, predicted top 3, each role's compatibility,
   coverage, and cosine
7. Metrics summary — top-1, top-3, top-5, MRR, component means
8. Weight sweep — the full table from §10.5
9. Per-family breakdown
10. Skill extraction evaluation — the qualitative table from §10.7
11. Explainability example — one role, fully decomposed, showing how its percentage was produced
12. Threats to validity — §10.8 verbatim
13. Conclusion — what the engine does well, what it does not, and what the numbers do **not** claim

**Nothing in this report is written before the corresponding measurement exists.** Placeholder values
are never committed; an unmeasured cell is marked `not measured` and the report is not finalised.

---

## 11. Frontend Implementation Plan

### 11.1 Route map

Next.js 16 App Router. Route groups `(public)`, `(app)`, `(admin)` share a URL prefix while getting
their own layouts — which is how the guard at `app/(app)/layout.tsx` protects eight routes without
repeating itself.

| URL | File | Guard | Purpose | CRUD performed |
|---|---|---|---|---|
| `/` | `app/(public)/page.tsx` | public | Landing, ported from `Landing.tsx` | — |
| `/about` | `app/(public)/about/page.tsx` | public | Ported from `About.tsx` | — |
| `/features` | `app/(public)/features/page.tsx` | public | Ported from `Features.tsx`, rewritten to describe real features | — |
| `/login` | `app/(public)/login/page.tsx` | redirect if authed | Login | — |
| `/register` | `app/(public)/register/page.tsx` | redirect if authed | Registration | `User` create |
| `/feedback` | `app/(public)/feedback/page.tsx` | authed | Ported from `Feedback.tsx` | feedback create |
| `/dashboard` | `app/(app)/dashboard/page.tsx` | **authed** | Real aggregates + onboarding checklist | — |
| `/profile` | `app/(app)/profile/page.tsx` | **authed** | Profile view/edit/delete | **Profile C/R/U/D** |
| `/skills` | `app/(app)/skills/page.tsx` | **authed** | Skill manager + taxonomy picker | **Skills C/R/U/D** |
| `/projects` | `app/(app)/projects/page.tsx` | **authed** | Project manager | **Projects C/R/U/D** |
| `/education` | `app/(app)/education/page.tsx` | **authed** | Degrees | **Education C/R/U/D** |
| `/certifications` | `app/(app)/certifications/page.tsx` | **authed** | Certifications | **Certifications C/R/U/D** |
| `/resume` | `app/(app)/resume/page.tsx` | **authed** | CV upload + detected-skill confirmation | **Resume C/R** + skill confirm |
| `/recommendations` | `app/(app)/recommendations/page.tsx` | **authed** | Generate + view ranked roles | run create/read |
| `/recommendations/[id]` | `app/(app)/recommendations/[id]/page.tsx` | **authed** | A persisted run, fully decomposed | run read |
| `/skill-gap` | `app/(app)/skill-gap/page.tsx` | **authed** | Target-role gap report | read |
| `/admin` | `app/(admin)/admin/page.tsx` | **admin** | Knowledge-base overview | read |
| `/admin/jobs` | `app/(admin)/admin/jobs/page.tsx` | **admin** | Role list + create | **Job roles C** |
| `/admin/jobs/[id]` | `app/(admin)/admin/jobs/[id]/page.tsx` | **admin** | Role editor + weight editor | **Job roles U/D** |
| `/admin/evaluation` | `app/(admin)/admin/evaluation/page.tsx` | **admin** | Committed evaluation report, charted | read |
| `*` | `app/not-found.tsx` | public | 404 | — |

**Removed from the current app:** `/quiz` (`Quiz.tsx`, 372 lines of hardcoded questions whose submit
handler only calls `navigate("/recommendations")` at `:194`), and `/admin/analytics` +
`/admin/questions` — which `Header.tsx:52-54` links to but which have never existed.

### 11.2 Screen specifications

#### `/login`

| Aspect | Specification |
|---|---|
| Purpose | Authenticate and start a session |
| Components | `Card`, `Input`, `Label`, `Button`, `Alert` (all from the kept kit), `useToast` |
| API calls | `POST /api/auth/login`; `GET /api/auth/me` on mount if a token exists |
| User actions | Type credentials, submit, toggle password visibility, "create an account" link |
| Auth | Public; redirect to `/dashboard` (or the `?from=` path) if already authenticated |
| Data shown | None beyond form state |
| Loading | Button spinner, `disabled` to prevent double submit |
| Empty | N/A |
| Error | `401` → inline `Alert` "Email or password is incorrect" (never reveals which field was wrong); `429` → "Too many attempts"; network → retry affordance |
| Reuse | `Login.tsx:24-41` validation and `:43-72` submit logic, ported nearly verbatim. The password minimum is raised from 6 (`Login.tsx:35`) to 8 to match the server and `Register.tsx:59` |

#### `/register`

| Aspect | Specification |
|---|---|
| Purpose | Create an account |
| Components | `Card`, `Input`, `Select` (education level), `Checkbox` (terms), `Button`, `Alert` |
| API calls | `POST /api/auth/register` |
| User actions | Fill first name, last name, email, password, confirm, education level, accept terms |
| Auth | Public; redirect if authenticated |
| Data shown | Field-level validation errors |
| Loading | Submit button spinner |
| Error | `409` email taken → inline on the email field; `422` per-field errors from Pydantic, mapped to fields |
| **Fix carried from the current code** | `Register.tsx:21,128` collects `educationLevel` and `:71-73` requires it, but `:92` calls `api.register(name, email, password)` — **the value is silently discarded**. The new page sends it, and the API stores it. T062 |
| Reuse | `Register.tsx:40-81` validation — the strongest client validation in the current codebase — ported to zod in `lib/schemas.ts` |

#### `/dashboard`

| Aspect | Specification |
|---|---|
| Purpose | Orientation: what the user has, what is missing, and what to do next |
| Components | `Card`, `Progress`, `Badge`, `Button`, `Skeleton`, onboarding checklist |
| API calls | `GET /api/dashboard/summary`, `GET /api/dashboard/completeness` |
| Data shown | **Real**: skill count, project count, education count, certification count, CV upload count, latest recommendation run with its top role, 0–100 completeness score with named missing steps |
| **Deleted** | `mockUser` (`Dashboard.tsx:22-27`), `mockQuizStatus` (`:29-33`), `mockRecommendations` (`:37`), `mockStats` (`:70-75` — `totalUsers: "12,847"`, `averageCompletion: "18 minutes"`, `successRate: "94%"`, `careerPaths: "500+"`), and the `setTimeout(…, 1000)` fake loading at `:83-86` |
| Loading | `Skeleton` cards, no spinner-over-blank-page |
| Empty | A brand-new user sees a 5-step onboarding checklist, not zeroes |
| Error | `ErrorState` with retry; distinguishes `401` (session expired → redirect to login) from `5xx` |

#### `/profile`

| Aspect | Specification |
|---|---|
| Purpose | View, edit, and delete the profile |
| Components | `ProfileForm` (client), `Input`, `Textarea`, `Button`, `AlertDialog` for delete, `Card` |
| API calls | `GET /api/profile`, `POST /api/profile` (if absent), `PATCH /api/profile`, `DELETE /api/profile` |
| User actions | Edit headline, career goal, bio, location, links, years of experience, preferred role family; save; delete profile |
| Data shown | The profile, plus live counts of skills/projects/education/certifications |
| Loading | Form skeleton; save button spinner |
| Empty | If `GET /api/profile` returns `404`, render the form in create mode with a "Complete your profile" heading — a user who registered but never filled in a profile has a real state here |
| Error | Per-field Pydantic errors; `404` on a concurrent delete reloads the page |
| Delete UX | The `AlertDialog` names exactly what will be removed and what will be **kept** (account, login, skills, projects) — the distinction is real per §6.4, so the dialog states it |

#### `/skills`

| Aspect | Specification |
|---|---|
| Purpose | The primary data-entry screen for the engine |
| Components | `SkillPicker` (searchable taxonomy with `Command` + `Popover`), `SkillList` (`Card` + `Badge` + proficiency `Select`), `Slider` for proficiency, `AlertDialog` for removal |
| API calls | `GET /api/skills`, `GET /api/skills/taxonomy?q=&category=`, `POST /api/skills`, `PATCH /api/skills/{id}`, `DELETE /api/skills/{id}` |
| User actions | Search the taxonomy by name or alias, add a skill, set proficiency 1–5, set years used, remove a skill, filter by category or source |
| Data shown | Each skill's canonical name, category, proficiency, and provenance (`manual` / `cv_extracted`) |
| Loading | `Skeleton` rows; the picker's search is debounced 250 ms with an inline spinner |
| Empty | "No skills yet. Search the taxonomy or upload your CV to get suggestions." with both CTAs |
| Error | Duplicate → `409` surfaced as a toast, not a crash; unknown id → `422` |
| **Design note** | The search box matches aliases, so typing `sklearn` finds `Scikit-learn`. This is the taxonomy's alias feature made visible, and it teaches the user the system's vocabulary |

#### `/projects`

| Aspect | Specification |
|---|---|
| Purpose | Record what the user has built |
| Components | `ProjectForm` (`Dialog`), `ProjectCard`, `Input` for tech-stack tags with taxonomy suggestions, `Badge` for each stack entry, `AlertDialog` for delete |
| API calls | `GET/POST /api/projects`, `PATCH/DELETE /api/projects/{id}` |
| User actions | Add a project with title, description, tech stack, role, dates, repository URL; edit; delete |
| Data shown | Title, description, tech-stack badges, role, date range, repo link |
| Loading | Card skeletons; dialog submit spinner |
| Empty | "No projects yet. Projects add real signal to your profile text." |
| Error | Per-field errors; a tech-stack entry the taxonomy does not recognise is shown with a "not in taxonomy" badge rather than rejected — a user may legitimately list a tool the taxonomy has not caught up with |

#### `/education` and `/certifications`

| Aspect | Specification |
|---|---|
| Purpose | Record academic and professional credentials |
| Components | `EducationForm`, `CertificationForm`, `Card` lists, `AlertDialog` |
| API calls | `GET/POST /api/education`, `PATCH/DELETE /api/education/{id}`; same for `/api/certifications` |
| User actions | Add/edit/delete a degree (institution, degree, field, years, grade) or a certification (name, issuer, dates, credential URL) |
| Data shown | Chronologically ordered, newest first |
| Loading | Skeletons; submit spinner |
| Empty | Per-entity empty state with an "Add" CTA |
| Error | `end_year >= start_year` and `expires_on > issued_on` validated client-side and re-validated server-side |

#### `/resume`

| Aspect | Specification |
|---|---|
| Purpose | Upload a CV, see what was extracted, confirm it |
| Components | `CvDropzone`, `DetectedSkillsPanel`, `Card`, `Badge`, `Button`, `Progress`, `Alert`, `Skeleton` |
| API calls | `POST /api/cv/upload`, `GET /api/cv`, `GET /api/cv/{id}`, `DELETE /api/cv/{id}`, `POST /api/skills/confirm` |
| User actions | Drag or browse for a PDF/DOCX, watch upload progress, review detected skills, accept or reject each individually, set proficiency on accepted ones, confirm all, delete an upload |
| Data shown | Filename, size, page/word count, extraction status, the detected-skill list with each `surface_form` and `occurrence_count` |
| Loading | Full-panel `Skeleton` while extraction runs — the whole point is that extraction is not instantaneous, and pretending otherwise would be dishonest |
| Empty | Dropzone with a one-line explanation of what happens next and a note that scanned PDFs are not supported (proposal §11) |
| Error | `415` wrong type, `413` too large, `422` scanned PDF, `500` extraction failure — each with distinct copy, because each needs a different user action |
| **The confirmation step is the point of this screen** | Detected skills are staged; nothing reaches `user_skill` until the user confirms. The UI must make that unambiguous — the panel is titled "Confirm your skills" and the primary button is "Add N confirmed skills" |
| Privacy | The delete button states that the file and its extracted text are permanently removed (proposal §6.4) |

#### `/recommendations`

| Aspect | Specification |
|---|---|
| Purpose | Generate and read the ranked role list — the product's payoff |
| Components | `Button` (Generate), `RecommendationCard` (`Card` + `Badge` + `Progress`), `ScoreBreakdown`, `RunHistory`, `Skeleton` |
| API calls | `POST /api/recommendations` (a `useMutation`, **triggered by a button, never on mount**), `GET /api/recommendations/runs` |
| User actions | Generate recommendations, expand a role to see its score breakdown, open a run, filter by family |
| Data shown | Per role: rank, title, family, seniority, compatibility %, top 3 matched, top 3 missing, and on expand the two component scores and the weights used |
| Loading | `Skeleton` cards sized to the real layout |
| Empty | Two distinct empties: (a) no skills yet → "Add skills or upload your CV first" with links; (b) runs exist → show the latest one instead of an empty list |
| Error | `409 profile_incomplete` → route to `/skills`. `5xx` → retry |
| **Removed** | `mockRecommendations` (`Recommendations.tsx:24`) with its invented `averageSalary: "$85,000 - $120,000"`, `growthRate`, `jobOutlook`, and `careerPath` arrays. The current UI presents fabricated salary bands as facts; that is a credibility failure in a graded submission, not a stylistic one |
| **Not carried over** | `savedCareers` (`Recommendations.tsx:169`, component-local `useState`, lost on refresh) — if a save feature is wanted later it must be a table, not state |

#### `/recommendations/[id]`

| Aspect | Specification |
|---|---|
| Purpose | Show a stored run in full, with the full explainability chain |
| Components | `Card`, `ScoreBreakdown`, `GapTable` |
| API calls | `GET /api/recommendations/runs/{id}` |
| Data shown | The full ranked list with every matched and missing skill and its weight, the run timestamp, the weights used, and a link into `/skill-gap?role={id}` |
| Loading | `Skeleton` |
| Empty | N/A |
| Error | `404` → "That recommendation run does not exist" (also covers another user's run) |
| **Design note** | This page reads from the database, never recomputes. A stored run is a historical record; recomputing it would silently change it if the knowledge base was edited in between |

#### `/skill-gap`

| Aspect | Specification |
|---|---|
| Purpose | Answer "what do I need to learn for this role?" |
| Components | Role `Select` (grouped by family, searchable), `GapTable`, tier `Badge`, `LearningPathCard`, `Progress` |
| API calls | `GET /api/skill-gap/{job_role_id}`; `POST /api/skill-gap/{id}/learning-path` (only when enabled) |
| User actions | Pick a target role, read the gap, optionally request a learning path |
| Data shown | Coverage %, matched skills with weight and proficiency, missing skills sorted by descending weight with a tier badge each, learning path if enabled |
| Loading | `Skeleton` while the role list loads, then the report |
| Empty | No role selected → a role picker with families and counts. A role with **no** missing skills → "You already cover every required skill for this role" |
| Error | `404` → the role was deactivated or deleted; offer a role picker |
| **Ordering is the feature** | The table is sorted strictly by descending weight, and tiers are visual, so the top row is the single most valuable thing to learn next. This is §4.2's "ranked by their importance weight for that role", rendered |

#### `/admin/jobs` and `/admin/jobs/[id]`

| Aspect | Specification |
|---|---|
| Purpose | Maintain the knowledge base — the product's control plane |
| Components | `JobRoleTable` (`Table`), `JobRoleForm` (`Dialog`), `SkillWeightEditor` (taxonomy search + `Slider` + numeric input per skill), `AlertDialog`, `Badge` for `is_active` |
| API calls | `GET/POST /api/admin/jobs`, `GET/PATCH/DELETE /api/admin/jobs/{id}`, `PUT /api/admin/jobs/{id}/skills`, `GET /api/admin/taxonomy` |
| User actions | Create a role (title, family, seniority, description, responsibilities); add required skills from the taxonomy; set each importance weight; reorder; remove a required skill; save; edit role fields; deactivate; delete |
| Data shown | Title, family, seniority, required-skill count, total weight, active state, updated timestamp |
| Loading | Table skeleton; save spinner |
| Empty | "No job roles yet. Create the first one." |
| Error | `409` duplicate title or alias collision → inline; `422` weight out of range or empty skill set → inline on the field; `409 conflict_role_in_use` on delete → explain that the role must be deactivated instead, and offer that action |
| **Weight UX is the key design problem** | A `Slider` from 0.05 to 1.00 in 0.05 steps with a live numeric readout, a tier badge that updates as it moves (critical / important / desirable), and a running total so the admin can see the distribution. Raw number inputs alone invite out-of-range values and give no sense of relative importance |
| **This is a real product feature, not a database browser** | The proposal's §6.3 requires "admins maintain job data from one panel", and §2 names "no controlled knowledge base" as a problem the system solves. A grid of columns is a database browser. A form with validation, weight semantics, and tier feedback is a product feature. Flask-Admin, which is what exists today at `backend/admin.py:40-54`, is the former |

#### `/admin/evaluation`

| Aspect | Specification |
|---|---|
| Purpose | Make the validation result visible in the product, not just in a document |
| Components | `recharts` `BarChart` (top-1 vs top-3 vs MRR per family), `Table` for the weight sweep, `Card` for the headline numbers |
| API calls | `GET /api/admin/evaluation` (the parsed `docs/evaluation_report.md`) |
| Data shown | Headline metrics, per-family breakdown, the weight sweep table, the report's conclusion |
| Loading | Chart skeleton |
| Empty | "The evaluation has not been run yet." with the command to run it |
| Error | Report absent → the empty state above, not a 500 |
| Note | Reads a **committed** report. It does not re-run the harness, so the chart can never disagree with the document in the repository |

### 11.3 Cross-cutting frontend concerns

| Concern | Decision |
|---|---|
| Server state | TanStack Query. `QueryClientProvider` already exists at `App.tsx:70`; it moves into `QueryProvider.tsx`. **No new state library** |
| Auth state | `AuthProvider` context wrapping a single `/api/auth/me` call. Not a store |
| Client vs server components | Server components by default; `"use client"` only on interactive leaves (forms, pickers, tables with mutations). Reduces bundle and keeps the ported client-heavy pages honest |
| Forms | `react-hook-form` + `zod` (all installed) + `@hookform/resolvers` for client validation, mirroring `lib/schemas.ts` |
| Mutations | Invalidate the relevant `queryKey` after success. **No optimistic updates on deletes** — a failed delete that appears to succeed is worse than a 300 ms wait |
| Errors | One `onError` handler on the `QueryClient` turning `ApiError` bodies into toasts; per-page `error.tsx` boundaries for render failures |
| Loading | `Skeleton` (already in the kit) matching real layout dimensions, never a centred spinner over a blank page |
| Empty states | Every list has one. A CRUD screen that renders nothing on an empty list is a broken CRUD screen |
| Accessibility | Labelled inputs, visible focus rings, `AlertDialog` focus trapping, keyboard-navigable pickers, `aria-live` on mutation results |
| Responsive | Verified at 375 / 768 / 1280 px. Tables become card lists below `md`. Verified in T137 |
| Styling | Unchanged. `globals.css` tokens and `tailwind.config.ts` are carried over as-is |
| Fonts / theme | `next/font` with the current stack; `next-themes` (installed) for dark mode, matching `darkMode: ["class"]` in `tailwind.config.ts` |
| TypeScript | Relaxed settings (`strict: false`, `noImplicitAny: false`) are **kept during the port** so the ported pages compile, then `strict` is enabled in Sprint 6 if the remaining error count is tractable. Turning it on mid-migration would consume the sprint budget on ported code, not new code |

### 11.4 Reuse ledger

| Asset | Disposition | Note |
|---|---|---|
| `src/components/ui/*` (49 files) | **Copied byte-identical** | T135 verifies zero diffs. Radix + Tailwind only; no Vite or React Router coupling |
| `src/lib/utils.ts` (`cn()`) | Copied byte-identical | — |
| `src/hooks/use-toast.ts`, `use-mobile.tsx` | Copied | — |
| `src/index.css` | Copied to `app/globals.css` | Import site changes; content does not |
| `tailwind.config.ts` | Copied **unmodified** | Its `content` globs already include `./app/**` and `./pages/**` — a real coincidence that makes the migration cheaper than expected |
| `postcss.config.js`, `components.json` | Copied; `components.json` flips `"rsc": true` | — |
| `Header.tsx` | Ported, nav **corrected** | `next/link` + `usePathname`; the four dead links at `:101,106,170,179` are replaced with real routes; admin group wired to `isAdmin` (correction C1) |
| `Footer.tsx` | Ported, copy updated | "CareerGuide AI" → "CareerLens AI" (`:44,126`) |
| `Landing.tsx`, `About.tsx`, `Features.tsx` | Ported, copy updated | `:44,138,203` and `:77` |
| `Login.tsx` | Ported; password minimum raised to 8 | Aligns with `Register.tsx:59` and the server |
| `Register.tsx` | Ported; `educationLevel` **now sent** | Fixes the silent drop at `:92` |
| `Feedback.tsx` | Ported | Payload shape preserved |
| `NotFound.tsx` | Ported to `app/not-found.tsx` | — |
| `api/client.ts` | **Replaced** | `import.meta.env` is a Vite-only construct (`client.ts:1`); reimplemented as `src/lib/api/client.ts` keeping the `.status`/`.body` error enrichment from `:20-29` |
| `Dashboard.tsx`, `Recommendations.tsx` | **Data layer replaced**, markup preserved | Mocks deleted |
| `Quiz.tsx`, `Index.tsx`, `App.tsx`, `main.tsx`, `App.css` | **Deleted** | Superseded or not in proposal §4.1 |
| `public/`, `src/assets/` | Copied | `hero-career-guidance.jpg`, `favicon.ico`, `robots.txt` |

---

## 12. User Journey

Every step names the page, the endpoint, the database operation, and the ML operation where one
occurs.

```text
  1  Register
  2  Login
  3  Complete Profile
  4  Add Skills
  5  Add Projects
  6  Add Education / Certifications
  7  (Optional) Upload CV
  8  AI extracts skills
  9  User confirms skills
 10  Generate Recommendations
 11  Ranked AI/ML Roles
 12  Select Target Role
 13  Skill Gap Analysis
 14  Missing Skills
 15  (Optional) Learning Path
```

### Step 1 — Register

| | |
|---|---|
| Page | `/register` |
| Endpoint | `POST /api/auth/register` |
| DB | `INSERT INTO user` + `INSERT INTO profile`, one transaction |
| ML | none |
| Notes | `educationLevel` is sent and stored (fixes the drop at `Register.tsx:92`). Response carries a token, so the session starts immediately |

### Step 2 — Login

| | |
|---|---|
| Page | `/login` |
| Endpoint | `POST /api/auth/login` → token; then `GET /api/auth/me` to populate the session |
| DB | `SELECT` `user`; `UPDATE user SET last_login_at` |
| ML | none |
| Notes | Token stored under the same `localStorage` key the current app uses, so the ported code and the new code read the same store |

### Step 3 — Complete Profile

| | |
|---|---|
| Page | `/profile` |
| Endpoint | `GET` then `POST /api/profile` (or `PATCH`) |
| DB | `SELECT` / `INSERT` / `UPDATE profile` |
| ML | none — but the headline, career goal, and bio **are** concatenated into `profile_text` by `ml.text_profile`, so this step has a downstream effect on TF-IDF |

### Step 4 — Add Skills

| | |
|---|---|
| Page | `/skills` |
| Endpoint | `GET /api/skills/taxonomy?q=sklearn` → `POST /api/skills` → `PATCH /api/skills/{id}` |
| DB | `SELECT skill` (search, alias-matched); `INSERT INTO user_skill(user_id, skill_id, proficiency, source='manual')`; `UPDATE user_skill SET proficiency` |
| ML | Alias resolution via `ml.taxonomy.canonicalise` so `sklearn` resolves to the `Scikit-learn` row. **No scoring yet** |
| Notes | This is step 3 of the alignment analysis's original path: the first time per-skill proficiency becomes representable at all, which the old `profile.skills` string made impossible |

### Step 5 — Add Projects

| | |
|---|---|
| Page | `/projects` |
| Endpoint | `POST /api/projects` |
| DB | `INSERT INTO project` with `tech_stack` stored as canonical slugs |
| ML | Each stack entry is passed through `ml.taxonomy.canonicalise`; the project's title, description, and stack names are concatenated into `profile_text` |

### Step 6 — Add Education / Certifications

| | |
|---|---|
| Pages | `/education`, `/certifications` |
| Endpoints | `POST /api/education`, `POST /api/certifications` |
| DB | `INSERT INTO education_record`, `INSERT INTO certification` |
| ML | Degree, field of study, institution, and certification names are concatenated into `profile_text` |

### Step 7 — Upload CV *(optional)*

| | |
|---|---|
| Page | `/resume` |
| Endpoint | `POST /api/cv/upload` |
| DB | `INSERT INTO resume_upload` (status `uploaded` → `extracted`); the file is written to `UPLOAD_DIR/{uuid}.{ext}` |
| ML | `ml.text_loader.extract_text` → pdfplumber or python-docx |
| Notes | Auth is **required** (fixes S4). Extension **and** content type are validated (fixes S3 — `utils.py:1-4` `allowed_file()` existed but was never imported). ≤ 5 MB. A textless PDF returns `422` with a clear OCR-unsupported message rather than silently returning zero skills |

### Step 8 — AI Extracts Skills

| | |
|---|---|
| Page | `/resume` (automatic, no click) |
| Endpoint | same `POST /api/cv/upload` response |
| DB | Bulk `INSERT INTO resume_detected_skill(..., accepted = false)` — **staged, not yet in `user_skill`** |
| ML | `ml.extractor.extract_skills`: normalise → spaCy `PhraseMatcher` over ≈150 canonical names plus all aliases → map each match to a `skill_id` via the alias index → de-duplicate → count occurrences → sort descending |
| Output | `detected_skills[]` with `canonical_name`, `surface_form`, `occurrence_count` |
| Notes | `skill` + `skill_alias` are read. `user_skill` is **not** written. Nothing here can affect a recommendation yet |

### Step 9 — User Confirms Skills

| | |
|---|---|
| Page | `/resume` panel → `/skills` |
| Endpoint | `POST /api/skills/confirm` |
| DB | `UPSERT INTO user_skill(source='cv_extracted', confirmed=true)` for each accepted skill; `UPDATE resume_detected_skill SET accepted`; `UPDATE resume_upload SET status='confirmed'` — one transaction |
| ML | none (persistence only) |
| Notes | Idempotent, so a double-click is harmless. Rejected skills are recorded as `accepted = false` and never enter `user_skill`. **This is the boundary that makes "every skill is user-confirmed" a checkable invariant** |

### Step 10 — Generate Recommendations

| | |
|---|---|
| Page | `/recommendations` (button press) |
| Endpoint | `POST /api/recommendations` |
| DB | `SELECT` profile + `user_skill` + `project` + `education_record` + `certification`; `SELECT` active `job_role` + `job_role_skill`; `INSERT INTO recommendation_run`; bulk `INSERT INTO recommendation_result` |
| ML | `ml.text_profile.build` → `ml.matcher.weighted_skill_coverage` per role → `ml.matcher.tfidf_cosine` over `[profile_text] + role descriptions` → `ml.ranker.rank` combining at 0.6/0.4 |
| Notes | Triggered by a mutation, never on mount. Returns `409 profile_incomplete` at zero skills, which is more useful than a list of zeroes |

### Step 11 — Ranked AI/ML Roles

| | |
|---|---|
| Page | `/recommendations`, then `/recommendations/[id]` |
| Endpoints | response of the previous call; `GET /api/recommendations/runs/{id}` |
| DB | `SELECT` persisted `recommendation_run` + `recommendation_result` (+ join `skill` to render names) |
| ML | none on this page — it displays stored results |
| Displayed | Rank, title, family, seniority, compatibility %, top matched, top missing; on expand, `skill_coverage`, `tfidf_similarity`, and the weights used |

### Step 12 — Select Target Role

| | |
|---|---|
| Page | `/skill-gap?role={id}` |
| Endpoint | `GET /api/skill-gap/{job_role_id}` |
| DB | `SELECT` `job_role` + `job_role_skill` (+ join `skill`); `SELECT` `user_skill` |
| ML | `ml.gap_analysis.analyse` → `required − present`, sorted by descending weight, tiered |

### Step 13 — Skill Gap Analysis

| | |
|---|---|
| Page | `/skill-gap` |
| Endpoint | same as step 12 |
| ML | `ml.gap_analysis` — set difference plus `tier_of(weight)` |
| Displayed | Coverage %, matched skills with weight and proficiency, missing skills with weight and tier |
| Notes | Reads `user_skill` **only**. An unconfirmed extraction can neither appear as matched nor suppress a genuine gap |

### Step 14 — Missing Skills

| | |
|---|---|
| Page | `/skill-gap` |
| Endpoint | none — derived from step 13 |
| DB | none |
| ML | Ordering is strict descending `job_role_skill.weight` |
| Displayed | The prioritised learning list: `critical` (≥ 0.8) first, then `important` (≥ 0.5), then `desirable` |

### Step 15 — Learning Path *(optional)*

| | |
|---|---|
| Page | `/skill-gap` |
| Endpoint | `POST /api/skill-gap/{job_role_id}/learning-path` |
| DB | none |
| ML | `ml.learning_path`, taking the **already-computed** `GapReport` |
| Notes | Returns `503 feature_disabled` when `LLM_ENABLED=false`, which is the default. With it disabled, steps 1–14 are entirely unaffected. Proposal §4.2: "The core features work without it" |

### 12.1 Journey data-path summary

```text
Step  Page            Endpoint                            DB write              ML
────  ──────────────  ──────────────────────────────────  ────────────────────  ──────────────────────────
 1    /register       POST /api/auth/register             user, profile         —
 2    /login          POST /api/auth/login                user (last_login_at)   —
 3    /profile        POST|PATCH /api/profile             profile               contributes to profile_text
 4    /skills         GET /api/skills/taxonomy            user_skill            alias resolution
                      POST /api/skills
                      PATCH /api/skills/{id}
 5    /projects       POST /api/projects                  project               tech-stack canonicalisation
 6    /education      POST /api/education                 education_record      contributes to profile_text
    /certifications  POST /api/certifications            certification         contributes to profile_text
 7    /resume         POST /api/cv/upload                 resume_upload         text extraction
 8    /resume         (same response)                     resume_detected_skill spaCy PhraseMatcher
 9    /resume         POST /api/skills/confirm            user_skill,           —
                                                        resume_detected_skill,
                                                        resume_upload
10    /recommendations POST /api/recommendations          recommendation_run,   coverage + TF-IDF + ranking
                                                        recommendation_result
11    /recommendations GET /api/recommendations/runs/{id} —                     —
    /[id]
12    /skill-gap      GET /api/skill-gap/{role_id}        —                     required − present
13    /skill-gap      (same)                              —                     tiering
14    /skill-gap      (derived)                           —                     descending-weight sort
15    /skill-gap      POST …/learning-path                —                     optional, flag-gated
```

---

## 13. Admin Journey

The admin surface is a **product feature**, not a database browser. The distinction is concrete:
Flask-Admin (what exists today at `backend/admin.py:40-54`) renders arbitrary table columns and
bypasses every validation rule in the application. The target admin panel validates, enforces
weights and tiers, handles conflicts, and is reachable through the same guarded layout as every
other screen.

```text
  1  Admin Login
  2  Admin Dashboard
  3  Job Role Management
  4  Create Job Role
  5  Assign Required Skills
  6  Set Skill Importance Weights
  7  Edit / Delete Job Role
  8  View System Data
```

### Steps 1–2 — Login and dashboard

| Step | Page | Endpoint | DB | Notes |
|---|---|---|---|---|
| 1 | `/login` | `POST /api/auth/login` | `SELECT` `user` | Identical to the user journey. Role is read from the token and from `GET /api/auth/me`. An `admin` lands on `/admin`; a `user` is redirected to `/dashboard` |
| 2 | `/admin` | `GET /api/admin/overview` | Aggregates: `COUNT` on `job_role` (total/active), `GROUP BY family`, top skills by `COUNT` over `job_role_skill`, `COUNT` on `user`, `COUNT` on `recommendation_run`, `MAX(created_at)` | Every figure is a real aggregate. The current dashboard's `totalUsers: "12,847"` and `successRate: "94%"` (`Dashboard.tsx:70-75`) are fabricated and are deleted, not reproduced |

`/admin` also shows the evaluation headline metrics from `GET /api/admin/evaluation` and links to
`/admin/evaluation`.

### Step 3 — Job role management

| | |
|---|---|
| Page | `/admin/jobs` |
| Endpoint | `GET /api/admin/jobs?q=&family=&is_active=&page=` |
| DB | `SELECT job_role LEFT JOIN (COUNT job_role_skill)` |
| Access | `require_role("admin")` → `403` for a non-admin, `401` for anonymous. The `app/(admin)/layout.tsx` guard also redirects client-side |
| Display | Title, family, seniority, required-skill count, total weight, active badge, updated timestamp |
| Empty | "No job roles yet. Create the first one." with a create button |

### Step 4 — Create a job role

| | |
|---|---|
| Page | `/admin/jobs` (create dialog) |
| Endpoint | `POST /api/admin/jobs` |
| Request | `{title, family, seniority?, description, responsibilities[], skills[]}` |
| DB | `INSERT INTO job_role` (slug auto-derived from the title) |
| Validation | title non-empty and ≤ 140; `description` non-empty — a role with no description **cannot** be TF-IDF-matched, so the API refuses to create one; `family` non-empty; ≥ 1 required skill; each weight in (0, 1] |
| Errors | `409` duplicate title; `422` per-field |
| Response | `201 JobRoleRead`, then navigation to `/admin/jobs/{id}` |

### Step 5 — Assign required skills

| | |
|---|---|
| Page | `/admin/jobs/{id}` |
| Endpoint | `PUT /api/admin/jobs/{id}/skills` (full replacement) or `PATCH` for individual changes |
| Request | `[{skill_id, weight}, …]` |
| DB | `DELETE FROM job_role_skill WHERE job_role_id = :id` then bulk `INSERT` — **one transaction**, so a validation failure leaves the previous set intact |
| Component | `SkillWeightEditor`: taxonomy search (alias-aware), a selected-skills list, remove buttons, and a running total |
| Errors | `404` unknown role; `422` empty set, duplicate `skill_id`, unknown `skill_id`, or a weight outside (0, 1] |
| Notes | A full replace rather than incremental add/remove keeps the endpoint atomic and the client's state simple. Concurrent editors are protected by the transaction: the second write wins, and because it is a replace it wins completely rather than interleaving |

### Step 6 — Set skill importance weights

| | |
|---|---|
| Page | `/admin/jobs/{id}` |
| Endpoint | `PUT /api/admin/jobs/{id}/skills` |
| DB | `UPDATE job_role_skill SET weight` via the same replace |
| Component | A `Slider` (0.05 → 1.00, step 0.05) paired with a numeric input, plus a live **tier badge** that updates as the value moves: `critical` ≥ 0.8, `important` ≥ 0.5, `desirable` < 0.5 — the same thresholds `ml.gap_analysis.tier_of` uses, so the admin sees exactly the banding the user will see |
| Validation | Client: range and step. Server: `CHECK (weight > 0 AND weight <= 1)` at the database level too |
| Design note | This control is the reason the schema needs `job_role_skill` as a table with a weight column. The same skill legitimately has different importance in different roles — `Docker` is 0.9 for MLOps Engineer and 0.3 for Data Analyst — and a flat `profile.skills` string has nowhere to store that |

### Step 7 — Edit / delete a job role

| Action | Endpoint | DB | Behaviour |
|---|---|---|---|
| Edit fields | `PATCH /api/admin/jobs/{id}` | `UPDATE job_role` | Partial; title uniqueness re-checked; description may not be emptied |
| Deactivate | `PATCH /api/admin/jobs/{id}` with `is_active=false` | `UPDATE job_role` | The **recommended** removal path. Hidden from new recommendations; historic `recommendation_result` rows keep working |
| Delete | `DELETE /api/admin/jobs/{id}` | `DELETE job_role` → cascades to `job_role_skill` | Returns `409 conflict_role_in_use` if any `recommendation_result` references it, with the message suggesting deactivation. The alternative — silently destroying a user's recommendation history — is worse than an orphaned title |
| Confirm | `AlertDialog` | — | States exactly what will be removed and whether history is affected |

### Step 8 — View system data

| Panel | Endpoint | Data |
|---|---|---|
| User list | `GET /api/admin/users` | Paged: name, email, role, created, last login, counts. **Never `password_hash`** — the current Flask-Admin exposes it publicly (S1) |
| Role management | `PATCH /api/admin/users/{id}/role` | Promote/demote. An admin cannot demote themselves, preventing lockout |
| Taxonomy | `GET/POST/PATCH/DELETE /api/admin/taxonomy` | Browse, add, edit, and remove skills and their aliases. Aliases that collide with an existing skill are rejected with `409`, because a silent collision makes one skill undetectable |
| Feedback | `GET /api/admin/feedback` | Paged and filterable, ported from `guidance.py:151-187` and now behind a real role dependency |
| Evaluation | `GET /api/admin/evaluation` | The committed report, charted with `recharts` |

### 13.1 Admin journey data-path summary

```text
Step  Page                    Endpoint                              DB                          Auth
────  ──────────────────────  ───────────────────────────────────  ─────────────────────────  ──────────
 1    /login                   POST /api/auth/login                  SELECT user                  public
 2    /admin                   GET /api/admin/overview               aggregates ×5                admin
 3    /admin/jobs              GET /api/admin/jobs                   SELECT job_role + counts     admin
 4    /admin/jobs (dialog)     POST /api/admin/jobs                  INSERT job_role              admin
 5    /admin/jobs/[id]         PUT /api/admin/jobs/{id}/skills       DELETE + INSERT job_role_    admin
                                                                     skill (1 transaction)
 6    /admin/jobs/[id]         PUT /api/admin/jobs/{id}/skills       UPDATE job_role_skill       admin
                                                                     (weight)
 7    /admin/jobs/[id]         PATCH|DELETE /api/admin/jobs/{id}     UPDATE|DELETE job_role      admin
 8    /admin/*                 GET /api/admin/users|feedback|       SELECT aggregates            admin
                               evaluation, PATCH …/role
```

### 13.2 What replaces Flask-Admin, precisely

| Flask-Admin (current) | Replacement (target) |
|---|---|
| `admin.init_app(app)` at `app.py:27`, **no `is_accessible` override** → `/admin/` public | `app/(admin)/layout.tsx` + `require_role("admin")` on every route; unauthenticated → `401`, non-admin → `403` |
| Raw column grid over 6 models, including `user.password_hash` | Purpose-built screens with curated fields; `password_hash` is not in any response schema |
| Bypasses application validation entirely — an admin can write `skills = "a,b,c"` | Every write passes Pydantic validation and database `CHECK` constraints |
| Cannot express "importance weight for this skill in this role" | `SkillWeightEditor` with a slider, a tier badge, and a live total |
| No audit trail | `updated_at` on every role, surfaced in the table |
| Generic, product-agnostic | The proposal's §6.3 requirement — "admins maintain job data from one panel" — met by a real feature |

---

## 14. File-Level Implementation Map

Every path below was verified against the live repository on 29 September 2026. Paths that do not
exist today are marked **NEW**.

### 14.1 KEEP — survives the migration unchanged

| Path | What | Why |
|---|---|---|
| `frontend/src/components/ui/*.tsx` (49 files) | shadcn/ui kit | Plain React + Radix + Tailwind. No Vite, no React Router, no `import.meta.env`. Byte-identical, verified by T135 |
| `frontend/src/lib/utils.ts` | `cn()` | `clsx` + `tailwind-merge` |
| `frontend/src/hooks/use-toast.ts`, `use-mobile.tsx` | Toast + mobile breakpoint | Framework-agnostic |
| `frontend/src/index.css` → `app/globals.css` | Design tokens | CSS custom properties; the import site changes, the content does not |
| `frontend/tailwind.config.ts` | Theme | **Already contains `./app/**` and `./pages/**` in its `content` globs** — no edit needed for Next.js |
| `frontend/postcss.config.js` | Tailwind pipeline | Unchanged |
| `frontend/src/assets/hero-career-guidance.jpg`, `frontend/public/*` | Static assets | Copied |
| `frontend/.gitignore` | Already correct for a Node project | Extended with `.next/` |
| `backend/scripts/seed_db.py` | Idempotent seed pattern | Pattern is reused by four new seed scripts; the file itself is replaced (see REPLACE) |
| Design language | Colour palette, typography, spacing, card patterns, responsive behaviour | The visual identity is stack-independent |

### 14.2 MODIFY — changed but conceptually the same file

| Path | Change | Reference |
|---|---|---|
| `frontend/components.json` | `"rsc": false` → `true` | `:4` |
| `frontend/package.json` | Name `vite_react_shadcn_ts` → `careerlens-ai`; add `next`, `eslint-config-next`; remove `vite`, `@vitejs/plugin-react-swc`, `react-router-dom`; keep everything shadcn needs | `:2`, `:13-82` |
| `frontend/tsconfig.json` | Add `"jsx": "preserve"`, `"plugins": [{"name": "next"}]`, `"moduleResolution": "bundler"`, `"incremental": true` | `:1-16` |
| `frontend/tsconfig.app.json` | Next.js module resolution; `strict` stays `false` during the port | `:18-20` |
| `frontend/src/components/layout/Header.tsx` | `react-router-dom` → `next/link` + `usePathname` + `useRouter`; nav targets corrected; `isAdmin` wired | `:1-3`, `:44-55`, `:101,106,170,179` |
| `frontend/src/components/layout/Footer.tsx` | `next/link`; "CareerGuide AI" → "CareerLens AI" | `:44,126` |
| `frontend/src/pages/Landing.tsx` → `app/(public)/page.tsx` | Ported; copy updated | `:44,138,203` |
| `frontend/src/pages/About.tsx` → `app/(public)/about/page.tsx` | Ported; copy updated | `:77` |
| `frontend/src/pages/Features.tsx` → `app/(public)/features/page.tsx` | Ported; rewritten to describe the real, shipped features rather than promises | — |
| `frontend/src/pages/Login.tsx` → `app/(public)/login/page.tsx` | Ported; password minimum 6 → 8; `useSearchParams` for the post-login redirect | `:35`, `:51` |
| `frontend/src/pages/Register.tsx` → `app/(public)/register/page.tsx` | Ported; **`educationLevel` now sent** | `:21,71-73,92` |
| `frontend/src/pages/Feedback.tsx` → `app/(public)/feedback/page.tsx` | Ported; payload shape kept | `:70` |
| `frontend/src/pages/NotFound.tsx` → `app/not-found.tsx` | Ported | — |
| `backend/Dockerfile` | `python:3.11-slim` → `3.12-slim`; gunicorn → uvicorn; non-root user; spaCy model in the build | `:1-7` |
| `backend/requirements.txt` | Full replacement of the dependency set | `:1-10` |
| `backend/.env.example` | Flask keys → target keys | `:1-6` |
| `backend/README.md` | Titled "Pathfinder AI Guide - Flask Backend (starter)"; describes a product that will no longer exist | `:1-23` |
| `frontend/README.md` | Unmodified Lovable boilerplate | — |
| `frontend/src/pages/Dashboard.tsx` → `app/(app)/dashboard/page.tsx` | Data layer replaced; all mocks deleted | `:22-75`, `:83-86`, `:140-161`, `:243` |
| `frontend/src/pages/Recommendations.tsx` → `app/(app)/recommendations/page.tsx` | Data layer replaced; mock salaries/growth/career paths deleted; `savedCareers` state dropped | `:24`, `:168-169`, `:222`, `:264` |

### 14.3 MOVE — relocated, content substantially preserved

| From | To |
|---|---|
| `frontend/src/index.css` | `frontend/app/globals.css` |
| `frontend/src/pages/Landing.tsx` | `frontend/app/(public)/page.tsx` |
| `frontend/src/pages/About.tsx` | `frontend/app/(public)/about/page.tsx` |
| `frontend/src/pages/Features.tsx` | `frontend/app/(public)/features/page.tsx` |
| `frontend/src/pages/Login.tsx` | `frontend/app/(public)/login/page.tsx` |
| `frontend/src/pages/Register.tsx` | `frontend/app/(public)/register/page.tsx` |
| `frontend/src/pages/Feedback.tsx` | `frontend/app/(public)/feedback/page.tsx` |
| `frontend/src/pages/NotFound.tsx` | `frontend/app/not-found.tsx` |
| `frontend/src/components/ui/*` | `frontend/components/ui/*` |
| `frontend/src/components/layout/*` | `frontend/components/layout/*` |
| `frontend/src/lib/utils.ts` | `frontend/lib/utils.ts` |
| `frontend/src/hooks/*` | `frontend/hooks/*` |
| `backend/instance/pathfinder.db` | `docs/archive/pathfinder-legacy.db` (**archived, not migrated** — see §3.5) |

### 14.4 REPLACE — implementation discarded, new one written

| Legacy path | Replaced by | Why |
|---|---|---|
| `backend/app.py` | `backend/app/main.py` | Flask factory → FastAPI factory. Also removes the weak secret fallbacks (`:19,22`), the open CORS (`:18`), the unauthenticated admin mount (`:27`), `db.create_all()` (`:46`), and APScheduler (`:49`) |
| `backend/extensions.py` | `backend/app/core/config.py`, `app/db/session.py` | Flask extension singletons → `pydantic-settings` + SQLAlchemy 2.0 engine. Also retires the `Admin(name='Pathfinder Admin')` singleton (`:8`) |
| `backend/auth.py` | `backend/app/api/routes/auth.py` + `app/core/security.py` | Framework wrapper replaced. Logic preserved and hardened: presence-only validation (`:14-15`) → Pydantic; unnormalised email (`:16`) → lowercased with a functional unique index; no-expiry tokens (`:31`) → explicit `exp`; no logout → `POST /auth/logout` |
| `backend/guidance.py` | Split into `app/api/routes/{cv,recommendations,skill_gap,feedback,dashboard}.py` | One module held five unrelated concerns. The LLM path (`:45-61`) is deleted outright. The feedback validation (`:107-128`) is converted to Pydantic. The upload storage (`:17-20`) is preserved |
| `backend/models.py` | `backend/app/models/*.py` (9 files) | 6 flat models → 14 normalized tables. `profile.skills` (`:26`) is dropped entirely |
| `backend/admin.py` | `backend/app/api/routes/admin.py` + `app/(admin)/admin/**` | Flask-Admin is unauthenticated (S1). Replaced by a real in-app panel |
| `backend/utils.py` | `backend/app/api/routes/cv.py` | `allowed_file()` (`:1-4`) was never imported anywhere. Its logic is folded into the CV route, which actually uses it |
| `frontend/src/api/client.ts` | `frontend/src/lib/api/*.ts` (11 modules) | `import.meta.env` (`:1`) is Vite-only. The `.status`/`.body` error enrichment (`:20-29`) is preserved |
| `frontend/src/App.tsx` | `frontend/src/middleware.ts` + `app/**/layout.tsx` | No route guards existed. `QueryClientProvider` (`:70`) is preserved in `QueryProvider.tsx`. The two identical layout wrappers (`:26-45`) are replaced by route groups |
| `backend/scripts/seed_db.py` | `backend/scripts/seed_{taxonomy,job_roles,admin,dev_users}.py` | Seeded 2 users and a fake event; seeds nothing the engine needs |
| `frontend/src/pages/Quiz.tsx` | — (deleted) | Not in proposal §4.1. `mockQuizData` (`:21`); submit only navigates (`:194`) |
| `frontend/src/pages/Index.tsx` | — (deleted) | 17-line routing shim superseded by `app/(public)/page.tsx` |

### 14.5 DELETE / DEPRECATE

| Path | When | Reason |
|---|---|---|
| `backend/pathfinder.db` | **Phase 0** (T011) | 0 bytes, stray duplicate |
| `backend/__pycache__/` | Phase 0 (T011) | Build artefact |
| `backend/scripts/e2e_test.py` | Phase 9 (T159) | Ad-hoc, hardcoded to `127.0.0.1:5001` |
| `backend/scripts/inspect_db.py` | Phase 11 (T175) | SQLite-specific introspection tool |
| `backend/scripts/create_feedback_table.py` | Phase 11 (T175) | Raw DDL; Alembic replaces it |
| `backend/scripts/post_feedback_test.py`, `show_feedbacks.py` | Phase 11 (T175) | Ad-hoc scripts superseded by pytest |
| `backend/instance/` | Phase 11 (T175) | After archiving the DB to `docs/archive/` |
| `frontend/vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/App.css`, `src/vite-env.d.ts` | Phase 6 (T125) | Vite surface |
| `frontend/.env`, `frontend/.env.development` | Phase 6 (T125) | The two disagree on ports (5001 vs 5000); replaced by one `.env.example` |
| `frontend/bun.lockb` | Phase 6 (T125) | Superseded by `package-lock.json` |
| `frontend/src/pages/**` (all 11) | Phase 6 (T125) | After porting each body |
| `frontend/src/api/` | Phase 6 (T125) | Replaced by `src/lib/api/` |
| `backend/app.py`, `auth.py`, `guidance.py`, `extensions.py`, `admin.py`, `tasks.py`, `utils.py`, `models.py` | **Phase 11 (T175)** | Single auditable commit, after the new app passes the CRUD demo. Frozen — not edited — until then |
| `backend/tasks.py` (APScheduler) | Phase 11 (T175) | Out of proposal scope |
| OpenAI LLM integration | Phase 11 (T175) | Violates proposal §4.2; the replacement is flag-gated and optional |

**Retained but not part of the core:** the feedback feature. `Feedback.tsx` ports to the frontend and
`POST /api/feedback` is re-implemented with the validation from `guidance.py:107-128` and **required
auth** (it was optional at `guidance.py:94`). The `Event` analytics table is **not** recreated — the
current `analyticsEvent` client export (`client.ts:56`) has no caller and the table has no proposal
justification. Recorded as a scope reduction, not an oversight.

### 14.6 CREATE — the new backend

```text
backend/
├── alembic.ini                                     NEW
├── alembic/
│   ├── env.py                                      NEW
│   ├── script.py.mako                              NEW
│   └── versions/
│       ├── 0001_infra_and_user.py                  NEW
│       ├── 0002_domain_schema.py                   NEW
│       └── 0003_pg_trgm_indexes.py                 NEW
├── app/
│   ├── __init__.py                                 NEW
│   ├── main.py                                     NEW   FastAPI factory, lifespan, routers
│   ├── core/
│   │   ├── __init__.py                             NEW
│   │   ├── config.py                               NEW   Settings; fail-fast on weak secret
│   │   ├── logging.py                              NEW   structured logging + request id
│   │   ├── exceptions.py                           NEW   APIError + error envelope
│   │   └── security.py                             NEW   bcrypt + PyJWT
│   ├── db/
│   │   ├── __init__.py                             NEW
│   │   ├── base.py                                 NEW   DeclarativeBase, naming convention
│   │   └── session.py                              NEW   engine, SessionLocal, get_db
│   ├── models/
│   │   ├── __init__.py                             NEW   imports every model
│   │   ├── user.py                                 NEW
│   │   ├── profile.py                              NEW   skills/education/experience REMOVED
│   │   ├── skill.py                                NEW   Skill, SkillAlias
│   │   ├── user_skill.py                           NEW   the replacement for profile.skills
│   │   ├── project.py                              NEW
│   │   ├── education.py                            NEW   EducationRecord, Certification
│   │   ├── job.py                                  NEW   JobRole, JobRoleSkill
│   │   ├── resume.py                               NEW   ResumeUpload, ResumeDetectedSkill
│   │   └── recommendation.py                       NEW   RecommendationRun, RecommendationResult
│   ├── schemas/
│   │   ├── __init__.py                             NEW
│   │   ├── auth.py                                 NEW
│   │   ├── profile.py                              NEW
│   │   ├── skill.py                                NEW
│   │   ├── project.py                              NEW
│   │   ├── education.py                            NEW
│   │   ├── job.py                                  NEW
│   │   ├── cv.py                                   NEW
│   │   ├── recommendation.py                       NEW
│   │   ├── gap.py                                  NEW
│   │   └── dashboard.py                            NEW
│   ├── api/
│   │   ├── __init__.py                             NEW
│   │   ├── deps.py                                 NEW   get_db, get_current_user, require_role
│   │   ├── router.py                               NEW
│   │   └── routes/
│   │       ├── __init__.py                         NEW
│   │       ├── auth.py                             NEW
│   │       ├── profile.py                          NEW
│   │       ├── skills.py                           NEW
│   │       ├── projects.py                         NEW
│   │       ├── education.py                        NEW
│   │       ├── certifications.py                   NEW
│   │       ├── jobs.py                             NEW   public read + admin write
│   │       ├── cv.py                               NEW
│   │       ├── recommendations.py                  NEW
│   │       ├── skill_gap.py                        NEW
│   │       ├── admin.py                            NEW
│   │       ├── dashboard.py                        NEW
│   │       └── feedback.py                         NEW
│   ├── services/
│   │   ├── __init__.py                             NEW
│   │   ├── auth_service.py                         NEW
│   │   ├── profile_service.py                      NEW
│   │   ├── skill_service.py                        NEW
│   │   ├── project_service.py                      NEW
│   │   ├── education_service.py                    NEW
│   │   ├── job_service.py                          NEW
│   │   ├── cv_service.py                           NEW
│   │   └── recommendation_service.py               NEW   the DB↔ML bridge
│   └── ml/
│       ├── __init__.py                             NEW
│       ├── types.py                                NEW   pure dataclasses — the ML contract
│       ├── taxonomy.py                             NEW   alias resolution
│       ├── text_loader.py                          NEW   PDF/DOCX → text
│       ├── extractor.py                            NEW   spaCy PhraseMatcher
│       ├── text_profile.py                         NEW   profile → profile_text
│       ├── matcher.py                              NEW   coverage + TF-IDF cosine
│       ├── gap_analysis.py                         NEW   required − present
│       ├── ranker.py                               NEW   combination + ranking
│       ├── learning_path.py                        NEW   OPTIONAL, flag-gated
│       └── evaluation/
│           ├── __init__.py                         NEW
│           ├── __main__.py                         NEW   python -m app.ml.evaluation
│           ├── metrics.py                          NEW
│           ├── harness.py                          NEW
│           ├── tuning.py                           NEW
│           ├── report.py                           NEW
│           ├── labelled_profiles.jsonl             NEW   24 profiles
│           └── sample_cvs/                         NEW   3 consented/anonymised CVs
├── data/
│   ├── skills_taxonomy.json                        NEW   ≈150 skills + aliases
│   └── job_roles.json                              NEW   50–100 roles + weights
├── scripts/
│   ├── seed_taxonomy.py                            NEW
│   ├── seed_job_roles.py                           NEW
│   ├── seed_admin.py                               NEW
│   └── seed_dev_users.py                           NEW
├── tests/
│   ├── __init__.py                                 NEW
│   ├── conftest.py                                 NEW
│   ├── pytest.ini                                  NEW
│   ├── test_health.py                              NEW
│   ├── test_config.py                              NEW
│   ├── test_cors.py                                NEW
│   ├── test_auth.py                                NEW
│   ├── test_roles.py                               NEW
│   ├── test_profile_crud.py                        NEW
│   ├── test_skills_crud.py                         NEW
│   ├── test_projects_crud.py                       NEW
│   ├── test_education_crud.py                      NEW
│   ├── test_jobs_crud.py                           NEW
│   ├── test_ownership.py                           NEW
│   ├── test_cascade.py                             NEW
│   ├── test_taxonomy.py                            NEW
│   ├── test_text_loader.py                         NEW
│   ├── test_extractor.py                           NEW
│   ├── test_matcher.py                             NEW
│   ├── test_determinism.py                         NEW
│   ├── test_gap_analysis.py                        NEW
│   ├── test_ranker.py                              NEW
│   ├── test_ml_isolation.py                        NEW
│   ├── test_explainability.py                      NEW
│   ├── test_extraction_pipeline.py                 NEW
│   ├── test_evaluation.py                          NEW
│   └── fixtures/                                   NEW   sample CVs for tests
├── docker-compose.yml                              NEW
├── render.yaml                                     NEW
├── requirements.txt                                MODIFIED
├── requirements-dev.txt                            NEW
├── .gitignore                                     NEW
├── .env.example                                    MODIFIED
├── Dockerfile                                      MODIFIED
└── README.md                                       MODIFIED
```

### 14.7 CREATE — the new frontend

```text
frontend/
├── app/
│   ├── layout.tsx                                  NEW
│   ├── globals.css                                 MOVED from src/index.css
│   ├── not-found.tsx                               NEW
│   ├── (public)/
│   │   ├── layout.tsx                              NEW   Header + Footer
│   │   ├── page.tsx                                NEW   landing
│   │   ├── about/page.tsx                          NEW
│   │   ├── features/page.tsx                       NEW
│   │   ├── login/page.tsx                          NEW
│   │   ├── register/page.tsx                       NEW
│   │   └── feedback/page.tsx                       NEW
│   ├── (app)/
│   │   ├── layout.tsx                              NEW   guarded shell
│   │   ├── dashboard/page.tsx                      NEW
│   │   ├── profile/page.tsx                        NEW
│   │   ├── skills/page.tsx                         NEW
│   │   ├── projects/page.tsx                       NEW
│   │   ├── education/page.tsx                      NEW
│   │   ├── certifications/page.tsx                 NEW
│   │   ├── resume/page.tsx                         NEW
│   │   ├── recommendations/page.tsx                NEW
│   │   ├── recommendations/[id]/page.tsx           NEW
│   │   └── skill-gap/page.tsx                      NEW
│   ├── (admin)/
│   │   ├── layout.tsx                              NEW   admin guard
│   │   ├── admin/page.tsx                          NEW
│   │   ├── admin/jobs/page.tsx                     NEW
│   │   ├── admin/jobs/[id]/page.tsx                NEW
│   │   ├── admin/evaluation/page.tsx               NEW
│   │   └── admin/taxonomy/page.tsx                 NEW   P1
│   └── **/error.tsx                                NEW   error boundaries
├── components/
│   ├── ui/*.tsx                                    KEEP  49 files, byte-identical
│   ├── layout/{Header,Footer}.tsx                  MODIFIED
│   ├── providers/
│   │   ├── AuthProvider.tsx                        NEW
│   │   ├── QueryProvider.tsx                       NEW
│   │   └── ThemeProvider.tsx                       NEW
│   └── shared/
│       ├── Loading.tsx                             NEW
│       ├── EmptyState.tsx                          NEW
│       ├── ErrorState.tsx                          NEW
│       ├── ConfirmDialog.tsx                       NEW
│       └── PageHeader.tsx                          NEW
├── features/
│   ├── profile/{ProfileForm.tsx,schemas.ts}        NEW
│   ├── skills/{SkillPicker.tsx,SkillList.tsx,DetectedSkillsPanel.tsx}  NEW
│   ├── projects/{ProjectForm.tsx,ProjectCard.tsx}  NEW
│   ├── education/{EducationForm.tsx,CertificationForm.tsx}            NEW
│   ├── cv/{CvDropzone.tsx}                         NEW
│   ├── recommendations/{RecommendationCard.tsx,ScoreBreakdown.tsx,RunHistory.tsx}  NEW
│   ├── skill-gap/{GapTable.tsx,LearningPathCard.tsx}                   NEW
│   └── admin/{JobRoleForm.tsx,SkillWeightEditor.tsx,JobRoleTable.tsx,AdminOverview.tsx}  NEW
├── lib/
│   ├── utils.ts                                    KEEP  cn()
│   ├── api/
│   │   ├── config.ts                               NEW   NEXT_PUBLIC_API_URL
│   │   ├── client.ts                               NEW   typed request(), ApiError
│   │   ├── auth.ts  profile.ts  skills.ts          NEW
│   │   ├── projects.ts  education.ts               NEW
│   │   ├── certifications.ts  jobs.ts              NEW
│   │   ├── recommendations.ts  cv.ts  admin.ts     NEW
│   ├── auth/session.ts                             NEW   localStorage token helpers
│   ├── hooks/
│   │   ├── use-profile.ts  use-skills.ts           NEW
│   │   ├── use-projects.ts  use-education.ts       NEW
│   │   ├── use-certifications.ts  use-jobs.ts      NEW
│   │   ├── use-recommendations.ts  use-cv.ts       NEW
│   │   └── use-dashboard.ts                        NEW
│   └── schemas.ts                                  NEW   zod mirrors
├── hooks/{use-toast.ts,use-mobile.tsx}             KEEP
├── middleware.ts                                   NEW   route guards
├── next.config.ts                                  NEW
├── next-env.d.ts                                   NEW
├── components.json                                 MODIFIED
├── tailwind.config.ts                              KEEP
├── postcss.config.js                               KEEP
├── package.json                                    MODIFIED
├── tsconfig.json / tsconfig.app.json               MODIFIED
├── .env.example                                    NEW
├── vercel.json                                     NEW
└── README.md                                       MODIFIED
```

### 14.8 CREATE — documentation

```text
docs/
├── architecture.md          NEW   ADR: decisions D1–D5, layer boundaries, request lifecycle
├── erd.md                   NEW   Mermaid ER diagram of all 14 tables
├── legacy-freeze.md         NEW   what was frozen and when
├── tutorials.md             NEW   proposal §6.4 "early tutorials in Sprint 1"
├── evaluation_report.md     NEW   Phase 9 output
├── deployment.md            NEW   env vars, deploy order, rollback
├── report.md                NEW   final report
├── user_manual.md           NEW
├── presentation_outline.md  NEW
├── limitations.md           NEW
└── archive/
    ├── README.md            NEW   why the SQLite DB was not migrated
    └── pathfinder-legacy.db NEW   archived copy
```

---

## 15. Dependency Graph

### 15.1 Layered view

```text
                        ┌───────────────────────────────────────────┐
                        │  P0  Repository + Environment (Phase 0)    │
                        │  git init · uv/3.12 · docker compose · ADR  │
                        └────────────────────┬──────────────────────┘
                                             │
                        ┌────────────────────▼──────────────────────┐
                        │  P1  FastAPI Platform (Phase 1)            │
                        │  config · session · alembic · error  · /health │
                        └────────────────────┬──────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
┌─────────────▼──────────────┐  ┌────────────▼─────────────┐  ┌────────────▼───────────┐
│ P2a  Auth slice of schema  │  │ P2b  Domain schema        │  │ P2c  Knowledge base    │
│ `user` (revision 1)       │  │ 13 tables (revision 2)    │  │ taxonomy + job roles   │
│ → enables P3              │  │ → enables P4, P5          │  │ → enables P5           │
└─────────────┬──────────────┘  └────────────┬─────────────┘  └────────────┬───────────┘
              │                              │                              │
┌─────────────▼──────────────┐  ┌────────────▼─────────────┐                │
│ P3  AuthN + AuthZ          │  │ P4  CRUD APIs             │                │
│ register/login/logout/role │  │ profile skills projects   │                │
│ → enables P7               │  │ education certs jobs      │                │
└─────────────┬──────────────┘  └────────────┬─────────────┘                │
              │                              │                              │
              │              ┌───────────────▼──────────────────────────────▼──────────┐
              │              │ P5  AI/ML Engine                                            │
              │              │ taxonomy → text_loader → extractor → matcher →           │
              │              │ gap_analysis → ranker → recommendation_service             │
              │              │ → enables P8, P9                                           │
              │              └───────────────────────┬───────────────────────────────┘
              │                                      │
              │              ┌───────────────────────▼───────────────────────────────┐
              │              │ P6  Next.js Migration                                    │
              │              │ structure, guards, typed client, providers             │
              │              │ → enables P7                                             │
              │              └───────────────────────┬───────────────────────────────┘
              │                                      │
              │              ┌───────────────────────▼───────────────────────────────┐
              └─────────────►│ P7  Frontend Integration                                 │
                             │ real data, React Query, all CRUD in the UI             │
                             │ → enables P8, P9                                        │
                             └───────────────────────┬───────────────────────────────┘
                                                     │
                             ┌───────────────────────▼───────────────────────────────┐
                             │ P8  Recommendation & Skill-Gap UX                        │
                             │ explainable scores, weighted gap, run history            │
                             └───────────────────────┬───────────────────────────────┘
                                                     │
                             ┌───────────────────────▼───────────────────────────────┐
                             │ P9  Testing & Evaluation                                 │
                             │ pytest suite · 24 profiles · weight sweep · report      │
                             └───────────────────────┬───────────────────────────────┘
                                                     │
                             ┌───────────────────────▼───────────────────────────────┐
                             │ P10 Deployment                                           │
                             │ Vercel + Render/Railway + managed PostgreSQL            │
                             └───────────────────────┬───────────────────────────────┘
                                                     │
                             ┌───────────────────────▼───────────────────────────────┐
                             │ P11 Validation & Legacy Deletion                         │
                             └───────────────────────────────────────────────────────┘
```

### 15.2 Tasks that cannot start until something else is complete

| Blocked task | Blocked by | Why |
|---|---|---|
| T008 (docker compose up) | T007 (compose file) — and a manual Docker daemon start | No PostgreSQL, no backend |
| T019 (`session.py`) | T008 (a live PostgreSQL) | The engine needs a URL to connect to |
| T023 (migration 1) | T022 (Alembic init), T019 | Needs a target database and a configured env |
| T031 (`user.py`) | T018 (`DeclarativeBase`) | Every model subclasses the base |
| T040 (models `__init__`) | T031–T039 | Imports every module |
| T041 (migration 2) | T040 | Generated from the metadata |
| T043 (`taxonomy.py`) | T042 (the JSON exists) | Loads it at import |
| T046/T047 (seed scripts) | T041, T043 | Need tables and a taxonomy |
| T050 (`deps.py`) | T016 (token encode/decode) | Must decode what it creates |
| T052 (auth routes) | T051, T050 | Service + dependency |
| T065–T075 (CRUD routers) | T052 (identity to scope by), T064–T074 (services) | Ownership checks need the current user |
| T105 (recommendation service) | T091, T097, T102, T100 (ML), T041 (tables) | The DB↔ML bridge needs both sides |
| T094 (extractor) | T043 (taxonomy loaded) | Builds its PhraseMatcher from the patterns |
| T097 (matcher) | T096 (profile text builder) | Consumes the snapshot |
| T102 (ranker) | T097, T100 | Combines both components |
| T108 (recommendations route) | T105 | Bridges HTTP to the service |
| T109 (Next.js scaffold) | T058 (`AuthProvider` exists) | The providers must mount somewhere |
| T120 (API client) | T109 (Next.js present) | `NEXT_PUBLIC_*` requires the framework |
| T126–T131 (screens) | T124 (hooks), T065–T070 (endpoints) | Nothing to render yet |
| T141 (recommendations UI) | T108, T126 | Needs the endpoint and the shell |
| T144 (skill-gap UI) | T106, T141 | — |
| T151 (labelled profiles) | T102 (the engine), T045 (the roles) | Labels must reference real role slugs |
| T156 (evaluation test) | T155 (the harness) | — |
| T161 (Dockerfile) | T160 (green tests) | Do not containerise a failing app |
| T175 (legacy deletion) | T174 (archive), T167 (deployed and verified) | Irreversible; last |

### 15.3 What can run fully in parallel

| Parallel track | Members | Why it is safe |
|---|---|---|
| Taxonomy curation (T042) ↔ schema writing (T031–T040) | M1+M4 ↔ M2 | Different files; the taxonomy is a JSON file, the schema is Python |
| Job-role curation (T045) ↔ CRUD routers (T063–T075) | M4 ↔ M2 | Roles depend only on the taxonomy JSON, not on the routers |
| Auth (T049–T055) ↔ profile/projects/education schemas (T063, T069, T071) | M2 ↔ M2/M3 | Distinct files; only `deps.py` is shared, and it lands first |
| ML core (T091–T102) ↔ Next.js scaffold (T109–T124) | M1 ↔ M3 | Zero shared files. **This is the highest-value parallelisation in the plan** — the two largest blocks run at once |
| Frontend structure (Phase 6) ↔ CV extraction (T092–T095) | M3 ↔ M1 | — |
| Marketing pages (T115) ↔ any backend work | M3 | — |
| Education/certification UI (T130) ↔ recommendation UI (T141) | M3 | Separate routes |
| Test writing ↔ feature writing within a phase | M4 ↔ whoever | pytest tests can be written against the agreed contract before the code lands |

### 15.4 Critical path and float

```text
Critical path (no float):
T001 → T004 → T005 → T008 → T019 → T022 → T023 → T052 → T065..T075
     → T091 → T097 → T102 → T105 → T108 → T120 → T126..T131 → T141
     → T151 → T155 → T160 → T161 → T165 → T167

Float (can slip without blocking the critical path):
T012 tutorials · T029 cors test · T056 refresh token · T083 completeness
T103 learning_path (P2, optional) · T132 feedback UI (P2)
T145 LearningPathCard (P2) · T147 run history (P1) · T148 admin eval chart
T170 user manual · T171 presentation · T174 archive
```

**Total float in the plan: 12 tasks, of which 3 are P2 and optional** (T103 `learning_path`,
T132 feedback UI, T145 `LearningPathCard`). If a sprint runs short, those are cut — in that order —
without affecting any proposal requirement.

---

## 16. Six-Sprint Development Plan

Mapped onto the proposal's own six two-week sprints (§5) and its 516 man-hour budget (§8). The
proposal's sprint focuses are preserved; the phase mapping is derived from what actually has to
happen given the verified code state.

| Proposal sprint | Proposal focus | This plan's phases | Why the shift |
|---|---|---|---|
| 1 | Requirements, mockups, architecture, database design, repository setup | **0** + start of **1** | The proposal's Sprint 1 is analysis and design. That is correct — but §7.2's stack must be committed to first, and the analysis shows the stack is wrong, so Sprint 1 also absorbs the platform skeleton |
| 2 | Authentication, profile, skills, projects, education CRUD | **1** end, **2**, **3**, **4** | Sprints 1–2 of the proposal assume a working platform. Phase 0 + 1 must complete first |
| 3 | Admin job CRUD, skill taxonomy, seed job data | end of **4**, **5** (taxonomy + extraction + matcher) | The ML engine cannot start without the knowledge base, so taxonomy and job data must land inside Phase 2, not in a later sprint |
| 4 | CV upload, skill extraction, job matching engine | **5** end, **6** | Phase 5 is 128 man-hours in the proposal's own estimate — it does not fit in one sprint, so it spans 3 and 4 |
| 5 | Skill-gap analysis, dashboards, optional LLM | **7**, **8** | The UI cannot be built until the APIs are stable (Phase 7) and the endpoints exist (Phase 5) |
| 6 | Testing, bug fixing, deployment, documentation, presentation | **9**, **10**, **11** | Proposal's Sprint 6 focus, mapped onto three phases |

### Sprint 1 — Foundation

**Goal.** Establish the target architecture and a working development environment, and make the
P0 security findings unshippable.

**Backend**
- T013–T021: `app/` package, `core/config.py` (fail-fast on weak secret), `core/logging.py`,
  `core/security.py` (bcrypt + PyJWT), `db/base.py`, `db/session.py`, `app/main.py` with restricted
  CORS
- T025: `tests/conftest.py` with the transactional-rollback pattern
- T026/T027: `/health` and config-failure tests

**Frontend**
- Nothing structural. **T109 (Next.js scaffold) is deliberately not started** — see the sequencing note
  below
- Update `frontend/.gitignore` with `.next/`

**Database**
- T007/T008: `docker-compose.yml` with `postgres:16` + `pgadmin:4`, daemon started, connectivity verified
- T022: Alembic initialised, `env.py` wired to `Base.metadata`
- T023: revision 1 — `user`
- T028: `upgrade → downgrade → upgrade` round-trip verified

**AI/ML**
- T005/T006: full dependency set installed; `spacy.load("en_core_web_sm")` succeeds. This is the
  earliest possible point to discover the Python 3.14 wheel problem (E1), which is why it is here and
  not in Sprint 3

**Testing**
- `test_health.py`, `test_config.py`, `test_cors.py`
- Security regression list created (S1–S12) with an owner per item

**Deliverables**
- `git` history with the legacy tree as the first commit
- `docs/architecture.md`, `docs/erd.md` (draft)
- FastAPI serving `/`, `/health`, `/docs` against a real PostgreSQL
- `backend/.gitignore` (fixes S6)
- Alembic managing the schema (replaces `db.create_all()`)

**Definition of Done**
- [ ] `git init` + first commit + GitHub remote + project board
- [ ] `docker compose ps` shows postgres and pgadmin healthy
- [ ] `uvicorn app.main:app --reload` starts with no warnings
- [ ] `GET /health` returns `{"status":"ok","database":"ok"}`
- [ ] `alembic upgrade head && alembic downgrade base && alembic upgrade head` succeeds
- [ ] Startup **fails** without a ≥ 32-character `JWT_SECRET_KEY`
- [ ] `import spacy, sklearn, pdfplumber, docx, alembic, pytest` all succeed on Python 3.12
- [ ] No `Flask-Admin` reachable: `curl /admin/` on the new app returns `404`

> **Sequencing note — why the Next.js scaffold waits for Sprint 2.**
> The ported pages' API contracts are not known until Phase 4 completes. Starting the Next.js
> migration in Sprint 1 means writing typed client functions against endpoints that do not exist, then
> rewriting them. The one exception is a 2-hour spike: a throwaway `create-next-app` to confirm the
> 49 shadcn components and the Tailwind config compile under the App Router. If they do not, the team
> needs to know in Sprint 1, not Sprint 5. That spike is T109's first 2 hours.

### Sprint 2 — Schema, Knowledge Base, and Authentication

**Goal.** Lock the schema, load the knowledge base, and deliver working auth. This is the phase the
whole plan turns on.

**Backend**
- T031–T040: all 9 model modules
- T041: revision 2 — the 13 domain tables
- T049–T055: auth schemas, `api/deps.py` with `require_role`, `auth_service`, auth routes, `api/router.py`
- T056: token refresh

**Database**
- T042: **taxonomy curation** — ≈150 skills, 8 categories, ≥ 2 aliases each
- T043/T044: `ml/taxonomy.py` and its tests
- T045: **job-role curation** — 50–100 roles, 8–18 weighted skills each
- T046–T048: four idempotent seed scripts
- T030 verification: `update, pg_trgm, taxonomy integrity, role completeness` (§6.5.4) all clean

**AI/ML**
- T091: `ml/types.py` — the pure contract. Doing this early prevents the ML layer from ever
  importing an ORM

**Frontend**
- T058/T059: `session.ts` + `AuthProvider`
- T060: `middleware.ts` route guards
- T061: header with fully-resolved nav (fixes C1)
- T062: registration sends `educationLevel`

**Testing**
- `test_auth.py` (7 cases), `test_roles.py`, `test_cascade.py`, `test_taxonomy.py`

**Deliverables**
- 14 tables in PostgreSQL, all constraints enforced
- ≈150 skills + aliases loaded; 50–100 roles with weights loaded
- Register / login / logout / `me` / refresh working, roles enforced
- `docs/erd.md` final, matching the implemented schema exactly

**Definition of Done**
- [ ] `psql \d` shows 14 tables with enforced FKs and `ON DELETE CASCADE` on every child
- [ ] No `skills`/`education`/`experience` TEXT column on `profile`
- [ ] `python -m scripts.seed_taxonomy` reports ≥ 150 skills; running it twice changes nothing
- [ ] `python -m scripts.seed_job_roles` reports ≥ 50 roles; every role has ≥ 5 required skills
- [ ] `require_role("admin")` returns 403 for a user, 401 for anonymous
- [ ] Duplicate email → 409; weak password → 422; wrong password → 401 with an identical message
- [ ] `grep -rn "sqlalchemy\|fastapi" backend/app/ml/` returns nothing

### Sprint 3 — CRUD APIs

**Goal.** Full CRUD on all six entities the proposal names, demonstrable through the API.

**Backend**
- T063–T075: profile, skills (+ taxonomy search + confirm), projects, education, certifications,
  public job read, admin job write
- T082/T083: dashboard summary and completeness endpoints

**Database**
- No new schema. Queries and indexes only

**AI/ML**
- None. Sprint 3 is CRUD, deliberately

**Frontend**
- T109–T124: the Next.js migration in full — scaffold, providers, route groups, guards, typed API
  client, zod schemas, shared UI states, React Query hooks
- T125: Vite surface deleted, `npm run build` and `npm run lint` clean

**Testing**
- `test_profile_crud.py`, `test_skills_crud.py`, `test_projects_crud.py`, `test_education_crud.py`,
  `test_jobs_crud.py`, `test_ownership.py`

**Deliverables**
- 61 endpoints live (§7.11)
- Next.js app with all 20 routes rendering, guards active
- All five §4.1 CRUD entities reachable via API, ownership enforced

**Definition of Done**
- [ ] Every §8.1 CRUD cell has a passing test
- [ ] `test_ownership.py` proves user A cannot touch user B's rows (404, not 403)
- [ ] `PUT /api/admin/jobs/{id}/skills` is atomic — a failed validation leaves the old set intact
- [ ] `npm run build` and `npm run lint` pass with zero errors
- [ ] Anonymous access to `/dashboard` redirects to `/login`; a non-admin on `/admin/jobs` is
      redirected to `/dashboard`
- [ ] `grep -rn "react-router-dom\|vite" frontend/package.json` returns nothing
- [ ] `src/components/ui/` has 49 files with zero diffs from the originals

### Sprint 4 — AI/ML Engine

**Goal.** The project's defining contribution: a real, explainable, deterministic recommendation
engine, and the CV pipeline feeding it.

**Backend**
- T094/T095: spaCy extractor + tests (including the Java-in-JavaScript guard)
- T092/T093: text loader + tests
- T096: profile text builder
- T097/T098: coverage + TF-IDF cosine + maths tests
- T100/T101: gap analysis + tests
- T102: ranker with the deterministic tiebreak
- T099: determinism test
- T104/T105: recommendation schemas + the DB↔ML service
- T106/T107/T108: skill-gap, CV, and recommendation routes

**Database**
- T038/T039 already exist; Sprint 4 verifies the recommendation write path under load

**AI/ML**
- The complete engine. T103 (`learning_path.py`) is **P2 — build it only if the sprint has slack**

**Frontend**
- T126–T133: dashboard, profile, skills, projects, education/certifications, resume, admin jobs
- T135: the §8 CRUD matrix walk with a screenshot per cell
- T137–T140: responsive check, build, journey walk

**Testing**
- `test_matcher.py`, `test_extractor.py`, `test_gap_analysis.py`, `test_ranker.py`,
  `test_determinism.py`, `test_ml_isolation.py`, `test_explainability.py`

**Deliverables**
- `POST /api/cv/upload` → text → detected skills → confirmation
- `POST /api/recommendations` → ranked, explainable roles with compatibility %
- `GET /api/skill-gap/{id}` → weighted, prioritised missing skills
- Every CRUD operation demonstrable in the browser
- Zero mock data in the served app

**Definition of Done**
- [ ] `alias` resolution: `sklearn` / `scikit learn` / `SKLearn` all → Scikit-learn
- [ ] `Java` does not match inside `JavaScript`; `Go` does not match inside `MongoDB`
- [ ] Coverage and cosine are in [0, 1] over 200 randomised inputs
- [ ] Two runs over identical input produce byte-identical output
- [ ] Every recommended role has matched and missing skills that **partition** its required set
- [ ] A scanned PDF returns 422 with an OCR-unsupported message
- [ ] `POST /api/recommendations` completes in < 2 s for 25 skills × 60 roles
- [ ] `grep -rn "mock\|12,847\|94%" frontend/app frontend/src` returns nothing application-facing
- [ ] S1, S3, S4, S5 are closed (S2 and S6 closed in Sprint 1)

### Sprint 5 — Recommendation UX, Evaluation, and Admin Completion

**Goal.** Make the output understandable, prove the engine works, and finish the admin surface.

**Backend**
- T148 support: `GET /api/admin/evaluation`
- Any fixes the evaluation surfaces in the engine

**Database**
- No schema change. Only seed refinement from evaluation findings

**AI/ML**
- T151: **24 hand-labelled profiles** with rationale written before running the engine
- T152/T153: metrics + harness
- T154: weight sweep across 0.5/0.5 … 0.9/0.1
- T155: `python -m app.ml.evaluation` writes `docs/evaluation_report.md`
- T156: `test_evaluation.py` as a regression gate
- T158: sample CVs + end-to-end extraction test
- T160: full suite, ≥ 60 tests, coverage recorded

**Frontend**
- T141–T143: recommendations list, score breakdown, persisted run detail
- T144: skill-gap with tiers and ordering
- T146/T147: empty states and run history
- T134: admin overview
- T148: evaluation chart (recharts)
- T145 learning-path card — **only if T103 was built**

**Testing**
- `test_evaluation.py`, `test_extraction_pipeline.py`, plus the full-suite run

**Deliverables**
- `/recommendations` and `/skill-gap` fully explainable
- Evaluation report committed with measured numbers
- The chosen weights, justified
- `/admin/evaluation` chart

**Definition of Done**
- [ ] Top-3 hit rate ≥ 0.75 over 24 profiles; top-1 and MRR reported honestly
- [ ] Two consecutive harness runs produce identical metrics
- [ ] The weight sweep table is committed with all five rows
- [ ] The report contains the §4.2 design-honesty disclosure and the §10.8 threats to validity
- [ ] `test_evaluation.py` fails if top-3 drops below target
- [ ] A role's missing skills are ordered strictly by descending weight, tiered at 0.8 and 0.5
- [ ] The score breakdown shows both components and the weights used
- [ ] `pytest` green, ≥ 60 tests, 0 failures
- [ ] No placeholder value appears anywhere in `docs/evaluation_report.md`

### Sprint 6 — Deployment, Documentation, and Cleanup

**Goal.** Ship it, prove it, document it, and remove the predecessor.

**Backend**
- T161/T162: Dockerfile and the `api` Compose service
- T163: `render.yaml`
- T165: production database, environment variables, `alembic upgrade head`, seed

**Database**
- Production schema created by migration, seeded by script. No manual SQL anywhere

**AI/ML**
- None. The engine is frozen; a change now invalidates the evaluation report

**Frontend**
- T164: `vercel.json`, `NEXT_PUBLIC_API_URL`, production build

**Testing**
- T166: `docs/deployment.md`
- T167: the full journey against the **deployed** URL, run by a member who did not build the
  feature, on desktop and phone viewports

**Docs**
- T169: `docs/report.md` with the design-honesty clause and the §11 limitations
- T170: user manual
- T171: presentation outline + limitations
- T172: branding sweep — zero "Pathfinder", zero "CareerGuide AI"
- T173: both READMEs rewritten
- T168: the §18 matrix walked, every row with evidence
- T174: archive the legacy SQLite DB
- T175/T176: delete the legacy tree in one auditable commit

**Deliverables**
- A public HTTPS frontend and API with a real PostgreSQL database
- The report, manual, and presentation
- A repository containing only CareerLens AI

**Definition of Done**
- [ ] `/health` and `/docs` reachable on the deployed API
- [ ] `alembic upgrade head` run against production; no secret in the repository
- [ ] The full §12 journey completed on the deployed URL by a second person
- [ ] Local `docker compose up` still works as the offline demo fallback (proposal §6.4)
- [ ] Every §18 row reads ✅ with evidence
- [ ] `grep -rn "Pathfinder\|CareerGuide" backend/ frontend/` returns nothing
- [ ] After the deletion commit, the app still builds, tests pass, and it runs

### 16.1 Effort check against the proposal's budget

| Proposal stage | Proposal man-hours | This plan's distribution | Verdict |
|---|---|---|---|
| 1 Analysis & Design | 48 | Phases 0 + design portion of 2 (≈ 55) | Slightly over — the stack decision and the ER design are larger here because the schema is being created, not reviewed |
| 2 Data Prep & ML Engine | 128 | Phase 2 curation + Phase 5 (≈ 130) | On budget |
| 3 Implementation | 236 | Phases 1, 3, 4, 6, 7, 8 (≈ 240) | On budget |
| 4 Testing & QA | 68 | Phase 9 (≈ 70) | On budget |
| 5 Deploy & Docs | 36 | Phases 10, 11 (≈ 40) | Slightly over |
| **Total** | **516** | **≈ 535** | **≈ 4 % over, absorbed by dropping T103/T145 (P2, ≈ 30 h) if needed** |

The proposal budgets 516 hours across 4 members over 12 weeks — about 11 hours per member per week.
The ~4 % overrun is well inside that, and the plan identifies exactly which optional work to cut if
it is not.

---

## 17. Risk Management

### 17.1 Migration and infrastructure risks

| # | Risk | Impact | Probability | Mitigation | Fallback |
|---|---|---|---|---|---|
| **R1** | **Docker daemon not running** — verified: `dial unix /var/run/docker.sock: no such file or directory`. Nothing else is installable: no `psql`, no `apt`, no passwordless `sudo` | **Critical** — blocks Sprint 1 entirely | **High** (already true) | T008 is the first infrastructure task; the user starts Docker Desktop before Sprint 1 begins. The plan treats it as a prerequisite, not a task | Free managed PostgreSQL (Neon or Supabase free tier). Works with zero local install and doubles as the production database. Switching costs one `DATABASE_URL` and one Compose file |
| **R2** | **Python 3.14 wheel resolution** — verified: `thinc 9.0.0+` publishes cp39–cp312 only, while `spacy 3.8.16` allows `thinc <9.3.0`, so a resolver on 3.14 may try a from-source build | High — a failed or 10-minute install blocks Phase 1 | Medium | T004 pins **Python 3.12** via `uv`; every wheel in the stack has a cp312 binary. Verified in T006 | `uv pip install --only-binary=:all:` to fail fast rather than compile; or drop to `spacy` with a pinned `thinc==8.3.13` |
| **R3** | **Framework migration scope** — replacing Flask, SQLite, and Vite at once | High — rework if underestimated | Medium | Phases 1, 4, 6 are separately gated with completion criteria. The ML layer and the domain schema are framework-independent, so the genuinely expensive intellectual work is not at risk from a framework choice | Cut the Next.js migration to a later sprint and ship the Vite SPA for the demo, disclosing the deviation. Chosen against — the proposal commits to Next.js |
| **R4** | **SQLAlchemy model ↔ migration drift** — `autogenerate` produces a diff that does not match the intent | Medium — confusing failures | Medium | Every revision is hand-reviewed; `upgrade → downgrade → upgrade` is verified per revision (T028); §6.5.4 verification queries run after each | Delete the revision, edit the models, regenerate. Safe because revision 1 and 2 are the only ones and no production data exists yet |
| **R5** | **shadcn components incompatible with App Router** | Medium | Low–Medium | 2-hour spike in Sprint 1 (the sequencing note) compiles all 49 under Next.js **before** committing a sprint to the migration | Mark a component `"use client"`. If a component fundamentally breaks, replace that one component; the kit is copy-paste by design, so a replacement is a file swap |
| **R6** | **spaCy model unavailable offline / download blocked** | High — blocks extraction | Low | T006 proves the model loads in Sprint 1, not Sprint 4. Commit the model directory to git if the download is unreliable | `spacy.blank("en")` with a hand-built `PhraseMatcher`. `PhraseMatcher` works on a blank pipeline, so **phrase matching — the only spaCy feature used — does not require a statistical model at all.** This is a genuinely safe fallback |

### 17.2 Data and AI quality risks

| # | Risk | Impact | Probability | Mitigation | Fallback |
|---|---|---|---|---|---|
| **R7** | **Skill taxonomy quality** — 150 skills, and a bad taxonomy degrades every downstream feature | **High** — it is the foundation of extraction, coverage, and gap | Medium | 8 categories, ≥ 2 aliases each, including the surface forms that actually break naive matching (`tf`, `torch`, `k8s`, `psql`, `np`, `pd`). `taxonomy.validate()` fails loudly on alias collisions. Curation is a 2-person task (proposal §10, M1+M4) with a review pass | Cut the taxonomy to the 80 highest-frequency AI/ML skills and state the scope reduction. The engine does not care about the count; the proposal says "about 150" |
| **R8** | **Job dataset quality** — proposal §6.4 rates this **High** | **High** — a weak candidate set makes every recommendation weak | Medium | 50–100 roles, 8–18 weighted skills each, weights in [0.3, 1.0] summing to ≈ 1.0. A §6.5.4 query rejects any role with < 5 required skills. Curated from public postings | Ship 30 solid roles rather than 100 thin ones, and disclose the count. Quality beats quantity for a curated knowledge base |
| **R9** | **CV parsing failures** — exotic layouts, multi-column, tables, images | Medium | **High** (guaranteed to happen at least once) | `text_loader` is isolated and format-dispatching; extraction is tested on a generated PDF and DOCX. A textless PDF raises `ScannedDocumentError` → `422` with a clear OCR-unsupported message rather than a silent zero | The user can always add skills manually — that path is independent of CV upload. The UI states this in the empty state. **The system degrades to manual entry, which is a legitimate design, not a failure** |
| **R10** | **Extraction false positives** — `Java` inside `JavaScript` | Medium — silently inflates coverage | High without testing | `test_extractor.py` asserts both the Java-in-JavaScript and Go-in-MongoDB cases, plus a "not in the document" negative set. The user confirmation step is the structural defence: nothing reaches `user_skill` unconfirmed | Tighten the phrase patterns, add a stop-alias list, re-run the harness. Both are data changes in one JSON file |
| **R11** | **Insufficient evaluation profiles** — 24 is small | Medium | Certain | 24 rather than 20 for margin. Pre-committed selection rule for the weight sweep. Full per-family breakdown | None needed — 24 exceeds the proposal's requirement. The report discloses the sample size and declines to claim statistical significance |
| **R12** | **TF-IDF scores hard to interpret** — users see a number with no intuition for it | Medium — an explainability failure dressed as a feature | Medium | The score is **decomposed on the UI**: both components, both weights, the formula rendered literally, and every matched/missing skill with its weight. This is proposal §2's "explain each score with matched skills" and §3.4's differentiator over the competitors | Present the two components as the headline instead of the combined percentage, if that reads better. The components are the more meaningful signal anyway |
| **R13** | **Weight tuning overfits 24 profiles** | Medium — a tuned number that does not generalise | Medium | The full sweep table is published, so a reader sees the sensitivity rather than a single tuned value. The report states that weights were tuned and reported on the same set | Use the proposal's 0.6/0.4 uncritically and say the sweep showed the choice is not sensitive. An honest null result is a valid finding |
| **R14** | **Proficiency semantics are arbitrary** — `(p-1)/4` is a design choice, not a derived fact | Low–Medium | Certain | Documented explicitly in §9.5.2 with the reasoning, and the coverage function is one constant away from a different choice | Any monotone mapping in [0, 1] is defensible; the constant is a one-line change and the tests are mapping-agnostic |

### 17.3 Product, process, and delivery risks

| # | Risk | Impact | Probability | Mitigation | Fallback |
|---|---|---|---|---|---|
| **R15** | **Time constraints** — 516 hours, 4 members, one semester | **High** | Medium | Proposal §6.4 freezes scope after Sprint 2. This plan identifies exactly **12 tasks with float**, of which 4 are P2 and optional (T103, T132, T145, and run history). Cutting them costs nothing in proposal compliance | Cut Sprint 5's admin evaluation chart and the LLM path; ship the core journey and the evaluation report as documents |
| **R16** | **Scope creep toward RAG/embeddings/OCR** — proposal §11 lists all three as future work | Medium — a semester lost to a tangent | Medium | They are explicitly out of scope in §1.6 and §9.1 of this plan. Any new feature goes to a "Future Works" list, not the backlog | — |
| **R17** | **Free-tier hosting limits or downtime** — proposal §6.4 rates this Low | High on the demo day | Medium | Local `docker compose up` is maintained as a working offline demo (T162, T167). Deployed to two platforms if free tiers allow | Demo from localhost. A working local system is a legitimate fallback and the proposal's own mitigation names it |
| **R18** | **No version control** — the repository is not a git repo (verified, correction C4) | **Critical** — the Phase 11 deletions become unrecoverable and the proposal's §5 agile process has no backlog | **Certain, today** | T001 is the first task in the plan, before anything else | None. This is a prerequisite, not a risk to be managed |
| **R19** | **Member unavailability** — proposal §10 limits a task to two members | Medium | Medium | Proposal §10's own mitigation: two members per task, workload reviewed each sprint. §15.3's parallel tracks make it easy for one person to be blocked without stalling a pair | Re-pair; the critical path (§15.4) is documented so a substitute can pick it up |
| **R20** | **Supervisor rejects the stack decision** — the proposal commits to FastAPI/PostgreSQL/Next.js and the codebase is Flask/SQLite/Vite | High — potentially invalidates Phases 1, 4, 6 | Low (the proposal is the submitted artifact) | Raise it in **Sprint 1** (T003, and T012's team discussion), not at the final review. At that point confirming the plan is a five-minute conversation; discovering it in Sprint 5 is a disaster | Fall back to the Vite SPA + Flask + PostgreSQL hybrid: keep the ML layer and the domain schema (the expensive intellectual work), swap only the serving layer. §0.3/§14 show exactly what survives either way |
| **R21** | **Deployment fails on the spaCy model** — the container is 500 MB+ and Render's free tier has a build timeout | Medium | Medium | The spaCy model is downloaded in the Dockerfile's **build** step, not at runtime, so the container starts fast. `en_core_web_sm` is ~12 MB | Pin the model as a direct `pip` dependency (`en-core-web-sm` on PyPI) so it installs as a wheel; or use `spacy.blank("en")` per R6, which removes the dependency entirely |
| **R22** | **Evaluation report and live behaviour disagree** — an admin edits roles after the report was generated | Medium — a credibility problem in grading | Medium | The harness reads the **version-controlled `job_roles.json`**, not the live database, and records the file version in the report | Regenerate the report and commit it. The `test_evaluation.py` gate catches the mismatch |
| **R23** | **Next.js App Router learning curve** — the team is new to it (proposal §6.4) | Medium | Medium | Proposal §6.4's own mitigation: tutorials in Sprint 1 (T012) and pair work on every task. The ported pages are mostly client components, so the RSC mental model is not deeply exercised | Use more client components than ideal. Slightly less idiomatic, functionally identical, and honest |

### 17.4 Security findings inherited from the current codebase

These are **verified findings in the code that exists today**, not hypotheticals. All are P0 and
must be closed before deployment.

| # | Finding | Severity | Evidence | Closed by |
|---|---|---|---|---|
| **S1** | **Flask-Admin mounted with no authentication.** No `is_accessible` override exists, so `/admin/` is publicly reachable and lists `user.email` **and `user.password_hash`** to anonymous visitors. Password hashes are offline-attackable | **Critical** | `extensions.py:8`, `app.py:27`, `admin.py:40-54` | T175 removes Flask-Admin entirely. The new `/api/admin/*` requires `role == 'admin'` on every route, and `UserRead` has no `password_hash` field |
| **S2** | Fully open CORS — no origins allowlist | High | `app.py:18` | T020: `CORSMiddleware` with `allow_origins` from `ALLOWED_ORIGINS`; T029 asserts an unlisted origin gets no header |
| **S3** | No file-type validation on upload. `allowed_file()` exists but is **never imported anywhere** | High | `utils.py:1-4`, `guidance.py:20` | T107 validates extension **and** content type, with a 5 MB limit |
| **S4** | Optional JWT on write endpoints — anonymous callers write `Upload`, `GuidanceSession`, `Event`, and `Feedback` rows with `user_id = NULL`, permanently unattributable | High | `guidance.py:10,40,73,94` | T050: every write requires `get_current_user`. `resume_upload.user_id` and `feedback.user_id` are `NOT NULL` |
| **S5** | **IDOR** on upload download — sequential integer ID, no auth, no ownership check | High | `guidance.py:31-37` | T107: `GET /api/cv/{id}` is auth-required and scoped by `user_id` |
| **S6** | No `backend/.gitignore` — `.env`, `pathfinder.db` (32 KB), and a 162 MB `venv/` are all in the tree | High | Verified: only `frontend/.gitignore` exists | T001 root `.gitignore` + T024 `backend/.gitignore` |
| **S7** | Weak secret fallbacks — `'dev-secret'`, `'jwt-secret'` when the env var is unset | Medium | `app.py:19,22` | T014: startup **fails loudly** below 32 characters. `T027` asserts it |
| **S8** | Upstream provider error text returned to the client **and persisted** | Medium | `guidance.py:59` | The OpenAI path is deleted (T175). `core/exceptions.py` never emits exception text; T136 surfaces `ApiError` codes to the UI |
| **S9** | Unnormalised email allows duplicate accounts — `A@B.com` and `a@b.com` are two users | Medium | `auth.py:16` | Lowercase + trim before the check, plus a functional unique index on `lower(email)`. `test_auth.py` covers it |
| **S10** | Foreign keys declared but never enforced — SQLite defaults `PRAGMA foreign_keys=OFF` and the code never sets it, so deleting a user orphans `profile`, `upload`, and `feedback` | Medium | `models.py:24,33,40,46,54` | PostgreSQL enforces them. T081 asserts the full cascade in one statement |
| **S11** | Duplicate database file — `backend/pathfinder.db` (0 bytes) vs `instance/pathfinder.db` (32 KB) | Low | Verified | T011 deletes the stray; T174 archives the live one with an explanation |
| **S12** | Unbounded anonymous upload storage — any caller can write files with no quota | Low | `guidance.py:17-20` | Auth-gated (S4) + a 5 MB per-file limit + authenticated `DELETE /api/cv/{id}` |

**Note.** `backend/.env` currently holds placeholders (`replace-with-a-secret`, empty
`OPENAI_API_KEY`), so no live secret is exposed today. The risk is structural: nothing prevents a
real key from being committed. S6 is preventive, not a breach response.

---

## 18. Proposal Compliance Matrix

Every row is a requirement from `CareerLens_AI_Project_Proposal.docx` mapped to the task that
satisfies it. **No row may be ticked without a `file:line` or a test name as evidence.** A row
without evidence is a bug, not a documentation gap (T168).

### 18.1 Committed technology stack (§7.2)

| Proposal requirement | Implementation | Evidence | Status |
|---|---|---|---|
| React / **Next.js** | Next.js 16 App Router, 20 routes, route groups + `middleware.ts` | T109–T125; `frontend/app/**` | ⬜ |
| **Tailwind CSS** | Unmodified `tailwind.config.ts` + `app/globals.css`; 49 shadcn components retained | T111; `frontend/tailwind.config.ts` | ⬜ |
| TypeScript | Next.js TypeScript config; `npm run build` clean | T125 | ⬜ |
| Python 3 | Python 3.12 venv pinned via `uv` | T004; `backend/.python-version` | ⬜ |
| **FastAPI** | `app/main.py` factory, 12 `APIRouter`s, 61 endpoints | T020, T052, T065–T108 | ⬜ |
| **SQLAlchemy** | 2.0 `DeclarativeBase`, `Mapped[]`, `SessionLocal` | T018, T019 | ⬜ |
| **Pydantic** | `schemas/` with separate Create/Update/Read models per domain | T049, T063, T066, T069, T071, T073 | ⬜ |
| **JWT** authentication | PyJWT HS256, explicit `exp`, `sub`, `role`; `get_current_user` / `require_role` | T016, T050 | ⬜ |
| **PostgreSQL** | `postgres:16` in Compose; production instance in Phase 10 | T007, T165 | ⬜ |
| pgAdmin | `pgadmin:4` Compose service | T007 | ⬜ |
| **scikit-learn** | `TfidfVectorizer` + `cosine_similarity` in `ml/matcher.py` | T097 | ⬜ |
| **pandas / NumPy** | Available in the env; used for the harness tables and weight sweep | T152, T154 | ⬜ |
| **spaCy** | `PhraseMatcher` over ≈150 canonical names + aliases | T094 | ⬜ |
| pdfplumber / PyPDF | `ml/text_loader.py` PDF branch | T092 | ⬜ |
| **python-docx** | `ml/text_loader.py` DOCX branch | T092 | ⬜ |
| Optional LLM API | `ml/learning_path.py`, flag-gated, **P2** | T103 | ⬜ *(optional — may be "not built", which is compliant)* |
| Docker | Compose + `backend/Dockerfile` | T007, T161 | ⬜ |
| Git / GitHub | T001, T002 | ⬜ |
| Postman | Optional; the OpenAPI UI at `/docs` covers the same need | T020 | ⬜ |
| Figma / draw.io | Mockups from the existing UI; `docs/erd.md` is Mermaid | T010 | ⬜ |
| Jupyter Notebook | Exploratory analysis of the weight sweep before codifying it into `evaluation/tuning.py` | T154 | ⬜ |
| **pytest** | ≥ 60 tests | T026–T081, T093–T160 | ⬜ |
| Browser testing | T135 (CRUD matrix), T140 (journey), T167 (deployed) | ⬜ |
| **Vercel** (frontend) | `vercel.json` + `NEXT_PUBLIC_API_URL` | T164 | ⬜ |
| **Render / Railway** (backend + DB) | `render.yaml` + managed PostgreSQL | T163, T165 | ⬜ |

### 18.2 In-scope features (§4.1)

| Module | Requirement | Implementation | Status |
|---|---|---|---|
| **Authentication** | Register | `POST /api/auth/register` → T051, T052 | ⬜ |
| | Login | `POST /api/auth/login` → T051 | ⬜ |
| | **Logout** | `POST /api/auth/logout` → T052, T059 | ⬜ |
| | Password hashing | bcrypt via `passlib` → T016 | ⬜ |
| | JWT sessions | PyJWT with explicit `exp` → T016 | ⬜ |
| | User/Admin roles | `role` enum + `require_role` → T031, T050 | ⬜ |
| | *DB ops: Create, Read* | covered | ⬜ |
| **User profile** | Create, view, edit, delete (name, headline, career goal, links) | T063–T065 + `/profile` screen T127 | ⬜ |
| | *DB ops: C, R, U, D* | §8.1 row 1 | ⬜ |
| **Skill management** | Add, update proficiency, remove, chosen from a taxonomy | T066–T068 + `/skills` T128 | ⬜ |
| | *DB ops: C, R, U, D* | §8.1 row 2 | ⬜ |
| **Project management** | Add, edit, delete with description and tech stack | T069, T070 + `/projects` T129 | ⬜ |
| | *DB ops: C, R, U, D* | §8.1 row 3 | ⬜ |
| **Education & certifications** | Add, edit, delete degrees and certifications | T071, T072 + T130 | ⬜ |
| | *DB ops: C, R, U, D* | §8.1 rows 4–5 | ⬜ |
| **Job management (Admin)** | Create, view, update, delete roles with required skills **and importance weights** | T073–T075 + `/admin/jobs` T133 | ⬜ |
| | *DB ops: C, R, U, D* | §8.1 row 6 | ⬜ |
| **AI resume analysis** | Upload CV (PDF/DOCX) | `POST /api/cv/upload` T107 + `/resume` T131 | ⬜ |
| | Extract text | `ml/text_loader.py` T092 | ⬜ |
| | Extract skills | `ml/extractor.py` T094 | ⬜ |
| | Show detected skills for confirmation | `resume_detected_skill` staging + `DetectedSkillsPanel` T107, T131 | ⬜ |
| | *DB ops: Create, Read* | §8.1 rows 10–11 | ⬜ |
| **AI job matching** | Ranked role list | `POST /api/recommendations` T108 + `/recommendations` T141 | ⬜ |
| | Compatibility % | `0.6·coverage + 0.4·cosine` T102 | ⬜ |
| | Matched skills | `matched_skill_ids` + `ScoreBreakdown` T142 | ⬜ |
| | *DB ops: Read* | §8.1 rows 13–14 | ⬜ |
| **Skill-gap analysis** | Pick a target role | `/skill-gap?role=` T144 | ⬜ |
| | Present and missing skills, ordered by importance | `ml/gap_analysis.py` T100, T144 | ⬜ |
| | *DB ops: Read* | §8.1 row 14 | ⬜ |

### 18.3 AI/ML design (§4.2)

| Requirement | Implementation | Status |
|---|---|---|
| Extract CV text, clean it, match against ≈150 AI/ML skills with aliases, using **spaCy phrase matching** | T042 (taxonomy), T092 (extraction), T094 (`PhraseMatcher`) | ⬜ |
| Users confirm or edit the result | Staging table + `POST /api/skills/confirm` + `DetectedSkillsPanel` — T107, T128, T131 | ⬜ |
| Represent a user by skills, projects, and education | `ml/text_profile.py` T096 | ⬜ |
| **Weighted skill-coverage** score, scikit-learn | `ml/matcher.weighted_skill_coverage` T097 | ⬜ |
| **TF-IDF cosine similarity** between profile text and each job description | `ml/matcher.tfidf_cosine` T097 | ⬜ |
| Initial weights ~60% / 40% | `Settings.SKILL_COVERAGE_WEIGHT = 0.6` T020 | ⬜ |
| Weights tuned on the labelled sample profiles | `evaluation/tuning.py` T154, sweep in `docs/evaluation_report.md` | ⬜ |
| Gap = required − user skills, ranked by importance weight | `ml/gap_analysis.py` T100 | ⬜ |
| LLM turns the gap into a learning path, **core works without it** | `ml/learning_path.py` T103 (P2); `503` when disabled | ⬜ |
| Unsupervised similarity + rule-based weighting, **not a trained classifier**, stated openly | No classifier anywhere; disclosure in `docs/report.md` T169 and `docs/evaluation_report.md` T157 | ⬜ |

### 18.4 Deliverables (§4.3)

| Deliverable | Implementation | Status |
|---|---|---|
| Working web application (frontend + API + PostgreSQL) **deployed online** | Phases 6, 7, 10 | ⬜ |
| Seed dataset: ~50–100 job listings **and** the skill taxonomy | `data/job_roles.json` T045, `data/skills_taxonomy.json` T042, seed scripts T046–T048 | ⬜ |
| ML module (skill extraction, matching, gap analysis) **with an evaluation summary** | `app/ml/*` + `docs/evaluation_report.md` T157 | ⬜ |
| Source repository, final report, user manual, presentation | T001, T169, T170, T171 | ⬜ |

### 18.5 Goals / objectives (§2)

| Objective | Implementation | Status |
|---|---|---|
| Secure, responsive web app with registration, login, role-based access | Phase 3 + T137 (responsive verification) | ⬜ |
| Full DB CRUD for profiles, skills, projects, education/certs, admin job listings | §8 matrix — all cells tested and UI-reachable | ⬜ |
| Extract skills from a CV using NLP and a curated taxonomy | T094 | ⬜ |
| Recommend and rank roles with a scikit-learn engine combining overlap and text similarity, **explaining each score with matched skills** | T097, T102, T142 | ⬜ |
| Skill-gap analysis for any target role, ordered by importance | T100, T144 | ⬜ |
| **Validate on 20+ hand-labelled profiles**, target: expected role in top 3 for most | 24 profiles, T151–T157; target top-3 ≥ 0.75 | ⬜ |
| Optional LLM learning path, core does not depend on it | T103 (P2) | ⬜ |

### 18.6 Data & process (§7.3, §5, §8)

| Requirement | Implementation | Status |
|---|---|---|
| Curated taxonomy of ~150 skills with aliases | T042 | ⬜ |
| 50–100 job listings with required skills and weights | T045 | ⬜ |
| Sample CVs and 20+ hand-labelled profiles; **only consented or anonymised samples** | T151 (synthetic, no real CVs), T158 (3 anonymised) | ⬜ |
| Agile, six two-week sprints, shared backlog | T002 project board; §16 | ⬜ |
| Database creation with PostgreSQL schema, migrations, seed data | T022, T023, T041, T046–T048 | ⬜ |

### 18.7 Non-functional requirements (§7.5)

| Requirement | Implementation | Status |
|---|---|---|
| Hashed passwords | bcrypt, T016 | ⬜ |
| Token-based sessions | JWT, T016 | ⬜ |
| Role-based access | `require_role` + `middleware.ts`, T050, T060 | ⬜ |
| Input validation | Pydantic on every request model; zod on the client | ⬜ |
| Responsive layout, desktop and mobile | T137 at 375 / 768 / 1280 px | ⬜ |
| Recommendations within a few seconds | T149 asserts < 2 s | ⬜ |
| Privacy of uploaded CVs — **allow deletion of files and profile** | `DELETE /api/cv/{id}` (file + row) and `DELETE /api/profile`, T107, T065 | ⬜ |
| HTTPS and hashed passwords | T165, T166 | ⬜ |

### 18.8 Competitor comparison claims (§3.4)

The proposal's table claims four differentiators. Each must be **demonstrably true in the shipped
product**, not just asserted in the report.

| Claim | Where it is demonstrated | Status |
|---|---|---|
| "Specialised for AI/ML roles" | The taxonomy is entirely AI/ML; there is no generic job category | ⬜ |
| "Recommends roles from a full profile" | §12 steps 3–10 build the profile first, then rank | ⬜ |
| "Skill-gap report for a target role" | `/skill-gap`, T144 | ⬜ |
| "Skill extraction from CV" | `/resume`, T131 | ⬜ |
| "Explains why a role matches — matched and missing skills" | `ScoreBreakdown` + `GapTable`, T142, T144 | ⬜ |
| "Free (open-source stack)" | Every dependency is OSS; hosting uses free tiers | ⬜ |

### 18.9 Out of scope (§4.4) — must **not** be built

| Excluded item | Verification |
|---|---|
| Applying to jobs, employer accounts, chat, payments, job-portal scraping | No routes, no tables, no UI |
| A RAG chatbot | No vector store, no retrieval endpoints |
| A trained deep-learning ranking model | No classifier; the report states so |

---

## 19. Definition of Done

The project is complete only when **all** of the following are true and evidenced. A partially met
item is not done; a met item without evidence is not done.

### 19.1 Architecture

- [ ] Frontend runs on Next.js App Router; `react-router-dom` and `vite` are absent from `package.json`
- [ ] Backend runs on FastAPI; no `import flask` anywhere under `backend/app/`
- [ ] PostgreSQL is the live database; `sqlite` appears in no connection string
- [ ] Alembic owns the schema; `Base.metadata.create_all` appears only in `tests/conftest.py`
- [ ] `app/ml/` imports neither SQLAlchemy nor FastAPI (asserted by `test_ml_isolation.py`)

### 19.2 Authentication and authorization

- [ ] Register, login, logout, and `me` all work
- [ ] Passwords are bcrypt-hashed; `password_hash` appears in no response schema
- [ ] Tokens carry an explicit expiry; an expired token returns `401`
- [ ] `role = "admin"` and `role = "user"` both enforced; a non-admin admin route returns `403`
- [ ] `middleware.ts` redirects unauthenticated users away from all eight protected routes
- [ ] No endpoint accepts a `user_id` from the client

### 19.3 CRUD, demonstrable through the UI

- [ ] Profile: create, read, update, delete
- [ ] Skills: add from the taxonomy, update proficiency, remove
- [ ] Projects: add, edit, delete
- [ ] Education records: add, edit, delete
- [ ] Certifications: add, edit, delete
- [ ] Job roles (admin): create, assign weighted required skills, edit, delete
- [ ] Every change survives a page refresh (it is in PostgreSQL, not component state)
- [ ] `test_ownership.py` proves cross-user access is impossible
- [ ] T135's matrix walk produced a screenshot per cell

### 19.4 CV and skill extraction

- [ ] PDF upload works
- [ ] DOCX upload works
- [ ] Text extraction produces non-empty text for both
- [ ] spaCy extraction detects the seeded sample CV's skills
- [ ] `sklearn` and `Scikit-learn` resolve to the same skill
- [ ] `Java` does not match inside `JavaScript`; `Go` does not match inside `MongoDB`
- [ ] Detected skills are **staged**, and reach `user_skill` only after user confirmation
- [ ] Confirmation is idempotent
- [ ] A scanned PDF returns `422` with a clear OCR-unsupported message

### 19.5 Recommendation engine

- [ ] Job roles carry weighted required skills in the database
- [ ] Weighted skill coverage is used and is in [0, 1]
- [ ] TF-IDF cosine similarity is used and is in [0, 1]
- [ ] The combination is `0.6·coverage + 0.4·cosine` (or the tuned values from §10.5, documented)
- [ ] Roles are ranked, and the ordering is a total order
- [ ] Every role reports a compatibility percentage
- [ ] The percentage is explainable: both components, both weights, and the formula are shown
- [ ] Every role carries matched **and** missing skills
- [ ] `matched ∪ missing` equals the role's required set and the two are disjoint
- [ ] Two runs over identical input produce byte-identical output
- [ ] `POST /api/recommendations` completes in under 2 seconds
- [ ] An empty profile produces a helpful `409`, not a list of zeroes

### 19.6 Skill-gap analysis

- [ ] A target role can be selected
- [ ] Matched and missing skills are shown
- [ ] Missing skills are ordered strictly by descending importance weight
- [ ] Tiers are applied at 0.8 and 0.5 and are visually distinct
- [ ] The optional learning path is either absent or clearly flag-gated, and its absence does not
      affect the gap report

### 19.7 Admin

- [ ] `/admin/jobs` lists roles with required-skill counts and weights
- [ ] A role can be created with a description and required skills
- [ ] Importance weights can be set per (role, skill) with a live tier badge
- [ ] Roles can be edited and deleted
- [ ] The panel validates; it is not a generic database browser
- [ ] Flask-Admin does not exist anywhere in the repository
- [ ] `/admin/*` is unreachable without an admin token

### 19.8 Evaluation

- [ ] 24 hand-labelled profiles exist with a written rationale each
- [ ] Top-1 accuracy, top-3 hit rate, and MRR are reported
- [ ] Top-3 hit rate ≥ 0.75
- [ ] The weight sweep table is committed with all five rows
- [ ] The chosen weights are justified
- [ ] Two harness runs produce identical metrics
- [ ] `test_evaluation.py` fails if the target is missed
- [ ] The report states plainly that **no trained classifier was used**, and why
- [ ] The report lists the threats to validity (§10.8)
- [ ] No number in the report is a placeholder

### 19.9 Quality

- [ ] `pytest` passes, ≥ 60 tests, 0 failures
- [ ] `ruff` and `mypy` clean on `backend/`
- [ ] `npm run build` and `npm run lint` clean on `frontend/`
- [ ] Responsive at 375 px, 768 px, and 1280 px
- [ ] Every screen has a loading, an empty, and an error state
- [ ] No accessibility regression: labelled inputs, focus rings, keyboard navigation

### 19.10 Data integrity

- [ ] No mock or fabricated data in any production flow
- [ ] `grep -rn "mockRecommendations\|mockStats\|mockQuizData\|12,847" frontend/` returns nothing
- [ ] No hardcoded recommendation string anywhere in the backend
- [ ] The legacy SQLite data was archived, not silently dropped, with the reason documented
- [ ] The knowledge base is curated seed data, version-controlled

### 19.11 Security

- [ ] S1–S12 from §17.4 are all closed
- [ ] No secret is committed; `.gitignore` covers `.env*`
- [ ] Production `JWT_SECRET_KEY` is a generated value ≥ 32 characters
- [ ] Production `ALLOWED_ORIGINS` contains only the deployed frontend origin
- [ ] CORS denies an unlisted origin
- [ ] Every file upload validates extension **and** content type and size
- [ ] Every user-owned read is scoped by `user_id` in the query

### 19.12 Deployment

- [ ] Frontend deployed to Vercel over HTTPS
- [ ] API deployed to Render/Railway over HTTPS
- [ ] `alembic upgrade head` run against the production database
- [ ] Seed data loaded into production
- [ ] The full §12 journey executed against the deployed URL by a second team member
- [ ] Local `docker compose up` still works as the offline demo fallback

### 19.13 Documentation and cleanup

- [ ] Every §18 row reads ✅ with evidence
- [ ] `docs/report.md` includes the §4.2 design-honesty disclosure
- [ ] `docs/limitations.md` matches the shipped system
- [ ] `docs/user_manual.md` and `docs/presentation_outline.md` committed
- [ ] Both READMEs are accurate
- [ ] Product name is "CareerLens AI" everywhere; zero "Pathfinder", zero "CareerGuide AI"
- [ ] Legacy Flask and Vite code deleted in one auditable commit
- [ ] The app still builds, tests, and runs after that deletion

---

## 20. Recommended Development Order

### 20.1 The single most important thing to get right

**The schema (Phase 2).** It blocks the ML layer, every CRUD router, the admin panel, and the
recommendation UI. More effort forks off it than off any other decision. Do not start writing
routers before §6 is implemented and the §6.5.4 verification queries return the expected empty sets.

### 20.2 The ten things that most often go wrong, in the order they bite

| # | Pitfall | Guard |
|---|---|---|
| 1 | Starting the Next.js migration before the API contracts are known, then rewriting the client twice | The 2-hour Sprint 1 spike, then Phase 6 **after** Phase 4 |
| 2 | Building the ML layer so it imports the ORM, which makes it untestable without a database | T091 `ml/types.py` first, plus `test_ml_isolation.py` |
| 3 | Adding a fourth scoring component "because it would help" | §9.1 fixes the design at coverage + cosine. Anything else is scope creep |
| 4 | Tuning the 0.6/0.4 weights to match the illustrative "91%" in proposal §2 | §9.5.5 shows the arithmetic and explains why those figures are labelled illustrative. Report measured numbers |
| 5 | Shipping mock data with a "real" UI on top of it | §19.10. The current codebase fails this; the mocks are deleted, not decorated |
| 6 | Writing extractor tests only for positive cases | `Java` in `JavaScript` and `Go` in `MongoDB` are the two that matter |
| 7 | Forgetting that `db.create_all()` cannot alter a table, and dropping the database to "fix" a schema | Alembic from Sprint 1. Never drop |
| 8 | Allowing unconfirmed CV extractions into `user_skill` | The staging table. It is a data invariant, not a UI convention |
| 9 | Deferring the security fixes to the end | S1 is **critical today**. S1–S6 are closed across Sprints 1 and 4 |
| 10 | Deleting the legacy code early | Frozen until T175. The auth logic and feedback validation are the reference for the new implementations |

### 20.3 Weekly operating rhythm

| Cadence | Activity | Purpose |
|---|---|---|
| Daily | Stand-up: yesterday, today, blockers | Proposal §5 |
| Twice weekly | Pair on the critical-path task (§15.4) | Proposal §10 limits a task to two members |
| Weekly | Run `pytest` and `npm run build`; check the §18 matrix for regressions | Catch drift early |
| End of sprint | Sprint review with the supervisor; update the GitHub board | Proposal §5's stated reason for choosing Scrum |
| End of Sprint 2 | **Scope freeze** (proposal §6.4). Everything after this is on the backlog, not the plan | The single most effective scope control in the proposal |
| Before any commit | `git status`, `git diff`, confirm no `.env`, no `*.db`, no `__pycache__` | Never commit a secret or the 32 KB database |

### 20.4 Where to cut if the schedule slips

In this order, because each is the first to go with the least compliance cost:

1. **T103 / T145 — the optional LLM path.** The proposal explicitly makes it optional. Not building
   it is compliant. (~30 h)
2. **T148 — the admin evaluation chart.** The report is a document; the chart is a nicety. (~12 h)
3. **T147 — recommendation run history.** `/recommendations/[id]` remains reachable from the
   results list. (~6 h)
4. **T132 — the feedback feature.** Not in proposal §4.1 at all. (~8 h)
5. **T130 — the certifications screen.** Certifications remain manageable via the API; only the
   screen is deferred. (~16 h) — *last resort; §4.1 requires the CRUD and the UI is what makes it
   demonstrable*

**Never cut:** the schema, auth with roles, the five CRUD entities, the ML engine, the evaluation
harness, the tests, or the deployment. Those are the proposal.

### 20.5 The one-paragraph version

> Freeze the Flask and Vite code, commit it, and start the Docker daemon. Build the FastAPI platform
> against PostgreSQL with Alembic. Design the schema properly — `skill`, `skill_alias`,
> `user_skill`, `job_role`, `job_role_skill` — because everything else depends on it, and drop
> `profile.skills` entirely. Seed 150 skills with aliases and 60 roles with weights. Add auth with
> enforced roles. Build CRUD for profile, skills, projects, education, certifications, and job
> roles, with ownership checks. Build the ML layer as pure functions over dataclasses: spaCy
> extraction, weighted coverage, TF-IDF cosine, gap analysis, ranking, deterministically. Wrap it in
> a service and expose it through three endpoints. Then move the frontend to Next.js, wire every
> screen to real data, delete every mock, and build the two screens that explain the answer. Evaluate
> on 24 hand-labelled profiles, publish the numbers including the ones you do not like, deploy, and
> only then delete the legacy code.

---

## 21. Final Implementation Checklist

Print this. Work down it. Tick nothing without evidence.

### Sprint 1 — Foundation

- [ ] `git init`, root `.gitignore`, first commit containing the legacy tree
- [ ] GitHub remote + Sprint 1–6 project board
- [ ] `docs/architecture.md` (decisions D1–D5) and `docs/erd.md` (draft)
- [ ] **Docker daemon started**
- [ ] `docker-compose.yml` with `postgres:16` + `pgadmin:4`; `docker compose up -d`; connectivity verified
- [ ] Python 3.12 venv via `uv`; `.python-version` committed
- [ ] `requirements.txt` (target set) + `requirements-dev.txt`; every import succeeds
- [ ] `spacy.load("en_core_web_sm")` succeeds
- [ ] `backend/.gitignore` (fixes S6)
- [ ] `backend/app/` package: `core/config.py` (fail-fast secret), `core/logging.py`, `core/exceptions.py`, `core/security.py`, `db/base.py`, `db/session.py`, `main.py`
- [ ] `GET /`, `GET /health` (`"database":"ok"`), `GET /docs`
- [ ] CORS allowlist from `ALLOWED_ORIGINS`; unlisted origin denied (S2)
- [ ] Alembic initialised; revision 1 creates `user`
- [ ] `alembic upgrade head && downgrade base && upgrade head` verified
- [ ] `tests/conftest.py` with transactional rollback; `test_health.py`, `test_config.py`, `test_cors.py` green
- [ ] `backend/pathfinder.db` and `backend/__pycache__/` deleted
- [ ] 2-hour Next.js spike: 49 shadcn components compile under App Router
- [ ] Proposal §6.4 tutorials logged

### Sprint 2 — Schema, knowledge base, auth

- [ ] 9 model modules; 14 tables total
- [ ] Revision 2 applied; all §6.5.4 verification queries return the expected empty sets
- [ ] `skill_alias.alias` is the primary key; `EXPLAIN` shows an index scan
- [ ] `job_role_skill.weight NUMERIC(3,2)` with `CHECK (weight > 0 AND weight <= 1)`
- [ ] `user_skill.proficiency` with `CHECK (proficiency BETWEEN 1 AND 5)`
- [ ] `ON DELETE CASCADE` on every child FK; `test_cascade.py` green
- [ ] **No `skills` / `education` / `experience` TEXT column on `profile`**
- [ ] `data/skills_taxonomy.json`: ≥ 150 skills, 8 categories, ≥ 2 aliases each
- [ ] `ml/taxonomy.py` + `test_taxonomy.py`: every alias resolves uniquely, no collisions
- [ ] `data/job_roles.json`: 50–100 roles, 8–18 weighted skills each
- [ ] Four idempotent seed scripts; running twice changes nothing
- [ ] `api/deps.py` with `get_current_user`, `require_user`, `require_role`
- [ ] register / login / logout / me / refresh working; roles enforced
- [ ] 409 on duplicate email; 422 on weak password; 401 with an identical message on bad credentials
- [ ] Email lowercased and trimmed (S9)
- [ ] `test_auth.py`, `test_roles.py`, `test_cascade.py`, `test_taxonomy.py` green
- [ ] `ml/types.py` created with no ORM imports
- [ ] `session.ts` + `AuthProvider` + `middleware.ts` guards
- [ ] Header nav links all resolve (fixes C1's four dead links); admin group wired to `isAdmin`
- [ ] Registration sends `educationLevel` (fixes the `Register.tsx:92` drop)
- [ ] `docs/erd.md` matches the implemented schema

### Sprint 3 — CRUD APIs

- [ ] Profile, skills (+ taxonomy search + confirm), projects, education, certifications routers and services
- [ ] Public job read; admin job write behind `require_role("admin")`
- [ ] `PUT /api/admin/jobs/{id}/skills` atomic
- [ ] Dashboard summary and completeness endpoints (real, not mocked)
- [ ] `test_profile_crud.py`, `test_skills_crud.py`, `test_projects_crud.py`, `test_education_crud.py`, `test_jobs_crud.py`, `test_ownership.py` green
- [ ] All 20 Next.js routes rendering
- [ ] Typed API client with `.status` / `.body` error enrichment
- [ ] zod schemas mirroring the Pydantic models
- [ ] Shared Loading / EmptyState / ErrorState / ConfirmDialog / PageHeader
- [ ] React Query hooks for every domain, with correct invalidation
- [ ] Vite surface deleted; `npm run build` and `npm run lint` clean
- [ ] `src/components/ui/` still 49 files, zero diffs

### Sprint 4 — AI/ML engine

- [ ] `ml/text_loader.py`: PDF + DOCX; oversize rejected; `ScannedDocumentError` for textless PDFs
- [ ] `ml/extractor.py`: spaCy `PhraseMatcher` over canonical names + aliases
- [ ] `Java` does not match inside `JavaScript`; `Go` does not match inside `MongoDB`
- [ ] `ml/text_profile.py`; `ml/matcher.py` (coverage + cosine); `ml/gap_analysis.py`; `ml/ranker.py`
- [ ] Coverage and cosine in [0, 1] over 200 randomised inputs
- [ ] `(-score, job_role_id)` total-order tiebreak; two runs byte-identical
- [ ] `recommendation_service.py` is the only module touching both SQLAlchemy and `ml/`
- [ ] `POST /api/recommendations`, `GET /api/skill-gap/{id}`, `POST /api/cv/upload`, `GET /api/cv/{id}` live
- [ ] `test_ml_isolation.py` green — `app/ml/` imports no ORM/framework
- [ ] `test_explainability.py` green — matched ∪ missing equals the required set, disjoint
- [ ] Upload validates extension **and** content type **and** size (S3)
- [ ] `GET /api/cv/{id}` is auth-required and ownership-scoped (S5)
- [ ] Every write requires a token (S4)
- [ ] All 12 screens wired to real endpoints; all mocks deleted
- [ ] CRUD matrix walked with a screenshot per cell
- [ ] Responsive at 375 / 768 / 1280 px
- [ ] `POST /api/recommendations` < 2 s
- [ ] `grep -rn "mock\|12,847\|94%" frontend/app frontend/src` empty
- [ ] *(P2, optional)* `ml/learning_path.py`

### Sprint 5 — Recommendation UX and evaluation

- [ ] `/recommendations` with a Generate action (a mutation, not on mount)
- [ ] `ScoreBreakdown` showing both components, both weights, and the formula
- [ ] `/recommendations/[id]` rendering a **persisted** run
- [ ] `/skill-gap` with descending-weight ordering and tier badges
- [ ] Empty states for zero skills and zero missing skills
- [ ] 24 labelled profiles with rationale written **before** running the engine
- [ ] `metrics.py`, `harness.py`, `tuning.py`, `__main__.py`
- [ ] Weight sweep across 0.5/0.5 … 0.9/0.1
- [ ] `docs/evaluation_report.md` committed with measured numbers only
- [ ] §4.2 design-honesty disclosure present
- [ ] §10.8 threats to validity present
- [ ] `test_evaluation.py` green and failing if top-3 < 0.75
- [ ] Two harness runs identical
- [ ] Full suite green, ≥ 60 tests
- [ ] Admin overview and the evaluation chart

### Sprint 6 — Deployment, docs, cleanup

- [ ] `backend/Dockerfile` on python:3.12-slim, uvicorn, non-root, spaCy model at build time
- [ ] `docker-compose.yml` has an `api` service
- [ ] `render.yaml` with `healthCheckPath: /health`
- [ ] `vercel.json` + `frontend/.env.example`
- [ ] Production database; `alembic upgrade head` run against it
- [ ] Every production env var set; no secret in the repository
- [ ] `docs/deployment.md` with the env table, deploy order, and rollback
- [ ] Full §12 journey on the deployed URL by a second person, desktop + phone
- [ ] Local `docker compose up` still works as the offline demo fallback
- [ ] `docs/report.md` with the design-honesty clause
- [ ] `docs/user_manual.md`, `docs/presentation_outline.md`, `docs/limitations.md`
- [ ] §18 matrix fully ticked with evidence
- [ ] Branding sweep: zero "Pathfinder", zero "CareerGuide AI"; `package.json` name fixed
- [ ] Both READMEs accurate
- [ ] Legacy SQLite DB archived to `docs/archive/` with the reason documented
- [ ] Legacy Flask and Vite code deleted in one auditable commit
- [ ] After deletion: build passes, tests pass, app runs

### Final gate

- [ ] Every §19 Definition-of-Done item ticked with evidence
- [ ] Scope freeze confirmed at the end of Sprint 2
- [ ] Supervisor has reviewed a working deployed system
- [ ] Report, manual, and presentation submitted

---

*Implementation plan produced 29 September 2026 against the verified repository state of the same
date. Every `file:line` reference was confirmed by direct inspection. Every task, table, endpoint,
entity, screen, risk, and acceptance criterion in this document is intended to be executed
step-by-step without re-deriving the architecture. Where the plan differs from
`PROJECT_CODEBASE_ALIGNMENT_ANALYSIS.md`, §0.1 records the correction and the reason.*

