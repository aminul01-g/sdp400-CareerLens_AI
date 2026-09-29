# Analysis Plan — Project Proposal vs Existing Codebase

**Date:** 29 September 2026
**Target artifact:** `PROJECT_CODEBASE_ALIGNMENT_ANALYSIS.md`
**Working directory:** `/home/aminul/Development/sdp400`
**Mode:** Read-only analysis. No file under `backend/` or `frontend/` may be created, modified, or deleted.

---

## 1. Objective

Answer one question with evidence:

> How far is the current frontend + backend codebase from the proposed project, exactly what
> prevents it from satisfying the proposal, and what specific changes are required to transform
> the existing codebase into the proposed system?

The output must function as an implementation blueprint for another developer, so every claim
must be traceable to a `file:line` citation. Filenames must match the repository's actual naming
conventions, not invented ones.

---

## 2. Source of truth

The project proposal is authoritative. It was transcribed from `sheet0.jpg` / `sheet1.jpg` into
`CareerLens_AI_Project_Proposal.docx` and defines:

- **Project name:** CareerLens AI — An AI-Powered Job & Career Recommendation System
- **Course:** SDP400 — Software Development Project, submitted 29 September 2026
- **Supervisor:** Md. Masudul Islam, Assistant Professor, Dept. of CSE, BUBT
- **12 sections**, including a 9-module CRUD table, a 7-row competitor comparison, a 9-row risk
  matrix, a 28-row man-hour schedule, and a 13-item budget
- **Committed stack (§7.2):** Next.js/React + Tailwind, Python 3 + FastAPI + SQLAlchemy + Pydantic
  + JWT, PostgreSQL, scikit-learn + pandas + NumPy + spaCy + pdfplumber/PyPDF + python-docx,
  pytest, Vercel (frontend), Render/Railway (backend + database)
- **AI/ML design (§4.2):** spaCy phrase matching against a ~150-skill taxonomy for CV skill
  extraction; job matching = weighted skill-coverage + TF-IDF cosine similarity (scikit-learn),
  initial weights ~60%/40%; skill-gap = required-role skills minus user skills, ranked by
  importance weight; optional LLM layer must not be load-bearing
- **Explicit design honesty (§4.2):** no large labelled dataset exists, so the engine uses
  unsupervised similarity + rule-based weighting, NOT a trained classifier — stated openly in the
  report

---

## 3. Locked decisions

Confirmed with the user before execution:

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Framework mismatch (Flask/Vite/SQLite vs FastAPI/Next.js/PostgreSQL) | **Proposal is binding.** Report recommends replacement. |
| 2 | Rewrite framing | **State it plainly**, including an explicit "implications for the submitted proposal" subsection. |
| 3 | Audience | **Both** — developer blueprint as the core, plus executive summary and proposal-clause traceability up front for grading. |
| 4 | Security findings | **Dedicated section**, P0-rated fixes, beyond strict alignment scope. |
| 5 | Naming inconsistency | **Include as a finding** in a dedicated subsection. |

---

## 4. Evidence already gathered

Investigated read-only; findings below are verified, not assumed.

### 4.1 Repository shape

```
sdp400/
├── sheet0.jpg, sheet1.jpg                    (source scans)
├── CareerLens_AI_Project_Proposal.docx       (transcribed proposal, source of truth)
├── backend/   (Flask, ~468 lines app code)
│   ├── app.py, models.py, auth.py, guidance.py, admin.py, tasks.py, extensions.py, utils.py
│   ├── scripts/  (seed_db, e2e_test, inspect_db, create_feedback_table, post_feedback_test, show_feedbacks)
│   ├── Dockerfile, requirements.txt, README.md, .env, .env.example
│   ├── pathfinder.db (0 bytes — stray)  ·  instance/pathfinder.db (32 KB — live)
│   └── venv/  (162 MB, committed-adjacent)
└── frontend/  (Vite + React 18 + TS + Tailwind + shadcn/ui)
    ├── src/pages/  (11 pages)  ·  src/components/ui/  (46 shadcn components)
    ├── src/api/client.ts, src/App.tsx, src/components/layout/{Header,Footer}.tsx
    └── package.json, vite.config.ts, .env, .env.development
```

### 4.2 Backend — complete route inventory

Only 10 routes exist across the entire backend (`auth.py`, `guidance.py`):

| Route | File:line | Methods |
|---|---|---|
| `/api/auth/register` | `auth.py:8` | POST |
| `/api/auth/login` | `auth.py:34` | POST |
| `/api/auth/me` | `auth.py:45` | GET |
| `/api/upload_resume` | `guidance.py:9` | POST |
| `/api/uploads/<int:upload_id>` | `guidance.py:31` | GET |
| `/api/ai/recommend` | `guidance.py:39` | POST |
| `/api/analytics/event` | `guidance.py:73` and `:74` (duplicate decorator) | POST |
| `/api/feedback` | `guidance.py:93` | POST |
| `/api/feedbacks` | `guidance.py:151` | GET (admin-gated in body) |

**grep for PUT/PATCH/DELETE across all backend `.py` → zero results.**

### 4.3 Backend — data model (`models.py`)

6 models: `User`, `Profile`, `Upload`, `GuidanceSession`, `Event`, `Feedback`.

- `Profile.skills` is `db.Column(db.Text)` holding comma-separated values (`models.py:26`) —
  a comment on the line says `# comma separated`
- No `Job`, `Role`, `Skill`, `Project`, `Education`, `Certification`, or taxonomy table exists
- `User.role` is `db.String(50)`, default `'user'` (`models.py:10`); live DB shows 1 admin, 10 users
- No `ON DELETE` cascade; FKs declared but SQLite does not enforce them by default
- No indexes beyond the implicit PK and the `UNIQUE(email)`

### 4.4 Backend — AI/ML status

- **No `sklearn`, `scikit-learn`, `spacy`, `pandas`, or `numpy` import exists in any `.py` file.**
- `requirements.txt` lists only Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Admin,
  APScheduler, requests, python-dotenv, gunicorn, flask-cors. No ML or PDF/DOCX libraries.
- `guidance.py:48` returns a hardcoded string:
  `{'recommendation': 'mock suggestion: build projects, learn data structures, apply to internships'}`
- `guidance.py:52-54` — self-described placeholder:
  `# This is a placeholder. The real api call depends on the model/provider.`
- Live DB confirms all 6 `guidance_session` rows stored that same mock string.
- `utils.allowed_file()` (allowlist for pdf/doc/docx/txt) is **never imported anywhere** → dead code,
  no file-type validation on upload.

### 4.5 Frontend — API wiring

Only **3 of 10 routed pages** call the API:

| Page | API call | Notes |
|---|---|---|
| `Login.tsx:51` | `api.login` | Stores JWT + user in `localStorage`, navigates to `/dashboard` |
| `Register.tsx:92` | `api.register` | Sends only `{name, email, password}` |
| `Feedback.tsx:70` | `api.submitFeedback` | Reads token from `localStorage` |
| `Dashboard.tsx:37` | **none** | `mockRecommendations` + `mockStats` (totalUsers "12,847", successRate "94%") |
| `Recommendations.tsx:24` | **none** | `mockRecommendations` array; no upload UI, no AI call |
| `Quiz.tsx:27` | **none** | `mockQuizData` sections; `handleSubmit` at `:182` just `navigate("/recommendations")` at `:194` |
| `About/Features/Landing/Index/NotFound` | **none** | Static marketing / routing |

Dead exports in `client.ts` with no importer: `uploadResume` (`:172`), `aiRecommend` (`:181`),
`analyticsEvent` (`:185`).

Other verified frontend facts:
- No route guard. `App.tsx:26-45` `PublicLayout`/`AuthenticatedLayout` are identical wrappers;
  `/dashboard`, `/quiz`, `/recommendations`, `/feedback` render for anonymous visitors.
- `Header.tsx` has no nav links to `/dashboard`, `/quiz`, or `/recommendations` — only `/login`
  and `/register` (`:121`, `:124`, `:201`, `:210`).
- `Register.tsx` collects `educationLevel` (`:21`, `:128`) and requires it (`:71-72`) but
  **never sends it** — dropped at the `api.register(name, email, password)` call on `:92`.
- `Recommendations.tsx:169` `savedCareers` is component-local `useState`, not persisted.
- `vite.config.ts` — port 8080, `@` alias, no dev proxy to the backend.
- `.env` → `VITE_API_BASE_URL=http://127.0.0.1:5001`; `.env.development` → `http://localhost:5000`.
  The two disagree; backend default port is 5000 (`app.py:60`).

### 4.6 Database — live state (`instance/pathfinder.db`)

```
user (11 rows) · profile (11) · upload (0) · guidance_session (6) · event (6) · feedback (2)
```
Sample profiles: `(1, 1, 'Sample headline', 'python,sql,ml', None)`; users 3–11 all empty.
`backend/pathfinder.db` at repo root is **0 bytes** — a stray/duplicate of the real DB.

### 4.7 Security and data hygiene

| Finding | Evidence |
|---|---|
| **Flask-Admin mounted with no access control** | `extensions.py:8` `Admin(name='Pathfinder Admin')`, `admin.init_app(app)` at `app.py:27`, views at `admin.py:49-54`. No `is_accessible` override anywhere → `/admin/` exposes all user emails + `password_hash` columns to anonymous visitors. |
| Fully open CORS | `app.py:18` `CORS(app)` — no `origins` allowlist |
| Optional JWT on upload and recommend | `guidance.py:10` and `guidance.py:40` use `@jwt_required(optional=True)` → `user_id` can be `None`, uploads are unattributable |
| No upload file-type validation | `allowed_file()` exists in `utils.py:2` but is never imported |
| IDOR on upload download | `guidance.py:31` `/api/uploads/<int:upload_id>` — sequential int ID, no ownership check, no auth |
| Weak secret fallback | `app.py:19-22` falls back to `'dev-secret'` / `'jwt-secret'` when env vars are absent |
| No `backend/.gitignore` | `.env`, `pathfinder.db`, and a 162 MB `venv/` all sit in the tree; only `frontend/.gitignore` exists |
| `.env` contains real-ish values | Values are placeholders today (`replace-with-a-secret`), but the file is untracked-safe only by accident — nothing enforces it |

### 4.8 Testing, tooling, deploy

- No Python test suite. `backend/scripts/e2e_test.py` is an ad-hoc script hitting
  `http://127.0.0.1:5001`. `pytest` is **not** in `requirements.txt`, contradicting proposal §7.2.
- `frontend/package.json` has `lint` and `build`; no `test` or `typecheck` script.
- No Alembic/migrations. `app.py:46` calls `db.create_all()` — schema change means drop + recreate,
  which destroys the 11 seeded users.
- `backend/Dockerfile` → gunicorn on port **8000**. No `Procfile`, `render.yaml`, or `vercel.json`,
  though `backend/README.md:11` claims a Procfile for Render. Frontend has no deploy config either.

### 4.9 Naming inconsistency

- `Pathfinder` — `app.py:53` return string, `extensions.py:8` admin title, `backend/README.md`
- `CareerGuide` — 8 occurrences in frontend copy (e.g. `Feedback.tsx:74`)
- `CareerLens AI` — 0 occurrences in any source file; exists only in the proposal

---

## 5. Report structure (15 sections)

| # | Section | Content |
|---|---------|---------|
| 1 | Executive Summary | Verdict up front + proposal-clause traceability table (for grading) |
| 2 | Proposed Project Requirements | Condensed spec from the docx, incl. stack commitments and §4.2 AI design |
| 3 | Existing System Overview | Verified fact base with citations |
| 4 | Current Architecture Analysis | Flow trace + the two stray branches (Flask-Admin, APScheduler) |
| 5 | Frontend Analysis | Pages, routing, API wiring, forms, mocks, gaps |
| 6 | Backend Analysis | Routes, auth, validation, error handling, gaps |
| 7 | Database Analysis | Tables, keys, relationships, missing entities, indexes |
| 8 | AI/ML Analysis | What exists, why it fails §4.2, and the realistic module layout |
| 9 | CRUD Analysis | Per-entity C/R/U/D matrix from route evidence only |
| 10 | Feature-by-Feature Alignment Matrix | Every proposal requirement → status + citation |
| 11 | Gap Analysis | 8-part structured gaps (requires / exists / missing / why / change / files / layer / approach) |
| 12 | Architecture Differences | Current vs proposed flow, divergence points marked |
| 13 | File-Level Modification Plan | Real paths, **NEW FILE REQUIRED** markers, priorities |
| 14 | Reusable Components | 4-way split: reuse / minor / major / new |
| 15 | Implementation Priority | P0–P3 roadmap with layer, files, dependency, reason, complexity |
| 16 | Dependency & Impact Analysis | What blocks what |
| 17 | Recommended Roadmap | Sequenced sprints |
| 18 | Security & Data Hygiene | Dedicated section, P0-rated |
| 19 | Naming & Branding Consistency | Dedicated subsection |
| 20 | Final Technical Assessment | The 4-way verdict, minimum viable change set |

---

## 6. Analysis constraints

- **Inspect before concluding.** Never infer capability from a filename or comment.
- **Every status must cite evidence.** No unsupported ✅/❌.
- **Do not invent filenames.** Follow the repo's flat-module convention (`backend/models.py`,
  `backend/<domain>.py` blueprints, `frontend/src/pages/<Name>.tsx`).
- **Separate fact from recommendation.** Mark recommendations explicitly.
- **Preserve working functionality.** The shadcn/ui kit, design system, and auth UX are assets.
- **No unnecessary AI complexity.** Recommend what is realistic for a 12-week, 4-member SDP400
  project while remaining genuine ML engineering.
- **Analysis only.** No code changes to the application.

---

## 7. Execution checklist

- [x] Confirm `@frontend` / `@backend` exist
- [x] Inventory full repo tree, excluding vendored deps
- [x] Read all 8 backend source modules in full
- [x] Enumerate every route and HTTP method
- [x] grep for PUT/PATCH/DELETE, ML libraries, skill-gap/compatibility logic
- [x] Inspect live SQLite schema and seed data
- [x] Read all 10 frontend pages + `App.tsx` + `client.ts` + `Header.tsx`
- [x] Map which pages actually call the API; identify dead exports and mocks
- [x] Audit auth, authorization, CORS, upload validation, secret handling
- [x] Check tests, migrations, deploy config, gitignore
- [x] Verify naming inconsistency across all source
- [ ] Write `PROJECT_CODEBASE_ALIGNMENT_ANALYSIS.md` (20 sections)
- [ ] Validate every `file:line` citation resolves
- [ ] Confirm no claim exceeds the evidence
