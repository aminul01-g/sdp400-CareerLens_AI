"""Email verification and password reset.

The two flows the limitations document used to list as missing. The tests are
mostly about the ways these flows go wrong rather than about the happy path:

* **A reset request must not reveal who has an account.** The response, the
  status code and the shape of the body are identical either way. An endpoint
  that answers "no such account" is an enumeration oracle, and the legacy
  login route was one.
* **A token is single-use.** Using it twice must fail the second time.
* **A token expires.**
* **A reset invalidates the sessions that were outstanding.** That is the
  whole point of resetting a password because you think it is compromised.
* **Only the hash is stored.** A database dump must not contain a working
  reset link.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth_token import AuthToken
from app.models.user import User


def _mailbox() -> Path:
    return Path(get_settings().mail_dir)


def _latest_mail() -> str:
    """The most recent message written to the development mailbox."""
    files = sorted(_mailbox().glob("*.txt"), key=lambda p: p.stat().st_mtime)
    assert files, "no mail was written"
    return files[-1].read_text(encoding="utf-8")


def _token_from_mail() -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", _latest_mail())
    assert match, "the email did not contain a token"
    return match.group(1)


# --------------------------------------------------------------------------- #
# email verification
# --------------------------------------------------------------------------- #


def test_registration_sends_a_verification_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"name": "Verify Me", "email": "verify@example.com", "password": "Str0ngPassw0rd"},
    )
    assert response.status_code == 201, response.text
    assert "verify@example.com" in _latest_mail()


def test_a_verification_token_marks_the_address_verified(
    client: TestClient, db: Session
) -> None:
    client.post(
        "/api/auth/register",
        json={"name": "Verify Me", "email": "verify2@example.com", "password": "Str0ngPassw0rd"},
    )
    token = _token_from_mail()

    response = client.post("/api/auth/verify-email", json={"token": token})
    assert response.status_code == 200, response.text
    assert response.json()["is_verified"] is True

    user = db.scalar(select(User).where(User.email == "verify2@example.com"))
    assert user is not None
    assert user.is_verified is True
    assert user.email_verified_at is not None


def test_a_verification_token_is_single_use(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"name": "Once", "email": "once@example.com", "password": "Str0ngPassw0rd"},
    )
    token = _token_from_mail()

    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    second = client.post("/api/auth/verify-email", json={"token": token})
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "invalid_token"


def test_an_unknown_verification_token_is_refused(client: TestClient) -> None:
    response = client.post("/api/auth/verify-email", json={"token": "not-a-real-token-value"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_token"


def test_only_the_hash_of_a_token_is_stored(client: TestClient, db: Session) -> None:
    """A database dump must not contain a working reset link."""
    client.post(
        "/api/auth/register",
        json={"name": "Hashed", "email": "hashed@example.com", "password": "Str0ngPassw0rd"},
    )
    token = _token_from_mail()

    rows = db.scalars(select(AuthToken)).all()
    assert rows
    for row in rows:
        assert row.token_hash != token
        assert len(row.token_hash) == 64


def test_a_new_verification_email_invalidates_the_old_token(
    client: TestClient, make_user
) -> None:
    user = make_user(email="resend@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.post("/api/auth/resend-verification").status_code == 202
    first = _token_from_mail()

    assert client.post("/api/auth/resend-verification").status_code == 202
    second = _token_from_mail()
    assert first != second

    # The first token no longer works.
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 422
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 200


# --------------------------------------------------------------------------- #
# password reset
# --------------------------------------------------------------------------- #


def test_a_reset_link_is_emailed(client: TestClient, make_user) -> None:
    user = make_user(email="forgot@example.com")
    response = client.post("/api/auth/forgot-password", json={"email": user.email})
    assert response.status_code == 202, response.text
    assert "forgot@example.com" in _latest_mail()


def test_the_response_is_the_same_for_an_unknown_address(client: TestClient) -> None:
    """The endpoint must not reveal who has an account."""
    known = client.post(
        "/api/auth/register",
        json={"name": "Known", "email": "known@example.com", "password": "Str0ngPassw0rd"},
    )
    assert known.status_code == 201

    response = client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert "if that address has an account" in body["message"].lower()

    # And the same for an address that does exist.
    same = client.post("/api/auth/forgot-password", json={"email": "known@example.com"})
    assert same.status_code == 202
    assert same.json() == body


def test_an_unknown_address_sends_no_mail(client: TestClient) -> None:
    before = set(_mailbox().glob("*.txt")) if _mailbox().exists() else set()
    client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    after = set(_mailbox().glob("*.txt")) if _mailbox().exists() else set()
    assert after == before


def test_a_reset_token_sets_a_new_password(client: TestClient, make_user) -> None:
    user = make_user(email="reset@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})
    token = _token_from_mail()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPassw0rd"},
    )
    assert response.status_code == 200, response.text

    # The new password works.
    login = client.post(
        "/api/auth/login", json={"email": user.email, "password": "BrandNewPassw0rd"}
    )
    assert login.status_code == 200, login.text
    # And the old one does not.
    old = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    )
    assert old.status_code == 401


def test_a_reset_token_is_single_use(client: TestClient, make_user) -> None:
    user = make_user(email="once-reset@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})
    token = _token_from_mail()

    first = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPassw0rd"},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "AnotherPassw0rd"},
    )
    assert second.status_code == 422


def test_a_new_reset_invalidates_the_old_token(client: TestClient, make_user) -> None:
    user = make_user(email="twice-reset@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})
    first = _token_from_mail()
    client.post("/api/auth/forgot-password", json={"email": user.email})
    second = _token_from_mail()
    assert first != second

    assert client.post(
        "/api/auth/reset-password", json={"token": first, "new_password": "BrandNewPassw0rd"}
    ).status_code == 422
    assert client.post(
        "/api/auth/reset-password", json={"token": second, "new_password": "BrandNewPassw0rd"}
    ).status_code == 200


def test_a_reset_token_enforces_the_password_policy(client: TestClient, make_user) -> None:
    user = make_user(email="weak@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})
    token = _token_from_mail()

    response = client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "weak"}
    )
    assert response.status_code == 422
    assert "password" in response.text.lower()


def test_a_reset_invalidates_the_outstanding_sessions(
    client: TestClient, make_user
) -> None:
    """The point of resetting a password is to stop the old sessions working."""
    user = make_user(email="stale@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # The session works before the reset.
    assert client.get("/api/auth/me").status_code == 200

    client.post("/api/auth/forgot-password", json={"email": user.email})
    reset_token = _token_from_mail()
    assert client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "BrandNewPassw0rd"},
    ).status_code == 200

    # And it does not afterwards.
    stale = client.get("/api/auth/me")
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "session_stale"


def test_a_password_change_also_invalidates_outstanding_sessions(
    client: TestClient, make_user
) -> None:
    user = make_user(email="changed@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.patch(
        "/api/auth/me",
        json={"password": "An0therPassw0rd", "current_password": "Str0ngPassw0rd"},
    )
    assert response.status_code == 200, response.text

    stale = client.get("/api/auth/me")
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "session_stale"


def test_an_expired_token_is_refused(client: TestClient, make_user, db: Session) -> None:
    from datetime import UTC, datetime, timedelta

    from app.core.tokens import hash_token

    user = make_user(email="expired@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})
    token = _token_from_mail()

    # Age the token out in the database, rather than waiting for the clock.
    row = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == hash_token(token))
    )
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPassw0rd"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "expired_token"


# --------------------------------------------------------------------------- #
# the optional gate
# --------------------------------------------------------------------------- #


def test_an_unverified_user_may_sign_in_by_default(
    client: TestClient, make_user
) -> None:
    """The gate is off by default: a product that locks out a user who has not
    clicked a link in an email reads as broken."""
    user = make_user(email="unverified@example.com")
    response = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    )
    assert response.status_code == 200, response.text


def test_the_gate_can_be_switched_on(monkeypatch, client: TestClient, make_user) -> None:
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    get_settings.cache_clear()
    try:
        user = make_user(email="gated@example.com")
        response = client.post(
            "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "email_unverified"
    finally:
        get_settings.cache_clear()
