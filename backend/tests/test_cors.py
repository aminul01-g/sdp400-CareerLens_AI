"""T029 — CORS is an allowlist, not an open door.

Security finding S2: the legacy app called ``CORS(app)`` at ``backend/app.py:18``
with no origins list, so any origin could make credentialed requests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

ALLOWED = "http://localhost:3000"
DENIED = "https://evil.example.test"


def test_listed_origin_receives_allow_origin_header(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": ALLOWED})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED


def test_unlisted_origin_receives_no_allow_origin_header(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": DENIED})
    assert response.status_code == 200  # the request itself is fine
    # The browser is the enforcement point, and it is denied the header.
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_listed_origin_is_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/profile",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "PATCH" in allowed_methods


def test_preflight_for_unlisted_origin_is_denied(client: TestClient) -> None:
    response = client.options(
        "/api/profile",
        headers={
            "Origin": DENIED,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_default_allowlist_is_localhost_only() -> None:
    origins = get_settings().allowed_origin_list
    assert origins
    assert all(
        origin.startswith(("http://localhost", "http://127.0.0.1")) for origin in origins
    ), f"a non-local origin is in the default allowlist: {origins}"


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)
def test_known_dev_origins_are_allowed(client: TestClient, origin: str) -> None:
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers.get("access-control-allow-origin") == origin
