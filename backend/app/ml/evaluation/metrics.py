"""Pure scoring functions for the evaluation harness.

Every function here is a total function of its arguments: same labels and same
predictions in, same number out. They know nothing about the ranker, the
knowledge base, the database or the filesystem, which is what makes them
testable in isolation and re-usable against predictions from anywhere.

A "prediction" is the ordered list of role slugs the engine returned for a
profile, best first. Order is meaningful -- it is what the ranker's tie-break
guarantees -- so nothing here sorts or dedupes.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "Metrics",
    "compute_metrics",
    "mean_compatibility_of_expected",
    "mean_reciprocal_rank",
    "per_component_means",
    "rank_of",
    "top1_accuracy",
    "top3_hit_rate",
]


def _validate(expected: Sequence[str], predictions: Sequence[Sequence[str]]) -> None:
    if len(expected) != len(predictions):
        raise ValueError(
            f"labels/predictions length mismatch: {len(expected)} labels, "
            f"{len(predictions)} predictions"
        )
    if not expected:
        raise ValueError("cannot score an empty label set")


def rank_of(expected_role: str, predicted_roles: Sequence[str]) -> int:
    """1-based position of the expected role, or 0 when it is absent.

    Zero rather than a sentinel string, because a missing expected role has to
    feed the same arithmetic as a present one: a reciprocal rank of 0 is what
    keeps MRR honest instead of quietly rewarding a short prediction list.
    """
    for position, slug in enumerate(predicted_roles, start=1):
        if slug == expected_role:
            return position
    return 0


def top1_accuracy(
    expected: Sequence[str], predictions: Sequence[Sequence[str]]
) -> float:
    """Fraction of profiles whose first prediction is the expected role."""
    _validate(expected, predictions)
    hits = sum(
        1
        for want, got in zip(expected, predictions, strict=True)
        if got and got[0] == want
    )
    return hits / len(expected)


def top3_hit_rate(
    expected: Sequence[str], predictions: Sequence[Sequence[str]], *, k: int = 3
) -> float:
    """Fraction of profiles with the expected role in their top ``k``.

    This is the metric the proposal commits to, because ``k = 3`` is the
    shortlist the UI actually renders.
    """
    _validate(expected, predictions)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    hits = sum(
        1
        for want, got in zip(expected, predictions, strict=True)
        if want in got[:k]
    )
    return hits / len(expected)


def mean_reciprocal_rank(
    expected: Sequence[str], predictions: Sequence[Sequence[str]]
) -> float:
    """Mean of 1/rank over the expected role, counting a miss as 0."""
    _validate(expected, predictions)
    return statistics.fmean(
        (1.0 / position) if position else 0.0
        for want, got in zip(expected, predictions, strict=True)
        for position in (rank_of(want, got),)
    )


def mean_compatibility_of_expected(
    expected: Sequence[str], compatibility_by_profile: Sequence[Mapping[str, float]]
) -> float:
    """Mean engine score actually assigned to the expected role.

    Reported alongside the rank metrics because a high hit rate built on 0.3
    compatibility scores means the shortlist is right and the percentages are
    not trustworthy, and those are different problems with different fixes.
    """
    if len(expected) != len(compatibility_by_profile):
        raise ValueError(
            f"labels/scores length mismatch: {len(expected)} labels, "
            f"{len(compatibility_by_profile)} score maps"
        )
    if not expected:
        raise ValueError("cannot average over an empty label set")

    scores: list[float] = []
    for want, scores_for_profile in zip(expected, compatibility_by_profile, strict=True):
        if want not in scores_for_profile:
            raise ValueError(f"expected role {want!r} missing from its score map")
        scores.append(float(scores_for_profile[want]))
    return statistics.fmean(scores)


def per_component_means(
    expected: Sequence[str],
    components_by_profile: Sequence[Mapping[str, Mapping[str, float]]],
) -> dict[str, float]:
    """Mean of each score component over the expected role.

    Reveals *why* a role matched: a high coverage with a near-zero cosine
    similarity means the user has the listed skills but the profile text says
    something else, which is a profile-completeness problem rather than a
    matching one.
    """
    if len(expected) != len(components_by_profile):
        raise ValueError(
            f"labels/components length mismatch: {len(expected)} labels, "
            f"{len(components_by_profile)} component maps"
        )
    if not expected:
        raise ValueError("cannot average over an empty label set")

    collected: dict[str, list[float]] = {}
    for want, components in zip(expected, components_by_profile, strict=True):
        if want not in components:
            raise ValueError(f"expected role {want!r} missing from its component map")
        for name, value in components[want].items():
            collected.setdefault(name, []).append(float(value))
    return {name: round(statistics.fmean(values), 6) for name, values in collected.items()}


@dataclass(frozen=True, slots=True)
class Metrics:
    """All headline numbers for one evaluation run."""

    n_profiles: int
    top1_accuracy: float
    top3_hit_rate: float
    mean_reciprocal_rank: float
    mean_compatibility_of_expected: float
    component_means: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_profiles": self.n_profiles,
            "top1_accuracy": self.top1_accuracy,
            "top3_hit_rate": self.top3_hit_rate,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "mean_compatibility_of_expected": self.mean_compatibility_of_expected,
            "component_means": dict(self.component_means),
        }


def compute_metrics(
    expected: Sequence[str],
    predictions: Sequence[Sequence[str]],
    *,
    compatibility_by_profile: Sequence[Mapping[str, float]] | None = None,
    components_by_profile: Sequence[Mapping[str, Mapping[str, float]]] | None = None,
    k: int = 3,
) -> Metrics:
    """Compute the full metric set, degrading gracefully on optional inputs.

    ``compatibility_by_profile`` and ``components_by_profile`` are optional
    because the rank metrics do not need them. When they are supplied the
    component and calibration numbers are filled in; when they are not they come
    back as ``0.0`` and empty rather than raising, so a caller holding only slug
    rankings can still get the three headline metrics.
    """
    _validate(expected, predictions)
    n = len(expected)
    return Metrics(
        n_profiles=n,
        top1_accuracy=round(top1_accuracy(expected, predictions), 6),
        top3_hit_rate=round(top3_hit_rate(expected, predictions, k=k), 6),
        mean_reciprocal_rank=round(mean_reciprocal_rank(expected, predictions), 6),
        mean_compatibility_of_expected=(
            round(mean_compatibility_of_expected(expected, compatibility_by_profile), 6)
            if compatibility_by_profile is not None
            else 0.0
        ),
        component_means=(
            per_component_means(expected, components_by_profile)
            if components_by_profile is not None
            else {}
        ),
    )
