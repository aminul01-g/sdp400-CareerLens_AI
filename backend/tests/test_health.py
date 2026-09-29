"""T026 — the service banner and the health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_service_banner(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "careerlens-api"
    assert body["docs"] == "/docs"
    assert "version" in body


def test_health_reports_database_ok(client: TestClient) -> None:
    """``/health`` must include a real database round trip, not a hard-coded "ok"."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["service"] == "careerlens-api"


def test_readiness_probe(client: TestClient) -> None:
    assert client.get("/readyz").status_code == 200


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "CareerLens AI API"
    assert schema["info"]["version"]
    # Every domain the proposal names must be represented in the spec.
    paths = schema["paths"]
    for prefix in (
        "/api/auth",
        "/api/profile",
        "/api/skills",
        "/api/projects",
        "/api/education",
        "/api/certifications",
        "/api/jobs",
        "/api/cv",
        "/api/recommendations",
        "/api/skill-gap",
        "/api/dashboard",
        "/api/admin",
    ):
        assert any(p.startswith(prefix) for p in paths), f"{prefix} missing from OpenAPI"


def test_request_id_header_is_returned(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Process-Time-Ms")
