"""``/api/dashboard`` — real aggregates for the signed-in user.

These two endpoints exist specifically to replace fabricated numbers. The legacy
dashboard rendered ``totalUsers: "12,847"``, ``successRate: "94%"`` and
``averageCompletion: "18 minutes"``; every field below is counted from the
database instead.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import DashboardSummary, ProfileCompleteness
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary, summary="Real counts for this user")
def summary(db: DbSession, user: CurrentUser) -> DashboardSummary:
    return dashboard_service.summary(db, user)


@router.get(
    "/completeness",
    response_model=ProfileCompleteness,
    summary="0-100 profile completeness with named next steps",
)
def completeness(db: DbSession, user: CurrentUser) -> ProfileCompleteness:
    return dashboard_service.completeness(db, user)
