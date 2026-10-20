"""Recommendation feedback schemas.

The structured signal a user gives about a role in a run. Separate from
``app.schemas.cv.FeedbackCreate``, which is the free-text message box on the
public feedback form — this one is a machine-readable action, and it is what
the community prior is computed from.

The actions fall into two kinds. **Interest**: ``saved``, ``dismissed``,
``interested`` — what the user did with the shortlist. **Outcome**:
``applied``, ``interview``, ``offer`` — what happened afterwards, reported by
the user. The prior weights the second kind above the first, because an
interview is better evidence of a good match than a save is.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

#: The actions a user may take on a recommended role.
FEEDBACK_ACTIONS = (
    "saved",
    "dismissed",
    "interested",
    "applied",
    "interview",
    "offer",
)

#: The actions that report an outcome rather than an opinion.
OUTCOME_ACTIONS = ("applied", "interview", "offer")


class FeedbackActionRequest(BaseModel):
    """``POST /api/recommendations/runs/{run_id}/roles/{role_id}/feedback``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    action: Annotated[
        str, Field(pattern="^(saved|dismissed|interested|applied|interview|offer)$")
    ]


class FeedbackActionRead(BaseModel):
    """The recorded action, and the role it applies to."""

    model_config = ConfigDict(from_attributes=True)

    job_role_id: int
    action: str
    created_at: datetime
