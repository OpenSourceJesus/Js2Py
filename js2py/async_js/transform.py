"""Downlevel async/await to Promise-based ES5."""

import re

CP_STRING = (
    '"([^\\\\"]+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|x[0-9a-fA-F]{2}|'
    'u[0-9a-fA-F]{4}))*"|\'([^\\\\\']+|\\\\([bfnrtv\'"\\\\]|[0-3]?[0-7]{1,2}|'
    'x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}))*\'')
CP_STRING_PLACEHOLDER = '__PyJsSTR_%i_PyJsSTR__'

_ASYNC_SYNTAX_RE = re.compile(
    r'(?:'
    r'\basync\s+(?:function|\()|'
    r'\bawait\b'
    r')',
    re.MULTILINE)

_FOR_LOOP_ID = 0


def looks_like_async(code):
    masked = re.sub(CP_STRING, lambda m: ' ', code)
    return bool(_ASYNC_SYNTAX_RE.search(masked))


def downlevel_async_await(code):
    """Transform async/await into Promise chains understood by pyjsparser."""
    if not looks_like_async(code):
        return code
    matches = []

    def mask(match):
        matches.append(match.group(0))
        return CP_STRING_PLACEHOLDER % (len(matches) - 1)

    masked = re.sub(CP_STRING, mask, code)
    masked = _transform_async_arrows(masked)
    masked = _transform_async_functions(masked)
    for index, value in enumerate(matches):
        masked = masked.replace(CP_STRING_PLACEHOLDER % index, value, 1)
    return masked


def _transform_async_arrows(code):
    pattern = re.compile(
        r'\basync\s+(\([^)]*\)|[\w$]+)\s*=>',
        re.MULTILINE)
    pos = 0
    out = []
    for match in pattern.finditer(code):
        out.append(code[pos:match.start()])
        params = match.group(1)
        body_start = match.end()
        body, body_end = _read_arrow_body(code, body_start)
        if body.startswith('{') and body.endswith('}'):
            inner = body[1:-1]
            transformed = _desugar_async_body(inner)
            out.append('function %s { %s }' % (params, transformed))
        else:
            expr = _desugar_await_in_expression(body.strip())
            out.append('function %s { return %s; }' % (params, expr))
        pos = body_end
    out.append(code[pos:])
    return ''.join(out)


def _transform_async_functions(code):
    pattern = re.compile(r'\basync\s+function(\s+[\w$]+)?\s*\(', re.MULTILINE)
    pos = 0
    out = []
    for match in pattern.finditer(code):
        out.append(code[pos:match.start()])
        name = match.group(1) or ''
        params_start = match.end()
        params_end = _find_matching_paren(code, params_start - 1)
        params = code[params_start:params_end]
        body_start = params_end + 1
        while body_start < len(code) and code[body_start].isspace():
            body_start += 1
        if body_start >= len(code) or code[body_start] != '{':
            out.append(code[match.start():params_end + 1])
            pos = params_end + 1
            continue
        body_end = _find_matching_brace(code, body_start)
        body = code[body_start + 1:body_end]
        transformed = _desugar_async_body(body)
        out.append('function%s(%s) { %s }' % (name, params, transformed))
        pos = body_end + 1
    out.append(code[pos:])
    return ''.join(out)


def _desugar_async_body(body):
    body = body.strip()
    if not body:
        return 'return Promise.resolve();'
    stmts = _parse_statements(body)
    if not stmts:
        return 'return Promise.resolve();'
    if not _statements_contain_await(stmts) and not _needs_promise_wrap(stmts):
        if len(stmts) == 1 and stmts[0]['type'] == 'return':
            arg = stmts[0].get('argument')
            if arg:
                return 'return Promise.resolve(%s);' % arg
            return 'return Promise.resolve();'
        return body
    chain = _desugar_statements(stmts)
    return 'return %s;' % chain


def _needs_promise_wrap(stmts):
    """Async functions must return a Promise even without await."""
    return True


def _statements_contain_await(stmts):
    for stmt in stmts:
        if stmt.get('await'):
            return True
        if stmt['type'] == 'block':
            if _statements_contain_await(stmt['body']):
                return True
        elif stmt['type'] == 'if':
            if (_statements_contain_await(stmt['consequent'])
                    or _statements_contain_await(stmt.get('alternate') or [])):
                return True
        elif stmt['type'] in ('for', 'while', 'do'):
            if _statements_contain_await(stmt['body']):
                return True
        elif stmt['type'] == 'try':
            if (_statements_contain_await(stmt['block'])
                    or _statements_contain_await(stmt.get('handler', {}).get('body', []))
                    or _statements_contain_await(stmt.get('finalizer') or [])):
                return True
    return False


def _desugar_statements(stmts, tail='Promise.resolve()'):
    chain = tail
    for stmt in reversed(stmts):
        chain = _wrap_statement(stmt, chain)
    return chain


def _wrap_statement(stmt, tail):
    stype = stmt['type']
    if stype == 'return':
        arg = stmt.get('argument')
        if not arg:
            if tail == 'Promise.resolve()':
                return 'Promise.resolve()'
            return 'Promise.resolve().then(function() { return %s; })' % tail
        if stmt.get('await'):
            expr = _desugar_await_in_expression(arg)
            if tail == 'Promise.resolve()':
                return expr
            return '%s.then(function(__ret) { return %s; })' % (expr, tail)
        if tail == 'Promise.resolve()':
            return 'Promise.resolve(%s)' % arg
        return 'Promise.resolve(%s).then(function(__ret) { return %s; })' % (
            arg, tail)
    if stype == 'throw':
        arg = stmt['argument']
        if stmt.get('await'):
            expr = _desugar_await_in_expression(arg)
            return '%s.then(function(__v) { throw __v; })' % expr
        return 'Promise.resolve().then(function() { throw %s; })' % arg
    if stype == 'var':
        if stmt.get('await'):
            expr = _desugar_await_in_expression(stmt['init'])
            return '%s.then(function(%s) { return %s; })' % (
                expr, stmt['name'], tail)
        return ('Promise.resolve().then(function() { %s %s = %s; return %s; })'
                % (stmt['kind'], stmt['name'], stmt['init'], tail))
    if stype == 'assign':
        if stmt.get('await'):
            expr = _desugar_await_in_expression(stmt['init'])
            return ('%s.then(function(__tmp) { %s = __tmp; return %s; })'
                    % (expr, stmt['name'], tail))
        return ('Promise.resolve().then(function() { %s = %s; return %s; })'
                % (stmt['name'], stmt['init'], tail))
    if stype == 'expr':
        src = stmt['source']
        if stmt.get('await'):
            m = re.match(
                r'([\w$]+)\s*(\+\=|-=|\*=|/=|%=|\|=|&=|\^=|<<=|>>=|>>>=)\s*await\s+(.+)$',
                src)
            if m:
                name, op, rhs = m.group(1), m.group(2), m.group(3).strip()
                return ('Promise.resolve(%s).then(function(__v) { %s %s __v; '
                        'return %s; })' % (rhs, name, op, tail))
            expr = _desugar_await_in_expression(src)
            return '%s.then(function() { return %s; })' % (expr, tail)
        return 'Promise.resolve().then(function() { %s; return %s; })' % (
            src, tail)
    if stype == 'block':
        inner = _desugar_statements(stmt['body'], tail)
        return 'Promise.resolve().then(function() { return %s; })' % inner
    if stype == 'if':
        cons = _desugar_statements(stmt['consequent'], tail)
        alt_stmts = stmt.get('alternate') or []
        if alt_stmts:
            alt = _desugar_statements(alt_stmts, tail)
            branch = 'if (%s) { return %s; } else { return %s; }' % (
                stmt['test'], cons, alt)
        else:
            branch = 'if (%s) { return %s; } return %s;' % (
                stmt['test'], cons, tail)
        return 'Promise.resolve().then(function() { %s })' % branch
    if stype == 'for':
        return _wrap_for_loop(stmt, tail)
    if stype == 'while':
        return _wrap_while_loop(stmt, tail)
    if stype == 'try':
        return _wrap_try(stmt, tail)
    return tail


def _wrap_for_loop(stmt, tail):
    global _FOR_LOOP_ID
    _FOR_LOOP_ID += 1
    name = '__for_%d' % _FOR_LOOP_ID
    init = stmt.get('init') or ''
    test = stmt.get('test') or 'true'
    update = stmt.get('update') or ''
    body_chain = _desugar_statements(stmt['body'])
    parts = []
    if init:
        parts.append(init + ';')
    parts.append('return (function %s() {' % name)
    parts.append('  if (!(%s)) return %s;' % (test, tail))
    parts.append('  return (%s).then(function() {' % body_chain)
    if update:
        parts.append('    %s;' % update)
    parts.append('    return %s();' % name)
    parts.append('  });')
    parts.append('})();')
    return 'Promise.resolve().then(function() { %s })' % '\n'.join(parts)


def _wrap_while_loop(stmt, tail):
    global _FOR_LOOP_ID
    _FOR_LOOP_ID += 1
    name = '__while_%d' % _FOR_LOOP_ID
    test = stmt['test']
    body_chain = _desugar_statements(stmt['body'])
    code = (
        'return (function %s() {\n'
        '  if (!(%s)) return %s;\n'
        '  return (%s).then(function() { return %s(); });\n'
        '})();' % (name, test, tail, body_chain, name))
    return 'Promise.resolve().then(function() { %s })' % code


def _wrap_try(stmt, tail):
    try_chain = _desugar_statements(stmt['block'], tail)
    handler = stmt.get('handler')
    if handler:
        param = handler.get('param') or '__err'
        catch_chain = _desugar_statements(handler['body'], tail)
        result = '%s.catch(function(%s) { return %s; })' % (
            try_chain, param, catch_chain)
    else:
        result = try_chain
    finalizer = stmt.get('finalizer')
    if finalizer:
        fin_chain = _desugar_statements(finalizer, tail)
        result = ('%s.then(function(__v) { return (%s).then(function() '
                  '{ return __v; }); }, function(__e) { return (%s).then('
                  'function() { throw __e; }); })'
                  % (result, fin_chain, fin_chain))
    return result


def _desugar_await_in_expression(expr):
    expr = expr.strip()
    while True:
        match = re.search(r'\bawait\b', expr)
        if not match:
            break
        start = match.start()
        operand_start = match.end()
        while operand_start < len(expr) and expr[operand_start].isspace():
            operand_start += 1
        operand_end = _scan_expression_end(expr, operand_start)
        operand = expr[operand_start:operand_end].strip()
        before = expr[:start].rstrip()
        after = expr[operand_end:].lstrip()
        if not before and not after:
            return 'Promise.resolve(%s)' % operand
        tmp = '__await_%d' % start
        if before.endswith('return '):
            inner = 'return %s' % tmp
        elif before:
            inner = '%s; return %s' % (before.rstrip(';'), tmp)
        else:
            inner = 'return %s' % tmp
        if after:
            if after.startswith('.'):
                inner = 'return (%s)%s' % (tmp, after)
            elif after[0] in '+-*/%&|^':
                inner = 'return %s%s' % (tmp, after)
            else:
                inner = 'return %s + %s' % (tmp, after)
        expr = 'Promise.resolve(%s).then(function(%s) { %s; })' % (
            operand, tmp, inner)
    return expr


def _parse_statements(code):
    code = code.strip()
    stmts = []
    i = 0
    n = len(code)
    while i < n:
        while i < n and code[i].isspace():
            i += 1
        if i >= n:
            break
        stmt, i = _parse_statement(code, i)
        if stmt is not None:
            stmts.append(stmt)
    return stmts


def _parse_statement(code, i):
    i = _skip_ws(code, i)
    if i >= len(code):
        return None, i

    for kw, stype in (
        ('for', 'for'), ('while', 'while'), ('if', 'if'),
        ('try', 'try'), ('return', 'return'), ('throw', 'throw'),
    ):
        if _starts_word(code, i, kw):
            parser = globals().get('_parse_' + stype)
            return parser(code, i)

    for kw in ('var', 'let', 'const'):
        if _starts_word(code, i, kw):
            return _parse_var(code, i, kw)

    if code[i] == '{':
        end = _find_matching_brace(code, i)
        body = _parse_statements(code[i + 1:end])
        return {'type': 'block', 'body': body}, end + 1

    end = _find_statement_end(code, i)
    src = code[i:end].strip()
    if not src:
        return None, end
    if src.endswith(';'):
        src = src[:-1].strip()
    return _parse_simple_statement(src), end


def _parse_return(code, i):
    i = _skip_ws(code, i + 6)
    end = _find_statement_end(code, i)
    arg = code[i:end].strip()
    if arg.endswith(';'):
        arg = arg[:-1].strip()
    await_flag = bool(re.search(r'\bawait\b', arg))
    if not arg:
        return {'type': 'return', 'argument': None, 'await': False}, end
    return {'type': 'return', 'argument': arg, 'await': await_flag}, end


def _parse_throw(code, i):
    i = _skip_ws(code, i + 5)
    end = _find_statement_end(code, i)
    arg = code[i:end].strip().rstrip(';')
    await_flag = bool(re.search(r'\bawait\b', arg))
    return {'type': 'throw', 'argument': arg, 'await': await_flag}, end


def _parse_var(code, i, kind):
    start = i
    end = _find_statement_end(code, i)
    src = code[i:end].strip().rstrip(';')
    m = re.match(r'(?:var|let|const)\s+([\w$]+)\s*=\s*(.+)$', src)
    if not m:
        return {'type': 'expr', 'source': code[start:end].strip()}, end
    name, init = m.group(1), m.group(2).strip()
    await_flag = bool(re.search(r'\bawait\b', init))
    return {'type': 'var', 'kind': kind, 'name': name, 'init': init,
            'await': await_flag}, end


def _parse_if(code, i):
    i = _skip_ws(code, i + 2)
    if code[i] != '(':
        raise SyntaxError('Expected ( after if')
    test_end = _find_matching_paren(code, i)
    test = code[i + 1:test_end].strip()
    i = _skip_ws(code, test_end + 1)
    cons, i = _parse_statement(code, i)
    if cons['type'] == 'block':
        cons = cons['body']
    else:
        cons = [cons]
    alternate = []
    i = _skip_ws(code, i)
    if _starts_word(code, i, 'else'):
        i = _skip_ws(code, i + 4)
        alt, i = _parse_statement(code, i)
        if alt['type'] == 'block':
            alternate = alt['body']
        else:
            alternate = [alt]
    return {'type': 'if', 'test': test, 'consequent': cons,
            'alternate': alternate}, i


def _parse_for(code, i):
    i = _skip_ws(code, i + 3)
    if code[i] != '(':
        raise SyntaxError('Expected ( after for')
    paren_end = _find_matching_paren(code, i)
    inner = code[i + 1:paren_end]
    init, test, update = _split_for_header(inner)
    i = _skip_ws(code, paren_end + 1)
    body_stmt, i = _parse_statement(code, i)
    if body_stmt['type'] == 'block':
        body = body_stmt['body']
    else:
        body = [body_stmt]
    return {'type': 'for', 'init': init, 'test': test, 'update': update,
            'body': body}, i


def _parse_while(code, i):
    i = _skip_ws(code, i + 5)
    if code[i] != '(':
        raise SyntaxError('Expected ( after while')
    test_end = _find_matching_paren(code, i)
    test = code[i + 1:test_end].strip()
    i = _skip_ws(code, test_end + 1)
    body_stmt, i = _parse_statement(code, i)
    if body_stmt['type'] == 'block':
        body = body_stmt['body']
    else:
        body = [body_stmt]
    return {'type': 'while', 'test': test, 'body': body}, i


def _parse_try(code, i):
    i = _skip_ws(code, i + 3)
    block_stmt, i = _parse_statement(code, i)
    if block_stmt['type'] == 'block':
        block = block_stmt['body']
    else:
        block = [block_stmt]
    handler = None
    i = _skip_ws(code, i)
    if _starts_word(code, i, 'catch'):
        i = _skip_ws(code, i + 5)
        if code[i] != '(':
            raise SyntaxError('Expected ( after catch')
        param_end = _find_matching_paren(code, i)
        param = code[i + 1:param_end].strip()
        i = _skip_ws(code, param_end + 1)
        hstmt, i = _parse_statement(code, i)
        if hstmt['type'] == 'block':
            hbody = hstmt['body']
        else:
            hbody = [hstmt]
        handler = {'param': param, 'body': hbody}
    finalizer = None
    i = _skip_ws(code, i)
    if _starts_word(code, i, 'finally'):
        i = _skip_ws(code, i + 7)
        fstmt, i = _parse_statement(code, i)
        if fstmt['type'] == 'block':
            finalizer = fstmt['body']
        else:
            finalizer = [fstmt]
    return {'type': 'try', 'block': block, 'handler': handler,
            'finalizer': finalizer}, i


def _parse_simple_statement(src):
    src = src.strip()
    m = re.match(r'(?:var|let|const)\s+([\w$]+)\s*=\s*(.+)$', src)
    if m:
        init = m.group(2).strip()
        await_flag = bool(re.search(r'\bawait\b', init))
        kind = src.split()[0]
        return {'type': 'var', 'kind': kind, 'name': m.group(1), 'init': init,
                'await': await_flag}
    m = re.match(r'([\w$]+)\s*=\s*(.+)$', src)
    if m:
        init = m.group(2).strip()
        await_flag = bool(re.search(r'\bawait\b', init))
        return {'type': 'assign', 'name': m.group(1), 'init': init,
                'await': await_flag}
    await_flag = bool(re.search(r'\bawait\b', src))
    return {'type': 'expr', 'source': src, 'await': await_flag}


def _split_for_header(inner):
    parts = []
    buf = []
    depth = 0
    for ch in inner:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth = max(0, depth - 1)
        if ch == ';' and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf).strip())
    while len(parts) < 3:
        parts.append('')
    return parts[0], parts[1], parts[2]


def _find_statement_end(code, i):
    depth = 0
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
        if ch in '\'"':
            in_str = ch
            i += 1
            continue
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth = max(0, depth - 1)
        if depth == 0:
            if ch == ';':
                return i + 1
            if ch == '{' and _starts_word(code, _word_start(code, i - 1), 'for'):
                pass
            if ch == '{' and i > 0:
                word = _word_at(code, i)
                if word in ('for', 'while', 'if', 'try', 'else', 'do', 'function'):
                    return i
        i += 1
    return len(code)


def _word_start(code, i):
    while i >= 0 and (code[i].isalnum() or code[i] in '_$'):
        i -= 1
    return i + 1


def _word_at(code, i):
    i = _skip_ws(code, i)
    if i >= len(code):
        return ''
    if code[i] == '{':
        j = i - 1
        while j >= 0 and code[j].isspace():
            j -= 1
        end = j + 1
        start = end
        while start > 0 and (code[start - 1].isalnum() or code[start - 1] in '_$'):
            start -= 1
        return code[start:end]
    return ''


def _starts_word(code, i, word):
    return code.startswith(word, i) and (
        i + len(word) >= len(code)
        or not (code[i + len(word)].isalnum() or code[i + len(word)] in '_$'))


def _skip_ws(code, i):
    while i < len(code) and code[i].isspace():
        i += 1
    return i


def _read_arrow_body(code, start):
    while start < len(code) and code[start].isspace():
        start += 1
    if start >= len(code):
        return '', start
    if code[start] == '{':
        end = _find_matching_brace(code, start)
        return code[start:end + 1], end + 1
    end = start
    depth = 0
    while end < len(code):
        ch = code[end]
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth = max(0, depth - 1)
        elif ch == ',' and depth == 0:
            break
        elif ch == ')' and depth == 0:
            break
        elif ch == ';' and depth == 0:
            end += 1
            break
        end += 1
    return code[start:end], end


def _find_matching_paren(code, open_index):
    if code[open_index] != '(':
        raise ValueError('expected (')
    depth = 0
    in_str = None
    for i in range(open_index, len(code)):
        ch = code[i]
        if in_str:
            if ch == '\\':
                continue
            if ch == in_str:
                in_str = None
            continue
        if ch in '\'"':
            in_str = ch
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i
    return len(code) - 1


def _find_matching_brace(code, open_index):
    if code[open_index] != '{':
        raise ValueError('expected {')
    depth = 0
    in_str = None
    for i in range(open_index, len(code)):
        ch = code[i]
        if in_str:
            if ch == '\\':
                continue
            if ch == in_str:
                in_str = None
            continue
        if ch in '\'"':
            in_str = ch
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return len(code) - 1


def _scan_expression_end(code, start):
    i = start
    while i < len(code) and code[i].isspace():
        i += 1
    if i >= len(code):
        return i
    if code[i] in '\'"':
        quote = code[i]
        i += 1
        while i < len(code):
            if code[i] == '\\':
                i += 2
                continue
            if code[i] == quote:
                return i + 1
            i += 1
        return i
    if code[i] == '(':
        return _find_matching_paren(code, i) + 1
    if code[i] == '{':
        return _find_matching_brace(code, i) + 1
    depth = 0
    while i < len(code):
        ch = code[i]
        if ch in '\'"':
            end = _scan_expression_end(code, i)
            i = end
            continue
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and ch in ',;':
            break
        elif depth == 0 and ch in '+-*' and i > start:
            prev = i - 1
            while prev >= start and code[prev].isspace():
                prev -= 1
            if prev >= start and (code[prev] in ')]}' or code[prev].isalnum()
                                    or code[prev] in '_$'):
                break
        elif depth == 0 and code.startswith('await', i):
            break
        i += 1
    return i
