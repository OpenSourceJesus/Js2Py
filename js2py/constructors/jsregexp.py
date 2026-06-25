from ..base import *

_REGEXP_ESCAPE_SYNTAX = set('^$\\.*+?()[]{}|')


@Js
def regexp_escape(string):
    s = string.to_string().value
    out = []
    for i, ch in enumerate(s):
        if ch in _REGEXP_ESCAPE_SYNTAX:
            out.append('\\' + ch)
        elif i == 0:
            o = ord(ch)
            if (48 <= o <= 57) or (65 <= o <= 90) or (97 <= o <= 122):
                out.append('\\x%02x' % o)
            else:
                out.append(ch)
        else:
            out.append(ch)
    return Js(''.join(out))


RegExp.define_own_property('escape', {
    'value': regexp_escape,
    'writable': True,
    'enumerable': False,
    'configurable': True
})

RegExpPrototype.define_own_property('constructor', {
    'value': RegExp,
    'enumerable': False,
    'writable': True,
    'configurable': True
})

RegExp.define_own_property(
    'prototype', {
        'value': RegExpPrototype,
        'enumerable': False,
        'writable': False,
        'configurable': False
    })
