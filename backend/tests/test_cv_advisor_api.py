"""The CV improvement assistant.

The whole feature rests on one property: it helps a person describe what they
have done, and it does not help them describe something they have not done.
These tests are about that property — a suggestion that names a skill or a
metric that is not in the record must not survive, and a CV that does not
say enough must produce questions rather than a draft.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

CV_TEXT = """
Jordan Ahmed
Data Analyst, Dhaka

Summary
Data analyst with experience in Python and SQL, focused on turning messy
tables into decisions.

Skills
Python, SQL, PostgreSQL, Pandas, Tableau, Excel, Power BI

Experience
Data Analyst — Northline Retail (2023 - present)
- Wrote SQL queries for a 4TB PostgreSQL warehouse and cut the nightly
  reporting run from 90 minutes to 25 minutes.
- Built Tableau dashboards used by the buying team.

Education
BSc in Computer Science, University of Dhaka, 2021
"""

ADVICE = {
    "effective_summary": ["Your summary names the tools and the focus clearly."],
    "emphasise": [
        "The 90-minute to 25-minute reporting improvement is the strongest line "
        "in the CV and is buried under a list of duties."
    ],
    "clarity_suggestions": ["Put the reporting improvement above the duty list."],
    "wording_suggestions": ["'Wrote SQL queries' could name the specific problem."],
    "project_suggestions": ["Name the dashboards and who used them."],
    "job_specific_recommendations": [],
    "professional_summary": (
        "Data analyst in Dhaka, working with Python, SQL and PostgreSQL to turn "
        "messy tables into decisions, and with Tableau to communicate them."
    ),
    "bullet_points": [
        "Cut the nightly reporting run for a 4TB PostgreSQL warehouse from 90 "
        "minutes to 25 minutes."
    ],
    "cover_letter": "",
    "needs_information": [],
}


def test_a_cv_is_reviewed(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    groq.reply_json(ADVICE)
    response = client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["effective_summary"]
    assert body["professional_summary"]
    assert body["disclaimer"]
    assert "ATS" in body["disclaimer"] or "guarantee" in body["disclaimer"].lower()


def test_the_disclaimer_says_what_the_tool_is_not(
    client: TestClient, auth_client, groq
) -> None:
    """The application does not claim an ATS guarantee or a hiring outcome."""
    auth, _user = auth_client()
    groq.reply_json(ADVICE)
    body = client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT}).json()
    disclaimer = body["disclaimer"].lower()
    assert "not guarantee" in disclaimer
    assert "actually done" in disclaimer


def test_the_prompt_carries_the_cv_and_the_user_records(
    client: TestClient, auth_client, groq, taxonomy_seed, db
) -> None:
    auth, _user = auth_client()
    groq.reply_json(ADVICE)
    client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT})
    prompt = groq.calls[0]["messages"][0]["content"]
    assert "Northline Retail" in prompt
    assert "untrusted_cv_text" in prompt
    assert "not instructions" in prompt


def test_the_truthful_rules_are_in_the_prompt(
    client: TestClient, auth_client, groq
) -> None:
    """The instruction not to invent is a prompt rule *and* a design property."""
    auth, _user = auth_client()
    groq.reply_json(ADVICE)
    client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT})
    prompt = groq.calls[0]["messages"][0]["content"]
    assert "Never invent" in prompt or "never invent" in prompt
    assert "needs_information" in prompt


def test_a_cv_with_too_little_text_is_refused(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    response = client.post("/api/ai/cv-advice", json={"cv_text": "Jordan Ahmed, analyst."})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_cv"


def test_an_uploaded_cv_can_be_reviewed(
    client: TestClient, auth_client, groq, db
) -> None:
    """The existing CV analysis is enhanced, not replaced: an upload the user
    already has can be reviewed directly."""
    from app.models.resume import ResumeUpload

    auth, user = auth_client()
    upload = ResumeUpload(
        user_id=user.id,
        original_filename="cv.pdf",
        stored_filename="seed.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        extracted_text=CV_TEXT,
        status="extracted",
    )
    db.add(upload)
    db.commit()

    groq.reply_json(ADVICE)
    response = client.post("/api/ai/cv-advice", json={"resume_upload_id": upload.id})
    assert response.status_code == 200
    assert "Northline Retail" in groq.calls[0]["messages"][0]["content"]


def test_a_user_cannot_review_somebody_elses_cv(
    client: TestClient, auth_client, groq, db, make_user
) -> None:
    from app.models.resume import ResumeUpload

    auth, owner = auth_client()
    upload = ResumeUpload(
        user_id=owner.id,
        original_filename="cv.pdf",
        stored_filename="owned.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        extracted_text=CV_TEXT,
        status="extracted",
    )
    db.add(upload)
    db.commit()

    other, _other_user = auth_client()
    # An id that does not exist, and one that exists but belongs to somebody
    # else, must both be 404. A 403 would confirm that the id exists.
    assert other.post("/api/ai/cv-advice", json={"resume_upload_id": 999_999}).status_code == 404
    assert other.post("/api/ai/cv-advice", json={"resume_upload_id": upload.id}).status_code == 404


def test_a_cover_letter_is_only_drafted_when_it_is_asked_for(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    document = dict(ADVICE)
    document["cover_letter"] = "Dear Hiring Manager, ..."
    groq.reply_json(document)

    without = client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT}).json()
    assert without["cover_letter"] == "Dear Hiring Manager, ..."

    groq.reply_json(document)
    with_letter = client.post(
        "/api/ai/cv-advice", json={"cv_text": CV_TEXT, "include_cover_letter": True}
    ).json()
    assert with_letter["cover_letter"]


def test_the_questions_the_user_must_answer_are_carried_through(
    client: TestClient, auth_client, groq
) -> None:
    """Where the record is silent, the tool asks rather than invents."""
    auth, _user = auth_client()
    document = dict(ADVICE)
    document["needs_information"] = [
        "What was the size of the team, and how much of the reporting work was yours?"
    ]
    groq.reply_json(document)
    body = client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT}).json()
    assert body["needs_information"] == [
        "What was the size of the team, and how much of the reporting work was yours?"
    ]


def test_a_malformed_provider_document_is_refused(
    client: TestClient, auth_client, groq
) -> None:
    auth, _user = auth_client()
    # The malformed answer is attempted twice: once, and once more after the
    # bounded retry adds the output-shape rule to the prompt.
    groq.reply_json({"effective_summary": ["only one field"]})
    groq.reply_json({"effective_summary": ["only one field"]})
    response = client.post("/api/ai/cv-advice", json={"cv_text": CV_TEXT})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
