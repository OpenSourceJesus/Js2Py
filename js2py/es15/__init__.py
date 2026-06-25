"""ES15 (ES2024) support: groupBy, withResolvers, well-formed strings, sumPrecise."""

import re

_ES15_SYNTAX_RE = re.compile(
    r'(?:'
    r'\bObject\.groupBy\s*\(|'
    r'\bPromise\.withResolvers\s*\(|'
    r'\.isWellFormed\s*\(|'
    r'\.toWellFormed\s*\(|'
    r'\bMath\.sumPrecise\s*\('
    r')',
    re.MULTILINE)


def looks_like_es15(code):
    """Return True if source likely contains ES15 syntax or APIs."""
    return bool(_ES15_SYNTAX_RE.search(code))


def prepare_es15(code):
    """Apply ES2024 source transforms before translation."""
    return code
