# CareerLens AI — Project Report

SDP400 Software Development Project.

**Product:** an AI-powered job and career recommendation system. A user builds a
profile, optionally uploads a CV, and receives a ranked shortlist of job roles with
the arithmetic behind every percentage and an ordered list of the skills standing
between them and each role.

---

## 1. Problem statement

Someone with a CV full of tools cannot answer three questions:

1. **Which roles am I actually a candidate for?** Not "which titles contain words
   from my CV" — which of the plausible career directions do I meet the
   requirements for?
2. **Why that role and not the one beside it?** A bare ranking is not actionable.
   A score nobody can interrogate is worse than no score, because it invites trust
   it has not earned.
3. **What is the single highest-value thing I could learn next?** Career advice
   that says "improve your skills" is not advice.

The predecessor application attempted this with a Flask backend, a Vite React
frontend, and a job list. It had hardcoded statistics presented as real
(`mockStats`, a fabricated `12,847` professionals, a `94%` match rate that was a
literal), a text-blob data model, an LLM integration that returned provider error
text to the browser, and authentication that fell back to `SECRET_KEY =
'dev-secret'`. It is described in full in
[`legacy-freeze.md`](legacy-freeze.md), and its defects are the reason several
decisions below look the way they do.

## 2. Requirements → what was built

Every clause of the proposal's §4.1 modules, with evidence.

| Module | Routes | Tests | Evidence |
|---|---|---|---|
| Profile | `POST/GET/PATCH/DELETE /api/profile` | `test_crud.py::test_profile_crud` | One profile per user, ownership-scoped |
| Skills | `POST/GET/PATCH/DELETE /api/skills`, `/api/skills/confirm` | `test_crud.py::test_skill_crud` | Full CRUD plus the CV confirmation gate |
| Projects | `/api/projects` | `test_crud.py::test_project_crud` | Tech stack matched against the taxonomy |
| Education | `/api/education` | `test_crud.py::test_education_crud` | One row per qualification |
| Certifications | `/api/certifications` | `test_crud.py::test_certification_crud` | One row per certification |
| CV | `/api/cv/upload`, `/api/cv/{id}`, `/api/cv/{id}/text` | `test_cv.py`, `test_extraction_pipeline.py` | PDF and DOCX, proposals only |
| Recommendations | `POST /api/recommendations`, `/api/recommendations/runs` | `test_recommendations.py` | Generated once, stored, re-readable |
| Skill gap | `/api/skill-gap/{id}` | `test_gap_analysis.py` | Weight-ordered, tiered |
| Admin | `/api/admin/*` | `test_crud.py`, `test_ownership.py` | Role-gated, 403 for a normal user |

Non-module additions: authentication (`/api/auth/*`), a public job catalogue,
dashboard aggregates, and optional feedback.

**Totals:** 45 paths, 67 operations, 20 screens, 419 tests in 20 files, 92%
statement coverage, ruff and mypy clean.

## 3. Architecture

Full detail in [`architecture.md`](architecture.md). The three decisions that shaped
everything else:

**The engine is a separate, pure layer.** `backend/app/ml/` imports only the
standard library and itself. Enforced by an AST check in
`tests/test_determinism.py` and again by `scripts/verify_compliance.py`. The
evaluation harness therefore runs with no database and no services, which is why it
produces byte-identical output on any machine.

**The data model is normalised.** The predecessor stored skills, education and
experience as delimited strings. They are now rows, which is what makes a
per-skill proficiency and a per-requirement weight possible at all. The full
diagram is in [`erd.md`](erd.md), generated from the live catalogue.

**Score components are persisted.** `recommendation_result` stores `skill_coverage`
and `tfidf_similarity` alongside the combined score, so a run from three weeks ago
stays explainable without re-running the engine against a profile that has since
changed.

## 4. The matching method

```
compatibility = 0.6 * weighted_skill_coverage + 0.4 * tfidf_cosine

weighted_skill_coverage = Σ(weight_i * proficiency_factor_i) / Σ(weight_i)
                        over the role's required skills

proficiency_factor = (proficiency − 1) / 4       # 1 → 0.0, 5 → 1.0
```

**Why the coverage term is normalised by total weight.** A role with twelve
requirements should not penalise a user more than a role with eight for the same
single missing skill. Dividing by the sum of the weights expresses that directly.

**Why a linear proficiency factor.** It is the simplest assumption that is not
absurd, and it is inspectable. A logistic curve would be marginally more
defensible in the abstract and would be impossible for a user to check. The honest
claim is that the shape is unvalidated, not that it is right.

**Why text similarity is capped at 0.4.** It is there to break ties between
equally-skilled candidates whose stated goals differ. It must never be able to
outvote a clear difference in skills, so it cannot.

## 5. Design honesty: no trained classifier

**No model was trained and none is loaded at inference time.** The engine is the
formula above, evaluated over a curated knowledge base.

This is per proposal §4.2, and the reasons are worth stating rather than
defending:

- **There is no labelled dataset.** Any classifier would be trained on
  self-generated labels — the system grading itself.
- **Explainability would be destroyed.** The proposal requires a percentage the
  user can interrogate. A classifier can only produce a number and assert it.
- **It would be a single point of silent failure.** When the distribution shifts,
  a learned model degrades quietly, and nobody notices until users stop trusting
  the output.

**What this costs**, stated as plainly as the benefit:

- No *learned* generalisation is claimed. The engine matches declared skills
  against curated requirements. That is the whole of what it does.
- The system cannot improve from use. A user who corrects a detection leaves no
  trace that affects a future result.
- The linear proficiency factor is unvalidated.
- The evaluation measures internal consistency, not career-advice quality — see §7.

## 6. The knowledge base

| | |
|---|---|
| Skills | 151, across 8 categories |
| Surface forms | 756, normalised from 555 declared aliases |
| Job roles | 82, across 16 families |
| Requirements | 1,043, each weighted in (0, 1] |

Both JSON files are the source of truth for a rebuild; PostgreSQL is the source of
truth at runtime. That split exists so the knowledge base is reviewable in a diff
and queryable in SQL. Seed scripts are idempotent, so adding a skill is a JSON edit
and a re-seed.

## 7. Evaluation

Full numbers, methodology and threats to validity in
[`evaluation_report.md`](evaluation_report.md).

| Metric | Value | Target |
|---|---|---|
| Top-1 accuracy | 0.692 (18/26) | none set |
| **Top-3 hit rate** | **1.000 (26/26)** | ≥ 0.75 — **met** |
| Mean reciprocal rank | 0.840 | none set |
| Mean compatibility of the expected role | 0.418 | none set |

26 profiles across 20 distinct roles and 11 families, against 82 candidate roles.

**The label set was built to be hard**, because a set where everything scores 90%
tests nothing: five near-boundary profiles where a second role is defensible, a
four-skill sparse profile whose top-1 is genuinely uncertain, and a backend profile
with no AI/ML skill at all to check the engine does not drift when that signal is
absent.

**Top-3 = 1.000 is a floor, not a ceiling.** It is measured against labels derived
from the same knowledge base the engine scores against, so it is evidence of a
working implementation and weak evidence of career-advice quality. This is the
single largest limitation of the project and it is stated at the top of the
evaluation report rather than in a footnote.

### Weight tuning

The sweep covers 0.5–0.9 with the complement as the tf-idf weight, plus 0.0 and
1.0 as component-isolation probes.

Top-3 is 1.000 across 0.5–0.8, dipping to 0.962 at 0.9. Un-guarded, the sweep
prefers 0.5/0.5 by +0.038 on top-1 — which is exactly **one profile on a
26-profile set**. So `tuning.recommend()` takes a noise floor of `1/n` and holds
0.6/0.4. Retuning on a margin the label set cannot resolve would be a coin toss
recorded as a finding.

The endpoints answer whether each component works at all, and both do: coverage
alone gives 0.923 top-3, text alone 0.808.

## 8. Security

Ordered by consequence, with the test that pins each.

| Control | Why | Test |
|---|---|---|
| Refuses to boot without a ≥32-character `JWT_SECRET_KEY` | The predecessor fell back to `'dev-secret'`. Swapping one weak default for another leaves the same hole. | `test_config.py::test_short_secret_is_rejected` |
| Ownership violations return 404, not 403 | A 403 confirms the id exists, making the API an enumeration oracle. | `test_ownership.py` (13 tests, one per entity) |
| `role` is in no update schema | `PATCH /api/auth/me {"role":"admin"}` must be ignored, not escalated. | verified against the running container |
| Password hashes never returned | — | `test_auth.py::test_register_never_returns_password_hash` |
| bcrypt at cost 4.0.1 with an explicit pin | passlib 1.7.4 predates bcrypt 4.1+ and warns spuriously on it. | — |
| Uploads checked three ways | Extension, declared content type, and actual parseability, plus a byte cap. | `test_cv.py` |
| Provider error text never returned | The predecessor leaked it at `guidance.py:59`. | `test_learning_path.py::test_provider_error_text_never_reaches_the_caller` |
| CORS is an allowlist; empty means none | A deployment whose frontend origin is unknown is safe by default. | `test_cors.py` |
| No tracked secrets, no populated `.env` templates | — | `scripts/verify_compliance.py` |

The last row of the table above the first: the app **warns at boot** about a
misspelt environment variable, because `extra="ignore"` otherwise makes a typo
indistinguishable from an unset value and silently falls back to the default.

## 9. Testing

419 tests, 92% statement coverage, 0 failures.

| Area | File | Tests |
|---|---|---|
| Skill extraction | `test_extractor.py` | 43 |
| Auth, roles, sessions | `test_auth.py` | 38 |
| CRUD for every module | `test_crud.py` | 36 |
| Optional LLM path | `test_learning_path.py` | 28 |
| Evaluation as a gate | `test_evaluation.py` | 27 |
| Recommendations and explainability | `test_recommendations.py` | 26 |
| CV pipeline end to end | `test_extraction_pipeline.py` | 25 |
| CV upload and error paths | `test_cv.py` | 25 |
| Error envelope | `test_error_envelope.py` | 24 |
| Taxonomy integrity | `test_taxonomy.py` | 22 |
| Ownership and IDOR | `test_ownership.py` | 13 |
| Determinism and ML purity | `test_determinism.py` | 15 |
| Generated docs cannot drift | `test_api_docs.py`, `test_erd.py` | 17 |

Two properties are enforced as **regression gates** rather than recorded once:

- `python -m app.ml.evaluation --check` exits non-zero below a 0.75 top-3 hit rate.
- `scripts/verify_compliance.py` fails on 31 repository-level violations.

## 10. Two bugs that only running the product found

Both are recorded because the process is the point, and because both had a test
gap that is now closed.

**CV upload returned HTTP 500 in the container.** The upload route creates its
directory at runtime, and `/srv/careerlens` is root-owned while the process is
not. 419 tests passed and the suite would still have passed, because the tests run
as a user who can write to the working directory. Found by building the image and
clicking through the product. Fixed by pre-creating the directory owned by the
runtime user and declaring it a `VOLUME`, and covered by
`test_extraction_pipeline.py` asserting the fixtures are real files.

**`/api/admin/evaluation` returned 404 for an admin.** It resolved
`docs/evaluation_report.json`, a file the harness has never written — the JSON goes
to `app/ml/evaluation/report.json` — and the Dockerfile copies no `docs/` directory
at all. No test caught it because every admin-route assertion stopped at the 401,
before the file check was ever reached. Fixed by importing the harness's own path
constant, so there is one source of truth, and by adding tests that get all the way
through to a 200.

A third bug was found by chasing a warning down: `configure_logging()` called
`dictConfig` on every application construction, and repeat application left the
`app.core.config` logger disabled — silently swallowing the misspelt-variable
warning. The function's docstring already promised idempotence. It is now actually
idempotent, with two regression tests.

## 11. Deployment

| Component | Platform | Notes |
|---|---|---|
| API | Render | uvicorn, 2 workers, non-root, health-checked |
| Database | Render Postgres 16 | Private network only |
| Frontend | Vercel | Next.js 16, one build-time variable |

`render.yaml` runs `alembic upgrade head`, then the seeds, then uvicorn — joined
with `&&`, so a failed migration stops the service rather than serving traffic
against a schema it does not understand. The Dockerfile deliberately does not: a
scaled replica would race a second migration, so there it is an explicit step.

The offline fallback required by proposal §6.4 is `docker compose up`, verified to
build the image, apply all three migrations, seed, and serve a healthy container.

Full procedure, environment variable table, deploy order and rollback in
[`deployment.md`](deployment.md).

## 12. Limitations

The full list, with the reasoning, is in [`limitations.md`](limitations.md). The
five that matter most:

1. **The recommendations are not career advice.** No labour-market data. A 92% is
   a similarity score, not a job offer.
2. **The evaluation is circular.** Labels come from the same knowledge base the
   engine scores against. The number measures internal consistency, not career
   quality. Getting a real one needs labels from outside this project.
3. **Skills are the only real signal.** No experience, recency, industry or
   seniority. A junior and a principal engineer with the same declared skills score
   identically. This is the largest engineering gap.
4. **Proficiency is self-reported, coarse, and biased upward.** A 1–5 integer with
   no rubric behind it.
5. **Nothing is learned from use.** No feedback loop, by design, and a real cost.

Also absent: email verification, password reset, rate limiting, an audit log, and
any accessibility audit.

## 13. What we would do next

Ordered by value per unit of effort, and none of it needs new architecture.

1. **Independent labels** from career practitioners or final-year students ranking
   candidate profiles. The largest gap in the project and the smallest amount of
   code. Nothing else on this list improves confidence as much.
2. **A written proficiency rubric**, so "4" means the same thing to everyone and
   the linear factor has something behind it.
3. **Experience and recency.** The two missing signals that most affect whether a
   shortlist is useful in practice.
4. **A real feedback loop**, so the system can improve rather than merely run.
5. **A user-journey walkthrough by someone who did not build it**, on a phone and
   a desktop viewport, against the deployed URL. This is required by the plan and
   is blocked only on access to the accounts.

## 14. Compliance

`scripts/verify_compliance.py` runs 31 assertions over the repository: no legacy
Flask code, no tracked secrets, no populated environment templates, no mock data,
no predecessor branding in any source file, and the ML layer's import purity
re-verified from outside the test suite.

`IMPLEMENTATION_PROGRESS.md` records task-by-task status with evidence, including
the two items that remain externally blocked.
