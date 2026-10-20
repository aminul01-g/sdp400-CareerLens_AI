"""The two scoring components: weighted skill coverage and TF-IDF cosine.

Both functions are pure, take plain mappings, and return a float in ``[0, 1]``.
That is what makes them testable without a database and reproducible.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from app.ml.types import RoleSpec, proficiency_factor

logger = logging.getLogger("app.ml.matcher")


def weighted_skill_coverage_from_factors(
    factors: Mapping[int, float],
    required: Mapping[int, float],
) -> float:
    """How much of a role's weighted requirement set the user satisfies.

    .. code-block:: text

        coverage = SUM(role_weight * strength) / SUM(role_weight)

    where ``strength`` is an already-computed number in ``[0, 1]`` for the
    skill. :func:`weighted_skill_coverage` is the special case where strength
    is the proficiency factor and nothing else; this function is the general
    form the ranker uses once recency and depth are folded in.

    The properties this function guarantees, each asserted in ``test_matcher.py``:

    * **Bounds.** Always in ``[0, 1]`` for any input, because the numerator is
      a subset of the denominator's terms and every factor is in ``[0, 1]``.
    * **Superset.** A user holding every required skill at full strength scores
      exactly ``1.0``.
    * **Disjoint.** No overlap scores exactly ``0.0``.
    * **Monotonic.** Raising a factor never lowers the score.
    * **Scale invariance.** Halving every weight leaves the score unchanged —
      correct, because only the *relative* importance of a role's requirements
      matters, not their absolute scale.

    Note the denominator is the sum of the role's weights, **not** a count of
    requirements, which is what makes a 0.9-weight critical skill count for more
    than a 0.3-weight desirable one.
    """
    if not required:
        return 0.0

    denominator = float(sum(required.values()))
    if denominator <= 0.0:
        return 0.0

    numerator = 0.0
    for skill_id, weight in required.items():
        factor = factors.get(skill_id)
        if factor is None:
            continue
        numerator += float(weight) * float(factor)

    coverage = numerator / denominator
    # Guard against floating-point drift pushing a mathematically in-range value
    # to 1.0000000000000002 and breaking a database CHECK constraint.
    return max(0.0, min(1.0, coverage))


def weighted_skill_coverage(
    user_skills: Mapping[int, int],
    required: Mapping[int, float],
) -> float:
    """How much of a role's weighted requirement set the user satisfies.

    .. code-block:: text

        coverage = SUM(role_weight * proficiency_factor) / SUM(role_weight)

    where ``proficiency_factor = (proficiency - 1) / 4``.

    This is the declared-proficiency view, with no recency or depth adjustment.
    The ranker uses :func:`weighted_skill_coverage_from_factors` so that both
    views can be reported side by side; this function remains the plain
    proficiency-only contract that the matcher tests pin down.
    """
    return weighted_skill_coverage_from_factors(
        {
            skill_id: proficiency_factor(int(proficiency))
            for skill_id, proficiency in user_skills.items()
        },
        required,
    )


def tfidf_cosine(
    profile_text: str,
    role_specs: Sequence[RoleSpec],
) -> list[float]:
    """Cosine similarity between the profile text and each role description.

    Four decisions, each with a reason:

    1. **The vectorizer is fitted per call, not once at startup.** Precomputing an
       IDF table over the job corpus and then only *transforming* the profile is
       faster, but it leaks the job descriptions' vocabulary into the profile's
       representation — so a profile's score would depend on which *other* roles
       happen to be active. Fitting per call keeps the profile row independent of
       the candidate set. At 60 documents this costs single-digit milliseconds.
    2. **``ngram_range=(1, 2)``.** Unigrams alone cannot distinguish "machine
       learning" from "learning machine"; bigrams capture multi-word skill names.
    3. **``sublinear_tf=True``.** A CV that says "Python" 40 times should not
       outrank one that mentions four technologies once.
    4. **Clamp to ``[0, 1]``.** ``cosine_similarity`` can return ``-1e-17`` from
       floating-point noise, and a negative cosine feeding a percentage display
       is a visible bug.
    """
    if not role_specs:
        return []
    if not profile_text or not profile_text.strip():
        return [0.0] * len(role_specs)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    corpus = [profile_text] + [spec.description for spec in role_specs]
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Raised when the vocabulary is empty — e.g. the profile text is entirely
        # stop words. Zero similarity is the honest answer, not a 500.
        logger.debug("Empty TF-IDF vocabulary; returning zero similarities")
        return [0.0] * len(role_specs)

    similarities = cosine_similarity(matrix[0], matrix[1:])[0]
    return [float(max(0.0, min(1.0, value))) for value in similarities]


def combined_score(
    coverage: float,
    cosine: float,
    coverage_weight: float,
    tfidf_weight: float,
) -> float:
    """``w1 * coverage + w2 * cosine``, clamped to ``[0, 1]``.

    The clamp exists because floating-point addition of two in-range products can
    land a hair outside, and the value is persisted into a column with a
    ``CHECK (... BETWEEN 0 AND 1)``.
    """
    score = coverage_weight * coverage + tfidf_weight * cosine
    return max(0.0, min(1.0, score))
