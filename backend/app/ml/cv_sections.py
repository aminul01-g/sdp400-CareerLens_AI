"""Finding the sections of a CV.

``docs/limitations.md`` used to say the extractor "is a phrase matcher over the
whole document. It cannot tell a skill listed under 'Skills' from the same word
inside a sentence describing something else."

That is a real difference, and it is worth making. A CV says "Python" under
**Skills** — that is a claim about the person. The same CV says "we migrated
the Python service" inside a **Project** description — that is a mention, and
it might be the writer's employer doing the work.

This module segments a document into sections so that the two can be told
apart. It is deliberately **rule-based**, not a model:

* A heading is a short line, on its own, that is either a known section name
  or title-cased / upper-cased and short enough to be a heading.
* A known section name is decisive. "Experience" is a section heading
  whatever case it is written in.
* Everything before the first heading is the preamble — the name, the
  contact details and the summary.

Rule-based is the right choice here for the same reason it is used everywhere
else in this project: the output is reproducible, it can be tested against
fixed inputs, and it does not need a model file to be shipped. spaCy's
sentence segmenter is used to decide where a *line* begins and ends, but the
decision about what a line *is* is made by these rules.

The module must not import SQLAlchemy or FastAPI, and neither may anything
else under ``app/ml/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The sections this module recognises, and what they are for.
#:
#: The value is the *kind*, which is what the rest of the system cares about;
#: the key is the heading that introduces it.
SECTION_KINDS: dict[str, str] = {
    "summary": "summary",
    "profile": "summary",
    "objective": "summary",
    "about": "summary",
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "competencies": "skills",
    "technologies": "skills",
    "experience": "experience",
    "work experience": "experience",
    "employment": "experience",
    "employment history": "experience",
    "professional experience": "experience",
    "career history": "experience",
    "work history": "experience",
    "projects": "projects",
    "selected projects": "projects",
    "personal projects": "projects",
    "education": "education",
    "academic background": "education",
    "qualifications": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "awards": "awards",
    "honours": "awards",
    "publications": "publications",
    "languages": "languages",
    "interests": "interests",
    "references": "references",
}

#: The kind used for a heading this module does not recognise.
UNKNOWN_KIND = "other"

#: A heading is short. Anything longer is a sentence, not a heading.
MAX_HEADING_CHARS = 48

#: A heading is short in words, too.
MAX_HEADING_WORDS = 6

#: A heading has no sentence punctuation at the end. "Skills." is still a
#: heading, but "Skills for the team I led." is a sentence.
_TRAILING_PUNCTUATION = " \t:;,.-–—•"

#: A line that is mostly a bullet is a bullet, not a heading.
_BULLET_PREFIXES = ("-", "•", "*", "▪", "–", "—", "·", "‣")


@dataclass(frozen=True, slots=True)
class Section:
    """One section of a document."""

    #: The recognised kind — "skills", "experience", "education", and so on.
    kind: str
    #: The heading that introduced it, or "" for the preamble.
    heading: str
    #: The text of the section, heading excluded.
    text: str
    #: Where the section starts in the original document.
    start: int
    #: Where it ends.
    end: int

    @property
    def is_declared_skills(self) -> bool:
        """Whether this section is where a person *declares* their skills.

        A skill listed under "Skills" is a claim. The same word inside a
        project description is a mention. The distinction is what makes the
        difference between "this person knows Python" and "this person has
        written about Python".
        """
        return self.kind == "skills"


def _normalise_heading(line: str) -> str:
    """A heading reduced to something comparable: lowercase, no decoration."""
    cleaned = line.strip().strip(_TRAILING_PUNCTUATION).strip()
    # "TECHNICAL SKILLS" and "Technical Skills" are the same heading.
    return re.sub(r"\s+", " ", cleaned).casefold()


def _looks_like_a_heading(line: str) -> bool:
    """Whether a line could be a heading at all."""
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_CHARS:
        return False
    if stripped.startswith(_BULLET_PREFIXES):
        return False
    if len(stripped.split()) > MAX_HEADING_WORDS:
        return False
    # A heading does not end a sentence.
    if stripped.endswith((".", "!", "?", ";")):
        return False
    return True


def _heading_kind(line: str) -> str | None:
    """The kind of section a heading introduces, or ``None`` if it is not one.

    A known name is decisive. An unknown name is accepted when the line is
    written like a heading — short, and in title case or capitals — because a
    CV with a "Selected Engagements" section should still have *some*
    structure.
    """
    normalised = _normalise_heading(line)
    if not normalised:
        return None

    known = SECTION_KINDS.get(normalised)
    if known is not None:
        return known

    # A heading with a known word in it: "Technical Skills & Tools" is a
    # skills section.
    for word in normalised.replace("&", " ").replace("/", " ").split():
        if word in SECTION_KINDS and len(word) > 3:
            return SECTION_KINDS[word]

    # An unknown heading is still a heading if it is written like one.
    letters = [char for char in normalised if char.isalpha()]
    if not letters:
        return None
    is_upper = all(char.isupper() for char in letters)
    is_title = normalised == normalised.title() or normalised.istitle()
    if is_upper or is_title:
        return UNKNOWN_KIND
    return None


def split_sections(text: str) -> list[Section]:
    """Split a document into its sections.

    The preamble — everything before the first heading — is returned as a
    section of kind ``"preamble"`` when it is not empty, so the caller can
    tell "no headings at all" from "a document that starts with a heading".
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    # Where each line starts, so the offsets are real offsets into the text.
    offsets: list[int] = []
    running = 0
    for line in lines:
        offsets.append(running)
        running += len(line) + 1  # +1 for the newline that splitlines removed

    sections: list[Section] = []
    current_kind = "preamble"
    current_heading = ""
    current_start = 0
    current_lines: list[str] = []

    def flush(end: int) -> None:
        body = "\n".join(current_lines).strip()
        if body or current_kind != "preamble":
            sections.append(
                Section(
                    kind=current_kind,
                    heading=current_heading,
                    text=body,
                    start=current_start,
                    end=end,
                )
            )

    for index, line in enumerate(lines):
        kind = _heading_kind(line) if _looks_like_a_heading(line) else None
        if kind is None:
            current_lines.append(line)
            continue

        # A heading closes the previous section.
        flush(offsets[index])
        current_kind = kind
        current_heading = line.strip()
        current_start = offsets[index] + len(line) + 1
        current_lines = []

    flush(len(text))
    return sections


def section_for_offset(sections: list[Section], offset: int) -> Section | None:
    """The section containing a character offset."""
    for section in sections:
        if section.start <= offset < section.end:
            return section
    return None


def declared_skills_section(sections: list[Section]) -> Section | None:
    """The section where a person declares their skills, if there is one."""
    for section in sections:
        if section.is_declared_skills:
            return section
    return None


__all__ = [
    "SECTION_KINDS",
    "UNKNOWN_KIND",
    "Section",
    "declared_skills_section",
    "section_for_offset",
    "split_sections",
]
