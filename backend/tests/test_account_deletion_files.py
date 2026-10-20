"""Deleting the account deletes the files too.

Proposal section 6.4 lists the privacy mitigation for uploaded CVs as
"store only extracted skills where possible, **allow deletion of files and
profile**", and section 7.5 lists it again as a requirement. The database
cascade removes the ``resume_upload`` rows when an account is deleted, but a
row is not a file: without an explicit unlink, the CV itself survives on disk
with the user's name, contact details and employment history in plain text.

The test uploads a real document, deletes the account, and checks the file
is gone from the upload directory. Counting files before and after, rather
than looking for one name, keeps it honest when the suite runs in parallel
with other tests writing to the same directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings


@pytest.fixture
def docx_bytes() -> bytes:
    """A minimal valid .docx, built with the same helper the CV tests use."""
    import io

    from docx import Document

    document = Document()
    document.add_paragraph("Md. Aminul")
    document.add_paragraph("aminul@example.com")
    document.add_paragraph("Senior Machine Learning Engineer")
    document.add_paragraph("Python, PyTorch, scikit-learn, Docker, Kubernetes")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _upload(client: TestClient, docx_bytes: bytes) -> tuple[int, Path]:
    response = client.post(
        "/api/cv/upload",
        files={
            "file": (
                "cv.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text
    upload_id = response.json()["resume_upload_id"]
    stored = Path(get_settings().upload_dir)
    files = list(stored.glob("*.docx"))
    assert files, "the upload did not write a file"
    return upload_id, stored


def test_deleting_the_account_removes_the_uploaded_cv_from_disk(
    auth_client, docx_bytes: bytes
) -> None:
    """The file goes, not just the row."""
    client, user = auth_client()
    _upload_id, stored = _upload(client, docx_bytes)
    before = len(list(stored.glob("*.docx")))
    assert before >= 1

    assert client.delete("/api/auth/me").status_code == 204

    after = len(list(stored.glob("*.docx")))
    assert after == before - 1, "the CV was left on disk after the account was deleted"


def test_the_upload_row_is_removed_too(auth_client, docx_bytes: bytes, db: Session) -> None:
    """The database cascade still does its job."""
    from sqlalchemy import select

    from app.models.resume import ResumeUpload

    client, _user = auth_client()
    upload_id, _stored = _upload(client, docx_bytes)

    assert db.scalar(select(ResumeUpload).where(ResumeUpload.id == upload_id)) is not None

    assert client.delete("/api/auth/me").status_code == 204

    assert db.scalar(select(ResumeUpload).where(ResumeUpload.id == upload_id)) is None


def test_deleting_an_account_with_no_uploads_still_succeeds(auth_client) -> None:
    """The purge is a no-op for a user who never uploaded anything."""
    client, _user = auth_client()
    assert client.delete("/api/auth/me").status_code == 204


def test_the_account_is_deleted_even_when_a_file_cannot_be_removed(
    auth_client, docx_bytes: bytes, monkeypatch
) -> None:
    """A locked file must not make the account undeletable.

    Failing the deletion because one file could not be unlinked would leave
    the user unable to delete their account at all, which is worse than the
    file remaining.
    """
    from app.services import cv_service

    client, _user = auth_client()
    _upload(client, docx_bytes)

    def explode(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(cv_service.Path, "unlink", explode, raising=False)
    monkeypatch.setattr(cv_service.Path, "exists", lambda self: True, raising=False)

    assert client.delete("/api/auth/me").status_code == 204
