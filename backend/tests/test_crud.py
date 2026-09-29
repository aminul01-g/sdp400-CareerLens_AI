"""CRUD for every entity the proposal's section 4.1 names.

Section 8.1 of the plan requires Create/Read/Update/Delete for profile, skills,
projects, education, certifications, and (admin-only) job roles. Each cell here
has a test, which is what makes the matrix demonstrable rather than asserted.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def user_client(client: TestClient, make_user, taxonomy_seed) -> TestClient:
    user = make_user(email="crud@example.com", name="CRUD User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def admin_client(client: TestClient, make_user, taxonomy_seed) -> TestClient:
    from app.models.user import UserRole

    user = make_user(email="crudadmin@example.com", name="CRUD Admin", role=UserRole.ADMIN)
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
def test_profile_crud(user_client: TestClient) -> None:
    created = user_client.post(
        "/api/profile",
        json={
            "headline": "ML Engineer",
            "career_goal": "Production MLOps",
            "bio": "Three years of experience.",
            "location": "Dhaka",
            "years_experience": 3,
            "preferred_role_family": "ML Engineer",
            "links": {"github": "https://github.com/example"},
        },
    )
    assert created.status_code == 201
    assert created.json()["headline"] == "ML Engineer"

    read = user_client.get("/api/profile")
    assert read.status_code == 200
    assert read.json()["location"] == "Dhaka"

    updated = user_client.patch("/api/profile", json={"headline": "Senior ML Engineer"})
    assert updated.status_code == 200
    assert updated.json()["headline"] == "Senior ML Engineer"
    assert updated.json()["location"] == "Dhaka", "PATCH wiped an untouched field"

    assert user_client.delete("/api/profile").status_code == 204
    assert user_client.get("/api/profile").status_code == 200  # get-or-create


def test_profile_update_distinguishes_absent_from_null(user_client: TestClient) -> None:
    user_client.post("/api/profile", json={"headline": "H", "bio": "B"})
    assert user_client.patch("/api/profile", json={}).json()["headline"] == "H"
    cleared = user_client.patch("/api/profile", json={"bio": None}).json()
    assert cleared["bio"] is None
    assert cleared["headline"] == "H"


def test_profile_validation(user_client: TestClient) -> None:
    assert user_client.post("/api/profile", json={"headline": "x" * 201}).status_code == 422
    assert user_client.post("/api/profile", json={"years_experience": 61}).status_code == 422
    assert user_client.post("/api/profile", json={"years_experience": -1}).status_code == 422
    assert user_client.post(
        "/api/profile", json={"links": {"github": "not-a-url"}}
    ).status_code == 422
    assert user_client.patch(
        "/api/profile", json={"headline": "x" * 201}
    ).status_code == 422


def test_profile_delete_removes_only_the_profile_row(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """The proposal treats profile and skills as separate modules with their own
    deletes, so removing a profile must not take the user's skills with it.
    """
    user_client.post("/api/profile", json={"headline": "ML Engineer"})
    user_client.post("/api/skills", json={"skill_id": skill_ids["python"]})
    user_client.post("/api/projects", json={"title": "P", "description": "d"})

    assert user_client.delete("/api/profile").status_code == 204

    # The account still authenticates, and the other modules survive.
    assert user_client.get("/api/auth/me").status_code == 200
    assert user_client.get("/api/skills").json() != []
    assert user_client.get("/api/projects").json()["total"] == 1
    # And GET /api/profile starts the user over with an empty profile.
    assert user_client.get("/api/profile").json()["headline"] is None


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
def test_skill_crud(user_client: TestClient, skill_ids: dict[str, int]) -> None:
    python = skill_ids["python"]
    sql = skill_ids["sql"]

    created = user_client.post("/api/skills", json={"skill_id": python, "proficiency": 4})
    assert created.status_code == 201
    assert created.json()["name"] == "Python"
    assert created.json()["proficiency"] == 4
    assert created.json()["source"] == "manual"

    user_client.post("/api/skills", json={"skill_id": sql, "proficiency": 2})
    listed = user_client.get("/api/skills").json()
    assert len(listed) == 2
    # Default ordering: strongest first.
    assert listed[0]["skill_id"] == python

    updated = user_client.patch(f"/api/skills/{python}", json={"proficiency": 5, "years_used": 2.5})
    assert updated.status_code == 200
    assert updated.json()["proficiency"] == 5
    assert updated.json()["years_used"] == 2.5

    assert user_client.delete(f"/api/skills/{sql}").status_code == 204
    assert len(user_client.get("/api/skills").json()) == 1
    assert user_client.delete(f"/api/skills/{sql}").status_code == 404


def test_skill_validation(user_client: TestClient, skill_ids: dict[str, int]) -> None:
    python = skill_ids["python"]
    assert user_client.post("/api/skills", json={"skill_id": python}).status_code == 201
    assert user_client.post("/api/skills", json={"skill_id": python}).status_code == 409
    assert user_client.post("/api/skills", json={"skill_id": 999999}).status_code == 422
    assert user_client.post(
        "/api/skills", json={"skill_id": skill_ids["sql"], "proficiency": 0}
    ).status_code == 422
    assert user_client.post(
        "/api/skills", json={"skill_id": skill_ids["sql"], "proficiency": 6}
    ).status_code == 422
    assert user_client.patch(f"/api/skills/{python}", json={"proficiency": 9}).status_code == 422


def test_taxonomy_search_matches_aliases(
    user_client: TestClient, taxonomy_seed
) -> None:
    """Typing ``sklearn`` must find ``Scikit-learn`` — the plan's named behaviour."""
    found = user_client.get("/api/skills/taxonomy", params={"q": "sklearn"})
    assert found.status_code == 200
    assert any(s["slug"] == "scikit-learn" for s in found.json()["items"])

    by_name = user_client.get("/api/skills/taxonomy", params={"q": "Scikit-learn"})
    assert {s["slug"] for s in by_name.json()["items"]} == {"scikit-learn"}


def test_taxonomy_search_paging_and_filters(
    user_client: TestClient, taxonomy_seed
) -> None:
    everything = user_client.get("/api/skills/taxonomy", params={"limit": 100}).json()
    assert everything["total"] >= len(taxonomy_seed)

    first = user_client.get("/api/skills/taxonomy", params={"limit": 2, "offset": 0}).json()
    second = user_client.get("/api/skills/taxonomy", params={"limit": 2, "offset": 2}).json()
    assert len(first["items"]) == len(second["items"]) == 2
    assert not {s["id"] for s in first["items"]} & {s["id"] for s in second["items"]}

    filtered = user_client.get(
        "/api/skills/taxonomy", params={"category": "ML Frameworks", "limit": 100}
    ).json()
    assert all(s["category"] == "ML Frameworks" for s in filtered["items"])

    assert user_client.get("/api/skills/taxonomy", params={"limit": 500}).status_code == 422


def test_bulk_confirm_is_idempotent(user_client: TestClient, skill_ids: dict[str, int]) -> None:
    payload = {
        "skills": [
            {"skill_id": skill_ids["python"], "accepted": True, "proficiency": 5},
            {"skill_id": skill_ids["sql"], "accepted": True, "proficiency": 3},
            {"skill_id": skill_ids["java"], "accepted": False},
        ]
    }
    first = user_client.post("/api/skills/confirm", json=payload)
    assert first.status_code == 200
    assert first.json()["added"] == 2
    assert first.json()["declined"] == 1

    held = {s["skill_id"] for s in user_client.get("/api/skills").json()}
    assert skill_ids["java"] not in held, "a rejected skill reached user_skill"

    second = user_client.post("/api/skills/confirm", json=payload)
    assert second.status_code == 200
    assert second.json()["added"] == 0
    assert len(user_client.get("/api/skills").json()) == 2, "confirmation duplicated rows"


def test_confirm_rejects_unknown_ids_per_item(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    result = user_client.post(
        "/api/skills/confirm",
        json={"skills": [
            {"skill_id": skill_ids["python"], "accepted": True},
            {"skill_id": 999999, "accepted": True},
        ]},
    )
    assert result.status_code == 200
    assert result.json()["added"] == 1
    assert result.json()["rejected"] == [999999]


def test_confirm_rejects_duplicate_skill_ids(user_client: TestClient, skill_ids) -> None:
    assert user_client.post(
        "/api/skills/confirm",
        json={"skills": [
            {"skill_id": skill_ids["python"], "accepted": True},
            {"skill_id": skill_ids["python"], "accepted": True},
        ]},
    ).status_code == 422


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def test_project_crud(user_client: TestClient) -> None:
    created = user_client.post(
        "/api/projects",
        json={
            "title": "Image classifier",
            "description": "Trained a CNN with PyTorch and served it with FastAPI.",
            "tech_stack": ["pytorch", "sklearn", "fastapi"],
            "role": "Solo developer",
            "repo_url": "https://github.com/example/project",
            "start_date": "2024-01-01",
        },
    )
    assert created.status_code == 201
    project_id = created.json()["id"]
    # Tech stack is canonicalised: "sklearn" is stored as the taxonomy slug.
    assert "scikit-learn" in created.json()["tech_stack"]
    assert "sklearn" not in created.json()["tech_stack"]

    assert user_client.get(f"/api/projects/{project_id}").status_code == 200

    updated = user_client.patch(
        f"/api/projects/{project_id}", json={"title": "Image classifier v2"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Image classifier v2"
    assert updated.json()["description"].startswith("Trained a CNN")

    assert user_client.delete(f"/api/projects/{project_id}").status_code == 204
    assert user_client.get(f"/api/projects/{project_id}").status_code == 404


def test_project_validation(user_client: TestClient) -> None:
    assert user_client.post("/api/projects", json={"title": "T"}).status_code == 422
    assert user_client.post("/api/projects", json={"description": "D"}).status_code == 422
    assert user_client.post(
        "/api/projects", json={"title": "x" * 161, "description": "d"}
    ).status_code == 422
    assert user_client.post(
        "/api/projects",
        json={"title": "T", "description": "d", "start_date": "2024-06-01", "end_date": "2024-01-01"},
    ).status_code == 422
    assert user_client.post(
        "/api/projects", json={"title": "T", "description": "d", "repo_url": "ftp://x"}
    ).status_code == 422


def test_project_keeps_unrecognised_tech_with_a_flag(user_client: TestClient) -> None:
    """A tool the taxonomy has not caught up with is flagged, not discarded."""
    response = user_client.post(
        "/api/projects",
        json={"title": "T", "description": "d", "tech_stack": ["pytorch", "SomeBrandNewTool"]},
    )
    assert response.status_code == 201
    assert "SomeBrandNewTool" in response.json()["unrecognised_tech"]


# ---------------------------------------------------------------------------
# Education and certifications
# ---------------------------------------------------------------------------
def test_education_crud(user_client: TestClient) -> None:
    created = user_client.post(
        "/api/education",
        json={
            "institution": "Example University",
            "degree": "BSc",
            "field_of_study": "Computer Science",
            "start_year": 2020,
            "end_year": 2024,
            "grade": "First Class",
        },
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    assert user_client.get(f"/api/education/{record_id}").status_code == 200
    updated = user_client.patch(f"/api/education/{record_id}", json={"grade": "Distinction"})
    assert updated.status_code == 200
    assert updated.json()["grade"] == "Distinction"
    assert updated.json()["institution"] == "Example University"

    assert user_client.delete(f"/api/education/{record_id}").status_code == 204
    assert user_client.get(f"/api/education/{record_id}").status_code == 404


def test_education_validation(user_client: TestClient) -> None:
    assert user_client.post("/api/education", json={"degree": "BSc"}).status_code == 422
    assert user_client.post("/api/education", json={"institution": "U"}).status_code == 422
    assert user_client.post(
        "/api/education",
        json={"institution": "U", "degree": "BSc", "start_year": 2024, "end_year": 2020},
    ).status_code == 422
    assert user_client.post(
        "/api/education", json={"institution": "U", "degree": "BSc", "start_year": 1800}
    ).status_code == 422


def test_certification_crud(user_client: TestClient) -> None:
    created = user_client.post(
        "/api/certifications",
        json={
            "name": "Deep Learning Specialization",
            "issuer": "Example University",
            "issued_on": "2023-06-01",
            "expires_on": "2026-06-01",
            "credential_url": "https://example.com/credential/123",
        },
    )
    assert created.status_code == 201
    cert_id = created.json()["id"]

    assert user_client.get(f"/api/certifications/{cert_id}").status_code == 200
    updated = user_client.patch(
        f"/api/certifications/{cert_id}", json={"name": "Deep Learning Specialization v2"}
    )
    assert updated.status_code == 200
    assert user_client.delete(f"/api/certifications/{cert_id}").status_code == 204
    assert user_client.get(f"/api/certifications/{cert_id}").status_code == 404


def test_certification_validation(user_client: TestClient) -> None:
    assert user_client.post("/api/certifications", json={"name": "X"}).status_code == 422
    assert user_client.post(
        "/api/certifications",
        json={"name": "X", "issuer": "Y", "issued_on": "2024-01-01", "expires_on": "2023-01-01"},
    ).status_code == 422
    assert user_client.post(
        "/api/certifications", json={"name": "X", "issuer": "Y", "credential_url": "javascript:alert(1)"}
    ).status_code == 422


# ---------------------------------------------------------------------------
# Job roles (admin)
# ---------------------------------------------------------------------------
def test_job_role_crud(admin_client: TestClient, skill_ids: dict[str, int]) -> None:
    created = admin_client.post(
        "/api/admin/jobs",
        json={
            "title": "Recommendation Systems Engineer",
            "family": "ML Engineer",
            "seniority": "Mid",
            "description": "Build and tune ranking and retrieval models for recommendations.",
            "responsibilities": ["Build ranking models"],
            "skills": [
                {"skill_id": skill_ids["python"], "weight": 1.0},
                {"skill_id": skill_ids["sql"], "weight": 0.7},
            ],
        },
    )
    assert created.status_code == 201
    role_id = created.json()["id"]
    assert created.json()["slug"] == "recommendation-systems-engineer"
    assert len(created.json()["skills"]) == 2

    assert admin_client.get(f"/api/admin/jobs/{role_id}").status_code == 200
    assert admin_client.get(f"/api/jobs/{role_id}").status_code == 200, "public read must work"

    updated = admin_client.patch(f"/api/admin/jobs/{role_id}", json={"seniority": "Senior"})
    assert updated.status_code == 200
    assert updated.json()["seniority"] == "Senior"
    assert len(updated.json()["skills"]) == 2, "a field PATCH must not clear the skills"

    replaced = admin_client.put(
        f"/api/admin/jobs/{role_id}/skills",
        json={"skills": [
            {"skill_id": skill_ids["python"], "weight": 0.9},
            {"skill_id": skill_ids["docker"], "weight": 0.6},
            {"skill_id": skill_ids["aws"], "weight": 0.4},
        ]},
    )
    assert replaced.status_code == 200
    assert len(replaced.json()["skills"]) == 3

    assert admin_client.delete(f"/api/admin/jobs/{role_id}").status_code == 204
    assert admin_client.get(f"/api/jobs/{role_id}").status_code == 404


def test_job_role_validation(admin_client: TestClient, skill_ids: dict[str, int]) -> None:
    base = {
        "title": "Validation Role",
        "family": "ML Engineer",
        "description": "A description.",
        "skills": [{"skill_id": skill_ids["python"], "weight": 1.0}],
    }
    assert admin_client.post("/api/admin/jobs", json={**base, "description": ""}).status_code == 422
    assert admin_client.post("/api/admin/jobs", json={**base, "skills": []}).status_code == 422
    assert admin_client.post(
        "/api/admin/jobs", json={**base, "skills": [{"skill_id": skill_ids["python"], "weight": 0}]}
    ).status_code == 422
    assert admin_client.post(
        "/api/admin/jobs", json={**base, "skills": [{"skill_id": skill_ids["python"], "weight": 1.5}]}
    ).status_code == 422
    assert admin_client.post(
        "/api/admin/jobs", json={**base, "skills": [{"skill_id": 999999, "weight": 1.0}]}
    ).status_code == 422
    assert admin_client.post("/api/admin/jobs", json={**base, "family": ""}).status_code == 422


def test_duplicate_job_title_returns_409(
    admin_client: TestClient, skill_ids: dict[str, int]
) -> None:
    payload = {
        "title": "Duplicate Role",
        "family": "ML Engineer",
        "description": "A description.",
        "skills": [{"skill_id": skill_ids["python"], "weight": 1.0}],
    }
    assert admin_client.post("/api/admin/jobs", json=payload).status_code == 201
    assert admin_client.post("/api/admin/jobs", json=payload).status_code == 409


def test_replace_skills_is_atomic(admin_client: TestClient, skill_ids: dict[str, int]) -> None:
    """A failed validation must leave the previous requirement set intact."""
    role_id = admin_client.post(
        "/api/admin/jobs",
        json={
            "title": "Atomic Role",
            "family": "ML Engineer",
            "description": "A description.",
            "skills": [
                {"skill_id": skill_ids["python"], "weight": 1.0},
                {"skill_id": skill_ids["sql"], "weight": 0.5},
            ],
        },
    ).json()["id"]

    before = admin_client.get(f"/api/admin/jobs/{role_id}").json()["skills"]

    for bad in (
        {"skills": []},                                              # empty
        {"skills": [{"skill_id": 999999, "weight": 1.0}]},            # unknown skill
        {"skills": [{"skill_id": skill_ids["python"], "weight": 2.0}]},# out of range
        {"skills": [                                                 # duplicate
            {"skill_id": skill_ids["python"], "weight": 1.0},
            {"skill_id": skill_ids["python"], "weight": 0.5},
        ]},
    ):
        assert admin_client.put(f"/api/admin/jobs/{role_id}/skills", json=bad).status_code == 422

    after = admin_client.get(f"/api/admin/jobs/{role_id}").json()["skills"]
    assert len(after) == len(before)
    assert {s["skill_id"] for s in after} == {s["skill_id"] for s in before}
    assert [float(s["weight"]) for s in after] == [float(s["weight"]) for s in before]


def test_non_admin_cannot_write_jobs(client: TestClient, make_user, skill_ids) -> None:
    user = make_user(email="plain@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "Should Not Exist",
        "family": "F",
        "description": "d",
        "skills": [{"skill_id": skill_ids["python"], "weight": 1.0}],
    }
    assert client.post("/api/admin/jobs", json=payload, headers=headers).status_code == 403
    assert client.get("/api/admin/jobs", headers=headers).status_code == 403
    assert client.get("/api/admin/overview", headers=headers).status_code == 403


def test_anonymous_cannot_reach_admin(client: TestClient) -> None:
    for method, path in (
        ("get", "/api/admin/overview"),
        ("get", "/api/admin/users"),
        ("get", "/api/admin/jobs"),
        ("get", "/api/admin/taxonomy"),
        ("get", "/api/admin/evaluation"),
        ("get", "/api/admin/feedback"),
    ):
        response = getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} returned {response.status_code}"


def test_public_job_read_needs_no_token(client: TestClient, role_seed) -> None:
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/jobs/families").status_code == 200
    assert client.get(f"/api/jobs/{role_seed[0].id}").status_code == 200
    # Inactive roles are hidden from the public list.
    assert all(item["is_active"] for item in client.get("/api/jobs").json()["items"])


def test_families_endpoint(client: TestClient, role_seed) -> None:
    families = client.get("/api/jobs/families").json()
    assert families
    assert all({"family", "count"} == set(f) for f in families)
    assert sum(f["count"] for f in families) == len(role_seed)


# ---------------------------------------------------------------------------
# Taxonomy administration
# ---------------------------------------------------------------------------
def test_taxonomy_admin_crud(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/admin/taxonomy",
        json={
            "name": "Example Skill",
            "category": "ML Frameworks",
            "description": "A skill added through the admin panel.",
            "aliases": ["ex-skill", "example-skill-alias"],
        },
    )
    assert created.status_code == 201
    skill_id = created.json()["id"]
    assert created.json()["slug"] == "example-skill"
    assert set(created.json()["aliases"]) == {"ex-skill", "example-skill-alias"}

    listed = admin_client.get("/api/admin/taxonomy", params={"q": "Example Skill"}).json()
    assert listed["total"] >= 1

    updated = admin_client.patch(
        f"/api/admin/taxonomy/{skill_id}", json={"description": "Updated description."}
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated description."
    assert len(updated.json()["aliases"]) == 2, "a PATCH without aliases cleared them"

    assert admin_client.delete(f"/api/admin/taxonomy/{skill_id}").status_code == 204


def test_taxonomy_rejects_alias_collisions(admin_client: TestClient) -> None:
    """A collision would make one skill undetectable, so it is refused."""
    response = admin_client.post(
        "/api/admin/taxonomy",
        json={
            "name": "Colliding Skill",
            "category": "ML Frameworks",
            "aliases": ["sklearn"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "alias_conflict"


def test_taxonomy_rejects_duplicate_name(admin_client: TestClient) -> None:
    assert admin_client.post(
        "/api/admin/taxonomy", json={"name": "Python", "category": "Programming & Core"}
    ).status_code == 409


def test_in_use_skill_cannot_be_deleted(admin_client: TestClient, role_seed, taxonomy_seed) -> None:
    """A taxonomy entry a role depends on must not vanish."""
    response = admin_client.delete(f"/api/admin/taxonomy/{taxonomy_seed[0].id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "skill_in_use"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def test_dashboard_summary_is_real(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    user_client.post("/api/skills", json={"skill_id": skill_ids["python"]})
    user_client.post("/api/projects", json={"title": "P", "description": "d"})
    user_client.post("/api/education", json={"institution": "U", "degree": "BSc"})
    user_client.post("/api/certifications", json={"name": "C", "issuer": "I"})

    summary = user_client.get("/api/dashboard/summary").json()
    assert summary["skills_count"] == 1
    assert summary["projects_count"] == 1
    assert summary["education_count"] == 1
    assert summary["certifications_count"] == 1
    assert summary["resume_uploads_count"] == 0
    assert summary["total_recommendation_runs"] == 0
    assert summary["top_compatibility_pct"] is None
    assert "12,847" not in str(summary) and "94%" not in str(summary)


def test_dashboard_completeness_moves_with_real_data(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    before = user_client.get("/api/dashboard/completeness").json()
    assert 0 <= before["score"] <= 100
    assert before["steps"] and before["next_action"] is not None

    user_client.post("/api/profile", json={"headline": "ML Engineer"})
    user_client.post("/api/skills", json={"skill_id": skill_ids["python"]})
    after = user_client.get("/api/dashboard/completeness").json()
    assert after["score"] > before["score"], "the completeness score did not react to real data"


def test_admin_overview_is_real(admin_client: TestClient, role_seed, taxonomy_seed) -> None:
    overview = admin_client.get("/api/admin/overview").json()
    assert overview["role_count"] == len(role_seed)
    assert overview["active_role_count"] == len(role_seed)
    assert overview["skill_count"] == len(taxonomy_seed)
    assert overview["user_count"] >= 1
    assert overview["families"]
    assert overview["top_skills"]
