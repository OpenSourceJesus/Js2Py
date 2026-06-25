"""Tests for ES8 (ES2017) JavaScript support."""
import js2py
from js2py.es8 import looks_like_es8


def test_looks_like_es8():
    assert looks_like_es8('"x".padStart(4)')
    assert looks_like_es8('Object.values({a: 1})')
    assert looks_like_es8('Object.getOwnPropertyDescriptors({})')
    assert not looks_like_es8('Object.keys({a: 1})')


def test_object_values():
    assert list(js2py.eval_js('Object.values({a: 1, b: 2})', es8=True)) == [1, 2]


def test_object_entries():
    ctx = js2py.EvalJs()
    ctx.execute('var e = Object.entries({x: 9, y: 8});', es8=True)
    assert list(ctx.e[0]) == ['x', 9]
    assert list(ctx.e[1]) == ['y', 8]


def test_string_pad_start():
    assert js2py.eval_js('"9".padStart(4, "0")', es8=True) == '0009'
    assert js2py.eval_js('"abc".padStart(3)', es8=True) == 'abc'
    assert js2py.eval_js('"abc".padStart(6, "123")', es8=True) == '123abc'


def test_string_pad_end():
    assert js2py.eval_js('"9".padEnd(4, "0")', es8=True) == '9000'
    assert js2py.eval_js('"abc".padEnd(3)', es8=True) == 'abc'
    assert js2py.eval_js('"abc".padEnd(6, "123")', es8=True) == 'abc123'


def test_pad_auto():
    ctx = js2py.EvalJs()
    ctx.execute('var s = "hi".padEnd(5, "-");', es8='auto')
    assert ctx.s == 'hi---'


def test_get_own_property_descriptors():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var o = {a: 1, b: 2};
        var d = Object.getOwnPropertyDescriptors(o);
        var keys = Object.keys(d).sort().join(",");
    ''', es8=True)
    assert ctx.keys == 'a,b'
    assert ctx.d.a.value == 1
    assert ctx.d.b.value == 2


def test_eval_js8():
    assert list(js2py.eval_js8('Object.values({k: 5})')) == [5]


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
