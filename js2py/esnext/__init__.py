"""ES.Next support: staging features beyond ES16 (Error.isError, Iterator.concat, using)."""

import re

_ESNEXT_SYNTAX_RE = re.compile(
    r'(?:'
    r'\bError\.isError\s*\(|'
    r'\bIterator\.concat\s*\(|'
    r'\busing\s+[A-Za-z_$][\w$]*\s*='
    r')',
    re.MULTILINE)

_USING_STMT_RE = re.compile(
    r'^\s*using\s+([A-Za-z_$][\w$]*)\s*=\s*',
    re.MULTILINE)


def _scan_expression_until_semicolon(code, start):
    i = start
    depth_paren = depth_bracket = depth_brace = 0
    in_single = in_double = False
    escape = False
    while i < len(code):
        ch = code[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_single or in_double:
            if ch == '\\':
                escape = True
            elif in_single and ch == "'":
                in_single = False
            elif in_double and ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == '(':
            depth_paren += 1
        elif ch == ')':
            depth_paren = max(0, depth_paren - 1)
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket = max(0, depth_bracket - 1)
        elif ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace = max(0, depth_brace - 1)
        elif (depth_paren == 0 and depth_bracket == 0 and depth_brace == 0
              and ch == ';'):
            return code[start:i].strip(), i + 1
        i += 1
    return code[start:].strip(), len(code)


def looks_like_esnext(code):
    """Return True if source likely contains ES.Next syntax or APIs."""
    return bool(_ESNEXT_SYNTAX_RE.search(code))


def _desugar_block_using(inner):
    pos = 0
    usings = []
    while pos < len(inner):
        match = _USING_STMT_RE.match(inner, pos)
        if not match:
            break
        name = match.group(1)
        init, end = _scan_expression_until_semicolon(inner, match.end())
        usings.append((name, init))
        pos = end
        while pos < len(inner) and inner[pos] in ' \t\r\n':
            pos += 1
    if not usings:
        return inner
    body = inner[pos:]
    declarations = ';\n'.join('var %s = (%s)' % (name, init) for name, init in usings)
    disposals = []
    for name, _ in reversed(usings):
        disposals.append(
            'if (%s != null && %s !== undefined) {'
            ' var __PyJsDispose = %s.dispose;'
            ' if (typeof __PyJsDispose === "function") __PyJsDispose.call(%s);'
            ' }' % (name, name, name, name))
    return (
        declarations + ';\n'
        'try {\n' + body + '\n'
        '} finally {\n' + '\n'.join(disposals) + '\n'
        '}')


def _find_matching_brace(code, start):
    i = start + 1
    depth = 1
    in_single = in_double = in_template = False
    escape = False
    while i < len(code) and depth:
        ch = code[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_single or in_double or in_template:
            if ch == '\\':
                escape = True
            elif in_single and ch == "'":
                in_single = False
            elif in_double and ch == '"':
                in_double = False
            elif in_template and ch == '`':
                in_template = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == '`':
            in_template = True
            i += 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        i += 1
    return i - 1


def _transform_using_blocks(code):
    if 'using ' not in code:
        return code
    out = []
    i = 0
    in_single = in_double = in_template = False
    escape = False
    while i < len(code):
        ch = code[i]
        if escape:
            escape = False
            out.append(ch)
            i += 1
            continue
        if in_single or in_double or in_template:
            if ch == '\\':
                escape = True
            elif in_single and ch == "'":
                in_single = False
            elif in_double and ch == '"':
                in_double = False
            elif in_template and ch == '`':
                in_template = False
            out.append(ch)
            i += 1
            continue
        if ch == "'":
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(ch)
            i += 1
            continue
        if ch == '`':
            in_template = True
            out.append(ch)
            i += 1
            continue
        if ch == '{':
            end = _find_matching_brace(code, i)
            inner = code[i + 1:end]
            inner = _transform_using_blocks(inner)
            if re.search(r'\busing\s+', inner):
                inner = _desugar_block_using(inner)
            out.append('{' + inner + '}')
            i = end + 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def prepare_esnext(code):
    """Apply ES.Next source transforms before translation."""
    return _transform_using_blocks(code)
