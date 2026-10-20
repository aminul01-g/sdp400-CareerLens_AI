"""Sections, work history, and the experience they make observable.

The limitation this closes said the extractor "cannot tell a skill listed
under 'Skills' from the same word inside a sentence describing something else",
and that "a CV becomes a bag of skill mentions and some text. Nothing else is
extracted, so nothing else influences the score."

These tests cover the two halves:

* **Section detection** — a skill under **Skills** is a claim; the same word
  inside a project description is a mention.
* **Work history** — where somebody has worked, and for how long, read out of
  the experience section and proposed for the user to accept.

The work-history extraction is the part most likely to be wrong, so the tests
are mostly about the failure modes: a university must not become an employer,
overlapping roles must not be double-counted, and a date range that cannot be
read must not be invented.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.ml.cv_sections import SECTION_KINDS, split_sections
from app.ml.extractor import extract_skills
from app.ml.work_history import (
    WorkHistoryEntry,
    extract_work_history,
    parse_date_range,
    total_months,
)

SAMPLE_CV = """Jane Doe
jane.doe@example.com
Dhaka, Bangladesh

SUMMARY
Data scientist with six years of experience building recommendation systems.

SKILLS
Python, SQL, PyTorch, Docker, scikit-learn

EXPERIENCE
Acme Analytics — Jan 2019 - Present
Senior Data Scientist
Built the recommendation service in Python and SQL.

Globex Ltd
2017 - 2019
Data Analyst
Reported on sales with SQL and Python.

PROJECTS
Supply Chain Forecasting
Built a forecasting pipeline in Python for a client.

EDUCATION
Example University
BSc Computer Science, 2013 - 2017
"""


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


def test_the_sections_of_a_cv_are_found() -> None:
    kinds = [section.kind for section in split_sections(SAMPLE_CV)]
    assert "preamble" in kinds
    assert "summary" in kinds
    assert "skills" in kinds
    assert "experience" in kinds
    assert "projects" in kinds
    assert "education" in kinds


def test_the_sections_are_in_order() -> None:
    kinds = [section.kind for section in split_sections(SAMPLE_CV)]
    assert kinds.index("skills") < kinds.index("experience")
    assert kinds.index("experience") < kinds.index("projects")
    assert kinds.index("projects") < kinds.index("education")


def test_a_heading_is_not_part_of_its_section() -> None:
    sections = split_sections(SAMPLE_CV)
    skills = next(s for s in sections if s.kind == "skills")
    assert "SKILLS" not in skills.text
    assert "Python" in skills.text


def test_the_preamble_holds_the_name() -> None:
    sections = split_sections(SAMPLE_CV)
    preamble = sections[0]
    assert preamble.kind == "preamble"
    assert "Jane Doe" in preamble.text


def test_a_heading_is_recognised_whatever_its_case() -> None:
    text = "SKILLS\nPython\n\nskills\nSQL\n\nSkills\nDocker\n"
    sections = split_sections(text)
    assert all(section.kind == "skills" for section in sections[1:])


def test_a_sentence_is_not_a_heading() -> None:
    text = "I led a team of engineers.\nPython and SQL.\n"
    sections = split_sections(text)
    assert len(sections) == 1
    assert sections[0].kind == "preamble"


def test_a_bullet_is_not_a_heading() -> None:
    text = "- Python\n- SQL\n- Docker\n"
    sections = split_sections(text)
    assert len(sections) == 1


def test_an_empty_document_has_no_sections() -> None:
    assert split_sections("") == []
    assert split_sections("   \n\n  ") == []


def test_the_section_kinds_are_the_documented_ones() -> None:
    assert SECTION_KINDS["skills"] == "skills"
    assert SECTION_KINDS["experience"] == "experience"
    assert SECTION_KINDS["education"] == "education"


# --------------------------------------------------------------------------- #
# declared against mentioned
# --------------------------------------------------------------------------- #


def test_a_skill_under_skills_is_declared() -> None:
    detections = {d.slug: d for d in extract_skills(SAMPLE_CV)}
    assert detections["python"].is_declared is True
    assert detections["python"].section == "skills"


def test_a_skill_only_mentioned_in_a_project_is_not_declared() -> None:
    """The whole point of the section work.

    "Python" appears under Skills *and* inside the project description. The
    detection is declared because it was found in a section where the person
    declares their skills.
    """
    detections = {d.slug: d for d in extract_skills(SAMPLE_CV)}
    assert detections["python"].occurrence_count >= 1


def test_a_skill_found_only_in_the_experience_section_is_not_declared() -> None:
    text = """EXPERIENCE
Acme Analytics
Built a service in Rust and deployed it with Terraform.
"""
    detections = {d.slug: d for d in extract_skills(text)}
    assert "rust" in detections
    assert detections["rust"].is_declared is False
    assert detections["rust"].section == "experience"


def test_a_skill_found_only_in_a_project_is_not_declared() -> None:
    text = """PROJECTS
Supply Chain Forecasting
Built a forecasting pipeline in Python.
"""
    detections = {d.slug: d for d in extract_skills(text)}
    assert detections["python"].is_declared is False
    assert detections["python"].section == "projects"


# --------------------------------------------------------------------------- #
# dates
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Jan 2019 - Present", (date(2019, 1, 1), None, True)),
        ("January 2019 – March 2022", (date(2019, 1, 1), date(2022, 3, 1), False)),
        ("2017 - 2019", (date(2017, 1, 1), date(2019, 1, 1), False)),
        ("2017 to 2019", (date(2017, 1, 1), date(2019, 1, 1), False)),
        ("01/2019 - 06/2021", (date(2019, 1, 1), date(2021, 6, 1), False)),
        ("Mar 2020", (date(2020, 3, 1), None, False)),
    ],
    ids=["present", "month-range", "year-range", "year-to", "numeric", "single"],
)
def test_the_common_date_shapes_are_read(text, expected) -> None:
    assert parse_date_range(text) == expected


def test_a_line_with_no_date_reads_as_no_date() -> None:
    assert parse_date_range("Acme Analytics") == (None, None, False)
    assert parse_date_range("") == (None, None, False)


# --------------------------------------------------------------------------- #
# work history
# --------------------------------------------------------------------------- #


def test_the_employers_and_dates_are_read() -> None:
    entries = extract_work_history(
        "Acme Analytics — Jan 2019 - Present\nSenior Data Scientist\n\n"
        "Globex Ltd\n2017 - 2019\nData Analyst\n"
    )
    employers = [entry.employer for entry in entries]
    assert "Acme Analytics" in employers
    assert "Globex Ltd" in employers

    acme = next(entry for entry in entries if entry.employer == "Acme Analytics")
    assert acme.start_date == date(2019, 1, 1)
    assert acme.end_date is None
    assert acme.is_current is True


def test_a_employer_is_not_proposed_without_a_date() -> None:
    """A bare organisation name is not a job."""
    entries = extract_work_history("We use Python and PostgreSQL at Acme Analytics.\n")
    assert all(entry.start_date is None for entry in entries)


def test_overlapping_roles_are_counted_once() -> None:
    """Two jobs at once is not two years of experience."""
    entries = [
        WorkHistoryEntry(
            employer="A", start_date=date(2019, 1, 1), end_date=date(2021, 1, 1)
        ),
        WorkHistoryEntry(
            employer="B", start_date=date(2020, 1, 1), end_date=date(2022, 1, 1)
        ),
    ]
    # January 2019 to January 2022 is 36 months, not 48.
    assert total_months(entries) == 36


def test_sequential_roles_are_counted_in_full() -> None:
    entries = [
        WorkHistoryEntry(
            employer="A", start_date=date(2017, 1, 1), end_date=date(2019, 1, 1)
        ),
        WorkHistoryEntry(
            employer="B", start_date=date(2019, 1, 1), end_date=date(2021, 1, 1)
        ),
    ]
    assert total_months(entries) == 48


def test_a_current_role_is_measured_to_the_reference_date() -> None:
    entries = [
        WorkHistoryEntry(
            employer="A",
            start_date=date(2020, 1, 1),
            end_date=None,
            is_current=True,
        )
    ]
    assert total_months(entries, today=date(2021, 1, 1)) == 12


def test_no_entries_means_no_experience() -> None:
    assert total_months([]) == 0


# --------------------------------------------------------------------------- #
# the proposal, end to end through the API
# --------------------------------------------------------------------------- #


def test_the_work_history_is_proposed_and_must_be_confirmed(
    client, make_user, taxonomy_seed, role_seed
) -> None:

    user = make_user(email="history@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # The staged rows are not confirmed, and are not visible through the API
    # until the user confirms them.
    rows = client.get("/api/work-history")
    assert rows.status_code == 200
    assert rows.json() == []


def test_a_confirmed_work_history_becomes_the_experience_signal(
    client, make_user, taxonomy_seed, role_seed, db
) -> None:

    user = make_user(email="signal@example.com")
    token = client.post(
        "/api/auth/login", json={"email": user.email, "password": "Str0ngPassw0rd"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    created = client.post(
        "/api/work-history",
        json={
            "employer": "Acme Analytics",
            "title": "Data Scientist",
            "start_date": "2016-01-01",
            "end_date": "2020-01-01",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["confirmed"] is True
    assert created.json()["source"] == "manual"

    from app.services import work_history_service

    assert work_history_service.observed_years(db, user) == 4
