"""ES11 (ES2020) support: optional chaining, nullish coalescing, globalThis."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES11_SYNTAX_RE = re.compile(
    r'(?:'
    r'\?\?|'
    r'\?\.|'
    r'\bglobalThis\b|'
    r'\bPromise\.allSettled\s*\('
    r')',
    re.MULTILINE)

_IDENT_RE = re.compile(r'[\w$]+')


def looks_like_es11(code):
    """Return True if source likely contains ES11 syntax or APIs."""
    return bool(_ES11_SYNTAX_RE.search(code))


def prepare_es11(code):
    """Apply ES2020 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _transform_nullish_coalescing(masked)
    masked = _transform_optional_chaining(masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked


def _is_ident_char(ch):
    return ch.isalnum() or ch in ('_', '$')


def _skip_ws(code, i, direction=1):
    if direction >= 0:
        while i < len(code) and code[i].isspace():
            i += 1
        return i
    while i >= 0 and code[i].isspace():
        i -= 1
    return i


def _find_matching(code, start, open_ch, close_ch):
    depth = 0
    in_str = None
    i = start
    while i < len(code):
        ch = code[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _parse_optional_access(code, pos):
    pos = _skip_ws(code, pos, 1)
    if pos >= len(code):
        return None, pos
    if code[pos] == '[':
        end = _find_matching(code, pos, '[', ']')
        if end is None:
            return None, pos
        return code[pos:end + 1], end + 1
    if code[pos] == '(':
        end = _find_matching(code, pos, '(', ')')
        if end is None:
            return None, pos
        return code[pos:end + 1], end + 1
    m = _IDENT_RE.match(code, pos)
    if m:
        return '.' + m.group(0), m.end()
    return None, pos


def _parse_member_access(code, pos):
    pos = _skip_ws(code, pos, 1)
    if pos >= len(code):
        return None, pos
    if code[pos] == '.':
        pos += 1
        m = _IDENT_RE.match(code, pos)
        if not m:
            return None, pos
        return '.' + m.group(0), m.end()
    if code[pos] == '[':
        end = _find_matching(code, pos, '[', ']')
        if end is None:
            return None, pos
        return code[pos:end + 1], end + 1
    if code[pos] == '(':
        end = _find_matching(code, pos, '(', ')')
        if end is None:
            return None, pos
        return code[pos:end + 1], end + 1
    return None, pos


def _parse_base_backwards(code, end):
    end = _skip_ws(code, end - 1, -1) + 1
    if end <= 0:
        return None, None
    i = end - 1
    if code[i] == ')':
        start = _find_matching(code, i, '(', ')')
        if start is None:
            return None, None
        return start, end
    if code[i] == ']':
        start = _find_matching(code, i, '[', ']')
        if start is None:
            return None, None
        return start, end
    if _is_ident_char(code[i]):
        while i >= 0 and _is_ident_char(code[i]):
            i -= 1
        if i >= 0 and code[i] == '.':
            while i >= 0:
                if _is_ident_char(code[i]) or code[i] == '.':
                    i -= 1
                elif code[i] == ')':
                    start = _find_matching(code, i, '(', ')')
                    if start is None:
                        break
                    i = start - 1
                else:
                    break
        return i + 1, end
    return None, None


def _parse_optional_chain(code, qmark_pos):
    if code[qmark_pos:qmark_pos + 2] != '?.':
        return None
    base_start, base_end = _parse_base_backwards(code, qmark_pos)
    if base_start is None:
        return None
    base = code[base_start:base_end].strip()
    pos = qmark_pos + 2
    segments = []
    access, pos = _parse_optional_access(code, pos)
    if access is None:
        return None
    segments.append(('opt', access))
    while True:
        pos = _skip_ws(code, pos, 1)
        if pos >= len(code):
            break
        if code[pos:pos + 2] == '?.':
            pos += 2
            access, pos = _parse_optional_access(code, pos)
            if access is None:
                break
            segments.append(('opt', access))
            continue
        if code[pos] == '.':
            access, pos = _parse_member_access(code, pos)
            if access is None:
                break
            segments.append(('req', access))
            continue
        break
    chain_end = pos
    return base_start, chain_end, base, segments


def _apply_access(var, access):
    if access.startswith('.'):
        return '%s%s' % (var, access)
    if access.startswith('['):
        return '%s%s' % (var, access)
    if access.startswith('('):
        return '%s%s' % (var, access)
    return var


def _emit_optional_chain(base, segments):
    lines = ['var _r = %s;' % base]
    for kind, access in segments:
        if kind == 'opt':
            lines.append('if (_r == null) return undefined;')
            if access.startswith('('):
                lines.append('_r = _r%s;' % access)
            else:
                lines.append('_r = _r%s;' % access)
        else:
            lines.append('_r = _r%s;' % access)
    lines.append('return _r;')
    body = ' '.join(lines)
    return '(function() { %s })()' % body


def _transform_optional_chaining(code):
    changed = True
    while changed:
        changed = False
        idx = 0
        while idx < len(code) - 1:
            if code[idx:idx + 2] != '?.':
                idx += 1
                continue
            parsed = _parse_optional_chain(code, idx)
            if parsed is None:
                idx += 1
                continue
            start, end, base, segments = parsed
            replacement = _emit_optional_chain(base, segments)
            code = code[:start] + replacement + code[end:]
            changed = True
            idx = start + len(replacement)
    return code


def _scan_nullish_operand(code, start, direction):
    """Scan one nullish-coalescing operand; start is first char of operand."""
    if direction < 0:
        i = _skip_ws(code, start, -1)
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
                if i > 0 and code[i - 1:i + 1] == '??':
                    break
                if code[i:i + 2] == '||' or code[i:i + 2] == '&&':
                    break
                if ch in ',;:{}':
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
        start_idx = i + 1
        while start_idx < end and code[start_idx].isspace():
            start_idx += 1
        return start_idx, end
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
            if code[i:i + 2] == '??':
                break
            if code[i:i + 2] == '||' or code[i:i + 2] == '&&':
                break
            if ch in ',;:{}':
                break
            if ch == ')':
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


def _parse_nullish_operand(code, op_pos, side):
    if side == 'left':
        return _scan_nullish_operand(code, op_pos - 1, -1)
    return _scan_nullish_operand(code, op_pos + 2, 1)


def _transform_nullish_coalescing(code):
    while True:
        op_pos = -1
        for i in range(len(code) - 1):
            if code[i:i + 2] == '??':
                op_pos = i
                break
        if op_pos < 0:
            break
        left_start, left_end = _parse_nullish_operand(code, op_pos, 'left')
        right_start, right_end = _parse_nullish_operand(code, op_pos, 'right')
        left = code[left_start:left_end].strip()
        right = code[right_start:right_end].strip()
        replacement = (
            '(%s !== null && %s !== undefined ? %s : %s)' % (left, left, left, right))
        code = code[:left_start] + replacement + code[right_end:]
    return code
