"""``/api/feedback`` — a thin in-app feature, retained from the predecessor app.

Not one of the proposal's nine modules. **Auth is now required**; the legacy route
used ``@jwt_required(optional=True)`` (``guidance.py:94``), which let anonymous
callers write unattributable rows (finding S4).
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.cv import FeedbackCreate, FeedbackRead
from app.services import dashboard_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    summary="Send feedback",
)
def create_feedback(
    payload: FeedbackCreate, db: DbSession, user: CurrentUser
) -> FeedbackRead:
    return dashboard_service.create_feedback(db, user, payload)
