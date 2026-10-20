"""Extracting a work history from a CV.

The limitations document said the extractor produced "a bag of skill mentions
and some text. Nothing else is extracted, so nothing else influences the
score." One of the things worth extracting is *where* somebody has worked,
because that is what makes "years of experience" something other than a number
the user typed.

The extraction is a two-step process, and the second step is the interesting
one:

1. **Find the dates.** A date range is usually written near the employer, in
   a handful of shapes. The patterns below cover the common ones, and a
   recogniser that understands "January 2019 – Present" is more useful than
   one that only understands "2019".
2. **Find the employer.** The employer is the line next to the dates, or the
   text before the dates on the same line.

**The employer is found by rule, not by a named-entity recogniser.** That is
a deliberate change, made after measuring the recogniser:

* ``en_core_web_sm`` tagged "Acme Analytics - Jan 2019 - Present, Senior Data
  Scientist, Globex Ltd" as a single ``ORG`` entity — three employers and two
  date ranges, one organisation.
* On a second attempt it tagged "Globex Ltd" as a ``PERSON``.

A rule is more reliable than that, and it is reproducible: the employer is the
text next to the dates, and the only way to be sure it is not a job title is to
check whether every word in it is a job-title word. "Senior Data Scientist"
is; "Acme Analytics" is not.

Every entry is therefore a **proposal**: an employer, a period, and the raw
text it came from. The user confirms it, and only then does it become part of
the profile.

The module must not import SQLAlchemy or FastAPI, and neither may anything
else under ``app/ml/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

#: Month names, for the date patterns. Both the full and the abbreviated form.
_MONTHS = (
    "january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|"
    "august|aug|september|sep|sept|october|oct|november|nov|december|dec"
)
_MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

#: "January 2019", "Jan 2019", "Jan 2019 - Present", "2019 - 2022",
#: "01/2019 - 06/2021".
_MONTH_YEAR = re.compile(rf"\b(?P<month>{_MONTHS})\.?\s+(?P<year>(?:19|20)\d{{2}})\b", re.I)
_YEAR_RANGE = re.compile(r"\b(?P<start>(?:19|20)\d{2})\s*(?:-|–|—|to|until)\s*(?P<end>(?:19|20)\d{2}|present|current|now|ongoing)\b", re.I)
_MONTH_YEAR_RANGE = re.compile(
    rf"\b(?P<start_month>{_MONTHS})\.?\s+(?P<start_year>(?:19|20)\d{{2}})"
    rf"\s*(?:-|–|—|to|until)\s*"
    rf"(?:(?P<end_month>{_MONTHS})\.?\s+)?(?P<end_year>(?:19|20)\d{{2}}|present|current|now|ongoing)\b",
    re.I,
)
_NUMERIC_RANGE = re.compile(
    r"\b(?P<start_month>\d{1,2})/(?P<start_year>(?:19|20)\d{2})"
    r"\s*(?:-|–|—|to|until)\s*"
    r"(?:(?P<end_month>\d{1,2})/(?P<end_year>(?:19|20)\d{2})|present|current|now|ongoing)\b",
    re.I,
)

#: Words that mark the present tense in a date range.
_PRESENT_WORDS = {"present", "current", "now", "ongoing"}

#: The vocabulary of a job title.
#:
#: A candidate employer is rejected when *every* word in it is one of these,
#: because "Senior Data Scientist" is a title and "Acme Analytics" is not.
#: "Acme" is the word that tells the two apart, which is why this is a
#: vocabulary and not a list of titles.
TITLE_WORDS: frozenset[str] = frozenset(
    {
        "administrator", "analyst", "apprentice", "architect", "assistant",
        "associate", "backend", "business", "cloud", "computer", "consultant",
        "contract", "coordinator", "customer", "data", "developer", "devops",
        "director", "engineer", "executive", "finance", "founder", "freelance",
        "front", "graduate", "head", "human", "intern", "lead", "machine",
        "manager", "marketing", "mobile", "officer", "operations", "partner",
        "platform", "principal", "product", "programmer", "project", "qa",
        "quality", "remote", "research", "researcher", "resources", "sales",
        "scientist", "security", "senior", "site", "software", "specialist",
        "staff", "success", "supervisor", "systems", "trainee", "vision",
        "web",
    }
)

#: The most words a candidate employer may have.
MAX_EMPLOYER_WORDS = 6


@dataclass(frozen=True, slots=True)
class WorkHistoryEntry:
    """One proposed job: who, when, and the text it came from."""

    employer: str
    start_date: date | None = None
    end_date: date | None = None
    #: The raw line or block the entry was read from, so the user can see
    #: what the system thinks it read.
    raw_text: str = ""
    #: Whether the end date is open — "Present", "Current".
    is_current: bool = False

    @property
    def months(self) -> int:
        """How many months the entry covers, when both ends are known.

        Overlapping entries are not de-duplicated here: a person who held two
        roles at once has, in a sense, more experience than the calendar
        shows. The service layer is the right place to reason about that, and
        it does.
        """
        if self.start_date is None:
            return 0
        end = self.end_date
        if end is None:
            return 0
        months = (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)
        return max(0, months)


def _month_number(name: str) -> int | None:
    return _MONTH_NUMBERS.get(name.casefold().rstrip("."))


def _safe_date(year: int, month: int | None) -> date | None:
    if year < 1900 or year > 2100:
        return None
    if month is None:
        month = 1
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def parse_date_range(text: str) -> tuple[date | None, date | None, bool]:
    """Find a date range in a line of text.

    Returns ``(start, end, is_current)``. A start with no end means the range
    is still open; ``is_current`` says whether the text said so explicitly.
    """
    if not text:
        return None, None, False

    match = _MONTH_YEAR_RANGE.search(text)
    if match:
        start = _safe_date(
            int(match.group("start_year")), _month_number(match.group("start_month"))
        )
        end_group = match.group("end_year")
        if end_group and end_group.casefold() in _PRESENT_WORDS:
            return start, None, True
        end = _safe_date(
            int(end_group), _month_number(match.group("end_month"))
        ) if end_group else None
        if end is None and end_group:
            end = _safe_date(int(end_group), None)
        return start, end, False

    match = _NUMERIC_RANGE.search(text)
    if match:
        start = _safe_date(
            int(match.group("start_year")), int(match.group("start_month"))
        )
        end_group = match.group("end_year")
        if end_group and end_group.casefold() in _PRESENT_WORDS:
            return start, None, True
        end = (
            _safe_date(int(end_group), int(match.group("end_month")))
            if end_group
            else None
        )
        return start, end, False

    match = _YEAR_RANGE.search(text)
    if match:
        start = _safe_date(int(match.group("start")), 1)
        end_group = match.group("end")
        if end_group.casefold() in _PRESENT_WORDS:
            return start, None, True
        end = _safe_date(int(end_group), 1)
        return start, end, False

    # A single month and year: the start of something, with no end in sight.
    match = _MONTH_YEAR.search(text)
    if match:
        start = _safe_date(
            int(match.group("year")), _month_number(match.group("month"))
        )
        return start, None, False

    return None, None, False


#: Separators that mark the end of a name and the start of something else.
_EMPLOYER_CUT = re.compile(r"\s+[-–—|]\s+")


def _has_date(text: str) -> bool:
    """Whether a line contains anything that reads as a date."""
    for pattern in (_MONTH_YEAR_RANGE, _YEAR_RANGE, _NUMERIC_RANGE, _MONTH_YEAR):
        if pattern.search(text) is not None:
            return True
    return False


def _looks_like_a_job_title(text: str) -> bool:
    """Whether a line is a job title rather than an employer.

    A title is made entirely of title words: "Senior Data Scientist" is a
    title, "Acme Analytics" is not, because "Acme" is not a title word.
    """
    words = [word for word in re.split(r"[^\w]+", text.casefold()) if word]
    if not words:
        return False
    return all(word in TITLE_WORDS for word in words)


def _plausible_employer(text: str) -> str | None:
    """The text as an employer name, or ``None`` if it cannot be one."""
    cleaned = text.strip(" \n\t,;:.()[]-–—")
    if not cleaned:
        return None
    words = cleaned.split()
    if len(words) > MAX_EMPLOYER_WORDS:
        return None
    if not cleaned[0].isupper():
        return None
    if _looks_like_a_job_title(cleaned):
        return None
    if _has_date(cleaned):
        return None
    return cleaned


def _employer_near(lines: list[str], date_index: int, date_line: str) -> str | None:
    """Find the employer for a block whose dates are on ``lines[date_index]``.

    Two layouts are handled:

    * the employer is on the same line, before the dates —
      ``Acme Analytics - Jan 2019 - Present``;
    * the employer is on a line above, with the job title in between —
      ``Acme Corp`` / ``Senior Data Scientist`` / ``Jan 2019 - Present``.
    """
    # The text before the dates on the date line.
    for pattern in (_MONTH_YEAR_RANGE, _YEAR_RANGE, _NUMERIC_RANGE, _MONTH_YEAR):
        found = pattern.search(date_line)
        if found is not None:
            before = date_line[: found.start()]
            candidate = _plausible_employer(before)
            if candidate is not None:
                return candidate
            break

    # Otherwise look up the block, skipping job titles on the way.
    for index in range(date_index - 1, max(-1, date_index - 4), -1):
        candidate = _plausible_employer(lines[index])
        if candidate is not None:
            return candidate
    return None


def _blocks(text: str) -> list[str]:
    """Split a section into blocks, one per job.

    A blank line is what separates one job from the next on most CVs. Running
    the recogniser over a whole section at once is what produced the greedy
    "one organisation, three employers" entity; a block at a time is both
    more accurate and easier to reason about.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _looks_like_an_employer(text: str) -> bool:
    """Whether a named entity is plausibly an employer.

    A rule rather than a hope: a person's own name is often tagged as an
    organisation, and so are universities, products and clients. The
    exclusions below are the ones that matter in practice.
    """
    lowered = text.casefold()
    if len(text) < 3 or len(text) > 80:
        return False
    if lowered in {"university", "college", "institute", "school", "ltd", "inc"}:
        return False
    # "Google" is an employer; "Google Cloud" is a product, but it is also
    # the name people put on a CV, so it is kept.
    if lowered.startswith(("the ", "a ", "an ")):
        return False
    return True


def extract_work_history(text: str) -> list[WorkHistoryEntry]:
    """Propose the jobs described in a block of CV text.

    The block should be the *experience* section. Passing the whole document
    finds organisations from every section, which is how a university ends up
    as an employer.

    The result is a list of proposals, ordered by the position they appear in
    the text. Nothing is inferred beyond what is written.
    """
    if not text or not text.strip():
        return []

    entries: list[WorkHistoryEntry] = []
    for block in _blocks(text):
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        # The dates anchor the block. A block without them is not a job.
        date_index = -1
        date_line = ""
        for index, line in enumerate(lines):
            if _has_date(line):
                date_index = index
                date_line = line
                break
        if date_index == -1:
            continue

        start, end, is_current = parse_date_range(date_line)
        if start is None and end is None:
            continue

        employer = _employer_near(lines, date_index, date_line)
        if employer is None:
            continue

        entries.append(
            WorkHistoryEntry(
                employer=employer,
                start_date=start,
                end_date=end,
                raw_text=block.strip(),
                is_current=is_current,
            )
        )

    # One entry per employer: the first mention wins, and a later duplicate
    # does not create a second job.
    seen: set[str] = set()
    unique: list[WorkHistoryEntry] = []
    for entry in entries:
        key = entry.employer.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)

    return unique


def _line_containing(text: str, offset: int) -> str:
    """The line of ``text`` that contains ``offset``."""
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return text[start:end]


def _next_line(text: str, offset: int) -> str:
    """The line of ``text`` after ``offset``."""
    end = text.find("\n", offset)
    if end == -1:
        return ""
    start = end + 1
    end = text.find("\n", start)
    if end == -1:
        end = len(text)
    return text[start:end]


def total_months(entries: list[WorkHistoryEntry], *, today: date | None = None) -> int:
    """The total months covered by a work history.

    Overlapping entries are counted once, by walking the months from the
    earliest start to the latest end and marking which are covered. A person
    who held two roles at once has not gained a year of experience by holding
    two jobs at once.

    ``today`` is the reference date for a role that is still open. It is an
    argument rather than a call to the system clock so that this function
    stays a pure function of its inputs.
    """
    reference = today or date.today()
    spans: list[tuple[date, date]] = []
    for entry in entries:
        if entry.start_date is None:
            continue
        end = entry.end_date
        if end is None:
            if not entry.is_current:
                continue
            end = reference
        if end < entry.start_date:
            continue
        spans.append((entry.start_date, end))

    if not spans:
        return 0

    covered: set[tuple[int, int]] = set()
    for start, end in spans:
        cursor = start
        # The end month is the month the role ended, so it is not covered:
        # January 2019 to January 2021 is twenty-four months, not twenty-five.
        while cursor < end:
            covered.add((cursor.year, cursor.month))
            # Advance one month.
            year, month = cursor.year, cursor.month
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1
            cursor = date(year, month, 1)
    return len(covered)


__all__ = [
    "WorkHistoryEntry",
    "extract_work_history",
    "parse_date_range",
    "total_months",
]
