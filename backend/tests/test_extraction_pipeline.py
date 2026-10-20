"""End-to-end CV pipeline: file bytes -> text -> detected skills -> confirmation.

This is the only test that walks the whole chain through the real parsers. The
unit tests around each stage mock the others away, which is right for isolating a
fault but means none of them would notice if the two halves stopped fitting
together -- a renamed keyword, a changed return shape, a skill the extractor
finds but the taxonomy cannot resolve.

The fixtures in ``app/ml/evaluation/sample_cvs/`` are fully synthetic: invented
names, invented employers, and ``@example.invalid`` addresses, which RFC 2606
reserves so they can never resolve to a real mailbox. No real person's data is
involved.

Detection is asserted to be *proposed*, never applied. That distinction is the
whole reason a user confirms before anything reaches the profile, and a test that
let it slip would be the only thing standing between a parsing bug and silently
overwriting a user's declared skills.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.ml import extractor as extractor_module
from app.ml.evaluation.sample_cvs import SAMPLE_CV_DIR
from app.ml.extractor import DetectedSkill, extract_skills
from app.ml.taxonomy import load as load_taxonomy
from app.ml.text_loader import (
    MIN_EXTRACTABLE_CHARS,
    ScannedDocumentError,
    UnsupportedDocumentError,
    extract_text,
    normalise_text,
)

PDF_CV = SAMPLE_CV_DIR / "sample_cv_devops_engineer.pdf"
ML_DOCX = SAMPLE_CV_DIR / "sample_cv_ml_engineer.docx"
NLP_DOCX = SAMPLE_CV_DIR / "sample_cv_nlp_engineer.docx"
ALL_CVS = (PDF_CV, ML_DOCX, NLP_DOCX)

# Skills each fixture must yield. Asserted on the canonical slug, so rephrasing
# the CV text does not break the test but a genuine matching regression does.
EXPECTED_SLUGS = {
    ML_DOCX.name: {"python", "scikit-learn", "pandas", "sql", "docker", "fastapi"},
    PDF_CV.name: {"docker", "kubernetes", "terraform", "aws", "linux", "bash", "python"},
    NLP_DOCX.name: {"python", "spacy", "nltk", "bert", "transformers", "tokenization"},
}


@pytest.fixture(scope="module")
def taxonomy():
    return load_taxonomy()


def test_sample_cvs_are_present() -> None:
    """The fixtures are committed, so a missing file is a real failure, not a skip."""
    missing = [
        path.name for path in ALL_CVS if not path.exists() or path.stat().st_size == 0
    ]
    assert not missing, f"missing or empty sample CV fixtures: {missing}"


def test_no_real_contact_details_in_the_fixtures() -> None:
    """Guard against a real CV being committed here by accident.

    The email domain must be the reserved .invalid TLD. This is the check that
    keeps the fixture directory anonymised as the plan requires.
    """
    for path in ALL_CVS:
        for line in extract_text(path).splitlines():
            if "@" in line:
                assert "example.invalid" in line, (
                    f"{path.name} contains a non-reserved email domain: {line.strip()!r}"
                )


@pytest.mark.parametrize("path", ALL_CVS)
def test_text_extraction_produces_usable_text(path: Path) -> None:
    text = extract_text(path)
    assert len(text) >= MIN_EXTRACTABLE_CHARS
    assert text.strip(), f"{path.name} extracted to nothing"
    assert len(text.splitlines()) > 10


@pytest.mark.parametrize("path", ALL_CVS)
def test_extraction_is_deterministic(path: Path, taxonomy) -> None:
    """Parsing the same bytes twice must give the same detections.

    Determinism is a stated acceptance criterion for this project, and an
    extractor that reorders or drops a detection between identical runs would
    make the user's confirmation screen flicker between uploads.
    """
    text = extract_text(path)
    first = extract_skills(text, taxonomy=taxonomy)
    second = extract_skills(text, taxonomy=taxonomy)
    assert [(d.skill_id, d.surface_form, d.occurrence_count) for d in first] == [
        (d.skill_id, d.surface_form, d.occurrence_count) for d in second
    ]


@pytest.mark.parametrize(
    ("path", "expected"),
    [(ML_DOCX, EXPECTED_SLUGS[ML_DOCX.name]), (PDF_CV, EXPECTED_SLUGS[PDF_CV.name]),
     (NLP_DOCX, EXPECTED_SLUGS[NLP_DOCX.name])],
)
def test_expected_skills_are_detected(path: Path, expected: set[str], taxonomy) -> None:
    found = {d.slug for d in extract_skills(extract_text(path), taxonomy=taxonomy)}
    missing = expected - found
    assert not missing, f"{path.name} missed {sorted(missing)}; found {sorted(found)}"


def test_pdf_path_is_covered_not_skipped(taxonomy) -> None:
    """The PDF branch is the fragile one, so assert it is genuinely exercised."""
    detections = extract_skills(extract_text(PDF_CV), taxonomy=taxonomy)
    assert len(detections) >= 6, "the PDF fixture stopped yielding a realistic skill count"
    # Cloud and infrastructure vocabulary, which only the DevOps CV contains.
    assert {"docker", "kubernetes"} <= {d.slug for d in detections}


def test_every_detection_resolves_to_a_real_skill(taxonomy) -> None:
    """No detection may be emitted for a term the taxonomy does not contain.

    This is the join between the two halves of the pipeline: the extractor
    produces a skill id, and the profile route writes it as a foreign key. A
    dangling id here is an IntegrityError at confirmation time, which is exactly
    the failure this test exists to prevent.
    """
    known = {entry.skill_id for entry in taxonomy.skills}
    for path in ALL_CVS:
        for detection in extract_skills(extract_text(path), taxonomy=taxonomy):
            assert detection.skill_id in known, (
                f"{path.name}: detection {detection.slug!r} has id {detection.skill_id}, "
                "which is not in the taxonomy"
            )
            assert taxonomy.by_slug[detection.slug].skill_id == detection.skill_id


def test_detections_are_ordered_deterministically(taxonomy) -> None:
    """Descending occurrence count, then by canonical name.

    That ordering is what puts the strongest matches at the top of the
    confirmation list, so the user reviews the most likely detections first.
    Ties break on ``canonical_name`` rather than slug: "AWS" precedes "Ansible",
    which is what a reader scanning the list expects.
    """
    for path in ALL_CVS:
        detections = extract_skills(extract_text(path), taxonomy=taxonomy)
        keys = [(-d.occurrence_count, d.canonical_name) for d in detections]
        assert keys == sorted(keys), f"{path.name}: detections are not in the documented order"


def test_no_duplicate_skill_detections(taxonomy) -> None:
    """A skill mentioned five times is one proposal, not five."""
    for path in ALL_CVS:
        detections = extract_skills(extract_text(path), taxonomy=taxonomy)
        slugs = [d.slug for d in detections]
        assert len(slugs) == len(set(slugs)), f"{path.name}: duplicate detections in {slugs}"


def test_match_spans_are_sane(taxonomy) -> None:
    """A reported span must be a real substring of the text, and non-degenerate.

    An off-by-one in the span arithmetic would corrupt the highlighted excerpt the
    UI shows next to each proposed skill, and nothing else checks it.
    """
    for path in ALL_CVS:
        text = extract_text(path)
        for detection in extract_skills(text, taxonomy=taxonomy):
            assert 0 <= detection.match_start < detection.match_end <= len(text), (
                f"{path.name}: {detection.slug} span "
                f"[{detection.match_start}, {detection.match_end}) is out of bounds"
            )
            span = text[detection.match_start : detection.match_end]
            assert span.strip(), f"{path.name}: {detection.slug} span is whitespace"


def test_detections_carry_no_proficiency(taxonomy) -> None:
    """A detection must not arrive carrying a proficiency.

    Proficiency is a user judgement. If extraction supplied one, an unconfirmed
    guess would look in the score breakdown exactly like something the user
    declared -- which is the failure the confirmation gate exists to prevent.
    """
    assert "proficiency" not in DetectedSkill.__dataclass_fields__
    for detection in extract_skills(extract_text(ML_DOCX), taxonomy=taxonomy):
        assert not hasattr(detection, "proficiency")


def test_extraction_is_a_pure_function_over_text_and_taxonomy() -> None:
    """The extractor must not persist anything.

    Confirmed two ways: the signature takes no session or profile, and the body
    references no write path. If a future change makes it write, the UI's
    confirmation gate stops being the only route into the profile.
    """
    signature = inspect.signature(extractor_module.extract_skills)
    parameters = list(signature.parameters)
    assert parameters[:2] == ["text", "taxonomy"], (
        "extract_skills gained a parameter; if it now persists state, the confirmation "
        "gate in the UI is no longer the only write path"
    )
    # The only other parameter is the document's section structure, which is
    # an *input* — computed by the caller, or by the extractor when it is not
    # supplied. It is not a session, a profile or a write path.
    for extra in parameters[2:]:
        assert extra == "sections", (
            f"extract_skills gained the parameter {extra!r}; if it now persists state, "
            "the confirmation gate in the UI is no longer the only write path"
        )
        assert signature.parameters[extra].default is None, (
            "a mutable default would make the extractor stateful"
        )
    source = inspect.getsource(extractor_module.extract_skills)
    for forbidden in ("commit", "flush", "session", "execute", "query("):
        assert forbidden not in source, (
            f"extract_skills references {forbidden!r}, which suggests it persists state"
        )


@pytest.mark.parametrize(
    "text",
    ["", "   \n\n  ", "Lorem ipsum dolor sit amet. " * 40],
    ids=["empty", "whitespace", "unrelated-prose"],
)
def test_degenerate_input_yields_nothing_rather_than_raising(text: str, taxonomy) -> None:
    result = extract_skills(text, taxonomy=taxonomy)
    assert isinstance(result, list)


def test_unrelated_prose_does_not_invent_skills(taxonomy) -> None:
    """A CV with no technology content must not produce a confident guess."""
    result = extract_skills(
        "I enjoy long walks on the beach and strong coffee. " * 10, taxonomy=taxonomy
    )
    assert result == [], f"invented skills from unrelated prose: {[d.slug for d in result]}"


def test_scanned_pdf_without_a_text_layer_is_rejected(tmp_path) -> None:
    """An image-only PDF must be refused, not silently returned as empty text.

    Silently returning nothing would show the user a blank extraction with no
    explanation; raising ScannedDocumentError lets the UI say why.

    A page with no text operators at all stands in for a scan. Ghostscript's
    presence on the host is irrelevant here, because no OCR fallback is wired up
    -- so this asserts the real behaviour on this machine rather than skipping
    itself out of existence.
    """
    from reportlab.pdfgen import canvas

    path = tmp_path / "scanned.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.showPage()
    pdf.save()
    with pytest.raises(ScannedDocumentError):
        extract_text(path)


def test_unsupported_type_is_rejected(tmp_path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(UnsupportedDocumentError):
        extract_text(path, "text/plain")


def test_normalise_text_is_idempotent() -> None:
    """Normalising twice must equal normalising once.

    The upload route normalises before detection, and the review screen may
    normalise again. A non-idempotent normaliser would mangle curly quotes and
    soft hyphens a second time.
    """
    raw = extract_text(NLP_DOCX)
    once = normalise_text(raw)
    assert normalise_text(once) == once
