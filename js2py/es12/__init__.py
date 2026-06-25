"""ES12 (ES2021) support: logical assignment, numeric separators, replaceAll."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES12_SYNTAX_RE = re.compile(
    r'(?:'
    r'\?\?=|&&=|\|\|=|'
    r'[0-9]+_[0-9]|'
    r'\.replaceAll\s*\(|'
    r'\bPromise\.any\s*\('
    r')',
    re.MULTILINE)

_LOGICAL_ASSIGN_OPS = ('??=', '&&=', '||=')
_NUMERIC_LITERAL_RE = re.compile(
    r'(?<![\w$])([0-9][0-9_]*(?:\.[0-9_]+)?(?:[eE][+-]?[0-9_]+)?)')


def looks_like_es12(code):
    """Return True if source likely contains ES12 syntax or APIs."""
    return bool(_ES12_SYNTAX_RE.search(code))


def prepare_es12(code):
    """Apply ES2021 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _transform_logical_assignment(masked)
    masked = _transform_numeric_separators(masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked


def _skip_ws(code, i, direction=1):
    if direction >= 0:
        while i < len(code) and code[i].isspace():
            i += 1
        return i
    while i >= 0 and code[i].isspace():
        i -= 1
    return i


def _scan_lhs(code, op_start):
    i = _skip_ws(code, op_start - 1, -1)
    end = i + 1
    paren = bracket = 0
    in_str = None
    while i >= 0:
        ch = code[i]
        if in_str:
            if ch == '\\':
                i -= 1
                continue
            if ch == in_str:
                in_str = None
            i -= 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            i -= 1
            continue
        if paren == 0 and bracket == 0:
            if ch in '=,;:{}':
                break
        if ch == ')':
            paren += 1
        elif ch == '(':
            paren -= 1
            if paren < 0:
                break
        elif ch == ']':
            bracket += 1
        elif ch == '[':
            bracket -= 1
            if bracket < 0:
                break
        i -= 1
    start = i + 1
    while start < end and code[start].isspace():
        start += 1
    return start, end


def _scan_rhs(code, start):
    i = _skip_ws(code, start, 1)
    begin = i
    paren = bracket = 0
    in_str = None
    while i < len(code):
        ch = code[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            i += 1
            continue
        if paren == 0 and bracket == 0:
            if ch in ',;':
                break
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket -= 1
        i += 1
    end = i
    while end > begin and code[end - 1].isspace():
        end -= 1
    return begin, end


def _transform_logical_assignment(code):
    while True:
        op_pos = -1
        op = None
        for candidate in _LOGICAL_ASSIGN_OPS:
            idx = code.find(candidate)
            if idx >= 0 and (op_pos < 0 or idx < op_pos):
                op_pos = idx
                op = candidate
        if op_pos < 0:
            break
        lhs_start, lhs_end = _scan_lhs(code, op_pos)
        rhs_start, rhs_end = _scan_rhs(code, op_pos + len(op))
        lhs = code[lhs_start:lhs_end].strip()
        rhs = code[rhs_start:rhs_end].strip()
        if op == '&&=':
            repl = '%s = (%s && (%s))' % (lhs, lhs, rhs)
        elif op == '||=':
            repl = '%s = (%s || (%s))' % (lhs, lhs, rhs)
        else:
            repl = ('%s = (%s !== null && %s !== undefined ? %s : %s)' %
                    (lhs, lhs, lhs, lhs, rhs))
        code = code[:lhs_start] + repl + code[rhs_end:]
    return code


def _strip_numeric_underscores(match):
    return match.group(1).replace('_', '')


def _transform_numeric_separators(code):
    return _NUMERIC_LITERAL_RE.sub(_strip_numeric_underscores, code)
