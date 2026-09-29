"""`docs/api.md` must describe the API that actually exists.

A hand-maintained API reference is a snapshot of the day someone typed it. This
suite regenerates the document from the live OpenAPI schema and fails if the
committed copy differs, which turns "did someone remember to update the docs?" from
a review question into a test result.

The reverse check matters just as much: every published operation must appear in
the document. A route added and forgotten is the failure mode that matters most in
an API reference, because a reader concludes the endpoint does not exist.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
API_DOC = BACKEND_ROOT.parent / "docs" / "api.md"
GENERATOR = BACKEND_ROOT / "scripts" / "generate_api_docs.py"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


@pytest.fixture(scope="module")
def schema() -> dict:
    from app.main import create_app

    return create_app().openapi()


@pytest.fixture(scope="module")
def document() -> str:
    assert API_DOC.exists(), (
        f"{API_DOC} is missing. Generate it with: python scripts/generate_api_docs.py"
    )
    return API_DOC.read_text(encoding="utf-8")


def test_committed_api_doc_matches_the_live_schema(document: str) -> None:
    """Regenerating must be a no-op.

    A non-empty diff means a route, summary, status code or auth requirement
    changed and the reference was not regenerated.
    """
    before = API_DOC.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    after = API_DOC.read_text(encoding="utf-8")
    assert before == after, (
        "docs/api.md is out of date with the routes. "
        "Run: python scripts/generate_api_docs.py"
    )
    del document


def test_every_operation_is_documented(schema: dict, document: str) -> None:
    """No published operation may be missing from the reference."""
    undocumented: list[str] = []
    for path, operations in schema["paths"].items():
        for method in HTTP_METHODS:
            if method not in operations:
                continue
            heading = f"`{method.upper()} {path}`"
            if heading not in document:
                undocumented.append(heading)
    assert not undocumented, f"undocumented operations: {undocumented}"


def test_no_documented_operation_is_phantom(schema: dict, document: str) -> None:
    """No operation may be documented that the application does not serve.

    The other direction of the drift, and the one a reader would hit hardest: the
    document would send someone to an endpoint that 404s.
    """
    real = {
        f"{method.upper()} {path}"
        for path, operations in schema["paths"].items()
        for method in HTTP_METHODS
        if method in operations
    }
    # Headings look like: #### `GET /api/jobs`
    documented = set(re.findall(r"^#### `([A-Z]+ [^`]+)`$", document, flags=re.MULTILINE))
    phantoms = documented - real
    assert not phantoms, f"documented but not served: {sorted(phantoms)}"


def test_operation_count_in_the_document_is_true(schema: dict, document: str) -> None:
    """The headline count must match reality, not be a number someone typed."""
    total = sum(
        1
        for operations in schema["paths"].values()
        for method in HTTP_METHODS
        if method in operations
    )
    paths = len(schema["paths"])
    assert f"**{paths} paths, {total} operations.**" in document


def test_error_envelope_is_documented(document: str) -> None:
    """The error shape is the first thing an integrator needs, so it is asserted."""
    for code in (
        "unauthorized",
        "forbidden",
        "not_found",
        "conflict",
        "validation_error",
        "feature_disabled",
    ):
        assert f"`{code}`" in document, f"error code {code} is not documented"


def test_the_404_rather_than_403_rationale_is_stated(document: str) -> None:
    """An undocumented security decision reads as an oversight.

    Returning 404 instead of 403 for another user's record is deliberate -- 403
    would confirm the id exists -- and a future maintainer "fixing" it to 403
    would reintroduce an enumeration oracle. The reason belongs in the document.
    """
    assert "enumeration" in document.lower()


def test_optional_feature_is_marked_optional(document: str) -> None:
    """The learning path must be visibly optional, per proposal section 4.2."""
    assert "off by default" in document.lower()
    assert "learning-path" in document


def test_generator_is_idempotent(schema: dict) -> None:
    """Two consecutive generations must produce identical bytes.

    The same determinism requirement the evaluation harness is held to. A
    timestamp or a set-iteration order in the generator would make this document
    churn in every diff.
    """
    first = API_DOC.read_text(encoding="utf-8")
    for _ in range(2):
        subprocess.run(
            [sys.executable, str(GENERATOR)],
            capture_output=True,
            cwd=str(BACKEND_ROOT),
            check=True,
            timeout=300,
        )
    assert API_DOC.read_text(encoding="utf-8") == first
    del schema


def test_schema_itself_is_servable(client: TestClient) -> None:
    """The document claims /openapi.json works. Check that it does."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    served = response.json()
    assert "paths" in served
    # The served schema and the in-process one must be the same object graph.
    assert set(served["paths"]) == set(
        __import__("app.main", fromlist=["create_app"]).create_app().openapi()["paths"]
    )
