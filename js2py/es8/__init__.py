"""ES8 (ES2017) support: trailing commas and syntax detection."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES8_SYNTAX_RE = re.compile(
    r'(?:'
    r'\bObject\.values\s*\(|'
    r'\bObject\.entries\s*\(|'
    r'\bObject\.getOwnPropertyDescriptors\s*\(|'
    r'\.padStart\s*\(|'
    r'\.padEnd\s*\(|'
    r'function\s+[^(]*\([^)]*,\s*\)|'   # trailing comma in params
    r'\([^)]*,\s*\)\s*=>'                 # trailing comma in arrow params
    r')',
    re.MULTILINE)


def looks_like_es8(code):
    """Return True if source likely contains ES8 syntax or APIs."""
    return bool(_ES8_SYNTAX_RE.search(code))


def prepare_es8(code):
    """Apply ES2017 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    prev = None
    while prev != masked:
        prev = masked
        masked = re.sub(r',(\s*)\)', r'\1)', masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked
