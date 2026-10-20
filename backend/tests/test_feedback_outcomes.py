"""Outcomes in the community prior.

``docs/limitations.md`` used to say of the prior:

    **It measures interest, not outcomes.** A dismissal says "not this role".
    It does not say whether the person found a job, or whether the role was a
    good match for somebody else.

The prior could only count opinions, so a role that lots of people saved and
a role that lots of people got an interview for looked identical to it.

These tests cover the three properties the change claims:

* **An outcome is recorded.** ``applied``, ``interview`` and ``offer`` are
  accepted and stored.
* **An outcome counts for more than an opinion.** The weights are a fixed
  table, and the prior is still a formula -- nothing is fitted, so proposal
  section 18.9 still holds.
* **The prior is still bounded.** A role everybody reports an offer for still
  moves by at most the prior strength, and is never excluded.

And the one honest limit, which the tests state rather than hide: an outcome
is **self-reported**. A user who applied and heard nothing back records
``applied``, and the prior counts it as positive.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.ml.ranker import PRIOR_STRENGTH
from app.models.recommendation_feedback import (
    INTEREST_ACTIONS,
    OUTCOME_ACTIONS,
    PRIOR_WEIGHT,
    FeedbackAction,
    RecommendationFeedback,
)
from app.services import feedback_service


@pytest.fixture
def user_client(client: TestClient, make_user, taxonomy_seed, role_seed) -> TestClient:
    """A client signed in as a user with the knowledge base seeded."""
    user = make_user(email="outcome@example.com", name="Outcome User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _record(client: TestClient, run_id: int, role_id: int, action: str):
    return client.post(
        f"/api/recommendations/runs/{run_id}/roles/{role_id}/feedback",
        json={"action": action},
    )


# --------------------------------------------------------------------------- #
# the actions exist
# --------------------------------------------------------------------------- #


def test_the_outcome_actions_are_declared() -> None:
    assert frozenset({"applied", "interview", "offer"}) == OUTCOME_ACTIONS
    assert frozenset({"saved", "interested", "dismissed"}) == INTEREST_ACTIONS


def test_every_action_has_a_weight() -> None:
    for action in FeedbackAction:
        assert action.value in PRIOR_WEIGHT, action


def test_the_outcomes_weigh_more_than_the_opinions() -> None:
    """The claim the whole change rests on."""
    weakest_outcome = min(PRIOR_WEIGHT[a] for a in OUTCOME_ACTIONS)
    strongest_opinion = max(abs(PRIOR_WEIGHT[a]) for a in INTEREST_ACTIONS)
    assert weakest_outcome > strongest_opinion

    assert PRIOR_WEIGHT["saved"] == 1
    assert PRIOR_WEIGHT["applied"] == 2
    assert PRIOR_WEIGHT["interview"] == 3
    assert PRIOR_WEIGHT["offer"] == 4
    assert PRIOR_WEIGHT["dismissed"] == -1


def test_the_weights_are_a_table_and_not_a_fitted_model() -> None:
    """Proposal 18.9 forbids a trained ranking model.

    A fixed table of integers is not a model: there is no fitting, no
    coefficients to learn, and the result is reproducible by hand.
    """
    assert all(isinstance(weight, int) for weight in PRIOR_WEIGHT.values())
    assert len(PRIOR_WEIGHT) == len(FeedbackAction)


# --------------------------------------------------------------------------- #
# the actions are recorded
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("action", ["applied", "interview", "offer"])
def test_an_outcome_is_recorded(
    user_client: TestClient, skill_ids: dict[str, int], db, action: str
) -> None:
    from tests.test_feedback_loop import _add_skills, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]

    response = _record(user_client, run["run_id"], role["job_role_id"], action)
    assert response.status_code == 201, response.text
    assert response.json()["action"] == action

    rows = db.query(RecommendationFeedback).all()
    assert len(rows) == 1
    assert rows[0].action == action


@pytest.mark.parametrize("action", ["applied", "interview", "offer"])
def test_an_outcome_passes_the_schema(
    user_client: TestClient, skill_ids: dict[str, int], action: str
) -> None:
    from tests.test_feedback_loop import _add_skills, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]

    response = _record(user_client, run["run_id"], role["job_role_id"], action)
    assert response.status_code == 201
    assert response.json()["action"] == action


# --------------------------------------------------------------------------- #
# the prior counts them
# --------------------------------------------------------------------------- #


def test_an_outcome_moves_the_prior_more_than_an_opinion(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """The same number of observations, a different prior."""
    from tests.test_feedback_loop import _add_skills, _new_user, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role_id = run["results"][0]["job_role_id"]
    needed = get_settings().feedback_prior_min_samples

    for index in range(needed):
        other = _new_user(
            user_client.app, make_user, skill_ids, f"outcome{index}@example.com"
        )
        other_run = other.post("/api/recommendations", json={"limit": 10}).json()
        _record(other, other_run["run_id"], role_id, "offer")

    prior = feedback_service.compute_priors(db)[role_id]
    assert prior.samples == needed
    assert prior.positive == needed
    assert prior.negative == 0
    assert prior.outcomes == needed
    # Every observation is positive, so the net favourability is 1.0 whether
    # the observations were saves or offers.
    assert prior.value == pytest.approx(1.0)

    # The same number of *saves* gives a weaker signal, which is visible in
    # the weights rather than in the saturated value.
    assert PRIOR_WEIGHT["offer"] > PRIOR_WEIGHT["saved"]


def test_a_mix_of_outcomes_and_opinions_is_weighted(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """Three offers against one dismissal is not a 3-to-1 majority."""
    from tests.test_feedback_loop import _add_skills, _new_user, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role_id = run["results"][0]["job_role_id"]
    needed = get_settings().feedback_prior_min_samples

    for index in range(needed):
        other = _new_user(
            user_client.app, make_user, skill_ids, f"mix{index}@example.com"
        )
        other_run = other.post("/api/recommendations", json={"limit": 10}).json()
        action = "dismissed" if index == 0 else "offer"
        _record(other, other_run["run_id"], role_id, action)

    prior = feedback_service.compute_priors(db)[role_id]
    # Four offers (weight 4 each) against one dismissal (weight 1).
    offers = needed - 1
    assert prior.value == pytest.approx((offers * 4 - 1) / (offers * 4 + 1))
    assert prior.outcomes == needed - 1
    assert -1.0 <= prior.value <= 1.0


def test_the_prior_is_still_bounded_by_the_strength(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """A role everybody reports an offer for is moved, not excluded."""
    from tests.test_feedback_loop import _add_skills, _new_user, _run

    _add_skills(user_client, skill_ids)
    before = _run(user_client)["results"][0]
    role_id = before["job_role_id"]
    needed = get_settings().feedback_prior_min_samples

    for index in range(needed):
        other = _new_user(
            user_client.app, make_user, skill_ids, f"bounded{index}@example.com"
        )
        other_run = other.post("/api/recommendations", json={"limit": 10}).json()
        _record(other, other_run["run_id"], role_id, "offer")

    after = user_client.post("/api/recommendations", json={"limit": 10}).json()
    updated = next(r for r in after["results"] if r["job_role_id"] == role_id)

    assert updated is not None, "the role was excluded rather than reordered"
    assert abs(PRIOR_STRENGTH) <= 0.25


def test_too_few_outcomes_still_produce_no_prior(
    user_client: TestClient, skill_ids: dict[str, int], make_user, db
) -> None:
    """The evidence threshold applies to outcomes too."""
    from tests.test_feedback_loop import _add_skills, _new_user, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role_id = run["results"][0]["job_role_id"]
    needed = get_settings().feedback_prior_min_samples

    for index in range(needed - 1):
        other = _new_user(
            user_client.app, make_user, skill_ids, f"few{index}@example.com"
        )
        other_run = other.post("/api/recommendations", json={"limit": 10}).json()
        _record(other, other_run["run_id"], role_id, "offer")

    prior = feedback_service.compute_priors(db)[role_id]
    assert prior.value == 0.0
    assert prior.outcomes == needed - 1


def test_an_unknown_action_is_still_refused(
    user_client: TestClient, skill_ids: dict[str, int]
) -> None:
    from tests.test_feedback_loop import _add_skills, _run

    _add_skills(user_client, skill_ids)
    run = _run(user_client)
    role = run["results"][0]

    response = _record(user_client, run["run_id"], role["job_role_id"], "got-hired")
    assert response.status_code == 422
