"""The signals the engine reads beyond declared proficiency.

``docs/limitations.md`` used to say that skills were the only real signal: two
profiles with identical skills and twenty years' difference in experience were
indistinguishable, a skill last used in 2004 counted the same as one used last
week, and a skill listed at proficiency 5 counted the same whether the user had
written one line of it or a decade of it. This module is the answer to that
sentence.

Three signals are modelled, and each one is a *discount* on a declared
proficiency rather than a new thing to collect:

* **Recency** — how long ago the skill was last used.
* **Depth** — how many years the skill has actually been used.
* **Level fit** — how close the user's declared level is to the role's level.

Three design rules hold throughout, and each of them exists to stop the engine
from being unfair to a user who has not filled in a field:

1. **Absence is neutral, never a penalty.** A skill with no ``last_used_at`` has
   a recency factor of exactly ``1.0``; a user with no declared level has a
   level fit of exactly ``1.0``. Not knowing something is not evidence of a
   mismatch, and a user who has never heard of the "years used" field must not
   be ranked below a user who has.
2. **The discount is bounded.** A stale *and* shallow skill is discounted by at
   most 30%, never erased. A skill you used in 2004 is still a skill you have.
3. **No wall clock inside the engine.** Every function that needs today's date
   takes it as an argument. The reference date is supplied by the service layer
   in production and by a fixed constant in the evaluation harness, so the
   engine stays a pure function of its inputs.

This module must not import SQLAlchemy or FastAPI, and neither may anything
else under ``app/ml/`` — see the rule stated at the top of ``app/ml/types.py``.
"""

from __future__ import annotations

from datetime import date

# ---------------------------------------------------------------------------
# Level bands
# ---------------------------------------------------------------------------

#: The six seniority bands, ordered from least to most experienced. The band
#: names are the same strings the job-role knowledge base already uses, so a
#: role's ``seniority`` and a user's declared level can be compared directly.
LEVEL_BANDS: tuple[str, ...] = ("Entry", "Junior", "Mid", "Senior", "Lead", "Principal")

#: Minimum years of experience for each band, in order. A user who has not
#: declared a level but has declared years gets a band derived from this table,
#: which is what makes the signal usable for everyone rather than only for the
#: people who find the level dropdown.
YEARS_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (0, "Entry"),
    (1, "Junior"),
    (2, "Mid"),
    (5, "Senior"),
    (9, "Lead"),
    (13, "Principal"),
)

# ---------------------------------------------------------------------------
# Level fit
# ---------------------------------------------------------------------------

#: How much of the coverage survives a level mismatch, by band distance.
#:
#: Deliberately gentle. A junior should still see senior roles — they are the
#: roles worth growing towards — and a senior should still see junior roles,
#: because the shortlist is a set of possibilities, not a filter. The
#: adjustment reorders; it does not exclude.
LEVEL_FIT_BY_DISTANCE: dict[int, float] = {
    0: 1.00,
    1: 0.92,
    2: 0.80,
}

#: The fit for a distance of three bands or more.
LEVEL_FIT_FAR: float = 0.65

# ---------------------------------------------------------------------------
# Recency
# ---------------------------------------------------------------------------

#: Months after which a skill's recency factor has decayed by half.
RECENCY_HALF_LIFE_MONTHS: float = 36.0

#: The floor for the recency factor. A skill last used in 2004 still counts.
RECENCY_FLOOR: float = 0.70

#: Average days in a month, for converting a day count into months.
DAYS_PER_MONTH: float = 30.436875

# ---------------------------------------------------------------------------
# Depth
# ---------------------------------------------------------------------------

#: Years of use after which the depth signal is fully satisfied.
DEPTH_FULL_YEARS: float = 5.0

#: The floor for the depth factor. Even a skill used for a fortnight counts for
#: something; the question is how much less than a decade of practice.
DEPTH_FLOOR: float = 0.80

# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

#: The floor for the combined recency-and-depth adjustment. This is the number
#: that makes the "bounded discount" promise in the module docstring true: a
#: skill that is both stale and shallow keeps at least 70% of its declared
#: strength.
SIGNAL_FLOOR: float = 0.70


def normalise_band(value: str | None) -> str | None:
    """Map a free-text level onto one of :data:`LEVEL_BANDS`.

    Returns ``None`` for anything unrecognised, including ``None`` and the
    empty string. A level the system does not understand is treated as
    "not declared" rather than being guessed at.
    """
    if not value:
        return None
    candidate = value.strip().casefold()
    for band in LEVEL_BANDS:
        if band.casefold() == candidate:
            return band
    return None


def band_from_years(years: int | None) -> str | None:
    """Derive a band from a number of years, or ``None`` if years are unknown."""
    if years is None or years < 0:
        return None
    band = LEVEL_BANDS[0]
    for threshold, candidate in YEARS_THRESHOLDS:
        if years >= threshold:
            band = candidate
    return band


def user_level_band(seniority: str | None, years_experience: int | None) -> str | None:
    """The band the user is at, from whatever they have told us.

    An explicitly declared level wins, because it is the more specific
    statement. Years of experience is the fallback, because it is a field the
    product already collected and mostly ignored.
    """
    declared = normalise_band(seniority)
    if declared is not None:
        return declared
    return band_from_years(years_experience)


def level_fit(user_band: str | None, role_band: str | None) -> float:
    """How close the user's level is to the role's level, as a multiplier.

    ``1.0`` when either side is unknown. That is the "absence is neutral" rule
    doing its work: a user who has not declared a level, or a role with no
    seniority label, must not be penalised.
    """
    if user_band is None or role_band is None:
        return 1.0
    try:
        distance = abs(LEVEL_BANDS.index(user_band) - LEVEL_BANDS.index(role_band))
    except ValueError:
        # A band outside the scale. Treat as unknown rather than guessing.
        return 1.0
    return LEVEL_FIT_BY_DISTANCE.get(distance, LEVEL_FIT_FAR)


def recency_factor(last_used_at: date | None, today: date) -> float:
    """How recently the skill was used, as a multiplier in ``[0.7, 1.0]``.

    Exponential decay with a 36-month half life, floored so that a skill last
    used in 2004 keeps 70% of its strength rather than decaying to nothing.

    ``None`` means "not stated", which is neutral: ``1.0``.
    """
    if last_used_at is None:
        return 1.0
    days = (today - last_used_at).days
    if days <= 0:
        # Used today, or a date in the future — which is a data-entry slip, not
        # a reason to punish the user.
        return 1.0
    months = days / DAYS_PER_MONTH
    decayed = 0.5 ** (months / RECENCY_HALF_LIFE_MONTHS)
    return max(RECENCY_FLOOR, min(1.0, RECENCY_FLOOR + (1.0 - RECENCY_FLOOR) * decayed))


def depth_factor(years_used: float | None) -> float:
    """How long the skill has actually been used, as a multiplier in ``[0.8, 1.0]``.

    ``None`` means "not stated", which is neutral: ``1.0``.
    """
    if years_used is None:
        return 1.0
    years = max(0.0, float(years_used))
    if years >= DEPTH_FULL_YEARS:
        return 1.0
    scaled = DEPTH_FLOOR + (1.0 - DEPTH_FLOOR) * (years / DEPTH_FULL_YEARS)
    return max(DEPTH_FLOOR, min(1.0, scaled))


def signal_factor(
    years_used: float | None,
    last_used_at: date | None,
    today: date | None,
) -> float:
    """The combined recency-and-depth adjustment for one skill.

    ``today`` of ``None`` means "no reference date", in which case the recency
    half of the signal is neutral. The evaluation harness passes a fixed date;
    the service layer passes the real one.
    """
    if today is None:
        return depth_factor(years_used)
    combined = recency_factor(last_used_at, today) * depth_factor(years_used)
    return max(SIGNAL_FLOOR, min(1.0, combined))
