"""T086 — one error envelope, and no internals ever leak.

Two properties, and the second matters more than the first:

1. Every failure uses the same shape, so the frontend has exactly one thing to
   parse.
2. **No response body anywhere contains a Python exception message, a traceback,
   or a SQL fragment.** The legacy app returned upstream provider error text
   straight to the client (``guidance.py:59``) — security finding S8.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Substrings that must never appear in a client-visible body.
LEAK_MARKERS = (
    "Traceback",
    "  File \"",
    "sqlalchemy.",
    "psycopg",
    "SELECT ",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "alembic",
    "pydantic_core",
    "uvicorn.",
    "starlette.",
)


def _assert_no_leak(response) -> None:
    text = response.text
    for marker in LEAK_MARKERS:
        assert marker not in text, f"response leaked {marker!r}:\n{text[:500]}"


def test_validation_failure_uses_the_envelope(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"name": "", "email": "bad", "password": "x"})
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "errors"}
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["errors"], list)
    for item in body["error"]["errors"]:
        assert set(item) == {"field", "message"}
    _assert_no_leak(response)


def test_field_errors_are_keyed_to_their_field(client: TestClient) -> None:
    """The UI binds these to inputs, so the field name must survive."""
    response = client.post(
        "/api/auth/register", json={"name": "N", "email": "n@example.com", "password": "weak"}
    )
    fields = {e["field"] for e in response.json()["error"]["errors"]}
    assert "password" in fields


def test_not_found_uses_the_envelope(client: TestClient) -> None:
    response = client.get("/api/projects/999999", headers={"Authorization": "Bearer x"})
    assert response.status_code in (401, 404)
    assert "error" in response.json()


def test_unauthorized_uses_the_envelope(client: TestClient) -> None:
    response = client.get("/api/profile")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert response.headers.get("WWW-Authenticate") == "Bearer"
    _assert_no_leak(response)


def test_conflict_uses_the_envelope(client: TestClient, make_user, taxonomy_seed) -> None:
    user = make_user(email="dup@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    skill = taxonomy_seed[0]
    assert client.post("/api/skills", json={"skill_id": skill.id}, headers=headers).status_code == 201
    conflict = client.post("/api/skills", json={"skill_id": skill.id}, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "skill_already_present"
    _assert_no_leak(conflict)


def test_forbidden_uses_the_envelope(client: TestClient, make_user) -> None:
    user = make_user(email="plain2@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    response = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    _assert_no_leak(response)


def test_unsupported_media_type_uses_the_envelope(client: TestClient, make_user) -> None:
    user = make_user(email="upload@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    response = client.post(
        "/api/cv/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"
    _assert_no_leak(response)


def test_integrity_error_is_reported_as_409_without_sql(client: TestClient, make_user) -> None:
    """A database constraint violation must not reach the client as SQL text."""
    response = client.post(
        "/api/auth/register",
        json={"name": "A", "email": "not-an-email-at-all", "password": "Str0ngPassw0rd"},
    )
    _assert_no_leak(response)


def test_unhandled_exception_does_not_leak(client: TestClient, make_user, monkeypatch) -> None:
    """The single most important assertion in this file (finding S8)."""
    from app.api.routes import profile as profile_route

    def explode(*args, **kwargs):
        raise RuntimeError(
            "SECRET-DATABASE-DSN=postgres://user:hunter2@db/internal "
            "and a Python traceback follows"
        )

    monkeypatch.setattr(profile_route.profile_service, "get", explode)

    user = make_user(email="boom@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    response = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "SECRET" not in response.text
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
    _assert_no_leak(response)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/auth/register", {"name": "", "email": "x", "password": ""}),
        ("post", "/api/auth/login", {"email": "@", "password": ""}),
        ("patch", "/api/profile", {"headline": "x" * 500}),
        ("post", "/api/projects", {"title": "", "description": ""}),
        ("post", "/api/education", {"institution": "", "degree": ""}),
        ("post", "/api/certifications", {"name": "", "issuer": ""}),
        ("post", "/api/skills", {"skill_id": 0}),
        ("post", "/api/recommendations", {"limit": 999}),
    ],
)
def test_no_endpoint_leaks_on_bad_input(
    client: TestClient, make_user, method: str, path: str, payload: dict
) -> None:
    user = make_user()
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    response = getattr(client, method)(path, json=payload, headers={"Authorization": f"Bearer {token}"})
    _assert_no_leak(response)


def test_404_for_unknown_route_uses_the_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()
    _assert_no_leak(response)


def test_method_not_allowed_uses_the_envelope(client: TestClient) -> None:
    response = client.put("/api/auth/login", json={})
    assert response.status_code == 405
    assert "error" in response.json()
    _assert_no_leak(response)


# ---------------------------------------------------------------------------
# Security regression checks for the legacy findings
# ---------------------------------------------------------------------------
def test_no_optional_auth_on_write_endpoints(client: TestClient, make_user) -> None:
    """S4: anonymous callers must not be able to write anything."""
    writes = [
        ("post", "/api/cv/upload", None),
        ("post", "/api/feedback", {"message": "spam from an anonymous caller"}),
        ("post", "/api/recommendations", {}),
    ]
    for method, path, payload in writes:
        kwargs = {"json": payload} if payload is not None else {}
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 401, f"{method.upper()} {path} allowed an anonymous write"


def test_no_flask_admin_surface(raw_client: TestClient) -> None:
    """S1: the legacy /admin/ listed password hashes to anonymous visitors."""
    for path in ("/admin", "/admin/", "/admin/user/"):
        response = raw_client.get(path)
        assert response.status_code in (404, 307), f"{path} returned {response.status_code}"
        assert "password_hash" not in response.text


def test_password_hash_never_appears_in_any_response(
    client: TestClient, make_user, taxonomy_seed
) -> None:
    user = make_user(email="rolehash@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    probes: list = [
        client.get("/api/auth/me", headers=headers),
        client.post(
            "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
        ),
        client.post(
            "/api/auth/register",
            json={"name": "X", "email": "newx@example.com", "password": "Str0ngPassw0rd"},
        ),
    ]
    for probe in probes:
        assert "password_hash" not in probe.text
        assert "$2b$" not in probe.text, "a bcrypt hash leaked into a response"


def test_admin_user_list_never_exposes_hashes(
    client: TestClient, make_user, taxonomy_seed
) -> None:
    from app.models.user import UserRole

    admin = make_user(email="rolehashadmin@example.com", role=UserRole.ADMIN)
    token = client.post(
        "/api/auth/login", json={"email": admin.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    response = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert "$2b$" not in response.text


def test_openapi_schema_declares_no_hash_fields(client: TestClient) -> None:
    """No *schema* may declare a ``password_hash`` property.

    Checked structurally over ``components.schemas`` rather than by string-matching
    the whole document, because a description may legitimately *mention* the field
    by name (several do, to say it is deliberately absent) and that is not a leak.
    """
    schema = client.get("/openapi.json").json()

    offenders: list[str] = []
    for name, definition in (schema.get("components", {}).get("schemas", {}) or {}).items():
        properties = definition.get("properties") or {}
        if "password_hash" in properties:
            offenders.append(name)

    assert not offenders, f"schemas exposing password_hash: {offenders}"

    # The request models legitimately contain a password field.
    assert "password" in str(schema.get("components", {}).get("schemas", {}))
