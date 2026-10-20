"""The feedback loop: recording what a user did, and turning it into a prior.

Two halves, and the separation between them is the whole design.

**Recording** is a user's own action on their own run. It is a write, it is
attributable, and it is audited.

**The prior** is an aggregate over every user's feedback, computed at
generation time and applied as a bounded multiplier. It is a *formula*:

.. code-block:: text

    prior = (positive_weight - negative_weight) / total_weight

which lands in ``[-1, 1]``, and is then applied as:

.. code-block:: text

    compatibility = compatibility * (1 + 0.10 * prior)

Four properties matter more than the arithmetic:

* **The prior needs evidence.** Below ``feedback_prior_min_samples``
  observations it is exactly ``0.0``. Three users' opinions are noise, and
  acting on noise is worse than not acting.
* **The prior is bounded.** At the default strength it can move a score by
  10% in either direction. A role everybody dismissed is still shown, still
  ranked, still explained.
* **Outcomes count for more than opinions.** A dismissal is weak negative
  evidence; an interview or an offer is strong positive evidence that the
  shortlist led somewhere. The weights are in
  ``app/models/recommendation_feedback.py`` and they are a fixed table, not a
  fitted one.
* **The individual is never exposed.** Only the aggregate is used, and only
  the aggregate is shown. The prior is about a role, not about a person.

The outcomes are **self-reported**: the application cannot observe that
somebody applied to a job, and it does not try to. The user tells it, and the
prior counts the report. A user who applied and heard nothing back records
"applied" and is counted as positive, which is a real limitation of counting
outcomes this way and is stated in ``docs/limitations.md``.

The engine stays pure: the aggregate is computed here, in the service layer,
and passed in as a plain mapping.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, UnprocessableError
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.recommendation_feedback import (
    OUTCOME_ACTIONS,
    PRIOR_WEIGHT,
    FeedbackAction,
    RecommendationFeedback,
)
from app.models.user import User
from app.services import audit_service

logger = logging.getLogger("app.services.feedback")


@dataclass(frozen=True, slots=True)
class RolePrior:
    """The community signal for one role."""

    #: The net favourability, in ``[-1, 1]``. Exactly ``0.0`` when there is
    #: not enough evidence to use one.
    value: float
    #: How many observations it is based on.
    samples: int
    #: How many were positive, and how many negative.
    positive: int
    negative: int
    #: How many of the observations were reported outcomes rather than
    #: opinions. A prior built entirely from opinions is weaker evidence, and
    #: the admin view shows the difference.
    outcomes: int = 0


def record_action(
    db: Session,
    user: User,
    run_id: int,
    job_role_id: int,
    action: str,
) -> RecommendationFeedback:
    """Record what the user did with a role in a run.

    Idempotent by ``(run, role)``: marking the same role again **updates** the
    row rather than adding a second one, so a single user cannot vote twice
    and a change of mind is recorded as a change of mind.
    """
    if action not in PRIOR_WEIGHT:
        raise UnprocessableError(
            f"'{action}' is not a known feedback action.",
            errors=[{"field": "action", "message": "Unknown feedback action."}],
        )

    run = db.scalar(
        select(RecommendationRun).where(
            RecommendationRun.id == run_id, RecommendationRun.user_id == user.id
        )
    )
    if run is None:
        # 404, not 403: the run either does not exist or belongs to someone
        # else, and the caller cannot tell which.
        raise NotFoundError("That recommendation run does not exist.")

    result = db.scalar(
        select(RecommendationResult).where(
            RecommendationResult.run_id == run_id,
            RecommendationResult.job_role_id == job_role_id,
        )
    )
    if result is None:
        raise NotFoundError("That role was not in the run.")

    row = db.scalar(
        select(RecommendationFeedback).where(
            RecommendationFeedback.run_id == run_id,
            RecommendationFeedback.job_role_id == job_role_id,
        )
    )
    if row is None:
        row = RecommendationFeedback(
            user_id=user.id,
            run_id=run_id,
            job_role_id=job_role_id,
            action=action,
        )
        db.add(row)
    else:
        row.action = action

    audit_service.record(
        db,
        action="recommendation.feedback_recorded",
        entity_type="recommendation",
        entity_id=job_role_id,
        summary=f"Marked a recommended role as '{action}'",
        actor=user,
        changes={"run_id": run_id, "action": action},
    )
    db.commit()
    db.refresh(row)
    return row


def list_user_actions(db: Session, user: User, run_id: int) -> dict[int, str]:
    """``job_role_id -> action`` for one of the user's runs."""
    rows = db.scalars(
        select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == user.id,
            RecommendationFeedback.run_id == run_id,
        )
    ).all()
    return {row.job_role_id: row.action for row in rows}


def compute_priors(db: Session) -> dict[int, RolePrior]:
    """The community signal for every role that has any feedback at all.

    Returns ``role_id -> RolePrior``. Roles with no feedback are absent from
    the mapping, which the engine treats as a prior of zero.

    The prior is a weighted net favourability:

    .. code-block:: text

        prior = (positive_weight - negative_weight) / total_weight

    The weights come from ``PRIOR_WEIGHT``: an opinion is worth 1, an
    application 2, an interview 3 and an offer 4, while a dismissal is worth
    -1. The denominator is the total weight rather than the number of
    observations, so the result stays inside ``[-1, 1]`` whatever the mix is.
    """
    settings = get_settings()
    rows = db.execute(
        select(
            RecommendationFeedback.job_role_id,
            RecommendationFeedback.action,
            func.count(RecommendationFeedback.id),
        ).group_by(
            RecommendationFeedback.job_role_id, RecommendationFeedback.action
        )
    ).all()

    totals: dict[int, list[int]] = {}
    for role_id, action, count in rows:
        # [positive weight, negative weight, positive count, negative count,
        #  outcome count]
        bucket = totals.setdefault(role_id, [0, 0, 0, 0, 0])
        count = int(count)
        weight = PRIOR_WEIGHT.get(str(action), 0)
        if weight > 0:
            bucket[0] += count * weight
            bucket[2] += count
        elif weight < 0:
            bucket[1] += count * abs(weight)
            bucket[3] += count
        if str(action) in OUTCOME_ACTIONS:
            bucket[4] += count

    priors: dict[int, RolePrior] = {}
    for role_id, (positive, negative, positive_count, negative_count, outcomes) in totals.items():
        observations = positive_count + negative_count
        if observations < settings.feedback_prior_min_samples:
            # Not enough evidence to act on. The prior is exactly zero, which
            # is different from a prior of "no opinion".
            priors[role_id] = RolePrior(
                value=0.0,
                samples=observations,
                positive=positive_count,
                negative=negative_count,
                outcomes=outcomes,
            )
            continue
        total_weight = positive + negative
        priors[role_id] = RolePrior(
            value=(positive - negative) / total_weight if total_weight else 0.0,
            samples=observations,
            positive=positive_count,
            negative=negative_count,
            outcomes=outcomes,
        )
    return priors


def prior_values(priors: dict[int, RolePrior]) -> dict[int, float]:
    """The engine-facing view: ``role_id -> prior``."""
    return {role_id: prior.value for role_id, prior in priors.items()}


def prior_samples(priors: dict[int, RolePrior]) -> dict[int, int]:
    """``role_id -> number of observations``."""
    return {role_id: prior.samples for role_id, prior in priors.items()}


def actions_for_run(db: Session, run_id: int) -> set[str]:
    """The distinct actions recorded for a run. Used by the admin view."""
    rows = db.scalars(
        select(RecommendationFeedback.action).where(
            RecommendationFeedback.run_id == run_id
        )
    ).all()
    return {str(row) for row in rows}


__all__ = [
    "FeedbackAction",
    "RolePrior",
    "actions_for_run",
    "compute_priors",
    "list_user_actions",
    "prior_samples",
    "prior_values",
    "record_action",
]
