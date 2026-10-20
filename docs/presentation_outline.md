# Presentation Outline

A 15-minute walkthrough with speaker notes. The order is deliberate: the
honest-weakness slide lands *after* the results, so the audience has seen the
system work before they hear where it falls short, and the final slide is the
limitation that matters most rather than a thank-you.

Timings are cumulative. If you are short on time, cut §7 (learning path) and §9
(future work), never §6 or §8.

---

## Slide 1 — Title (0:00)

**CareerLens AI: an AI-powered job and career recommendation system**

- Team, course, date
- One line: *a system that tells you which roles you are a credible candidate for,
  and exactly which skills stand between you and each one.*

Do not start with the technology. Start with the user's problem.

---

## Slide 2 — The problem (0:45)

A graduate with a CV full of tools has no way to answer three questions:

1. Which of the 100 roles in our taxonomy am I actually a candidate for?
2. Why that role and not the one next to it?
3. What is the single highest-value thing I could learn next?

Spreadsheets and job boards answer none of them. A score without an explanation
answers none of them either — and that second failure is the common one.

**Say:** "The hard part is not ranking. It is being able to justify the ranking."

---

## Slide 3 — Requirements → what we built (1:30)

| Proposal requirement | Where it lives |
|---|---|
| Nine modules, full CRUD | Profile, skills, projects, education, certifications, CV, recommendations, skill gap, admin |
| Weighted skill matching | 100 roles, 1,234 weighted requirements |
| Explainable scoring | Both components stored and shown |
| CV extraction with confirmation | PDF/DOCX → proposals → user accepts |
| 20+ labelled evaluation profiles | 26 profiles, top-3 hit rate 1.000 |
| Local demo fallback | `docker compose up` |

**Nine modules, 67 API operations, 20 screens.** Those are the numbers to say out
loud; the table is for the handout.

---

## Slide 4 — Architecture (2:30)

Show `docs/architecture.md`. The one idea to land:

> The engine (`app/ml/`) imports nothing but the standard library and itself. It
> cannot see the database or the web framework.

**Why that matters, concretely:** the evaluation runs with no services at all,
which is why it produces byte-identical output on any machine and why the engine
can be tested without a single fixture.

Then the request path in one line:
`Next.js → FastAPI route → service (ownership + transaction) → engine or database`.

---

## Slide 5 — The matching engine (4:00)

Put the formula on the screen. All of it.

```
compatibility = 0.6 × weighted_skill_coverage + 0.4 × tfidf_cosine

weighted_skill_coverage = Σ(weight × strength) / Σ(weight)
strength                = proficiency_factor × recency_factor × depth_factor
proficiency_factor      = (proficiency − 1) / 4
```

and the coverage component is then scaled by how close the user's level is to
the role's:

```
compatibility = 0.6 × (weighted_skill_coverage × level_fit) + 0.4 × tfidf_cosine
```

`recency_factor`, `depth_factor` and `level_fit` are all **1.000 when the user
has not stated anything**, so a profile that fills in none of the extra fields
scores exactly what it scored before any of this existed.

Three points, in this order:

1. **No model is trained.** This is per proposal §4.2, and it is a decision, not
   an omission. No labelled dataset exists; a classifier could not be explained to
   a user shown a percentage; and it would be a single point of silent failure.
2. **Explainability is free.** Because it is arithmetic, the UI can show a reader
   how 63% was produced, and they can check it. A classifier could only show a
   number and assert it.
3. **Text similarity is capped at 0.4** so it can break ties between equally
   skilled candidates but never outvote a real difference in skills.
4. **The context signals are bounded.** A stale *and* shallow skill keeps at
   least 70% of its strength; a level mismatch costs at most 35%. The signals
   reorder, they never exclude.

**If asked "why not machine learning?"** — that is slide 8. Say so and move on;
do not defend it twice.

---

## Slide 6 — Explainability in the product (5:30)

*Live demo, or screenshots. This is the strongest thing we have.*

1. Open the profile, show a handful of skills with proficiencies.
2. Generate recommendations.
3. Open the score breakdown: both components, both weights, the arithmetic.
4. Open the skill gap: missing skills in strict weight order, tiered critical →
   important → desirable.

**The line to say:** "The gap list is sorted by weight, so the first item is
literally the highest-value thing this person can learn next. No interpretation
required."

---

## Slide 7 — CV extraction (6:30)

Show the pipeline: PDF/DOCX → text → 686 surface forms matched → **proposals** →
user accepts a subset.

**The point to make:** detection never writes to the profile. Proposals live in
their own table, and only a user's confirmation creates a declared skill. So the
invariant *"every skill on a profile is user-confirmed"* is checkable, and a
parsing bug cannot overwrite something someone typed by hand.

Then the honest limitation in the same breath: no OCR, no layout understanding, it
is a phrase matcher and will propose a skill named in passing. That is exactly why
the confirmation step exists.

*(Optional — cut if short on time.)*

---

## Slide 8 — Evaluation, honestly (8:00)

The numbers, from `docs/evaluation_report.md`:

| Metric | Value |
|---|---|
| Top-1 accuracy | 0.692 |
| **Top-3 hit rate** | **1.000** (target ≥ 0.75) |
| Mean reciprocal rank | 0.840 |
| Labelled profiles | 26 across 20 roles and 11 families |
| Weight sweep | 1.000 top-3 across 0.5–0.8; the default was held |

Then immediately, unprompted, the two things that make 1.000 less impressive than
it sounds:

- **The labels are not independent.** They were assigned by reading the same
  required-skill sets the engine scores against. So this measures internal
  consistency, not career-advice quality.
- **Top-3 = 1.000 is a floor, not a ceiling.** The label set deliberately includes
  near-boundary profiles, a four-skill sparse profile, and a backend profile with
  no AI/ML skill at all.

**And the weight tuning result**, because it is the most interesting thing on the
slide: the un-guarded sweep prefers 0.5/0.5 by +0.039 on top-1 — which is *one
profile on a 26-profile set*. So the code holds 0.6/0.4 rather than retuning on a
margin the data cannot resolve.

**Say:** "We wrote a test that fails the build if the top-3 rate drops below
0.75. It is a regression gate, not a number someone read once."

---

## Slide 9 — What we did not build (9:30)

Say this before anyone asks.

- **The LLM learning path is implemented but disabled.** Optional per the
  proposal. No key is needed to boot, it is reachable from one endpoint, and it
  degrades to deterministic local steps when a provider is unavailable.
- **No email verification or password reset.** A real gap, and it is in the
  limitations document.
- **No mobile app.** The web app works on a phone viewport; that is not the same
  thing.
- **No experience, recency or seniority modelling.** See slide 10.

---

## Slide 10 — Limitations (10:30)

The honest list, largest first. Do not soften it; a limitation you raise yourself
is worth more than one you get caught on.

1. **The recommendations are not career advice.** No labour-market data. A 92% is
   a similarity score, not a job offer.
2. **The evaluation is circular.** Covered on slide 8. And it is *more* circular
   now: the engine reads five signals the 26 profiles declare none of, so the
   evaluation is silent about all five.
3. **The new signals are self-declared.** Experience, level, recency and depth
   are all things the user states. A junior and a principal with the same
   declared skills now score differently — but the engine cannot check that the
   claim is true, and nothing here measures whether the signals help.
4. **Proficiency is self-reported and biased upward.** There is a rubric now, so
   "4" means the same thing to everyone. It does not make it true.
5. **250 skills and 100 roles** is a demonstration taxonomy, not a career
   taxonomy.
6. **The community prior is thin.** A user can say a role is worth keeping and
   the aggregate moves future rankings by at most 10% — but the sample is small,
   self-selected, and measures interest rather than outcomes.

**Say what was closed**, because the list above is only credible if the
improvements are stated too: the experience, level, recency and depth signals; a
written proficiency rubric; section-aware CV extraction and a work history read
out of the document; a bounded community prior; rate limiting; email
verification and password reset; and an audit log. All of it is in
`docs/limitations.md` with the test that proves it.

**The line to say:** "If you want one number to judge this project by: the
evaluation proves the engine does what we said. It does not prove the role
definitions are right. Getting that right needs labels from outside this project,
and we know exactly who should provide them."

---

## Slide 11 — Engineering (12:00)

- **702 tests, 0 failures.** 92% statement coverage, plus 38 browser tests.
- **Security:** refuses to boot without a 32-character signing key; ownership
  violations return 404, not 403, so the API is not an enumeration oracle;
  mass assignment of `role` is impossible.
- **Determinism:** the same input produces the same output on every run, and
  there is a test for it.
- **The documentation cannot lie:** `docs/api.md` and `docs/erd.md` are generated
  from the live schema, and tests fail if they drift.

Two bugs worth mentioning, because they show the process working:

- The admin evaluation endpoint 404'd in a container. It pointed at a file the
  build never produced, and **no test caught it** because every test stopped at
  the 401. Found by building the image and clicking through the product.
- The startup warning for a misspelt environment variable was being swallowed,
  because the logging configuration was not idempotent and a repeat call
  disabled the logger.

**Say:** "Neither was found by reading the code. Both were found by running the
thing, and each one now has a test."

---

## Slide 12 — Deployment and the demo fallback (13:00)

- API on Render, database on Render Postgres (private network), frontend on
  Vercel.
- Migrations run on boot and the service refuses to start if they fail.
- **`docker compose up` runs the whole thing locally with no account** — the
  offline fallback the proposal asks for, which is also what you use if the
  deployed instance is down on the day.

---

## Slide 13 — What we would do next (14:00)

Ordered by value per unit of effort, and be specific:

1. **Independent labels** from career practitioners. The largest gap, and it
   needs no new code.
2. **A measurement of the new signals.** They are implemented, tested and
   explained, and nothing measures whether they make a shortlist better.
3. **Real usage data.** The instrument now exists — a user can say a role is
   worth keeping — but nobody has used it, and outcome data is the only thing
   that would settle question 1 empirically.
4. **A screen-reader, contrast and reflow pass.** The structural accessibility
   work is done and linted; the perceptual work is not, and it is what a WCAG
   claim would rest on.

---

## Slide 14 — Questions (15:00)

Anticipated, with the honest answer ready:

| Likely question | Answer |
|---|---|
| "Why not train a model?" | No labelled data. §4.2 makes it optional. We chose explainability, and the evaluation documents what that costs. |
| "Top-3 of 1.000 — isn't that just testing yourself?" | Yes, partly. The labels come from the same knowledge base. That is the single biggest limitation and we have said so. |
| "How do you know the weights are right?" | We do not know they are optimal. The sweep is flat, so we held the default rather than retune on noise. |
| "What if a user lies about their skills?" | Nothing detects it. It is a self-assessment tool, not a credential check. The same is true of the years of experience and the level — they are stated, not verified. |
| "How does the system know anything the user did not type?" | It does not. Every signal the engine reads beyond declared proficiency is either stated by the user or read out of a document the user supplied, and the latter is confirmed by them before it counts. |
| "Is it a trained model that got better with more data?" | No. It is a formula, and the one thing that is learned — the community prior — is a bounded ratio of saves to dismissals, capped at a 10% effect and switched off below five observations. |
| "Is the data safe?" | bcrypt hashes, per-user ownership, cascade delete, CV never exposed to another user, and admin responses never contain a password hash. There are tests for each. |
| "Does it work offline?" | Yes — `docker compose up`. |

---

## Appendix — artefacts to have open

| Artefact | Use |
|---|---|
| `docs/architecture.md` | Slides 4–5 |
| `docs/evaluation_report.md` | Slide 8, and the honesty slide |
| `docs/erd.md` | Slide 4, if asked about the data model |
| `docs/limitations.md` | Slide 10 — the source of every claim there |
| `docs/api.md` | Slide 3, if asked about scope |
| Live demo | Slides 6–7. **Pre-register the account; do not register live.** |
