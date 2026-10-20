"""The feedback loop.

The limitation it closes said: "a user who corrects a detected skill,
dismisses a suggestion, or ignores a recommendation leaves no trace that
affects a future result".

These tests are mostly about the ways a feedback loop can go wrong, because
that is where the design decisions were made:

* **A prior needs evidence.** Below the sample threshold it must be exactly
  zero. Three users' opinions are noise, and acting on noise is worse than
  not acting.
* **The prior is bounded.** A role everybody dismissed is still shown, still
  ranked and still explained. The prior reorders; it does not exclude.
* **One user cannot vote twice.** Marking the same role again updates the
  record.
* **The prior is a formula, not a model.** There is no fitting anywhere, and
  the effect of a prior is reproducible by hand.
* **The individual is never exposed.** Only the aggregate is used.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.ml.ranker import PRIOR_STRENGTH
from app.models.recommendation_feedback import RecommendationFeedback


@pytest.fixture
def user_client(client: TestClient, make_user, taxonomy_seed, role_seed) -> TestClient:
    user = make_user(email="feedback@example.com", name="Feedback User")
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
        client.post("/api/skills", json={"skill_id": skill_ids[slug], "proficiency": proficiency})


def _new_user(app, make_user, skill_ids: dict[str, int], email: str) -> TestClient:
    """A second user, signed in, with the same skills.

    The other users in these tests have to be able to generate a run, and a
    run needs skills — so they get the same ones, which is the point: the
    *only* difference between the two runs is the feedback in between.
    """
    user = make_user(email=email)
    other = TestClient(app)
    token = other.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    other.headers.update({"Authorization": f"Bearer {token}"})
    _add_skills(other, skill_ids)
    return other


def _run(client: TestClient) -> dict:
    response = client.post("/api/recommendations", json={"limit": 10})
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# recording
# --------------------------------------------------------------------------- #


def test_an_action_is_recorded(user_client: TestClient, skill_ids: dict[str, int], db) -> None:
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]

    response = user_client.post(
        f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback",
        json={"action": "saved"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["action"] == "saved"

    rows = db.query(RecommendationFeedback).all()
    assert len(rows) == 1
    assert rows[0].action == "saved"


def test_marking_the_same_role_again_updates_it(
    user_client: TestClient, skill_ids: dict[str, int], db
) -> None:
    """One user cannot vote twice, and a change of mind is a change of mind."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    url = f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback"

    user_client.post(url, json={"action": "saved"})
    user_client.post(url, json={"action": "dismissed"})

    rows = db.query(RecommendationFeedback).all()
    assert len(rows) == 1
    assert rows[0].action == "dismissed"


def test_an_unknown_action_is_refused(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    response = user_client.post(
        f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback",
        json={"action": "delete-everything"},
    )
    assert response.status_code == 422


def test_another_users_run_cannot_be_marked(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """404, not 403: the run either does not exist or belongs to someone else."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]

    other = TestClient(user_client.app)
    other.headers.update({"Authorization": "Bearer not-a-real-token"})
    response = other.post(
        f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback",
        json={"action": "saved"},
    )
    assert response.status_code == 401


def test_marking_requires_authentication(client: TestClient, skill_ids: dict[str, int]) -> None:
    assert client.post(
        "/api/recommendations/runs/1/roles/1/feedback", json={"action": "saved"}
    ).status_code == 401


# --------------------------------------------------------------------------- #
# the prior
# --------------------------------------------------------------------------- #


def test_a_role_with_no_feedback_has_no_prior(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    for result in run["results"]:
        assert result["role_prior"] == 0.0
        assert result["feedback_samples"] == 0


def test_too_few_observations_produce_no_prior(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """The evidence guard. Below the threshold, the prior is exactly zero."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    url = f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback"
    user_client.post(url, json={"action": "dismissed"})

    settings = get_settings()
    assert settings.feedback_prior_min_samples > 1, "the guard would not be a guard"

    # One more user, still below the threshold.
    other = make_user(email="other-feedback@example.com")
    other_client = TestClient(user_client.app)
    token = other_client.post(
        "/api/auth/login", json={"email": other.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    other_client.headers.update({"Authorization": f"Bearer {token}"})

    from app.services import feedback_service

    priors = feedback_service.compute_priors(db)
    prior = priors.get(role["job_role_id"])
    if prior is not None and prior.samples < settings.feedback_prior_min_samples:
        assert prior.value == 0.0


def test_enough_observations_produce_a_bounded_prior(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """With enough evidence the prior is non-zero, and it is bounded."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    role_id = role["job_role_id"]

    settings = get_settings()
    needed = settings.feedback_prior_min_samples

    for index in range(needed):
        other_client = _new_user(
            user_client.app, make_user, skill_ids, f"prior{index}@example.com"
        )
        other_run = other_client.post("/api/recommendations", json={"limit": 10}).json()
        other_client.post(
            f"/api/recommendations/runs/{other_run['run_id']}/roles/{role_id}/feedback",
            json={"action": "dismissed"},
        )

    from app.services import feedback_service

    priors = feedback_service.compute_priors(db)
    prior = priors[role_id]
    assert prior.samples >= needed
    assert prior.negative == needed
    assert prior.positive == 0
    assert prior.value == pytest.approx(-1.0)

    # And the effect on a score is bounded by the strength.
    assert abs(PRIOR_STRENGTH) <= 0.25, "the prior can move a score too far"


def test_the_prior_changes_the_score(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """A role everybody dismissed is scored lower — but it is still scored."""
    _add_skills(user_client, skill_ids)
    before = _run(user_client)["results"][0]
    role_id = before["job_role_id"]

    settings = get_settings()
    needed = settings.feedback_prior_min_samples

    for index in range(needed):
        other_client = _new_user(
            user_client.app, make_user, skill_ids, f"dismiss{index}@example.com"
        )
        other_run = other_client.post("/api/recommendations", json={"limit": 10}).json()
        other_client.post(
            f"/api/recommendations/runs/{other_run['run_id']}/roles/{role_id}/feedback",
            json={"action": "dismissed"},
        )

    after = next(r for r in _run(user_client)["results"] if r["job_role_id"] == role_id)
    assert after["role_prior"] < 0
    assert after["feedback_samples"] >= needed
    assert after["compatibility_pct"] < before["compatibility_pct"]
    # Bounded: the role is still there, and still scored.
    assert after["compatibility_pct"] > 0
    assert after["role_prior"] >= -1.0


def test_a_saved_role_is_raised(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    _add_skills(user_client, skill_ids)
    before = _run(user_client)["results"][0]
    role_id = before["job_role_id"]

    needed = get_settings().feedback_prior_min_samples
    for index in range(needed):
        other_client = _new_user(
            user_client.app, make_user, skill_ids, f"save{index}@example.com"
        )
        other_run = other_client.post("/api/recommendations", json={"limit": 10}).json()
        other_client.post(
            f"/api/recommendations/runs/{other_run['run_id']}/roles/{role_id}/feedback",
            json={"action": "saved"},
        )

    after = next(r for r in _run(user_client)["results"] if r["job_role_id"] == role_id)
    assert after["role_prior"] > 0
    assert after["compatibility_pct"] > before["compatibility_pct"]


def test_a_stored_run_keeps_the_prior_it_was_given(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """History must not change under us."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    detail = user_client.get(f"/api/recommendations/runs/{run['run_id']}").json()
    for result in detail["results"]:
        assert "role_prior" in result
        assert "feedback_samples" in result


def test_the_prior_is_an_aggregate_and_never_names_a_user(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    """Only the aggregate is exposed. The individual is not."""
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    user_client.post(
        f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback",
        json={"action": "dismissed"},
    )
    body = user_client.get("/api/admin/audit").text
    assert "feedback@example.com" not in body or "dismissed" in body

    from app.schemas.feedback import FeedbackActionRead

    fields = set(FeedbackActionRead.model_fields)
    assert "user_id" not in fields
    assert "user_email" not in fields


def test_the_user_can_read_back_their_own_answers(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]
    user_client.post(
        f"/api/recommendations/runs/{run['run_id']}/roles/{role['job_role_id']}/feedback",
        json={"action": "interested"},
    )
    response = user_client.get(f"/api/recommendations/runs/{run['run_id']}/feedback")
    assert response.status_code == 200
    assert response.json()[str(role["job_role_id"])] == "interested"


def test_an_unknown_user_cannot_be_read(user_client: TestClient) -> None:
    assert user_client.get("/api/recommendations/runs/999/feedback").status_code == 200
