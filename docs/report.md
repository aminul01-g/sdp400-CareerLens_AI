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
| Work history | `/api/work-history` | `test_cv_sections.py` | Typed or read out of a CV, confirmed before it counts |
| Admin | `/api/admin/*` | `test_crud.py`, `test_ownership.py` | Role-gated, 403 for a normal user |

Non-module additions: authentication (`/api/auth/*`, including verification and
password reset), a public job catalogue, dashboard aggregates, the audit log,
and optional feedback.

**Totals:** 56 paths, 80 operations, 27 screens, 692 tests in 38 files, 92%
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
| Skills | 250, across 14 categories |
| Surface forms | 1,016, normalised from 852 declared aliases |
| Job roles | 100, across 21 families |
| Requirements | 1,234, each weighted in (0, 1] |

Both JSON files are the source of truth for a rebuild; PostgreSQL is the source of
truth at runtime. That split exists so the knowledge base is reviewable in a diff
and queryable in SQL. Seed scripts are idempotent, so adding a skill is a JSON edit
and a re-seed.

### 6.1 Scope beyond the proposal

The proposal describes a system for AI/ML roles, and its §3.4 comparison table
claims "Specialised for AI/ML roles". **The shipped catalogue is wider than
that, deliberately, and this section exists so nobody has to discover it by
counting rows.**

| | Count | |
|---|---|---|
| Skills in the eight original AI/ML categories | 181 | |
| Skills in six later non-technical categories | 69 | Accounting & Finance, Civil & Electrical Engineering, Education & Training, Healthcare & Clinical, Human Resources, Marketing |
| Job roles in the AI/ML families | 92 | including three AI-governance roles |
| Job roles in the seven non-AI/ML families | 8 | Accountant, Financial Analyst, Senior Financial Analyst, Civil Engineer, Quantity Surveyor, Marketing Manager, Secondary School Teacher, Registered Nurse |

The eight non-AI/ML roles are in the catalogue because a catalogue of only AI/ML
roles cannot answer the question a great many students actually have. "Which
AI/ML role fits me?" presupposes that AI/ML is the only field on the table. A
registered nurse, a secondary school teacher and an accountant have career paths
that a skill-gap report is exactly the right tool for, and excluding them would
mean shipping a system that answers the question for a minority of the people
who might use it.

This is a widening, not a replacement. Every role still carries a weighted
requirement set, the matching engine does not know or care which family a role
belongs to, and the AI/ML specialisation is intact where it matters: 92 of the
100 roles, and the whole of the evaluation's 26 labelled profiles, are AI/ML.
The three AI-governance roles — AI Ethics and Governance Specialist, Responsible
AI Auditor, Data Governance Manager — sit on the boundary and are counted with
the AI/ML side, because "responsible AI" is an AI/ML specialism.

What it does mean is that **the proposal's "specialised for AI/ML roles" claim
no longer describes the shipped system in full**, and a reader comparing this
report against the proposal should read that row of §3.4 as "AI/ML, plus
several other fields" rather than "AI/ML only". The alternative — deleting
eight working roles and 69 working skills — would restore the wording at the
cost of the feature, which seemed the worse trade.

The limitation is not only that the catalogue is wider than advertised. It is
also that it is small: 100 roles is a demonstration, not a career taxonomy.
Section 11 covers what that means.

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

702 tests, 92% statement coverage, 0 failures, plus 38 browser tests.

| Area | File | Tests |
|---|---|---|
| CRUD for every module | `test_crud.py` | 36 |
| Context signals (recency, depth, level) | `test_signals.py` | 29 |
| Auth, roles, sessions | `test_auth.py` | 29 |
| Evaluation as a gate | `test_evaluation.py` | 28 |
| Recommendations and explainability | `test_recommendations.py` | 26 |
| Optional LLM path | `test_learning_path.py` | 26 |
| Matching primitives | `test_matcher.py` | 23 |
| CV sections and work history | `test_cv_sections.py` | 23 |
| CV upload and error paths | `test_cv.py` | 22 |
| Email verification and password reset | `test_account.py` | 18 |
| Taxonomy integrity | `test_taxonomy.py` | 17 |
| CV pipeline end to end | `test_extraction_pipeline.py` | 17 |
| Error envelope | `test_error_envelope.py` | 17 |
| Audit log | `test_audit_log.py` | 16 |
| Skill extraction | `test_extractor.py` | 16 |
| Determinism and ML purity | `test_determinism.py` | 15 |
| Feedback loop and the community prior | `test_feedback_loop.py` | 14 |
| Ranking and the total order | `test_ranker.py` | 14 |
| Ownership and IDOR | `test_ownership.py` | 13 |
| Skill-gap analysis | `test_gap_analysis.py` | 13 |
| Context signals over the API | `test_signals_api.py` | 10 |
| Rate limiting | `test_rate_limit.py` | 10 |
| Generated docs cannot drift | `test_api_docs.py`, `test_erd.py` | 17 |

Two properties are enforced as **regression gates** rather than recorded once:

- `python -m app.ml.evaluation --check` exits non-zero below a 0.75 top-3 hit rate.
- `scripts/verify_compliance.py` fails on 32 repository-level violations.

## 10. Two bugs that only running the product found

Both are recorded because the process is the point, and because both had a test
gap that is now closed.

**CV upload returned HTTP 500 in the container.** The upload route creates its
directory at runtime, and `/srv/careerlens` is root-owned while the process is
not. Every test passed and the suite would still have passed, because the tests run
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
build the image, apply all eight migrations, seed, and serve a healthy container.

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
3. **The context signals are self-declared.** Experience, level, per-skill
   recency and per-skill depth are all things the user states, and the engine
   cannot check any of them. The 26-profile evaluation declares none of them, so
   nothing here measures whether they help.
4. **Proficiency is self-reported and biased upward.** A written rubric makes
   "4" mean the same thing to everyone; it does not make it true.
5. **The community prior is thin.** A user can say whether a role is worth
   keeping, and the aggregate moves future rankings by at most 10% — but the
   sample is small, self-selected, and measures interest rather than outcomes.

Also true, and worth stating plainly because the earlier draft of this
report claimed otherwise: the rate limiter is **shared** across workers and
replicas (the counters live in the database, not in a process's memory), the
SMTP transport **is** exercised end to end against a live mail server in the
test suite, and the accessibility checks are **machine-verified** — `axe-core`
over every route in both colour schemes, a keyboard walkthrough of the tab
order, focus indicator, focus trap and focus return, and a reflow check at
320 CSS pixels and at 200% zoom. What has *not* been done is a screen-reader
pass, so no WCAG conformance claim is made; see
[`accessibility-audit.md`](accessibility-audit.md) for exactly what was and
was not checked.

Two limits are worth naming here rather than burying. The rate limiter
counts on the client address, and `X-Forwarded-For` is client-supplied, so
the API believes it only from a proxy listed in `TRUSTED_PROXY_CIDRS`; a
deployment that forgets to set it counts every request from the proxy as one
address, which is the safe direction. And a free Render Postgres expires
after 30 days, so the demonstration database has a shelf life — the
procedure for replacing it is in [`deployment.md`](deployment.md).

The capabilities that were delivered beyond the proposal — the context signals,
a proficiency rubric, section-aware CV extraction, a work history, a community
prior, rate limiting, email verification, password reset and an audit log —
are listed with their evidence in [`compliance-matrix.md`](compliance-matrix.md).

## 13. What we would do next

Ordered by value per unit of effort, and none of it needs new architecture.

1. **Independent labels** from career practitioners or final-year students ranking
   candidate profiles. The largest gap in the project and the smallest amount of
   code. Nothing else on this list improves confidence as much.
2. **A measurement of the new signals.** They are implemented, tested and
   explained, and nothing measures whether they make a shortlist better. That
   needs profiles carrying the extra fields and someone who knows which roles are
   the right ones.
3. **Real usage data.** The instrument now exists — a user can say a role is
   worth keeping — but nobody has used it, and outcome data is the only thing
   that would settle question 1 empirically.
4. **A screen-reader, contrast and reflow pass.** The structural work is done;
   the perceptual work is not, and it is what a WCAG claim would rest on.
5. **A user-journey walkthrough by someone who did not build it**, on a phone and
   a desktop viewport, against the deployed URL. This is required by the plan and
   is blocked only on access to the accounts.

## 14. Compliance

`scripts/verify_compliance.py` runs 34 assertions over the repository: no legacy
Flask code, no tracked secrets, no populated environment templates, no mock data,
no predecessor branding in any source file, and the ML layer's import purity
re-verified from outside the test suite.

`IMPLEMENTATION_PROGRESS.md` records task-by-task status with evidence, including
the two items that remain externally blocked.
