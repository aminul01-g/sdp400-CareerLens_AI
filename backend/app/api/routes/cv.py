"""``/api/cv`` — CV upload, text extraction, detected-skill review, and deletion.

**Auth is required on every route here.** The legacy equivalents used
``@jwt_required(optional=True)`` (``guidance.py:10,31``), which let anonymous
callers write unattributable upload rows and read anyone's CV text by guessing a
sequential integer id. Both are findings S4 and S5.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.cv import ExtractedTextResponse, ResumeUploadRead, UploadResponse
from app.schemas.pagination import PageParamsDep, build_page
from app.services import cv_service

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CV, extract its text, and detect skills",
    responses={
        401: {"description": "Authentication required"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Empty file, or a scanned PDF (OCR is out of scope)"},
    },
)
async def upload_cv(
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(..., description="A PDF or DOCX CV, at most 5 MB."),
) -> UploadResponse:
    """Extraction runs on upload; nothing is written to ``user_skill`` here.

    Detected skills are **staged** in ``resume_detected_skill``. They reach the
    user's profile only through ``POST /api/skills/confirm``, which is what makes
    "every skill in ``user_skill`` is user-confirmed" a checkable invariant.
    """
    data = await file.read()
    return cv_service.upload_and_extract(
        db,
        user,
        filename=file.filename or "upload",
        content_type=file.content_type,
        data=data,
    )


@router.get("", summary="The caller's uploads")
def list_uploads(params: PageParamsDep, db: DbSession, user: CurrentUser):
    total, items = cv_service.list_uploads(db, user, limit=params.limit, offset=params.offset)
    return build_page(items, total, params)


@router.get(
    "/{upload_id}",
    response_model=ResumeUploadRead,
    summary="One upload with its detected skills",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_upload(upload_id: int, db: DbSession, user: CurrentUser) -> ResumeUploadRead:
    upload, staged = cv_service.get_upload(db, user, upload_id)
    return cv_service._to_read(upload, staged)


@router.get(
    "/{upload_id}/text",
    response_model=ExtractedTextResponse,
    summary="The extracted plain text",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_upload_text(upload_id: int, db: DbSession, user: CurrentUser) -> ExtractedTextResponse:
    text = cv_service.get_text(db, user, upload_id)
    return ExtractedTextResponse(text=text, text_length=len(text))


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete an upload and the stored file",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def delete_upload(upload_id: int, db: DbSession, user: CurrentUser) -> Response:
    """Removes the row **and** the file on disk.

    Proposal section 7.5 requires the ability to delete uploaded files; deleting
    only the row would leave the CV text sitting in the uploads directory, which
    is the opposite of what the requirement means.
    """
    cv_service.delete_upload(db, user, upload_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
