"""Generate docs/api.md from the live OpenAPI schema.

Hand-written API documentation drifts: it describes the API that existed when
someone typed it. This reads the schema the application actually publishes and
emits the reference from it, so the document and the routes cannot disagree.

Run after any route change:

    python scripts/generate_api_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

OUTPUT = BACKEND_ROOT.parent / "docs" / "api.md"

# Grouped by who calls them, which is how a reader wants to navigate. Order is
# the journey, not alphabetical.
GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "Health",
        "Liveness and readiness. `/health` fails when the database is unreachable.",
        ["/health", "/readyz", "/"],
    ),
    (
        "Authentication",
        "Session lifecycle. Every other route needs `Authorization: Bearer <token>`.",
        ["/api/auth/register", "/api/auth/login", "/api/auth/refresh", "/api/auth/logout",
         "/api/auth/me", "/api/auth/verify-email", "/api/auth/resend-verification",
         "/api/auth/forgot-password", "/api/auth/reset-password"],
    ),
    (
        "Profile",
        "The single profile a user owns, and the work history on it.",
        ["/api/profile", "/api/work-history", "/api/work-history/{entry_id}",
         "/api/work-history/{entry_id}/confirm"],
    ),
    (
        "Skills",
        "User skills and the taxonomy they are drawn from. `POST /api/skills/confirm` is "
        "the CV confirmation gate: it is the only path from a *detected* skill to a "
        "*declared* one.",
        ["/api/skills", "/api/skills/taxonomy", "/api/skills/confirm"],
    ),
    (
        "Projects, education, certifications",
        "Full CRUD. Every row is scoped to its owner; another user's id returns 404.",
        ["/api/projects", "/api/education", "/api/certifications"],
    ),
    (
        "CV",
        "Upload, inspect, delete. Extraction proposes skills; it never applies them.",
        ["/api/cv", "/api/cv/upload"],
    ),
    (
        "Recommendations",
        "`POST` generates and stores a run. `GET /api/recommendations/runs` is a history, "
        "so the UI can list past runs without regenerating.",
        ["/api/recommendations", "/api/recommendations/runs"],
    ),
    (
        "Skill gap",
        "Per-role gap analysis with tiered missing skills. The learning path is optional "
        "and off by default.",
        ["/api/skill-gap/{job_role_id}", "/api/skill-gap/{job_role_id}/learning-path"],
    ),
    (
        "AI assistant",
        "The optional AI layer. Every route here answers `503 feature_disabled` when no "
        "model provider is configured, and none of them is on the path of a core "
        "feature. The engine still owns every score: the model explains, sequences, "
        "drafts and asks, and never decides.",
        [
            "/api/ai/status",
            "/api/ai/mentor/ask",
            "/api/ai/roadmaps",
            "/api/ai/roadmaps/{roadmap_id}",
            "/api/ai/roadmaps/{roadmap_id}/tasks/{task_key}",
            "/api/ai/job-analysis",
            "/api/ai/cv-advice",
            "/api/ai/interviews",
            "/api/ai/interviews/{session_id}",
            "/api/ai/interviews/{session_id}/answers",
            "/api/ai/interviews/{session_id}/next-question",
        ],
    ),
    (
        "Job roles (public)",
        "Readable without a token, so a signed-out visitor can browse.",
        ["/api/jobs", "/api/jobs/families"],
    ),
    (
        "Dashboard",
        "Real aggregates computed from the database, never a hard-coded figure.",
        ["/api/dashboard/summary", "/api/dashboard/completeness"],
    ),
    (
        "Feedback",
        "Optional, not one of the proposal's nine modules.",
        ["/api/feedback"],
    ),
    (
        "Admin",
        "Requires the `admin` role. A normal user gets 403, not 404.",
        ["/api/admin/overview", "/api/admin/users", "/api/admin/jobs", "/api/admin/taxonomy",
         "/api/admin/evaluation", "/api/admin/feedback", "/api/admin/health",
         "/api/admin/audit"],
    ),
]

METHOD_ORDER = ["get", "post", "put", "patch", "delete"]


def method_name(operation: dict) -> str:
    for key in ("get", "post", "put", "patch", "delete"):
        if key in operation:
            return key
    return "get"


def auth_requirement(operation: dict) -> str:
    security = operation.get("security")
    if security is None:
        return "public"
    if not security:
        return "public"
    for entry in security:
        for scheme in entry:
            if "bearer" in scheme.lower():
                return "bearer"
    return "public"


def success_codes(operation: dict) -> list[str]:
    found = []
    for code in (operation.get("responses") or {}):
        if str(code).startswith("2"):
            found.append(str(code))
    return sorted(found) or ["200"]


def error_codes(operation: dict) -> list[str]:
    found = []
    for code in (operation.get("responses") or {}):
        if str(code).startswith(("4", "5")):
            found.append(str(code))
    return sorted(found)


def resolve_ref(schema: dict, components: dict, depth: int = 0) -> str:
    """Reduce a response schema to a readable one-line type name.

    Kept for callers that want the expanded field list rather than the bare type
    name. The reference itself prefers the name, because a reader following a link
    from the API to the Pydantic model wants the model, not a flattened summary
    that has to be re-derived.
    """
    if depth > 3 or not isinstance(schema, dict):
        return "any"
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return name
    kind = schema.get("type")
    if kind == "array":
        return f"array<{resolve_ref(schema.get('items', {}), components, depth + 1)}>"
    if kind == "object" and "additionalProperties" in schema:
        return "object<string, any>"
    return str(kind or "any")


def main() -> int:
    from app.main import create_app

    app = create_app()
    schema = app.openapi()
    paths = schema["paths"]
    # Endpoint count, used in the summary and checked by a test.
    total = sum(len(ops) for ops in paths.values())

    lines: list[str] = []
    add = lines.append

    add("# API Reference")
    add("")
    add("Base URL in production: `https://<api-host>`  ")
    add("Local: `http://localhost:8000`  ")
    add("Interactive schema: `/docs` (Swagger UI), `/redoc`, `/openapi.json`")
    add("")
    add(
        f"**{len(paths)} paths, {total} operations.** Generated from the live OpenAPI "
        "schema by `backend/scripts/generate_api_docs.py`, so this page cannot describe "
        "an API the application does not have. Re-run that script after changing a route."
    )
    add("")

    add("## Conventions")
    add("")
    add("**Errors.** Every error has the same envelope, whatever produced it:")
    add("")
    add("```json")
    add("{")
    add('  "error": {')
    add('    "code": "validation_error",')
    add('    "message": "One or more fields are invalid.",')
    add('    "errors": [{ "field": "email", "message": "value is not a valid email address" }]')
    add("  }")
    add("}")
    add("```")
    add("")
    add("| Status | `code` | When |")
    add("| --- | --- | --- |")
    add("| 400 | `bad_request` | Malformed request the schema could not reject. |")
    add("| 401 | `unauthorized` | Missing, expired or invalid token. |")
    add("| 403 | `forbidden` | Authenticated, but the role is insufficient. |")
    add("| 404 | `not_found` | Absent, **or owned by another user**. See below. |")
    add("| 409 | `conflict` | Uniqueness violation, e.g. an email already registered. |")
    add("| 422 | `validation_error` | Pydantic rejected the body; `errors` is per field. |")
    add("| 503 | `feature_disabled` | An optional feature is switched off. |")
    add("")
    add(
        "**Why a 404 and not a 403 for someone else's record.** Returning 403 would "
        "confirm the id exists, which turns the API into an enumeration oracle. Every "
        "ownership check therefore reports 404, and the tests assert it."
    )
    add("")
    add("**Authentication.** `Authorization: Bearer <access_token>`. Tokens are JWTs, "
        "HS256, valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440).")
    add("")
    add("**Pagination.** List routes accept `limit` and `offset` and return "
        "`{items, total, limit, offset}`.")
    add("")
    add("**CORS.** Only the origins in `ALLOWED_ORIGINS` are permitted. An empty value "
        "means no browser origin is allowed, which is the safe default.")
    add("")

    add("## Endpoints")
    add("")
    seen: set[str] = set()
    for title, blurb, wanted in GROUPS:
        # Prefix match, so "/api/projects/{project_id}" is documented under
        # Projects rather than dumped into the catch-all at the bottom. Matched
        # prefixes are consumed, so the most specific group wins.
        #
        # A trailing slash means "everything under here", which is what
        # "/api/admin/" would mean — but the root path "/" is not a directory
        # prefix. Treating it as one made the Health group swallow every route
        # in the API, and every curated group below it repeated its own.
        matched = [
            (path, ops)
            for path, ops in sorted(paths.items())
            if any(
                path == prefix
                or (
                    prefix.endswith("/")
                    and len(prefix) > 1
                    and path.startswith(prefix)
                )
                or path.startswith(prefix + "/")
                or path.startswith(prefix + "?")
                or path.startswith(prefix + "{")
                for prefix in wanted
            )
        ]
        if not matched:
            continue
        add(f"### {title}")
        add("")
        add(blurb)
        add("")
        for path, ops in matched:
            for verb in METHOD_ORDER:
                operation = ops.get(verb)
                if operation is None:
                    continue
                seen.add(f"{verb.upper()} {path}")
                summary = operation.get("summary") or "(no summary)"
                auth = auth_requirement(operation)
                ok = ", ".join(success_codes(operation))
                bad = error_codes(operation)
                query = [
                    p.get("name")
                    for p in (operation.get("parameters") or [])
                    if p.get("in") == "query"
                ]
                add(f"#### `{verb.upper()} {path}`")
                add("")
                add(f"{summary}")
                add("")
                add(f"- Auth: {'bearer token' if auth == 'bearer' else 'public'}")
                add(f"- Success: `{ok}`")
                if bad:
                    add(f"- Errors: `{', '.join(bad)}`")
                if query:
                    add(f"- Query: `{', '.join(q for q in query if q)}`")
                if operation.get("description"):
                    body = operation["description"].strip().splitlines()
                    add("")
                    add(body[0].strip())
                add("")

    # Anything the GROUPS table did not name would silently vanish from the
    # document, so it is listed rather than dropped.
    ungrouped = [
        f"{verb.upper()} {path}"
        for path, ops in sorted(paths.items())
        for verb in METHOD_ORDER
        if verb in ops and f"{verb.upper()} {path}" not in seen
    ]
    add("## Every other operation")
    add("")
    if ungrouped:
        add(
            "These are in the schema but not in a group above. Listed explicitly so that "
            "adding a route without documenting it is visible in review:"
        )
        add("")
        for item in ungrouped:
            add(f"- `{item}`")
    else:
        add("None. Every published operation appears in a group above.")
    add("")

    add("## Verifying this document")
    add("")
    add("```bash")
    add("cd backend && python scripts/generate_api_docs.py && git diff --exit-code docs/api.md")
    add("```")
    add("")
    add(
        "A non-empty diff means the routes changed and this page was not regenerated. "
        "`tests/test_api_docs.py` runs exactly that check."
    )
    add("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(paths)} paths, {total} operations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
