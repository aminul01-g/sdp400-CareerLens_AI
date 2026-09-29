"""PDF / DOCX to plain text.

Deliberately **no OCR**. Proposal section 11 lists OCR as out of scope, so a
scanned, image-only PDF raises :class:`ScannedDocumentError` and the route returns
``422`` with a clear message. Silently returning zero skills would be the worst
outcome: the user would conclude the system had read their CV and found nothing,
which is both wrong and undiscoverable.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("app.ml.text_loader")

#: A document yielding fewer characters than this is treated as image-only.
#: 50 is chosen so a genuinely short CV (name, email, one skill line) is not
#: rejected, while any real page of prose comfortably clears it.
MIN_EXTRACTABLE_CHARS = 50

MAX_EXTRACT_BYTES = 5 * 1024 * 1024

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class DocumentTooLargeError(Exception):
    """The file exceeds the configured size limit."""


class UnsupportedDocumentError(Exception):
    """The extension or content type is not supported."""


class ExtractionFailedError(Exception):
    """The file was the right type but could not be parsed."""


class ScannedDocumentError(Exception):
    """The PDF appears to be image-only.

    OCR is explicitly out of scope (proposal section 11). The message is written
    for the end user, because it is surfaced verbatim in the API response.
    """

    def __init__(self, extracted_chars: int) -> None:
        super().__init__(
            "This PDF appears to be a scanned image rather than selectable text "
            f"(only {extracted_chars} characters could be read). CareerLens AI does not "
            "perform OCR, so the text of a scanned CV cannot be analysed. Please upload "
            "a text-based PDF or a DOCX file, or add your skills manually."
        )
        self.extracted_chars = extracted_chars


def _extract_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise ExtractionFailedError("pdfplumber is not installed.") from exc

    pages: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
    except ScannedDocumentError:
        raise
    except Exception as exc:
        logger.warning("pdfplumber failed on %s: %s", path.name, exc, extra={"kind": "cv_extract"})
        raise ExtractionFailedError("The PDF could not be parsed.") from exc
    return "\n".join(pages)


def _extract_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise ExtractionFailedError("python-docx is not installed.") from exc

    try:
        document = docx.Document(str(path))
    except Exception as exc:
        logger.warning("python-docx failed on %s: %s", path.name, exc, extra={"kind": "cv_extract"})
        raise ExtractionFailedError("The DOCX file could not be parsed.") from exc

    blocks: list[str] = [paragraph.text for paragraph in document.paragraphs]
    # Tables hold most of the structure in a formatted CV, and skipping them loses
    # a large fraction of the content.
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
            if cells:
                blocks.append(" | ".join(cells))
    return "\n".join(blocks)


def normalise_text(raw: str) -> str:
    """Flatten a document into a single line-per-block form.

    Newlines are kept (they are useful context for the caller) but runs of spaces
    and tabs collapse, and stray non-breaking spaces from PDF extraction — a
    common source of "why did my skill not match" — are removed.
    """
    if not raw:
        return ""
    import re

    cleaned = raw.replace("\xa0", " ").replace("", "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_text(
    path: str | Path,
    content_type: str | None = None,
    *,
    max_bytes: int = MAX_EXTRACT_BYTES,
) -> str:
    """Extract plain text from a stored upload.

    Args:
        path: Location on disk.
        content_type: The declared MIME type. Used to choose the parser, with the
            extension as a fallback.
        max_bytes: Reject larger files before reading them.

    Returns:
        Normalised plain text.

    Raises:
        DocumentTooLargeError, UnsupportedDocumentError, ExtractionFailedError,
        ScannedDocumentError
    """
    file_path = Path(path)
    if not file_path.exists():
        raise ExtractionFailedError("The uploaded file is missing from storage.")

    size = file_path.stat().st_size
    if size > max_bytes:
        raise DocumentTooLargeError(
            f"The file is {size} bytes; the limit is {max_bytes} bytes."
        )

    extension = file_path.suffix.lower()
    declared = (content_type or "").split(";")[0].strip().lower()

    if extension == ".pdf" or declared == PDF_CONTENT_TYPE:
        text = _extract_pdf(file_path)
    elif extension == ".docx" or declared == DOCX_CONTENT_TYPE:
        text = _extract_docx(file_path)
    else:
        raise UnsupportedDocumentError(
            f"Unsupported file type '{extension or declared}'. Upload a PDF or DOCX file."
        )

    normalised = normalise_text(text)
    if len(normalised) < MIN_EXTRACTABLE_CHARS:
        raise ScannedDocumentError(len(normalised))
    return normalised


def page_count(path: str | Path) -> int | None:
    """Best-effort page count for PDFs. ``None`` for DOCX."""
    file_path = Path(path)
    if file_path.suffix.lower() != ".pdf":
        return None
    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception:  # pragma: no cover - purely informational
        return None
