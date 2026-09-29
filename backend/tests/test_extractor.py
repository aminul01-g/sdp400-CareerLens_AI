"""T094/T095 — skill extraction from text.

The two negative cases here are the most valuable tests in the whole suite. They
are the concrete failure modes that make a naive keyword matcher look competent in
a demo and useless in production, and they are exactly what a curated taxonomy
buys over a substring search.
"""

from __future__ import annotations

import pytest

from app.ml.extractor import extract_skill_slugs, extract_skills

SYNTHETIC_CV = """
Amina Rahman — Machine Learning Engineer
Dhaka, Bangladesh | amina@example.com

SUMMARY
Machine learning engineer with three years building and deploying models.

SKILLS
Python, scikit-learn (sklearn), PyTorch, pandas, NumPy, SQL, Docker, TensorFlow, spaCy

EXPERIENCE
Senior ML Engineer, Example Analytics (2023 - present)
  - Built a CNN image classifier in PyTorch and served it behind a FastAPI service.
  - Used scikit-learn for regression and cross-validation on tabular data.
  - Deployed with Docker on AWS. Wrote REST APIs with FastAPI.

Earlier: JavaScript and MongoDB in a web development role. Also Java and Go.
"""


@pytest.fixture(scope="module")
def detected() -> dict[str, int]:
    return {skill.slug: skill.occurrence_count for skill in extract_skills(SYNTHETIC_CV)}


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "slug",
    [
        "python", "scikit-learn", "pytorch", "pandas", "numpy",
        "sql", "docker", "tensorflow", "spacy", "fastapi",
        "aws", "cnn" if False else "convolutional-neural-networks",
        "machine-learning", "regression-analysis", "cross-validation", "rest-apis",
        "javascript", "mongodb", "java", "go",
    ],
)
def test_expected_skill_is_detected(detected: dict[str, int], slug: str) -> None:
    assert slug in detected, f"{slug} was not detected; got {sorted(detected)}"


def test_aliases_in_the_document_resolve_to_canonical_skills(detected: dict[str, int]) -> None:
    """The CV literally says "sklearn" and "cnn"; both must land on the canonical entry."""
    assert "scikit-learn" in detected
    assert "sklearn" not in detected, "the raw alias leaked through instead of the canonical skill"
    assert "convolutional-neural-networks" in detected


def test_occurrences_are_counted(detected: dict[str, int]) -> None:
    """The CV mentions PyTorch twice and scikit-learn twice."""
    assert detected["pytorch"] >= 2
    assert detected["scikit-learn"] >= 2


def test_results_are_sorted_by_descending_count() -> None:
    skills = extract_skills(SYNTHETIC_CV)
    counts = [s.occurrence_count for s in skills]
    assert counts == sorted(counts, reverse=True)


def test_skill_ids_are_populated() -> None:
    for skill in extract_skills(SYNTHETIC_CV):
        assert skill.skill_id > 0
        assert skill.canonical_name
        assert skill.slug
        assert skill.category


def test_match_offsets_are_recorded() -> None:
    skill = next(s for s in extract_skills(SYNTHETIC_CV) if s.slug == "docker")
    assert skill.match_start is not None and skill.match_end is not None
    assert skill.match_end > skill.match_start
    assert SYNTHETIC_CV[skill.match_start : skill.match_end]


# ---------------------------------------------------------------------------
# The two negative cases the plan names
# ---------------------------------------------------------------------------
def test_java_does_not_match_inside_javascript() -> None:
    """A document with only JavaScript must not report the Java language."""
    found = extract_skill_slugs("I write JavaScript and TypeScript every day.")
    assert "javascript" in found
    assert "java" not in found, "Java matched inside JavaScript"


def test_go_does_not_match_inside_mongodb() -> None:
    found = extract_skill_slugs("We run MongoDB and PostgreSQL in production.")
    assert "mongodb" in found
    assert "go" not in found, "Go matched inside MongoDB"


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("Django and JavaScript projects", "java"),
        ("Machine learning with MongoDB", "go"),
        ("R&D budget review with C-suite stakeholders", "r"),
        ("I go to university every morning", "go"),
        ("TypeScript and Golang services", "java"),
        ("MongoDB, PostgreSQL and Redis caches", "c"),
    ],
)
def test_no_substring_false_positives(text: str, forbidden: str) -> None:
    assert forbidden not in extract_skill_slugs(text)


@pytest.mark.parametrize(
    "text", ["", "   ", "\n\n\t", "The quick brown fox jumps over the lazy dog."]
)
def test_text_with_no_skills_returns_empty(text: str) -> None:
    assert extract_skills(text) == []


def test_a_skill_absent_from_the_document_is_not_detected() -> None:
    found = extract_skill_slugs("I have written spreadsheets in Excel for years.")
    assert "excel" in found
    for absent in ("pytorch", "kubernetes", "terraform", "hugging-face"):
        assert absent not in found


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_two_runs_produce_identical_output() -> None:
    first = extract_skills(SYNTHETIC_CV)
    second = extract_skills(SYNTHETIC_CV)
    assert first == second


def test_ordering_is_stable_across_runs() -> None:
    assert extract_skill_slugs(SYNTHETIC_CV) == extract_skill_slugs(SYNTHETIC_CV)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------
def test_bullets_and_separators_are_stripped() -> None:
    found = extract_skill_slugs("• Python\n- SQL\n* Docker\n1. AWS")
    assert set(found) == {"python", "sql", "docker", "aws"}


def test_repeated_and_mixed_case_mentions_are_collapsed() -> None:
    found = extract_skill_slugs("PYTHON python PyThOn")
    assert found == ["python"]


def test_very_long_text_is_handled() -> None:
    text = ("Experience with Python, SQL and Docker. " * 200)
    found = extract_skill_slugs(text)
    assert set(found) >= {"python", "sql", "docker"}
