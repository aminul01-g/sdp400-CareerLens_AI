"""T100/T101 — skill-gap analysis: set difference, ordering, and tiering."""

from __future__ import annotations

import pytest

from app.ml.gap_analysis import CRITICAL_THRESHOLD, IMPORTANT_THRESHOLD, analyse, tier_of
from app.ml.types import RoleSpec

REQUIRED = {
    1: 1.00,  # critical
    2: 0.90,  # critical
    3: 0.80,  # critical (boundary)
    4: 0.50,  # important (boundary)
    5: 0.30,  # desirable
    6: 0.75,
}
ROLE = RoleSpec(
    job_role_id=1, title="ML Engineer", slug="ml-engineer", family="ML Engineer",
    description="Build models.", required_skills=REQUIRED,
)
NAMES = {i: (f"Skill {i}", "Test") for i in REQUIRED}


def test_matched_and_missing_partition_the_required_set() -> None:
    report = analyse({1: 5, 2: 4, 5: 2}, ROLE, skill_names=NAMES)
    matched = {m.skill_id for m in report.matched}
    missing = {m.skill_id for m in report.missing}
    assert matched == {1, 2, 5}
    assert missing == {3, 4, 6}
    assert matched | missing == set(REQUIRED)
    assert not matched & missing


def test_missing_is_sorted_by_descending_weight() -> None:
    report = analyse({1: 5}, ROLE, skill_names=NAMES)
    weights = [m.weight for m in report.missing]
    assert weights == sorted(weights, reverse=True)
    assert weights == [0.90, 0.80, 0.75, 0.50, 0.30]


def test_equal_weights_break_ties_by_skill_id() -> None:
    role = RoleSpec(1, "R", "r", "F", "d", {9: 0.5, 3: 0.5, 7: 0.5})
    report = analyse({}, role)
    assert [m.skill_id for m in report.missing] == [3, 7, 9]


def test_tier_boundaries_are_exact() -> None:
    assert tier_of(1.0) == "critical"
    assert tier_of(0.8) == "critical"
    assert tier_of(0.79) == "important"
    assert tier_of(0.5) == "important"
    assert tier_of(0.49) == "desirable"
    assert tier_of(0.01) == "desirable"


def test_tier_thresholds_match_the_documented_constants() -> None:
    assert CRITICAL_THRESHOLD == 0.8
    assert IMPORTANT_THRESHOLD == 0.5
    assert tier_of(CRITICAL_THRESHOLD) == "critical"
    assert tier_of(IMPORTANT_THRESHOLD) == "important"


def test_tier_on_a_stored_report() -> None:
    report = analyse({1: 5}, ROLE, skill_names=NAMES)
    by_id = {m.skill_id: m for m in report.missing}
    assert by_id[2].tier == "critical"  # 0.90
    assert by_id[3].tier == "critical"  # 0.80, boundary
    assert by_id[4].tier == "important"  # 0.50, boundary
    assert by_id[5].tier == "desirable"  # 0.30
    assert by_id[6].tier == "important"  # 0.75


def test_coverage_agrees_with_the_matcher() -> None:
    from app.ml.matcher import weighted_skill_coverage

    user = {1: 5, 2: 4, 5: 2}
    report = analyse(user, ROLE)
    assert report.coverage == pytest.approx(weighted_skill_coverage(user, REQUIRED))


def test_contribution_is_weight_times_proficiency_factor() -> None:
    report = analyse({1: 4}, ROLE, skill_names=NAMES)
    matched = next(m for m in report.matched if m.skill_id == 1)
    assert matched.proficiency == 4
    assert matched.contribution == pytest.approx(1.0 * 0.75)


def test_empty_user_has_everything_missing() -> None:
    report = analyse({}, ROLE, skill_names=NAMES)
    assert report.matched == ()
    assert len(report.missing) == len(REQUIRED)
    assert report.coverage == 0.0
    assert report.required_count == len(REQUIRED)


def test_full_cover_has_nothing_missing() -> None:
    report = analyse({i: 5 for i in REQUIRED}, ROLE, skill_names=NAMES)
    assert report.missing == ()
    assert len(report.matched) == len(REQUIRED)
    assert report.coverage == 1.0


def test_role_with_no_requirements() -> None:
    role = RoleSpec(1, "Empty", "empty", "F", "d", {})
    report = analyse({1: 5}, role)
    assert report.matched == () and report.missing == ()
    assert report.coverage == 0.0
    assert report.required_count == 0


def test_names_are_passed_through() -> None:
    names = {1: ("Python", "Programming & Core")}
    role = RoleSpec(1, "R", "r", "F", "d", {1: 1.0, 2: 0.5})
    report = analyse({1: 5}, role, skill_names=names)
    assert next(m for m in report.matched if m.skill_id == 1).name == "Python"
    # An unmapped id gets a readable placeholder rather than a crash.
    assert next(m for m in report.missing if m.skill_id == 2).name == "Skill 2"


def test_report_is_deterministic() -> None:
    a = analyse({1: 5}, ROLE, skill_names=NAMES)
    b = analyse({1: 5}, ROLE, skill_names=NAMES)
    assert a == b
