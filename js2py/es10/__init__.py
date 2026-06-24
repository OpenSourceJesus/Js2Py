"""ES10 (ES2019) support: optional catch binding and syntax detection."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES10_SYNTAX_RE = re.compile(
    r'(?:'
    r'\.flat\s*\(|'
    r'\.flatMap\s*\(|'
    r'\.trimStart\s*\(|'
    r'\.trimEnd\s*\(|'
    r'\bcatch\s*\{'
    r')',
    re.MULTILINE)

_OPTIONAL_CATCH_RE = re.compile(r'\bcatch\s*\{')


def looks_like_es10(code):
    """Return True if source likely contains ES10 syntax or APIs."""
    return bool(_ES10_SYNTAX_RE.search(code))


def prepare_es10(code):
    """Apply ES2019 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _OPTIONAL_CATCH_RE.sub('catch (__PyJsOptionalCatch) {', masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked
