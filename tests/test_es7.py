"""Tests for ES7 (ES2016) JavaScript support."""
import js2py
from js2py.es7 import looks_like_es7, prepare_es7


def test_looks_like_es7():
    assert looks_like_es7('[1, 2, 3].includes(2)')
    assert looks_like_es7('2 ** 3')
    assert looks_like_es7('x **= 2')
    assert not looks_like_es7('var a = [1, 2]; a.indexOf(1)')


def test_prepare_es7_exponentiation():
    out = prepare_es7('2 ** 3 ** 2')
    assert 'Math.pow' in out
    assert '**' not in out


def test_prepare_es7_exponentiation_assign():
    out = prepare_es7('x **= 3')
    assert out == 'x = Math.pow(x, 3)'


def test_exponentiation():
    assert js2py.eval_js('2 ** 10', es7=True) == 1024


def test_exponentiation_right_associative():
    assert js2py.eval_js('2 ** 3 ** 2', es7=True) == 512


def test_exponentiation_assign():
    ctx = js2py.EvalJs()
    ctx.execute('var x = 2; x **= 3;', es7=True)
    assert ctx.x == 8


def test_array_includes_true():
    assert js2py.eval_js('[1, 2, 3].includes(2)', es7=True) is True


def test_array_includes_false():
    assert js2py.eval_js('[1, 2, 3].includes(4)', es7=True) is False


def test_array_includes_nan():
    assert js2py.eval_js('[NaN].includes(NaN)', es7=True) is True


def test_array_includes_from_index():
    assert js2py.eval_js('[1, 2, 3].includes(2, 2)', es7=True) is False


def test_array_includes_auto():
    ctx = js2py.EvalJs()
    ctx.execute('var ok = [10, 20].includes(20);', es7='auto')
    assert ctx.ok is True


def test_eval_js7():
    assert js2py.eval_js7('3 ** 4') == 81


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
