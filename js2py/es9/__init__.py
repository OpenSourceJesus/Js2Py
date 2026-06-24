"""ES9 (ES2018) support: object spread/rest and Promise.finally."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ES9_SYNTAX_RE = re.compile(
    r'(?:'
    r'\{\s*\.\.\.|'
    r',\s*\.\.\.|'
    r'\{\s*[^}]*,\s*\.\.\.[\w$]|'
    r'\.finally\s*\(|'
    r'\bObject\.assign\s*\(|'
    r'\bObject\.fromEntries\s*\('
    r')',
    re.MULTILINE)

_REST_DECL_RE = re.compile(
    r'\b(var|let|const)\s+\{([^}]+)\}\s*=\s*([^;\n]+)\s*;?',
    re.MULTILINE)


def looks_like_es9(code):
    """Return True if source likely contains ES9 syntax or APIs."""
    return bool(_ES9_SYNTAX_RE.search(code))


def prepare_es9(code):
    """Apply ES2018 source transforms before translation."""
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _transform_object_rest_declarations(masked)
    masked = _transform_object_spreads(masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked


def _contains_spread_property(inner):
    return bool(re.search(r'(?:^\s*,?\s*|\,\s*)\.\.\.', inner))


def _find_matching_brace(code, start):
    if start >= len(code) or code[start] != '{':
        raise ValueError('expected {')
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
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _split_object_properties(inner):
    parts = []
    buf = []
    depth = 0
    in_str = None
    for ch in inner:
        if in_str:
            buf.append(ch)
            if ch == '\\':
                continue
            if ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            buf.append(ch)
            continue
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth -= 1
        if ch == ',' and depth == 0:
            part = ''.join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        buf.append(ch)
    part = ''.join(buf).strip()
    if part:
        parts.append(part)
    return parts


def _is_destructuring_brace(code, brace_pos):
    before = code[:brace_pos].rstrip()
    if re.search(r'\b(var|let|const|for)\s*$', before):
        return True
    if re.search(r'(?:function\s+\w+\s*|\()\s*$', before):
        return True
    return False


def _desugar_spread_object(literal):
    inner = literal[1:-1]
    props = _split_object_properties(inner)
    lines = ['var __o = {};']
    for prop in props:
        prop = prop.strip()
        if prop.startswith('...'):
            expr = prop[3:].strip()
            lines.append(
                'var __t = %s; if (__t != null) { for (var __k in __t) { '
                'if (__t.hasOwnProperty(__k)) __o[__k] = __t[__k]; } }' % expr)
        elif re.match(r'^[\w$]+\s*:', prop):
            key, val = prop.split(':', 1)
            key = key.strip()
            val = val.strip()
            if re.match(r'^[\w$]+$', key):
                lines.append('__o.%s = %s;' % (key, val))
            else:
                lines.append('__o[%s] = %s;' % (key, val))
        elif re.match(r'^[\w$]+$', prop):
            lines.append('__o.%s = %s;' % (prop, prop))
        else:
            lines.append('__o[%s] = %s;' % (prop, prop))
    lines.append('return __o;')
    return '(function() { %s })()' % ' '.join(lines)


def _transform_object_spreads(code):
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(code):
            if code[i] != '{':
                i += 1
                continue
            if _is_destructuring_brace(code, i):
                i += 1
                continue
            end = _find_matching_brace(code, i)
            if end is None:
                i += 1
                continue
            literal = code[i:end + 1]
            if not _contains_spread_property(literal[1:-1]):
                i = end + 1
                continue
            replacement = _desugar_spread_object(literal)
            code = code[:i] + replacement + code[end + 1:]
            changed = True
            i += len(replacement)
    return code


def _transform_object_rest_declarations(code):
    def replacer(match):
        kind, inner, src = match.group(1), match.group(2), match.group(3).strip()
        props = [p.strip() for p in _split_object_properties(inner) if p.strip()]
        if not any(p.startswith('...') for p in props):
            return match.group(0)
        fixed = []
        rest_name = None
        excluded = []
        for prop in props:
            if prop.startswith('...'):
                rest_name = prop[3:].strip()
                continue
            if ':' in prop:
                key, val = prop.split(':', 1)
                key = key.strip().strip('"').strip("'")
                val = val.strip()
            else:
                key = prop.strip()
                val = '__src.' + key
            excluded.append(key)
            if re.match(r'^[\w$]+$', key):
                fixed.append('var %s = __src.%s;' % (key, key))
            else:
                fixed.append('var %s = __src[%s];' % (val, repr(key)))
        if rest_name is None:
            return match.group(0)
        cond = 'true'
        for key in excluded:
            piece = '(__k !== "%s")' % key
            cond = piece if cond == 'true' else cond + ' && ' + piece
        fixed.append('var %s = {};' % rest_name)
        fixed.append(
            'for (var __k in __src) { if (__src.hasOwnProperty(__k) && %s) '
            '%s[__k] = __src[__k]; }' % (cond, rest_name))
        return 'var __src = %s; %s' % (src, ' '.join(fixed))

    return _REST_DECL_RE.sub(replacer, code)
