"""A provider key must never be in a file git tracks.

The credential belongs in the environment: ``backend/.env`` locally, the
deployment's encrypted environment variables in production. A key pasted into
a source file is committed, pushed and published with the code, and this
repository is public.

The failure is silent and the consequence is not: the application keeps
working perfectly, the tests keep passing, and the key is simply in the
repository. So it is checked, in the test suite as well as in
``scripts/verify_compliance.py``, because the two run in different places
and a check that only runs in one of them is a check that is sometimes
skipped.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The shape of a provider credential. The prefixes are the two this project
#: uses: Groq for inference, Render for deployment.
KEY_PATTERN = re.compile(r"\bgsk_[A-Za-z0-9_\-]{16,}|\brnd_[A-Za-z0-9_\-]{16,}")

#: Files that are not text, or that are generated, and so are skipped.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".woff2"}


def _tracked_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_no_tracked_file_contains_a_provider_key() -> None:
    """The check that would have caught a pasted-in key before it was pushed."""
    offenders: list[str] = []
    for name in _tracked_files():
        path = REPO_ROOT / name
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(body.splitlines(), start=1):
            if KEY_PATTERN.search(line):
                offenders.append(f"{name}:{lineno}")
    assert not offenders, (
        "a provider key is in a tracked file, which means it is in the "
        f"repository: {offenders}. Move it to the environment — backend/.env "
        "locally, the deployment's environment variables in production — and "
        "rotate the key, because it has been committed."
    )


def test_the_configuration_default_is_empty() -> None:
    """The default in the settings must be empty.

    A default is a value that ships to every deployment that does not
    override it, so a credential must never be one.
    """
    from app.core.config import Settings

    assert Settings.model_fields["groq_api_key"].default == ""
    assert Settings.model_fields["llm_api_key"].default == ""


def test_the_key_is_read_from_the_environment_not_the_source() -> None:
    """``backend/.env`` is where the key lives, and it is not tracked."""
    ignored = subprocess.run(
        ["git", "check-ignore", "backend/.env"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ignored.returncode == 0, "backend/.env is not gitignored"

    tracked = _tracked_files()
    assert "backend/.env" not in tracked


@pytest.mark.parametrize("variable", ["GROQ_API_KEY", "GROQ_MODEL"])
def test_the_environment_template_documents_the_variable(variable: str) -> None:
    """A deployment has to be able to find out what to set."""
    template = (REPO_ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    assert variable in template
