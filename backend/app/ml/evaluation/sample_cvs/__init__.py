"""Committed CV fixtures for the end-to-end extraction test.

Fully synthetic. The names, employers and dates are invented, and every address
uses the ``example.invalid`` domain reserved by RFC 2606, so nothing here can
resolve to a real person or a real mailbox. Regenerate with
``scripts/make_sample_cvs.py``.
"""

from pathlib import Path

SAMPLE_CV_DIR = Path(__file__).parent

__all__ = ["SAMPLE_CV_DIR"]
