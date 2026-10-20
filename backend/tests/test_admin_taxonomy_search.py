"""The admin can reach every skill in the catalogue.

The knowledge base holds 250 skills across 14 categories. The admin job-role
editor used to fetch the *first page* of that list and filter it in the
browser, so the picker only ever contained the categories that sort first
alphabetically -- "Accounting & Finance", "Analytics & Communication",
"Civil & Electrical Engineering" and a handful of "Data Engineering" skills.
Everything else, including every skill in "ML Frameworks", "MLOps & Cloud",
"Deep Learning" and "NLP & LLM", was unreachable.

The consequence was not cosmetic. 94 of the 100 job roles require at least
one skill from an unreachable category, so an administrator editing a real
role was told "no match" for PyTorch or Docker -- the skills the role was
built around -- and could not add them. The search had to move to the
server, where the whole catalogue is reachable.

These tests pin the server-side behaviour, and the case-insensitivity that
came with it: the database runs with ``--locale=C`` for deterministic
collation, which makes ``LIKE`` case-sensitive, and ten aliases carry
uppercase by design ("AP", "BIM", "CRO", "L&D").

The full catalogue is seeded here rather than the small slice the shared
``taxonomy_seed`` fixture provides, because the bug was precisely a
consequence of the catalogue being *large* -- a test against eighteen skills
would pass with the old code and would not have caught it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def full_taxonomy(db: Session) -> None:
    """Seed the real 250-skill catalogue and the 100 job roles, as deployed does."""
    from scripts.seed_job_roles import seed as seed_roles
    from scripts.seed_taxonomy import seed as seed_taxonomy

    seed_taxonomy(db)
    seed_roles(db)


@pytest.fixture
def admin_client(auth_client, full_taxonomy) -> TestClient:
    client, _user = auth_client(role="admin")
    return client


@pytest.fixture
def user_client(auth_client, full_taxonomy) -> TestClient:
    """A signed-in user, against the full catalogue."""
    client, _user = auth_client()
    return client


def _search(client: TestClient, q: str) -> list[str]:
    response = client.get("/api/admin/taxonomy", params={"q": q, "page_size": 100})
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


# --------------------------------------------------------------------------- #
# the skills that were unreachable
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("pytorch", "PyTorch"),
        ("docker", "Docker"),
        ("kubernetes", "Kubernetes"),
        ("tensorflow", "TensorFlow"),
        ("transformers", "Transformers"),
        ("pytorch lightning", "PyTorch Lightning"),
    ],
)
def test_a_skill_from_a_late_category_is_reachable(
    admin_client: TestClient, query: str, expected: str
) -> None:
    """The categories that sort after "Data Engineering" must be searchable."""
    assert expected in _search(admin_client, query)


def test_the_search_finds_a_skill_by_its_alias(admin_client: TestClient) -> None:
    """Typing an alias finds the canonical skill, which is the point of aliases."""
    assert "Scikit-learn" in _search(admin_client, "sklearn")


@pytest.mark.parametrize("query", ["pytorch", "PyTorch", "PYTORCH", "PyToRcH"])
def test_the_search_is_case_insensitive(admin_client: TestClient, query: str) -> None:
    """Case sensitivity is a real bug here, not a nicety.

    The database is initialised with ``--locale=C`` for deterministic
    collation, which makes ``LIKE`` case-sensitive. A search built on
    ``lower(name) LIKE lower(needle)`` still worked for names, but the alias
    lookup did not lower the column, so the ten uppercase aliases -- "AP",
    "BIM", "CRO", "L&D" -- could not be found by typing them.
    """
    assert "PyTorch" in _search(admin_client, query)


@pytest.mark.parametrize(
    ("query", "expected"),
    [("bim", "Building Information Modelling"), ("ap", "Accounts Payable")],
)
def test_an_uppercase_alias_is_reachable(admin_client: TestClient, query: str, expected: str) -> None:
    """The aliases that carry uppercase are the ones a case-sensitive search lost."""
    assert expected in _search(admin_client, query)


def test_the_search_reaches_beyond_the_first_page(admin_client: TestClient) -> None:
    """A broad search returns skills from many categories, not just the first."""
    response = admin_client.get(
        "/api/admin/taxonomy", params={"q": "a", "page_size": 100}
    )
    assert response.status_code == 200
    categories = {item["category"] for item in response.json()["items"]}
    assert len(categories) > 4, f"only {categories} were reachable"


def test_the_taxonomy_covers_every_role(admin_client: TestClient, db) -> None:
    """Every skill a role requires is findable by an admin.

    This is the invariant the bug broke: 94 of the 100 roles needed a skill
    the picker could not return.
    """
    from sqlalchemy import select

    from app.models.job import JobRoleSkill
    from app.models.skill import Skill

    pairs = db.execute(
        select(JobRoleSkill.skill_id, JobRoleSkill.job_role_id, Skill.name)
        .join(Skill, Skill.id == JobRoleSkill.skill_id)
    ).all()
    assert pairs, "the seed data is missing"

    # Fetch every distinct skill name the catalogue contains, by searching for
    # a fragment of it, and confirm each one comes back.
    unreachable: list[str] = []
    for skill_name in sorted({row[2] for row in pairs}):
        fragment = skill_name.split()[0][:6]
        found = _search(admin_client, fragment)
        if skill_name not in found:
            unreachable.append(skill_name)

    assert not unreachable, f"unreachable skills: {unreachable[:10]}"


def test_the_search_endpoint_requires_an_admin(user_client: TestClient) -> None:
    """A normal user cannot browse the admin taxonomy."""
    assert user_client.get("/api/admin/taxonomy", params={"q": "pytorch"}).status_code == 403


def test_an_empty_query_lists_the_first_page(admin_client: TestClient) -> None:
    """With no query the endpoint pages the catalogue as it always did."""
    response = admin_client.get("/api/admin/taxonomy", params={"page_size": 50})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 200, "the catalogue is smaller than it should be"
    assert len(body["items"]) == 50


# --------------------------------------------------------------------------- #
# the user-facing picker uses the same search
# --------------------------------------------------------------------------- #
def test_the_user_taxonomy_search_is_also_case_insensitive(user_client: TestClient) -> None:
    """The user-facing picker shares the search, so it shares the fix."""
    response = user_client.get(
        "/api/skills/taxonomy", params={"q": "bim", "limit": 50}
    )
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert "Building Information Modelling" in names


def test_the_taxonomy_categories_endpoint_lists_the_catalogue(user_client: TestClient) -> None:
    """The category filter is built from the catalogue, not from the user.

    A filter built from the caller's own skills is empty for a user who has
    not added one yet -- which is exactly the person who needs the picker.
    """
    response = user_client.get("/api/skills/taxonomy/categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 14
    assert "ML Frameworks" in categories
    assert "MLOps & Cloud" in categories
    assert categories == sorted(categories)


def test_the_categories_endpoint_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/skills/taxonomy/categories").status_code == 401
