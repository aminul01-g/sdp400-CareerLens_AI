"""Skill extraction from raw CV text using spaCy phrase matching.

The design point is **phrase matching against a curated taxonomy rather than
substring search**. Substring search cannot tell ``Java`` inside ``JavaScript``
from the Java language, nor ``Go`` inside ``MongoDB`` from Go — the two failures
that make a naive keyword matcher look competent in a demo and useless in
production. spaCy tokenises first, so ``JavaScript`` is one token and the
``Java`` pattern cannot fire inside it. ``tests/test_extractor.py`` asserts both
cases.

Why the tokenizer model barely matters: only ``PhraseMatcher`` is used, and
``PhraseMatcher`` operates on the token stream. A blank English pipeline would
match identically (plan risk R6).
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING

from app.ml.cv_sections import Section, section_for_offset, split_sections
from app.ml.taxonomy import Taxonomy, load, normalise_surface
from app.ml.types import DetectedSkill

logger = logging.getLogger("app.ml.extractor")

_SPACY_MODEL = "en_core_web_sm"

# Decorations that surround a skill mention in a real CV bullet list.
_BULLET_PREFIX = re.compile(r"^[\s\-\u2022\u2023\u25aa\u25cf\*\u00b7\u2013\u2014o]+\s*")
_TRAILING_PUNCT = ".,;:!?)]}\"'`"

# ---------------------------------------------------------------------------
# Context gate for short, ambiguous skill names
# ---------------------------------------------------------------------------
# A one- or two-character name is a different problem from a multi-character one.
# spaCy's tokenizer already protects us from the substring failures the plan
# cares about ("Java" cannot fire inside "JavaScript"; "Go" cannot fire inside
# "MongoDB"), but it cannot protect us from a *standalone* token: "R&D budget"
# tokenises as ["R", "&", "D", "budget"], so a bare "R" pattern matches a
# finance sentence.
#
# Requiring neighbouring list context fixes that without a stop-list. A genuine
# CV writes "Languages: Go, Rust" or "R, Python, SQL" — a bare "R" inside a
# skills list is always adjacent to a separator or a language cue. A bare "R" in
# prose is not. The gate therefore accepts a short skill only when a neighbour
# token looks like enumeration.
#
# Distinctive aliases ("golang", "rstudio", "ansi c") are never gated, so a
# developer who spells the language out is unaffected either way.
CONTEXT_GATED_SKILLS: frozenset[str] = frozenset({"r", "c", "go"})

_LIST_CUE_TOKENS: frozenset[str] = frozenset(
    {
        # Separators and enumerators only. Hyphens and dashes are deliberately
        # absent: they introduce compounds such as "C-suite" and "front-end",
        # which must not read as a language name.
        ",", "/", ";", "+", "and", "or",
        # language / stack cues
        "language", "languages", "lang", "stack", "tech", "technologies",
        "programming", "scripting", "using", "with", "in", "experience",
        "proficient", "skills", "tools", "framework", "frameworks",
        # cue ":"
        ":", "= ",
    }
)

# "R" / "C" in a two-letter language name is legitimate; "&" and "x" are not.
_AMBIGUOUS_NEIGHBOURS: frozenset[str] = frozenset({"&", "x"})


def _blank_pipeline():
    """Load the English pipeline, falling back to a blank one.

    The blank fallback exists because ``PhraseMatcher`` only needs a tokenizer
    and a vocab — no statistical model. That makes the extractor resilient to a
    missing model download without changing any behaviour.
    """
    import spacy

    try:
        return spacy.load(_SPACY_MODEL)
    except OSError:
        logger.warning(
            "spaCy model %s unavailable; using spacy.blank('en'). "
            "PhraseMatcher does not require a statistical model, so extraction "
            "quality is unaffected.",
            _SPACY_MODEL,
        )
        return spacy.blank("en")


@lru_cache(maxsize=1)
def get_nlp():
    return _blank_pipeline()


@lru_cache(maxsize=1)
def get_matcher() -> tuple[PhraseMatcher, Taxonomy]:
    """Build the ``PhraseMatcher`` once per process.

    The 9.9 performance budget allows 500 ms for this; at 1,016 patterns it
    costs a few milliseconds, so building it per request would be pure waste.
    """
    from spacy.matcher import PhraseMatcher

    taxonomy = load()
    nlp = get_nlp()
    # attr="LOWER" makes every pattern case-insensitive, which is what lets
    # "sklearn", "SKLearn" and "Scikit-learn" all resolve.
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = taxonomy.all_patterns()
    matcher.add("SKILL", [nlp.make_doc(pattern) for pattern in patterns])
    logger.info("PhraseMatcher built with %d patterns", len(patterns))
    return matcher, taxonomy


def _clean_surface(token_text: str) -> str:
    """Strip bullet characters and trailing punctuation from a matched phrase."""
    cleaned = _BULLET_PREFIX.sub("", token_text)
    return cleaned.rstrip(_TRAILING_PUNCT).strip()


def _has_list_context(doc, start: int, end: int) -> bool:
    """Is the span at ``[start, end)`` adjacent to enumeration or a language cue?

    Used only for :data:`CONTEXT_GATED_SKILLS`. A bare one- or two-character
    token is only accepted when a neighbouring token says "this is a list of
    technologies" — otherwise "R&D" and "C-suite" would register as the R and C
    languages.
    """
    candidates: list[str] = []
    for index in (start - 1, end, end + 1):
        if 0 <= index < len(doc):
            candidates.append(doc[index].text.lower().strip())
    for token in candidates:
        if token in _AMBIGUOUS_NEIGHBOURS:
            continue
        if token in _LIST_CUE_TOKENS:
            return True
    return False


if TYPE_CHECKING:  # pragma: no cover - typing only
    from spacy.matcher import PhraseMatcher

    from app.ml.taxonomy import SkillEntry


def extract_skills(
    text: str,
    *,
    taxonomy: Taxonomy | None = None,
    sections: list[Section] | None = None,
) -> list[DetectedSkill]:
    """Find every taxonomy skill mentioned in ``text``.

    Returns skills de-duplicated by id, sorted by descending occurrence count then
    by name so the ordering is deterministic.

    Note the deliberately asymmetric overlap rule: when two patterns match
    overlapping spans (an alias and its own canonical name), the **longer** match
    wins, because it carries more specific information. Short matches fully
    contained in a longer match are discarded.

    ``sections`` is the document's section structure, as produced by
    :func:`app.ml.cv_sections.split_sections`. When it is not supplied the
    sections are computed here, which costs a little time but keeps the
    caller's life simple. Each detection records the section it was found in,
    and whether that section is one where the person *declares* their skills.
    """
    if not text or not text.strip():
        return []

    matcher, default_taxonomy = get_matcher()
    resolved_taxonomy = taxonomy or default_taxonomy
    nlp = get_nlp()
    doc = nlp(text)

    matches = matcher(doc)
    if not matches:
        return []

    # Resolve each match to (start_char, end_char, entry, surface).
    resolved: list[tuple[int, int, SkillEntry, str]] = []
    for _match_id, start, end in matches:
        span = doc[start:end]
        surface = _clean_surface(span.text)
        if not surface:
            continue
        entry = resolved_taxonomy.canonicalise(surface)
        if entry is None:
            # The pattern came from the taxonomy, so this should be unreachable;
            # if it ever fires, the log is the signal that the two indexes drifted.
            logger.debug("Unresolvable taxonomy pattern matched: %r", surface)
            continue
        if entry.slug in CONTEXT_GATED_SKILLS and not _has_list_context(doc, start, end):
            logger.debug(
                "Skipped context-gated skill %r at token %d (no list context)", surface, start
            )
            continue
        resolved.append((span.start_char, span.end_char, entry, surface))

    # Prefer longer spans, then earlier spans, so "scikit learn" beats "scikit".
    resolved.sort(key=lambda item: (-(item[1] - item[0]), item[0], item[3]))

    kept: list[tuple[int, int, SkillEntry, str]] = []
    for candidate in resolved:
        start, end, _entry, _surface = candidate
        # Discard a match contained inside one we already kept.
        if any(
            start >= k_start and end <= k_end and (end - start) < (k_end - k_start)
            for k_start, k_end, _, _ in kept
        ):
            continue
        kept.append(candidate)

    # Aggregate by skill id.
    aggregated: dict[int, dict] = {}
    for start, end, entry, surface in kept:
        record = aggregated.get(entry.skill_id)
        if record is None:
            aggregated[entry.skill_id] = {
                "entry": entry,
                "surface": surface,
                "count": 1,
                "start": start,
                "end": end,
            }
        else:
            record["count"] += 1
            # Keep the most descriptive surface form seen, preferring longer.
            if len(surface) > len(record["surface"]):
                record["surface"] = surface

    if sections is None:
        sections = split_sections(text)

    results = [
        DetectedSkill(
            skill_id=record["entry"].skill_id,
            canonical_name=record["entry"].name,
            slug=record["entry"].slug,
            category=record["entry"].category,
            surface_form=record["surface"],
            occurrence_count=record["count"],
            match_start=record["start"],
            match_end=record["end"],
            section=_section_kind_at(sections, record["start"]),
            is_declared=_is_declared_at(sections, record["start"]),
        )
        for record in aggregated.values()
    ]
    results.sort(key=lambda item: (-item.occurrence_count, item.canonical_name))
    logger.info(
        "Extracted %d skills from %d characters of text", len(results), len(text)
    )
    return results


def _section_kind_at(sections: list[Section], offset: int) -> str:
    """The kind of the section containing a character offset."""
    section = section_for_offset(sections, offset)
    return section.kind if section is not None else ""


def _is_declared_at(sections: list[Section], offset: int) -> bool:
    """Whether a character offset falls inside a section where skills are declared."""
    section = section_for_offset(sections, offset)
    return section is not None and section.is_declared_skills


def extract_skill_slugs(text: str) -> list[str]:
    """Convenience wrapper returning just the canonical slugs."""
    return [skill.slug for skill in extract_skills(text)]


__all__ = [
    "DetectedSkill",
    "extract_skill_slugs",
    "extract_skills",
    "get_matcher",
    "get_nlp",
    "normalise_surface",
]
