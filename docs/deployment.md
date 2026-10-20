# Deployment

How to run CareerLens AI in production, and how to run it locally when production
is not available. Written to be followed without reading the code.

- [1. What gets deployed where](#1-what-gets-deployed-where)
- [2. Architecture](#2-architecture)
- [3. Environment variables](#3-environment-variables)
- [4. Deploying the API](#4-deploying-the-api)
- [5. Deploying the frontend](#5-deploying-the-frontend)
- [6. Deploy order](#6-deploy-order)
- [7. Migrations](#7-migrations)
- [8. Seeding](#8-seeding)
- [9. Rollback](#9-rollback)
- [10. Local Docker fallback](#10-local-docker-fallback)
- [11. Verification](#11-verification)
- [12. What is not automated, and why](#12-what-is-not-automated-and-why)

---

## 1. What gets deployed where

| Component | Platform | Entry point | Notes |
|---|---|---|---|
| API | Render web service | `app.main:app` via uvicorn | `backend/render.yaml` |
| Database | Render Postgres 16 | — | Private network, not internet-reachable |
| Frontend | Vercel | Next.js 16 App Router | `frontend/vercel.json` |

The database uses Render's **internal** connection URL. It is not exposed publicly,
so the connection string in the service's environment is not a public secret —
though `JWT_SECRET_KEY` genuinely is, and must be generated per environment.

---

## 2. Architecture

```
                 ┌──────────────────────┐
   browser ──────▶  Vercel (Next.js 16) │  static + SSR, no server state
                 └──────────┬───────────┘
                            │  HTTPS, CORS restricted to the frontend origin
                            ▼
                 ┌──────────────────────┐
                 │  Render web service  │  uvicorn, 2 workers
                 │  FastAPI app.main:app│  /health, /docs, /api/*
                 └──────────┬───────────┘
                            │  Render private network
                            ▼
                 ┌──────────────────────┐
                 │  Render Postgres 16  │  20 tables + alembic_version
                 └──────────────────────┘

  Optional, off by default and off the critical path:
  LLM provider ──(only when LLM_ENABLED=true AND a key is set)──▶ learning path
```

The optional learning path is a single outbound call that turns a skill-gap list
into a short plan. The core product never calls it. See
[`evaluation_report.md`](evaluation_report.md) for why no model is trained at
inference time.

---

## 3. Environment variables

Every variable the API reads is a field of `Settings` in
[`backend/app/core/config.py`](../backend/app/core/config.py). Names are
case-insensitive; the canonical spelling is the lower-case field name.

### Required in production

| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://careerlens:…@dpg-…/careerlens` | Use Render's **internal** URL. |
| `JWT_SECRET_KEY` | `secrets.token_urlsafe(48)` | **≥ 32 characters.** The app refuses to boot otherwise. |
| `ENVIRONMENT` | `production` | Enables the production checks. |
| `ALLOWED_ORIGINS` | `https://careerlens.vercel.app` | Comma-separated. Empty means no browser origin is allowed. |

Generate the signing key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

That yields 64 characters. Never reuse the value from `backend/.env.example`, and
never reuse the development key — a leaked signing key means anyone can mint a
valid session for any account.

### Recommended

| Variable | Default | Notes |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 7 days is `10080`. |
| `DEBUG` | `false` | Must be `false` in production. |
| `LLM_ENABLED` | `false` | Leave `false`. Proposal §4.2 makes it optional. |
| `SKILL_COVERAGE_WEIGHT` | `0.6` | Must sum to 1.0 with `TFIDF_WEIGHT`. |
| `TFIDF_WEIGHT` | `0.4` | See the sweep in the evaluation report. |
| `RATE_LIMIT_ENABLED` | `true` | Per process, not shared across replicas. See the limitations. |
| `RATE_LIMIT_AUTH_REQUESTS` | `10` | Sign-in, registration and password-reset attempts per window. |
| `RATE_LIMIT_AUTH_WINDOW_SECONDS` | `60` | |
| `RATE_LIMIT_GENERATE_REQUESTS` | `30` | Recommendation runs per window. |
| `RATE_LIMIT_UPLOAD_REQUESTS` | `10` | CV uploads per window. |
| `SMTP_HOST` | — | Empty means the message is written to `MAIL_DIR` instead of being sent. **Set it in production**, or the verification and password-reset flows never reach anybody. |
| `SMTP_PORT` | `587` | |
| `SMTP_USERNAME` | — | |
| `SMTP_PASSWORD` | — | |
| `SMTP_USE_TLS` | `true` | |
| `MAIL_FROM` | `no-reply@careerlens.dev` | Must be a domain you can send from, or the mail will be rejected. |
| `PUBLIC_BASE_URL` | `http://localhost:3000` | The front end's public URL. The verification and reset links are built from it, so it must be the address a user can actually open. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Leave `false`. Locking out a user who has not clicked a link in an email reads as a broken product. |
| `FEEDBACK_PRIOR_STRENGTH` | `0.10` | How much the community prior may move a score. `0` switches it off. |
| `FEEDBACK_PRIOR_MIN_SAMPLES` | `5` | How many observations a role needs before its prior is used at all. |
| `LOG_LEVEL` | `INFO` | |
| `LOG_JSON` | `false` | `true` for machine-readable logs. |
| `ADMIN_EMAIL` | — | Read by `scripts/seed_admin.py`, not the API. |
| `ADMIN_PASSWORD` | — | As above. Generate; do not hand-write. |

### A typo will not fail the boot — it will be ignored

`Settings` is configured with `extra="ignore"`, which is deliberate: Render, Vercel
and the shell all inject variables this app has never heard of, and refusing to
start over those would break every deployment.

The cost is that a misspelt setting name is indistinguishable from an unset one,
and the default is silently used. So the app checks at boot and warns:

```
Environment variable ALLOWED_ORIGIN is not read by this application; did you mean ALLOWED_ORIGINS?
```

**Read the boot log.** That warning is the only thing standing between a typo in
`ALLOWED_ORIGINS` and a frontend that mysteriously cannot reach the API.

---

## 4. Deploying the API

1. Create the database and service together:

   ```bash
   cd backend
   render blueprint launch          # creates careerlens-db and careerlens-api
   ```

2. In the Render dashboard, set the variables the blueprint marks `sync: false`:
   `ALLOWED_ORIGINS`, `ADMIN_EMAIL`. `JWT_SECRET_KEY` and `ADMIN_PASSWORD` are set
   to `generateValue: true` and are shown to you once — copy them somewhere safe.

3. Deploy. `render.yaml` runs, in order:

   ```bash
   alembic upgrade head
   python -m scripts.seed_taxonomy
   python -m scripts.seed_job_roles
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

   The `&&` between migration and serve is load-bearing. If the migration fails the
   service does not start, rather than serving traffic against a schema it does not
   understand.

### Why migrations run on boot here, but not in the Dockerfile

Render runs one instance per web service, so there is no second process to race.
The Dockerfile is also used for horizontal scaling, where a second replica booting
at the same moment *would* race — so there, migrations are an explicit step:

```bash
docker run --rm <image> alembic upgrade head
```

### Running the seeds

`seed_taxonomy.py` and `seed_job_roles.py` are idempotent, so running them on
every boot is safe and self-healing: add a skill to `data/skills_taxonomy.json`,
redeploy, and the new skill is there. `seed_admin.py` is idempotent by email and is
*not* in the boot command, because an admin account should be created deliberately
rather than resurrected on every deploy.

### Why `-m scripts.seed_taxonomy` and not `scripts/seed_taxonomy.py`

Running a file by path puts `scripts/` on `sys.path`, not the project root, so
`import app` fails. `-m` runs it as a module with the working directory on the
path. This bit the first deploy attempt.

---

## 5. Deploying the frontend

1. Import the repository into Vercel. Root directory: `frontend`. Framework
   preset: Next.js. `vercel.json` supplies the build command and the security
   headers, so nothing else needs setting.

2. Set one environment variable:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://careerlens-api.onrender.com` |

   `NEXT_PUBLIC_*` values are **inlined at build time**. Setting it after the first
   deploy requires a rebuild, not just a restart. This is the single most common
   way to end up with a frontend still pointing at localhost.

3. Deploy, then set `ALLOWED_ORIGINS` on the API to the Vercel URL and redeploy the
   API. The two must agree; see §12.

---

## 6. Deploy order

Strictly, because each step depends on the previous one existing:

1. Database + API service (Render blueprint).
2. Migrations and seeds (automatic on first boot).
3. Frontend (Vercel), with `NEXT_PUBLIC_API_URL` set.
4. `ALLOWED_ORIGINS` on the API, set to the Vercel URL, then redeploy the API.
5. Verify with §11.

Doing step 4 last is deliberate: the API cannot know the frontend's URL until the
frontend exists, and an API that allows no origins is safe while an API that
allows `*` is not.

---

## 7. Migrations

```bash
cd backend
alembic current                       # what is applied
alembic upgrade head                  # apply everything
alembic history --verbose             # what exists
alembic downgrade -1                  # step back one (see §9)
```

The chain is `0001_infra_and_user` → `0002_domain_schema` → `0003_feedback`.

Never edit an applied migration. Add a new one:

```bash
alembic revision --autogenerate -m "add x to y"
```

---

## 8. Seeding

```bash
cd backend
python -m scripts.seed_taxonomy     # 250 skills, 1,159 aliases
python -m scripts.seed_job_roles    # 100 roles, 1,234 requirements
python -m scripts.seed_admin        # reads ADMIN_EMAIL / ADMIN_PASSWORD
python -m scripts.seed_dev_users    # optional, development only
```

Verify:

```sql
SELECT count(*) FROM skill;       -- 250
SELECT count(*) FROM skill_alias;  -- 1,159
SELECT count(*) FROM job_role;     -- 100
SELECT count(*) FROM job_role_skill; -- 1234
```

`pg_trgm` must exist for the trigram indexes:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## 9. Rollback

**Schema.** Roll back one migration:

```bash
alembic downgrade -1
```

Only do this if the migration is genuinely reversible. If it dropped a column, the
data is gone and the fix is a restore, not a downgrade.

**Application.** Render keeps the previous deploy. Roll back via the dashboard's
*Rollback to this deploy*, or redeploy the previous commit. Because `alembic upgrade
head` runs on boot, a rollback to an older commit does **not** downgrade the schema.
If the newer code requires a newer schema, downgrade the schema explicitly first.

**Frontend.** Vercel keeps every deployment; promote the previous one from the
dashboard. Instant, and independent of the API.

**Seeds.** Seeds are idempotent and additive, so rolling the code back does not need
a seed rollback. If a skill was removed from the JSON, the row remains in the
database; delete it by hand only if you are sure nothing references it.

**The order that matters:** frontend first, then API. A frontend expecting a field
the old API does not return fails loudly in the browser; an API expecting a column
the new frontend does not send usually degrades more gracefully.

---

## 10. Local Docker fallback

Proposal §6.4 requires a local stack as the demo fallback. This is it — no external
account, no network.

```bash
docker compose up -d                              # postgres + api
docker compose up -d postgres pgadmin api          # ...and the GUI on :5050

docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.seed_taxonomy
docker compose run --rm api python -m scripts.seed_job_roles
docker compose run --rm api python -m scripts.seed_admin
```

Then:

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |
| Frontend | `cd frontend && npm run dev` → http://localhost:3000 |

**Rootless Docker.** On a host where the daemon cannot run as root:

```bash
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

If the daemon cannot start at all, install `rootlesskit` and `slirp4netns` and run
`dockerd-rootless.sh`. Keep the image store off `/tmp`: on a host where `/tmp` is a
small tmpfs, a scipy/numpy/spaCy image will exhaust it and fail the build with
`OSError: [Errno 122] Disk quota exceeded`. Point the data root at a real
filesystem:

```bash
export DOCKER_DATA_ROOT=$HOME/.local/share/docker-rootless   # before starting dockerd
```

---

## 11. Verification

Run in this order; each step assumes the previous one.

```bash
# 1. The API is up and can reach its database. "database":"ok" is the part that matters.
curl -s https://<api-host>/health | jq
# {"status":"ok","service":"careerlens-api","version":"1.0.0","database":"ok",…}

# 2. Interactive docs are served.
curl -s -o /dev/null -w '%{http_code}\n' https://<api-host>/docs      # 200

# 3. CORS is restricted to the real frontend origin.
curl -s -i -H 'Origin: https://<frontend-host>' \
     -H 'Origin: https://evil.example' https://<api-host>/api/jobs | grep -i access-control-allow-origin

# 4. The knowledge base is seeded.
curl -s https://<api-host>/api/jobs | jq '.total'          # 100
curl -s https://<api-host>/api/jobs/families | jq 'length' # 21

# 5. Anonymous writes are refused.
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<api-host>/api/recommendations   # 401
```

Then the user journey, on a phone viewport and a desktop viewport:

1. Register → redirected to onboarding.
2. Fill in profile, skills, one project, one education record.
3. Upload a CV → review the detected skills → confirm a subset.
4. Generate recommendations → read the score breakdown.
5. Open the skill gap for the top role.
6. Sign out, sign back in, confirm the profile persisted.
7. Sign in as the admin → open the job-role editor → change a weight → confirm the
   change is reflected in a new recommendation run.

Step 7 is the one that catches a deployment where the API works but the admin
wiring does not.

The offline equivalent of all of the above:

```bash
cd backend && python -m app.ml.evaluation --check
cd ../.. && python scripts/verify_compliance.py
cd backend && python -m pytest -q
cd ../frontend && npm run build && npx eslint .
```

There is also a browser suite, which is the only part of the verification that
exercises the application as a person would use it — the accessibility of every
route in both colour schemes, the keyboard, the layout at 320 CSS pixels, and
the whole journey. It needs the API running:

```bash
# terminal one
cd backend && python -m uvicorn app.main:app --port 8000

# terminal two
cd frontend && npx playwright install chromium   # once
npm run test:e2e
```

The administrator specs are skipped unless `E2E_ADMIN_EMAIL` and
`E2E_ADMIN_PASSWORD` are exported, because a repository should not carry an
administrator's password.

---

## 12. What is not automated, and why

Three things in this document need a human with access to the accounts. They are
listed here rather than left implied, because "it is in the docs" and "it is done"
are very different claims.

| Step | Why it cannot be automated from the repository |
|---|---|
| Creating the Render/Vercel projects | Requires accounts and payment details that must not live in git. |
| Setting `ALLOWED_ORIGINS` to the Vercel URL | The URL does not exist until the frontend is deployed, so the value cannot be known at authoring time. |
| The second-person journey on two viewports | Plan task T167 requires someone who did not build the feature. A test written by the author cannot satisfy it. |

Everything else in this document is verified: the image builds, migrations and
seeds run inside the container, the container reports healthy, `/health` reports
`database: ok`, and registration → CV upload → confirmation → recommendations → skill
gap all work against the containerised API. See
[`IMPLEMENTATION_PROGRESS.md`](../IMPLEMENTATION_PROGRESS.md) for the recorded
evidence.
