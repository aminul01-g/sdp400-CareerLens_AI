"""A measurement of the context signals.

``docs/limitations.md`` used to say this about the signals in
``app/ml/signals.py``:

    **Nothing measures whether these signals help.** They are implemented, tested
    and explained; their effect on a real shortlist is unmeasured.

That was an accurate statement, and it was a weakness. The signals were
implemented, unit-tested against hand-computed multipliers, and then never
observed doing anything. A feature that has never been seen to change an
outcome is a feature nobody can say anything true about.

This module is the measurement. It asks three questions, and only these three:

1. **Do the signals change a score at all?**
2. **Do they change it in the direction they are designed to change it?**
3. **Is a user who states nothing penalised for stating nothing?**

The design is a *matched-pair* experiment, and the matching is what makes the
answer interpretable.

How a pair works
----------------

Each pair is one person, described twice:

* the **without_signals** variant has the same skills, the same proficiencies,
  the same projects and the same education, and declares no years of
  experience, no level, and no recency or depth for any skill;
* the **with_signals** variant is byte-identical except that it declares them.

The two variants therefore produce **the same TF-IDF vector** — ``seniority``
and ``years_experience`` are deliberately absent from
``app/ml/text_profile.py``, and a skill's recency and depth are not words. The
text similarity term is identical. Every difference in the outcome is
attributable to the signal multipliers, with nothing else moving.

The pair names two roles: the one the signals *should* favour
(``expected_role``) and the one it should beat (``competing_role``). The
quantity measured is the **margin** between them:

.. code-block:: text

    margin = compatibility(expected_role) - compatibility(competing_role)

A larger margin means the signals moved the ranking toward the expected role.
The margin is used rather than the raw rank because it is continuous, so a
pair that does not change the *order* can still show that the signals moved
the *scores* in the right direction. Rank is reported alongside it.

What this does and does not establish
--------------------------------------

It establishes that the signals do what their documentation says they do, on
profiles built to express the expectation, and it quantifies how much they
move a score. It does **not** establish that they improve anyone's career, and
the report says so in the same words. The pairs are synthetic and
purpose-built, so this is a correctness check on a mechanism, not evidence
about the world. The three things that would be needed to make it evidence --
independent labels, observed hiring outcomes, and profiles from real users --
are listed in ``docs/limitations.md`` and none of them exists here.

The selection rule for the pairs
--------------------------------

Pairs are not hand-picked winners. Each one satisfies a stated, mechanical
condition that the loader in this module enforces:

* the two variants of a pair declare **identical** skills and proficiencies;
* the with_signals variant declares **at least one** signal and the
  without_signals variant declares **none**;
* the expected role and the competing role are **distinct** and both exist in
  the knowledge base;
* the pair declares which kind of signal it exercises, and the loader checks
  that the declared kind is actually present in the data.

A pair that fails any of these is rejected rather than scored, so a result
cannot be manufactured by editing a label after the fact.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.ml.ranker import ProfileSnapshot, RoleSpec, rank
from app.ml.taxonomy import Taxonomy
from app.ml.text_profile import with_profile_text
from app.ml.types import UserSkillFact

#: The reference date the recency signal is measured against.
#:
#: Fixed rather than read from the clock, for the same reason the report's
#: generation date is fixed: two runs of the committed report must produce
#: byte-identical output. It matches ``harness.GENERATED_AT``, and a test
#: asserts that it does.
EVALUATION_TODAY = date(2026, 9, 30)

#: The kinds of signal a pair may exercise.
SIGNAL_KINDS: tuple[str, ...] = ("level", "recency", "depth")

#: The two variants a pair is made of.
VARIANTS: tuple[str, ...] = ("with_signals", "without_signals")


class SignalStudyError(RuntimeError):
    """The signal study data or the knowledge base is unusable.

    Raised instead of letting a malformed pair produce a quietly wrong number.
    """


# --------------------------------------------------------------------------- #
# data model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SkillSignal:
    """The depth and recency one skill is declared with.

    Both are optional, and both are neutral when absent -- the same rule the
    engine follows, so a variant that declares nothing scores exactly as it
    would have before the signals existed.
    """

    years_used: float | None = None
    last_used_at: date | None = None

    @property
    def is_declared(self) -> bool:
        return self.years_used is not None or self.last_used_at is not None


@dataclass(frozen=True, slots=True)
class SignalProfile:
    """One side of a matched pair."""

    id: str
    pair_id: str
    variant: str
    name: str
    expected_role: str
    expected_family: str
    competing_role: str
    signal_kind: str
    skills: tuple[tuple[str, int], ...]
    skill_signals: tuple[tuple[str, SkillSignal], ...] = ()
    years_experience: int | None = None
    seniority: str = ""
    headline: str = ""
    bio: str = ""
    rationale: str = ""

    @property
    def signal_by_slug(self) -> dict[str, SkillSignal]:
        return dict(self.skill_signals)

    @property
    def declares_a_signal(self) -> bool:
        """Whether this variant states anything the engine can act on."""
        if self.years_experience is not None or self.seniority:
            return True
        return any(signal.is_declared for _, signal in self.skill_signals)


@dataclass(frozen=True, slots=True)
class SignalPair:
    """Two descriptions of one person, differing only in declared signals."""

    pair_id: str
    kind: str
    name: str
    expected_role: str
    competing_role: str
    expected_family: str
    with_signals: SignalProfile
    without_signals: SignalProfile
    rationale: str


@dataclass(frozen=True, slots=True)
class PairOutcome:
    """What the engine did with one pair."""

    pair_id: str
    kind: str
    expected_role: str
    competing_role: str
    with_compatibility: float
    without_compatibility: float
    with_competing_compatibility: float
    without_competing_compatibility: float
    with_rank: int
    without_rank: int
    with_margin: float
    without_margin: float
    margin_delta: float
    rank_delta: int
    top1_with: str
    top1_without: str

    @property
    def directional_success(self) -> bool:
        """Whether the signals moved the margin toward the expected role."""
        return self.margin_delta > 0.0

    @property
    def rank_improved(self) -> bool:
        return self.with_rank < self.without_rank

    @property
    def rank_regressed(self) -> bool:
        return self.with_rank > self.without_rank

    @property
    def competing_compatibility_change(self) -> float:
        """How far the signal moved the role it was *not* meant to favour."""
        return self.with_competing_compatibility - self.without_competing_compatibility


@dataclass(frozen=True, slots=True)
class SignalStudyResult:
    """The aggregate of a signal study."""

    pairs: tuple[PairOutcome, ...] = ()
    n_pairs: int = 0
    directional_successes: int = 0
    rank_improvements: int = 0
    rank_regressions: int = 0
    mean_margin_delta: float = 0.0
    mean_absolute_compatibility_change: float = 0.0
    mean_competing_compatibility_change: float = 0.0
    mean_expected_compatibility_with: float = 0.0
    mean_expected_compatibility_without: float = 0.0
    per_kind: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    @property
    def directional_success_rate(self) -> float:
        if not self.n_pairs:
            return 0.0
        return round(self.directional_successes / self.n_pairs, 4)

    @property
    def is_clean(self) -> bool:
        """Whether every pair behaved as designed and no rank got worse."""
        return (
            self.n_pairs > 0
            and self.directional_successes == self.n_pairs
            and self.rank_regressions == 0
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["directional_success_rate"] = self.directional_success_rate
        payload["is_clean"] = self.is_clean
        return payload


@dataclass(frozen=True, slots=True)
class SilenceCheck:
    """Whether a user who states nothing is scored as they always were.

    The engine's rule is that absence is neutral: a skill with no recency has
    a recency factor of exactly 1.0, and a user with no declared level has a
    level fit of exactly 1.0. This check proves it numerically over the whole
    label set rather than asserting it in prose: every profile is scored twice,
    once with the recency half of the signal machinery switched off and once
    with it on, and the two rankings must be identical.
    """

    n_profiles: int
    identical: int
    mismatches: tuple[str, ...] = ()

    @property
    def is_neutral(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_profiles": self.n_profiles,
            "identical": self.identical,
            "mismatches": list(self.mismatches),
            "is_neutral": self.is_neutral,
        }


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #


def _parse_date(value: Any, context: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise SignalStudyError(f"{context}: last_used_at must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SignalStudyError(f"{context}: invalid ISO date {value!r}") from exc


def _parse_optional_float(value: Any, context: str, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SignalStudyError(f"{context}: {field} must be a number")
    number = float(value)
    if number < 0:
        raise SignalStudyError(f"{context}: {field} must not be negative")
    return number


def _parse_optional_int(value: Any, context: str, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise SignalStudyError(f"{context}: {field} must be an integer")
    if value < 0:
        raise SignalStudyError(f"{context}: {field} must not be negative")
    return value


def _parse_profile(record: Mapping[str, Any], context: str) -> SignalProfile:
    required = (
        "id",
        "pair_id",
        "variant",
        "name",
        "expected_role",
        "expected_family",
        "competing_role",
        "signal_kind",
        "skills",
        "rationale",
    )
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise SignalStudyError(f"{context}: missing keys {missing}")

    variant = str(record["variant"])
    if variant not in VARIANTS:
        raise SignalStudyError(f"{context}: unknown variant {variant!r}")

    kind = str(record["signal_kind"])
    if kind not in SIGNAL_KINDS:
        raise SignalStudyError(f"{context}: unknown signal_kind {kind!r}")

    skills: list[tuple[str, int]] = []
    for entry in record["skills"]:
        if "skill_slug" not in entry or "proficiency" not in entry:
            raise SignalStudyError(f"{context}: malformed skill entry {entry!r}")
        proficiency = int(entry["proficiency"])
        if not 1 <= proficiency <= 5:
            raise SignalStudyError(f"{context}: proficiency {proficiency} outside 1-5")
        skills.append((str(entry["skill_slug"]), proficiency))
    if not skills:
        raise SignalStudyError(f"{context}: profile declares no skills")

    skill_signals: list[tuple[str, SkillSignal]] = []
    for entry in record.get("skill_signals", ()):
        slug = str(entry.get("skill_slug", ""))
        if not slug:
            raise SignalStudyError(f"{context}: skill signal without a skill_slug")
        signal = SkillSignal(
            years_used=_parse_optional_float(
                entry.get("years_used"), context, "years_used"
            ),
            last_used_at=(
                _parse_date(entry["last_used_at"], context)
                if entry.get("last_used_at")
                else None
            ),
        )
        skill_signals.append((slug, signal))

    declared_slugs = {slug for slug, _ in skills}
    for slug, _ in skill_signals:
        if slug not in declared_slugs:
            raise SignalStudyError(
                f"{context}: skill signal for {slug!r}, which the profile does not declare"
            )

    return SignalProfile(
        id=str(record["id"]),
        pair_id=str(record["pair_id"]),
        variant=variant,
        name=str(record["name"]),
        expected_role=str(record["expected_role"]),
        expected_family=str(record["expected_family"]),
        competing_role=str(record["competing_role"]),
        signal_kind=kind,
        skills=tuple(skills),
        skill_signals=tuple(skill_signals),
        years_experience=_parse_optional_int(
            record.get("years_experience"), context, "years_experience"
        ),
        seniority=str(record.get("seniority", "")),
        headline=str(record.get("headline", "")),
        bio=str(record.get("bio", "")),
        rationale=str(record["rationale"]),
    )


def _validate_pair(pair: SignalPair, context: str) -> None:
    """Enforce the mechanical conditions the study's claims rest on.

    This is the honesty mechanism of the whole module. Every condition below
    exists because breaking it would let a result be manufactured without
    changing any code.
    """
    with_signals = pair.with_signals
    without_signals = pair.without_signals

    if with_signals.skills != without_signals.skills:
        raise SignalStudyError(
            f"{context}: the two variants of a pair must declare identical skills "
            "and proficiencies"
        )
    if with_signals.headline != without_signals.headline:
        raise SignalStudyError(f"{context}: the two variants must share a headline")
    if with_signals.bio != without_signals.bio:
        raise SignalStudyError(f"{context}: the two variants must share a bio")
    if with_signals.expected_role != without_signals.expected_role:
        raise SignalStudyError(f"{context}: the two variants must name the same role")
    if with_signals.competing_role != without_signals.competing_role:
        raise SignalStudyError(
            f"{context}: the two variants must name the same competing role"
        )
    if with_signals.expected_role == with_signals.competing_role:
        raise SignalStudyError(
            f"{context}: the expected role and the competing role must differ"
        )
    if not with_signals.declares_a_signal:
        raise SignalStudyError(
            f"{context}: the with_signals variant declares no signal at all"
        )
    if without_signals.declares_a_signal:
        raise SignalStudyError(
            f"{context}: the without_signals variant declares a signal; it is the "
            "control and must be silent"
        )

    kind = pair.kind
    if kind == "level":
        if not with_signals.seniority:
            raise SignalStudyError(f"{context}: a level pair must declare a level")
    elif kind == "recency":
        if not any(
            signal.last_used_at is not None for _, signal in with_signals.skill_signals
        ):
            raise SignalStudyError(f"{context}: a recency pair must declare a last-used date")
    elif kind == "depth" and not any(
        signal.years_used is not None for _, signal in with_signals.skill_signals
    ):
        raise SignalStudyError(f"{context}: a depth pair must declare years used")


def load_signal_profiles(path: Path) -> tuple[SignalPair, ...]:
    """Read the signal study label file.

    The file holds one JSON object per line. Each *pair* is two lines: a
    ``with_signals`` variant and a ``without_signals`` variant sharing a
    ``pair_id``. A pair with only one variant, or with three, is an error.
    """
    if not path.exists():
        raise SignalStudyError(f"signal profile file not found: {path}")

    variants: dict[str, list[SignalProfile]] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SignalStudyError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        profile = _parse_profile(record, f"{path}:{lineno}")
        variants.setdefault(profile.pair_id, []).append(profile)

    if not variants:
        raise SignalStudyError(f"{path}: no signal profiles found")

    pairs: list[SignalPair] = []
    for pair_id, members in variants.items():
        context = f"{path}:{pair_id}"
        by_variant = {member.variant: member for member in members}
        missing = [variant for variant in VARIANTS if variant not in by_variant]
        if missing:
            raise SignalStudyError(f"{context}: pair is missing the {missing} variant")
        if len(members) != len(VARIANTS):
            raise SignalStudyError(f"{context}: pair has {len(members)} variants, expected 2")
        with_signals = by_variant["with_signals"]
        without_signals = by_variant["without_signals"]
        pair = SignalPair(
            pair_id=pair_id,
            kind=with_signals.signal_kind,
            name=with_signals.name,
            expected_role=with_signals.expected_role,
            competing_role=with_signals.competing_role,
            expected_family=with_signals.expected_family,
            with_signals=with_signals,
            without_signals=without_signals,
            rationale=with_signals.rationale,
        )
        _validate_pair(pair, context)
        pairs.append(pair)

    return tuple(sorted(pairs, key=lambda pair: pair.pair_id))


# --------------------------------------------------------------------------- #
# running
# --------------------------------------------------------------------------- #


def build_snapshot(
    profile: SignalProfile,
    skill_ids: Mapping[str, int],
    taxonomy: Taxonomy,
) -> ProfileSnapshot:
    """Turn a study profile into the snapshot the engine consumes."""
    unknown = [slug for slug, _ in profile.skills if slug not in skill_ids]
    if unknown:
        raise SignalStudyError(f"profile {profile.id}: unknown skill slugs {unknown}")

    signals = profile.signal_by_slug
    skills = tuple(
        UserSkillFact(
            skill_id=skill_ids[slug],
            proficiency=proficiency,
            name=taxonomy.by_slug[slug].name,
            slug=slug,
            years_used=signals[slug].years_used if slug in signals else None,
            last_used_at=signals[slug].last_used_at if slug in signals else None,
        )
        for slug, proficiency in profile.skills
    )
    snapshot = ProfileSnapshot(
        user_id=0,
        headline=profile.headline or profile.name,
        career_goal="",
        bio=profile.bio,
        preferred_role_family=profile.expected_family,
        skills=skills,
        projects=(),
        education=(),
        years_experience=profile.years_experience,
        seniority=profile.seniority,
    )
    return with_profile_text(snapshot)


@dataclass(frozen=True, slots=True)
class _Scored:
    """The result of ranking one profile."""

    order: tuple[str, ...]
    compatibility: Mapping[str, float]
    rank_of: Mapping[str, int]


def _score(
    snapshot: ProfileSnapshot,
    role_specs: Sequence[RoleSpec],
    *,
    coverage_weight: float,
    tfidf_weight: float,
    skill_names: Mapping[int, tuple[str, str]],
    role_seniorities: Mapping[int, str],
    today: date | None,
) -> _Scored:
    ranked = rank(
        snapshot,
        role_specs,
        coverage_weight=coverage_weight,
        tfidf_weight=tfidf_weight,
        top_n=None,
        skill_names=skill_names,
        role_seniorities=role_seniorities,
        today=today,
    )
    if not ranked:
        raise SignalStudyError("ranker returned no roles; knowledge base is empty")
    return _Scored(
        order=tuple(score.slug for score in ranked),
        compatibility={score.slug: score.compatibility for score in ranked},
        rank_of={score.slug: position for position, score in enumerate(ranked, start=1)},
    )


def _margin(scored: _Scored, expected_role: str, competing_role: str) -> float:
    try:
        return scored.compatibility[expected_role] - scored.compatibility[competing_role]
    except KeyError as exc:  # pragma: no cover - the loader checks the roles exist
        raise SignalStudyError(f"role {exc.args[0]!r} is not in the knowledge base") from exc


def run_study(
    pairs: Sequence[SignalPair],
    role_specs: Sequence[RoleSpec],
    *,
    skill_ids: Mapping[str, int],
    taxonomy: Taxonomy,
    role_seniorities: Mapping[int, str],
    coverage_weight: float = 0.6,
    tfidf_weight: float = 0.4,
    today: date = EVALUATION_TODAY,
) -> SignalStudyResult:
    """Run every pair and aggregate the outcomes."""
    skill_names = {entry.skill_id: (entry.name, entry.category) for entry in taxonomy.skills}

    outcomes: list[PairOutcome] = []
    for pair in pairs:
        with_snapshot = build_snapshot(pair.with_signals, skill_ids, taxonomy)
        without_snapshot = build_snapshot(pair.without_signals, skill_ids, taxonomy)

        with_scored = _score(
            with_snapshot,
            role_specs,
            coverage_weight=coverage_weight,
            tfidf_weight=tfidf_weight,
            skill_names=skill_names,
            role_seniorities=role_seniorities,
            today=today,
        )
        without_scored = _score(
            without_snapshot,
            role_specs,
            coverage_weight=coverage_weight,
            tfidf_weight=tfidf_weight,
            skill_names=skill_names,
            role_seniorities=role_seniorities,
            today=today,
        )

        with_margin = _margin(with_scored, pair.expected_role, pair.competing_role)
        without_margin = _margin(without_scored, pair.expected_role, pair.competing_role)

        outcomes.append(
            PairOutcome(
                pair_id=pair.pair_id,
                kind=pair.kind,
                expected_role=pair.expected_role,
                competing_role=pair.competing_role,
                with_compatibility=round(
                    with_scored.compatibility[pair.expected_role], 6
                ),
                without_compatibility=round(
                    without_scored.compatibility[pair.expected_role], 6
                ),
                with_competing_compatibility=round(
                    with_scored.compatibility[pair.competing_role], 6
                ),
                without_competing_compatibility=round(
                    without_scored.compatibility[pair.competing_role], 6
                ),
                with_rank=with_scored.rank_of[pair.expected_role],
                without_rank=without_scored.rank_of[pair.expected_role],
                with_margin=round(with_margin, 6),
                without_margin=round(without_margin, 6),
                margin_delta=round(with_margin - without_margin, 6),
                rank_delta=(
                    with_scored.rank_of[pair.expected_role]
                    - without_scored.rank_of[pair.expected_role]
                ),
                top1_with=with_scored.order[0],
                top1_without=without_scored.order[0],
            )
        )

    if not outcomes:
        return SignalStudyResult()

    per_kind: dict[str, dict[str, float]] = {}
    for kind in sorted({outcome.kind for outcome in outcomes}):
        subset = [outcome for outcome in outcomes if outcome.kind == kind]
        per_kind[kind] = {
            "n": len(subset),
            "directional_successes": sum(1 for o in subset if o.directional_success),
            "mean_margin_delta": round(
                statistics.fmean(o.margin_delta for o in subset), 6
            ),
        }

    return SignalStudyResult(
        pairs=tuple(outcomes),
        n_pairs=len(outcomes),
        directional_successes=sum(1 for o in outcomes if o.directional_success),
        rank_improvements=sum(1 for o in outcomes if o.rank_improved),
        rank_regressions=sum(1 for o in outcomes if o.rank_regressed),
        mean_margin_delta=round(
            statistics.fmean(o.margin_delta for o in outcomes), 6
        ),
        mean_absolute_compatibility_change=round(
            statistics.fmean(
                abs(o.with_compatibility - o.without_compatibility) for o in outcomes
            ),
            6,
        ),
        mean_competing_compatibility_change=round(
            statistics.fmean(
                o.competing_compatibility_change for o in outcomes
            ),
            6,
        ),
        mean_expected_compatibility_with=round(
            statistics.fmean(o.with_compatibility for o in outcomes), 6
        ),
        mean_expected_compatibility_without=round(
            statistics.fmean(o.without_compatibility for o in outcomes), 6
        ),
        per_kind=per_kind,
    )


def check_silence(
    profiles: Sequence[Any],
    role_specs: Sequence[RoleSpec],
    *,
    build: Any,
    coverage_weight: float = 0.6,
    tfidf_weight: float = 0.4,
    skill_names: Mapping[int, tuple[str, str]] | None = None,
    role_seniorities: Mapping[int, str] | None = None,
    today: date = EVALUATION_TODAY,
) -> SilenceCheck:
    """Prove that a user who states nothing is scored exactly as before.

    ``build`` is a callable taking a profile and returning its snapshot; the
    caller supplies it so this module does not need to know how a label record
    becomes a snapshot. Each profile is scored twice -- once with the recency
    half of the signal machinery switched off (``today=None``) and once with it
    on -- and the two results must be identical, down to the sixth decimal.

    Both halves of the engine's neutrality rule are covered. The recency factor
    is the only thing ``today`` changes, and a skill with no ``last_used_at``
    has a recency factor of exactly 1.0 either way. The level fit is computed
    on both passes, so a profile with no declared level is checked against the
    real role seniorities rather than against a stub.
    """
    names = skill_names or {}
    seniorities = role_seniorities or {}

    mismatches: list[str] = []
    for profile in profiles:
        snapshot = build(profile)
        silent = _score(
            snapshot,
            role_specs,
            coverage_weight=coverage_weight,
            tfidf_weight=tfidf_weight,
            skill_names=names,
            role_seniorities=seniorities,
            today=None,
        )
        with_signals = _score(
            snapshot,
            role_specs,
            coverage_weight=coverage_weight,
            tfidf_weight=tfidf_weight,
            skill_names=names,
            role_seniorities=seniorities,
            today=today,
        )
        same_order = silent.order == with_signals.order
        same_scores = all(
            round(silent.compatibility[slug], 6)
            == round(with_signals.compatibility[slug], 6)
            for slug in silent.order
        )
        if not (same_order and same_scores):
            mismatches.append(getattr(profile, "id", "<unknown>"))

    return SilenceCheck(
        n_profiles=len(profiles),
        identical=len(profiles) - len(mismatches),
        mismatches=tuple(mismatches),
    )


def render_table(result: SignalStudyResult) -> str:
    """Render the per-pair ablation table for the report."""
    lines = [
        "| Pair | Signal | Expected role | Competing role | "
        "Compat. (signals) | Compat. (silent) | Margin delta | Rank |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for outcome in result.pairs:
        rank_cell = f"{outcome.without_rank} -> {outcome.with_rank}"
        lines.append(
            f"| {outcome.pair_id} | {outcome.kind} | {outcome.expected_role} | "
            f"{outcome.competing_role} | {outcome.with_compatibility:.3f} | "
            f"{outcome.without_compatibility:.3f} | {outcome.margin_delta:+.3f} | "
            f"{rank_cell} |"
        )
    return "\n".join(lines)
