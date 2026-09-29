# API Reference

Base URL in production: `https://<api-host>`  
Local: `http://localhost:8000`  
Interactive schema: `/docs` (Swagger UI), `/redoc`, `/openapi.json`

**45 paths, 67 operations.** Generated from the live OpenAPI schema by `backend/scripts/generate_api_docs.py`, so this page cannot describe an API the application does not have. Re-run that script after changing a route.

## Conventions

**Errors.** Every error has the same envelope, whatever produced it:

```json
{
  "error": {
    "code": "validation_error",
    "message": "One or more fields are invalid.",
    "errors": [{ "field": "email", "message": "value is not a valid email address" }]
  }
}
```

| Status | `code` | When |
| --- | --- | --- |
| 400 | `bad_request` | Malformed request the schema could not reject. |
| 401 | `unauthorized` | Missing, expired or invalid token. |
| 403 | `forbidden` | Authenticated, but the role is insufficient. |
| 404 | `not_found` | Absent, **or owned by another user**. See below. |
| 409 | `conflict` | Uniqueness violation, e.g. an email already registered. |
| 422 | `validation_error` | Pydantic rejected the body; `errors` is per field. |
| 503 | `feature_disabled` | An optional feature is switched off. |

**Why a 404 and not a 403 for someone else's record.** Returning 403 would confirm the id exists, which turns the API into an enumeration oracle. Every ownership check therefore reports 404, and the tests assert it.

**Authentication.** `Authorization: Bearer <access_token>`. Tokens are JWTs, HS256, valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440).

**Pagination.** List routes accept `limit` and `offset` and return `{items, total, limit, offset}`.

**CORS.** Only the origins in `ALLOWED_ORIGINS` are permitted. An empty value means no browser origin is allowed, which is the safe default.

## Endpoints

### Health

Liveness and readiness. `/health` fails when the database is unreachable.

#### `GET /`

Service banner

- Auth: public
- Success: `200`

#### `GET /api/admin/evaluation`

The committed evaluation report as JSON

- Auth: bearer token
- Success: `200`
- Errors: `404`

Serve the **committed** report rather than re-running the harness.

#### `GET /api/admin/feedback`

Submitted feedback, paged

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `category, page, page_size`

#### `GET /api/admin/health`

Lightweight admin liveness probe

- Auth: bearer token
- Success: `200`

A probe proving the role gate works end to end.

#### `GET /api/admin/jobs`

List every role, including deactivated ones

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, family, is_active, page, page_size`

#### `POST /api/admin/jobs`

Create a job role with its weighted required skills

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `GET /api/admin/jobs/{role_id}`

Get Job Admin

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/admin/jobs/{role_id}`

Update Job

- Auth: bearer token
- Success: `200`
- Errors: `404, 409, 422`

#### `DELETE /api/admin/jobs/{role_id}`

Delete a job role

- Auth: bearer token
- Success: `204`
- Errors: `404, 409, 422`

#### `PUT /api/admin/jobs/{role_id}/skills`

Atomically replace a role's weighted skill set

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `GET /api/admin/overview`

Real system aggregates

- Auth: bearer token
- Success: `200`

#### `GET /api/admin/taxonomy`

Browse the skill taxonomy

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, category, page, page_size`

#### `POST /api/admin/taxonomy`

Add a skill to the taxonomy

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `PATCH /api/admin/taxonomy/{skill_id}`

Update Skill

- Auth: bearer token
- Success: `200`
- Errors: `404, 409, 422`

#### `DELETE /api/admin/taxonomy/{skill_id}`

Delete Skill

- Auth: bearer token
- Success: `204`
- Errors: `404, 409, 422`

#### `GET /api/admin/users`

Paged user list (never includes password_hash)

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `PATCH /api/admin/users/{user_id}/role`

Promote or demote

- Auth: bearer token
- Success: `200`
- Errors: `422`

An admin cannot demote themselves.

#### `POST /api/auth/login`

Exchange credentials for an access token

- Auth: public
- Success: `200`
- Errors: `401, 422`

#### `POST /api/auth/logout`

End the client session

- Auth: bearer token
- Success: `204`
- Errors: `401`

Acknowledge a logout.

#### `GET /api/auth/me`

The authenticated user

- Auth: bearer token
- Success: `200`

#### `PATCH /api/auth/me`

Update name or password

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `DELETE /api/auth/me`

Delete the account and all of its data

- Auth: bearer token
- Success: `204`

Delete the authenticated user.

#### `POST /api/auth/refresh`

Issue a fresh access token

- Auth: bearer token
- Success: `200`
- Errors: `401, 422`

Re-issue a token for a still-valid subject.

#### `POST /api/auth/register`

Create an account and start a session

- Auth: public
- Success: `201`
- Errors: `409, 422`

Register a new user. Returns a token so the session starts immediately.

#### `GET /api/certifications`

The caller's certifications

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/certifications`

Add a certification

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/certifications/{cert_id}`

Get Certification

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/certifications/{cert_id}`

Update Certification

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/certifications/{cert_id}`

Delete Certification

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `GET /api/cv`

The caller's uploads

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/cv/upload`

Upload a CV, extract its text, and detect skills

- Auth: bearer token
- Success: `201`
- Errors: `401, 413, 415, 422`

Extraction runs on upload; nothing is written to ``user_skill`` here.

#### `GET /api/cv/{upload_id}`

One upload with its detected skills

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/cv/{upload_id}`

Delete an upload and the stored file

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

Removes the row **and** the file on disk.

#### `GET /api/cv/{upload_id}/text`

The extracted plain text

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `GET /api/dashboard/completeness`

0-100 profile completeness with named next steps

- Auth: bearer token
- Success: `200`

#### `GET /api/dashboard/summary`

Real counts for this user

- Auth: bearer token
- Success: `200`

#### `GET /api/education`

The caller's education records

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/education`

Add a degree

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/education/{record_id}`

Get Education

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/education/{record_id}`

Update Education

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/education/{record_id}`

Delete Education

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `POST /api/feedback`

Send feedback

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/jobs`

Browse active job roles

- Auth: public
- Success: `200`
- Errors: `422`
- Query: `family, q, page, page_size`

#### `GET /api/jobs/families`

Role families with counts

- Auth: public
- Success: `200`

#### `GET /api/jobs/{role_id}`

Get Job

- Auth: public
- Success: `200`
- Errors: `404, 422`

Includes the weighted skill set, so a user can see what a role asks for.

#### `GET /api/profile`

The caller's profile

- Auth: bearer token
- Success: `200`

#### `POST /api/profile`

Create or replace the caller's profile

- Auth: bearer token
- Success: `201`
- Errors: `422`

Idempotent: a user who already has a profile has it updated, not duplicated.

#### `PATCH /api/profile`

Partially update the profile

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `DELETE /api/profile`

Delete the profile (account and data are kept)

- Auth: bearer token
- Success: `204`

Deletes the profile row only.

#### `GET /api/projects`

The caller's projects

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

Paged. The generic Page[ProjectRead] is the response model, so the

#### `POST /api/projects`

Create a project

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/projects/{project_id}`

One project

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/projects/{project_id}`

Update a project

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/projects/{project_id}`

Delete a project

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `POST /api/recommendations`

Generate a ranked, explainable set of recommendations

- Auth: bearer token
- Success: `201`
- Errors: `401, 409, 422`

Runs the deterministic engine and persists the run.

#### `GET /api/recommendations/runs`

The caller's run history

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `GET /api/recommendations/runs/{run_id}`

A persisted run, read from the database

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

Read-only, and never recomputed — a stored run is a historical record.

#### `GET /api/skill-gap/{job_role_id}`

Skill-gap analysis for a target role

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

Reads confirmed ``user_skill`` rows only.

#### `POST /api/skill-gap/{job_role_id}/learning-path`

Optional LLM-generated learning path

- Auth: bearer token
- Success: `200`
- Errors: `422, 503`

The one route in the system that may return ``503``.

#### `GET /api/skills`

The caller's skills

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `source, category`

#### `POST /api/skills`

Add a skill from the taxonomy

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `POST /api/skills/confirm`

Confirm or reject CV-detected skills

- Auth: bearer token
- Success: `200`
- Errors: `422`

Upsert accepted skills into ``user_skill``.

#### `GET /api/skills/taxonomy`

Search the skill taxonomy by name or alias

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, category, limit, offset`

Searching ``sklearn`` finds ``Scikit-learn`` — the alias feature made visible.

#### `PATCH /api/skills/{skill_id}`

Update proficiency, years used, or confirmed state

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/skills/{skill_id}`

Remove a skill

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `GET /health`

Liveness and database readiness

- Auth: public
- Success: `200`

#### `GET /readyz`

Readiness probe

- Auth: public
- Success: `200`

### Authentication

Session lifecycle. Every other route needs `Authorization: Bearer <token>`.

#### `POST /api/auth/login`

Exchange credentials for an access token

- Auth: public
- Success: `200`
- Errors: `401, 422`

#### `POST /api/auth/logout`

End the client session

- Auth: bearer token
- Success: `204`
- Errors: `401`

Acknowledge a logout.

#### `GET /api/auth/me`

The authenticated user

- Auth: bearer token
- Success: `200`

#### `PATCH /api/auth/me`

Update name or password

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `DELETE /api/auth/me`

Delete the account and all of its data

- Auth: bearer token
- Success: `204`

Delete the authenticated user.

#### `POST /api/auth/refresh`

Issue a fresh access token

- Auth: bearer token
- Success: `200`
- Errors: `401, 422`

Re-issue a token for a still-valid subject.

#### `POST /api/auth/register`

Create an account and start a session

- Auth: public
- Success: `201`
- Errors: `409, 422`

Register a new user. Returns a token so the session starts immediately.

### Profile

The single profile a user owns.

#### `GET /api/profile`

The caller's profile

- Auth: bearer token
- Success: `200`

#### `POST /api/profile`

Create or replace the caller's profile

- Auth: bearer token
- Success: `201`
- Errors: `422`

Idempotent: a user who already has a profile has it updated, not duplicated.

#### `PATCH /api/profile`

Partially update the profile

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `DELETE /api/profile`

Delete the profile (account and data are kept)

- Auth: bearer token
- Success: `204`

Deletes the profile row only.

### Skills

User skills and the taxonomy they are drawn from. `POST /api/skills/confirm` is the CV confirmation gate: it is the only path from a *detected* skill to a *declared* one.

#### `GET /api/skills`

The caller's skills

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `source, category`

#### `POST /api/skills`

Add a skill from the taxonomy

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `POST /api/skills/confirm`

Confirm or reject CV-detected skills

- Auth: bearer token
- Success: `200`
- Errors: `422`

Upsert accepted skills into ``user_skill``.

#### `GET /api/skills/taxonomy`

Search the skill taxonomy by name or alias

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, category, limit, offset`

Searching ``sklearn`` finds ``Scikit-learn`` — the alias feature made visible.

#### `PATCH /api/skills/{skill_id}`

Update proficiency, years used, or confirmed state

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/skills/{skill_id}`

Remove a skill

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

### Projects, education, certifications

Full CRUD. Every row is scoped to its owner; another user's id returns 404.

#### `GET /api/certifications`

The caller's certifications

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/certifications`

Add a certification

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/certifications/{cert_id}`

Get Certification

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/certifications/{cert_id}`

Update Certification

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/certifications/{cert_id}`

Delete Certification

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `GET /api/education`

The caller's education records

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/education`

Add a degree

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/education/{record_id}`

Get Education

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/education/{record_id}`

Update Education

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/education/{record_id}`

Delete Education

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

#### `GET /api/projects`

The caller's projects

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

Paged. The generic Page[ProjectRead] is the response model, so the

#### `POST /api/projects`

Create a project

- Auth: bearer token
- Success: `201`
- Errors: `422`

#### `GET /api/projects/{project_id}`

One project

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/projects/{project_id}`

Update a project

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/projects/{project_id}`

Delete a project

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

### CV

Upload, inspect, delete. Extraction proposes skills; it never applies them.

#### `GET /api/cv`

The caller's uploads

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `POST /api/cv/upload`

Upload a CV, extract its text, and detect skills

- Auth: bearer token
- Success: `201`
- Errors: `401, 413, 415, 422`

Extraction runs on upload; nothing is written to ``user_skill`` here.

#### `GET /api/cv/{upload_id}`

One upload with its detected skills

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `DELETE /api/cv/{upload_id}`

Delete an upload and the stored file

- Auth: bearer token
- Success: `204`
- Errors: `404, 422`

Removes the row **and** the file on disk.

#### `GET /api/cv/{upload_id}/text`

The extracted plain text

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

### Recommendations

`POST` generates and stores a run. `GET /api/recommendations/runs` is a history, so the UI can list past runs without regenerating.

#### `POST /api/recommendations`

Generate a ranked, explainable set of recommendations

- Auth: bearer token
- Success: `201`
- Errors: `401, 409, 422`

Runs the deterministic engine and persists the run.

#### `GET /api/recommendations/runs`

The caller's run history

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `GET /api/recommendations/runs/{run_id}`

A persisted run, read from the database

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

Read-only, and never recomputed — a stored run is a historical record.

### Skill gap

Per-role gap analysis with tiered missing skills. The learning path is optional and off by default.

#### `GET /api/skill-gap/{job_role_id}`

Skill-gap analysis for a target role

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

Reads confirmed ``user_skill`` rows only.

#### `POST /api/skill-gap/{job_role_id}/learning-path`

Optional LLM-generated learning path

- Auth: bearer token
- Success: `200`
- Errors: `422, 503`

The one route in the system that may return ``503``.

### Job roles (public)

Readable without a token, so a signed-out visitor can browse.

#### `GET /api/jobs`

Browse active job roles

- Auth: public
- Success: `200`
- Errors: `422`
- Query: `family, q, page, page_size`

#### `GET /api/jobs/families`

Role families with counts

- Auth: public
- Success: `200`

#### `GET /api/jobs/{role_id}`

Get Job

- Auth: public
- Success: `200`
- Errors: `404, 422`

Includes the weighted skill set, so a user can see what a role asks for.

### Dashboard

Real aggregates computed from the database, never a hard-coded figure.

#### `GET /api/dashboard/completeness`

0-100 profile completeness with named next steps

- Auth: bearer token
- Success: `200`

#### `GET /api/dashboard/summary`

Real counts for this user

- Auth: bearer token
- Success: `200`

### Feedback

Optional, not one of the proposal's nine modules.

#### `POST /api/feedback`

Send feedback

- Auth: bearer token
- Success: `201`
- Errors: `422`

### Admin

Requires the `admin` role. A normal user gets 403, not 404.

#### `GET /api/admin/evaluation`

The committed evaluation report as JSON

- Auth: bearer token
- Success: `200`
- Errors: `404`

Serve the **committed** report rather than re-running the harness.

#### `GET /api/admin/feedback`

Submitted feedback, paged

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `category, page, page_size`

#### `GET /api/admin/health`

Lightweight admin liveness probe

- Auth: bearer token
- Success: `200`

A probe proving the role gate works end to end.

#### `GET /api/admin/jobs`

List every role, including deactivated ones

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, family, is_active, page, page_size`

#### `POST /api/admin/jobs`

Create a job role with its weighted required skills

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `GET /api/admin/jobs/{role_id}`

Get Job Admin

- Auth: bearer token
- Success: `200`
- Errors: `404, 422`

#### `PATCH /api/admin/jobs/{role_id}`

Update Job

- Auth: bearer token
- Success: `200`
- Errors: `404, 409, 422`

#### `DELETE /api/admin/jobs/{role_id}`

Delete a job role

- Auth: bearer token
- Success: `204`
- Errors: `404, 409, 422`

#### `PUT /api/admin/jobs/{role_id}/skills`

Atomically replace a role's weighted skill set

- Auth: bearer token
- Success: `200`
- Errors: `422`

#### `GET /api/admin/overview`

Real system aggregates

- Auth: bearer token
- Success: `200`

#### `GET /api/admin/taxonomy`

Browse the skill taxonomy

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `q, category, page, page_size`

#### `POST /api/admin/taxonomy`

Add a skill to the taxonomy

- Auth: bearer token
- Success: `201`
- Errors: `409, 422`

#### `PATCH /api/admin/taxonomy/{skill_id}`

Update Skill

- Auth: bearer token
- Success: `200`
- Errors: `404, 409, 422`

#### `DELETE /api/admin/taxonomy/{skill_id}`

Delete Skill

- Auth: bearer token
- Success: `204`
- Errors: `404, 409, 422`

#### `GET /api/admin/users`

Paged user list (never includes password_hash)

- Auth: bearer token
- Success: `200`
- Errors: `422`
- Query: `page, page_size`

#### `PATCH /api/admin/users/{user_id}/role`

Promote or demote

- Auth: bearer token
- Success: `200`
- Errors: `422`

An admin cannot demote themselves.

## Every other operation

None. Every published operation appears in a group above.

## Verifying this document

```bash
cd backend && python scripts/generate_api_docs.py && git diff --exit-code docs/api.md
```

A non-empty diff means the routes changed and this page was not regenerated. `tests/test_api_docs.py` runs exactly that check.

