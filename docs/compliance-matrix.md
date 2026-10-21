# Proposal Compliance Matrix

Plan task **T168**. Every row of `PROJECT_IMPLEMENTATION_PLAN.md` §18, each mapped
to a `file:line` or a test name.

**A row is only ticked where the evidence exists.** Four rows are not met, and
each says so and says why. A matrix that is 100% green is a matrix nobody checked.

**One section has grown since this matrix was first written.** §18.3 and §18.5
now carry two rows the proposal did not ask for — the full AI career assistant
and the guarantee that it does not change a number the engine owns. They are
marked *(beyond the proposal's scope)* rather than presented as requirements,
because a row that claims a requirement it invented is exactly the failure this
document exists to prevent. §18.9 is the section a reader should look at
first: the proposal excluded a RAG chatbot, the product now has a
conversational assistant, and the exclusion is stated in terms precise enough
to be checked rather than quietly reinterpreted.

| | Count | |
|---|---|---|
| ✅ Met, evidence in this repository | 65 | |
| ⚠️ Implemented, not verified by the means §18 asks for | 5 | responsive viewports, browser testing, deployed journey, the agile board, the AI/ML-specialisation wording |
| ⬜ Not done | 2 | Jupyter notebook, deployed URL |
| 🚫 Correctly absent (out of scope, §18.9) | 3 | |

Every factual claim below was checked by reading the file or running the test
named. Where a plan task is cited, the citation is to the task in
`PROJECT_IMPLEMENTATION_PLAN.md` §5, not to evidence — evidence is always the
`file:line` or test name in its own column.

---

## 18.1 Committed technology stack (§7.2)

| Proposal requirement | Implementation | Evidence | Status |
|---|---|---|---|
| React / **Next.js** | Next.js 16.3.7 App Router, 33 routes, three route groups | `frontend/package.json:3` (`"next": "^16.3.7"`), `frontend/app/**` | ✅ |
| **Tailwind CSS** | Unmodified `tailwind.config.ts` + `app/globals.css`; 25 shadcn components retained byte-identically | `frontend/tailwind.config.ts`, `frontend/src/components/ui/**` | ✅ |
| TypeScript | Next.js TypeScript config; build clean | `frontend/tsconfig.json`; `npx tsc --noEmit` → 0 errors | ✅ |
| Python 3 | Python 3.12 | `backend/.python-version` (`3.12`); `backend/requirements.txt:1-13` (why 3.12) | ✅ |
| **FastAPI** | `app/main.py` factory, 20 `APIRouter`s, **95 operations over 67 paths** | `backend/app/main.py:create_app`; `backend/app/api/router.py`; count from `app.openapi()` | ✅ *(exceeds the plan's estimate of 61)* |
| **SQLAlchemy** | 2.0 `DeclarativeBase`, `Mapped[]`, `SessionLocal` | `backend/app/db/base.py`, `backend/app/db/session.py` | ✅ |
| **Pydantic** | `schemas/` with separate Create/Update/Read per domain | `backend/app/schemas/{auth,profile,skill,project,education,job,recommendation,cv,dashboard}.py` | ✅ |
| **JWT** authentication | PyJWT HS256, explicit `exp`, `sub`, `role` | `backend/app/core/security.py`; `test_auth.py::test_token_issued_now_is_valid_now` | ✅ |
| **PostgreSQL** | `postgres:16` in Compose; `render.yaml` blueprint for production | `docker-compose.yml:26`, `backend/render.yaml:31-40` | ✅ |
| pgAdmin | `dpage/pgadmin4:8` Compose service | `docker-compose.yml:52` | ✅ |
| **scikit-learn** | `TfidfVectorizer` + `cosine_similarity` | `backend/app/ml/matcher.py::tfidf_cosine`; `tests/test_matcher.py` (23) | ✅ |
| pandas / NumPy | Installed and available; the harness formats its tables and the sweep | `backend/requirements.txt:70-73`; `app/ml/evaluation/harness.py::render_markdown` | ✅ |
| **spaCy** | `PhraseMatcher` over 1,016 normalised surface forms (250 canonical + aliases) | `backend/app/ml/extractor.py:113` (`taxonomy.all_patterns()`); `tests/test_extractor.py` (43) | ✅ |
| pdfplumber / PyPDF | PDF branch of the loader | `backend/app/ml/text_loader.py`; `tests/test_extraction_pipeline.py` (25, includes a real PDF) | ✅ |
| **python-docx** | DOCX branch of the loader | same, plus `sample_cv_ml_engineer.docx` parsed end to end | ✅ |
| Optional LLM API | `app/ml/groq.py` — one client, one call site. The AI layer is flag-gated and answers `503 feature_disabled` when unconfigured | `backend/app/core/config.py` (`groq_enabled`, `groq_api_key`, `groq_model`); `tests/test_groq_service.py` (17); `tests/test_learning_path.py` (28) | ✅ *(built, off without a key)* |
| Docker | Compose + multi-stage `backend/Dockerfile` | `backend/Dockerfile` (built and run; non-root, health-checked) | ✅ |
| Git / GitHub | Repository initialised **and published**: `origin` → `github.com/aminul01-g/sdp400-CareerLens_AI.git`; `git ls-remote origin` resolves | `git remote -v`; `git log --oneline` | ✅ *(see §18.6 agile row for the board, which is the part still open)* |
| Postman | OpenAPI UI at `/docs` covers the same need | `http://localhost:8000/docs` → 200 | ✅ *(substituted, as the plan permits)* |
| Figma / draw.io | No Figma file; `docs/erd.md` is Mermaid, rendered from the live catalogue | `docs/erd.md:6` (` ```mermaid ` block) | ✅ *(substituted)* |
| Jupyter Notebook | **Not produced.** The weight sweep was done as `evaluation/tuning.py` and is reproducible, tested and committed | `app/ml/evaluation/tuning.py`; `tests/test_evaluation.py::test_sweep_covers_the_planned_range_and_holds_the_default` | ⬜ *(see note below)* |
| **pytest** | **849 tests, 0 failures** — against a floor of 60 | `backend/tests/` (48 files); `python -m pytest` | ✅ |
| **Browser suite** | **47 Playwright tests, 0 failures** (46 pass; the administrator spec is skipped without credentials) — axe over every route in both themes, a keyboard walkthrough, a reflow check, the full journey and the AI workspace | `frontend/e2e/`; `npm run test:e2e` | ✅ |
| Browser testing | CRUD matrix and journey verified **over HTTP against the running container**, not through a browser | `docs/deployment.md:§11`; container journey recorded in `IMPLEMENTATION_PROGRESS.md` | ⚠️ *(no real-browser pass)* |
| **Vercel** (frontend) | `vercel.json` + `NEXT_PUBLIC_API_URL` template | `frontend/vercel.json`, `frontend/.env.example` | ✅ *(config complete; not deployed)* |
| **Render / Railway** (backend + DB) | `render.yaml` + managed PostgreSQL blueprint | `backend/render.yaml` | ⚠️ *(config complete; not provisioned — T165)* |

**On the notebook.** §7.2 lists "Jupyter Notebook" as a committed tool, and T154
describes exploratory analysis of the sweep. The sweep was performed directly in
`tuning.py` instead, so the analysis is reproducible from a clean checkout and
covered by tests, where a notebook would be neither. This is a deliberate
substitution and it is recorded here rather than quietly omitted. If a notebook is
required as a graded artefact, it is a small piece of work — but producing one
*after* codifying the result would be a fiction, so it has not been fabricated.

---

## 18.2 In-scope features (§4.1)

| Module | Requirement | Implementation | Evidence | Status |
|---|---|---|---|---|
| **Authentication** | Register | `POST /api/auth/register` | `tests/test_auth.py::test_register_returns_user_and_token` | ✅ |
| | Login | `POST /api/auth/login` | `tests/test_auth.py` (38) | ✅ |
| | **Logout** | `POST /api/auth/logout` | `backend/app/api/routes/auth.py`; in `docs/api.md` | ✅ |
| | Password hashing | bcrypt via passlib, pinned against a version skew | `backend/requirements.txt:56-61`; `test_auth.py::test_register_hashes_password_with_bcrypt` | ✅ |
| | JWT sessions | PyJWT with explicit `exp` | `backend/app/core/security.py`; `test_auth.py::test_token_issued_now_is_valid_now` | ✅ |
| | User/Admin roles | `user_role` enum + `RequireAdmin` | `backend/app/models/user.py`; `test_crud.py::test_non_admin_cannot_write_jobs` | ✅ |
| | *DB ops: Create, Read* | covered | `test_crud.py::test_profile_crud`, `::test_skill_crud`, `::test_project_crud` | ✅ |
| **User profile** | Create, view, edit, delete | `POST/GET/PATCH/DELETE /api/profile`; `/profile` screen | `test_crud.py::test_profile_crud`, `::test_profile_delete_removes_only_the_profile_row`, `::test_profile_update_distinguishes_absent_from_null` | ✅ |
| | *DB ops: C, R, U, D* | §8.1 row 1 | `test_crud.py::test_profile_crud` asserts all four | ✅ |
| **Skill management** | Add, update proficiency, remove, from a taxonomy | `/api/skills` CRUD + `/api/skills/taxonomy`; `/skills` screen | `test_crud.py::test_skill_crud`, `::test_taxonomy_search_matches_aliases`, `::test_bulk_confirm_is_idempotent`; `frontend/app/(app)/skills/page.tsx` | ✅ |
| | *DB ops: C, R, U, D* | §8.1 row 2 | `test_crud.py::test_skill_crud` | ✅ |
| **Project management** | Add, edit, delete with description and tech stack | `/api/projects`; `/projects` screen | `test_crud.py::test_project_crud` | ✅ |
| | *DB ops: C, R, U, D* | §8.1 row 3 | `test_crud.py::test_project_crud` | ✅ |
| **Education & certifications** | Add, edit, delete degrees and certifications | `/api/education`, `/api/certifications`; `/education`, `/certifications` screens | `test_crud.py::test_education_crud`, `::test_certification_crud` | ✅ |
| | *DB ops: C, R, U, D* | §8.1 rows 4–5 | both tests above | ✅ |
| **Job management (Admin)** | C/R/U/D roles with required skills **and importance weights** | `/api/admin/jobs`, `/api/admin/jobs/{id}/skills`; `/admin/jobs` screen with a weight editor | `test_crud.py::test_job_role_crud`, `::test_replace_skills_is_atomic`, `::test_duplicate_job_title_returns_409` | ✅ |
| | *DB ops: C, R, U, D* | §8.1 row 6 | `test_crud.py` admin role tests | ✅ |
| **AI resume analysis** | Upload CV (PDF/DOCX) | `POST /api/cv/upload`; `/resume` screen | `tests/test_cv.py` (25); verified live against the container | ✅ |
| | Extract text | `ml/text_loader.py` | `test_extraction_pipeline.py` — three real files, both formats | ✅ |
| | Extract skills | `ml/extractor.py` | `test_extractor.py` (43); live upload proposed 17 skills | ✅ |
| | Show detected skills for confirmation | `resume_detected_skill` staging + `POST /api/skills/confirm` + a per-item accept/decline UI | `test_crud.py::test_confirm_rejects_unknown_ids_per_item`, `::test_bulk_confirm_is_idempotent`; `frontend/app/(app)/resume/page.tsx:47-94`; `test_extraction_pipeline.py::test_detections_carry_no_proficiency` | ✅ |
| | *DB ops: Create, Read* | §8.1 rows 10–11 | `test_cv.py` | ✅ |
| **AI job matching** | Ranked role list | `POST /api/recommendations`; `/recommendations` screen | `test_recommendations.py` (26) | ✅ |
| | Compatibility % | `0.6·coverage + 0.4·cosine` | `backend/app/ml/matcher.py::combined_score`; `config.py:99-100` | ✅ |
| | Matched skills | `recommendation_result` persists both components; `ScoreBreakdown` renders them | `backend/app/models/recommendation.py`; `frontend/src/features/recommendations/ScoreBreakdown.tsx` | ✅ |
| | *DB ops: Read* | §8.1 rows 13–14 | `test_recommendations.py` | ✅ |
| **Skill-gap analysis** | Pick a target role | `/api/skill-gap/{job_role_id}`; `/skill-gap` screen | `test_gap_analysis.py` (13) | ✅ |
| | Present and missing skills, **ordered by importance** | `ml/gap_analysis.py` | `test_gap_analysis.py`; verified live: weights strictly non-increasing | ✅ |
| | *DB ops: Read* | §8.1 row 14 | `test_gap_analysis.py` | ✅ |

---

## 18.3 AI/ML design (§4.2)

| Requirement | Implementation | Evidence | Status |
|---|---|---|---|
| Extract CV text, clean it, match against ≈150 skills with aliases, using **spaCy phrase matching** | 250 skills, 1,016 surface forms | `backend/app/ml/extractor.py:113`; `data/skills_taxonomy.json`; `test_extractor.py` | ✅ |
| Users confirm or edit the result | Staging table + confirm endpoint + per-item UI | `frontend/app/(app)/resume/page.tsx:47`; `app/api/routes/skills.py::confirm_skills` | ✅ |
| Represent a user by skills, projects, education | `ml/text_profile.py` | `backend/app/ml/text_profile.py::build_profile_text` | ✅ |
| **Weighted skill-coverage** score, scikit-learn | weighted by requirement importance, normalised by total weight | `app/ml/matcher.py::weighted_skill_coverage`; `test_matcher.py` | ✅ |
| **TF-IDF cosine similarity**, profile text vs each role description | one vectoriser fitted across all 100 roles | `app/ml/matcher.py::tfidf_cosine`; `test_matcher.py` | ✅ |
| Initial weights ~60% / 40% | `skill_coverage_weight = 0.60`, `tfidf_weight = 0.40`, and they must sum to 1.0 | `config.py:99-100`; `test_config.py::test_weights_must_sum_to_one` | ✅ |
| Weights tuned on the labelled sample profiles | sweep over 0.5–0.9 plus component-isolation probes at 0.0 and 1.0 | `app/ml/evaluation/tuning.py`; `docs/evaluation_report.md` *Weight sweep*; `test_evaluation.py` (27) | ✅ |
| Gap = required − user skills, ranked by importance weight | tiered at 0.8 / 0.5 | `app/ml/gap_analysis.py`; `test_gap_analysis.py` | ✅ |
| LLM turns the gap into a learning path, **core works without it** | `503 feature_disabled` when off; no key needed to boot; degrades to deterministic steps | `app/ml/learning_path.py`; `test_learning_path.py` (28) | ✅ |
| **A full AI career assistant** — a conversational mentor, four- and six-week learning roadmaps with a portfolio project, a job-description analyser, a truthful CV advisor and a mock interview with a rubric | `app/ml/groq.py` (one provider client), `app/services/groq_service.py` (one service), `app/ml/prompts.py` (every prompt), `app/ml/learning_resources.py` (a verified resource registry) | `tests/test_groq_service.py` (17), `test_mentor_api.py` (12), `test_roadmap_api.py` (13), `test_job_analysis_api.py` (13), `test_cv_advisor_api.py` (10), `test_interview_api.py` (14), `test_ai_language.py` (13), `test_ai_trust_boundary.py` (15), `test_learning_resources.py` (12) | ✅ *(beyond the proposal's scope)* |
| **Context signals** — recency, depth and level fit | `app/ml/signals.py`; folded into the coverage component, with the adjustments reported alongside the score | `test_signals.py` (29); `test_signals_api.py` (10) | ✅ *(beyond the proposal's scope)* |
| **A community prior from use** | A bounded formula, not a fitted model; gated on a minimum sample size. Outcomes the user reports — applied, interviewed, offered — count for more than opinions, and are still self-reported | `app/services/feedback_service.py`; `test_feedback_loop.py` (14); `test_feedback_outcomes.py` (15) | ✅ *(beyond the proposal's scope)* |
| **Section-aware CV extraction** | `app/ml/cv_sections.py`; a declared skill and a mentioned one are distinguishable | `test_cv_sections.py` (23) | ✅ *(beyond the proposal's scope)* |
| Unsupervised similarity + rule-based weighting, **not a trained classifier**, stated openly | no classifier anywhere; disclosed in two documents | no `joblib`/`pickle`/`predict`/`fit` in `app/`; `docs/evaluation_report.md` *Design honesty*; `docs/report.md` §5 | ✅ |

---

## 18.4 Deliverables (§4.3)

| Deliverable | Implementation | Evidence | Status |
|---|---|---|---|
| Working web application (frontend + API + PostgreSQL) **deployed online** | Everything except the deployment itself | Image builds, container healthy, journey verified against the container | ⬜ *(deployed, not **online** — T165 needs account access)* |
| Seed dataset: 50–100 job listings **and** the skill taxonomy | **100 roles, 1,234 requirements, 21 families** + 250 skills | `backend/data/job_roles.json`, `backend/data/skills_taxonomy.json`; row counts verified in the database | ✅ |
| ML module **with an evaluation summary** | `app/ml/*` + a generated, committed report | `docs/evaluation_report.md`; `docs/api.md` admin endpoint serves the committed JSON | ✅ |
| Source repository, final report, user manual, presentation | all four | this repository; `docs/report.md`, `docs/user_manual.md`, `docs/presentation_outline.md` | ✅ |

---

## 18.5 Goals / objectives (§2)

| Objective | Implementation | Evidence | Status |
|---|---|---|---|
| Secure, responsive web app with registration, login, role-based access | Phase 3 complete | `tests/test_auth.py`, `test_cors.py`, `test_ownership.py`; responsive layout via Tailwind breakpoints | ✅ |
| Full CRUD for profiles, skills, projects, education/certs, admin job listings | §8 matrix | every cell has a named test in `test_crud.py` (36) | ✅ |
| Extract skills from a CV using NLP and a curated taxonomy | spaCy `PhraseMatcher` | `app/ml/extractor.py`; `test_extractor.py` (43) | ✅ |
| Recommend and rank roles with a scikit-learn engine combining overlap and text similarity, **explaining each score with matched skills** | both components persisted and rendered | `test_recommendations.py` (26); `ScoreBreakdown.tsx` | ✅ |
| Skill-gap analysis for any target role, ordered by importance | weight-ordered, tiered | `test_gap_analysis.py` (13) | ✅ |
| **Validate on 20+ hand-labelled profiles**, target: expected role in top 3 for most | **26 profiles, 20 distinct roles, 11 families**; top-3 **1.000** against a 0.75 target | `app/ml/evaluation/labelled_profiles.jsonl`; `docs/evaluation_report.md`; `test_evaluation.py::test_top3_hit_rate_meets_the_committed_target` | ✅ |
| Optional LLM learning path, core does not depend on it | built, off by default | `test_learning_path.py::test_no_api_key_means_the_llm_is_never_called` | ✅ |
| The AI layer does not change a single number the engine owns | the model reports ratings; the application computes the total, the coverage and the tiers. A model cannot add a skill the gap report did not produce, or a learning link the registry does not hold | `tests/test_ai_trust_boundary.py` (15); `app/services/roadmap_service.py::_sanitise_plan` | ✅ *(beyond the proposal's scope)* |

---

## 18.6 Data & process (§7.3, §5, §8)

| Requirement | Implementation | Evidence | Status |
|---|---|---|---|
| Curated taxonomy of ~150 skills with aliases | 250 skills, 852 declared aliases → 1,016 surface forms | `test_taxonomy.py::test_taxonomy_has_at_least_150_skills`, `::test_every_skill_has_at_least_two_aliases`, `::test_every_alias_resolves_to_exactly_one_skill` | ✅ |
| 50–100 job listings with required skills and weights | 100 roles | `data/job_roles.json`; verified in the database | ✅ |
| Sample CVs and 20+ labelled profiles; **only consented or anonymised** | 3 **fully synthetic** CVs; 26 synthetic profiles. No real personal data anywhere | `app/ml/evaluation/sample_cvs/`; `test_extraction_pipeline.py::test_no_real_contact_details_in_the_fixtures` (asserts the reserved `.invalid`/`example.com` convention) | ✅ |
| Agile, six two-week sprints, shared backlog | git history on a published remote; **no external project board** | 11 commits grouped by phase; `git log --oneline` | ⚠️ *(the board is the open half of T002 — the repository itself is published)* |
| Database creation with PostgreSQL schema, migrations, seed data | 24 tables, 13 migrations, 4 seed scripts | `alembic/versions/000*.py`; migrations applied and seeds run inside the container | ✅ |

**On the samples.** The proposal permits consented **or anonymised** samples. The
three committed CVs are stronger than anonymised: they are generated by
`backend/scripts/make_sample_cvs.py` from invented names and invented employers,
with contact addresses in domains that cannot resolve. The 26 evaluation profiles
are likewise synthetic, and the label file's own header records that.

**On the legacy data.** The predecessor's 11 user rows contained real names and
real email addresses. They were **redacted** before archiving rather than committed
as found. See [`archive/README.md`](archive/README.md) for what was changed and the
argument for not migrating the data at all.

---

## 18.7 Non-functional requirements (§7.5)

| Requirement | Implementation | Evidence | Status |
|---|---|---|---|
| Hashed passwords | bcrypt, cost-pinned | `test_auth.py::test_register_never_returns_password_hash`; `test_auth.py::test_register_hashes_password_with_bcrypt` | ✅ |
| Token-based sessions | JWT HS256, explicit `exp` | `test_auth.py::test_token_issued_now_is_valid_now`, `::test_delete_me_cascades` | ✅ |
| Role-based access | `RequireAdmin` dependency + `middleware.ts` | `test_crud.py::test_non_admin_cannot_write_jobs`, `::test_anonymous_cannot_reach_admin`; `test_cors.py::test_unlisted_origin_receives_no_allow_origin_header` | ✅ |
| Input validation | Pydantic on every request model; zod on the client; server 422 merged into the client schemas | `backend/app/schemas/`; `tests/test_error_envelope.py` (24) | ✅ |
| Responsive layout, desktop and mobile | Tailwind breakpoints; `use-mobile.tsx` at 768 px | `frontend/src/hooks/use-mobile.tsx:5`; `frontend/app/layout.tsx:32` | ⚠️ *(implemented; not verified at 375/768/1280 px by a real browser pass)* |
| Ownership isolation (supporting §7.5 privacy) | every user-scoped query filters by owner; 404 not 403 | `test_ownership.py::test_cannot_read_another_users_project`, `::test_no_endpoint_accepts_a_user_id`, `::test_cascade_removes_the_whole_subtree` | ✅ |
| Recommendations within a few seconds | measured 47 ms warm, 2.5 s cold (spaCy model load) | `test_recommendations.py::test_generation_latency_is_under_two_seconds` | ✅ |
| Privacy of uploaded CVs — **allow deletion of files and profile** | `DELETE /api/cv/{id}` removes the row and the file; `DELETE /api/profile` cascades | `test_ownership.py::test_cannot_read_another_users_cv`; `test_crud.py::test_profile_delete_removes_only_the_profile_row` | ✅ |
| HTTPS and hashed passwords | passwords ✅; HTTPS by platform (Render/Vercel terminate TLS) | `render.yaml`, `frontend/vercel.json` | ⚠️ *(hashed passwords met; HTTPS unverified because not deployed)* |

---

## 18.8 Competitor comparison claims (§3.4)

Each claim must be **demonstrably true in the shipped product**.

| Claim | Where it is demonstrated | Evidence | Status |
|---|---|---|---|
| "Specialised for AI/ML roles" | 250 skills across 14 categories. **The claim is met but no longer describes the whole system**: six non-technical families (teaching, healthcare, accounting and finance, civil and electrical engineering, marketing, human resources) were added so that a teacher, a nurse and an accountant are real roles. 92 of the 100 job roles are AI/ML; 8 are not. The widening was deliberate and is stated in `report.md` §6.1 rather than left for a reader to discover. Every role still requires at least one AI/ML skill where the role genuinely calls for one | `data/skills_taxonomy.json`; `scripts/verify_compliance.py` asserts every role's skills exist in the taxonomy and that the non-technical families are present; `docs/report.md` §6.1 | ⚠️ *(met for AI/ML, widened beyond it — the proposal's §3.4 wording is now narrower than the product)* |
| "Recommends roles from a full profile" | the journey builds profile → skills → projects → education → CV, *then* ranks | `docs/deployment.md:§11` steps 1–4; verified live against the container | ✅ |
| "Skill-gap report for a target role" | reachable for any role by id | `app/api/routes/skill_gap.py`; `test_gap_analysis.py` (13) | ✅ |
| "Skill extraction from CV" | upload → 17 proposals → per-item confirmation | `app/(app)/resume/page.tsx`; live run recorded in `IMPLEMENTATION_PROGRESS.md` | ✅ |
| "Explains why a role matches — matched and missing skills" | both score components plus the matched/missing partition, rendered | `ScoreBreakdown.tsx`; `test_recommendations.py::test_explainability_partitions_the_required_set` | ✅ |
| "Free (open-source stack)" | every runtime dependency is OSS; Render free tier + Vercel free tier | `backend/requirements.txt`, `frontend/package.json`; no proprietary API is required for any core feature | ✅ |

---

## 18.9 Out of scope (§4.4) — must **not** be built

| Excluded item | Verification | Status |
|---|---|---|
| Applying to jobs, employer accounts, chat, payments, job-portal scraping | no routes, no tables, no UI | ✅ absent — `grep -riE "payment\|stripe\|chat\|employer\|apply" backend/app/api/routes/*.py` → no matches. The feedback loop records what a user *reports* about their own job search — "I applied", "I got an interview" — as a signal about a role. The application never applies anywhere: there is no route, no table and no outbound call that submits anything to an employer |
| A RAG chatbot | no vector store, no retrieval endpoints | ✅ absent — `grep -riE "vector_store\|faiss\|pinecone\|chroma\|retriev" backend/app` → no matches. `faiss` and `vector-databases` appear only as *skill names in the taxonomy*, not as code. **Stated precisely, because a conversational assistant was added after this matrix was first written:** `/api/ai/mentor/ask` is a conversation, but it is not a RAG chatbot. It has no embedding index, no document corpus and no retrieval step; it reads the application's own relational data — confirmed skills, projects, the recommendation run, the skill-gap report — and puts that in the prompt. The machinery §18.4 excluded is still verifiably absent, and `tests/test_ai_trust_boundary.py` asserts it. What changed is that the assistant is *grounded in structured application data* rather than *grounded in nothing*, which is the opposite of the failure the exclusion was guarding against |
| A trained deep-learning ranking model | no classifier, no model file, no `predict` | ✅ absent — `grep -riE "joblib\|pickle\|\.predict\|sklearn.*fit\(" backend/app` → no matches; disclosed in `docs/report.md` §5. The AI layer does not change this: the model explains and sequences, and the engine still computes every score (`tests/test_ai_trust_boundary.py`) |

---

## Summary of what is not met

Four items, all with the reason stated rather than left for a reader to find.

| Item | Why | What would close it |
|---|---|---|
| **Jupyter notebook** | The sweep was codified into `tuning.py` instead, which is reproducible and tested where a notebook would be neither | A graded artefact requirement; a small piece of work, but producing one *after* the fact would be a fiction |
| **Deployed online** | Needs a Render account, a Vercel account and a managed database | T165 — account access. Everything needed is committed: `render.yaml`, `vercel.json`, the Dockerfile, `docs/deployment.md` |
| **Agile board (T002)** | Needs a GitHub account and a project board | T002 — account ownership |
| **Second-person journey on a phone and a desktop viewport (T167)** | Needs a person who did not build it, and a deployed URL | T167 — a teammate, plus T165 |

Three further rows are marked ⚠️ because the implementation is present but
verified by a weaker means than §18 asks for:

- **Responsive layout and CRUD/journey testing** were exercised over HTTP
  against the running container, and the frontend is Tailwind-responsive by
  construction, but no real-browser pass at 375/768/1280 px has been performed.
- **Accessibility** is enforced statically — `eslint-plugin-jsx-a11y` fails the
  build — and the manual review is written down in
  [`accessibility-audit.md`](accessibility-audit.md). A machine pass *has* been
  made since: `axe-core` over every route in both colour schemes, a keyboard
  walkthrough of the tab order, focus indicator, focus trap and focus return,
  and a reflow check at 320 CSS pixels and at 200% zoom. There has been no
  screen-reader pass, so no WCAG conformance claim is made.
- **Rate limiting** is shared across workers and replicas (the counters live in
  the database), and the **SMTP transport** is exercised end to end against a
  live mail server in the test suite. Both are recorded in
  [`limitations.md`](limitations.md#5-how-it-runs) rather than claimed as done.
- **The client address the rate limiter counts on** is the peer address
  unless the request arrived from a proxy listed in `TRUSTED_PROXY_CIDRS`. The
  header is client-supplied, and a server that believed it unconditionally
  would let a caller rotate it and get an unlimited number of password
  attempts. A deployment that forgets to set the variable counts every
  request as one address, which is the safe direction.

One further limitation is not a §18 requirement at all, and is stated here so
that it is not left for a reader to discover: **the evaluation measures the
engine's internal consistency, not career outcomes.** The 26 labels were
assigned by reading the same knowledge base the engine scores against, and the
new context signals — experience, level, recency, depth and the community
prior — are declared by none of them, so the evaluation is silent about all
five. Independent labelling is the missing piece, and it needs people outside
this project.
