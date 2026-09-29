"""Evaluation harness for the matching engine.

This package is part of the pure ML layer. It reads the knowledge-base JSON and
the hand-labelled profile set from disk and never touches the database, ORM or
web layer, so an evaluation can be reproduced from a clean checkout with no
services running. ``scripts/verify_compliance.py`` enforces that boundary with an
AST check over ``app/ml``.

Layering, so each piece stays testable on its own:

``metrics``  pure functions over (labels, predictions); no engine knowledge
``tuning``   weight sweep and the tie-break rule; no engine knowledge
``harness``  loads labels and the knowledge base, drives ``ranker``, reports
"""

from app.ml.evaluation.harness import (
    EvaluationDataError,
    EvaluationResult,
    LabelledProfile,
    ProfileOutcome,
    evaluate,
    load_profiles,
    load_role_specs,
    load_seniorities,
    load_taxonomy_index,
    render_markdown,
    sweep,
    write_reports,
)
from app.ml.evaluation.metrics import (
    Metrics,
    compute_metrics,
    mean_compatibility_of_expected,
    mean_reciprocal_rank,
    per_component_means,
    rank_of,
    top1_accuracy,
    top3_hit_rate,
)
from app.ml.evaluation.tuning import (
    SWEEP_WEIGHTS,
    TuningPoint,
    recommend,
    render_table,
)

__all__ = [
    "SWEEP_WEIGHTS",
    "EvaluationDataError",
    "EvaluationResult",
    "LabelledProfile",
    "Metrics",
    "ProfileOutcome",
    "TuningPoint",
    "compute_metrics",
    "evaluate",
    "load_profiles",
    "load_role_specs",
    "load_seniorities",
    "load_taxonomy_index",
    "mean_compatibility_of_expected",
    "mean_reciprocal_rank",
    "per_component_means",
    "rank_of",
    "recommend",
    "render_markdown",
    "render_table",
    "sweep",
    "top1_accuracy",
    "top3_hit_rate",
    "write_reports",
]
