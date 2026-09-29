# Legacy Freeze Record

The predecessor codebase was preserved unmodified in the first commit so that the
rewrite could be compared against it, and so that nothing was lost before the new
system was demonstrably working. This document records that baseline, what was
frozen, and what happened to it.

**Status:** the legacy tree is deleted. The baseline remains in git history at
commit `4097115`, and the legacy database is archived under
[`docs/archive/`](archive/README.md).

---

## 1. Why freeze before rewriting

A rewrite that starts by deleting has no reference point. Three things go wrong
without a frozen baseline:

1. **Requirements drift.** The proposal describes CareerLens AI. The code described
   Pathfinder. Once the old code is gone, there is nothing to check a requirement
   against, and a reviewer cannot tell whether a missing feature was deliberately
   dropped or quietly forgotten.
2. **Silent data loss.** If the old data model is deleted before anyone has looked
   at it, the reasons it was shaped that way disappear with it.
3. **Unreviewable diffs.** Deleting 30 files and adding 30 in one commit is not a
   change anyone can review.

So the first commit contained the legacy tree exactly as found, and everything
after that was additive until the new system was working.

## 2. What was frozen

Commit `4097115` — `chore(repo): initialise git repository with the frozen legacy
Pathfinder tree`.

| Path | What it was |
|---|---|
| `backend/app.py` | Flask application entry point, 5001 |
| `backend/auth.py` | Authentication, hardcoded weak defaults |
| `backend/admin.py` | Flask admin blueprint |
| `backend/models.py` | SQLAlchemy models over SQLite |
| `backend/extensions.py` | Extension wiring |
| `backend/tasks.py` | Background/celery-ish stubs |
| `backend/utils.py` | Helpers |
| `backend/guidance.py` | LLM guidance calls, the origin of a provider-error leak |
| `backend/instance/pathfinder.db` | SQLite database, 6 tables |
| `backend/scripts/e2e_test.py` | Ad-hoc script, hardcoded to `127.0.0.1:5001` |
| `backend/scripts/{create_feedback_table,inspect_db,post_feedback_test,show_feedbacks}.py` | One-off operational scripts |
| `frontend/vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/App.css` | Vite entry points |
| `frontend/src/pages/` | The 14 page components |
| `frontend/src/api/` | The API client |
| `frontend/.env`, `frontend/.env.development` | Two files disagreeing about the API port (5001 vs 5000) |

**Data in the frozen tree:** 6 SQLite tables, 11 users, 11 profiles, 6 guidance
sessions, 6 events, 2 feedback rows. Row counts and structure are preserved in the
archive; personal data is not. See [`archive/README.md`](archive/README.md) for
exactly what was redacted and why.

## 3. Defects found in the legacy code

Recorded because they are the reason for several non-obvious decisions in the new
system, and because "we fixed it" is not an answer to "why is it built this way".

| Defect | Location | What was done instead |
|---|---|---|
| Hardcoded weak secrets | `app.py:19,22` — `SECRET_KEY = 'dev-secret'`, `JWT_SECRET_KEY = 'jwt-secret'` | `Settings` refuses to start without a ≥32-character key, and rejects the example placeholder in production. |
| Secrets could be replaced by equally weak defaults | `app.py` | The validator raises rather than defaulting. There is no fallback value to swap in. |
| Password hash leaked in API responses | `auth.py` | No response schema contains `password_hash`; a test asserts the string `password` never appears in a registration response. |
| Provider error text returned to the client | `guidance.py:59` | Provider failures are logged server-side and the caller receives deterministic local steps. Tested. |
| No ownership checks on user resources | `models.py`, routes | Every user-scoped query filters by `user_id` in the `WHERE` clause. `test_ownership.py` covers each entity. |
| Mock data presented as real | `mockStats` in the dashboard, `mockRecommendations`, hardcoded `12,847` / `94%` / `500+` figures | All removed. `scripts/verify_compliance.py` fails if any reappear. |
| A fabricated quiz | frontend `pages/Quiz` | Removed. Not in the proposal. |
| Two `.env` files disagreeing about the API port | `frontend/.env` (5001) vs `.env.development` (5000) | One variable, documented in one template. |
| Delimited strings for skills/education/experience | `models.py` | Normalised tables. See [`erd.md`](erd.md). |
| Ad-hoc e2e script outside the test suite | `scripts/e2e_test.py` | Deleted. The suite is pytest-only. |
| Undisclosed "AI" | LLM calls behind a `/guidance` route | Optional, off by default, and the absence of a trained model is disclosed in the evaluation report. |

## 4. What was deleted, and when

The legacy tree was removed in a single commit *after* the new system was
demonstrably working — register, upload a CV, get ranked recommendations — so
nothing was deleted while it was the only thing running.

Deleting early would have made the project unrunnable at every moment before the
cutover, and unreviewable at the cutover.

The deleted files, and the commit that removed them, are enumerated in that
commit's message. To recover any of it:

```bash
git show 4097115:backend/app.py          # view the original
git checkout 4097115 -- backend/app.py   # restore one file
```

The frozen commit is never rewritten or garbage-collected, so this works
indefinitely.

## 5. How the compliance checks keep the legacy out

`scripts/verify_compliance.py` runs 31 assertions over the repository. The ones
that guard this decision:

- **No legacy Flask module remains tracked.** Any `.py` at `backend/*.py` outside
  `app/`, `tests/`, `scripts/` and `alembic/` fails the check. This is what
  prevented a stray file surviving the cutover.
- **No SQLite database is tracked** outside `docs/archive/`, which is where the
  redacted legacy copy lives and why it is allowed.
- **No `.env` is tracked**, and no `.env` template ships a populated secret.
- **No 'Pathfinder' or 'CareerGuide'** survives in any source file or document.

Run it:

```bash
python scripts/verify_compliance.py
```

## 6. The rule for the future

If a file in the frozen tree contains behaviour we want, it is copied, not
restored. Restoring a file brings its defects and its Flask assumptions with it —
which is the mistake this document exists to prevent.
