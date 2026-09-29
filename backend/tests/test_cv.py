"""T107/T092/T093 — the CV pipeline: PDF/DOCX in, staged skills out.

Two invariants matter more than anything else here:

1. **Nothing reaches ``user_skill`` on upload.** Detection stages into
   ``resume_detected_skill``; only ``POST /api/skills/confirm`` promotes a skill.
   That is what makes "every skill in ``user_skill`` is user-confirmed" checkable.
2. **A scanned PDF returns ``422``** with a message a user can act on, rather than
   silently reporting zero skills — which would tell the user their CV was read and
   found nothing, which is both wrong and undiscoverable.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.ml.text_loader import (
    DocumentTooLargeError,
    ExtractionFailedError,
    ScannedDocumentError,
    UnsupportedDocumentError,
    extract_text,
)

CV_TEXT = """Farhana Akter
Machine Learning Engineer
farhana@example.com

SUMMARY
Machine learning engineer specialising in computer vision and NLP.

SKILLS
Python, scikit-learn, PyTorch, pandas, NumPy, SQL, Docker, TensorFlow, spaCy, JavaScript

EXPERIENCE
Built a CNN image classifier with PyTorch and served it through a FastAPI API on AWS.
Used scikit-learn with cross-validation for tabular regression.
Deployed with Docker and Kubernetes.
"""


# ---------------------------------------------------------------------------
# Fixtures that build real documents
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def docx_bytes() -> bytes:
    import docx

    document = docx.Document()
    for line in CV_TEXT.splitlines():
        if line:
            document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """A real PDF built in-process, so no binary fixture is committed."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    y = 720
    for line in CV_TEXT.splitlines():
        if y < 60:
            pdf.showPage()
            y = 720
        pdf.drawString(60, y, line[:95])
        y -= 14
    pdf.save()
    return buffer.getvalue()


@pytest.fixture(scope="module")
def blank_pdf_bytes() -> bytes:
    """A PDF with no text layer at all — the scanned-document case."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    pdf.rect(50, 50, 500, 700, fill=1)  # a filled rectangle: pixels, no glyphs
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def cv_client(client: TestClient, make_user, taxonomy_seed) -> TestClient:
    user = make_user(email="cv@example.com", name="CV User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(scope="module")
def _reportlab() -> None:
    pytest.importorskip("reportlab", reason="needed to build PDF fixtures in-process")


# ---------------------------------------------------------------------------
# text_loader unit tests
# ---------------------------------------------------------------------------
def test_docx_text_is_extracted(docx_bytes: bytes, tmp_path) -> None:
    path = tmp_path / "cv.docx"
    path.write_bytes(docx_bytes)
    text = extract_text(path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert "Farhana Akter" in text
    assert "scikit-learn" in text
    assert len(text) > 200


def test_pdf_text_is_extracted(pdf_bytes: bytes, tmp_path) -> None:
    path = tmp_path / "cv.pdf"
    path.write_bytes(pdf_bytes)
    text = extract_text(path, "application/pdf")
    assert "Farhana Akter" in text
    assert len(text) > 200


def test_scanned_pdf_raises_scanned_document_error(blank_pdf_bytes: bytes, tmp_path) -> None:
    """OCR is out of scope; the error must be explicit, not a silent empty result."""
    path = tmp_path / "scanned.pdf"
    path.write_bytes(blank_pdf_bytes)
    with pytest.raises(ScannedDocumentError) as exc:
        extract_text(path, "application/pdf")
    message = str(exc.value)
    assert "OCR" in message
    assert "scanned" in message.lower()


def test_oversize_file_is_rejected(tmp_path) -> None:
    path = tmp_path / "big.pdf"
    path.write_bytes(b"0" * 5000)
    with pytest.raises(DocumentTooLargeError):
        extract_text(path, "application/pdf", max_bytes=1000)


def test_unsupported_type_is_rejected(tmp_path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    with pytest.raises(UnsupportedDocumentError):
        extract_text(path, "text/plain")


def test_missing_file_raises(tmp_path) -> None:
    # The precise type, not a bare Exception: a bare one would also pass if the
    # function raised for an unrelated reason. ExtractionFailedError is what the
    # loader raises when a stored upload has gone missing, which is an internal
    # inconsistency rather than a caller's bad path.
    with pytest.raises(ExtractionFailedError):
        extract_text(tmp_path / "absent.pdf", "application/pdf")


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------
def test_upload_requires_authentication(client: TestClient, docx_bytes: bytes) -> None:
    """S4: the legacy upload routes accepted anonymous writes."""
    response = client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 401


def test_docx_upload_extracts_and_detects(
    cv_client: TestClient, docx_bytes: bytes, skill_ids: dict[str, int]
) -> None:
    response = cv_client.post(
        "/api/cv/upload",
        files={"file": ("farhana.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "extracted"
    assert body["text_length"] > 200
    assert body["filename"] == "farhana.docx"

    detected = {s["slug"]: s for s in body["detected_skills"]}
    for slug in ("python", "scikit-learn", "pytorch", "pandas", "sql", "docker", "spacy"):
        assert slug in detected, f"{slug} not detected; got {sorted(detected)}"
    assert detected["scikit-learn"]["surface_form"].lower() in {"scikit-learn", "scikit learn"}


def test_upload_stages_and_does_not_pollute_user_skills(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    """The central invariant: extraction alone never changes the user's profile."""
    assert cv_client.get("/api/skills").json() == []
    cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert cv_client.get("/api/skills").json() == [], "upload wrote straight to user_skill"


def test_pdf_upload(cv_client: TestClient, pdf_bytes: bytes) -> None:
    response = cv_client.post(
        "/api/cv/upload", files={"file": ("farhana.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 201
    assert response.json()["detected_skills"]


def test_scanned_pdf_returns_422_with_a_clear_message(
    cv_client: TestClient, blank_pdf_bytes: bytes
) -> None:
    response = cv_client.post(
        "/api/cv/upload", files={"file": ("scan.pdf", blank_pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ocr_not_supported"
    assert "OCR" in body["error"]["message"]
    assert "scanned" in body["error"]["message"].lower()


@pytest.mark.parametrize(
    ("filename", "content_type", "expected"),
    [
        ("cv.txt", "text/plain", 415),
        ("cv.exe", "application/octet-stream", 415),
        # Right extension, wrong content type: the extension check alone is not
        # enough, because the caller controls the filename.
        ("cv.pdf", "text/html", 415),
        ("cv.exe", "application/pdf", 415),
    ],
)
def test_upload_validates_type(
    cv_client: TestClient, filename: str, content_type: str, expected: int, docx_bytes: bytes
) -> None:
    response = cv_client.post(
        "/api/cv/upload", files={"file": (filename, docx_bytes, content_type)}
    )
    assert response.status_code == expected, response.text


def test_oversize_upload_returns_413(cv_client: TestClient) -> None:
    payload = b"%PDF-1.4\n" + b"0" * (6 * 1024 * 1024)
    response = cv_client.post(
        "/api/cv/upload", files={"file": ("big.pdf", payload, "application/pdf")}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_empty_upload_is_rejected(cv_client: TestClient) -> None:
    response = cv_client.post(
        "/api/cv/upload", files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 422


def test_missing_file_field_returns_422(cv_client: TestClient) -> None:
    assert cv_client.post("/api/cv/upload", data={}).status_code == 422


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------
def test_confirmation_promotes_only_accepted_skills(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    upload = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    detected = upload["detected_skills"]
    assert len(detected) >= 5

    accept, reject = detected[0], detected[1]
    result = cv_client.post(
        "/api/skills/confirm",
        json={
            "resume_upload_id": upload["resume_upload_id"],
            "skills": [
                {"skill_id": accept["skill_id"], "accepted": True, "proficiency": 4},
                {"skill_id": reject["skill_id"], "accepted": False},
            ],
        },
    )
    assert result.status_code == 200
    assert result.json()["added"] == 1
    assert result.json()["declined"] == 1

    held = {s["skill_id"] for s in cv_client.get("/api/skills").json()}
    assert accept["skill_id"] in held
    assert reject["skill_id"] not in held

    confirmed = next(
        s for s in held if s == accept["skill_id"]
    )
    assert confirmed == accept["skill_id"]


def test_confirmed_skills_are_marked_cv_extracted(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    upload = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    first = upload["detected_skills"][0]
    cv_client.post(
        "/api/skills/confirm",
        json={"skills": [{"skill_id": first["skill_id"], "accepted": True, "proficiency": 4}]},
    )
    stored = next(
        s for s in cv_client.get("/api/skills").json() if s["skill_id"] == first["skill_id"]
    )
    assert stored["source"] == "cv_extracted"
    assert stored["confirmed"] is True
    assert stored["proficiency"] == 4


def test_upload_status_becomes_confirmed(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    upload = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    first = upload["detected_skills"][0]
    cv_client.post(
        "/api/skills/confirm",
        json={
            "resume_upload_id": upload["resume_upload_id"],
            "skills": [{"skill_id": first["skill_id"], "accepted": True}],
        },
    )
    detail = cv_client.get(f"/api/cv/{upload['resume_upload_id']}").json()
    assert detail["status"] == "confirmed"
    assert any(s["accepted"] for s in detail["detected_skills"])


def test_already_confirmed_skills_are_flagged(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    upload = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    first = upload["detected_skills"][0]
    cv_client.post(
        "/api/skills/confirm", json={"skills": [{"skill_id": first["skill_id"], "accepted": True}]}
    )
    again = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv2.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()
    assert first["canonical_name"] in again["already_confirmed"]
    flagged = [s for s in again["detected_skills"] if s["skill_id"] == first["skill_id"]]
    assert flagged[0]["already_confirmed"] is True


# ---------------------------------------------------------------------------
# Reading and deleting
# ---------------------------------------------------------------------------
def test_upload_can_be_read_back(cv_client: TestClient, docx_bytes: bytes) -> None:
    upload_id = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()["resume_upload_id"]

    detail = cv_client.get(f"/api/cv/{upload_id}").json()
    assert detail["id"] == upload_id
    assert detail["detected_skills"]
    assert detail["text_length"] > 200

    text = cv_client.get(f"/api/cv/{upload_id}/text").json()
    assert "Farhana Akter" in text["text"]

    listed = cv_client.get("/api/cv").json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == upload_id


def test_delete_removes_the_row_and_the_file(
    cv_client: TestClient, docx_bytes: bytes
) -> None:
    from pathlib import Path

    from app.core.config import get_settings

    upload_id = cv_client.post(
        "/api/cv/upload",
        files={"file": ("cv.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    ).json()["resume_upload_id"]
    stored = Path(get_settings().upload_dir)
    before = len(list(stored.glob("*.docx")))
    assert before >= 1

    assert cv_client.delete(f"/api/cv/{upload_id}").status_code == 204
    assert cv_client.get(f"/api/cv/{upload_id}").status_code == 404
    assert len(list(stored.glob("*.docx"))) == before - 1, "the file was left on disk"
    assert cv_client.delete(f"/api/cv/{upload_id}").status_code == 404


def test_stored_filename_is_a_uuid_not_the_original(
    cv_client: TestClient, docx_bytes: bytes, db
) -> None:
    from sqlalchemy import select

    from app.models.resume import ResumeUpload

    cv_client.post(
        "/api/cv/upload",
        files={"file": ("../../etc/passwd.docx", docx_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    stored = db.scalars(select(ResumeUpload)).all()
    assert stored
    for upload in stored:
        assert "/" not in upload.stored_filename
        assert ".." not in upload.stored_filename
        assert len(upload.stored_filename) == 32 + len(".docx")
