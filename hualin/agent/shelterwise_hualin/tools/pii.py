"""Remove personal info before text is embedded, logged or stored."""

from __future__ import annotations

import re

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"),
    (re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"), "[phone]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ssn]"),
    # unit numbers must contain a digit, so "the unit is cold" is untouched
    (re.compile(r"(?:\b(?i:apt|apartment|unit|suite|ste)\b\.?|#)\s*#?\s*[\w-]*\d[\w-]*"), "[unit]"),
    # trigger phrase is case-insensitive, the name itself must be Capitalized
    (re.compile(r"\b((?i:my name is|name is|named|this is))\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?"), r"\1 [name]"),
    (re.compile(r"\b(Mr|Mrs|Ms|Miss|Mx|Dr)\.?\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?"), "[name]"),
]


def scrub(text: str) -> str:
    out = text or ""
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out
