"""
Mask anything that shouldn't leave the device before a message is sent to
Jev: links (the link checks already ran locally), email addresses, phone
numbers, and bare numbers of four or more digits (one-time codes, account
and card numbers). Money amounts with a currency sign are kept -- they
matter to the judgment and aren't secret.

The placeholder names match the ones the IMC 2025 smishing dataset uses,
so messages from that dataset and freshly masked messages look the same.
"""

import re

from .links import URL_RE

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_PHONE_RE = re.compile(r"(?<![\w£$€])\+?\d[\d \-()]{6,}\d(?!\w)")
_LONG_NUMBER_RE = re.compile(r"(?<![\w£$€.,])\d{4,}(?![\w.,]\d)")


def _mask_url(match: re.Match) -> str:
    url = match.group(0)
    trailing = url[len(url.rstrip(".,;:!?)")):]  # keep sentence punctuation that follows a link
    return "<URL>" + trailing


def mask_for_jev(text: str) -> str:
    text = _EMAIL_RE.sub("<EMAIL_ADDRESS>", text)
    text = URL_RE.sub(_mask_url, text)
    text = _PHONE_RE.sub("<PHONE_NUMBER>", text)
    text = _LONG_NUMBER_RE.sub("<NUMBER>", text)
    return text
