"""ES7 (ES2016) support: exponentiation operator and includes()."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES7_SYNTAX_RE = re.compile(
    r'(?:'
    r'\*\*=|\*\*|'
    r'\.includes\s*\('
    r')',
    re.MULTILINE)


def looks_like_es7(code):
    """Return True if source likely contains ES7 syntax or APIs."""
    return bool(_ES7_SYNTAX_RE.search(code))


def prepare_es7(code):
    """Apply ES2016 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _transform_exponentiation_assignment(masked)
    masked = _transform_exponentiation(masked)
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
    escape = False
    while i < len(code):
        ch = code[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_str:
            if ch == '\\':
                escape = True
                i += 1
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


def _transform_exponentiation_assignment(code):
    while True:
        op_pos = code.find('**=')
        if op_pos < 0:
            break
        lhs_start, lhs_end = _scan_lhs(code, op_pos)
        rhs_start, rhs_end = _scan_rhs(code, op_pos + 3)
        lhs = code[lhs_start:lhs_end].strip()
        rhs = code[rhs_start:rhs_end].strip()
        repl = '%s = Math.pow(%s, %s)' % (lhs, lhs, rhs)
        code = code[:lhs_start] + repl + code[rhs_end:]
    return code


def _find_exponentiation(code):
    for i in range(len(code) - 1, 0, -1):
        if code[i - 1:i + 1] == '**' and (i + 1 >= len(code) or code[i + 1] != '='):
            return i - 1
    return -1


def _scan_exp_lhs(code, op_start):
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
            if ch == '*' and i > 0 and code[i - 1] == '*' and (i - 1) != op_start:
                break
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


def _scan_exp_rhs(code, start):
    i = _skip_ws(code, start, 1)
    begin = i
    paren = bracket = 0
    in_str = None
    escape = False
    while i < len(code):
        ch = code[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_str:
            if ch == '\\':
                escape = True
                i += 1
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
            if ch == '*' and i + 1 < len(code) and code[i + 1] == '*':
                break
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


def _transform_exponentiation(code):
    while True:
        op_pos = _find_exponentiation(code)
        if op_pos < 0:
            break
        lhs_start, lhs_end = _scan_exp_lhs(code, op_pos)
        rhs_start, rhs_end = _scan_exp_rhs(code, op_pos + 2)
        lhs = code[lhs_start:lhs_end].strip()
        rhs = code[rhs_start:rhs_end].strip()
        repl = 'Math.pow(%s, %s)' % (lhs, rhs)
        code = code[:lhs_start] + repl + code[rhs_end:]
    return code
