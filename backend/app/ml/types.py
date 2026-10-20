"""The ML layer's public contract: pure dataclasses.

**This module must not import SQLAlchemy or FastAPI, and neither may anything else
under ``app/ml/``.** That single rule is what makes the engine unit-testable with
no database, makes ``python -m app.ml.evaluation`` runnable with no HTTP server,
makes determinism assertable, and means the engine could be replaced without
touching a route. It is verified mechanically by ``tests/test_ml_isolation.py``.

The engine takes dataclasses and returns dataclasses. The single module that
speaks both dialects is ``app/services/recommendation_service.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Proficiency 1..5 mapped onto [0, 1].
#
# (p - 1) / 4 rather than p / 5 is a deliberate choice, and it is the right one
# for this domain: it makes a proficiency-1 skill contribute *nothing*. Someone
# who has "heard of" a technology should not receive partial credit against a role
# that requires working command of it. It also makes a full superset at
# proficiency 5 score exactly 1.0, so a compatibility percentage stays
# interpretable on a 0-100 scale.
PROFICIENCY_FACTOR: dict[int, float] = {1: 0.0, 2: 0.25, 3: 0.5, 4: 0.75, 5: 1.0}

MIN_PROFICIENCY = 1
MAX_PROFICIENCY = 5


def proficiency_factor(proficiency: int) -> float:
    """Map a 1-5 proficiency onto [0, 1]. Clamped, so bad data cannot escape [0, 1]."""
    if proficiency < MIN_PROFICIENCY:
        return PROFICIENCY_FACTOR[MIN_PROFICIENCY]
    if proficiency > MAX_PROFICIENCY:
        return PROFICIENCY_FACTOR[MAX_PROFICIENCY]
    return PROFICIENCY_FACTOR[proficiency]


@dataclass(frozen=True, slots=True)
class SkillRef:
    """A taxonomy entry as the engine needs to see it."""

    skill_id: int
    name: str
    slug: str
    category: str


@dataclass(frozen=True, slots=True)
class UserSkillFact:
    """One confirmed skill the user holds.

    ``years_used`` and ``last_used_at`` are the depth and recency signals. Both
    are optional, and both are *neutral* when absent: a skill with no
    ``last_used_at`` is treated as recently used, because not knowing is not
    evidence of staleness.
    """

    skill_id: int
    proficiency: int
    name: str = ""
    slug: str = ""
    years_used: float | None = None
    last_used_at: date | None = None

    @property
    def factor(self) -> float:
        return proficiency_factor(self.proficiency)


@dataclass(frozen=True, slots=True)
class ProjectFact:
    title: str
    description: str
    tech_stack: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EducationFact:
    institution: str
    degree: str
    field_of_study: str = ""


@dataclass(frozen=True, slots=True)
class CertificationFact:
    name: str
    issuer: str = ""


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    """Everything the engine knows about one user at one moment in time.

    ``years_experience``, ``seniority``, ``industry`` and ``location`` are the
    context signals. The first two feed the level fit, ``industry`` joins the
    text the TF-IDF similarity is computed over, and ``location`` is carried
    for display only — a city name carries no lexical signal about a role, and
    putting it in the text would dilute the vector for every user who filled
    the field in.
    """

    user_id: int
    headline: str = ""
    career_goal: str = ""
    bio: str = ""
    preferred_role_family: str = ""
    skills: tuple[UserSkillFact, ...] = ()
    projects: tuple[ProjectFact, ...] = ()
    education: tuple[EducationFact, ...] = ()
    certifications: tuple[CertificationFact, ...] = ()
    years_experience: int | None = None
    seniority: str = ""
    industry: str = ""
    location: str = ""
    # Built by ml.text_profile.build_profile_text; empty means "not yet built".
    profile_text: str = field(default="", compare=False)

    @property
    def skill_proficiency(self) -> dict[int, int]:
        """skill_id -> proficiency, for the coverage function."""
        return {skill.skill_id: skill.proficiency for skill in self.skills}


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """One job role and its weighted requirements."""

    job_role_id: int
    title: str
    slug: str
    family: str
    description: str
    required_skills: dict[int, float]  # skill_id -> importance weight in (0, 1]

    @property
    def total_weight(self) -> float:
        return sum(self.required_skills.values())


@dataclass(frozen=True, slots=True)
class MatchedSkill:
    skill_id: int
    name: str
    weight: float
    proficiency: int
    contribution: float
    category: str = ""


@dataclass(frozen=True, slots=True)
class MissingSkill:
    skill_id: int
    name: str
    weight: float
    tier: str
    category: str = ""


@dataclass(frozen=True, slots=True)
class RoleScore:
    """One role's fully explained score.

    The arithmetic between these numbers is published so a reader can
    reconstruct any percentage by hand:

    .. code-block:: text

        compatibility = w_cov * skill_coverage + w_txt * tfidf_similarity

    * ``declared_coverage`` is the coverage using declared proficiency alone —
      what the engine scored before recency and depth were modelled.
    * ``signal_coverage`` is that coverage after the recency and depth
      adjustments, floored so a stale skill is discounted but never erased.
    * ``level_fit`` is the multiplier for the distance between the user's level
      and the role's level. It is ``1.0`` when no level has been declared.
    * ``skill_coverage`` is what actually enters the formula:
      ``signal_coverage * level_fit``.
    * ``role_prior`` is the community signal for this role, in ``[-1, 1]``, and
      ``0.0`` when there is not enough evidence to use one. It is applied as a
      bounded multiplier after the two components are combined.
    """

    job_role_id: int
    title: str
    slug: str
    family: str
    seniority: str
    compatibility: float
    skill_coverage: float
    tfidf_similarity: float
    matched: tuple[MatchedSkill, ...]
    missing: tuple[MissingSkill, ...]
    rank: int = 0
    declared_coverage: float = 0.0
    signal_coverage: float = 0.0
    level_fit: float = 1.0
    role_prior: float = 0.0
    feedback_samples: int = 0

    @property
    def compatibility_pct(self) -> float:
        return round(self.compatibility * 100.0, 1)


@dataclass(frozen=True, slots=True)
class GapReport:
    """``required - present`` for one role, ordered by descending weight."""

    job_role_id: int
    title: str
    family: str
    coverage: float
    matched: tuple[MatchedSkill, ...]
    missing: tuple[MissingSkill, ...]
    declared_coverage: float = 0.0
    signal_coverage: float = 0.0
    level_fit: float = 1.0

    @property
    def required_count(self) -> int:
        return len(self.matched) + len(self.missing)


@dataclass(frozen=True, slots=True)
class DetectedSkill:
    """A skill found in raw CV text, before any database round trip.

    ``section`` is the kind of section the match was found in — "skills",
    "experience", "projects" and so on. ``is_declared`` is the thing that
    matters: a skill under **Skills** is a claim about the person, and the
    same word inside a project description is a mention that may describe
    somebody else's work.
    """

    skill_id: int
    canonical_name: str
    slug: str
    category: str
    surface_form: str
    occurrence_count: int
    match_start: int | None = None
    match_end: int | None = None
    section: str = ""
    is_declared: bool = False
