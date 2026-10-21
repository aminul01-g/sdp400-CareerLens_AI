# CareerLens AI

An AI-powered job and career recommendation system. Tell it what you can do; it
tells you which of 100 job roles you are a credible candidate for, shows you the
arithmetic behind every percentage, and tells you exactly which skills stand
between you and each one.

An optional **AI career assistant**, powered by Groq, sits on top of that: a
conversational mentor, four- and six-week learning roadmaps with a portfolio
project, a job-description analyser, a truthful CV advisor and a mock interview
with a visible rubric. The assistant explains and sequences; the engine still
decides every number. It is off unless you give it an API key, and nothing in
the core needs it.

Built for SDP400. Runs entirely on your machine with `docker compose up`.

---

## What it does

| | |
|---|---|
| **Nine modules, full CRUD** | Profile, skills, projects, education, certifications, CV, recommendations, skill gap, admin |
| **Knowledge base** | 250 skills resolving 1,016 normalised surface forms from 852 declared aliases; 100 job roles with 1,234 weighted requirements across 21 families |
| **Explainable scoring** | `0.6 × weighted skill coverage + 0.4 × tf-idf cosine`, both components stored and displayed |
| **Context signals** | Experience, level, per-skill recency and depth — so a junior and a principal with the same skills score differently |
| **CV extraction** | PDF and DOCX → skills and work history proposed, section by section → **the user decides** what to accept |
| **Skill gap** | Missing skills in strict weight order, tiered critical → important → desirable |
| **Learns from use** | Say whether a role is worth keeping; the aggregate moves future rankings by at most 10% |
| **Operational** | Rate limiting, email verification, password reset and a full audit log |
| **Evaluation** | 26 hand-labelled profiles; top-3 hit rate 1.000 against a committed threshold of 0.75 |
| **AI career assistant** *(optional)* | A mentor that answers from your own record, learning roadmaps with a portfolio project, a job-description analyser, a CV advisor and a mock interview — in **English or Bangla** |
| **No trained model** | A formula, chosen so every number in the UI can be checked by hand |

### The AI assistant, and what it is not

The assistant is an *enhancement*. It reads the application's own structured
data — your confirmed skills, your projects, your latest recommendation run,
your skill-gap report — and explains it. Three rules hold, and each is a test
rather than a claim:

- **The engine owns every number.** The model reports a rating per rubric
  dimension; the application adds them up. It never produces a compatibility
  score, a tier, or a skill the gap report did not.
- **The model cannot invent a link.** It is shown resource *identifiers* and
  never a URL, and its output schema has no field for one. A learning
  resource comes from a curated registry of 211 verified official documents.
- **The CV advisor cannot invent your history.** It works from your CV and
  your stored records, and where something is missing it asks rather than
  filling the gap.

Without `GROQ_API_KEY` every AI route answers `503 feature_disabled` and the
core is unaffected. The API key is read in one place, never sent to the
browser and never logged.

**No model is trained and none is loaded at inference time.** That is a decision,
not an omission, and it has costs. Both the reasoning and the costs are written
down in [`docs/limitations.md`](docs/limitations.md) and
[`docs/evaluation_report.md`](docs/evaluation_report.md).

---

## Quick start

```bash
# 1. Database + API
docker compose up -d
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.seed_taxonomy
docker compose run --rm api python -m scripts.seed_job_roles
docker compose run --rm api python -m scripts.seed_admin

# 2. Frontend, in another terminal
cd frontend && npm install
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Turning the AI assistant on (optional)

```bash
# backend/.env
GROQ_API_KEY=gsk_...              # from https://console.groq.com/keys
GROQ_MODEL=openai/gpt-oss-120b    # a Groq model with structured-output support
```

Nothing else changes. Without the key the AI screens explain that they are
unavailable and everything else keeps working.

| | |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 (if you started it) |

The seed scripts read `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your environment.
If you have not set them, no admin account is created and the admin section is
simply absent — which is the correct behaviour for a default install.

If you are **not** using Docker, see [`docs/tutorials.md`](docs/tutorials.md#1-set-up-the-environment-from-scratch).

---

## Verifying it works

```bash
cd backend
python -m pytest                      # 847 tests
python -m app.ml.evaluation --check   # the evaluation, as a gate
cd .. && python scripts/verify_compliance.py
cd frontend && npm run build && npx eslint .
```

`verify_compliance.py` runs 37 repository-level assertions: no legacy code, no
tracked secrets, no mock data, no branding leakage, and the ML layer's purity.

There is a browser suite as well. It drives the real application against the
real API, so the API has to be running first:

```bash
cd backend && python -m uvicorn app.main:app --port 8000   # in another terminal
cd frontend && npx playwright install chromium              # once
npm run test:e2e                                            # 47 tests, 1 skipped without admin credentials
```

It checks the accessibility of every route with `axe-core` in both colour
schemes, walks the keyboard, measures the layout at 320 CSS pixels, and
completes the whole journey. The administrator specs are skipped unless
`E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` are set, because a repository
should not contain an administrator's password.

---

## Documentation

| Document | What it is for |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | How it fits together, and why each decision was made |
| [`docs/api.md`](docs/api.md) | API reference — **generated** from the live schema |
| [`docs/erd.md`](docs/erd.md) | Data model — **generated** from the live database |
| [`docs/user_manual.md`](docs/user_manual.md) | Using the product, and troubleshooting it |
| [`docs/tutorials.md`](docs/tutorials.md) | Task-oriented: add a skill, add a role, add an endpoint, add a screen |
| [`docs/evaluation_report.md`](docs/evaluation_report.md) | How good the engine is, and how that number should be read |
| [`docs/limitations.md`](docs/limitations.md) | **What this cannot do** — and what it used not to be able to do |
| [`docs/proficiency-rubric.md`](docs/proficiency-rubric.md) | What a proficiency number means, written down |
| [`docs/accessibility-audit.md`](docs/accessibility-audit.md) | What was checked for accessibility, and what was not |
| [`docs/deployment.md`](docs/deployment.md) | Production deploy, rollback, and the offline fallback |
| [`docs/legacy-freeze.md`](docs/legacy-freeze.md) | The system this replaced, its defects, and why its data was not migrated |
| [`docs/report.md`](docs/report.md) | The final project report |

The two generated documents cannot drift: a test regenerates each and fails if the
committed copy differs. The same applies to the evaluation report, which the admin
UI serves from the committed file so the chart can never disagree with the text.

---

## Project layout

```
backend/
  app/
    api/routes/     HTTP shape only
    services/       Ownership, transactions, orchestration
    models/         SQLAlchemy over PostgreSQL
    ml/             The engine. Pure: no ORM, no framework, no I/O
    core/           Settings, security, logging
  data/             skills_taxonomy.json, job_roles.json — the knowledge base
  alembic/          Migrations
  tests/            38 files, 692 tests
frontend/
  app/              Next.js App Router: (public), (app), (admin)
  src/              components, hooks, lib/api, middleware
docs/               Everything above
scripts/            verify_compliance.py — the repository-level checks
```

The purity boundary in `backend/app/ml/` is enforced, not merely intended: a test
walks its AST and fails on any import outside the standard library. That is what
lets the evaluation run with no database and produce byte-identical output on any
machine.

---

## Technology

**Backend** — Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic,
PostgreSQL 16, spaCy, scikit-learn, PyJWT, bcrypt.

**Frontend** — Next.js 16 (App Router), React 18, TypeScript, TanStack Query,
Tailwind v3, shadcn/ui.

**Infrastructure** — Docker, Docker Compose, Render, Vercel.

Python is pinned to 3.12 for a concrete reason: `spacy` 3.8 has no working wheel
for 3.13/3.14 and the fallback source build usually fails. The full explanation is
at the top of `backend/requirements.txt`.

---

## Engineering

- **847 tests**, ruff and mypy clean.
- **47 browser tests** (Playwright + axe) over the live application — 46 pass;
  the administrator spec is skipped unless `E2E_ADMIN_PASSWORD` is set.
- **Determinism** is a stated acceptance criterion: the same input gives the same
  output on every run, and there is a test for it.
- **The app refuses to start** without a real 32-character signing key, rather than
  falling back to a weak default.
- **Ownership violations return 404, not 403**, so the API is not an enumeration
  oracle.
- **Two bugs that only running the product found** — a container-only upload
  failure and a 404 on an admin endpoint — are documented in
  [`docs/report.md`](docs/report.md) along with the tests that now prevent them.

---

## Licence

Coursework. Not licensed for other use.
