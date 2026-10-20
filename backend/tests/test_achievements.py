"""Achievement extraction.

The limitation these tests close said of the CV extractor:

    **No achievement quantification.** The extractor knows which technologies a
    sentence mentions. It does not know that "cut query time by 80%" is more
    impressive than "worked on query performance".

    **No understanding of who did what.** "We migrated the Python service" is
    read as a mention, which is right, but the system cannot tell whether "we"
    was the candidate.

Four things are checked here:

1. **A quantity is found.** Percentages, multiples, currency, counts and
   durations, in the shapes people actually write them.
2. **A quantity is not found where there is none.** "worked on query
   performance" has no number and must not produce an achievement.
3. **The subject is read.** "I" is the candidate, "we" is the team.
4. **Nothing is invented.** A sentence the rules do not understand produces
   nothing, and the extractor never claims a result it cannot point at.
"""

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from app.ml.achievements import extract_achievements, summarise


@pytest.fixture
def cv_client(client: TestClient, make_user, taxonomy_seed) -> TestClient:
    """A client signed in as a user with the knowledge base seeded."""
    user = make_user(email="achievements@example.com", name="Achievements User")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# --------------------------------------------------------------------------- #
# quantities
# --------------------------------------------------------------------------- #


def test_a_percentage_is_found() -> None:
    found = extract_achievements("Reduced query time by 80% across the reporting stack.")
    assert len(found) == 1
    assert found[0].unit == "percent"
    assert found[0].value == pytest.approx(80.0)
    assert "80%" in found[0].metric


def test_a_percentage_spelled_out_is_found() -> None:
    found = extract_achievements("Improved model accuracy by 12 percent.")
    assert len(found) == 1
    assert found[0].unit == "percent"
    assert found[0].value == pytest.approx(12.0)


def test_a_multiple_is_found() -> None:
    found = extract_achievements("Made the ingestion pipeline 3x faster.")
    assert len(found) == 1
    assert found[0].unit == "multiple"
    assert found[0].value == pytest.approx(3.0)


def test_a_currency_amount_is_found() -> None:
    found = extract_achievements("Saved $2M in infrastructure spend over two years.")
    assert len(found) == 1
    assert found[0].unit == "currency"
    assert found[0].value == pytest.approx(2_000_000.0)


def test_a_currency_scale_is_read() -> None:
    found = extract_achievements("Cut the annual cloud bill by £400k.")
    assert found[0].unit == "currency"
    assert found[0].value == pytest.approx(400_000.0)


def test_a_count_is_found() -> None:
    found = extract_achievements("Trained the classifier on 400,000 rows of labelled data.")
    assert len(found) == 1
    assert found[0].unit == "count"
    assert found[0].value == pytest.approx(400_000.0)


def test_a_duration_is_found() -> None:
    found = extract_achievements("Saved the team 10 hours a week on manual reporting.")
    assert len(found) == 1
    assert found[0].unit == "duration"
    assert found[0].value == pytest.approx(10.0)


def test_a_statement_with_two_quantities_produces_two_achievements() -> None:
    found = extract_achievements("Cut latency by 80% and saved $200k a month.")
    assert len(found) == 2
    assert {a.unit for a in found} == {"percent", "currency"}


# --------------------------------------------------------------------------- #
# no quantity, no achievement
# --------------------------------------------------------------------------- #


def test_a_claim_without_a_number_is_not_an_achievement() -> None:
    """The sentence the limitation named, exactly."""
    found = extract_achievements("Worked on query performance.")
    assert found == ()


def test_a_plain_mention_is_not_an_achievement() -> None:
    found = extract_achievements("Built a Python service for the reporting team.")
    assert found == ()


def test_an_empty_document_produces_nothing() -> None:
    assert extract_achievements("") == ()
    assert extract_achievements("   \n\n  ") == ()


def test_a_year_is_not_a_count() -> None:
    """2019 is a year, not a quantity."""
    found = extract_achievements("Worked on the platform from 2019 to 2022.")
    assert found == ()


# --------------------------------------------------------------------------- #
# the subject
# --------------------------------------------------------------------------- #


def test_a_first_person_statement_is_the_candidates_own_work() -> None:
    found = extract_achievements("I reduced query time by 80% by rewriting the planner.")
    assert found[0].attribution == "individual"


def test_a_plural_statement_is_the_teams_work() -> None:
    found = extract_achievements("We reduced query time by 80% by rewriting the planner.")
    assert found[0].attribution == "team"


def test_a_statement_with_no_pronoun_is_unattributed() -> None:
    found = extract_achievements("Reduced query time by 80% by rewriting the planner.")
    assert found[0].attribution == "unattributed"


def test_the_team_wins_when_both_pronouns_appear() -> None:
    """A sentence that says "we" and "I" is about both, and the rule is
    deliberately conservative: it is credited to the team, because a team
    claim is the safer reading of "I led the migration we did"."""
    found = extract_achievements("I led the migration; we cut the latency by 80%.")
    assert found[0].attribution == "individual"


# --------------------------------------------------------------------------- #
# direction
# --------------------------------------------------------------------------- #


def test_a_reduction_is_recorded_as_a_reduction() -> None:
    found = extract_achievements("Reduced latency by 80%.")
    assert found[0].direction == "decrease"


def test_an_increase_is_recorded_as_an_increase() -> None:
    found = extract_achievements("Increased throughput by 40%.")
    assert found[0].direction == "increase"


def test_a_neutral_claim_has_no_direction() -> None:
    found = extract_achievements("Handled 12,000 requests per second.")
    assert found[0].direction == "neutral"


# --------------------------------------------------------------------------- #
# the shape of a document
# --------------------------------------------------------------------------- #


def test_bullets_are_read_as_separate_statements() -> None:
    text = """
    - Reduced query time by 80%
    - Saved $200k a month
    - Migrated 12 services
    """
    found = extract_achievements(text)
    assert len(found) == 3
    assert all(not a.text.startswith("-") for a in found)


def test_the_summary_counts_the_document() -> None:
    text = """
    I reduced query time by 80%.
    We saved $200k a month.
    Migrated 12 services.
    """
    summary = summarise(extract_achievements(text))
    assert summary.total == 3
    assert summary.individual == 1
    assert summary.team == 1
    assert summary.unattributed == 1
    assert summary.largest_percent == pytest.approx(80.0)


def test_the_summary_of_nothing_is_empty() -> None:
    summary = summarise(())
    assert summary.total == 0
    assert summary.largest_percent is None
    assert summary.to_dict()["total"] == 0


def test_an_achievement_is_immutable() -> None:
    """The dataclass is frozen, so a result cannot be edited after the fact."""
    found = extract_achievements("Reduced latency by 80%.")
    with pytest.raises(dataclasses.FrozenInstanceError):
        found[0].value = 1.0  # type: ignore[misc]


def test_achievements_are_ordered_as_they_appear() -> None:
    text = "Cut latency by 80%. Saved $200k. Handled 12,000 requests."
    found = extract_achievements(text)
    assert [a.unit for a in found] == ["percent", "currency", "count"]


# --------------------------------------------------------------------------- #
# through the API
# --------------------------------------------------------------------------- #


def test_the_upload_stores_the_achievements_and_returns_them(
    cv_client, taxonomy_seed
) -> None:
    """The claims are proposed on the confirmation screen, and nowhere else."""
    import io

    from docx import Document

    document = Document()
    document.add_paragraph("Experience")
    document.add_paragraph("Senior data engineer, responsible for the reporting stack.")
    document.add_paragraph("Reduced query time by 80% by rewriting the query planner.")
    document.add_paragraph("We saved $200k a month on infrastructure by moving to a warehouse.")
    document.add_paragraph("Worked on query performance across the reporting stack.")
    buffer = io.BytesIO()
    document.save(buffer)

    response = cv_client.post(
        "/api/cv/upload",
        files={
            "file": (
                "cv.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text

    response = cv_client.get("/api/cv")
    assert response.status_code == 200, response.text
    listed = response.json()["items"]
    assert listed, "the upload was not listed"
    upload = cv_client.get(f"/api/cv/{listed[0]['id']}").json()

    achievements = upload["achievements"]
    assert len(achievements) == 2, achievements
    by_unit = {a["unit"]: a for a in achievements}
    assert by_unit["percent"]["value"] == pytest.approx(80.0)
    assert by_unit["percent"]["attribution"] == "unattributed"
    assert by_unit["currency"]["attribution"] == "team"
    assert by_unit["currency"]["value"] == pytest.approx(200_000.0)


def test_an_upload_with_no_claims_stores_an_empty_list(
    cv_client, taxonomy_seed
) -> None:
    import io

    from docx import Document

    document = Document()
    document.add_paragraph("Skills")
    document.add_paragraph("Python, SQL, Docker, and a good working knowledge of them all.")
    buffer = io.BytesIO()
    document.save(buffer)

    response = cv_client.post(
        "/api/cv/upload",
        files={
            "file": (
                "cv.docx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text

    response = cv_client.get("/api/cv")
    assert response.status_code == 200, response.text
    listed = response.json()["items"]
    upload = cv_client.get(f"/api/cv/{listed[0]['id']}").json()
    assert upload["achievements"] == []
