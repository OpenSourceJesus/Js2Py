"""ES8 (ES2017) support: padStart/padEnd, Object.values/entries, getOwnPropertyDescriptors."""

import re

_ES8_SYNTAX_RE = re.compile(
    r'(?:'
    r'\.padStart\s*\(|'
    r'\.padEnd\s*\(|'
    r'\bObject\.values\s*\(|'
    r'\bObject\.entries\s*\(|'
    r'\bObject\.getOwnPropertyDescriptors\s*\('
    r')',
    re.MULTILINE)


def looks_like_es8(code):
    """Return True if source likely contains ES8 syntax or APIs."""
    return bool(_ES8_SYNTAX_RE.search(code))


def prepare_es8(code):
    """Apply ES2017 source transforms before translation."""
    return code
