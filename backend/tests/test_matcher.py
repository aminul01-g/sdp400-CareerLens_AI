"""T097/T098 — the coverage and cosine maths.

Every property the plan's section 9.5.2 promises is asserted here, including the
two that are easy to get wrong: scale invariance, and monotonicity under both
adding a skill and raising a proficiency.
"""

from __future__ import annotations

import math
import random

import pytest

from app.ml.matcher import combined_score, tfidf_cosine, weighted_skill_coverage
from app.ml.types import PROFICIENCY_FACTOR, RoleSpec, proficiency_factor

# Hand-computed reference case, straight from the plan's section 9.5.5 weights.
REFERENCE_REQUIRED = {
    1: 1.00,  # Python
    2: 0.80,  # SQL
    3: 0.90,  # scikit-learn
    5: 0.85,  # PyTorch
    4: 0.60,  # LangChain
    6: 0.70,  # Docker
    7: 0.50,  # FastAPI
    8: 0.55,  # AWS
    9: 0.40,  # Git
}
# Σw = 6.30
# covered = 1.00(1.00) + 0.80(0.75) + 0.90(0.75) + 0.85(0.75) + 0.60(0.50) = 3.2125
# coverage = 3.2125 / 6.30 = 0.509920634...
REFERENCE_USER = {1: 5, 2: 4, 3: 4, 5: 4, 4: 3}


def test_proficiency_factor_table() -> None:
    assert PROFICIENCY_FACTOR == {1: 0.0, 2: 0.25, 3: 0.5, 4: 0.75, 5: 1.0}
    for proficiency, expected in PROFICIENCY_FACTOR.items():
        assert proficiency_factor(proficiency) == expected


def test_proficiency_factor_is_clamped() -> None:
    assert proficiency_factor(0) == 0.0
    assert proficiency_factor(-5) == 0.0
    assert proficiency_factor(6) == 1.0
    assert proficiency_factor(99) == 1.0


def test_proficiency_one_contributes_nothing() -> None:
    """(p-1)/4 means "has heard of it" earns no credit — a deliberate choice."""
    assert weighted_skill_coverage({1: 1}, {1: 1.0}) == 0.0


# ---------------------------------------------------------------------------
# Core properties
# ---------------------------------------------------------------------------
def test_hand_computed_reference_value() -> None:
    coverage = weighted_skill_coverage(REFERENCE_USER, REFERENCE_REQUIRED)
    assert coverage == pytest.approx(3.2125 / 6.30, abs=1e-12)
    assert coverage == pytest.approx(0.5099206349206349, abs=1e-12)


def test_superset_at_maximum_proficiency_is_exactly_one() -> None:
    user = {skill_id: 5 for skill_id in REFERENCE_REQUIRED}
    assert weighted_skill_coverage(user, REFERENCE_REQUIRED) == 1.0


def test_disjoint_is_exactly_zero() -> None:
    assert weighted_skill_coverage({999: 5}, REFERENCE_REQUIRED) == 0.0
    assert weighted_skill_coverage({}, REFERENCE_REQUIRED) == 0.0


def test_empty_requirements_is_zero() -> None:
    assert weighted_skill_coverage({1: 5}, {}) == 0.0
    assert weighted_skill_coverage({}, {}) == 0.0


def test_scale_invariance() -> None:
    """Halving every weight must not change the score: only relative importance matters."""
    full = weighted_skill_coverage(REFERENCE_USER, REFERENCE_REQUIRED)
    halved = {k: v / 2 for k, v in REFERENCE_REQUIRED.items()}
    assert weighted_skill_coverage(REFERENCE_USER, halved) == pytest.approx(full, abs=1e-12)

    equalised = {k: 1.0 for k in REFERENCE_REQUIRED}
    assert weighted_skill_coverage(REFERENCE_USER, equalised) == pytest.approx(
        sum(PROFICIENCY_FACTOR[p] for p in REFERENCE_USER.values()) / len(REFERENCE_REQUIRED)
    )


def test_bounds_over_200_random_inputs() -> None:
    rng = random.Random(20260930)  # fixed seed: the test must be reproducible
    for _ in range(200):
        size = rng.randint(1, 15)
        required = {i: round(rng.uniform(0.01, 1.0), 2) for i in range(1, size + 1)}
        user = {i: rng.randint(1, 5) for i in range(1, size + 1) if rng.random() < 0.6}
        coverage = weighted_skill_coverage(user, required)
        assert 0.0 <= coverage <= 1.0, f"{coverage} out of range for {user} / {required}"


def test_monotonic_adding_a_skill_never_lowers_the_score() -> None:
    rng = random.Random(7)
    for _ in range(100):
        required = {i: round(rng.uniform(0.05, 1.0), 2) for i in range(1, 8)}
        partial = {i: rng.randint(1, 5) for i in range(1, 8) if i < 6}
        before = weighted_skill_coverage(partial, required)
        extra = dict(partial)
        extra[6] = rng.randint(1, 5)
        after = weighted_skill_coverage(extra, required)
        assert after >= before - 1e-12


def test_monotonic_raising_a_proficiency_never_lowers_the_score() -> None:
    for skill_id in REFERENCE_REQUIRED:
        for start in range(1, 5):
            user = dict(REFERENCE_USER)
            if skill_id not in user:
                user[skill_id] = start
            else:
                user[skill_id] = start
            lower = weighted_skill_coverage(user, REFERENCE_REQUIRED)
            user[skill_id] = start + 1
            higher = weighted_skill_coverage(user, REFERENCE_REQUIRED)
            assert higher >= lower - 1e-12


def test_a_zero_weight_denominator_does_not_divide_by_zero() -> None:
    assert weighted_skill_coverage({1: 5}, {1: 0.0}) == 0.0


# ---------------------------------------------------------------------------
# TF-IDF cosine
# ---------------------------------------------------------------------------
def _role(role_id: int, description: str) -> RoleSpec:
    return RoleSpec(
        job_role_id=role_id, title=f"Role {role_id}", slug=f"role-{role_id}",
        family="Test", description=description, required_skills={1: 1.0},
    )


def test_identical_text_gives_similarity_one() -> None:
    description = "Design and deploy machine learning models with Python and Scikit-learn."
    role = _role(1, description)
    assert tfidf_cosine(description, [role])[0] == pytest.approx(1.0, abs=1e-9)


def test_similar_text_scores_higher_than_unrelated_text() -> None:
    relevant = _role(1, "Train machine learning models using Python, Scikit-learn and pandas.")
    unrelated = _role(2, "Manage a retail store, schedule staff and process payroll invoices.")
    sims = tfidf_cosine(
        "I build machine learning models in Python with Scikit-learn and pandas.",
        [relevant, unrelated],
    )
    assert sims[0] > sims[1]
    assert sims[1] < 0.1


def test_similarity_is_never_negative() -> None:
    """cosine_similarity can return -1e-17 from float noise; the display must not."""
    role = _role(1, "Completely unrelated content about office stationery and printers.")
    for value in tfidf_cosine("Machine learning with Python and neural networks.", [role]):
        assert 0.0 <= value <= 1.0


def test_empty_profile_text_yields_zero() -> None:
    role = _role(1, "Machine learning engineering.")
    assert tfidf_cosine("", [role]) == [0.0]
    assert tfidf_cosine("   ", [role]) == [0.0]


def test_no_roles_yields_empty_list() -> None:
    assert tfidf_cosine("some text", []) == []


def test_similarity_bounds_over_random_text() -> None:
    rng = random.Random(99)
    words = ["alpha", "beta", "gamma", "delta", "epsilon", "model", "data", "pipeline"]
    roles = [_role(i, " ".join(rng.choices(words, k=40))) for i in range(1, 21)]
    text = " ".join(rng.choices(words, k=60))
    for value in tfidf_cosine(text, roles):
        assert 0.0 <= value <= 1.0


def test_all_stopword_text_does_not_raise() -> None:
    role = _role(1, "Machine learning engineering role.")
    assert tfidf_cosine("the and of to a in", [role]) == [0.0]


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------
def test_combined_score_matches_the_formula() -> None:
    assert combined_score(0.6, 0.4, 0.6, 0.4) == pytest.approx(0.52)


def test_combined_score_is_bounded() -> None:
    assert combined_score(1.0, 1.0, 0.6, 0.4) == pytest.approx(1.0)
    assert combined_score(0.0, 0.0, 0.6, 0.4) == 0.0
    for _ in range(200):
        rng = random.Random(4)
        value = combined_score(rng.random(), rng.random(), 0.6, 0.4)
        assert 0.0 <= value <= 1.0


def test_combination_is_monotone_in_each_component() -> None:
    for coverage, cosine in ((0.2, 0.8), (0.5, 0.5), (0.9, 0.1)):
        assert combined_score(coverage + 0.05, cosine, 0.6, 0.4) >= combined_score(coverage, cosine, 0.6, 0.4)
        assert combined_score(coverage, cosine + 0.05, 0.6, 0.4) >= combined_score(coverage, cosine, 0.6, 0.4)


def test_math_is_finite_for_degenerate_inputs() -> None:
    assert not math.isnan(combined_score(0.0, 0.0, 0.0, 0.0))
    assert combined_score(0.0, 0.0, 0.0, 0.0) == 0.0
