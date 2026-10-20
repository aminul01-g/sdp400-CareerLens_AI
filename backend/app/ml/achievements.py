"""Achievements: what the candidate did, how much of it, and whose it was.

``docs/limitations.md`` used to say of the CV extractor:

    **No achievement quantification.** The extractor knows which technologies a
    sentence mentions. It does not know that "cut query time by 80%" is more
    impressive than "worked on query performance".

    **No understanding of who did what.** "We migrated the Python service" is
    read as a mention, which is right, but the system cannot tell whether "we"
    was the candidate.

Both sentences describe the same missing thing: the extractor reads a CV as a
list of technology mentions, and a CV is not a list of technology mentions. It
is a set of claims about results, and the results are what a reader is
actually looking for.

This module extracts the two things a rule can honestly extract from a
sentence: **a quantity**, and **a subject**.

Quantities
----------

Four shapes are recognised, because four shapes cover most of what people
write:

* a **percentage** -- "reduced latency by 80%", "improved accuracy by 12%";
* a **multiple** -- "3x faster", "2 times more requests";
* a **currency amount** -- "saved $2M", "£400k of infrastructure spend";
* a **count** -- "400,000 rows", "12,000 requests per second";
* a **duration** -- "saved 10 hours a week", "cut two days off deploy time".

Subject
-------

A sentence is **individual** when it says "I", "my" or "me"; **team** when it
says "we", "our" or "us"; and **unattributed** otherwise. This is a first
person pronoun, not a semantic judgement: "We reduced latency by 80%" is
attributed to the team, and the system is not claiming to know who in the
team did the work — only that the candidate was part of it.

What this module does *not* do
------------------------------

It does not judge whether an achievement was impressive, and it does not feed
the score. The engine still matches declared skills against weighted
requirements. What this produces is **context for the user**: a panel on the
confirmation screen that says "here is what the document claims you
achieved, and here is whether it reads as yours or the team's" — so that the
user can confirm or reject it, in the same way they confirm or reject a
detected skill.

That is the same bargain the rest of the CV pipeline makes: the extraction
proposes, the user disposes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: The units a quantity can be measured in.
UNITS: Final = ("percent", "multiple", "currency", "count", "duration")

#: The directions a result can point in.
DIRECTIONS: Final = ("increase", "decrease", "neutral")

#: Who a sentence says did the work.
ATTRIBUTIONS: Final = ("individual", "team", "unattributed")

#: How a sentence is split into statements. A bullet or a line is a
#: statement; two sentences on one line are two statements.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

#: The bullet markers a CV line may start with.
_BULLET = re.compile(r"^\s*[-•*▪–—·‣]+\s*")

#: A percentage: "80%", "80 per cent", "80 percent".
_PERCENT = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:%|percent\b|per\s*cent\b)",
    re.IGNORECASE,
)

#: A multiple: "3x", "3 x", "3 times faster", "3-fold".
_MULTIPLE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:x\b|times\b|fold\b)",
    re.IGNORECASE,
)

#: A currency amount: "$2M", "£400k", "2 million dollars".
_CURRENCY = re.compile(
    r"(?P<symbol>[$£€₹])\s?(?P<value>\d+(?:[.,]\d+)?)\s*"
    r"(?P<scale>[kKmMbB]|thousand|million|billion)?",
)

#: A count: "400,000 rows", "12000 users".
_COUNT = re.compile(
    r"(?P<value>\d[\d,]*)\s+"
    r"(?P<unit>rows?|records?|users?|customers?|requests?|queries|"
    r"lines? of code|people|students?|patients?|orders?|transactions?|"
    r"documents?|files?|models?|features?|endpoints?|services?|teams?|"
    r"emails?|tickets?|articles?|posts?|sessions?|events?|transactions)",
    re.IGNORECASE,
)

#: A duration: "10 hours a week", "2 days", "three weeks".
_DURATION = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>hours?|days?|weeks?|months?|minutes?|seconds?)",
    re.IGNORECASE,
)

#: The words that say a number went down. "Cut latency by 80%" is an
#: improvement, even though the number fell.
_DECREASE_VERBS = frozenset(
    {
        "cut",
        "cuts",
        "reduced",
        "reduce",
        "reduces",
        "lowered",
        "lower",
        "lowers",
        "decreased",
        "decrease",
        "halved",
        "halve",
        "eliminated",
        "eliminate",
        "saved",
        "save",
        "saves",
        "dropped",
        "drop",
        "drops",
        "shortened",
        "shorten",
    }
)

#: The words that say a number went up. "Handled 12,000 requests" is not in
#: here: handling a volume is an action, not a direction.
_INCREASE_VERBS = frozenset(
    {
        "increased",
        "increase",
        "increases",
        "raised",
        "raise",
        "raises",
        "grew",
        "grow",
        "grows",
        "boosted",
        "boost",
        "boosts",
        "improved",
        "improve",
        "improves",
        "accelerated",
        "accelerate",
        "doubled",
        "double",
        "tripled",
        "triple",
        "scaled",
    }
)

#: The first person pronouns. "I built it" is the candidate's own work.
_INDIVIDUAL_PRONOUNS = frozenset({"i", "i'm", "i've", "me", "my", "mine", "myself"})

#: The plural pronouns. "We built it" is the team's work.
_TEAM_PRONOUNS = frozenset(
    {"we", "we're", "we've", "us", "our", "ours", "ourselves", "team", "our team"}
)

#: A word that says the number fell, used when the verb is ambiguous.
_DOWN_WORDS = frozenset(
    {"down", "lower", "less", "fewer", "decrease", "reduced", "cut"}
)


@dataclass(frozen=True, slots=True)
class Achievement:
    """One quantified claim, and who the claim is about."""

    #: The sentence the claim was read from, with the bullet marker removed.
    text: str
    #: The quantity, as it was written: "80%", "3x", "$2M", "400,000 rows".
    metric: str
    #: The numeric part of the quantity, or ``None`` when there is not one.
    value: float | None
    #: What the quantity measures.
    unit: str
    #: Whether the number went up, went down, or neither.
    direction: str
    #: Whether the sentence reads as the candidate's own work.
    attribution: str

    @property
    def is_quantified(self) -> bool:
        """Always true. A claim without a number is not an achievement here."""
        return self.value is not None


@dataclass(frozen=True, slots=True)
class AchievementSummary:
    """The shape of a document's achievements."""

    total: int = 0
    quantified: int = 0
    individual: int = 0
    team: int = 0
    unattributed: int = 0
    improvements: int = 0
    reductions: int = 0
    largest_percent: float | None = None
    largest_multiple: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "quantified": self.quantified,
            "individual": self.individual,
            "team": self.team,
            "unattributed": self.unattributed,
            "improvements": self.improvements,
            "reductions": self.reductions,
            "largest_percent": self.largest_percent,
            "largest_multiple": self.largest_multiple,
        }


def _statements(text: str) -> list[str]:
    """The text split into statements, with bullet markers removed."""
    statements: list[str] = []
    for raw in _SENTENCE_SPLIT.split(text or ""):
        cleaned = _BULLET.sub("", raw).strip()
        if cleaned:
            statements.append(cleaned)
    return statements


def _numbers_in(statement: str) -> list[tuple[str, float | None, str]]:
    """Every quantity in a statement, as ``(metric, value, unit)``."""
    found: list[tuple[str, float | None, str]] = []

    for match in _PERCENT.finditer(statement):
        found.append((match.group(0), float(match.group("value")), "percent"))

    for match in _MULTIPLE.finditer(statement):
        found.append((match.group(0), float(match.group("value")), "multiple"))

    for match in _CURRENCY.finditer(statement):
        value = float(match.group("value").replace(",", ""))
        scale = (match.group("scale") or "").lower()
        if scale in {"k", "thousand"}:
            value *= 1_000
        elif scale in {"m", "million"}:
            value *= 1_000_000
        elif scale in {"b", "billion"}:
            value *= 1_000_000_000
        found.append((match.group(0).strip(), value, "currency"))

    for match in _COUNT.finditer(statement):
        value = float(match.group("value").replace(",", ""))
        found.append((match.group(0), value, "count"))

    for match in _DURATION.finditer(statement):
        found.append((match.group(0), float(match.group("value")), "duration"))

    return found


def _direction(statement: str) -> str:
    """Whether the statement's number went up or down.

    The verb decides, not the number: "reduced latency by 80%" is an
    improvement, so the direction recorded is ``decrease`` -- which is what
    the *quantity* did -- while the summary counts it as an improvement.
    """
    words = set(re.findall(r"[a-z']+", statement.casefold()))
    if words & _DECREASE_VERBS:
        return "decrease"
    if words & _INCREASE_VERBS:
        return "increase"
    if words & _DOWN_WORDS:
        return "decrease"
    return "neutral"


def _attribution(statement: str) -> str:
    """Whether the statement reads as the candidate's own work."""
    words = re.findall(r"[a-z']+", statement.casefold())
    if any(word in _INDIVIDUAL_PRONOUNS for word in words):
        return "individual"
    if any(word in _TEAM_PRONOUNS for word in words):
        return "team"
    return "unattributed"


def extract_achievements(text: str) -> tuple[Achievement, ...]:
    """Every quantified claim in ``text``, in the order it appears.

    A statement with more than one quantity produces one achievement per
    quantity, because "cut latency by 80% and saved $200k a month" makes two
    claims.
    """
    achievements: list[Achievement] = []
    for statement in _statements(text):
        quantities = _numbers_in(statement)
        if not quantities:
            continue
        direction = _direction(statement)
        attribution = _attribution(statement)
        for metric, value, unit in quantities:
            achievements.append(
                Achievement(
                    text=statement,
                    metric=metric,
                    value=value,
                    unit=unit,
                    direction=direction,
                    attribution=attribution,
                )
            )
    return tuple(achievements)


def summarise(achievements: tuple[Achievement, ...]) -> AchievementSummary:
    """The shape of a document's achievements."""
    percents = [
        a.value for a in achievements if a.unit == "percent" and a.value is not None
    ]
    multiples = [
        a.value for a in achievements if a.unit == "multiple" and a.value is not None
    ]
    return AchievementSummary(
        total=len(achievements),
        quantified=sum(1 for a in achievements if a.value is not None),
        individual=sum(1 for a in achievements if a.attribution == "individual"),
        team=sum(1 for a in achievements if a.attribution == "team"),
        unattributed=sum(1 for a in achievements if a.attribution == "unattributed"),
        # A reduction is an improvement when the thing that fell was a cost.
        # The extractor does not know which; a CV that says "reduced churn" and
        # one that says "reduced revenue" are the same sentence to a rule.
        improvements=sum(
            1
            for a in achievements
            if (a.direction == "decrease" and a.unit in {"percent", "duration", "currency"})
            or a.direction == "increase"
        ),
        reductions=sum(
            1
            for a in achievements
            if a.direction == "decrease" and a.unit in {"count", "multiple"}
        ),
        largest_percent=max(percents) if percents else None,
        largest_multiple=max(multiples) if multiples else None,
    )


__all__ = [
    "ATTRIBUTIONS",
    "DIRECTIONS",
    "UNITS",
    "Achievement",
    "AchievementSummary",
    "extract_achievements",
    "summarise",
]
