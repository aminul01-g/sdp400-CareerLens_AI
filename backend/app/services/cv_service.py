"""CV upload, text extraction, and staging of detected skills.

Ordering matters and is enforced by the two-table design: **extraction happens on
upload, persistence into ``user_skill`` happens only on confirmation.** A failed
extraction therefore can never contaminate a user's profile, and a user who
dislikes the extraction can reject every skill without any cleanup.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.ml.extractor import extract_skills
from app.ml.text_loader import (
    ExtractionFailedError,
    ScannedDocumentError,
    UnsupportedDocumentError,
    extract_text,
    page_count,
)
from app.models.resume import ResumeDetectedSkill, ResumeStatus, ResumeUpload
from app.models.skill import Skill
from app.models.user import User
from app.models.user_skill import UserSkill
from app.schemas.cv import DetectedSkill as DetectedSkillSchema
from app.schemas.cv import ResumeUploadRead, UploadResponse

logger = logging.getLogger("app.services.cv")


def _validate_extension(filename: str) -> str:
    """Allowlist the extension. Closes finding S3.

    The legacy ``backend/utils.py:1-4`` defined ``allowed_file()`` and **never
    imported it anywhere**, so the check existed only on paper.
    """
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.allowed_extension_list:
        raise UnsupportedMediaTypeError(
            f"'{suffix or filename}' is not a supported file type. "
            f"Upload one of: {', '.join(settings.allowed_extension_list)}."
        )
    return suffix


def _validate_content_type(content_type: str | None) -> str:
    """Allowlist the declared MIME type as well as the extension.

    Checking only the extension is not enough: a caller controls the filename, so
    a shell script named ``resume.pdf`` would pass. Both must agree.
    """
    settings = get_settings()
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared not in settings.allowed_content_type_list:
        raise UnsupportedMediaTypeError(
            f"Content type '{declared or 'unknown'}' is not supported. "
            f"Upload one of: {', '.join(settings.allowed_content_type_list)}."
        )
    return declared


def _safe_stored_path(upload_dir: Path, suffix: str) -> tuple[str, Path]:
    """Generate a UUID-based stored filename.

    The user's original filename is never used as a path component, which is what
    removes path traversal (``../../etc/passwd``) as a possibility rather than
    filtering for it. The original name is retained in the database for display.
    """
    stored_filename = f"{uuid.uuid4().hex}{suffix}"
    return stored_filename, upload_dir / stored_filename


def _to_read(upload: ResumeUpload, skills: list[ResumeDetectedSkill] | None = None) -> ResumeUploadRead:
    return ResumeUploadRead(
        id=upload.id,
        original_filename=upload.original_filename,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        status=upload.status,
        error_message=upload.error_message,
        created_at=upload.created_at,
        text_length=len(upload.extracted_text or ""),
        detected_skills=[
            DetectedSkillSchema(
                skill_id=item.skill_id,
                canonical_name=item.skill.name if item.skill else f"Skill {item.skill_id}",
                slug=item.skill.slug if item.skill else "",
                category=item.skill.category if item.skill else "",
                surface_form=item.surface_form,
                occurrence_count=item.occurrence_count,
                match_start=item.match_start,
                match_end=item.match_end,
                accepted=item.accepted,
            )
            for item in (skills or [])
        ],
    )


def upload_and_extract(
    db: Session,
    user: User,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> UploadResponse:
    """Store, extract, detect, and stage. Nothing reaches ``user_skill``."""
    settings = get_settings()

    if not data:
        raise UnprocessableError("The uploaded file is empty.", code="empty_file")

    # 413 before anything is written to disk.
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError(
            f"The file is {len(data) / 1024 / 1024:.1f} MB; the limit is {settings.max_upload_mb} MB."
        )

    suffix = _validate_extension(filename)
    declared_type = _validate_content_type(content_type)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename, stored_path = _safe_stored_path(upload_dir, suffix)
    stored_path.write_bytes(data)

    upload = ResumeUpload(
        user_id=user.id,
        # Bound the length: the column is unconstrained text, and a pathological
        # document should not be able to write megabytes of it.
        original_filename=filename[:255],
        stored_filename=stored_filename,
        content_type=declared_type,
        size_bytes=len(data),
        status=ResumeStatus.UPLOADED.value,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        text = extract_text(stored_path, declared_type, max_bytes=settings.max_upload_bytes)
    except ScannedDocumentError as exc:
        # OCR is out of scope (proposal section 11). The message is the end user's
        # action, not an internal error string.
        upload.status = ResumeStatus.FAILED.value
        upload.error_message = str(exc)
        db.commit()
        logger.info("Rejected image-only upload id=%s user=%s", upload.id, user.id)
        raise UnprocessableError(str(exc), code="ocr_not_supported") from exc
    except (UnsupportedDocumentError, ExtractionFailedError) as exc:
        upload.status = ResumeStatus.FAILED.value
        upload.error_message = str(exc)
        db.commit()
        raise UnprocessableError(str(exc), code="extraction_failed") from exc

    upload.extracted_text = text[:200_000]
    upload.status = ResumeStatus.EXTRACTED.value

    detected = extract_skills(text)

    # The extractor returns the taxonomy's synthetic skill ids; they must be
    # remapped onto the database's real ids before anything is persisted.
    skill_by_slug = {
        skill.slug: skill for skill in db.scalars(select(Skill)).all()
    }
    already_held = {
        row.skill_id
        for row in db.scalars(select(UserSkill).where(UserSkill.user_id == user.id)).all()
    }

    staged: list[ResumeDetectedSkill] = []
    response_skills: list[DetectedSkillSchema] = []
    already_confirmed: list[str] = []

    for found in detected:
        match = skill_by_slug.get(found.slug)
        if match is None:
            # The taxonomy is ahead of the database. Skip rather than invent an id.
            logger.warning("Detected skill %s has no database row; skipping", found.slug)
            continue
        staged.append(
            ResumeDetectedSkill(
                resume_upload_id=upload.id,
                skill_id=match.id,
                surface_form=found.surface_form[:120],
                match_start=found.match_start,
                match_end=found.match_end,
                occurrence_count=found.occurrence_count,
                accepted=False,
            )
        )
        if match.id in already_held:
            already_confirmed.append(match.name)
        response_skills.append(
            DetectedSkillSchema(
                skill_id=match.id,
                canonical_name=match.name,
                slug=match.slug,
                category=match.category,
                surface_form=found.surface_form,
                occurrence_count=found.occurrence_count,
                match_start=found.match_start,
                match_end=found.match_end,
                accepted=False,
                already_confirmed=match.id in already_held,
            )
        )

    db.add_all(staged)
    db.commit()
    db.refresh(upload)

    logger.info(
        "Processed upload id=%s user=%s chars=%s detected=%s",
        upload.id, user.id, len(text), len(response_skills),
    )
    return UploadResponse(
        resume_upload_id=upload.id,
        status=upload.status,
        filename=upload.original_filename,
        size_bytes=upload.size_bytes,
        text_length=len(text),
        page_count=page_count(stored_path),
        detected_skills=response_skills,
        already_confirmed=sorted(set(already_confirmed)),
        message=(
            f"Detected {len(response_skills)} skill(s). Review them and confirm the ones "
            "that are accurate before they affect your recommendations."
        ),
    )


def list_uploads(db: Session, user: User, *, limit: int, offset: int) -> tuple[int, list[ResumeUploadRead]]:
    from sqlalchemy import func

    total = int(
        db.scalar(
            select(func.count())
            .select_from(ResumeUpload)
            .where(ResumeUpload.user_id == user.id)
        )
        or 0
    )
    uploads = list(
        db.scalars(
            select(ResumeUpload)
            .where(ResumeUpload.user_id == user.id)
            .order_by(ResumeUpload.created_at.desc(), ResumeUpload.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return total, [_to_read(upload) for upload in uploads]


def get_upload(db: Session, user: User, upload_id: int) -> tuple[ResumeUpload, list[ResumeDetectedSkill]]:
    """Ownership enforced in the query — this is the S5 IDOR fix.

    The legacy ``guidance.py:31`` did ``Upload.query.get(upload_id)`` with no auth
    and no ownership check, on a sequential integer id. Anyone could read anyone
    else's CV text.
    """
    upload = db.scalar(
        select(ResumeUpload).where(
            ResumeUpload.id == upload_id, ResumeUpload.user_id == user.id
        )
    )
    if upload is None:
        raise NotFoundError("That upload does not exist.")
    staged = list(
        db.scalars(
            select(ResumeDetectedSkill)
            .where(ResumeDetectedSkill.resume_upload_id == upload.id)
            .order_by(ResumeDetectedSkill.occurrence_count.desc())
        ).all()
    )
    return upload, staged


def get_text(db: Session, user: User, upload_id: int) -> str:
    upload, _ = get_upload(db, user, upload_id)
    return upload.extracted_text or ""


def delete_upload(db: Session, user: User, upload_id: int) -> None:
    """Delete the row and unlink the file.

    Proposal section 7.5 requires the ability to delete uploaded files, so the
    physical file goes too — deleting only the row would leave the user's CV text
    on disk, which is the opposite of what the requirement means.
    """
    upload, _ = get_upload(db, user, upload_id)
    settings = get_settings()
    path = Path(settings.upload_dir) / upload.stored_filename
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:  # pragma: no cover - filesystem dependent
        logger.warning("Could not unlink %s: %s", path, exc, extra={"kind": "cv"})

    db.delete(upload)
    db.commit()
    logger.info("Deleted upload id=%s user=%s", upload_id, user.id)
