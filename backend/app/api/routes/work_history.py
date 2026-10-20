"""``/api/work-history`` — where the user has worked, and for how long.

The rows the CV pipeline proposes are staged with ``confirmed = False`` and
appear here alongside the user's own. Accepting one is a separate, explicit
call, which is the same rule the detected skills follow: the system proposes,
the user disposes.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.work_history import (
    WorkHistoryCreate,
    WorkHistoryRead,
    WorkHistoryUpdate,
)
from app.services import work_history_service

router = APIRouter(prefix="/work-history", tags=["work-history"])


@router.get("", response_model=list[WorkHistoryRead], summary="The caller's work history")
def list_work_history(db: DbSession, user: CurrentUser) -> list[WorkHistoryRead]:
    return work_history_service.list_entries(db, user)


@router.post(
    "",
    response_model=WorkHistoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a role to the work history",
)
def create_work_history(
    payload: WorkHistoryCreate, db: DbSession, user: CurrentUser
) -> WorkHistoryRead:
    return work_history_service.create_entry(db, user, payload)


@router.patch(
    "/{entry_id}",
    response_model=WorkHistoryRead,
    responses={404: {"description": "No such entry, or it belongs to someone else"}},
)
def update_work_history(
    entry_id: int, payload: WorkHistoryUpdate, db: DbSession, user: CurrentUser
) -> WorkHistoryRead:
    return work_history_service.update_entry(db, user, entry_id, payload)


@router.post(
    "/{entry_id}/confirm",
    response_model=WorkHistoryRead,
    summary="Accept a role the CV pipeline proposed",
    responses={404: {"description": "No such entry, or it belongs to someone else"}},
)
def confirm_work_history(
    entry_id: int, db: DbSession, user: CurrentUser
) -> WorkHistoryRead:
    """Accept a proposal.

    Until this happens the row does not count towards the experience signal.
    """
    return work_history_service.confirm_entry(db, user, entry_id)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "No such entry, or it belongs to someone else"}},
)
def delete_work_history(entry_id: int, db: DbSession, user: CurrentUser) -> Response:
    work_history_service.delete_entry(db, user, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
