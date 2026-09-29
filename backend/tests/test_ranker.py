"""T102 — the ranker: combination, total order, limit, and explainability."""

from __future__ import annotations

import pytest

from app.ml.ranker import rank
from app.ml.types import (
    EducationFact,
    ProfileSnapshot,
    ProjectFact,
    RoleSpec,
    UserSkillFact,
)

NAMES = {
    1: ("Python", "Programming & Core"),
    2: ("SQL", "Data Engineering"),
    3: ("Scikit-learn", "ML Frameworks"),
    4: ("PyTorch", "Deep Learning"),
    5: ("Docker", "MLOps & Cloud"),
    6: ("AWS", "MLOps & Cloud"),
    7: ("Java", "Programming & Core"),
    8: ("Kubernetes", "MLOps & Cloud"),
}

ROLES = [
    RoleSpec(1, "Machine Learning Engineer", "ml-engineer", "ML Engineer",
             "Train and deploy machine learning models with Python, Scikit-learn, PyTorch and SQL.",
             {1: 1.0, 3: 0.9, 4: 0.85, 2: 0.7, 5: 0.5}),
    RoleSpec(2, "Data Analyst", "data-analyst", "Data Science",
             "Answer business questions with SQL and spreadsheets and clear dashboards.",
             {2: 1.0, 7: 0.1}),
    RoleSpec(3, "MLOps Engineer", "mlops-engineer", "MLOps",
             "Deploy models with Docker and Kubernetes on AWS with CI/CD pipelines.",
             {5: 1.0, 8: 0.9, 6: 0.8, 1: 0.4}),
    RoleSpec(4, "Java Developer", "java-developer", "Software Engineering",
             "Build large Java enterprise systems with relational databases.",
             {7: 1.0, 2: 0.6}),
    RoleSpec(5, "Quantum Chemist", "quantum-chemist", "Research",
             "Research molecular simulation using entirely unrelated quantum methods.",
             {99: 1.0, 98: 0.9}),
]


@pytest.fixture
def snapshot() -> ProfileSnapshot:
    return ProfileSnapshot(
        user_id=1,
        headline="Machine Learning Engineer",
        skills=(
            UserSkillFact(1, 5, "Python", "python"),
            UserSkillFact(2, 4, "SQL", "sql"),
            UserSkillFact(3, 4, "Scikit-learn", "scikit-learn"),
            UserSkillFact(4, 4, "PyTorch", "pytorch"),
            UserSkillFact(5, 3, "Docker", "docker"),
        ),
        projects=(ProjectFact("Classifier", "Built a CNN with PyTorch", ("python", "pytorch")),),
        education=(EducationFact("Example University", "BSc", "Computer Science"),),
    )


def test_ranks_are_dense_and_ordered(snapshot: ProfileSnapshot) -> None:
    scored = rank(snapshot, ROLES, skill_names=NAMES)
    assert [s.rank for s in scored] == [1, 2, 3, 4, 5]
    scores = [s.compatibility for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_top_n_limits_without_reordering(snapshot: ProfileSnapshot) -> None:
    full = rank(snapshot, ROLES, skill_names=NAMES)
    top3 = rank(snapshot, ROLES, skill_names=NAMES, top_n=3)
    assert len(top3) == 3
    assert [(s.job_role_id, s.compatibility) for s in top3] == [
        (s.job_role_id, s.compatibility) for s in full[:3]
    ]


def test_no_roles_returns_empty(snapshot: ProfileSnapshot) -> None:
    assert rank(snapshot, []) == []


def test_zero_match_role_is_present_and_ranked_last(snapshot: ProfileSnapshot) -> None:
    """A role with no matching skills scores 0 and is kept, not dropped."""
    scored = rank(snapshot, ROLES, skill_names=NAMES)
    zero = next(s for s in scored if s.job_role_id == 5)
    assert zero.skill_coverage == 0.0
    assert zero.compatibility == 0.0
    assert zero.rank == len(scored)
    assert len(scored) == len(ROLES), "a poor match was silently dropped"


def test_zero_skill_user_scores_everything_zero(snapshot: ProfileSnapshot) -> None:
    from dataclasses import replace

    empty = replace(snapshot, skills=(), projects=(), education=(), headline="")
    scored = rank(empty, ROLES, skill_names=NAMES)
    assert len(scored) == len(ROLES)
    assert all(s.skill_coverage == 0.0 for s in scored)
    assert all(s.compatibility == pytest.approx(0.4 * s.tfidf_similarity) for s in scored)


def test_combination_formula_is_applied(snapshot: ProfileSnapshot) -> None:
    scored = rank(snapshot, ROLES, skill_names=NAMES, coverage_weight=0.6, tfidf_weight=0.4)
    for s in scored:
        assert s.compatibility == pytest.approx(0.6 * s.skill_coverage + 0.4 * s.tfidf_similarity)


def test_ties_break_deterministically_by_role_id(snapshot: ProfileSnapshot) -> None:
    """Two roles with identical requirements and descriptions must order stably."""
    duplicate_a = RoleSpec(50, "Twin A", "twin-a", "F", "Identical description text here.", {1: 1.0})
    duplicate_b = RoleSpec(20, "Twin B", "twin-b", "F", "Identical description text here.", {1: 1.0})
    scored = rank(snapshot, [duplicate_a, duplicate_b], skill_names=NAMES)
    assert [s.job_role_id for s in scored] == [20, 50], "lower id must rank first on a tie"
    # And the order must not depend on the input order.
    reversed_input = rank(snapshot, [duplicate_b, duplicate_a], skill_names=NAMES)
    assert [s.job_role_id for s in reversed_input] == [20, 50]


def test_every_score_is_explainable(snapshot: ProfileSnapshot) -> None:
    """matched and missing must partition the required set, and be disjoint."""
    by_id = {r.job_role_id: r for r in ROLES}
    for s in rank(snapshot, ROLES, skill_names=NAMES):
        required = set(by_id[s.job_role_id].required_skills)
        matched = {m.skill_id for m in s.matched}
        missing = {x.skill_id for x in s.missing}
        assert matched | missing == required, f"{s.title}: union mismatch"
        assert not matched & missing, f"{s.title}: matched and missing overlap"
        for m in s.matched:
            assert m.proficiency is not None and m.name
        for x in s.missing:
            assert x.tier in {"critical", "important", "desirable"}


def test_matched_and_missing_are_each_sorted_by_descending_weight(
    snapshot: ProfileSnapshot,
) -> None:
    for s in rank(snapshot, ROLES, skill_names=NAMES):
        for items, label in ((s.matched, "matched"), (s.missing, "missing")):
            weights = [i.weight for i in items]
            assert weights == sorted(weights, reverse=True), f"{s.title} {label} unsorted"


def test_compatibility_pct_is_a_percentage(snapshot: ProfileSnapshot) -> None:
    for s in rank(snapshot, ROLES, skill_names=NAMES):
        assert 0.0 <= s.compatibility_pct <= 100.0
        assert s.compatibility_pct == round(s.compatibility * 100, 1)


def test_higher_weight_requirement_counts_for_more(snapshot: ProfileSnapshot) -> None:
    """A role needing only Docker should score higher than one diluting it with a 0.05."""
    focused = RoleSpec(1, "Docker Specialist", "ds", "F", "Docker everywhere.", {5: 1.0})
    diluted = RoleSpec(2, "Docker Generalist", "dg", "F", "Docker everywhere.", {5: 0.2, 7: 1.0})
    scored = rank(snapshot, [focused, diluted], skill_names=NAMES)
    assert next(s for s in scored if s.job_role_id == 1).skill_coverage > next(
        s for s in scored if s.job_role_id == 2
    ).skill_coverage


def test_proficiency_above_zero_is_necessary_for_credit(snapshot: ProfileSnapshot) -> None:
    from dataclasses import replace

    level_one = replace(snapshot, skills=tuple(
        UserSkillFact(s.skill_id, 1, s.name, s.slug) for s in snapshot.skills
    ))
    scored = rank(level_one, [ROLES[0]], skill_names=NAMES)
    assert scored[0].skill_coverage == 0.0


def test_seniority_is_carried_through(snapshot: ProfileSnapshot) -> None:
    seniors = rank(snapshot, ROLES, skill_names=NAMES, role_seniorities={1: "Senior"})
    assert next(s for s in seniors if s.job_role_id == 1).seniority == "Senior"


def test_no_skill_names_supplied_still_ranks(snapshot: ProfileSnapshot) -> None:
    scored = rank(snapshot, ROLES)
    assert len(scored) == len(ROLES)
    for s in scored:
        for item in (*s.matched, *s.missing):
            assert item.name
