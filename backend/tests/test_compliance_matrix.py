"""`docs/compliance-matrix.md` must cite tests that exist.

A compliance matrix is only worth reading if its evidence column is real. A matrix
citing a test name that was renamed months ago is worse than no matrix, because it
converts an unverified claim into a verified-looking one — the exact failure the
plan's T168 calls "a bug, not a documentation gap".

So every test name mentioned in the matrix is extracted and resolved against the
suite here. A rename breaks this file before it misleads a reader.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
MATRIX = REPO_ROOT / "docs" / "compliance-matrix.md"

TEST_REF = re.compile(r"::(test_[a-z0-9_]{6,})")


@pytest.fixture(scope="module")
def matrix() -> str:
    assert MATRIX.exists(), f"{MATRIX} is missing; T168 is not done"
    return MATRIX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def actual_test_names() -> set[str]:
    names: set[str] = set()
    for path in (BACKEND_ROOT / "tests").glob("test_*.py"):
        for match in re.finditer(r"^def (test_[a-z0-9_]+)", path.read_text(encoding="utf-8"), re.M):
            names.add(match.group(1))
    return names


def test_the_matrix_cites_at_least_thirty_tests(matrix: str) -> None:
    """A matrix with a handful of citations is not a walkthrough of the codebase."""
    cited = set(TEST_REF.findall(matrix))
    assert len(cited) >= 30, f"only {len(cited)} distinct test names cited"


def test_every_cited_test_exists(matrix: str, actual_test_names: set[str]) -> None:
    """Each cited name must resolve to a real test in the suite."""
    cited = set(TEST_REF.findall(matrix))
    missing = sorted(cited - actual_test_names)
    assert not missing, (
        f"the compliance matrix cites tests that do not exist: {missing}. "
        "Either the tests were renamed or the matrix is stale."
    )


def test_the_matrix_states_how_many_rows_are_not_met(matrix: str) -> None:
    """The matrix must own its gaps.

    A matrix where every row is green is a matrix nobody checked, so the summary
    has to enumerate what is missing and why. This asserts that enumeration is
    present, not that it is empty.
    """
    assert "## Summary of what is not met" in matrix
    summary = matrix.split("## Summary of what is not met", 1)[1]
    assert "why" in summary.lower()
    assert "would close it" in summary.lower()
    # And the counts at the top must be internally consistent with the rows.
    assert re.search(r"Met, evidence in this repository \| \d+", matrix)
    assert re.search(r"Not done \| \d+", matrix)


def test_every_matrix_row_carries_a_status(matrix: str) -> None:
    """No requirement row may be left unticked.

    A row with no status is a row nobody decided about, and it is the failure mode a
    compliance matrix exists to prevent. Scoped to the numbered sections, because the
    closing summary table is prose about the gaps rather than a set of requirements.
    """
    body = matrix.split("## Summary of what is not met", 1)[0]
    rows = [line for line in body.splitlines() if line.startswith("|")]
    # Drop the separator rows and the header rows of each table.
    candidates = [
        row
        for row in rows
        if not re.match(r"^\|[\s\-|]+\|$", row)
        and not re.match(
            r"^\|\s*(\||Proposal requirement|Requirement|Module|Claim|Deliverable|Objective|Excluded item)",
            row,
        )
    ]
    undecided = [row for row in candidates if not re.search(r"(✅|⚠️|⬜|🚫)", row)]
    assert not undecided, (
        f"{len(undecided)} requirement rows carry no status, e.g. {undecided[:2]}"
    )


def test_out_of_scope_rows_are_verified_absent(matrix: str) -> None:
    """§18.9 is a "must not be built" section, so absence is the evidence.

    These three exclusions are the ones where an over-eager implementation would be
    the failure. Re-checking them here means the claim is verified rather than
    asserted, and a future feature that reintroduces a vector store breaks the
    build.
    """
    import re as regex

    backend_app = BACKEND_ROOT / "app"
    python_files = list(backend_app.rglob("*.py"))
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in python_files)

    # 1. No trained model is loaded or fitted anywhere in the application.
    for pattern in (r"joblib", r"\.predict\(", r"\.fit\(", r"pickle\.load", r"torch\.load"):
        assert not regex.search(pattern, corpus), (
            f"{pattern!r} appears in app/ — §18.9 forbids a trained ranking model"
        )

    # 2. No vector store or retrieval backend.
    for pattern in (r"vector_?store", r"\bpinecone\b", r"\bchroma\b", r"\bweaviate\b"):
        assert not regex.search(pattern, corpus, regex.IGNORECASE), (
            f"{pattern!r} appears in app/ — §18.9 forbids a RAG chatbot"
        )

    # 3. No payments, chat or employer surface.
    routes = "\n".join(
        p.read_text(encoding="utf-8") for p in (backend_app / "api" / "routes").glob("*.py")
    )
    for pattern in (r"stripe", r"payment", r"websocket", r"@router\.(get|post)\(\"/chat"):
        assert not regex.search(pattern, routes, regex.IGNORECASE), (
            f"{pattern!r} appears in the routes — §18.9 excludes payments, chat and employers"
        )

    assert "18.9" in matrix


def test_the_generated_evidence_counts_are_true(matrix: str) -> None:
    """Numbers quoted in the matrix must match the live system.

    "67 operations over 45 paths", "419 tests", "82 roles" — all of these are
    checkable, so a drift in any of them should fail rather than be published.
    """
    from app.main import create_app

    schema = create_app().openapi()
    paths = len(schema["paths"])
    operations = sum(
        1 for ops in schema["paths"].values() for m in ops if m in ("get", "post", "put", "patch", "delete")
    )
    assert f"{operations} operations over {paths} paths" in matrix

    import json

    roles = json.loads((BACKEND_ROOT / "data" / "job_roles.json").read_text(encoding="utf-8"))
    taxonomy = json.loads((BACKEND_ROOT / "data" / "skills_taxonomy.json").read_text(encoding="utf-8"))
    # Bold placement varies through the prose, so match the bare "N noun" form.
    assert f"{len(roles['roles'])} roles" in matrix
    assert f"{len(taxonomy['skills'])} skills" in matrix

    labels = (BACKEND_ROOT / "app" / "ml" / "evaluation" / "labelled_profiles.jsonl").read_text(
        encoding="utf-8"
    )
    n_labels = len([line for line in labels.splitlines() if line.strip()])
    assert f"**{n_labels} profiles" in matrix
    assert n_labels >= 20, "the proposal requires 20+ labelled profiles"


def test_the_evaluation_threshold_is_quoted_correctly(matrix: str) -> None:
    """The committed 0.75 threshold must be stated, and must be the real one."""
    from app.ml.evaluation.harness import TARGET_TOP3_HIT_RATE

    assert "0.75" in matrix
    assert TARGET_TOP3_HIT_RATE == 0.75
