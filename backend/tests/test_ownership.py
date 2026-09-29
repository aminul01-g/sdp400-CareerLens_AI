"""T080 — cross-user access is impossible.

Every user-owned resource is scoped by ``user_id`` **in the query**, so another
user's row is invisible rather than forbidden. That is why these tests assert
``404`` and not ``403``: a ``403`` confirms the row exists, which is itself an
information leak (the legacy IDOR at ``guidance.py:31``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.education import Certification, EducationRecord
from app.models.project import Project
from app.models.resume import ResumeUpload
from app.models.user_skill import SkillSource, UserSkill

NOT_FOUND = 404


@pytest.fixture
def alice(make_user):
    return make_user(email="alice@example.com", name="Alice")


@pytest.fixture
def bob(make_user):
    return make_user(email="bob@example.com", name="Bob")


def _authenticated_client(db: Session, email: str) -> TestClient:
    """A *separate* TestClient bound to the same database session.

    Two identities cannot be simulated on one client: ``client.headers`` is shared
    state, so the second login would silently replace the first token and every
    "cross-user" request would be made by Alice while believing it was Bob.
    """
    from app.db.session import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    http = TestClient(app, raise_server_exceptions=False)

    response = http.post(
        "/api/auth/login", json={"email": email, "password": "Str0ngPassw0rd"}
    )
    assert response.status_code == 200, response.text
    http.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
    return http


@pytest.fixture
def alice_client(db: Session, alice) -> TestClient:
    return _authenticated_client(db, alice.email)


@pytest.fixture
def bob_client(db: Session, bob) -> TestClient:
    return _authenticated_client(db, bob.email)


def _alice_project(client: TestClient) -> int:
    return client.post(
        "/api/projects",
        json={"title": "Alice Project", "description": "Alice's private project."},
    ).json()["id"]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def test_cannot_read_another_users_project(
    alice_client: TestClient, bob_client: TestClient
) -> None:
    project_id = _alice_project(alice_client)
    assert bob_client.get(f"/api/projects/{project_id}").status_code == NOT_FOUND


def test_cannot_update_another_users_project(
    alice_client: TestClient, bob_client: TestClient
) -> None:
    project_id = _alice_project(alice_client)
    response = bob_client.patch(
        f"/api/projects/{project_id}", json={"title": "Hijacked"}
    )
    assert response.status_code == NOT_FOUND
    # And Alice's data is genuinely untouched.
    assert alice_client.get(f"/api/projects/{project_id}").json()["title"] == "Alice Project"


def test_cannot_delete_another_users_project(
    alice_client: TestClient, bob_client: TestClient
) -> None:
    project_id = _alice_project(alice_client)
    assert bob_client.delete(f"/api/projects/{project_id}").status_code == NOT_FOUND
    assert alice_client.get(f"/api/projects/{project_id}").status_code == 200


# ---------------------------------------------------------------------------
# Education and certifications
# ---------------------------------------------------------------------------
def test_cannot_touch_another_users_education(
    alice_client: TestClient, bob_client: TestClient
) -> None:
    record_id = alice_client.post(
        "/api/education",
        json={"institution": "Alice University", "degree": "BSc"},
    ).json()["id"]
    assert bob_client.get(f"/api/education/{record_id}").status_code == NOT_FOUND
    assert bob_client.patch(
        f"/api/education/{record_id}", json={"degree": "PhD"}
    ).status_code == NOT_FOUND
    assert bob_client.delete(f"/api/education/{record_id}").status_code == NOT_FOUND


def test_cannot_touch_another_users_certification(
    alice_client: TestClient, bob_client: TestClient
) -> None:
    cert_id = alice_client.post(
        "/api/certifications", json={"name": "Alice Cert", "issuer": "Alice Institute"}
    ).json()["id"]
    assert bob_client.get(f"/api/certifications/{cert_id}").status_code == NOT_FOUND
    assert bob_client.patch(
        f"/api/certifications/{cert_id}", json={"name": "Hijacked"}
    ).status_code == NOT_FOUND
    assert bob_client.delete(f"/api/certifications/{cert_id}").status_code == NOT_FOUND


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
def test_cannot_update_or_remove_another_users_skill(
    alice_client: TestClient, bob_client: TestClient, skill_ids: dict[str, int]
) -> None:
    skill_id = skill_ids["python"]
    alice_client.post("/api/skills", json={"skill_id": skill_id, "proficiency": 5})

    assert bob_client.patch(
        f"/api/skills/{skill_id}", json={"proficiency": 1}
    ).status_code == NOT_FOUND
    assert bob_client.delete(f"/api/skills/{skill_id}").status_code == NOT_FOUND

    # Alice still has it, at her own proficiency.
    alice_skills = alice_client.get("/api/skills").json()
    assert any(s["skill_id"] == skill_id and s["proficiency"] == 5 for s in alice_skills)


def test_adding_a_skill_another_user_has_is_allowed(
    alice_client: TestClient, bob_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """Skills are a shared taxonomy; two users holding the same skill is normal."""
    skill_id = skill_ids["python"]
    assert alice_client.post("/api/skills", json={"skill_id": skill_id}).status_code == 201
    assert bob_client.post("/api/skills", json={"skill_id": skill_id}).status_code == 201


# ---------------------------------------------------------------------------
# CV uploads
# ---------------------------------------------------------------------------
def test_cannot_read_another_users_cv(
    alice_client: TestClient, bob_client: TestClient, db: Session, monkeypatch
) -> None:
    """This is the S5 IDOR: the legacy route had no auth and no ownership check."""
    from app.models.user import User

    real_alice = db.scalar(select(User).where(User.email == "alice@example.com"))
    upload = ResumeUpload(
        user_id=real_alice.id,
        original_filename="secret.pdf",
        stored_filename="secret.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        extracted_text="Alice's private CV text.",
        status="extracted",
    )
    db.add(upload)
    db.flush()

    assert bob_client.get(f"/api/cv/{upload.id}").status_code == NOT_FOUND
    assert bob_client.get(f"/api/cv/{upload.id}/text").status_code == NOT_FOUND
    assert bob_client.delete(f"/api/cv/{upload.id}").status_code == NOT_FOUND


# ---------------------------------------------------------------------------
# Recommendation runs
# ---------------------------------------------------------------------------
def test_cannot_read_another_users_recommendation_run(
    alice_client: TestClient, bob_client: TestClient, db: Session, skill_ids
) -> None:
    from app.models.recommendation import RecommendationRun
    from app.models.user import User

    alice = db.scalar(select(User).where(User.email == "alice@example.com"))
    run = RecommendationRun(
        user_id=alice.id,
        profile_snapshot={},
        coverage_weight=0.6,
        tfidf_weight=0.4,
        engine_version="1.0.0",
        candidate_count=0,
    )
    db.add(run)
    db.flush()
    assert bob_client.get(f"/api/recommendations/runs/{run.id}").status_code == NOT_FOUND


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------
def test_lists_only_return_the_callers_rows(
    alice_client: TestClient, bob_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """A missing ``user_id`` predicate on a list is where a leak would hide."""
    alice_client.post("/api/projects", json={"title": "A1", "description": "x"})
    alice_client.post("/api/projects", json={"title": "A2", "description": "x"})
    bob_client.post("/api/projects", json={"title": "B1", "description": "x"})

    alice_titles = {p["title"] for p in alice_client.get("/api/projects").json()["items"]}
    bob_titles = {p["title"] for p in bob_client.get("/api/projects").json()["items"]}
    assert alice_titles == {"A1", "A2"}
    assert bob_titles == {"B1"}

    alice_client.post("/api/skills", json={"skill_id": skill_ids["python"]})
    alice_client.post("/api/skills", json={"skill_id": skill_ids["sql"]})
    bob_client.post("/api/skills", json={"skill_id": skill_ids["java"]})
    assert len(alice_client.get("/api/skills").json()) == 2
    assert len(bob_client.get("/api/skills").json()) == 1

    alice_client.post("/api/education", json={"institution": "AU", "degree": "BSc"})
    alice_client.post("/api/certifications", json={"name": "AC", "issuer": "AI"})
    assert alice_client.get("/api/education").json()["total"] == 1
    assert bob_client.get("/api/education").json()["total"] == 0
    assert alice_client.get("/api/certifications").json()["total"] == 1
    assert bob_client.get("/api/certifications").json()["total"] == 0


def test_profile_has_no_id_parameter(alice_client: TestClient) -> None:
    """IDOR is structurally impossible for the profile: there is no path id."""
    spec = alice_client.get("/openapi.json").json()
    assert "/api/profile" in spec["paths"]
    assert not any(path.startswith("/api/profile/") for path in spec["paths"])


def test_no_endpoint_accepts_a_user_id(alice_client: TestClient) -> None:
    """The identity always comes from the token, never from the body."""

    spec = alice_client.get("/openapi.json").json()
    offenders: list[str] = []
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method not in {"post", "patch", "put", "delete"}:
                continue
            body = operation.get("requestBody") or {}
            schema_name = (
                (body.get("content", {}).get("application/json", {}).get("schema", {}) or {}).get(
                    "$ref", ""
                )
                or (
                    (body.get("content", {}).get("application/json", {}).get("schema", {}) or {}).get(
                        "title", ""
                    )
                )
            )
            if "user_id" in schema_name:
                offenders.append(f"{method.upper()} {path} -> {schema_name}")
    assert not offenders, f"schemas exposing user_id: {offenders}"


def test_cascade_removes_the_whole_subtree(db: Session, make_user, taxonomy_seed) -> None:
    """T081: deleting a user removes every child in one statement (S10)."""

    from app.models.user import User

    user = make_user(email="cascade@example.com")
    db.add_all(
        [
            Project(user_id=user.id, title="P", description="d"),
            EducationRecord(user_id=user.id, institution="I", degree="BSc"),
            Certification(user_id=user.id, name="C", issuer="Issuer"),
            UserSkill(
                user_id=user.id,
                skill_id=taxonomy_seed[0].id,
                proficiency=3,
                source=SkillSource.MANUAL.value,
            ),
        ]
    )
    db.flush()
    user_id = user.id

    db.delete(user)
    db.commit()

    assert db.get(User, user_id) is None
    assert db.query(Project).filter(Project.user_id == user_id).count() == 0
    assert db.query(EducationRecord).filter(EducationRecord.user_id == user_id).count() == 0
    assert db.query(Certification).filter(Certification.user_id == user_id).count() == 0
    assert db.query(UserSkill).filter(UserSkill.user_id == user_id).count() == 0
    from app.models.profile import Profile

    assert db.query(Profile).filter(Profile.user_id == user_id).count() == 0
