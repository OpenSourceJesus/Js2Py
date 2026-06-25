"""Tests for ES13 (ES2022) JavaScript support."""
import js2py
from js2py.es13 import looks_like_es13


def test_looks_like_es13():
    assert looks_like_es13('[1, 2, 3].at(-1)')
    assert looks_like_es13('Object.hasOwn({}, "x")')
    assert not looks_like_es13('var a = [1, 2]; a[0]')


def test_array_at_positive():
    assert js2py.eval_js('[10, 20, 30].at(1)', es13=True) == 20


def test_array_at_negative():
    assert js2py.eval_js('[10, 20, 30].at(-1)', es13=True) == 30


def test_array_at_out_of_range():
    assert js2py.eval_js('[1].at(5)', es13=True) is None


def test_array_at_auto():
    ctx = js2py.EvalJs()
    ctx.execute('var a = [5, 6]; var v = a.at(-2);', es13='auto')
    assert ctx.v == 5


def test_string_at():
    assert js2py.eval_js('"hello".at(-1)', es13=True) == 'o'
    assert js2py.eval_js('"hi".at(5)', es13=True) is None


def test_object_has_own_true():
    assert js2py.eval_js('Object.hasOwn({a: 1}, "a")', es13=True) is True


def test_object_has_own_false():
    assert js2py.eval_js('Object.hasOwn({a: 1}, "toString")', es13=True) is False


def test_object_has_own_inherited():
    ctx = js2py.EvalJs()
    ctx.execute('var o = Object.create({x: 1}); var v = Object.hasOwn(o, "x");',
                es13=True)
    assert ctx.v is False


def test_eval_js13():
    assert js2py.eval_js13('Object.hasOwn({k: 9}, "k")') is True


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
