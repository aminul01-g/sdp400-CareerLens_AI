"""Rate limiting.

The limiter is a process-wide singleton, so the rest of the suite runs with it
off (see ``tests/conftest.py``). This file turns it back on deliberately and
exercises both halves of the feature:

* the **window** — a sliding window that lets exactly the configured number of
  attempts through, and then refuses;
* the **wiring** — that the limit is actually attached to the routes that
  need it, and that the refusal is a well-formed ``429`` with a
  ``Retry-After`` header.

The second half matters more than it looks. A limiter that is implemented
correctly and then not attached to anything is a very common way to end up
with no protection at all.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowLimiter
from app.db.session import get_db
from app.main import create_app

# --------------------------------------------------------------------------- #
# the window
# --------------------------------------------------------------------------- #


def test_the_window_lets_exactly_the_limit_through() -> None:
    now = [1000.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])

    for attempt in range(3):
        allowed, retry_after = limiter.hit("k", limit=3, window=60.0)
        assert allowed, f"attempt {attempt} was refused"
        assert retry_after == 0

    allowed, retry_after = limiter.hit("k", limit=3, window=60.0)
    assert not allowed
    assert retry_after > 0


def test_the_window_slides_rather_than_resetting() -> None:
    """A fixed window lets a caller make twice the limit across a boundary.

    The sliding window is the reason the implementation keeps timestamps
    instead of a counter.
    """
    now = [1000.0]
    limiter = SlidingWindowLimiter(clock=lambda: now[0])

    for _ in range(3):
        limiter.hit("k", limit=3, window=60.0)
    allowed, _ = limiter.hit("k", limit=3, window=60.0)
    assert not allowed

    # Two seconds later, still inside the window: still refused.
    now[0] += 2.0
    allowed, _ = limiter.hit("k", limit=3, window=60.0)
    assert not allowed

    # Once the first entry has aged out, a slot frees up.
    now[0] += 61.0
    allowed, _ = limiter.hit("k", limit=3, window=60.0)
    assert allowed


def test_keys_are_independent() -> None:
    limiter = SlidingWindowLimiter(clock=lambda: 1000.0)
    for _ in range(3):
        limiter.hit("a", limit=3, window=60.0)
    assert not limiter.hit("a", limit=3, window=60.0)[0]
    assert limiter.hit("b", limit=3, window=60.0)[0]


def test_the_table_of_tracked_keys_is_bounded() -> None:
    """A caller must not be able to exhaust memory by cycling addresses."""
    limiter = SlidingWindowLimiter(max_keys=10, clock=lambda: 1000.0)
    for index in range(100):
        limiter.hit(f"key-{index}", limit=5, window=60.0)
    assert limiter.tracked_keys() <= 10


def test_a_zero_limit_disables_the_check() -> None:
    limiter = SlidingWindowLimiter(clock=lambda: 1000.0)
    for _ in range(100):
        assert limiter.hit("k", limit=0, window=60.0)[0]


# --------------------------------------------------------------------------- #
# the wiring
# --------------------------------------------------------------------------- #


@pytest.fixture
def throttled_client(monkeypatch, _isolated_session: Session):
    """A client with the limiter on and a deliberately tiny limit.

    The settings are changed *before* the application is created, because
    ``create_app`` reads them once and the dependency reads the same cache.
    """
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "3")
    monkeypatch.setenv("RATE_LIMIT_AUTH_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

    from app.core.rate_limit import limiter

    limiter.reset()

    application = create_app()
    application.dependency_overrides[get_db] = lambda: _isolated_session
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client

    limiter.reset()
    get_settings.cache_clear()


def test_the_login_route_is_rate_limited(throttled_client: TestClient) -> None:
    """The route that matters most: the one an attacker would hammer."""
    for _ in range(3):
        response = throttled_client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401, response.text

    response = throttled_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "rate_limited"
    assert "error" in body


def test_the_refusal_carries_a_retry_after_header(throttled_client: TestClient) -> None:
    for _ in range(3):
        throttled_client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
    response = throttled_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1


def test_the_registration_route_is_rate_limited(throttled_client: TestClient) -> None:
    for index in range(3):
        throttled_client.post(
            "/api/auth/register",
            json={
                "name": f"User {index}",
                "email": f"user{index}@example.com",
                "password": "Str0ngPassw0rd",
            },
        )
    response = throttled_client.post(
        "/api/auth/register",
        json={"name": "User 4", "email": "user4@example.com", "password": "Str0ngPassw0rd"},
    )
    assert response.status_code == 429


def test_a_successful_request_is_not_throttled_by_a_failed_one(
    throttled_client: TestClient, make_user
) -> None:
    """The limiter counts attempts, not failures — and it must not lock a
    legitimate user out of the API for someone else's bad guesses."""
    user = make_user(email="legit@example.com")
    for _ in range(2):
        throttled_client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
    response = throttled_client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    )
    assert response.status_code == 200, response.text


def test_the_limiter_can_be_turned_off(client: TestClient) -> None:
    """The switch exists so an operator can turn it off without a redeploy."""
    assert get_settings().rate_limit_enabled is False

    for _ in range(20):
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401
