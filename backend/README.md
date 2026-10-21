# CareerLens AI — Backend

FastAPI service for CareerLens AI: the profile store, the CV pipeline, and the
matching engine.

The engine itself lives in [`app/ml/`](app/ml) and imports nothing but the
standard library and itself — no ORM, no web framework, no I/O. That boundary is
what lets the evaluation run with no database and produce identical output on any
machine, and it is enforced by `tests/test_determinism.py` and
`../scripts/verify_compliance.py`.

## Requirements

**Python 3.12, exactly.** Not 3.13, not 3.14. `spacy` 3.8 resolves `thinc` to a
version with no cp313/cp314 wheel, and the fallback is a multi-minute Rust source
build that usually fails. The full reasoning is at the top of
[`requirements.txt`](requirements.txt).

**PostgreSQL 16** with the `pg_trgm` extension. SQLite is not supported: the schema
uses PostgreSQL enums, trigram indexes and `ON DELETE` behaviour that SQLite does
not offer.

**No GPU, and no network at request time for the core.** Every model runs on
CPU and is baked into the image. The *optional* AI layer is the one thing
that reaches the network, and it is off unless a provider key is configured.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

Configuration. The app **refuses to start** without a real signing key, so
generate one before anything else:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET_KEY
```

## Database

```bash
# Either the compose stack…
docker compose up -d postgres
docker compose exec postgres psql -U careerlens -d careerlens -c \
  "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# …or your own PostgreSQL 16.
```

Then:

```bash
alembic upgrade head
python -m scripts.seed_taxonomy       # 250 skills, 1,159 alias surface forms
python -m scripts.seed_job_roles      # 100 roles, 1,234 weighted requirements
python -m scripts.seed_admin          # reads ADMIN_EMAIL / ADMIN_PASSWORD
```

> Use `python -m scripts.seed_x`, **not** `python scripts/seed_x.py`. Run by path,
> Python puts `scripts/` on `sys.path` rather than the project root and
> `import app` fails. This is the most common stumble here.

The seeds are idempotent. Editing `data/skills_taxonomy.json` and re-seeding adds
the new skill without touching the existing ones.

## Run

```bash
uvicorn app.main:app --reload
```

| URL | What |
|---|---|
| `http://localhost:8000/health` | Liveness **and** database readiness |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/openapi.json` | The schema `docs/api.md` is generated from |

Check `/health` says `"database": "ok"`. A 200 with a database error is a service
that will fail on its first real request.

## Tests

```bash
python -m pytest                                  # 847 tests, ~240s
python -m pytest tests/test_ranker.py -v
python -m pytest -k ownership
python -m pytest --cov=app --cov-report=term-missing
ruff check app tests scripts
mypy app
```

No services need to be running. The suite creates `careerlens_test`, applies the
schema, and tears it down.

### The evaluation is a gate, not a number

```bash
python -m app.ml.evaluation --check
```

Prints the metrics and the weight sweep, writes `docs/evaluation_report.md` and
`app/ml/evaluation/report.json`, and **exits non-zero** if the top-3 hit rate falls
below the committed 0.75 threshold. `tests/test_evaluation.py` runs it in-process
so CI fails on a regression rather than on a report nobody reads.

## Layout

```
app/
  api/routes/     HTTP shape only. No business logic.
  services/       Ownership checks, transactions, orchestration.
  models/         SQLAlchemy models over PostgreSQL.
  ml/             The engine. Pure. No ORM, no framework, no I/O.
  core/           Settings, security, logging, exceptions.
  schemas/        Pydantic request and response models.
  schemas/dashboard.py   Real aggregates, not stored numbers.
alembic/          Migrations. Never edit one that has been applied.
data/             The knowledge base. skills_taxonomy.json, job_roles.json,
                  learning_resources.json (211 verified learning resources).
scripts/          Seeds, doc generators, fixture generator.
tests/            47 files, 847 tests.
```

Dependencies point downwards. A route that contains an `if` statement is a route
that cannot be reused by a seed script, a CLI, or a test without going through
HTTP.

## The formula

```
compatibility = 0.6 * weighted_skill_coverage + 0.4 * tfidf_cosine

weighted_skill_coverage = sum(weight_i * proficiency_factor_i) / sum(weight_i)
proficiency_factor      = (proficiency - 1) / 4     # 1 -> 0.0, 5 -> 1.0
```

No model is trained and none is loaded at inference time. This is deliberate per
proposal §4.2: there is no labelled dataset, a classifier could not be explained to
a user who is shown a percentage, and it would be a single point of silent failure
under distribution shift. The cost is that no *learned* generalisation is claimed,
and that is stated rather than glossed — see
[`../docs/limitations.md`](../docs/limitations.md).

## Adding a skill or a role

Both are JSON edits plus a re-seed, and both have tutorials with the full rules:
[add a skill](../docs/tutorials.md#3-add-a-skill-to-the-taxonomy) and
[add a job role](../docs/tutorials.md#4-add-a-job-role).

Adding a role changes every user's ranking, because TF-IDF is fitted across the
whole candidate set. Re-run the evaluation afterwards.

## Security notes

- The app **refuses to boot** if `JWT_SECRET_KEY` is missing, under 32 characters,
  or still the `.env.example` placeholder in production.
- Ownership violations return **404, not 403** — a 403 confirms the id exists,
  which turns the API into an enumeration oracle.
- The `role` field is in no update schema, so `PATCH /api/auth/me {"role":"admin"}`
  is ignored rather than escalating.
- Password hashes are never returned. A test asserts the string `password` does
  not appear in a registration response.
- `Settings` warns at boot about a misspelt environment variable, because
  `extra="ignore"` would otherwise make a typo indistinguishable from an unset
  value. **Read the boot log.**

## Documentation

| Document | Where |
|---|---|
| Architecture and the reasoning behind it | [`../docs/architecture.md`](../docs/architecture.md) |
| API reference — **generated** from the live schema | [`../docs/api.md`](../docs/api.md) |
| ERD — **generated** from the live catalogue | [`../docs/erd.md`](../docs/erd.md) |
| Evaluation, with threats to validity | [`../docs/evaluation_report.md`](../docs/evaluation_report.md) |
| Deployment, including the offline fallback | [`../docs/deployment.md`](../docs/deployment.md) |
| Task-oriented tutorials | [`../docs/tutorials.md`](../docs/tutorials.md) |
| What this cannot do | [`../docs/limitations.md`](../docs/limitations.md) |
| What a proficiency number means | [`../docs/proficiency-rubric.md`](../docs/proficiency-rubric.md) |
| What was checked for accessibility, and what was not | [`../docs/accessibility-audit.md`](../docs/accessibility-audit.md) |
| The legacy tree we replaced, and why | [`../docs/legacy-freeze.md`](../docs/legacy-freeze.md) |

## Regenerating the generated documents

```bash
python scripts/generate_api_docs.py    # docs/api.md  — no database needed
python scripts/generate_erd.py         # docs/erd.md   — needs a migrated database
```

`tests/test_api_docs.py` and `tests/test_erd.py` fail if either is stale.

## The optional AI layer

`app/ml/groq.py` is the **only** place in the application that opens a
connection to a model provider. `app/services/groq_service.py` is the only
place that calls it, and it is the only thing the five AI features have in
common.

| | |
|---|---|
| `GET /api/ai/status` | Whether the provider is configured, and which model answers. Never the key |
| `POST /api/ai/mentor/ask` | A conversational mentor, grounded in your confirmed skills, projects, latest run and gap report |
| `POST /api/ai/roadmaps` | A four- or six-week plan for a role, with a portfolio project, tasks and checkable completion criteria |
| `PATCH /api/ai/roadmaps/{id}/tasks/{key}` | Progress, notes and a portfolio link — recorded beside the plan, never inside it |
| `POST /api/ai/job-analysis` | Reads a pasted job description, normalises its skills against the taxonomy, and compares them with your profile |
| `POST /api/ai/cv-advice` | Suggests how to present an analysed CV more clearly, without inventing anything |
| `POST /api/ai/interviews` | A mock interview with rubric-scored feedback, saved for later |

### Configuration

```bash
GROQ_API_KEY=gsk_...              # from https://console.groq.com/keys
GROQ_MODEL=openai/gpt-oss-120b    # a Groq model with structured-output support
```

The key is read in `app/core/config.py` and nowhere else. It is never sent to
the browser, never logged, and never included in a response — three checks in
`../scripts/verify_compliance.py` and `tests/test_groq_service.py` say so.

Without a key every route above answers `503 feature_disabled`, the interface
shows an honest "not enabled on this deployment" panel, and the rest of the
application is unaffected.

### What the model is and is not allowed to do

The boundary is enforced in code, not by prompt wording:

- **It never computes a number the engine owns.** The job analyser computes
  the coverage with `app/ml/matcher.py`, the same function the ranker uses. The
  model only says *which* skills a description wants.
- **It never adds a skill the gap report did not produce.** A roadmap task
  naming a skill outside the verified gap set has its `skill_slug` cleared
  (`app/services/roadmap_service.py::_sanitise_plan`).
- **It never produces a link.** It is shown resource *identifiers* and never a
  URL, and its output schema has no field for one. A link comes from
  `data/learning_resources.json`, and an identifier the registry does not hold
  resolves to nothing.
- **It never overwrites a verified fact.** Suggestions are a separate list; the
  CV, the skills and the scores are untouched.
- **It is told when the record is thin.** The mentor reports what it used and
  what was missing.

`tests/test_ai_trust_boundary.py` asserts all of this against the live code.

### Untrusted documents

A CV and a job description are *data*, not instructions. Both are wrapped in an
`<untrusted_…>` block with an explicit statement that the contents cannot
change the rules, and the prompt says plainly that nothing may be invented.
`tests/test_cv_advisor_api.py` and `tests/test_job_analysis_api.py` cover it.
