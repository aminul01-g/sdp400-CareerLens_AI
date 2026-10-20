# Tutorials

Task-oriented walkthroughs, in the order you are likely to need them. Each one
assumes you have already run [`deployment.md` §10](deployment.md#10-local-docker-fallback)
once and have a working local stack.

- [1. Set up the environment from scratch](#1-set-up-the-environment-from-scratch)
- [2. Run the tests](#2-run-the-tests)
- [3. Add a skill to the taxonomy](#3-add-a-skill-to-the-taxonomy)
- [4. Add a job role](#4-add-a-job-role)
- [5. Change the matching weights](#5-change-the-matching-weights)
- [6. Trace a score from the API to the formula](#6-trace-a-score-from-the-api-to-the-formula)
- [7. Add an API endpoint](#7-add-an-api-endpoint)
- [8. Add a frontend screen](#8-add-a-frontend-screen)
- [9. Change the CV pipeline](#9-change-the-cv-pipeline)
- [10. Regenerate the documentation](#10-regenerate-the-documentation)
- [11. Read the evaluation output](#11-read-the-evaluation-output)
- [12. Deploy](#12-deploy)

---

## 1. Set up the environment from scratch

**Goal: a running API and frontend on your machine, from an empty checkout.**

```bash
git clone <repo> && cd careerlens
```

**Backend.** Python 3.12 exactly — not 3.13, not 3.14. The pin is not
theoretical: `spacy` resolves a multi-minute Rust source build on 3.14 and usually
fails. The reasoning is written out at the top of
[`backend/requirements.txt`](../backend/requirements.txt).

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

**Database.**

```bash
docker compose up -d postgres
docker compose exec postgres psql -U careerlens -d careerlens -c \
  "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

**Configuration.** The app refuses to start without a real signing key, so
generate one:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# paste into JWT_SECRET_KEY in .env
```

**Migrations and data.**

```bash
alembic upgrade head
python -m scripts.seed_taxonomy        # 250 skills, 1,159 aliases
python -m scripts.seed_job_roles       # 100 roles, 1,234 requirements
```

> Use `python -m scripts.seed_x`, **not** `python scripts/seed_x.py`. Run by path,
> Python puts `scripts/` on `sys.path` instead of the project root and
> `import app` fails. This is the single most common stumble here.

**Run it.**

```bash
uvicorn app.main:app --reload
```

Check `http://localhost:8000/health` — you want `"database": "ok"`, not just a 200.
A 200 with a database error is a service that will fail on its first real request.

**Frontend**, in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local            # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

`NEXT_PUBLIC_*` values are inlined **at build time**. Changing one needs a
rebuild, not just a restart.

**Troubleshooting**

| Symptom | Cause |
|---|---|
| `ERROR: Could not find a version that satisfies thinc` | Wrong Python. Use 3.12. |
| `RuntimeError: JWT_SECRET_KEY is not set` | `.env` missing, or the key is under 32 characters. |
| `/health` says `database: error` | Postgres is not up, or `DATABASE_URL` points elsewhere. |
| `relation "skill" does not exist` | Migrations have not run. |
| Frontend loads but every request 4xx | `NEXT_PUBLIC_API_URL` is wrong, or was set after the build. |
| `OSError: [Errno 122] Disk quota exceeded` during a build | The Docker data root is on a small `/tmp`. See [`deployment.md`](deployment.md#10-local-docker-fallback). |

---

## 2. Run the tests

```bash
cd backend
python -m pytest                    # 702 tests, about 200 seconds
python -m pytest tests/test_ranker.py -v
python -m pytest -k "ownership"     # by keyword
python -m pytest --cov=app --cov-report=term-missing
```

The suite needs no running services. It creates its own database
(`careerlens_test`), applies the schema, and tears it down.

**The four checks worth knowing about**, because each exists to catch a specific
real regression:

| Command | What it protects |
|---|---|
| `python -m app.ml.evaluation --check` | Exits non-zero if the top-3 hit rate falls below 0.75. The evaluation is a **gate**, not a number. |
| `python scripts/verify_compliance.py` | 32 repository-level assertions: no legacy code, no tracked secrets, no mock data, ML purity. |
| `python scripts/generate_api_docs.py && git diff --exit-code docs/api.md` | The API reference still matches the routes. |
| `cd frontend && npm run build && npx eslint .` | The frontend still compiles and lints. |

**Linting and types:**

```bash
ruff check app tests scripts
mypy app
```

---

## 3. Add a skill to the taxonomy

**Goal: a new skill appears in the CV extractor's patterns and in the admin UI.**

1. Edit [`backend/data/skills_taxonomy.json`](../backend/data/skills_taxonomy.json):

```json
{
  "name": "Rust",
  "slug": "rust",
  "category": "Programming & Core",
  "description": "Systems programming with strict memory safety.",
  "aliases": ["rust-lang", "rust lang"]
}
```

2. **Every skill needs at least two aliases.** There is a test for it, and it is
   worth satisfying even for an obvious name: `rust` matching the English word
   "rust" or "trusted" is a false positive you will regret.

3. Re-seed and verify:

```bash
python -m scripts.seed_taxonomy
# expect: +1 skills, ~0 updated, +N aliases
```

4. Add a test. Detection is not a guess, so assert it:

```python
def test_rust_is_detected():
    assert {d.slug for d in extract_skills("I write Rust daily.", taxonomy=load())} >= {"rust"}
```

5. Run the full suite. Adding a pattern can change an existing detection —
   `test_extractor.py` has 43 tests that will notice.

The same skill is now immediately available to be attached to a profile and to be
a requirement of a role. The pattern set is built at startup from the loaded
taxonomy, so there is no separate pattern file to keep in sync.

---

## 4. Add a job role

**Goal: a new role appears in `/api/jobs` and can be recommended.**

1. Edit [`backend/data/job_roles.json`](../backend/data/job_roles.json):

```json
{
  "title": "Rust Systems Engineer",
  "slug": "rust-systems-engineer",
  "family": "Software Engineering",
  "seniority": "Mid",
  "min_years_experience": 3,
  "description": "Build memory-safe services and CLIs where predictability matters more than iteration speed.",
  "responsibilities": [
    "Own latency-sensitive services",
    "Keep the unsafe surface small and audited"
  ],
  "skills": [
    { "skill_slug": "rust",        "weight": 1.0  },
    { "skill_slug": "python",      "weight": 0.55 },
    { "skill_slug": "docker",      "weight": 0.6  },
    { "skill_slug": "postgresql",  "weight": 0.5  }
  ]
}
```

2. **The rules, and why they exist:**

| Rule | Reason |
|---|---|
| Weights in (0, 1] | A weight of 0 means "required but irrelevant"; a weight above 1 breaks the normalisation. A database check constraint enforces it, so you find out at seed time. |
| Every `skill_slug` in the taxonomy | A dangling slug raises a hard error — it would silently lower the denominator and *inflate* coverage for that role. |
| 8–18 required skills | Where the knowledge base settled. Enforced by `verify_compliance.py`, not by the API, which accepts as few as one. |
| A non-empty `description` | It is the text the TF-IDF component compares against. An empty description means the role can only ever be matched by skills. |
| `min_years_experience` | The experience the role typically expects. It is display context, and the fallback source for the role's band when `seniority` is blank. The engine derives the band from `seniority` first. |

3. Seed and check:

```bash
python -m scripts.seed_job_roles
curl -s localhost:8000/api/jobs | python -m json.tool | head -20
```

4. **Adding a role changes every user's ranking**, because TF-IDF is fitted across
   the whole candidate set. Re-run the evaluation afterwards:

```bash
python -m app.ml.evaluation --check
```

If the top-3 hit rate drops, the new role is competing with a labelled profile for
a slot. That is a real signal, not noise — investigate before adjusting labels.
**Never change a label to make a number look better.**

Adding a role also changes the **committed evaluation report**, because the
per-family statistics move. The report is a golden artefact: a test regenerates
it and fails if the committed copy differs. So regenerate and commit it in the
same change:

```bash
python -m app.ml.evaluation
```

---

## 5. Change the matching weights

**Goal: shift the balance between skill coverage and text similarity.**

```bash
cd backend
```

1. Edit the default in [`app/core/config.py`](../backend/app/core/config.py):

```python
skill_coverage_weight: float = 0.6
tfidf_weight: float = 0.4
```

2. **They must sum to 1.0.** A validator enforces it at startup:

```
SKILL_COVERAGE_WEIGHT + TFIDF_WEIGHT must equal 1.0 (got 0.6 + 0.5 = 1.1)
```

This is not fussiness. The combined score is a weighted mean of two numbers in
`[0, 1]`; if the weights do not partition that range, the output is not a
percentage and the UI is lying.

3. **Measure before you decide.** Never change a weight on intuition:

```bash
python -m app.ml.evaluation            # prints the metrics and the sweep
```

4. Read the sweep before acting:

- The curve is **flat across 0.5–0.8** (1.000 at each), dipping at 0.9. That is the
  current finding, and it means
  the split is close to a free parameter on this label set.
- A change smaller than `1 / n_profiles` (currently 0.038) is noise. The
  recommendation logic holds the default rather than retune on a margin one
  profile could flip.

5. Update the committed report and the evaluation test's expectations if you do
   change it. `docs/evaluation_report.md` and `report.json` are artefacts; the
   endpoint serves the committed file so the chart cannot disagree with the
   document.

**Environment override, for trying a value without editing code:**

```bash
SKILL_COVERAGE_WEIGHT=0.7 TFIDF_WEIGHT=0.3 uvicorn app.main:app --reload
```

---

## 6. Trace a score from the API to the formula

**Goal: understand exactly how a number in the UI was produced.** This is the
most useful five minutes you can spend in this codebase.

```bash
# 1. Ask for a recommendation and keep the response
curl -s -X POST localhost:8000/api/recommendations \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"limit":3}' | python -m json.tool > /tmp/rec.json
```

Read the path in this order:

| Step | File | What to look for |
|---|---|---|
| 1. Route | `app/api/routes/recommendations.py` | Where the profile is loaded and the result is paginated. No logic. |
| 2. Service | `app/services/recommendation_service.py` | Where ownership is checked, the transaction is opened, and the run is persisted. |
| 3. Snapshot | `app/ml/text_profile.py::build_profile_text` | How the profile becomes the text used for TF-IDF. |
| 4. Rank | `app/ml/ranker.py::rank` | **The one place** all roles are scored. Look for the `(-compatibility, job_role_id)` sort — that is the determinism guarantee. |
| 5. Coverage | `app/ml/matcher.py::weighted_skill_coverage` | The weighted sum and the division by total weight. |
| 6. Similarity | `app/ml/matcher.py::tfidf_cosine` | One vectoriser fitted for all roles, not one per role. |
| 7. Combine | `app/ml/matcher.py::combined_score` | The 0.6/0.4 blend. |

Then reproduce it offline, with no server and no database:

```python
from app.ml.ranker import rank, ProfileSnapshot
from app.ml.types import UserSkillFact
from app.ml.evaluation.harness import load_role_specs, load_taxonomy_index

ids = load_taxonomy_index()
specs = load_role_specs(skill_ids=ids)
skills = (
    UserSkillFact(skill_id=ids["python"], proficiency=5, name="Python", slug="python"),
    UserSkillFact(skill_id=ids["sql"],    proficiency=4, name="SQL",    slug="sql"),
)
result = rank(ProfileSnapshot(user_id=0, skills=skills), specs)[0]
print(result.title, result.compatibility, result.skill_coverage, result.tfidf_similarity)
```

The numbers match the API response exactly. That is not a coincidence — it is the
purity boundary doing its job, and it is the fastest way to convince yourself the
engine is doing what the formula says.

---

## 7. Add an API endpoint

**Goal: a new read endpoint, following the existing conventions.**

1. Decide the layer. Routes hold no logic; if you are writing an `if` in a route,
   it belongs in a service.

2. Add the schema in `app/schemas/`:

```python
class SkillTrendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    added_at: datetime
```

3. Add the service function in `app/services/skill_service.py`. Own the
   transaction and filter by owner:

```python
def skills_added_since(db: Session, user: User, since: datetime) -> list[UserSkill]:
    return list(
        db.scalars(
            select(UserSkill)
            .where(UserSkill.user_id == user.id, UserSkill.created_at >= since)
            .order_by(UserSkill.created_at.desc())
        ).all()
    )
```

The `user_id` filter is not optional. Filtering after fetching turns a forgotten
check into a data leak, and `test_ownership.py` exists to catch exactly that.

4. Add the route in `app/api/routes/`:

```python
@router.get("/skills/recent", response_model=list[SkillTrendRead], summary="Recently added skills")
def recent_skills(since: datetime, db: DbSession, user: CurrentUser) -> Any:
    return skill_service.skills_added_since(db, user, since)
```

`CurrentUser` handles authentication; add `RequireAdmin` if it needs the admin role.

5. **Write the tests before you run them** — the negative cases are the point:

```python
def test_recent_skills_requires_authentication(client):
    assert client.get("/api/skills/recent").status_code == 401

def test_recent_skills_is_scoped_to_the_owner(client, user_client, make_user):
    other = make_user(email="other@example.com")
    ...
    assert all(s["skill_id"] != other_skill for s in user_client.get(...).json())

def test_a_normal_user_is_refused_admin_routes(user_client):
    assert user_client.get("/api/admin/overview").status_code == 403
```

6. Regenerate the API reference, or its test will fail:

```bash
python scripts/generate_api_docs.py
```

That failure is the system working: an undocumented endpoint is invisible to
review, and a documented endpoint that does not exist sends someone to a 404.

---

## 8. Add a frontend screen

**Goal: a new page in the right route group.**

1. **Pick the group.** The filesystem structure is the authorisation model:

| Directory | Access | Layout |
|---|---|---|
| `app/(public)/` | Anyone | Public chrome, no session required |
| `app/(app)/` | Signed in | `src/middleware.ts` guard, plus a server-side session check in the layout |
| `app/(admin)/` | Admin role | As above, plus the admin layout |

```bash
mkdir -p 'frontend/app/(app)/certifications'
```

2. **A server component reads; a client component interacts.** Fetch on the server
   where you can, and keep the client bundle to what genuinely needs state:

```tsx
// app/(app)/certifications/page.tsx  — server component
import { listCertifications } from '@/src/lib/api/certifications';

export default async function Page() {
  const items = await listCertifications();
  return <CertList items={items} />;
}
```

3. **Never fetch in `useEffect`.** The moment a screen renders and then fills in,
   the user sees an empty state that is not true. Use React Query for anything
   that genuinely changes:

```tsx
'use client';
const { data, isLoading, error } = useCertifications();
```

4. **A mutation is a mutation, never a query.** Generating recommendations is a
   `useMutation`, so opening `/recommendations` does not silently burn an engine
   run. Getting this backwards is the most expensive client-side mistake available
   here.

5. Add the hook to `src/lib/api/<domain>.ts`, with the type hand-mirrored from the
   Pydantic model.

6. Every destructive action confirms. A profile is the only copy of someone's
   career history.

7. Verify:

```bash
cd frontend
npx tsc --noEmit
npx eslint .
npm run build
```

`npm run build` matters more than `npm run dev`: the build exercises server
component boundaries and the middleware, which a dev server tolerates.

---

## 9. Change the CV pipeline

**Goal: change how skills are found in an uploaded CV.**

The chain, and where each stage lives:

| Stage | File |
|---|---|
| Allowlist, size cap, storage | `app/services/cv_service.py` |
| PDF/DOCX text extraction | `app/ml/text_loader.py` |
| Normalisation | `app/ml/text_loader.py::normalise_text` |
| Skill matching | `app/ml/extractor.py` |
| Proposals | `app/ml/evaluation/sample_cvs/`, `resume_detected_skill` |
| User confirmation | `app/api/routes/skills.py::confirm_skills` |

**The three rules, and breaking any of them is the mistake:**

1. **Extraction never writes to a profile.** `extract_skills(text, taxonomy)` is a
   pure function. It emits proposals. Only `POST /api/skills/confirm` creates a
   declared skill, tagged `cv_extracted`. `test_extraction_pipeline.py` asserts the
   function's purity by inspecting its signature and its body.

2. **A detection must not carry a proficiency.** Proficiency is a user judgement.
   A detection that arrives with one looks, in the score breakdown, exactly like
   something the user declared. There is a test asserting the field does not exist.

3. **Longest match wins on overlap.** "machine learning" inside "machine learning
   engineer" must produce one detection, not two. Changing this produces
   duplicate-looking proposals and is a real regression, not a cosmetic one.

**After any change:**

```bash
python -m pytest tests/test_extractor.py tests/test_extraction_pipeline.py
```

43 unit tests plus 25 end-to-end tests against three committed sample CVs. If you
change the CV fixtures, regenerate them with
`python scripts/make_sample_cvs.py` — they are committed on purpose, so the
pipeline is tested against real parser output rather than a mock.

**Adding a format** means a new branch in `extract_text`, a new content type in
the allowlist, and a test with a real file of that type. A format that cannot be
parsed should raise a specific error — never return empty text, which the user
cannot distinguish from a bug.

---

## 10. Regenerate the documentation

Two documents are generated, and both have tests that fail when they drift.

```bash
cd backend

# API reference, from the published OpenAPI schema. No database needed.
python scripts/generate_api_docs.py

# ERD, from the live PostgreSQL catalogue. Needs a migrated database.
python scripts/generate_erd.py
```

Then confirm nothing changed unexpectedly:

```bash
git diff --exit-code docs/api.md docs/erd.md
```

A non-empty diff after a route or migration change is the *expected* result — you
just have to look at it. A non-empty diff with no code change means the committed
document was stale.

**What is generated and what is written by hand:**

| Document | Generated from | Why |
|---|---|---|
| `docs/api.md` | Live OpenAPI schema | Hand-written API docs describe the API that existed when someone typed them. |
| `docs/erd.md` | Live catalogue | A hand-drawn diagram drifts within a week of the migration that changed the shape. |
| `docs/evaluation_report.md` | The harness, then committed | The admin chart serves the committed file so it cannot disagree with the document. |
| Everything else | By hand | Judgement, reasoning and limitations are not derivable from the code. |

The generated ones are mechanical on purpose: they contain no opinions, so there
is nothing for a person to add and then have silently overwritten by the next
regeneration.

---

## 11. Read the evaluation output

```bash
cd backend
python -m app.ml.evaluation              # metrics + write both reports
python -m app.ml.evaluation --check      # same, but non-zero exit below target
python -m app.ml.evaluation --no-sweep   # fast, one weight pair
```

```
profiles          : 26
roles             : 82
weights           : 0.6 / 0.4
top-1 accuracy    : 0.692
top-3 hit rate    : 1.000 (target 0.75)
mean reciprocal   : 0.840
mean compat.      : 0.418
recommended split : 0.60 / 0.40 (top-3 1.000, top-1 0.692)
```

**How to read each number:**

- **Top-1** is strict and will look mediocre. That is expected: several profiles
  sit deliberately between two defensible roles.
- **Top-3** is the committed threshold, because three is what the UI shows. A 1.000
  here is *not* a claim of perfect accuracy — see below.
- **Mean reciprocal rank** shows how deep users must look. 0.840 means the average
  user finds the expected role near the top rather than in the tail.
- **Mean compatibility of expected** is the score the expected role actually got.
  A high hit rate on low scores means the shortlist is right and the percentages
  are not trustworthy — two different problems with two different fixes.

**The number not to over-read.** A top-3 of 1.000 is measured against labels
derived from the same knowledge base the engine scores against. It is evidence of a
working implementation and weak evidence of career-advice quality. The full
reasoning is in the *Threats to validity* section of
[`evaluation_report.md`](../docs/evaluation_report.md).

**Reading the sweep.** Top-3 is 1.000 across 0.5–0.8, dipping to 0.962 at 0.9. The
0.0 and 1.0 entries are component-isolation probes — they answer whether each
component is doing any work at all. Both do: coverage alone gives 0.923 top-3 and
text alone 0.808, so neither is carrying the result on its own.

**Never change a label to improve a number.** The labels are the measurement
instrument. If a number looks wrong, the response is to investigate the engine,
not to re-label the case. `tests/test_evaluation.py` checks the label file's
structure precisely so a casual edit is visible.

---

## 12. Deploy

Full instructions, including the environment variable table, the exact deploy
order, migrations, seeding and rollback, are in
[`deployment.md`](deployment.md).

The short version:

```bash
# 1. API + database
cd backend && render blueprint launch

# 2. Set ALLOWED_ORIGINS and ADMIN_EMAIL in the dashboard, then deploy.
#    Migrations and seeds run on boot.

# 3. Frontend, with NEXT_PUBLIC_API_URL set to the API's public URL.
#    Because it is inlined at build time, set it before the first build.

# 4. Now that the frontend exists, set ALLOWED_ORIGINS on the API to its URL
#    and redeploy the API.

# 5. Verify
curl -s https://<api-host>/health | jq
```

Step 4 is last on purpose. An API with no allowed origins is safe; an API
allowing `*` is not.

**Offline fallback**, for the day the deployed instance is unavailable:

```bash
docker compose up -d
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.seed_taxonomy
docker compose run --rm api python -m scripts.seed_job_roles
```
