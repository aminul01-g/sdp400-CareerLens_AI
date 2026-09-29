# Architecture

How CareerLens AI is put together, and why. This is the document to read before
changing anything, because most of the decisions below look arbitrary until you
know what they are defending against.

- [1. The shape of the system](#1-the-shape-of-the-system)
- [2. Layers](#2-layers)
- [3. The purity boundary](#3-the-purity-boundary)
- [4. The matching engine](#4-the-matching-engine)
- [5. The CV pipeline](#5-the-cv-pipeline)
- [6. Data model](#6-data-model)
- [7. Security](#7-security)
- [8. Frontend](#8-frontend)
- [9. Determinism](#9-determinism)
- [10. Deliberate non-choices](#10-deliberate-non-choices)
- [11. Where to look in the code](#11-where-to-look-in-the-code)

---

## 1. The shape of the system

```
┌──────────────────────────────────────────────────────────────────┐
│  Next.js 16 (App Router)                                        │
│  Server components for the shell, client components for the     │
│  interactive islands. Middleware guards the route tree.          │
└────────────────────────────┬─────────────────────────────────────┘
                             │  HTTPS, JSON, bearer token
                             │  CORS restricted to ALLOWED_ORIGINS
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI                                                          │
│                                                                  │
│  api/routes/*      HTTP shape only. No business logic.            │
│         │                                                        │
│         ▼                                                        │
│  services/*          ownership checks, transactions, orchestration│
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐   ┌────────────────────────────────────────┐  │
│  │ models/*     │   │ ml/*                                   │  │
│  │ SQLAlchemy   │   │ PURE. No ORM, no web framework, no I/O  │  │
│  │ (PostgreSQL) │   │ importable without a database           │  │
│  └──────────────┘   └────────────────────────────────────────┘  │
└────────────┬──────────────────────────────────┬──────────────────┘
             │ SQLAlchemy                       │ pure function calls
┌────────────▼─────────────┐        ┌───────────▼──────────────────┐
│ PostgreSQL 16            │        │ data/skills_taxonomy.json    │
│ 15 tables, pg_trgm       │        │ data/job_roles.json          │
└──────────────────────────┘        └──────────────────────────────┘
```

Roughly 10,000 lines of Python across 76 modules, 12,900 lines of TypeScript
across 121 files, and 419 tests in 20 files.

---

## 2. Layers

Dependencies point downwards only. A module may import from a layer below it and
never from one above.

| Layer | Directory | May import | Knows about |
|---|---|---|---|
| HTTP | `app/api/routes/` | services, schemas, deps | Requests, status codes |
| Service | `app/services/` | models, ml, core | Transactions, ownership |
| Domain | `app/models/` | db | Tables |
| Engine | `app/ml/` | `app/ml/` only | Nothing |
| Config | `app/core/` | — | Environment |

**Why routes hold no logic.** A route that decides something is a route that
cannot be reused by the seed scripts, the CLI, or a test without going through
HTTP. Every business decision here lives in a service, and the tests exercise
services directly.

**Why services own the transaction.** `db.commit()` appears in service functions
and nowhere else. A route that commits halfway through leaves a partial write if
the second half raises, and there is no test that reliably catches that.

---

## 3. The purity boundary

`app/ml/` imports **only the standard library and itself**. No SQLAlchemy, no
FastAPI, no `app.models`, no `app.services`, no I/O.

This is enforced, not merely intended. `tests/test_determinism.py` walks the AST
of every file under `app/ml/` and fails on any import outside an explicit
allowlist; `scripts/verify_compliance.py` re-checks it from outside the test
suite.

What it buys:

- The evaluation harness runs with **no database and no services**. That is why
  `python -m app.ml.evaluation` produces byte-identical output on any machine.
- The engine is testable without fixtures. `test_ranker.py` constructs a
  `ProfileSnapshot` and asserts on a list.
- The engine cannot drift toward the schema. Renaming a column does not touch the
  scoring code, because the scoring code has never heard of columns.
- A future move to a trained model is a change *inside* this boundary, not a
  rewrite of it.

The one deliberate exception to "no I/O" is `ml/taxonomy.py`, which reads a JSON
file, and `ml/text_loader.py`, which parses a document. Both are pure functions
of their arguments with the path as a parameter, so a caller can pass text they
already have. They are on the boundary, not across it.

---

## 4. The matching engine

No model is trained and none is loaded at inference time. The engine is a formula
over a curated knowledge base, which is what makes every number in the UI
reconstructable by hand.

```
compatibility = 0.6 * weighted_skill_coverage + 0.4 * tfidf_cosine

weighted_skill_coverage = Σ(weight_i × proficiency_factor_i) / Σ(weight_i)
                        over the skills the role requires

proficiency_factor = (proficiency − 1) / 4        # 1 → 0.0, 5 → 1.0
```

Three consequences worth stating plainly:

**Why coverage is weighted.** A role's requirements carry a weight in (0, 1]
representing how much the role depends on that skill. Dividing by the total
weight means a role with twelve requirements is not penalised for having more of
them than a role with eight. A user missing one skill from a short list is worse
off than a user missing one from a long one, and the normalisation is what
expresses that.

**Why the linear proficiency factor.** It is the simplest assumption that is not
absurd, and it is *inspectable*. A logistic curve would fit "how good is a
three-out-of-five developer" slightly better in the abstract and would be
impossible for a user to check. The honest statement is that the shape is
unvalidated, not that it is right.

**Why cosine similarity on the profile text at all.** Skill overlap alone is a
weak signal: two people with identical skill lists and different goals are not
equally suited to the same role. The text similarity term lets a stated career
goal and project descriptions break ties that coverage cannot. It is deliberately
capped at 0.4 so it can never outvote a clear difference in skills.

### The knowledge base

| File | Contents | Loaded |
|---|---|---|
| `data/skills_taxonomy.json` | 151 skills, 555 declared aliases, 8 categories | At startup, cached |
| `data/job_roles.json` | 82 roles, 16 families, 1,043 weighted requirements | At startup, cached |

Both are seeded into PostgreSQL, which is what the application reads at request
time. The JSON is the source of truth for a rebuild; the database is the source
of truth at runtime. That split exists so the knowledge base is reviewable in a
diff and queryable in SQL.

### Weight tuning

The 0.6/0.4 split is not a guess, but it is also not a measured optimum. The
sweep over 0.5–0.9 plus component-isolation probes at 0.0 and 1.0 is flat across
0.5–0.8: top-3 hit rate is 1.000 at every one of those, dipping only at 0.9 (0.962)
and at the two extremes. Un-guarded, the sweep prefers 0.5/0.5 by
0.039 on top-1 — which is one profile on a 26-profile label set. So
`tuning.recommend()` takes a noise floor of `1/n` and holds the default. Retuning
on a margin the evidence cannot resolve would be a coin toss recorded as a
finding. Full numbers and the threats to validity are in
[`evaluation_report.md`](evaluation_report.md).

---

## 5. The CV pipeline

```
file bytes
    │  size, extension and content-type allowlists
    ▼
stored to disk
    │
    ▼
text extraction            pdfplumber (PDF) | python-docx (DOCX)
    │                      raises rather than returning "" for an image-only PDF
    ▼
normalisation              smart quotes, dashes, whitespace
    │
    ▼
skill detection            spaCy PhraseMatcher, 686 surface forms
    │                      longest match wins on overlap
    ▼
proposals                  resume_detected_skill rows
    │
    ▼  ← the user decides
user_skill rows            tagged source='cv_extracted'
```

Two decisions matter more than the implementation.

**Detection never writes to the profile.** The extractor is a pure function of
`(text, taxonomy)`; it emits proposals, the user confirms a subset, and only then
does anything reach `user_skill`. The invariant "every row in `user_skill` is
user-confirmed" is therefore checkable, and a parsing bug cannot overwrite
something a user typed. `test_extraction_pipeline.py` asserts both the purity of
the function and the absence of a `proficiency` field on a detection.

**The longest match wins.** When an alias and a canonical name overlap — "machine
learning" inside "machine learning engineer" — the longer, more specific match
wins. The short match is discarded rather than producing a spurious second
detection.

OCR is deliberately out of scope. A scanned CV raises a specific error so the UI
can say why, instead of returning empty text and looking like a bug.

---

## 6. Data model

The full diagram is in [`erd.md`](erd.md), generated from the live catalogue. The
shape in one line: **the predecessor's text blobs are now rows.**

| Predecessor | Now | Why |
|---|---|---|
| `profile.skills = "python,sql,ml"` | `user_skill` rows | A proficiency per skill, joinable to role requirements |
| `profile.education` (text) | `education_record` rows | Queryable, and deletable per record |
| `profile.experience` (text) | `project` rows | Carries a tech stack, so it feeds the matcher |
| `guidance_session.result_json` | `recommendation_run` + `recommendation_result` | Both score components persisted, so a past run stays explainable |

`recommendation_result` stores `skill_coverage` and `tfidf_similarity` next to the
combined score. Without them, re-explaining a run from three weeks ago would mean
re-running the engine against a profile that has since changed — which answers a
different question than the one the user is looking at.

`resume_detected_skill` is a separate table from `user_skill` for the reason above.

---

## 7. Security

Ordered by how much they would hurt if wrong.

**The app refuses to start without a real signing key.** `Settings` raises if
`JWT_SECRET_KEY` is missing, under 32 characters, or still the `.env.example`
placeholder in production. The predecessor shipped `SECRET_KEY = 'dev-secret'`,
and swapping one weak default for another would have left the same hole. Failing
at import means a misconfigured deployment is caught before it serves a request.

**Ownership violations return 404, not 403.** A 403 confirms the id exists, which
turns the API into an enumeration oracle. Every user-scoped query filters by
`user_id` in the `WHERE` clause rather than fetching and comparing, so a
forgotten check is a query that returns nothing. `test_ownership.py` covers each
entity.

**Mass assignment is impossible.** The role field is not in any update schema, so
`PATCH /api/auth/me {"role": "admin"}` is silently ignored rather than escalating.
Verified against the running container.

**Uploads are validated three times** — extension, declared content type, and
actual parseability — with a hard byte cap. A file that fails any of them never
reaches the extractor.

**CORS is an allowlist.** An empty `ALLOWED_ORIGINS` means no browser origin is
allowed, which is the correct default for a deployment whose frontend origin is
not yet known.

**A misspelt environment variable warns rather than being ignored in silence.**
`Settings` uses `extra="ignore"` so that platform-injected variables do not break
startup. The cost is that a typo is indistinguishable from an unset variable, so
a boot-time check looks for near-misses and names the variable that was meant.

---

## 8. Frontend

Next.js 16 App Router. Twenty routes, all rendering, no mock data anywhere.

**Route groups mirror the authorisation model.** `(public)`, `(app)` and
`(admin)` are filesystem groups, so `/dashboard` and `/admin/jobs` share a URL
shape while having different layouts, different guards and different data rules.

**The session is mirrored into a cookie.** The Edge middleware that guards routes
cannot reach localStorage, so the token is also written to a cookie the middleware
can read. Middleware only checks *presence*; the server layout revalidates against
the API. Middleware is a fast rejection, not the security boundary — a client
that forges the cookie still gets 401 from the layout's server-side check.

**Data fetching is typed at the boundary.** `src/lib/api/` holds one module per
domain, each with a hand-mirrored TypeScript type per Pydantic model. They are
mirrored by hand rather than generated, because a generated client would let a
schema change reach the browser untyped and unnoticed. The cost is that the
mirrors can drift, which is why server 422 field errors are merged into the same
zod schemas — the server stays the authority.

**Destructive actions confirm.** Delete dialogs on every entity, because a
profile is the only copy of someone's career history.

---

## 9. Determinism

Stated as an acceptance criterion, and enforced in `test_determinism.py`:

- Ranking sorts by `(-compatibility, job_role_id)`, so equal scores resolve the
  same way on every run and in every process.
- TF-IDF is fitted **once per request across all 82 roles**, not per role. Fitting
  per role would make each role's vector space differ and the similarities
  incomparable.
- No `random`, no clock, no `set` iteration in any scoring path.
- The evaluation harness produces byte-identical `report.json` across runs.

The CV fixtures are regenerated by `backend/scripts/make_sample_cvs.py` and
committed, so the pipeline is tested against real parser output rather than a
mock.

---

## 10. Deliberate non-choices

Things a reviewer will reasonably ask about, and the answer.

**No trained classifier.** Proposal §4.2 makes it optional and the reasoning is
recorded in full in the evaluation report. In short: no labelled dataset exists,
a classifier would be unexplainable to a user shown a percentage, and it would be
a single point of silent failure under distribution shift. The cost is that no
learned generalisation is claimed, and that is stated rather than glossed.

**No microservices.** One deployable API and one database. The split that would
matter — engine versus application — already exists as a module boundary, which is
the part that pays off. Separate deployables would add network failure modes and
a distributed transaction to a system whose hardest problem is explaining a score.

**No background job queue.** Measured on the containerised API, ranking all 82
roles takes **4.8 ms**, and a `POST /api/recommendations` request returns in
**47 ms** warm. The first request after a restart takes about **2.5 s**, which is
the spaCy model loading — hence the model's wheel being baked into the image
rather than fetched at boot. A queue would be the right answer at a hundred times
these numbers, and is pure cost now.

**No Redis.** Nothing here needs a cache that a query index cannot serve.

**The learning path is off and optional.** `LLM_ENABLED=false` by default, no key
required to boot, reachable only through one endpoint, and a provider failure
degrades to deterministic local steps with the error logged server-side and never
returned to the client.

---

## 11. Where to look in the code

| Question | Start at |
|---|---|
| How is a score computed? | `app/ml/ranker.py`, then `app/ml/matcher.py` |
| What exactly is the formula? | `app/ml/matcher.py::combined_score` |
| Where do the weights come from? | `app/core/config.py`, `data/job_roles.json` |
| How is a skill extracted from a CV? | `app/ml/extractor.py` |
| How is ownership enforced? | `app/services/*_service.py`, `app/api/deps.py` |
| What is the API surface? | [`api.md`](api.md) — generated from the live schema |
| What does the data look like? | [`erd.md`](erd.md) — generated from the live catalogue |
| How good is the engine, honestly? | [`evaluation_report.md`](evaluation_report.md) |
| How do I run this? | [`deployment.md`](deployment.md) |
| How do I run the tests? | `cd backend && python -m pytest` |
