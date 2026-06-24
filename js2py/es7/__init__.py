"""ES7 (ES2016) support: exponentiation operator and related syntax detection."""

import re

_ES7_SYNTAX_RE = re.compile(
    r'(?:'
    r'(?<![*/])\*\*(?!\*)|'  # ** but not */ or ***
    r'\.includes\s*\('       # Array.prototype.includes
    r')',
    re.MULTILINE)

_PATCHED = False


def looks_like_es7(code):
    """Return True if source likely contains ES7 syntax."""
    return bool(_ES7_SYNTAX_RE.search(code))


def ensure_pyjsparser_es7():
    """Patch pyjsparser once to parse ** with correct right-associativity."""
    global _PATCHED
    if _PATCHED:
        return
    import pyjsparser.parser as parser
    import pyjsparser.pyjsparserdata as data
    from pyjsparser.pyjsparserdata import Token

    data.PRECEDENCE['**'] = 12

    _orig_scan = parser.PyJsParser.scanPunctuator

    def scan_punctuator(self):
        if (self.index < self.length - 1
                and self.source[self.index:self.index + 2] == '**'):
            start = self.index
            self.index += 2
            return {
                'type': Token.Punctuator,
                'value': '**',
                'lineNumber': self.lineNumber,
                'lineStart': self.lineStart,
                'start': start,
                'end': self.index,
            }
        return _orig_scan(self)

    def _should_reduce(new_prec, stack_prec, stack_op, new_op):
        if new_prec < stack_prec:
            return True
        if new_prec > stack_prec:
            return False
        if stack_op == '**' or new_op == '**':
            return False
        return True

    _orig_parse_binary = parser.PyJsParser.parseBinaryExpression

    def parse_binary_expression(self):
        marker = self.lookahead
        left = self.inheritCoverGrammar(self.parseUnaryExpression)

        token = self.lookahead
        prec = self.binaryPrecedence(token, self.state['allowIn'])
        if prec == 0:
            return left
        self.isAssignmentTarget = self.isBindingElement = parser.false
        token['prec'] = prec
        self.lex()

        markers = [marker, self.lookahead]
        right = self.isolateCoverGrammar(self.parseUnaryExpression)

        stack = [left, token, right]

        while True:
            prec = self.binaryPrecedence(self.lookahead, self.state['allowIn'])
            if not prec > 0:
                break
            new_op = self.lookahead['value']
            while len(stack) > 2:
                stack_prec = stack[len(stack) - 2]['prec']
                stack_op = stack[len(stack) - 2]['value']
                if not _should_reduce(prec, stack_prec, stack_op, new_op):
                    break
                right = stack.pop()
                operator = stack.pop()['value']
                left = stack.pop()
                markers.pop()
                expr = parser.WrappingNode(
                    markers[len(markers) - 1]).finishBinaryExpression(
                        operator, left, right)
                stack.append(expr)

            token = self.lex()
            token['prec'] = prec
            stack.append(token)
            markers.append(self.lookahead)
            expr = self.isolateCoverGrammar(self.parseUnaryExpression)
            stack.append(expr)

        i = len(stack) - 1
        expr = stack[i]
        markers.pop()
        while i > 1:
            expr = parser.WrappingNode(markers.pop()).finishBinaryExpression(
                stack[i - 1]['value'], stack[i - 2], expr)
            i -= 2
        return expr

    parser.PyJsParser.scanPunctuator = scan_punctuator
    parser.PyJsParser.parseBinaryExpression = parse_binary_expression
    _PATCHED = True
