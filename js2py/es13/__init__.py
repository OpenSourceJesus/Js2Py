"""ES13 (ES2022) support: at() and Object.hasOwn detection."""

import re

_ES13_SYNTAX_RE = re.compile(
    r'(?:'
    r'\.at\s*\(|'
    r'\bObject\.hasOwn\s*\('
    r')',
    re.MULTILINE)


def looks_like_es13(code):
    """Return True if source likely contains ES13 syntax or APIs."""
    return bool(_ES13_SYNTAX_RE.search(code))


def prepare_es13(code):
    """Apply ES2022 source transforms before translation."""
    return code
