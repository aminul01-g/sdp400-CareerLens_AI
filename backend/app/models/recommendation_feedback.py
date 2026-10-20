"""``RecommendationFeedback`` — what a user did with a recommendation.

``docs/limitations.md`` used to say there was no feedback loop: "a user who
corrects a detected skill, dismisses a suggestion, or ignores a recommendation
leaves no trace that affects a future result". The free-text ``feedback`` table
existed, and it was read by an admin, and that was all it did.

This table is the structured half. A user marks a role as **saved** or
**dismissed**, and the aggregate across all users becomes a small, bounded
adjustment to every future ranking — a *prior*.

Four decisions keep this honest rather than clever:

1. **The prior is a formula, not a model.** It is a net favourability in
   ``[-1, 1]`` applied as a bounded multiplier. Proposal §18.9 forbids a
   trained ranking model, and this is not one: there is no fitting, no
   coefficients to learn, and the result is reproducible by hand.
2. **The prior is bounded at 10%.** A role that everyone dismisses is still
   shown, still ranked, still explained. The prior reorders; it does not
   exclude.
3. **The prior needs evidence.** Below a minimum number of observations it is
   exactly zero. Three users' opinions are noise, and acting on noise is worse
   than not acting.
4. **One row per (run, role).** A user who changes their mind updates the row
   rather than adding a second one, so a single user cannot vote twice.

The user who produced the feedback is never exposed. Only the aggregate is
used, and only the aggregate is shown.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import JobRole
    from app.models.recommendation import RecommendationRun
    from app.models.user import User


class FeedbackAction(StrEnum):
    """What a user did with a recommendation.

    Two kinds of action live here, and the difference between them is the
    whole point of this revision.

    **Interest** -- ``SAVED``, ``INTERESTED``, ``DISMISSED``. The user looked
    at the shortlist and said something about it. It says nothing about
    whether the role was right.

    **Outcome** -- ``APPLIED``, ``INTERVIEW``, ``OFFER``. The user reports
    what happened afterwards. This is the evidence the community prior was
    missing: a role somebody got an interview for is a better match than a
    role somebody merely saved, and the old prior could not tell the two
    apart.

    The outcomes are **self-reported**. The application cannot observe that
    somebody applied to a job, and it does not try to; the user tells it, and
    the prior counts the report. ``docs/limitations.md`` says so in those
    words.
    """

    SAVED = "saved"
    DISMISSED = "dismissed"
    INTERESTED = "interested"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"


#: How much each action counts towards the prior, and in which direction.
#:
#: A positive weight means "this role is a good match"; a negative one means
#: "it is not". The magnitude is the weight, not a probability: an offer is
#: four times the evidence a save is, because it is four times the signal.
#:
#: The asymmetry is deliberate. A dismissal is weak negative evidence -- the
#: user may simply not want that job -- while an interview or an offer is
#: strong positive evidence that the shortlist led somewhere real. The
#: denominator is the total weight, so the prior stays inside ``[-1, 1]``
#: whatever the mix of actions is.
PRIOR_WEIGHT: dict[str, int] = {
    FeedbackAction.SAVED.value: 1,
    FeedbackAction.INTERESTED.value: 1,
    FeedbackAction.DISMISSED.value: -1,
    FeedbackAction.APPLIED.value: 2,
    FeedbackAction.INTERVIEW.value: 3,
    FeedbackAction.OFFER.value: 4,
}

#: The actions that record an outcome rather than an opinion.
OUTCOME_ACTIONS: frozenset[str] = frozenset(
    {
        FeedbackAction.APPLIED.value,
        FeedbackAction.INTERVIEW.value,
        FeedbackAction.OFFER.value,
    }
)

#: The actions that record an opinion.
INTEREST_ACTIONS: frozenset[str] = frozenset(
    {
        FeedbackAction.SAVED.value,
        FeedbackAction.INTERESTED.value,
        FeedbackAction.DISMISSED.value,
    }
)

#: The direction of each action, kept for callers that only need the sign.
PRIOR_DIRECTION: dict[str, int] = {
    action: (1 if weight > 0 else -1 if weight < 0 else 0)
    for action, weight in PRIOR_WEIGHT.items()
}


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        CheckConstraint(
            "action IN ('saved','dismissed','interested','applied','interview','offer')",
            name="action_valid",
        ),
        # One row per (run, role): a user who changes their mind updates the
        # row rather than voting twice.
        UniqueConstraint("run_id", "job_role_id", name="uq_feedback_run_role"),
        # "What has the community said about this role?"
        # The names are prefixed because index names are unique per schema in
        # PostgreSQL, and `feedback` already owns `ix_feedback_user`.
        Index("ix_recommendation_feedback_role", "job_role_id", "action"),
        # "What has this user said, and when?"
        Index("ix_recommendation_feedback_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_run.id", ondelete="CASCADE"), nullable=False
    )
    job_role_id: Mapped[int] = mapped_column(
        ForeignKey("job_role.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship()
    run: Mapped[RecommendationRun] = relationship()
    job_role: Mapped[JobRole] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RecommendationFeedback id={self.id} run={self.run_id} "
            f"role={self.job_role_id} action={self.action!r}>"
        )
