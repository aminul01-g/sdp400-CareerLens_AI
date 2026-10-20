"""The audit log.

Three properties are worth testing, and they are different in kind:

1. **The change and its record are written together.** An audit log that can
   disagree with the data is worse than none, because it looks authoritative.
2. **The record outlives the actor.** Deleting an account must not delete the
   history of what that account did.
3. **Anonymous failures are recorded too.** A failed sign-in has no user, and
   it is precisely the event an administrator most wants to see.

Everything else — the read endpoint, the filters — is plumbing over those.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def _entries(db: Session) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)).all())


# --------------------------------------------------------------------------- #
# authentication events
# --------------------------------------------------------------------------- #


def test_registration_is_recorded(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/auth/register",
        json={"name": "Audit User", "email": "audit@example.com", "password": "Str0ngPassw0rd"},
    )
    assert response.status_code == 201, response.text

    actions = [entry.action for entry in _entries(db)]
    assert "auth.registered" in actions


def test_a_successful_sign_in_is_recorded(client: TestClient, make_user, db: Session) -> None:
    user = make_user(email="signin@example.com")
    response = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    )
    assert response.status_code == 200, response.text

    entry = next(e for e in _entries(db) if e.action == "auth.login_succeeded")
    assert entry.actor_id == user.id
    assert entry.actor_email == user.email


def test_a_failed_sign_in_is_recorded(client: TestClient, db: Session) -> None:
    """A failed sign-in has no user, and that is exactly why it needs recording."""
    response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert response.status_code == 401

    entry = next(e for e in _entries(db) if e.action == "auth.login_failed")
    assert entry.actor_id is None
    assert entry.actor_email is None
    assert "nobody@example.com" in entry.summary


def test_a_wrong_password_is_recorded(client: TestClient, make_user, db: Session) -> None:
    user = make_user(email="wrongpw@example.com")
    response = client.post(
        "/api/auth/login", json={"email": user.email, "password": "not-the-password"}
    )
    assert response.status_code == 401
    assert any(e.action == "auth.login_failed" for e in _entries(db))


def test_a_password_change_is_recorded(client: TestClient, make_user, db: Session) -> None:
    user = make_user(email="pwchange@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.patch(
        "/api/auth/me",
        json={"password": "N3wPassw0rd!", "current_password": "Str0ngPassw0rd"},
    )
    assert response.status_code == 200, response.text

    entry = next(e for e in _entries(db) if e.action == "auth.password_changed")
    assert entry.actor_id == user.id


# --------------------------------------------------------------------------- #
# administrative changes
# --------------------------------------------------------------------------- #


@pytest.fixture
def admin_client(client: TestClient, make_user) -> TestClient:
    user = make_user(email="admin@example.com", role="admin")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_a_role_promotion_is_recorded(
    admin_client: TestClient, make_user, db: Session
) -> None:
    target = make_user(email="promote@example.com")
    response = admin_client.patch(f"/api/admin/users/{target.id}/role", json={"role": "admin"})
    assert response.status_code == 200, response.text

    entry = next(e for e in _entries(db) if e.action == "user.role_changed")
    assert entry.entity_type == "user"
    assert entry.entity_id == str(target.id)
    assert entry.changes == {"before": "user", "after": "admin"}


def test_creating_a_job_role_is_recorded(admin_client: TestClient, db: Session) -> None:
    skill = admin_client.post(
        "/api/admin/taxonomy", json={"name": "Audited Skill", "category": "Programming & Core"}
    )
    assert skill.status_code == 201, skill.text

    response = admin_client.post(
        "/api/admin/jobs",
        json={
            "title": "Audited Role",
            "family": "Auditing",
            "description": "A role that exists so the audit log has something to record.",
            "skills": [{"skill_id": skill.json()["id"], "weight": 1.0}],
        },
    )
    assert response.status_code == 201, response.text

    entry = next(e for e in _entries(db) if e.action == "job_role.created")
    assert entry.entity_type == "job_role"
    assert "Audited Role" in entry.summary


def test_editing_a_job_role_records_the_before_and_after(
    admin_client: TestClient, db: Session
) -> None:
    skill = admin_client.post(
        "/api/admin/taxonomy", json={"name": "Before After Skill", "category": "Programming & Core"}
    ).json()
    created = admin_client.post(
        "/api/admin/jobs",
        json={
            "title": "Before After Role",
            "family": "Auditing",
            "description": "A role whose family is about to change.",
            "skills": [{"skill_id": skill["id"], "weight": 1.0}],
        },
    ).json()

    response = admin_client.patch(
        f"/api/admin/jobs/{created['id']}", json={"family": "Changed Family"}
    )
    assert response.status_code == 200, response.text

    entry = next(e for e in _entries(db) if e.action == "job_role.updated")
    assert entry.changes["before"]["family"] == "Auditing"
    assert entry.changes["after"]["family"] == "Changed Family"


def test_replacing_a_roles_skill_set_is_recorded(
    admin_client: TestClient, db: Session
) -> None:
    first = admin_client.post(
        "/api/admin/taxonomy", json={"name": "Set Skill A", "category": "Programming & Core"}
    ).json()
    second = admin_client.post(
        "/api/admin/taxonomy", json={"name": "Set Skill B", "category": "Programming & Core"}
    ).json()
    created = admin_client.post(
        "/api/admin/jobs",
        json={
            "title": "Set Role",
            "family": "Auditing",
            "description": "A role whose skill set is about to be replaced.",
            "skills": [{"skill_id": first["id"], "weight": 1.0}],
        },
    ).json()

    response = admin_client.put(
        f"/api/admin/jobs/{created['id']}/skills",
        json={"skills": [{"skill_id": second["id"], "weight": 0.8}]},
    )
    assert response.status_code == 200, response.text

    entry = next(e for e in _entries(db) if e.action == "job_role.skills_replaced")
    assert str(first["id"]) in entry.changes["before"]
    assert str(second["id"]) in entry.changes["after"]


def test_a_taxonomy_change_is_recorded(admin_client: TestClient, db: Session) -> None:
    created = admin_client.post(
        "/api/admin/taxonomy", json={"name": "Taxonomy Audited", "category": "Programming & Core"}
    )
    assert created.status_code == 201, created.text

    entry = next(e for e in _entries(db) if e.action == "taxonomy.skill_created")
    assert "Taxonomy Audited" in entry.summary


# --------------------------------------------------------------------------- #
# the properties that make it worth having
# --------------------------------------------------------------------------- #


def test_the_record_outlives_the_actor(client: TestClient, make_user, db: Session) -> None:
    """Deleting an account must not delete the history of what it did."""
    user = make_user(email="ghost@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.post("/api/profile", json={"headline": "Ghost"})

    assert client.delete("/api/auth/me").status_code == 204

    entry = next(
        e for e in _entries(db) if e.action == "auth.login_succeeded" and e.actor_email == user.email
    )
    assert entry.actor_id is None, "the foreign key should be nulled, not cascaded"
    assert entry.actor_email == user.email, "the email is what survives"


def test_the_audit_row_and_the_change_are_one_transaction(
    client: TestClient, db: Session
) -> None:
    """A failed change must not leave a record of a change that did not happen."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Transactional",
            "email": "transactional@example.com",
            "password": "Str0ngPassw0rd",
        },
    )
    before = len(_entries(db))

    # A registration with an address that is already taken.
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Transactional",
            "email": "transactional@example.com",
            "password": "Str0ngPassw0rd",
        },
    )
    assert response.status_code == 409

    assert len(_entries(db)) == before, "a rejected registration was still recorded"


# --------------------------------------------------------------------------- #
# the read endpoint
# --------------------------------------------------------------------------- #


def test_the_audit_endpoint_requires_an_admin(client: TestClient, make_user) -> None:
    assert client.get("/api/admin/audit").status_code == 401

    user = make_user(email="notadmin@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    assert client.get("/api/admin/audit").status_code == 403


def test_the_audit_endpoint_lists_entries(admin_client: TestClient, db: Session) -> None:
    admin_client.post(
        "/api/admin/taxonomy", json={"name": "Listed Skill", "category": "Programming & Core"}
    )
    response = admin_client.get("/api/admin/audit")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"]
    assert "summary" in body["items"][0]


def test_the_audit_endpoint_filters_by_action(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/admin/taxonomy", json={"name": "Filtered Skill", "category": "Programming & Core"}
    )
    response = admin_client.get("/api/admin/audit", params={"action": "taxonomy.skill_created"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 1
    assert all(item["action"] == "taxonomy.skill_created" for item in body["items"])


def test_an_unknown_action_is_refused(client: TestClient, db: Session) -> None:
    """A typo in an action name must be a failure, not a row nobody can find."""
    from app.services import audit_service

    with pytest.raises(ValueError, match="Unknown audit action"):
        audit_service.record(
            db, action="not.a.real.action", entity_type="user", summary="nope"
        )
