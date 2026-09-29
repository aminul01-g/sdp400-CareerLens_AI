# Project Codebase Alignment Analysis

**Project:** CareerLens AI — An AI-Powered Job & Career Recommendation System
**Course:** SDP400 — Software Development Project, BUBT
**Analysis date:** 29 September 2026
**Source of truth:** `CareerLens_AI_Project_Proposal.docx` (transcribed from `sheet0.jpg`, `sheet1.jpg`)
**Codebase examined:** `backend/` (Flask), `frontend/` (Vite + React 18 + TypeScript)
**Prepared for:** Development team + course supervisor (Md. Masudul Islam)

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented — verified in code |
| 🟡 | Partially implemented — some capability exists, incomplete |
| ❌ | Not implemented — no supporting code exists |
| 🔴 | Implemented incorrectly / inconsistent with the proposal |
| ⚠️ | Unclear or requires clarification |

---

## 1. Executive Summary

### 1.1 The central finding

The repository does **not** contain a partial build of the proposed project. It contains a
**different product built on a different technology stack**.

The code identifies itself as **"Pathfinder"** (backend, 2 occurrences) and **"CareerGuide AI"**
(frontend, 8 occurrences). The proposal defines **"CareerLens AI"**, which appears in **zero**
source files. More consequentially than the naming, the two stacks do not overlap:

| Layer | Proposal (submitted) | Codebase (actual) | Overlap |
|---|---|---|---|
| Backend framework | FastAPI (Python 3, Pydantic, SQLAlchemy) | Flask + Flask-SQLAlchemy | None |
| Database | PostgreSQL (+ pgAdmin) | SQLite, two files | None |
| Frontend | Next.js (React) | Vite SPA + React Router | None |
| ML stack | scikit-learn, pandas, NumPy, spaCy, pdfplumber, python-docx | **not installed at all** | None |
| Testing | pytest | not installed | None |

Of approximately **468 lines** of backend application code, there are **10 routes**, **6 models**,
and **zero** update or delete operations.

### 1.2 What exists and is genuinely reusable

This is not an empty repository, and three assets are real:

1. **A complete shadcn/ui component library** — 46 components in `frontend/src/components/ui/`,
   fully configured (`components.json`, Tailwind, `cn()` in `src/lib/utils.ts`). This is the
   largest reusable asset and satisfies the proposal's "Tailwind CSS (or similar)" (§7.2).
2. **A working authentication flow** — register/login/`me` against real endpoints with hashed
   passwords (`werkzeug.security`), JWT issuance, and a consistent client (`src/api/client.ts`).
   The *logic* is portable; only the framework changes.
3. **A coherent visual identity and responsive layout shell** — `Header.tsx`, `Footer.tsx`, the
   landing/marketing pages, and consistent Tailwind theming.

### 1.3 What is absent

Every substantive proposal requirement is missing. Most importantly:

- **No CRUD beyond Create/Read.** A grep for `PUT`, `PATCH`, and `DELETE` across every backend
  `.py` file returns **zero matches**. The proposal's §4.1 table requires full CRUD on 9 entities.
- **No knowledge base.** There is no `Job`, `Role`, `Skill`, `Project`, `Education`, or
  `Certification` model. The recommendation engine the proposal is built around has no data to
  operate on.
- **No machine learning.** No `sklearn`, `spacy`, `pandas`, or `numpy` import exists anywhere.
  `/api/ai/recommend` returns a hardcoded English string.
- **No genuine UI.** 7 of 10 routed pages never call the API. `Dashboard.tsx`, `Recommendations.tsx`,
  and `Quiz.tsx` render hardcoded arrays.

### 1.4 Verdict

**Evolve selectively; replace the platform layer.** Keep the UI kit, design system, and auth UX.
Replace Flask → FastAPI, SQLite → PostgreSQL, Vite → Next.js. Build the Job/Skill domain and the
ML engine essentially from scratch.

The proposal's committed stack is the single largest driver of rework, and that should be raised
with the supervisor early. See §20.

### 1.5 Proposal-clause traceability (for grading)

Each row traces a proposal requirement to its implementation status and evidence.

| Proposal § | Requirement | Status | Evidence |
|-----------|-------------|--------|----------|
| 1 | Needs/problems addressed by role recommendations | ❌ | No role or recommendation model exists |
| 2 | Ranked roles with compatibility % | ❌ | `Recommendations.tsx:24` hardcoded array |
| 2 | Skill-gap report | ❌ | Zero code occurrences outside `Features.tsx:54` marketing copy |
| 2 | CV skill extraction via NLP | ❌ | No `spacy`/`pdfplumber` import; `allowed_file()` never imported |
| 2 | Validate on 20+ labelled profiles | ❌ | No evaluation code; `pytest` not installed |
| 3 | Competitor analysis | 🟡 | Analysis exists as prose only; no comparison logic |
| 4.1 | Auth module (register/login/logout/JWT/User-Admin) | 🟡 | `auth.py` has register/login/me; **no logout**; roles not enforced except on one route |
| 4.1 | User profile CRUD | ❌ | No profile endpoint of any kind |
| 4.1 | Skill management CRUD | ❌ | No skill entity |
| 4.1 | Project management CRUD | ❌ | No project entity |
| 4.1 | Education & certifications CRUD | ❌ | No such entity |
| 4.1 | Admin job management CRUD | ❌ | No job entity; Flask-Admin is a generic DB browser |
| 4.1 | AI resume analysis | 🟡 | Upload works; **no text extraction, no skill extraction** |
| 4.1 | AI job matching | ❌ | Returns a hardcoded string (`guidance.py:48`) |
| 4.1 | Skill-gap analysis | ❌ | Not implemented |
| 4.2 | Weighted skill-coverage + TF-IDF cosine | ❌ | No `sklearn` import anywhere |
| 4.2 | ~150-skill taxonomy with aliases | ❌ | `profile.skills` is a comma-separated `TEXT` (`models.py:26`) |
| 4.3 | Deployed app (frontend + API + PostgreSQL) | 🔴 | SQLite (`app.py:20`); no deploy config for frontend |
| 5 | Agile, 6 × 2-week sprints | 🔴 | No project board, backlog, or sprint tooling present |
| 6.1 | React/Next.js, FastAPI, PostgreSQL, sklearn, spaCy | 🔴 | Flask, SQLite; ML libs absent |
| 6.3 | Users need no training; admins maintain from one panel | ❌ | No admin panel in the product sense |
| 6.4 | Risk mitigations (curated data, user confirmation) | ❌ | No seeded data; no confirmation UI |
| 7.1 | 4 laptops, no GPU | ✅ | Compatible with the actual stack |
| 7.2 | FastAPI + SQLAlchemy + Pydantic | 🔴 | Flask; Pydantic absent |
| 7.2 | PostgreSQL + pgAdmin | 🔴 | SQLite |
| 7.2 | scikit-learn, spaCy, pdfplumber, python-docx | ❌ | None installed |
| 7.2 | pytest | ❌ | Not in `requirements.txt` |
| 7.2 | Vercel / Render deployment | ❌ | No `Procfile`, `render.yaml`, or `vercel.json` |
| 8 | 516 man-hours across 5 stages | N/A | Planning artifact; no code implication |
| 9 | BDT 15,400 budget | ✅ | Free/open-source stack assumption holds |
| 10 | 4 members, max 2 per task | N/A | Process artifact |
| 11 | Limitations acknowledged honestly | ⚠ | Accurate for Pathfinder; must be rewritten for CareerLens |
| 12 | 13 references | ⚠ | Citations are real; they document competitors, not this system |

---

## 2. Proposed Project Requirements (Condensed)

Extracted from the submitted proposal for use as the comparison baseline.

### 2.1 Core promise

Users create a profile (skills, projects, education, certifications) or upload a CV, and receive:

1. A **ranked list of suitable AI/ML job roles** with a **compatibility percentage**
2. A **skill-gap report** listing what to learn for a chosen target role, ordered by importance

Administrators manage the job listings that form the knowledge base.

### 2.2 In-scope module table (§4.1, verbatim)

| Module | Features | DB operations |
|---|---|---|
| Authentication | Register, login, logout, password hashing, JWT sessions, User/Admin roles | Create, Read |
| User profile | Create, view, edit, delete profile (name, headline, career goal, links) | Create, Read, Update, Delete |
| Skill management | Add, update (proficiency level), remove skills chosen from a taxonomy | Create, Read, Update, Delete |
| Project management | Add, edit, delete projects with description and tech stack | Create, Read, Update, Delete |
| Education and certifications | Add, edit, delete degrees and certifications | Create, Read, Update, Delete |
| Job management (Admin) | Create, view, update, delete job roles with required skills and importance weights | Create, Read, Update, Delete |
| AI resume analysis | Upload CV (PDF/DOCX), extract text, extract skills, show detected skills for user confirmation | Create, Read |
| AI job matching | Ranked role list with compatibility % and matched skills | Read |
| Skill-gap analysis | Pick a target role, see present and missing skills ordered by importance | Read |

### 2.3 AI/ML design (§4.2, verbatim intent)

- **Skill extraction** — extract CV text, clean it, match against a curated taxonomy of ~150
  AI/ML skills **with aliases** (e.g. "sklearn" → Scikit-learn) using **spaCy phrase matching**.
  Users confirm or edit the result.
- **Job matching** — score = **weighted skill-coverage** + **TF-IDF cosine similarity** between
  profile text and each job description, both via scikit-learn. Initial weights ~60% / 40%, tuned
  on labelled sample profiles.
- **Skill-gap analysis** — required skills of target role **minus** user skills, ranked by the
  role's importance weight.
- **Optional LLM** — turns the gap list into a short learning path. Core features must work without it.
- **Stated design honesty** — no large labelled dataset exists, so the engine uses unsupervised
  similarity and rule-based weighting **rather than a trained classifier**, and this is disclosed
  openly in the report.

### 2.4 Committed stack (§7.2)

| Layer | Commitment |
|---|---|
| Frontend | React / Next.js, Tailwind CSS, JavaScript/TypeScript |
| Backend | Python 3, **FastAPI**, SQLAlchemy, Pydantic, JWT authentication |
| Database | **PostgreSQL** (with pgAdmin) |
| AI/ML/NLP | **scikit-learn, pandas, NumPy, spaCy**, pdfplumber/PyPDF, python-docx; optional LLM API |
| Dev tools | VS Code, Git/GitHub, Postman, Docker, Figma/draw.io, Jupyter Notebook |
| Test/deploy | **pytest**, browser testing, **Vercel** (frontend), **Render/Railway** (backend + DB) |

### 2.5 Non-functional requirements (§7.5)

- **Security** — hashed passwords, token-based sessions, role-based access, input validation
- **Usability** — responsive layout on desktop and mobile
- **Performance** — recommendations returned within a few seconds (target)

---

## 3. Existing System Overview

### 3.1 What the codebase actually is

A generic career-quiz web application. A user registers, logs in, answers a hardcoded quiz, and
views a hardcoded list of three careers (Software Developer, Data Scientist, UX/UI Designer) with
confidence scores. A feedback form persists to the database. An analytics event endpoint records
events. An APScheduler job prints an event count every 24 hours.

### 3.2 Backend — verified inventory

**8 modules, ~468 lines:**

| File | Lines | Responsibility |
|---|---|---|
| `backend/app.py` | 60 | App factory, config, blueprint registration, `db.create_all()` |
| `backend/guidance.py` | 187 | Upload, download, `/ai/recommend`, analytics, feedback (5 routes) |
| `backend/models.py` | 85 | 6 SQLAlchemy models |
| `backend/admin.py` | 54 | Flask-Admin model views |
| `backend/auth.py` | 52 | Register, login, me (3 routes) |
| `backend/tasks.py` | 17 | APScheduler daily summary |
| `backend/extensions.py` | 9 | `db`, `jwt`, `admin`, `scheduler` singletons |
| `backend/utils.py` | 4 | `allowed_file()` — **dead code, never imported** |

**Complete route inventory (10 routes):**

| Method | Path | File:line | Auth |
|---|---|---|---|
| POST | `/api/auth/register` | `auth.py:8` | none |
| POST | `/api/auth/login` | `auth.py:34` | none |
| GET | `/api/auth/me` | `auth.py:45` | `@jwt_required()` |
| POST | `/api/upload_resume` | `guidance.py:9` | `@jwt_required(optional=True)` |
| GET | `/api/uploads/<int:upload_id>` | `guidance.py:31` | **none** |
| POST | `/api/ai/recommend` | `guidance.py:39` | `@jwt_required(optional=True)` |
| POST | `/api/analytics/event` | `guidance.py:73`, `:74` | `@jwt_required(optional=True)` |
| POST | `/api/feedback` | `guidance.py:93` | `@jwt_required(optional=True)` |
| GET | `/api/feedbacks` | `guidance.py:151` | `@jwt_required()` + inline role check |

Also: `GET /` returns a status object (`app.py:51`), and Flask-Admin is mounted at `/admin/`.

**Verified absences:** grep for `PUT|PATCH|DELETE` across all `.py` → **zero**. grep for
`sklearn|scikit|spacy|pandas|numpy|tfidf|cosine` → **zero**.

**Dependencies** (`backend/requirements.txt`): Flask, Flask-SQLAlchemy, Flask-JWT-Extended,
Flask-Admin, APScheduler, requests, python-dotenv, gunicorn, flask-cors. No ML, no PDF/DOCX,
no pytest, no Pydantic.

### 3.3 Frontend — verified inventory

**11 pages, ~3,038 lines**, React 18 + TypeScript + Vite + Tailwind + shadcn/ui.
`tsconfig.app.json:18-20` sets `strict: false`, `noUnusedLocals: false`,
`noUnusedParameters: false`. `npx tsc --noEmit` passes clean.

| Page | Lines | Calls API? | Notes |
|---|---|---|---|
| `Recommendations.tsx` | 536 | ❌ | `mockRecommendations` at `:24`; no upload UI, no AI call |
| `Register.tsx` | 421 | ✅ `:92` | Sends only name/email/password |
| `Dashboard.tsx` | 415 | ❌ | `mockRecommendations` `:37`, `mockStats` `:66` |
| `Quiz.tsx` | 372 | ❌ | `mockQuizData` `:21`; submit → `navigate` only |
| `Feedback.tsx` | 363 | ✅ `:70` | Only page reading the token from `localStorage` |
| `Features.tsx` | 284 | ❌ | Static marketing |
| `Landing.tsx` | 278 | ❌ | Static marketing |
| `About.tsx` | 218 | ❌ | Static marketing |
| `Login.tsx` | 207 | ✅ `:51` | Stores JWT + user |
| `Footer.tsx` / `Header.tsx` | 145 / 221 | ❌ | Layout |
| `NotFound.tsx`, `Index.tsx` | 27 / 17 | ❌ | Routing |

**Only 3 of 10 routed pages call the API.**

`frontend/src/api/client.ts` (65 lines) provides a reusable `request()` wrapper with token
injection and rich error objects. It exports `uploadResume` (`:43`), `aiRecommend` (`:52`), and
`analyticsEvent` (`:56`) — **none of which any page imports.**

### 3.4 Database — verified live state

`backend/instance/pathfinder.db` (32 KB) holds the live data:

```
user (11 rows) · profile (11) · upload (0) · guidance_session (6) · event (6) · feedback (2)
```

Sample: `profile(id=1, user_id=1, headline='Sample headline', skills='python,sql,ml')`.
Users 3–11 have **completely empty** profiles. Roles: 1 `admin`, 10 `user`.

`backend/pathfinder.db` at the repo root is **0 bytes** — a stray duplicate.

All 6 `guidance_session` rows stored the identical mock string, confirming the placeholder has
never produced a real result.

---

## 4. Current Architecture Analysis

### 4.1 Actual request flow

```text
User
  ↓
Vite SPA (frontend/src, port 8080)
  ├─ App.tsx — BrowserRouter, no route guards
  ├─ pages/*  — 7 of 10 never contact the API
  └─ api/client.ts — fetch() wrapper, token from localStorage
  ↓  fetch → VITE_API_BASE_URL (http://127.0.0.1:5001 or localhost:5000)
Flask app (backend/app.py, port 5000, gunicorn :8000 in Docker)
  ├─ /api/auth/*   → auth.py    → SQLAlchemy → SQLite
  ├─ /api/*        → guidance.py → SQLAlchemy → SQLite
  ├─ /admin/       → Flask-Admin → direct DB access (UNAUTHENTICATED)
  └─ APScheduler   → tasks.py daily_summary() → stdout
```

### 4.2 Architectural observations

1. **No service layer.** Business logic is embedded in route handlers. `guidance.py:39-71`
   contains prompt construction, an HTTP call, response parsing, error capture, and persistence
   in a single function. The proposal's §4.3 "ML module (skill extraction, matching, gap
   analysis)" implies testable, separable units.
2. **No validation layer.** Validation exists only inside `submit_feedback`
   (`guidance.py:107-128`) and is hand-rolled with inline `if` statements. `register`
   (`auth.py:11-17`) checks only that email and password are non-empty — no length, no format, no
   password strength. The proposal commits to Pydantic (§7.2).
3. **Two write models.** The product has no admin UI; job data would be edited through Flask-Admin,
   which bypasses the application's validation entirely.
4. **Configuration inconsistency.** `frontend/.env` → port 5001; `frontend/.env.development` →
   port 5000; `backend/app.py:60` → port 5000. No dev proxy in `vite.config.ts`.
5. **No schema migration strategy.** `app.py:46` calls `db.create_all()`, which creates missing
   tables but **never alters existing ones**. Any schema change requires deleting the file and
   losing all 11 users.

---

## 5. Frontend Analysis

### 5.1 Routing and access control

`App.tsx:74-124` defines 10 routes. `PublicLayout` (`App.tsx:26-34`) and `AuthenticatedLayout`
(`App.tsx:37-45`) are **byte-for-byte identical wrappers** differing only in name.

**Consequence:** `/dashboard`, `/quiz`, `/recommendations`, and `/feedback` are fully reachable by
anonymous visitors. There is no `<Navigate>`, no redirect, and no guard anywhere. The proposal's
§7.5 "role-based access" is unimplemented at the routing layer.

Additionally, `Header.tsx` contains **no links** to `/dashboard`, `/quiz`, or
`/recommendations` — only `/login` (`:121`, `:201`) and `/register` (`:124`, `:210`). An
authenticated user who lands on `/dashboard` has no in-app navigation to the rest of the
application.

### 5.2 Data flow — what is real vs. mocked

| Page | Data source | Assessment |
|---|---|---|
| `Dashboard.tsx` | `mockRecommendations` (`:37`), `mockStats` (`:66`) | ❌ Fabricated. `totalUsers: "12,847"`, `successRate: "94%"` presented as facts. Loading simulated by `setTimeout` (`:83-86`). |
| `Recommendations.tsx` | `mockRecommendations` (`:24`) | ❌ Fabricated, with invented salary bands (`$85,000-$120,000`), growth rates, and career paths. |
| `Quiz.tsx` | `mockQuizData` (`:21`) | ❌ Hardcoded. `handleSubmit` (`:182`) only calls `navigate("/recommendations")` (`:194`). No persistence. |
| `Recommendations.tsx:169` | `savedCareers` `useState` | ❌ Lost on refresh; no API call. |

The proposal's §4.2 user workflow — *upload CV → extract skills → confirm → view ranked roles with
compatibility % → view skill gap* — **has no implementation at any step**. There is no CV upload
UI; `client.ts:43` provides the function but no page calls it.

### 5.3 Forms and validation

| Form | Validation | Sends to API? | Issues |
|---|---|---|---|
| `Login.tsx` | client-side required checks (`:40-46`) | ✅ | Reasonable |
| `Register.tsx` | Strong: required fields, email regex, ≥8 chars, uppercase+lowercase+digit (`:43-75`) | 🟡 | **`educationLevel` collected (`:21`, `:128`) and required (`:71`) but never sent** — `api.register(name, email, password)` at `:92` omits it. Data silently lost. |
| `Feedback.tsx` | fields + rating | ✅ | Best-integrated form |

The registration form's client-side password policy is **stronger than the backend's**, which
accepts any non-empty password (`auth.py:14`). The server is the weaker boundary.

### 5.4 Missing frontend capability

| Proposal requirement | Status | Evidence |
|---|---|---|
| Profile CRUD screens | ❌ | No `Profile` page exists; `src/pages/` has no profile file |
| Skills management UI | ❌ | No skill entity in the app |
| Projects management UI | ❌ | No project entity |
| Education/certifications UI | ❌ | No entity |
| Admin job management UI | ❌ | Only Flask-Admin outside the SPA |
| CV upload + skill confirmation UI | ❌ | Function exists, no caller |
| Compatibility % display | 🔴 | Label rendered (`Recommendations.tsx:230,259`) against mock data |
| Skill-gap report UI | ❌ | Zero code occurrences |
| Role-based navigation | ❌ | No role logic in the frontend at all |

### 5.5 Frontend assets worth preserving

- **46 shadcn/ui components** in `src/components/ui/` — production-quality, typed, consistent
- `api/client.ts` `request()` helper — clean token injection and error enrichment (`client.ts:20-29`)
- `toast` / `sonner` dual toaster setup (`App.tsx:72-73`) — already wired
- `@tanstack/react-query` **installed and its `QueryClientProvider` already mounted**
  (`App.tsx:5,23,70`) but **never used by any page** — a significant opportunity, since server-state
  fetching is exactly what this app needs
- `recharts` installed — suitable for the evaluation dashboard
- `Header`/`Footer` responsive layout, consistent Tailwind theme in `index.css`

---

## 6. Backend Analysis

### 6.1 API architecture

Blueprint-based with two prefixes (`app.py:42-43`): `/api/auth` → `auth_bp`, `/api` →
`guidance_bp`. Clean enough for a starter; but `guidance.py` has become a catch-all holding five
unrelated concerns (uploads, AI, analytics, feedback, admin listing). The proposal's nine modules
warrant separate domain blueprints.

### 6.2 Authentication and authorization

**Authentication: partially correct.**

- Password hashing via `werkzeug.security.generate_password_hash` (`models.py:3,14`) ✅
- JWT access tokens via `flask-jwt-extended` (`auth.py:31,42`) ✅
- `email` is `unique=True, nullable=False` (`models.py:8`) ✅

**Gaps:**

- **No logout.** `auth.py` has 3 routes; the proposal §4.1 explicitly requires logout. Since
  tokens are stored in `localStorage` (`Login.tsx:55`) with no server-side revocation or refresh
  strategy, there is no logout mechanism at all — not even client-side token clearing.
- **No token expiry configured.** `create_access_token(identity=str(u.id))` (`auth.py:31,42`) sets
  no `expires_delta`, so Flask's default applies (30 minutes) but it is implicit and undocumented.
- **Role enforcement exists in exactly one place.** `guidance.py:157-163` loads the user and
  checks `role != 'admin'` → 403. `User.role` (`models.py:10`) is otherwise unused. The
  proposal's User/Admin role separation (§4.1) is 1/8 implemented.
- **Most endpoints use `@jwt_required(optional=True)`.** `guidance.py:10` (upload), `:40`
  (recommend), `:73` (analytics), `:93` (feedback) accept **unauthenticated** requests. For
  upload this means files are stored with `user_id = None` — unattributable, and the storage
  grows unbounded.

### 6.3 Validation

- `register` (`auth.py:11-17`): presence checks only. No password strength, length, or email
  format. Note the frontend enforces a strong policy (`Register.tsx:57-61`) that the API ignores.
- `login` (`auth.py:37-41`): presence checks only.
- `submit_feedback` (`guidance.py:107-128`): the **best** validation in the codebase — required
  message, subject ≤256, message ≤5000, email regex, rating 0–5 range, aggregated into a
  `details` array. This is the pattern to carry forward.
- `ai_recommend` (`guidance.py:43-44`): no validation whatsoever; `profile` and `goals` are taken
  as-is and interpolated into a prompt string (`:47`).

**No Pydantic.** The proposal commits to Pydantic (§7.2); it is not installed.

### 6.4 Error handling

Ad hoc but reasonable: `try/except` around each `db.session.commit()` with `rollback()` and
`logger.exception()`, returning `{'error': 'internal server error'}` with HTTP 500
(`guidance.py:64-70`, `:83-89`, `:143-147`). `register` follows the same pattern
(`auth.py:27-30`).

**Weaknesses:**
- Exceptions are caught and collapsed to a generic message; the cause is logged but never
  surfaced.
- `register` checks `User.query.filter_by(email=email).first()` (`auth.py:16`) but does not
  normalise case or whitespace — `A@b.com` and `a@b.com` are distinct accounts.
- No global error handler; no structured error envelope.
- The OpenAI branch stores raw provider error text into the response body
  (`result['api_error'] = resp.text`, `guidance.py:59`), which is returned to the client and
  persisted — an information-leak pattern if ever populated.

### 6.5 AI/ML integration — the critical gap

`guidance.py:39-71` is the entirety of the "AI" implementation. Annotated:

```python
# guidance.py:45-48
# simple placeholder: call OpenAI if key present, otherwise return mock
key = os.getenv('OPENAI_API_KEY') or current_app.config.get('OPENAI_API_KEY')
prompt = f"Make a short career recommendation for goals: {goals} and profile: {profile}"
result = {'recommendation': 'mock suggestion: build projects, learn data structures, apply to internships'}   # ← hardcoded

# guidance.py:52-54
# This is a placeholder. The real api call depends on the model/provider.
payload = { 'model': 'gpt-4o-mini', 'input': prompt }
resp = requests.post('https://api.openai.com/v1/responses', headers=headers, json=payload, timeout=15)
```

**Findings:**

1. The default response is a **hardcoded English string**, not model output.
2. The code's own comments describe it as a placeholder.
3. All 6 persisted `guidance_session` rows contain that mock string — the endpoint has never
   produced a genuine result.
4. **No ML library is installed.** No `sklearn`, `spacy`, `pandas`, `numpy`, `pdfplumber`, or
   `python-docx` in `requirements.txt` or anywhere in the source.
5. **The OpenAI payload is likely wrong.** It uses `/v1/responses` with an `input` field; the
   actual Responses API returns structured `output` (an array of content items). Line `:57`
   assigns `j.get('output')` — a list — directly to `recommendation`, so even a successful call
   would return a nested structure the frontend cannot render. `OPENAI_API_KEY` is empty in
   `.env`, so this path has never executed.
6. **This is exactly what the proposal forbids.** §4.2 specifies TF-IDF cosine similarity plus
   weighted skill coverage, and explicitly makes the LLM *optional* and *non-load-bearing*. The
   code makes an LLM call the centrepiece and implements none of the required ML.

**The proposal's own §4.2 honesty clause is respected by the codebase in letter but inverted in
spirit:** the design correctly avoids a trained classifier, but replaces the specified transparent
similarity math with an opaque external API call.

### 6.6 Missing backend capability

No profile endpoint · no skill endpoint · no project endpoint · no education/certification
endpoint · no job CRUD endpoint · no skill-gap endpoint · no CV text extraction · no skill
extraction · no matching service · no logout · no migrations · no tests.

---

## 7. Database Analysis

### 7.1 Actual schema

```sql
user(id PK, name, email UNIQUE NOT NULL, password_hash NOT NULL, role, created_at)
profile(id PK, user_id FK→user.id NOT NULL, headline, skills TEXT, education TEXT, experience TEXT)
upload(id PK, user_id FK→user.id NULL, filename, filepath, uploaded_at)
guidance_session(id PK, user_id FK→user.id NULL, inputs_json TEXT, result_json TEXT, created_at)
event(id PK, user_id FK→user.id NULL, name, metadata_json TEXT, created_at)
feedback(id PK, user_id FK→user.id NULL, name, email, feedback_type, rating,
         subject, message TEXT, features_json TEXT, allow_contact, created_at)
```

### 7.2 Structural problems

**1. The knowledge base does not exist.**
There is no `job`, `role`, `skill`, `taxonomy`, `project`, `education`, or `certification` table.
The proposal's entire premise — matching users against a curated set of AI/ML roles with weighted
required skills — has **no data model**.

**2. `profile.skills` is unusable for the required features.**
`models.py:26`: `skills = db.Column(db.Text)  # comma separated`. Live data:
`'python,sql,ml'`.

This single design decision blocks three proposal requirements simultaneously:

- **§4.1 Skill management CRUD** — no per-skill row, so no proficiency level per skill
- **§4.2 weighted skill-coverage** — importance weights are *per role per skill*; a flat string
  cannot express them
- **§4.2 skill-gap analysis** — computing "required minus present" requires set operations on
  normalised skill identifiers, impossible on a comma-delimited blob with no taxonomy mapping and
  no alias handling ("sklearn" ≠ "scikit-learn")

**3. No normalisation or aliasing.** The proposal's taxonomy requirement (≈150 skills with
aliases) implies a `skill` table plus a `skill_alias` mapping. Neither exists.

**4. Unnormalised JSON-in-TEXT columns.** `guidance_session.inputs_json/result_json`,
`event.metadata_json`, `feedback.features_json`, `profile.education`, `profile.experience`.
Acceptable for logs; not acceptable for `result_json`, which will hold structured recommendation
output that must be queried and rendered per field.

**5. Foreign keys are declared but not enforced.** SQLite does not enable `PRAGMA
foreign_keys=ON` by default and the code never sets it. Declared FKs (`models.py:24,33,40,46,54`)
are documentation, not constraints. Deleting a `user` will leave orphaned `profile`,
`upload`, `feedback` rows.

**6. No `ON DELETE` cascade** is declared anywhere, so even with enforcement enabled, deletion
would fail rather than cascade. The proposal requires delete operations on 4 entities.

**7. No indexes** beyond the implicit primary key and `UNIQUE(email)`. The proposal's admin job
listings (50–100 rows, filtered by role, ordered by match) and feedback filtering
(`guidance.py:173-183` orders by `created_at DESC` and filters by type/rating/user) have no
supporting indexes. Harmless at current scale; relevant as data grows.

**8. Nullable `user_id` on 4 of 6 tables** (`models.py:33,40,46,54`) — a direct consequence of
`@jwt_required(optional=True)`. Anonymous uploads, feedback, and sessions are permanently
unattributable.

**9. No migration tooling.** `app.py:46` → `db.create_all()`. Existing tables are never
altered. Adding a required column means dropping the database and losing all 11 users and 2
feedback entries.

**10. Duplicate database file.** `backend/pathfinder.db` (0 bytes) and
`backend/instance/pathfinder.db` (32 KB, the live one per `app.py:20`'s relative resolution).

### 7.3 Schema support for AI/recommendation features

| Proposal capability | Schema support |
|---|---|
| Store roles with required skills + weights | ❌ No table exists |
| Store a curated skill taxonomy with aliases | ❌ No table exists |
| Per-skill proficiency for a user | ❌ Flat TEXT column |
| CV → extracted skills (user-confirmed) | 🟡 `upload` records the file; no extracted-skills table |
| Persist a ranked recommendation with score | 🟡 `guidance_session.result_json` could hold it, but unstructured |
| Compute required-minus-present gap | ❌ Impossible with current schema |

**Conclusion:** the schema cannot support the proposed system and requires both new entities and a
redesign of `profile.skills`.

---

## 8. AI/ML Analysis

### 8.1 Current state

| Item | Status | Evidence |
|---|---|---|
| ML libraries installed | ❌ None | `requirements.txt` — no sklearn/spacy/pandas/numpy |
| ML imports anywhere | ❌ None | grep across all `.py` → zero |
| Skill extraction | ❌ None | No text extraction of any kind |
| Taxonomy | ❌ None | `profile.skills` is free text |
| Weighted skill coverage | ❌ None | — |
| TF-IDF / cosine similarity | ❌ None | — |
| Skill-gap computation | ❌ None | — |
| Training data | ❌ None | No dataset, no seed job listings |
| Evaluation harness | ❌ None | No metrics, no labelled profiles |
| LLM call | 🔴 Placeholder, self-described, never executed | `guidance.py:45-61`, empty key in `.env` |
| Jupyter notebook | ❌ None | Not present despite §7.2 |

**Nothing in the current codebase constitutes AI/ML engineering.** It is a single hardcoded string
behind an HTTP route.

### 8.2 The proposal's design is achievable and appropriately scoped

The proposal is unusually well-posed here, and this matters for planning:

- It specifies **TF-IDF cosine similarity** and **weighted skill coverage**, both classical,
  CPU-only, no GPU — consistent with §6.1 and §7.1.
- It **acknowledges** the absence of a large labelled dataset and **discloses** the choice of
  unsupervised similarity plus rule-based weighting over a trained classifier (§4.2).
- It **demarcates** the LLM as optional and non-load-bearing.

This means the AI component is genuinely achievable by 4 students in one semester, and — critically
— it can be **demonstrably real** without any external API. That is the correct engineering call for
an academic AI/ML project, and it is the opposite of what the code currently does.

### 8.3 Recommended ML module design

Realistic, testable, and directly traceable to §4.2. Files marked **NEW FILE REQUIRED**, following
the repo's flat-module backend convention.

**`backend/ml/taxonomy.py` — NEW FILE REQUIRED**
Loads and exposes the curated skill taxonomy: canonical skill name, category, and alias list
(≈150 skills, per §4.2/§7.3). Provides `canonicalise(term) -> str | None` for alias resolution and
`skill_id(name)` lookups. Load from a version-controlled JSON/YAML seed so the taxonomy is
inspectable and diffable.

**`backend/ml/extractor.py` — NEW FILE REQUIRED**
Implements §4.2 skill extraction. Reads CV text (delegating file-format handling to a text
loader), then runs **spaCy `PhraseMatcher`** with the taxonomy's canonical names *and aliases* as
patterns. Returns `[{skill_id, canonical_name, surface_form, count}]` plus the matched text span.
Deliberately returns **suggestions for user confirmation**, matching §4.1's "show detected skills
for user confirmation".

**`backend/ml/text_loader.py` — NEW FILE REQUIRED**
Thin wrapper over `pdfplumber`/`PyPDF2` for PDF and `python-docx` for DOCX, returning plain text.
Isolates format handling so the extractor stays format-agnostic and unit-testable.

**`backend/ml/matcher.py` — NEW FILE REQUIRED**
Implements §4.2 job matching. Two components:

1. **Weighted skill coverage** — for each role, sum importance weights of required skills the user
   possesses, divide by total role weight → `coverage ∈ [0,1]`.
2. **TF-IDF cosine similarity** — build a corpus from profile text and job descriptions, fit
   `TfidfVectorizer` from scikit-learn, compute pairwise cosine similarity.

Combine with weights defaulting to ~0.6/0.4, exposed as configuration so they can be tuned (§4.2
"tuned on the labelled sample profiles").

**`backend/ml/gap_analysis.py` — NEW FILE REQUIRED**
Implements §4.2 skill-gap: `required(role) − user_skills`, sorted by the role's importance weight
descending. Returns matched skills, missing skills, and per-skill weights so the frontend can
explain the score.

**`backend/ml/ranker.py` — NEW FILE REQUIRED**
Thin orchestration layer over matcher + gap_analysis producing the ranked, explainable response the
API returns. Keeping this separate from route handlers satisfies the proposal's §4.3 "ML module"
deliverable and keeps routes thin.

**`backend/services/recommendation_service.py` — NEW FILE REQUIRED**
Bridges DB and ML: loads the user's confirmed skills/projects/education plus the curated job
listings, invokes `ranker`, persists the result, and returns an explainable payload
(`role`, `compatibility_pct`, `matched_skills[]`, `missing_skills[]`). This is the boundary where
FastAPI routes call into ML — never the reverse.

**`backend/ml/evaluation/evaluate.py` — NEW FILE REQUIRED**
Implements the §2/§4.2 validation requirement: run the engine over ≥20 hand-labelled sample
profiles and report top-3 hit rate (§2 target: "the expected role appears in the top 3 for most
profiles"). Also tunes the 60/40 weights, satisfying §4.2. Outputs a small report — this is what
makes the ML component *demonstrable* rather than asserted.

**`backend/data/skills_taxonomy.json` — NEW FILE REQUIRED**
The ≈150-skill taxonomy with aliases. Version-controlled seed data (§7.3).

**`backend/data/job_listings.json` — NEW FILE REQUIRED**
50–100 curated AI/ML job listings with required skills and importance weights (§4.3, §7.3),
loadable by an admin seed script.

**`backend/tests/` — NEW FILE REQUIRED**
pytest suite covering: taxonomy alias resolution, extractor on sample CV text, gap calculation,
matcher score bounds and determinism, and API endpoints. Directly satisfies §7.2's pytest
commitment and makes evaluation reproducible.

### 8.4 Model/backend integration contract

```text
POST /api/match          (auth)  → recommendation_service → ranker → matcher + gap_analysis
                                                     ↓
                                          PostgreSQL (skills, jobs, weights)
```

Response shape — designed to satisfy §4.1's "Ranked role list with compatibility % and matched
skills" and §4.1's explainability requirement:

```json
{
  "target_role_id": 3,
  "compatibility_pct": 91,
  "components": { "skill_coverage": 0.88, "tfidf_similarity": 0.62, "weights": [0.6, 0.4] },
  "matched_skills": [{ "name": "Python", "weight": 1.0 }, { "name": "scikit-learn", "weight": 0.9 }],
  "missing_skills": [{ "name": "Docker", "weight": 0.8 }, { "name": "Kubernetes", "weight": 0.6 }]
}
```

`components` makes the score explainable per §2 ("explain each score with matched skills") and
§4.2's disclosure requirement. `missing_skills` carries the importance weight so the skill-gap
view can order by it.

### 8.5 Recommendation approach assessment

| Approach | Proposal says | Assessment |
|---|---|---|
| TF-IDF cosine + weighted coverage | ✅ Specified | Correct. Transparent, deterministic, CPU-only, defensible in a report. |
| Trained classifier / deep model | Explicitly declined (§4.2) | Correct given no labelled data. Do **not** introduce one. |
| LLM for recommendation core | Explicitly optional (§4.2, §4.4) | The code does this; the proposal does not. Must be demoted to an optional enhancement. |
| Embeddings for semantic matching | Future work (§11) | Correctly deferred. Do not build now. |

**Recommendation: implement precisely what §4.2 specifies.** The current code's LLM-centre design
should be removed from the critical path entirely, per §4.4's "keep LLM optional, freeze scope
after Sprint 2".

---

## 9. CRUD Analysis

Derived **strictly** from route evidence. `C`=Create `R`=Read `U`=Update `D`=Delete.

### 9.1 Existing entities

| Entity | Create | Read | Update | Delete | Evidence | Status |
|---|---|---|---|---|---|---|
| User | ✅ | ✅ | ❌ | ❌ | `auth.py:8` POST register; `auth.py:45` GET me | 🟡 Partial |
| Profile | 🟡 | ❌ | ❌ | ❌ | Created implicitly at `auth.py:24`; **no endpoint of any kind** | 🔴 Incomplete |
| Upload | ✅ | ✅ | ❌ | ❌ | `guidance.py:9` POST; `guidance.py:31` GET | 🟡 Partial |
| Feedback | ✅ | ✅ | ❌ | ❌ | `guidance.py:93` POST; `guidance.py:151` GET (admin) | 🟡 Partial |
| Event | ✅ | ❌ | ❌ | ❌ | `guidance.py:73` POST | 🟡 Partial |
| GuidanceSession | ✅ | ❌ | ❌ | ❌ | `guidance.py:63` POST | 🟡 Partial |

### 9.2 Proposal-required entities

| Entity | Create | Read | Update | Delete | Status |
|---|---|---|---|---|---|
| Skill | ❌ | ❌ | ❌ | ❌ | **Absent** — no model, no endpoint |
| Skill taxonomy / alias | ❌ | ❌ | ❌ | ❌ | **Absent** |
| Job role (admin) | ❌ | ❌ | ❌ | ❌ | **Absent** — no model, no endpoint |
| Project | ❌ | ❌ | ❌ | ❌ | **Absent** |
| Education | ❌ | ❌ | ❌ | ❌ | **Absent** |
| Certification | ❌ | ❌ | ❌ | ❌ | **Absent** |
| User skill (with proficiency) | ❌ | ❌ | ❌ | ❌ | **Absent** — flattened into `profile.skills` |

### 9.3 Summary

- **Full CRUD (C+R+U+D): 0 entities**
- **Create + Read only: 4 entities** (User, Upload, Feedback, Event)
- **Proposal entities with any CRUD: 0 of 7**

The proposal's §4.1 table requires full CRUD on **6 entities** (profile, skill, project,
education/certifications, job management) plus partial on 3. **None** meet the requirement.

---

## 10. Feature-by-Feature Alignment Matrix

| # | Proposal requirement | Status | Evidence |
|---|---|---|---|
| **Stack** | | | |
| 1 | FastAPI backend | 🔴 | Flask factory `app.py:14-15` |
| 2 | PostgreSQL | 🔴 | SQLite `app.py:20` |
| 3 | Next.js frontend | 🔴 | Vite `vite.config.ts` |
| 4 | Pydantic validation | ❌ | Not installed; ad-hoc checks only |
| 5 | SQLAlchemy | ✅ | `Flask-SQLAlchemy` used throughout |
| 6 | JWT authentication | ✅ | `flask-jwt-extended`, `auth.py:31` |
| 7 | scikit-learn | ❌ | Not installed |
| 8 | spaCy | ❌ | Not installed |
| 9 | pandas / NumPy | ❌ | Not installed |
| 10 | pdfplumber / PyPDF / python-docx | ❌ | Not installed; upload saves file only (`guidance.py:20`) |
| 11 | pytest | ❌ | Not in `requirements.txt` |
| 12 | Vercel / Render deploy | ❌ | No `vercel.json`, `Procfile`, or `render.yaml`; README claims Procfile at `README.md:11` |
| **Features** | | | |
| 13 | Register | ✅ | `auth.py:8` |
| 14 | Login | ✅ | `auth.py:34` |
| 15 | **Logout** | ❌ | No route; no client token clearing |
| 16 | Password hashing | ✅ | `models.py:13-14` |
| 17 | User/Admin role separation | 🟡 | Field exists (`models.py:10`); enforced on 1 of 10 routes (`guidance.py:162`) |
| 18 | Profile CRUD | ❌ | No endpoint |
| 19 | Skill management CRUD | ❌ | No entity |
| 20 | Project management CRUD | ❌ | No entity |
| 21 | Education/certification CRUD | ❌ | No entity |
| 22 | Admin job CRUD | ❌ | No entity |
| 23 | CV upload | 🟡 | Works (`guidance.py:9-29`) but no type validation, no text extraction, no UI caller |
| 24 | Skill extraction from CV | ❌ | Not implemented |
| 25 | User confirmation of detected skills | ❌ | No UI, no endpoint |
| 26 | Ranked roles + compatibility % | ❌ | Mock data `Recommendations.tsx:24` |
| 27 | Explanation of scores | ❌ | No matched-skill data |
| 28 | Skill-gap report | ❌ | Not implemented |
| 29 | Optional LLM learning path | 🔴 | Implemented as the *core* (§4.2 says optional), and it is a placeholder |
| 30 | Seed dataset (50–100 jobs, ~150 skills) | ❌ | No seed files; `scripts/seed_db.py` seeds 2 users only |
| 31 | Evaluation on 20+ labelled profiles | ❌ | No evaluation code |
| 32 | Responsive layout | ✅ | Tailwind throughout `Header.tsx`, `Footer.tsx`, all pages |
| 33 | Admin panel | 🔴 | Flask-Admin exists but is a generic unauthenticated DB browser, not a product feature |
| **Quality** | | | |
| 34 | Error handling | 🟡 | Try/except + rollback present (`guidance.py:64-70`); no global handler, no error envelope |
| 35 | Input validation | 🟡 | Only feedback is well-validated (`guidance.py:107-128`) |
| 36 | Route protection | ❌ | No guards in `App.tsx` |
| 37 | Schema migrations | ❌ | `db.create_all()` only (`app.py:46`) |
| 38 | Documentation | 🟡 | `backend/README.md` accurate but describes Pathfinder; `frontend/README.md` is unmodified Lovable boilerplate |

---

## 11. Gap Analysis

### Gap 1 — No job/role knowledge base

**Proposal requires:** a curated set of 50–100 AI/ML job listings, each with required skills and
importance weights, maintained by an administrator through CRUD (§2, §4.1, §4.3, §7.3).

**Currently exists:** nothing. `models.py` defines 6 models; none represent a job or role.

**What is missing:** `JobRole`, `JobRoleSkill` (with weight), taxonomy tables, admin CRUD
endpoints, seed data, and an admin UI.

**Why insufficient:** the recommendation engine has no candidate set to rank. Every downstream
requirement — compatibility %, matched skills, skill-gap — is defined relative to a target role.

**Required change:** create the schema, loaders, admin API, and seed data.

**Files affected:** `backend/models.py` (new models); **NEW** `backend/data/job_listings.json`;
**NEW** `backend/routes/jobs.py`; **NEW** `frontend/src/pages/admin/Jobs.tsx`.

**Layer:** Database + Backend + Frontend (cross-layer).

**Approach:** model a role as a row plus a weighted child table:

```sql
CREATE TABLE job_role (
  id SERIAL PRIMARY KEY,
  title VARCHAR(120) NOT NULL UNIQUE,
  family VARCHAR(80),                -- e.g. 'AI Engineer', 'ML Engineer'
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE job_role_skill (
  job_role_id INTEGER NOT NULL REFERENCES job_role(id) ON DELETE CASCADE,
  skill_id     INTEGER NOT NULL REFERENCES skill(id)     ON DELETE CASCADE,
  weight       NUMERIC(3,2) NOT NULL DEFAULT 1.00,
  PRIMARY KEY (job_role_id, skill_id)
);
```

The weight lives per (role, skill) — this is precisely what `profile.skills` as a flat string
cannot express, and what §4.2's "ranked by their importance weight for that role" requires.

### Gap 2 — `profile.skills` cannot support the AI features

**Proposal requires:** per-skill proficiency (§4.1 "update (proficiency level)"), weighted role
matching (§4.2), and gap analysis (§4.2), all against a ~150-skill taxonomy with aliases.

**Currently exists:** `models.py:26` — `skills = db.Column(db.Text)  # comma separated`, holding
values like `'python,sql,ml'`.

**What is missing:** normalised skill storage, a taxonomy, an alias map, and a join table for
user↔skill with proficiency.

**Why insufficient:** three independent failures in one column.
(i) No per-skill row means no proficiency level.
(ii) No weights means no coverage scoring.
(iii) No canonical identifiers means `'sklearn'` and `'scikit-learn'` are distinct strings, so gap
analysis produces false positives — exactly the alias problem §4.2 calls out.

**Required change:** replace the column with a normalised structure.

**Files affected:** `backend/models.py`; **NEW** `backend/models_skills.py` or new models in
`models.py`; **NEW** `backend/data/skills_taxonomy.json`; migration.

**Layer:** Database (primary), Backend.

**Approach:**

```sql
CREATE TABLE skill (
  id         SERIAL PRIMARY KEY,
  name       VARCHAR(120) NOT NULL UNIQUE,
  category   VARCHAR(80),
  is_ai_ml   BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE skill_alias (
  alias      VARCHAR(120) PRIMARY KEY,
  skill_id   INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE
);
CREATE TABLE user_skill (
  user_id     INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  skill_id    INTEGER NOT NULL REFERENCES skill(id)     ON DELETE CASCADE,
  proficiency SMALLINT NOT NULL DEFAULT 3 CHECK (proficiency BETWEEN 1 AND 5),
  source      VARCHAR(20) NOT NULL DEFAULT 'manual',   -- 'manual' | 'cv_extracted'
  PRIMARY KEY (user_id, skill_id)
);
```

`skill_alias.alias` as the primary key makes alias lookup a single indexed hit, which is what the
extractor's hot path needs. `source` records whether the user confirmed a skill or accepted a CV
extraction — supporting §4.1's confirmation requirement and §4.3's later evaluation.

### Gap 3 — No CV text extraction or skill extraction

**Proposal requires:** upload PDF/DOCX, extract text, match against the taxonomy with spaCy phrase
matching, present detected skills for user confirmation (§4.2, §4.1).

**Currently exists:** `guidance.py:9-29` saves the file to disk with a UUID-prefixed name and
records the path. Nothing reads it back.

**What is missing:** text extraction, spaCy matcher, detection results, and a confirmation UI.

**Why insufficient:** the upload is currently a dead end — the file is stored and never processed.

**Files affected:** **NEW** `backend/ml/text_loader.py`, **NEW** `backend/ml/extractor.py`;
`backend/guidance.py` (replace `upload_resume` body); **NEW**
`frontend/src/pages/CVUpload.tsx`.

**Layer:** Backend (AI/ML) + Frontend.

**Approach:** extract on upload, return suggestions, persist only on confirmation:

```text
POST /api/cv/upload      → text_loader.load() → extractor.extract() → 200 {detected_skills: [...]}
POST /api/skills/confirm → user_skill upsert (source='cv_extracted') → 201
```

Per §11's stated limitation ("OCR is not included"), reject scanned/image PDFs with a clear
message rather than silently returning nothing.

### Gap 4 — No matching or gap engine

**Proposal requires:** weighted skill-coverage + TF-IDF cosine (scikit-learn), and required-minus-
present gap ranked by weight (§4.2).

**Currently exists:** a hardcoded string (`guidance.py:48`) and a non-functional OpenAI placeholder
(`guidance.py:52-54`).

**What is missing:** the entire ML layer — see §8.3.

**Why insufficient:** this is the project's core AI contribution. Without it the system produces
no genuine output, which is the single most damaging gap for an AI/ML-degree project.

**Files affected:** **NEW** `backend/ml/{matcher,gap_analysis,ranker}.py`, **NEW**
`backend/services/recommendation_service.py`; `backend/requirements.txt` (add scikit-learn,
spacy, pandas, numpy, pdfplumber, python-docx).

**Layer:** Backend (AI/ML), cross-layer with Database.

**Approach:** see §8.3 and §8.4. Deterministic, CPU-only, no GPU, no external API.

### Gap 5 — No CRUD update or delete operations anywhere

**Proposal requires:** full CRUD on profile, skills, projects, education/certifications, and admin
job management (§4.1).

**Currently exists:** 0 PUT/PATCH/DELETE routes in the entire backend.

**What is missing:** every update and delete path; and for Profile, Project, Education, and Job,
even create and read.

**Why insufficient:** the course requirement explicitly demands CRUD operations. This is the most
easily-checked grading criterion and it currently fails outright.

**Files affected:** **NEW** `backend/routes/profile.py`, **NEW** `backend/routes/skills.py`,
**NEW** `backend/routes/projects.py`, **NEW** `backend/routes/education.py`, **NEW**
`backend/routes/jobs.py`.

**Layer:** Backend + Frontend.

**Approach:** FastAPI `APIRouter` per domain with explicit `@router.put`/`@router.delete`
handlers, ownership checks (`user_id == get_current_user().id`), Pydantic request/response models,
and 404/403/409 error semantics. In SQLAlchemy this is `session.get()` → mutate → `commit()` for
update, and `session.delete()` + commit for delete.

### Gap 6 — Authentication gaps

**Proposal requires:** register, login, **logout**, JWT sessions, User/Admin roles (§4.1, §7.5).

**Currently exists:** register, login, `me`. Roles enforced on 1 of 10 routes.

**What is missing:** logout; role enforcement; token lifetime configuration; consistent protection.

**Why insufficient:** §7.5 requires role-based access. With `@jwt_required(optional=True)` on
upload, recommend, analytics, and feedback (`guidance.py:10,40,73,93`), an anonymous caller can
write rows — and those rows can never be attributed or deleted by their author.

**Files affected:** `backend/auth.py` (add logout, role guards); **NEW**
`backend/dependencies.py` (shared `require_role("admin")`); `frontend/src/api/client.ts`;
`frontend/src/App.tsx` (route guards).

**Layer:** Backend + Frontend.

**Approach:** add a `require_role` dependency; apply `@jwt_required()` (not optional) to all
authenticated writes; add `POST /api/auth/logout`; add client-side route guards with
`<Navigate to="/login" state={{from}} />`.

### Gap 7 — Frontend is 70% mock

**Proposal requires:** profile, skills, projects, education, CV upload, ranked roles with
compatibility %, and skill-gap views (§4.1).

**Currently exists:** 3 pages call the API; 7 render static content; `Dashboard.tsx`, `Recommendations.tsx`,
and `Quiz.tsx` display fabricated data including invented statistics (`totalUsers: "12,847"`,
`successRate: "94%"` at `Dashboard.tsx:70-74`).

**What is missing:** every CRUD screen, the recommendation screen, and the skill-gap screen.

**Why insufficient:** the deliverable is a working web application (§4.3). Fabricated statistics
are also a credibility risk in a graded submission.

**Files affected:** `frontend/src/pages/{Dashboard,Recommendations}.tsx` (rewrite);
**NEW** `frontend/src/pages/{Profile,Skills,Projects,Education,CVUpload,SkillGap}.tsx`;
`frontend/src/App.tsx`; `frontend/src/api/client.ts`.

**Layer:** Frontend.

**Approach:** keep existing page shells and Tailwind styling; replace only the data layer with
React Query mutations/queries — the `QueryClientProvider` is already mounted (`App.tsx:70`), so no
new state-management dependency is needed.

### Gap 8 — Wrong frameworks throughout

**Proposal requires:** FastAPI, PostgreSQL, Next.js (§7.2).

**Currently exists:** Flask, SQLite, Vite.

**Why insufficient:** these are explicit, submitted commitments. Alignment means conformance.

**Files affected:** new FastAPI backend package; SQLAlchemy models retargeted to PostgreSQL;
frontend reconfigured for Next.js.

**Layer:** Cross-layer, foundational.

**Approach:** see §13 and §20. This is the largest single driver of rework and should be decided
before Sprint 1.

### Gap 9 — No migrations, no tests

**Proposal requires:** pytest (§7.2, §7.2 "Testing and deployment").

**Currently exists:** `db.create_all()` (`app.py:46`); `scripts/e2e_test.py` as an ad-hoc script
against `127.0.0.1:5001`; no test directory; pytest not installed.

**Why insufficient:** `create_all()` never alters existing tables, so schema evolution is
impossible without data loss. And with no tests, the ML module's correctness — the project's core
claim — cannot be demonstrated.

**Files affected:** **NEW** `backend/alembic/` (or `backend/migrations/`);
**NEW** `backend/tests/`; `backend/requirements.txt`.

**Layer:** Backend + Database.

**Approach:** Alembic for migrations; pytest + `TestClient` for API tests; a dedicated evaluation
test that runs the 20-profile harness and asserts the top-3 hit-rate target.

---

## 12. Architecture Differences

### 12.1 Current

```text
User
  ↓
Vite SPA (React Router, no guards)
  ↓  fetch
Flask Blueprints (auth, guidance)
  ↓  inline logic
SQLAlchemy → SQLite
  ↓
[ Flask-Admin — unauthenticated direct DB access ]
[ APScheduler → stdout ]
```

### 12.2 Proposed

```text
User
  ↓
Next.js (React) — guarded routes, React Query
  ↓  REST + JWT
FastAPI routers (auth, profile, skills, projects, education, cv, jobs, match)
  ↓
Pydantic validation
  ↓
Services (recommendation_service)
  ↓
ML layer (extractor, matcher, gap_analysis, ranker)
  ↓
SQLAlchemy → PostgreSQL
  ├─ user, profile, user_skill, skill, skill_alias, project, education, certification
  └─ job_role, job_role_skill
```

### 12.3 Divergence points

| # | Current | Proposed | Severity |
|---|---|---|---|
| 1 | Flask blueprints | FastAPI routers + Pydantic | 🔴 Full rewrite of the API layer |
| 2 | SQLite file | PostgreSQL + Alembic | 🔴 Schema + migration rewrite |
| 3 | Vite SPA routing | Next.js App Router | 🔴 Frontend restructure |
| 4 | Inline route logic | Service layer | 🔴 Required for testable ML |
| 5 | LLM call as the AI core | TF-IDF + weighted coverage | 🔴 Different algorithm entirely |
| 6 | No skill/role entities | 10+ normalised tables | 🔴 New domain |
| 7 | Flask-Admin as admin UI | In-app admin CRUD | 🔴 Product-level gap |
| 8 | `@jwt_required(optional=True)` | Mandatory auth + role guards | 🔴 Security |
| 9 | No evaluation | 20-profile harness + report | 🟡 Required for credibility |

---

## 13. File-Level Modification Plan

### 13.1 Backend

| File | Current purpose | Required change | Priority |
|---|---|---|---|
| `backend/models.py` | 6 models | **REPLACE** — normalise `Profile.skills`; add Skill, SkillAlias, UserSkill, JobRole, JobRoleSkill, Project, Education, Certification | P0 |
| `backend/app.py` | Flask app factory | **REPLACE** with FastAPI app factory + Alembic + router registration | P0 |
| `backend/auth.py` | 3 auth routes | **REPLACE** with FastAPI `APIRouter`; add logout, refresh, explicit token expiry, role dependency | P0 |
| `backend/guidance.py` | 5 unrelated routes | **SPLIT AND REPLACE** — upload→`cv.py`, AI→`match.py`, analytics→`analytics.py`, feedback→`feedback.py` | P0 |
| `backend/requirements.txt` | 10 deps | Add `fastapi`, `uvicorn`, `pydantic`, `python-jose[cryptography]` or `pyjwt`, `psycopg2-binary`, `alembic`, `scikit-learn`, `spacy`, `pandas`, `numpy`, `pdfplumber`, `python-docx`, `pytest`, `httpx` | P0 |
| `backend/extensions.py` | Singleton instances | **REPLACE** — SQLAlchemy async engine/session, settings via `pydantic-settings` | P0 |
| `backend/admin.py` | Flask-Admin views | **REMOVE** — superseded by in-app admin (§17). If retained during transition, it **must** be auth-gated first (§18) | P0 |
| `backend/tasks.py` | APScheduler demo | **REMOVE** — out of proposal scope | P1 |
| `backend/utils.py` | `allowed_file()` | **REPLACE** — actually wire it, or fold into `cv.py` | P0 |
| **NEW** `backend/ml/taxonomy.py` | — | **NEW FILE REQUIRED** — load taxonomy, `canonicalise()` | P0 |
| **NEW** `backend/ml/text_loader.py` | — | **NEW FILE REQUIRED** — PDF/DOCX → text | P0 |
| **NEW** `backend/ml/extractor.py` | — | **NEW FILE REQUIRED** — spaCy PhraseMatcher extraction | P0 |
| **NEW** `backend/ml/matcher.py` | — | **NEW FILE REQUIRED** — weighted coverage + TF-IDF cosine | P0 |
| **NEW** `backend/ml/gap_analysis.py` | — | **NEW FILE REQUIRED** — required − present, ranked by weight | P0 |
| **NEW** `backend/ml/ranker.py` | — | **NEW FILE REQUIRED** — orchestration | P0 |
| **NEW** `backend/services/recommendation_service.py` | — | **NEW FILE REQUIRED** — DB↔ML bridge | P0 |
| **NEW** `backend/dependencies.py` | — | **NEW FILE REQUIRED** — `require_role()` | P0 |
| **NEW** `backend/schemas.py` | — | **NEW FILE REQUIRED** — Pydantic models | P0 |
| **NEW** `backend/routes/{profile,skills,projects,education,cv,jobs,match,feedback,analytics}.py` | — | **NEW FILE REQUIRED** — domain routers | P0 |
| **NEW** `backend/data/skills_taxonomy.json` | — | **NEW FILE REQUIRED** — ~150 skills + aliases | P0 |
| **NEW** `backend/data/job_listings.json` | — | **NEW FILE REQUIRED** — 50–100 listings + weights | P1 |
| **NEW** `backend/ml/evaluation/evaluate.py` | — | **NEW FILE REQUIRED** — 20-profile harness | P1 |
| **NEW** `backend/tests/` | — | **NEW FILE REQUIRED** — pytest suite | P1 |
| **NEW** `backend/alembic/` | — | **NEW FILE REQUIRED** — migrations | P0 |
| `backend/scripts/seed_db.py` | Seeds 2 users | **REPLACE** — seed admin + taxonomy + job listings | P1 |
| `backend/Dockerfile` | gunicorn :8000 | **REPLACE** — uvicorn, PostgreSQL connection | P1 |
| **NEW** `backend/.gitignore` | **MISSING** | **NEW FILE REQUIRED** — `.env`, `*.db`, `venv/`, `__pycache__/` | **P0 (security)** |

### 13.2 Frontend

| File | Current purpose | Required change | Priority |
|---|---|---|---|
| `frontend/src/App.tsx` | Routes, no guards | **REPLACE** — Next.js App Router; add auth guards; role-based nav | P0 |
| `frontend/src/api/client.ts` | fetch wrapper | **REPLACE** — typed client; reuse its error-enrichment pattern (`:149-155`) | P0 |
| `frontend/src/pages/Dashboard.tsx` | Mock stats | **REPLACE** — real counts + match summary; **remove fabricated stats** | P0 |
| `frontend/src/pages/Recommendations.tsx` | Mock roles | **REPLACE** — real ranked roles, compatibility %, matched/missing skills | P0 |
| `frontend/src/pages/Login.tsx` | Working login | **MIGRATE** to Next.js; add logout | P1 |
| `frontend/src/pages/Register.tsx` | Working register | **MIGRATE**; **fix `educationLevel` drop** (`:92`) | P1 |
| `frontend/src/pages/Feedback.tsx` | Working feedback | **MIGRATE** | P2 |
| `frontend/src/pages/Quiz.tsx` | Mock quiz | **REPLACE or remove** — §4.1 lists no quiz module | P1 |
| `frontend/src/pages/{About,Features,Landing,Index}.tsx` | Marketing | **MIGRATE** as-is | P2 |
| **NEW** `frontend/src/pages/Profile.tsx` | — | **NEW FILE REQUIRED** — profile CRUD | P0 |
| **NEW** `frontend/src/pages/Skills.tsx` | — | **NEW FILE REQUIRED** — skill CRUD + proficiency | P0 |
| **NEW** `frontend/src/pages/Projects.tsx` | — | **NEW FILE REQUIRED** — project CRUD | P0 |
| **NEW** `frontend/src/pages/Education.tsx` | — | **NEW FILE REQUIRED** — education/cert CRUD | P1 |
| **NEW** `frontend/src/pages/CVUpload.tsx` | — | **NEW FILE REQUIRED** — upload + detected-skill confirmation | P0 |
| **NEW** `frontend/src/pages/SkillGap.tsx` | — | **NEW FILE REQUIRED** — gap report by target role | P0 |
| **NEW** `frontend/src/pages/admin/Jobs.tsx` | — | **NEW FILE REQUIRED** — admin job CRUD | P1 |
| `frontend/src/components/ui/*` (46 files) | shadcn kit | **REUSE UNCHANGED** | — |
| `frontend/src/components/layout/{Header,Footer}.tsx` | Layout | **MIGRATE**; add nav to real pages | P1 |
| `frontend/src/lib/utils.ts` | `cn()` | **REUSE UNCHANGED** | — |
| **NEW** `frontend/.env.example` | — | **NEW FILE REQUIRED** — document `NEXT_PUBLIC_API_URL` | P1 |
| `frontend/package.json` | Vite | **REPLACE** — Next.js, TanStack Query, remove unused | P0 |
| `frontend/vite.config.ts` | Vite config | **REMOVE** | P0 |

---

## 14. Reusable Components

### 14.1 Reusable without changes

| Component | Evidence | Why it survives |
|---|---|---|
| **shadcn/ui kit (46 components)** | `src/components/ui/` | Framework-agnostic React + Tailwind; works under Next.js unchanged |
| **`cn()` utility** | `src/lib/utils.ts` | Standard `clsx` + `tailwind-merge` helper |
| **`request()` error pattern** | `client.ts:20-29` | Attaches `status` + parsed body to a thrown Error — a good pattern to port to the typed client |
| **Tailwind theme** | `index.css`, `tailwind.config.ts` | Visual identity is stack-independent |
| **`@tanstack/react-query`** | Installed; `QueryClientProvider` mounted at `App.tsx:70` | Server-state fetching is exactly what this app needs; provider already in place |
| **`recharts`** | Installed | Suitable for the §4.2 evaluation dashboard |
| **Auth domain logic** | `auth.py:13-17,31-43` | Hashing and JWT issuance logic ports directly to FastAPI |
| **Feedback validation approach** | `guidance.py:107-128` | Aggregated error list is the right shape; port the concept to Pydantic |

### 14.2 Reusable with minor changes

| Component | Change |
|---|---|
| `Login.tsx`, `Register.tsx` | Port to Next.js; add logout; send `educationLevel` |
| `Feedback.tsx` | Port; keep payload shape |
| `Header.tsx`, `Footer.tsx` | Port; add real nav links |
| `models.py: User` | Keep; add indexes, cascade FKs |
| `Dockerfile` | Swap gunicorn → uvicorn; add PostgreSQL env |
| `scripts/seed_db.py` | Keep the pattern; seed taxonomy + job listings instead of 2 users |

### 14.3 Requires major modification

| Component | Change |
|---|---|
| `models.py: Profile` | `skills` TEXT must become normalised `user_skill` rows |
| `guidance.py` | Split into 4 routers; remove the OpenAI path from the critical path |
| `app.py` | Flask factory → FastAPI factory + Alembic |
| `Dashboard.tsx`, `Recommendations.tsx` | Data layer entirely replaced |
| `api/client.ts` | Typed, Next.js-integrated |

### 14.4 Must be newly implemented

Skill taxonomy + aliases · spaCy extractor · TF-IDF/weighted matcher · gap analysis · ranker ·
recommendation service · 7 new domain routers · profile/skills/projects/education/job CRUD APIs ·
CV upload + confirmation UI · ranked-recommendations UI · skill-gap UI · admin job UI · evaluation
harness · Alembic migrations · pytest suite.

---

## 15. Implementation Priority

### P0 — Critical (the project cannot function without these)

| Task | Layer | Files | Depends on | Complexity |
|---|---|---|---|---|
| Decide and commit to the target stack (§20) | Cross | — | — | Low |
| Normalise schema; add Skill/UserSkill/JobRole entities | DB | `models.py`, **NEW** `alembic/` | stack decision | Medium |
| Replace Flask with FastAPI app + routers | Backend | `app.py`, **NEW** `schemas.py`, `dependencies.py` | schema | High |
| Retarget to PostgreSQL | DB | config, **NEW** Alembic | schema | Medium |
| Build the ML layer (taxonomy, extractor, matcher, gap, ranker) | AI/ML | **NEW** `backend/ml/*` | schema | High |
| Recommendation service bridging DB↔ML | Backend | **NEW** `services/recommendation_service.py` | ML layer | Medium |
| Full CRUD routers for profile/skills/projects | Backend | **NEW** `backend/routes/*` | schema | High |
| Replace mocked frontend pages with real data | Frontend | `Dashboard.tsx`, `Recommendations.tsx`, `client.ts` | API | Medium |
| Fix authentication gaps (logout, role guards, mandatory JWT) | Backend + Frontend | `auth.py`, **NEW** `dependencies.py`, `App.tsx` | FastAPI port | Medium |
| **Harden `/admin/` or remove Flask-Admin** | Backend | `admin.py` | — | Low |
| **Add `backend/.gitignore`** | Infra | **NEW** `.gitignore` | — | Low |

### P1 — High (major proposal requirements)

| Task | Layer | Files | Depends on | Complexity |
|---|---|---|---|---|
| CV upload → extraction → confirmation flow | Backend + Frontend | **NEW** `routes/cv.py`, **NEW** `ml/text_loader.py`, `ml/extractor.py`, **NEW** `pages/CVUpload.tsx` | ML layer | Medium |
| Skill-gap report UI | Frontend | **NEW** `pages/SkillGap.tsx`, `routes/match.py` | matcher | Medium |
| Seed taxonomy (~150 skills) + job listings (50–100) | DB | **NEW** `backend/data/*.json`, `seed_db.py` | schema | Medium |
| Evaluation harness on 20+ labelled profiles | AI/ML | **NEW** `ml/evaluation/evaluate.py` | ML layer | Medium |
| Admin job management UI | Frontend | **NEW** `pages/admin/Jobs.tsx`, `routes/jobs.py` | CRUD routers | Medium |
| pytest suite | Backend | **NEW** `backend/tests/` | routers | Medium |
| Frontend → Next.js migration | Frontend | `App.tsx`, `package.json`, pages | API | High |
| Education/certification CRUD | Backend + Frontend | **NEW** `routes/education.py`, **NEW** `pages/Education.tsx` | schema | Medium |

### P2 — Medium (supporting)

| Task | Layer | Files | Depends on | Complexity |
|---|---|---|---|---|
| Deploy configs (Vercel, Render, PostgreSQL) | Infra | **NEW** `render.yaml`, `vercel.json` | stack | Low |
| Evaluation dashboard (recharts) | Frontend | **NEW** admin evaluation view | evaluation harness | Medium |
| Analytics event tracking | Backend | **NEW** `routes/analytics.py` | — | Low |
| Error-envelope standardisation | Backend | **NEW** `exceptions.py` | routers | Low |
| Feedback UI migration | Frontend | `Feedback.tsx` | Next.js | Low |
| Marketing page migration | Frontend | `About/Features/Landing` | Next.js | Low |

### P3 — Optional (§4.2 marks the LLM explicitly optional)

| Task | Layer | Files | Depends on | Complexity |
|---|---|---|---|---|
| LLM learning-path suggestions | AI/ML | **NEW** `ml/learning_path.py` | core ML complete | Low |
| Similarity caching | Backend | `services/` | matcher | Low |
| Query optimisation | DB | indexes on `job_role_skill` | seed data | Low |

**Keep P3 out of scope until P0 and P1 are complete** — §4.4's mitigation explicitly says "Keep LLM
optional, freeze scope after Sprint 2".

---

## 16. Dependency & Impact Analysis

```text
Stack decision (§20)
  └─→ Schema design
        ├─→ Alembic + PostgreSQL
        ├─→ ML layer (taxonomy → extractor → matcher → gap_analysis → ranker)
        │     └─→ recommendation_service
        │           └─→ /api/match
        ├─→ CRUD routers
        │     ├─→ profile/skills/projects/education APIs
        │     └─→ job admin API
        └─→ Seed data (taxonomy, job listings)
              └─→ Evaluation harness (needs both taxonomy and matcher)

Auth hardening ──→ can proceed independently, P0, low complexity

Admin exposure ──→ independent, P0, must happen before any deployment

Frontend rewire ──→ blocked by API completion
  └─→ React Query pages
        └─→ Next.js migration (can proceed in parallel, applied last)
```

**Critical path:** stack decision → schema → ML layer → service → API → frontend wiring. Everything
else is parallelisable.

**Highest-leverage sequencing insight:** the schema decision blocks the most work. Resolve it first;
several weeks of frontend and ML effort fork off it.

---

## 17. Recommended Implementation Roadmap

Maps to the proposal's §5 six-sprint model, re-scoped to actual code state.

| Sprint | Focus | Deliverable |
|---|---|---|
| **1** | Stack commitment, schema design, Alembic, FastAPI skeleton, auth hardening, `/admin/` fix, `.gitignore` | Working FastAPI + PostgreSQL with JWT auth and zero critical security issues |
| **2** | CRUD routers (profile, skills, projects), taxonomy seed data | All P0 CRUD endpoints live; 9-module table partially satisfied |
| **3** | ML layer: matcher, gap analysis, ranker, recommendation service; 20-profile evaluation | Ranked roles with explainable compatibility %; evaluation report |
| **4** | CV upload → extraction → confirmation; frontend rewire | End-to-end AI flow with user confirmation |
| **5** | Admin job CRUD + admin UI; skill-gap UI; seed 50–100 listings | Full knowledge base manageable in-app |
| **6** | Next.js migration, testing, deployment, documentation | Deployed application + report artifacts |

This front-loads the security fixes (Sprint 1) and the AI core (Sprint 3), which is the correct
order for a graded AI/ML submission.

---

## 18. Security & Data Hygiene

Findings beyond strict proposal alignment, rated for action.

| # | Finding | Severity | Evidence | Fix |
|---|---|---|---|---|
| **S1** | **Flask-Admin mounted with no authentication** | 🔴 **Critical** | `extensions.py:8`, `app.py:27`, `admin.py:49-54`. No `is_accessible` override exists anywhere, so `/admin/` is publicly reachable and lists all `user` rows including `email` and `password_hash`. Password hashes are offline-attackable. | Remove Flask-Admin (superseded by in-app admin), or gate it with an `is_accessible` check before any deployment |
| **S2** | Fully open CORS | 🔴 High | `app.py:18` — `CORS(app)` with no `origins` allowlist permits any origin | `CORS(app, resources={r"/api/*": {"origins": os.getenv("ALLOWED_ORIGINS", "").split(",")}})` |
| **S3** | No file-type validation on upload | 🔴 High | `allowed_file()` exists at `utils.py:2` but is never imported; `guidance.py:20` saves whatever is posted | Wire the allowlist in; validate extension **and** content type |
| **S4** | Optional JWT on write endpoints | 🔴 High | `guidance.py:10,40,73,93` — `@jwt_required(optional=True)` lets anonymous callers write `Upload`, `GuidanceSession`, `Event`, `Feedback` rows with `user_id = NULL` | `@jwt_required()` on all authenticated writes |
| **S5** | IDOR on upload download | 🔴 High | `guidance.py:31` — `/api/uploads/<int:upload_id>` has sequential IDs and no ownership check | Require auth; verify `up.user_id == current_user.id` |
| **S6** | No `backend/.gitignore` | 🔴 High | `.env`, `pathfinder.db` (32 KB), and `venv/` (162 MB) all in tree | **NEW** `.gitignore`: `.env`, `*.db`, `venv/`, `__pycache__/` |
| **S7** | Weak secret fallbacks | 🟡 Medium | `app.py:19,22` — `'dev-secret'`, `'jwt-secret'` if env unset | Fail fast at startup if secrets are missing |
| **S8** | Provider error text returned and persisted | 🟡 Medium | `guidance.py:59` — `result['api_error'] = resp.text` is both returned to the client and stored | Log server-side only; never return upstream error bodies |
| **S9** | Unnormalised email allows duplicate accounts | 🟡 Medium | `auth.py:16` — no case/whitespace normalisation | Normalise to lowercase; consider a functional unique index |
| **S10** | Foreign keys not enforced | 🟡 Medium | SQLite defaults `PRAGMA foreign_keys=OFF`; never enabled | Resolved by the PostgreSQL migration; add `ON DELETE CASCADE` |
| **S11** | Duplicate/stray database file | 🟡 Low | `backend/pathfinder.db` (0 bytes) vs `instance/pathfinder.db` | Delete the stray file |
| **S12** | Unbounded anonymous upload storage | 🟡 Low | `guidance.py:17-20` — any anonymous caller can write files with no quota | Auth-gated (S4) + size limit |

**Note:** `.env` currently holds placeholder values (`replace-with-a-secret`,
`JWT_SECRET_KEY=replace-with-jwt-secret`, empty `OPENAI_API_KEY`), so **no live secret is exposed
right now**. The risk is structural: nothing prevents a real key from being committed. S6 is
preventive, not an active breach.

**Priority:** S1, S3, S4, S5, S6 are all P0 and should be resolved before any deployment.

---

## 19. Naming & Branding Consistency

The codebase carries **three different product names**:

| Name | Occurrences | Locations |
|---|---|---|
| **Pathfinder** | 2 | `backend/app.py:53`, `backend/extensions.py:8` |
| **CareerGuide AI** | 8 | `Footer.tsx:44,126`, `Header.tsx:69`, `Landing.tsx:44,138,203`, `Feedback.tsx:74`, `Login.tsx:93`, `Register.tsx:101,170`, `About.tsx:77` |
| **CareerLens AI** | **0** | Proposal only |

`package.json:2` is still the scaffold default `"vite_react_shadcn_ts"`.
`backend/README.md` is titled "Pathfinder AI Guide - Flask Backend (starter)" and describes the
Flask starter, so it documents a product that will no longer exist.
`frontend/README.md` is unmodified **Lovable** boilerplate with an empty "Project info" section.

**Recommendation:** settle on **CareerLens AI** (the submitted name) and perform one sweep across
`Header`, `Footer`, all page copy, `app.py:53`, admin title, both READMEs, and `package.json`. This
is cosmetic and P2, but shipping three names in a graded submission is avoidable.

---

## 20. Final Technical Assessment

### 20.1 Already supported

- Password hashing, JWT issuance, and a complete register/login/me flow (`auth.py`, `models.py`)
- Tailwind + shadcn/ui design system (46 components) — directly satisfies §7.2's "Tailwind CSS (or similar)"
- SQLAlchemy ORM usage and a normalised `User` entity
- File upload mechanics (storage works; processing does not)
- A consistent API client with useful error enrichment
- React Query installed and its provider already mounted
- Feedback validation — the best validation code in the repo

### 20.2 Partially supported

- Authentication: register/login/me work; **logout, token lifetime, and role enforcement do not**
- CV upload: the file is stored but never read, parsed, or matched
- Roles: `User.role` exists and works on one route
- Error handling: present and reasonable, but ad hoc and unenveloped

### 20.3 Completely missing

- **All update and delete operations** (zero PUT/PATCH/DELETE in the backend)
- **The entire Job/Role/Skill domain** — 7 required entities, none exist
- **The entire ML layer** — no extraction, matching, gap analysis, or evaluation
- **Profile, project, education, and certification CRUD APIs**
- **Admin job management** as a product feature
- **Migrations, tests, and deployment configuration**

### 20.4 Major gaps by layer

| Layer | Severity | Summary |
|---|---|---|
| **AI/ML** | 🔴 Critical | Not started. The single most important gap for an AI/ML-degree project |
| **Database** | 🔴 Critical | No domain schema; `profile.skills` design actively blocks three requirements; no migrations |
| **Backend** | 🔴 Critical | No CRUD beyond C+R; wrong framework; no validation layer; no service layer |
| **Frontend** | 🔴 High | 7 of 10 pages mocked; no CRUD screens; no route guards; wrong framework |
| **Security** | 🔴 High | Publicly exposed admin panel; open CORS; unauthenticated writes; IDOR |
| **Infrastructure** | 🟡 Medium | No migrations, tests, or deploy config |

### 20.5 Can the codebase realistically be evolved into the proposed project?

**Yes — but only by replacing roughly half of it.**

The reusable portion is the **presentation layer and the auth domain logic**. The portion that must
be replaced is the **entire serving stack and the entire domain and ML layer**.

Concretely: of ~468 lines of backend application code, only the auth *logic*
(~50 lines) carries forward in substance. Everything else is either replaced or newly written. On
the frontend, the shadcn kit (~46 components), `cn()`, the theme, and the auth forms carry forward;
the three data pages are rewritten.

### 20.6 Minimum change set to satisfy the proposal

1. Commit to the target stack (FastAPI + PostgreSQL + Next.js) — §20.7
2. Normalise the schema; add the 7 missing entities with weights and aliases
3. Build the ML layer exactly as §4.2 specifies (taxonomy → extractor → matcher → gap → ranker)
4. Implement full CRUD across the 9 modules of §4.1
5. Wire the three mocked pages to real endpoints
6. Seed the taxonomy (~150 skills) and job listings (50–100)
7. Run the 20-profile evaluation and report top-3 hit rate
8. Close the P0 security findings (S1–S6)
9. Add migrations and a pytest suite
10. Deploy and document

### 20.7 Implications for the submitted proposal

**This is the most important section for the supervisor conversation.**

The proposal was submitted on 29 September 2026 and commits to FastAPI, PostgreSQL, and Next.js
(§7.2). The codebase implements Flask, SQLite, and Vite. These are not incremental differences —
they are different stacks with no shared runtime.

The proposal's committed stack is therefore **the single largest driver of rework** in this project.
Meeting the proposal as written requires replacing the serving layer wholesale.

Three options, honestly assessed:

| Option | Effort | Risk |
|---|---|---|
| **A. Conform to the proposal** (FastAPI + PostgreSQL + Next.js) | Highest — full backend and frontend rewrite | Low technical risk; matches the submitted document. UI kit and auth logic still transfer. |
| **B. Amend the proposal** to match the existing stack | Lowest | Requires supervisor approval. The proposal would then state Flask + SQLite + Vite, which weakens it against §7.2 as originally written but is honest. |
| **C. Hybrid** — FastAPI + PostgreSQL backend, keep the Vite SPA | Medium | Partially contradicts §7.2's "Next.js". Reduces frontend churn. |

**Recommendation: Option A.** The proposal is the source of truth, the UI kit is portable across
frameworks, and the ML/domain work is required regardless of which option is chosen. The stack
decision changes *when* the AI core can be built, not *whether* it must be.

**Raise this with the supervisor in Sprint 1**, before building. Discovering late that the committed
stack forces a rewrite would be substantially worse than raising it now, when the mitigation is
simply to confirm the plan.

### 20.8 Direct answer

> How far is the current codebase from the proposed project?

**The AI/ML core — the project's defining contribution — has not been started.** What exists is a
generic career-quiz application with a hardcoded response behind an AI-sounding route name.

> What prevents it from satisfying the proposal?

**(1)** A framework/stack mismatch across all three tiers. **(2)** Complete absence of the
Job/Role/Skill domain that the whole system is designed around. **(3)** No update or delete
operations anywhere. **(4)** No machine learning. **(5)** Seven of ten pages rendering fabricated
data. **(6)** A publicly exposed admin panel leaking password hashes.

> What changes are required?

Replace the platform layer, build the domain schema, implement the ML pipeline per §4.2, implement
full CRUD across 9 modules, rewire the frontend, and close the security gaps — in that order, with
the schema decision first because it blocks the most work.

**The existing codebase is a reasonable starting skeleton, not a partial implementation.** Treat it
as a prototype to draw UI patterns and auth logic from, and as a concrete statement of what the
CareerLens system must do differently.

---

*Analysis performed 29 September 2026. Every claim cites a `file:line` reference verified by direct
inspection of the source. Recommendations are labelled as such and are distinct from findings.*
