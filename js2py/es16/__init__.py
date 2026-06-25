"""ES16 (ES2025) support: RegExp.escape, Promise.try, JSON rawJSON."""

import re

_ES16_SYNTAX_RE = re.compile(
    r'(?:'
    r'\bRegExp\.escape\s*\(|'
    r'\bPromise\.try\s*\(|'
    r'\bJSON\.rawJSON\s*\(|'
    r'\bJSON\.isRawJSON\s*\('
    r')',
    re.MULTILINE)


def looks_like_es16(code):
    """Return True if source likely contains ES16 syntax or APIs."""
    return bool(_ES16_SYNTAX_RE.search(code))


def prepare_es16(code):
    """Apply ES2025 source transforms before translation."""
    return code
