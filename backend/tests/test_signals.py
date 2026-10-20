"""The context signals: recency, depth and level fit.

These are the tests for the change that closed the "skills are the only real
signal" limitation. Three properties matter more than anything else here, and
each of them is a property the *product* needs, not just the maths:

1. **Absence is neutral.** A user who has filled in nothing new must score
   exactly what they scored before these signals existed. If that ever stops
   being true, every existing user's shortlist changes under them for no
   reason, which is the failure mode this file exists to prevent.
2. **The discount is bounded.** A stale and shallow skill is discounted, not
   erased.
3. **A junior and a principal are distinguishable.** That was the sentence in
   the limitations document; if the engine still cannot tell them apart, the
   limitation is still there and this file should fail.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.ml.matcher import weighted_skill_coverage_from_factors
from app.ml.ranker import rank
from app.ml.signals import (
    DEPTH_FLOOR,
    LEVEL_BANDS,
    LEVEL_FIT_BY_DISTANCE,
    LEVEL_FIT_FAR,
    RECENCY_FLOOR,
    SIGNAL_FLOOR,
    band_from_years,
    depth_factor,
    level_fit,
    normalise_band,
    recency_factor,
    signal_factor,
    user_level_band,
)
from app.ml.types import ProfileSnapshot, RoleSpec, UserSkillFact

TODAY = date(2026, 10, 19)

ROLE = RoleSpec(
    job_role_id=1,
    title="Machine Learning Engineer",
    slug="machine-learning-engineer",
    family="ML Engineer",
    description="Train and deploy machine learning models with Python.",
    required_skills={1: 1.0, 2: 0.8},
)
NAMES = {1: ("Python", "Programming & Core"), 2: ("SQL", "Data Engineering")}


def _snapshot(**overrides) -> ProfileSnapshot:
    base = {
        "user_id": 1,
        "skills": (
            UserSkillFact(1, 5, "Python", "python"),
            UserSkillFact(2, 4, "SQL", "sql"),
        ),
    }
    base.update(overrides)
    return ProfileSnapshot(**base)


# --------------------------------------------------------------------------- #
# level bands
# --------------------------------------------------------------------------- #


def test_the_band_scale_is_ordered_from_least_to_most_experienced() -> None:
    assert LEVEL_BANDS == ("Entry", "Junior", "Mid", "Senior", "Lead", "Principal")


def test_a_band_is_matched_case_insensitively() -> None:
    assert normalise_band("senior") == "Senior"
    assert normalise_band("  SENIOR  ") == "Senior"
    assert normalise_band("Principal") == "Principal"


def test_an_unknown_level_is_treated_as_not_declared() -> None:
    """A level the engine cannot compare against a role's must not be guessed at."""
    assert normalise_band("Wizard") is None
    assert normalise_band("") is None
    assert normalise_band(None) is None


def test_the_api_schema_and_the_engine_agree_on_the_band_names() -> None:
    """Two lists of band names would drift. One list, imported by both."""
    from app.schemas.profile import SENIORITY_BANDS

    assert SENIORITY_BANDS == LEVEL_BANDS


def test_years_map_onto_the_documented_bands() -> None:
    assert band_from_years(0) == "Entry"
    assert band_from_years(1) == "Junior"
    assert band_from_years(2) == "Mid"
    assert band_from_years(4) == "Mid"
    assert band_from_years(5) == "Senior"
    assert band_from_years(8) == "Senior"
    assert band_from_years(9) == "Lead"
    assert band_from_years(12) == "Lead"
    assert band_from_years(13) == "Principal"
    assert band_from_years(40) == "Principal"


def test_unknown_years_produce_no_band() -> None:
    assert band_from_years(None) is None
    assert band_from_years(-1) is None


def test_a_declared_level_beats_the_years_estimate() -> None:
    assert user_level_band("Senior", years_experience=1) == "Senior"
    assert user_level_band(None, years_experience=7) == "Senior"
    assert user_level_band("nonsense", years_experience=7) == "Senior"


# --------------------------------------------------------------------------- #
# level fit
# --------------------------------------------------------------------------- #


def test_level_fit_is_one_when_either_side_is_unknown() -> None:
    """Absence is neutral. Not knowing is not a mismatch."""
    assert level_fit(None, "Senior") == 1.0
    assert level_fit("Mid", None) == 1.0
    assert level_fit(None, None) == 1.0


def test_an_exact_level_match_scores_one() -> None:
    assert level_fit("Mid", "Mid") == 1.0


def test_level_fit_decays_with_band_distance() -> None:
    assert level_fit("Mid", "Senior") == pytest.approx(LEVEL_FIT_BY_DISTANCE[1])
    assert level_fit("Mid", "Lead") == pytest.approx(LEVEL_FIT_BY_DISTANCE[2])
    assert level_fit("Entry", "Principal") == pytest.approx(LEVEL_FIT_FAR)
    # And it is symmetric: being over-qualified costs the same as under.
    assert level_fit("Senior", "Mid") == level_fit("Mid", "Senior")


def test_level_fit_never_exceeds_one() -> None:
    for user in LEVEL_BANDS:
        for role in LEVEL_BANDS:
            assert 0.0 < level_fit(user, role) <= 1.0


# --------------------------------------------------------------------------- #
# recency
# --------------------------------------------------------------------------- #


def test_an_unstated_recency_is_neutral() -> None:
    assert recency_factor(None, TODAY) == 1.0


def test_a_skill_used_today_scores_full() -> None:
    assert recency_factor(TODAY, TODAY) == 1.0


def test_a_date_in_the_future_does_not_penalise() -> None:
    """A data-entry slip is not evidence of anything."""
    assert recency_factor(date(2027, 1, 1), TODAY) == 1.0


def test_recency_decays_and_is_floored() -> None:
    recent = recency_factor(date(2026, 10, 1), TODAY)
    older = recency_factor(date(2024, 10, 1), TODAY)
    ancient = recency_factor(date(2004, 1, 1), TODAY)

    assert 1.0 > recent > older
    # The decay is asymptotic, so the floor is approached rather than reached.
    # What matters is that it is never crossed.
    assert ancient >= RECENCY_FLOOR
    assert ancient == pytest.approx(RECENCY_FLOOR, abs=0.01)
    assert pytest.approx(0.70) == RECENCY_FLOOR


def test_a_three_year_old_skill_loses_less_than_a_third() -> None:
    value = recency_factor(date(2023, 10, 19), TODAY)
    assert value == pytest.approx(0.85, abs=0.02)


# --------------------------------------------------------------------------- #
# depth
# --------------------------------------------------------------------------- #


def test_an_unstated_depth_is_neutral() -> None:
    assert depth_factor(None) == 1.0


def test_depth_saturates_at_five_years() -> None:
    assert depth_factor(5.0) == 1.0
    assert depth_factor(20.0) == 1.0


def test_a_brand_new_skill_keeps_its_floor() -> None:
    assert depth_factor(0.0) == pytest.approx(DEPTH_FLOOR)
    assert depth_factor(2.5) == pytest.approx(0.90)
    assert pytest.approx(0.80) == DEPTH_FLOOR


# --------------------------------------------------------------------------- #
# combined
# --------------------------------------------------------------------------- #


def test_the_combined_signal_never_falls_below_the_floor() -> None:
    """A stale and shallow skill is discounted, never erased."""
    value = signal_factor(0.0, date(2000, 1, 1), TODAY)
    assert value == pytest.approx(SIGNAL_FLOOR)
    assert pytest.approx(0.70) == SIGNAL_FLOOR


def test_no_reference_date_leaves_recency_neutral() -> None:
    assert signal_factor(None, date(2000, 1, 1), None) == 1.0
    assert signal_factor(None, None, None) == 1.0


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


def test_a_profile_with_no_new_data_scores_exactly_as_it_did_before() -> None:
    """The compatibility promise: absence is neutral.

    This is the assertion that keeps the change from being a regression for
    every user who has never heard of the "years used" field.
    """
    snapshot = _snapshot()
    scored = rank(snapshot, [ROLE], skill_names=NAMES, today=TODAY)

    expected = weighted_skill_coverage_from_factors(
        {1: 1.0, 2: 0.75}, ROLE.required_skills
    )
    assert scored[0].skill_coverage == pytest.approx(expected)
    assert scored[0].declared_coverage == pytest.approx(expected)
    assert scored[0].signal_coverage == pytest.approx(expected)
    assert scored[0].level_fit == 1.0


def test_a_stale_skill_scores_lower_than_a_fresh_one() -> None:
    fresh = _snapshot(
        skills=(
            UserSkillFact(1, 5, "Python", "python", years_used=6.0, last_used_at=TODAY),
            UserSkillFact(2, 4, "SQL", "sql", years_used=5.0, last_used_at=TODAY),
        )
    )
    stale = _snapshot(
        skills=(
            UserSkillFact(1, 5, "Python", "python", years_used=0.0, last_used_at=date(2005, 1, 1)),
            UserSkillFact(2, 4, "SQL", "sql", years_used=0.0, last_used_at=date(2005, 1, 1)),
        )
    )
    fresh_score = rank(fresh, [ROLE], skill_names=NAMES, today=TODAY)[0]
    stale_score = rank(stale, [ROLE], skill_names=NAMES, today=TODAY)[0]

    assert fresh_score.declared_coverage == pytest.approx(stale_score.declared_coverage)
    assert stale_score.signal_coverage < fresh_score.signal_coverage
    assert stale_score.skill_coverage < fresh_score.skill_coverage
    # Bounded: the discount never erases the skill.
    assert stale_score.skill_coverage >= stale_score.declared_coverage * SIGNAL_FLOOR - 1e-9


def test_a_junior_and_a_principal_with_identical_skills_are_different() -> None:
    """The sentence the limitations document used to make.

    "Two profiles with identical skills and twenty years' difference in
    experience are indistinguishable" — they are not any more.
    """
    junior = _snapshot(years_experience=1)
    principal = _snapshot(years_experience=20)

    junior_score = rank(
        junior, [ROLE], skill_names=NAMES, role_seniorities={1: "Mid"}, today=TODAY
    )[0]
    principal_score = rank(
        principal, [ROLE], skill_names=NAMES, role_seniorities={1: "Mid"}, today=TODAY
    )[0]

    assert junior_score.declared_coverage == pytest.approx(principal_score.declared_coverage)
    assert junior_score.level_fit != principal_score.level_fit
    assert junior_score.skill_coverage != principal_score.skill_coverage


def test_a_role_with_no_seniority_label_is_neutral() -> None:
    """A role the knowledge base has not levelled cannot be levelled against."""
    snapshot = _snapshot(years_experience=1)
    scored = rank(snapshot, [ROLE], skill_names=NAMES, today=TODAY)[0]
    assert scored.level_fit == 1.0


def test_level_fit_uses_the_roles_own_seniority() -> None:
    snapshot = _snapshot(seniority="Junior")
    scored = rank(snapshot, [ROLE], skill_names=NAMES, role_seniorities={1: "Principal"}, today=TODAY)
    assert scored[0].level_fit == pytest.approx(LEVEL_FIT_FAR)


def test_the_published_formula_still_holds() -> None:
    """`0.6 * coverage + 0.4 * cosine` must remain literally true."""
    snapshot = _snapshot(years_experience=6, industry="fintech")
    scored = rank(snapshot, [ROLE], skill_names=NAMES, today=TODAY)[0]
    assert scored.compatibility == pytest.approx(
        0.6 * scored.skill_coverage + 0.4 * scored.tfidf_similarity
    )


def test_the_industry_reaches_the_profile_text() -> None:
    from app.ml.text_profile import build_profile_text

    text = build_profile_text(_snapshot(industry="fintech"))
    assert "fintech" in text


def test_the_location_does_not_reach_the_profile_text() -> None:
    """A city name is not lexical signal about a role.

    Putting it in the document would dilute the vector for every user who
    filled the field in, quietly lowering their text similarity.
    """
    from app.ml.text_profile import build_profile_text

    text = build_profile_text(_snapshot(location="Reykjavik"))
    assert "Reykjavik" not in text
