"""Weight sweep over the coverage / tf-idf split.

The engine ships a 0.6 / 0.4 split. This module exists to answer one question:
is that split a defensible choice on evidence, or is it a number someone liked the
look of? The sweep re-scores the whole label set at each candidate coverage
weight, with the tf-idf weight as the complement so the two always sum to 1.

Tie-breaking is specified rather than left to dict ordering: ties on top-3 hit
rate go to the higher top-1 accuracy, then the higher MRR, and if those are also
equal the split closest to the proposal's 0.6 wins. Without that last rule the
recommendation would drift with the iteration order of the candidate list, and
the "chosen weight" in the report would be an artefact of Python.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

__all__ = [
    "DEFAULT_COVERAGE_WEIGHT",
    "SWEEP_WEIGHTS",
    "TuningPoint",
    "recommend",
    "sweep",
]

#: The proposal's split, and the value every tie is broken toward.
DEFAULT_COVERAGE_WEIGHT = 0.6

#: The candidate range the plan specifies for T154.
SWEEP_WEIGHTS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9)


@dataclass(frozen=True, slots=True)
class TuningPoint:
    """Metrics observed at one coverage weight."""

    coverage_weight: float
    tfidf_weight: float
    top1_accuracy: float
    top3_hit_rate: float
    mean_reciprocal_rank: float
    mean_compatibility_of_expected: float

    def to_dict(self) -> dict[str, float]:
        return {
            "coverage_weight": self.coverage_weight,
            "tfidf_weight": self.tfidf_weight,
            "top1_accuracy": self.top1_accuracy,
            "top3_hit_rate": self.top3_hit_rate,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "mean_compatibility_of_expected": self.mean_compatibility_of_expected,
        }

    def row(self) -> str:
        """One fixed-width table row, so the text report stays diffable."""
        return (
            f"| {self.coverage_weight:.2f} | {self.tfidf_weight:.2f} "
            f"| {self.top1_accuracy:.3f} | {self.top3_hit_rate:.3f} "
            f"| {self.mean_reciprocal_rank:.3f} | {self.mean_compatibility_of_expected:.3f} |"
        )


def render_table(points: Sequence[TuningPoint], *, default_weight: float = DEFAULT_COVERAGE_WEIGHT) -> str:
    """Markdown table of the sweep, with the shipped weight marked."""
    header = (
        "| Coverage | tf-idf | Top-1 | Top-3 | MRR | Mean compat. of expected |\n"
        "| --- | --- | --- | --- | --- | --- |"
    )
    lines = [header]
    for point in points:
        mark = " (default)" if abs(point.coverage_weight - default_weight) < 1e-9 else ""
        row = point.row()
        if mark:
            row = row.replace(
                f"| {point.coverage_weight:.2f} |",
                f"| {point.coverage_weight:.2f}{mark} |",
            )
        lines.append(row)
    return "\n".join(lines)


def recommend(
    points: Sequence[TuningPoint],
    *,
    default_weight: float = DEFAULT_COVERAGE_WEIGHT,
    noise_floor: float = 0.0,
) -> TuningPoint:
    """Pick the weight to ship, with a noise floor so a single profile cannot move it.

    Ranking is by top-3 hit rate, then top-1 accuracy, then MRR, then closeness to
    the proposal's 0.6. The noise floor is the final and most important guard: a
    candidate only displaces the default if it beats it by *more* than
    ``noise_floor`` on the metric that matters.

    Without that guard a 26-profile label set will happily recommend a different
    weight on the strength of one profile flipping, and the "chosen value" in the
    report would be a coin toss dressed up as a finding. The correct response to a
    difference that small is to keep the default and say the evidence is
    inconclusive, not to retune the engine.

    Pass ``noise_floor = 1 / n_profiles`` -- the resolution of the label set -- to
    make the recommendation mean something.
    """
    if not points:
        raise ValueError("cannot recommend a weight from an empty sweep")

    by_weight = {round(point.coverage_weight, 6): point for point in points}
    default_point = by_weight.get(round(default_weight, 6))

    def sort_key(point: TuningPoint) -> tuple[float, float, float, float]:
        # Negated distance last: smaller distance sorts higher.
        return (
            point.top3_hit_rate,
            point.top1_accuracy,
            point.mean_reciprocal_rank,
            -abs(point.coverage_weight - default_weight),
        )

    best = max(points, key=sort_key)
    if default_point is None or best is default_point or noise_floor <= 0.0:
        return best

    # A challenger must win by more than the noise floor on top-3, or tie on
    # top-3 and win by more than the noise floor on top-1.
    if best.top3_hit_rate > default_point.top3_hit_rate + noise_floor:
        return best
    if (
        abs(best.top3_hit_rate - default_point.top3_hit_rate) <= 1e-9
        and best.top1_accuracy > default_point.top1_accuracy + noise_floor
    ):
        return best
    return default_point


#: Signature of the callable the sweep drives: given a coverage weight, return
#: the metrics measured at that weight. The harness derives the complement and
#: normalises the pair, so a caller only has to name the coverage side.
EvaluateAt = Callable[[float], TuningPoint]


def sweep(
    evaluate_at: EvaluateAt, weights: Sequence[float] = SWEEP_WEIGHTS
) -> tuple[TuningPoint, ...]:
    """Run ``evaluate_at`` across ``weights``.

    The closed interval is allowed because the 0.0 and 1.0 endpoints are
    meaningful: they disable one component entirely, which is the only way to
    find out whether a component is doing any work at all. Weights are rounded
    to six places before being passed on, so a stored report never shows
    ``0.7000000000000001`` and a re-run compares equal.
    """
    points: list[TuningPoint] = []
    for weight in weights:
        if not 0.0 <= weight <= 1.0:
            raise ValueError(f"coverage weight must be within [0, 1], got {weight}")
        points.append(evaluate_at(round(weight, 6)))
    return tuple(points)
