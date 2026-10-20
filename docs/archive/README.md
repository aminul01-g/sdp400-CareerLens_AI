# Archived legacy artefacts

This directory holds the predecessor system's data, kept for one reason: to show
what it actually looked like, so the decision not to migrate it can be judged
rather than taken on trust.

## `pathfinder-legacy.db`

A copy of the predecessor's SQLite database, `backend/instance/pathfinder.db`.

### Why it was not migrated

The proposal (§3.5) requires an explicit decision on legacy data. The decision
here is: **do not migrate any of it.** The reasons are structural, not
convenient:

| Legacy table | Why it cannot be carried across |
|---|---|
| `user` | Password hashes are bcrypt with a cost factor chosen for a Flask app that no longer exists. Re-using them would carry a credential-verification scheme we would then be responsible for, with no benefit — every user can simply re-register. |
| `profile` | `skills`, `education` and `experience` are free-text blobs, not rows. There is no structure to lift: "python,sql,ml" in one cell has no table to become. Migrating it would mean writing a parser for a format nobody specified, and silently guessing at the parts it could not parse. |
| `upload` | Empty. Nothing to migrate. |
| `guidance_session` | Ephemeral LLM transcripts from a feature that no longer exists. Keeping them would imply the feature does. |
| `event` | Analytics from an app with a different event vocabulary. Carrying them forward would fabricate a history that never happened. |
| `feedback` | Two rows, both the string "Testing feedback endpoint". Test noise. |

The decisive point: the new system models a profile as **normalised rows**
(`skill`, `user_skill`, `education_record`, `project`, `certification`), while the
old one stored a delimited string. A migration would either lose data or invent
structure, and the plan's own ERD review exists precisely because the old shape
was the problem. A clean cut with a documented archive beats a lossy migration.

Anyone who needs their old profile back re-enters it. That is a worse afternoon
than a corrupted import, and it is a decision the team can revisit with real
evidence rather than now, on incomplete data.

### It has been redacted, deliberately

The literal instruction was to archive the file unchanged. That was not followed,
because the file contains **real people's data**: 11 user rows with genuine names
and genuine email addresses. Committing those to a repository is a privacy
incident, and the fact that they are probably a teammate's own test accounts
does not change that.

Those names and addresses are not reproduced here either. A redaction that
quotes what it redacted is only half a redaction — the very document that
describes removing the data would otherwise republish it, in the one place a
reader is guaranteed to look. The rows themselves are in the archive, in the
same `.invalid` form described below.

What was changed:

| Column | Treatment |
|---|---|
| `user.name` | Replaced with `legacy-user-<id>`. The id is preserved, so row relationships stay traceable. |
| `user.email` | Replaced with `legacy-user-<id>@redacted.invalid`. `.invalid` is reserved by RFC 2606 and can never resolve. |
| `user.password_hash` | Replaced with a short non-bcrypt digest. No archive needs working credentials. |
| `feedback.name`, `feedback.email` | Replaced with `redacted`. |

What was **not** changed, and is the entire reason to keep the file:

- The full schema — every table, column, type and constraint.
- Every row count: 11 users, 11 profiles, 0 uploads, 2 feedback, 6 guidance
  sessions, 6 events.
- Every non-identifying value, including the `profile` free-text blobs, which are
  what demonstrate *why* the migration was rejected.

So the file is still a truthful record of the legacy data model. It is not a
record of anyone's personal information.

If you believe the redaction was over-cautious and the data should be preserved
intact, that is a reasonable position — but it should be a decision someone makes
explicitly, with the repository's visibility in mind, not a side effect of running
a copy command.

### Inspecting it

```bash
sqlite3 docs/archive/pathfinder-legacy.db .schema
sqlite3 docs/archive/pathfinder-legacy.db "select count(*) from profile;"
```

The file is read-only history. Nothing in the application reads it, and
`scripts/verify_compliance.py` asserts that no SQLite database is tracked outside
this directory.
