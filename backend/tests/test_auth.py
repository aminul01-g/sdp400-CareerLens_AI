"""T054 — registration, login, and the session contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token
from app.models.user import User, UserRole

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
ME = "/api/auth/me"

GOOD_PASSWORD = "Str0ngPassw0rd"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_register_returns_user_and_token(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={"name": "New User", "email": "new@example.com", "password": GOOD_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "user"
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == 1440 * 60


def test_register_never_returns_password_hash(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={"name": "Hash Check", "email": "hash@example.com", "password": GOOD_PASSWORD},
    )
    assert "password_hash" not in response.text
    assert "password" not in response.json()["user"]


def test_register_hashes_password_with_bcrypt(client: TestClient, db: Session) -> None:
    client.post(
        REGISTER,
        json={"name": "Hashed", "email": "hashed@example.com", "password": GOOD_PASSWORD},
    )
    user = db.query(User).filter(User.email == "hashed@example.com").one()
    assert user.password_hash.startswith("$2b$")
    assert GOOD_PASSWORD not in user.password_hash


def test_register_creates_a_profile_in_the_same_transaction(client: TestClient) -> None:
    """A user who never fills in a profile still has a consistent row."""
    response = client.post(
        REGISTER,
        json={"name": "Profiled", "email": "profiled@example.com", "password": GOOD_PASSWORD},
    )
    token = response.json()["access_token"]
    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["skills_count"] == 0


def test_register_stores_education_level(client: TestClient) -> None:
    """T062: the legacy register form collected this and silently dropped it."""
    response = client.post(
        REGISTER,
        json={
            "name": "Educated",
            "email": "educated@example.com",
            "password": GOOD_PASSWORD,
            "education_level": "Undergraduate",
        },
    )
    token = response.json()["access_token"]
    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile.json()["education_level"] == "Undergraduate"


@pytest.mark.parametrize(
    ("email_a", "email_b"),
    [
        ("dup@example.com", "dup@example.com"),
        ("Case@Example.COM", "case@example.com"),  # S9: case-insensitive uniqueness
        ("  spaced@example.com", "spaced@example.com"),  # S9: trimmed
    ],
)
def test_duplicate_email_returns_409(
    client: TestClient, email_a: str, email_b: str
) -> None:
    first = client.post(REGISTER, json={"name": "A", "email": email_a, "password": GOOD_PASSWORD})
    assert first.status_code == 201
    second = client.post(REGISTER, json={"name": "B", "email": email_b, "password": GOOD_PASSWORD})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_exists"


def test_duplicate_email_is_409_not_400(client: TestClient) -> None:
    """The legacy auth.py:17 returned 400, which means 'malformed', not 'taken'."""
    client.post(REGISTER, json={"name": "A", "email": "x@example.com", "password": GOOD_PASSWORD})
    response = client.post(
        REGISTER, json={"name": "B", "email": "x@example.com", "password": GOOD_PASSWORD}
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "password",
    [
        "short1A",  # too short
        "alllowercase1",  # no uppercase
        "ALLUPPERCASE1",  # no lowercase
        "NoDigitsHere",  # no digit
        "Password",  # no digit
        "password1",  # no uppercase
    ],
)
def test_weak_password_returns_422(client: TestClient, password: str) -> None:
    response = client.post(
        REGISTER, json={"name": "Weak", "email": "weak@example.com", "password": password}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert any(e["field"] == "password" for e in body["error"]["errors"])


def test_password_policy_is_the_documented_one(client: TestClient) -> None:
    """8+ chars, upper, lower, digit — matching the client-side zod rule."""
    assert client.post(
        REGISTER,
        json={"name": "Ok", "email": "ok1@example.com", "password": "Abcdefg1"},
    ).status_code == 201
    assert client.post(
        REGISTER,
        json={"name": "Ok", "email": "ok2@example.com", "password": "Abc1"},
    ).status_code == 422


def test_malformed_email_returns_422(client: TestClient) -> None:
    response = client.post(
        REGISTER, json={"name": "X", "email": "not-an-email", "password": GOOD_PASSWORD}
    )
    assert response.status_code == 422
    assert any(e["field"] == "email" for e in response.json()["error"]["errors"])


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_invalid_name_returns_422(client: TestClient, name: str) -> None:
    response = client.post(
        REGISTER, json={"name": name, "email": "n@example.com", "password": GOOD_PASSWORD}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def test_login_success(client: TestClient) -> None:
    client.post(REGISTER, json={"name": "L", "email": "login@example.com", "password": GOOD_PASSWORD})
    response = client.post(LOGIN, json={"email": "login@example.com", "password": GOOD_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "login@example.com"


def test_login_is_case_insensitive(client: TestClient) -> None:
    client.post(REGISTER, json={"name": "L", "email": "case@example.com", "password": GOOD_PASSWORD})
    assert client.post(
        LOGIN, json={"email": "CASE@EXAMPLE.COM", "password": GOOD_PASSWORD}
    ).status_code == 200


def test_wrong_password_returns_401(client: TestClient) -> None:
    client.post(REGISTER, json={"name": "L", "email": "wrong@example.com", "password": GOOD_PASSWORD})
    assert client.post(
        LOGIN, json={"email": "wrong@example.com", "password": "Wr0ngPassword"}
    ).status_code == 401


def test_unknown_email_and_wrong_password_are_indistinguishable(client: TestClient) -> None:
    """Account-enumeration defence: identical status, code, and message."""
    client.post(REGISTER, json={"name": "L", "email": "real@example.com", "password": GOOD_PASSWORD})
    wrong_password = client.post(
        LOGIN, json={"email": "real@example.com", "password": "Wr0ngPassword"}
    )
    unknown_email = client.post(
        LOGIN, json={"email": "ghost@example.com", "password": GOOD_PASSWORD}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["code"] == unknown_email.json()["error"]["code"]
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_deactivated_account_cannot_log_in(client: TestClient, db: Session) -> None:
    client.post(REGISTER, json={"name": "D", "email": "off@example.com", "password": GOOD_PASSWORD})
    user = db.query(User).filter(User.email == "off@example.com").one()
    user.is_active = False
    db.flush()
    response = client.post(LOGIN, json={"email": "off@example.com", "password": GOOD_PASSWORD})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "account_disabled"


def test_login_updates_last_login_at(client: TestClient, db: Session) -> None:
    client.post(REGISTER, json={"name": "L", "email": "ll@example.com", "password": GOOD_PASSWORD})
    assert db.query(User).filter(User.email == "ll@example.com").one().last_login_at is None
    client.post(LOGIN, json={"email": "ll@example.com", "password": GOOD_PASSWORD})
    assert db.query(User).filter(User.email == "ll@example.com").one().last_login_at is not None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
def test_me_requires_a_token(client: TestClient) -> None:
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_me_with_a_valid_token(client: TestClient) -> None:
    token = client.post(
        REGISTER, json={"name": "M", "email": "me@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    response = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_me_rejects_a_garbage_token(client: TestClient) -> None:
    response = client.get(ME, headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_invalid"


def test_expired_token_returns_401_token_expired(client: TestClient, make_user) -> None:
    """The legacy tokens had no expiry at all (auth.py:31)."""
    user = make_user(email="exp@example.com")
    expired = create_access_token(
        subject=str(user.id), role=user.role.value, expires_delta=timedelta(seconds=-60)
    )[0]
    response = client.get(ME, headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_token_carries_the_required_claims(client: TestClient) -> None:
    token = client.post(
        REGISTER, json={"name": "C", "email": "c@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    claims = decode_access_token(token)
    for claim in ("sub", "role", "exp", "iat"):
        assert claim in claims, f"{claim} missing from the token"
    assert claims["exp"] > claims["iat"]


def test_refresh_issues_a_new_token_and_takes_role_from_the_database(
    client: TestClient, make_user
) -> None:
    """A demoted admin must lose admin on refresh, not at token expiry."""
    user = make_user(email="ref@example.com")
    token = create_access_token(subject=str(user.id), role="admin")[0]
    headers = {"Authorization": f"Bearer {token}"}

    # Escalate in the DB, then refresh: the response must reflect the DB.
    db_user = client.app.dependency_overrides[next(iter(client.app.dependency_overrides))]()
    db_user_obj = db_user.get(User, user.id)
    db_user_obj.role = UserRole.ADMIN
    db_user.commit()

    refreshed = client.post("/api/auth/refresh", json={}, headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["user"]["role"] == "admin"


def test_logout_returns_204(client: TestClient) -> None:
    token = client.post(
        REGISTER, json={"name": "O", "email": "o@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204


def test_logout_requires_a_token(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 401


def test_patch_me_changes_the_name(client: TestClient) -> None:
    token = client.post(
        REGISTER, json={"name": "Old", "email": "pm@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    response = client.patch(ME, json={"name": "New Name"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_password_change_requires_the_current_password(client: TestClient) -> None:
    token = client.post(
        REGISTER, json={"name": "P", "email": "pc@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.patch(ME, json={"password": "N3wPassword"}, headers=headers).status_code == 403
    assert client.patch(
        ME, json={"password": "N3wPassword", "current_password": "wrong"}, headers=headers
    ).status_code == 401
    assert client.patch(
        ME, json={"password": "N3wPassword", "current_password": GOOD_PASSWORD}, headers=headers
    ).status_code == 200
    assert client.post(
        LOGIN, json={"email": "pc@example.com", "password": "N3wPassword"}
    ).status_code == 200


def test_delete_me_cascades(client: TestClient, db: Session) -> None:
    token = client.post(
        REGISTER, json={"name": "D", "email": "dm@example.com", "password": GOOD_PASSWORD}
    ).json()["access_token"]
    user_id = client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()["id"]
    assert client.delete(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 204
    assert db.get(User, user_id) is None
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_issued_now_is_valid_now() -> None:
    """A guard against a clock/expiry mistake in token issuance."""
    now = datetime.now(UTC)
    token = create_access_token(subject="1", role="user", expires_delta=timedelta(minutes=5))[0]
    claims = decode_access_token(token)
    assert datetime.fromtimestamp(claims["iat"], UTC) >= now - timedelta(seconds=5)
    assert datetime.fromtimestamp(claims["exp"], UTC) > now
