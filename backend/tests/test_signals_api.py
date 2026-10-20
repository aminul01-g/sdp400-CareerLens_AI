"""The context signals, end to end over the API.

``tests/test_signals.py`` proves the engine's arithmetic. This file proves the
arithmetic is *reachable*: that a user can state their level, that the
statement survives the round trip through the database, and that the engine
actually reads it.

The test that matters most is
:func:`test_a_junior_and_a_principal_with_the_same_skills_score_differently`.
It is the sentence the limitations document used to make — "a junior and a
principal engineer with the same declared skills get the same score" — and it
is the claim this work existed to make false.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ml.signals import LEVEL_FIT_FAR


@pytest.fixture
def user_client(client: TestClient, make_user, taxonomy_seed, role_seed) -> TestClient:
    user = make_user(email="signals@example.com", name="Signals User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _add_skills(client: TestClient, skill_ids: dict[str, int]) -> None:
    for slug, proficiency in (
        ("python", 5), ("sql", 4), ("scikit-learn", 4), ("pytorch", 4),
        ("docker", 3), ("aws", 3), ("pandas", 4),
    ):
        response = client.post(
            "/api/skills", json={"skill_id": skill_ids[slug], "proficiency": proficiency}
        )
        assert response.status_code == 201, response.text


def _top(client: TestClient) -> dict:
    response = client.post("/api/recommendations", json={"limit": 10})
    assert response.status_code == 201, response.text
    return response.json()["results"][0]


# --------------------------------------------------------------------------- #
# round trips
# --------------------------------------------------------------------------- #


def test_the_profile_keeps_a_declared_level_and_industry(user_client: TestClient) -> None:
    response = user_client.patch(
        "/api/profile",
        json={"seniority": "Senior", "industry": "fintech", "years_experience": 7},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["seniority"] == "Senior"
    assert body["industry"] == "fintech"
    assert body["years_experience"] == 7


def test_an_unknown_level_is_refused(user_client: TestClient) -> None:
    """A level the engine cannot compare against a role's is a client error."""
    response = user_client.patch("/api/profile", json={"seniority": "Grandmaster"})
    assert response.status_code == 422
    assert "Seniority" in response.text


def test_a_skill_keeps_its_recency_and_depth(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    created = user_client.post(
        "/api/skills",
        json={
            "skill_id": skill_ids["python"],
            "proficiency": 5,
            "years_used": 4.5,
            "last_used_at": "2026-09-01",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["years_used"] == pytest.approx(4.5)
    assert body["last_used_at"] == "2026-09-01"

    listed = user_client.get("/api/skills").json()
    python = next(item for item in listed if item["slug"] == "python")
    assert python["last_used_at"] == "2026-09-01"

    patched = user_client.patch(
        f"/api/skills/{skill_ids['python']}", json={"last_used_at": "2026-10-01"}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["last_used_at"] == "2026-10-01"


# --------------------------------------------------------------------------- #
# the engine reads them
# --------------------------------------------------------------------------- #


def test_the_response_carries_the_new_factors(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)
    user_client.patch("/api/profile", json={"seniority": "Mid"})

    top = _top(user_client)
    for field in ("declared_coverage", "signal_coverage", "level_fit"):
        assert field in top, f"{field} is missing from the recommendation response"
    assert 0.0 <= top["declared_coverage"] <= 1.0
    assert 0.0 <= top["signal_coverage"] <= 1.0
    assert 0.0 < top["level_fit"] <= 1.0


def test_a_junior_and_a_principal_with_the_same_skills_score_differently(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """The claim the limitations document used to make, now false."""
    _add_skills(user_client, skill_ids)

    user_client.patch("/api/profile", json={"seniority": "Junior"})
    junior = _top(user_client)

    user_client.patch("/api/profile", json={"seniority": "Principal"})
    principal = _top(user_client)

    # Identical skills, identical declared coverage.
    assert junior["declared_coverage"] == pytest.approx(principal["declared_coverage"])
    # Different level fit, and therefore a different score.
    assert junior["level_fit"] != principal["level_fit"]
    assert junior["skill_coverage"] != principal["skill_coverage"]
    assert junior["compatibility_pct"] != principal["compatibility_pct"]


def test_a_user_with_no_declared_level_is_not_penalised(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """Absence is neutral: not knowing is not a mismatch."""
    _add_skills(user_client, skill_ids)

    top = _top(user_client)
    assert top["level_fit"] == 1.0


def test_the_published_formula_holds_over_the_api(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)
    user_client.patch("/api/profile", json={"seniority": "Senior", "years_experience": 9})

    top = _top(user_client)
    expected = 0.6 * top["skill_coverage"] + 0.4 * top["tfidf_similarity"]
    assert top["compatibility_pct"] == pytest.approx(round(expected * 100, 1), abs=0.11)


def test_a_stale_skill_scores_lower_over_the_api(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """Recency reaches the engine."""
    _add_skills(user_client, skill_ids)
    fresh = _top(user_client)

    for slug in ("python", "sql", "scikit-learn", "pytorch", "docker", "aws", "pandas"):
        user_client.patch(
            f"/api/skills/{skill_ids[slug]}",
            json={"years_used": 0, "last_used_at": "2005-01-01"},
        )
    stale = _top(user_client)

    assert stale["declared_coverage"] == pytest.approx(fresh["declared_coverage"])
    assert stale["signal_coverage"] < fresh["signal_coverage"]
    assert stale["compatibility_pct"] < fresh["compatibility_pct"]


def test_the_gap_report_reflects_the_level_fit(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)

    roles = user_client.get("/api/jobs").json()
    target = next(
        role for role in roles["items"] if role["seniority"] == "Mid"
    )

    user_client.patch("/api/profile", json={"seniority": "Mid"})
    matched = user_client.get(f"/api/skill-gap/{target['id']}").json()
    assert matched["level_fit"] == 1.0

    # "Principal" is three bands above "Mid", so the far factor applies.
    user_client.patch("/api/profile", json={"seniority": "Principal"})
    mismatched = user_client.get(f"/api/skill-gap/{target['id']}").json()
    assert mismatched["level_fit"] == pytest.approx(LEVEL_FIT_FAR)
    assert mismatched["coverage"] < matched["coverage"]


def test_a_stored_run_can_still_be_explained(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """A run persisted today must read back with its factors intact."""
    _add_skills(user_client, skill_ids)
    user_client.patch("/api/profile", json={"seniority": "Senior"})

    run = user_client.post("/api/recommendations", json={"limit": 5}).json()
    detail = user_client.get(f"/api/recommendations/runs/{run['run_id']}").json()

    assert detail["results"]
    for result in detail["results"]:
        assert result["declared_coverage"] is not None
        assert result["level_fit"] is not None
        assert 0.0 < result["level_fit"] <= 1.0
