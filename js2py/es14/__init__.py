"""ES14 (ES2023) support: hashbang comments and findLast APIs."""

import re

_ES14_SYNTAX_RE = re.compile(
    r'(?:'
    r'^#!|'
    r'\.findLast\s*\(|'
    r'\.findLastIndex\s*\('
    r')',
    re.MULTILINE)


def looks_like_es14(code):
    """Return True if source likely contains ES14 syntax or APIs."""
    if code.startswith('#!'):
        return True
    return bool(_ES14_SYNTAX_RE.search(code))


def prepare_es14(code):
    """Apply ES2023 source transforms before translation."""
    if code.startswith('#!'):
        newline = code.find('\n')
        if newline >= 0:
            code = code[newline + 1:]
        else:
            code = ''
    return code
