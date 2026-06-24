"""Tests for ES8 (ES2017) JavaScript support."""
import js2py
from js2py.es8 import looks_like_es8


def test_looks_like_es8():
    assert looks_like_es8('Object.values({})')
    assert looks_like_es8('"x".padStart(3)')
    assert looks_like_es8('function f(a,) { return a; }')
    assert not looks_like_es8('var a = 1; Object.keys({})')


def test_object_values():
    assert list(js2py.eval_js('Object.values({a: 1, b: 2})')) == [1, 2]


def test_object_entries():
    result = js2py.eval_js('Object.entries({a: 1, b: 2})')
    assert list(result) == [['a', 1], ['b', 2]]


def test_object_get_own_property_descriptors():
    descs = js2py.eval_js(
        'Object.getOwnPropertyDescriptors({a: 1, get b() { return 2; }})')
    assert descs.a.value == 1
    assert descs.b.get is not None


def test_string_pad_start():
    assert js2py.eval_js('"5".padStart(3, "0")') == '005'
    assert js2py.eval_js('"hello".padStart(8)') == '   hello'


def test_string_pad_end():
    assert js2py.eval_js('"5".padEnd(3, "0")') == '500'
    assert js2py.eval_js('"hello".padEnd(8)') == 'hello   '


def test_trailing_comma_params():
    ctx = js2py.EvalJs()
    ctx.execute('function f(a, b,) { return a + b; }', es8=True)
    assert ctx.f(1, 2) == 3


def test_trailing_comma_auto():
    ctx = js2py.EvalJs()
    ctx.execute('function g(x,) { return x * 2; }', es8='auto')
    assert ctx.g(5) == 10


def test_eval_js8():
    assert js2py.eval_js8('Object.values({x: 9})')[0] == 9


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
    sys.exit(1 if failed else 0)
