"""Tests for ES14 (ES2023) JavaScript support."""
import js2py
from js2py.es14 import looks_like_es14


def test_looks_like_es14():
    assert looks_like_es14('[1, 2, 3].findLast(function(x) { return x > 1; })')
    assert looks_like_es14('[1, 2, 3].findLastIndex(function(x) { return x > 1; })')
    assert looks_like_es14('#!/usr/bin/env node\nvar x = 1;')
    assert not looks_like_es14('var a = [1, 2]; a[0]')


def test_array_find_last():
    assert js2py.eval_js(
        '[1, 2, 3, 4].findLast(function(x) { return x % 2 === 0; })',
        es14=True) == 4


def test_array_find_last_none():
    assert js2py.eval_js(
        '[1, 3, 5].findLast(function(x) { return x % 2 === 0; })',
        es14=True) is None


def test_array_find_last_index():
    assert js2py.eval_js(
        '[1, 2, 3, 4].findLastIndex(function(x) { return x % 2 === 0; })',
        es14=True) == 3


def test_array_find_last_index_missing():
    assert js2py.eval_js(
        '[1, 3, 5].findLastIndex(function(x) { return x % 2 === 0; })',
        es14=True) == -1


def test_array_find_last_sparse():
    assert js2py.eval_js(
        '[1, , 3, 4].findLast(function(x) { return x > 2; })',
        es14=True) == 4


def test_array_find_last_auto():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var a = [10, 20, 30]; var v = a.findLast(function(x) { return x < 25; });',
        es14='auto')
    assert ctx.v == 20


def test_hashbang_execute():
    ctx = js2py.EvalJs()
    ctx.execute('#!/usr/bin/env node\nvar x = 42;', es14=True)
    assert ctx.x == 42


def test_hashbang_eval():
    assert js2py.eval_js('#!/usr/bin/env node\n1 + 2', es14=True) == 3


def test_eval_js14():
    assert js2py.eval_js14(
        '[5, 6, 7].findLastIndex(function(x) { return x < 7; })') == 1


if __name__ == '__main__':
    import inspect
    import sys

    failed = 0
    for name, func in sorted(inspect.getmembers(sys.modules[__name__], inspect.isfunction)):
        if not name.startswith('test_'):
            continue
        try:
            func()
            print('ok', name)
        except Exception as exc:
            failed += 1
            print('FAIL', name, exc)
            import traceback
            traceback.print_exc()
    sys.exit(1 if failed else 0)
