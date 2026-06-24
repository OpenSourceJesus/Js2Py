"""Tests for ES7 (ES2016) JavaScript support."""
import js2py
from js2py.es7 import looks_like_es7


def test_looks_like_es7():
    assert looks_like_es7('2 ** 3')
    assert looks_like_es7('[1].includes(1)')
    assert not looks_like_es7('var a = 1; Math.pow(2, 3)')


def test_exponentiation_basic():
    assert js2py.eval_js('2 ** 3', es7=True) == 8


def test_exponentiation_right_associative():
    assert js2py.eval_js('2 ** 3 ** 2', es7=True) == 512


def test_exponentiation_precedence():
    assert js2py.eval_js('2 * 3 ** 2', es7=True) == 18
    assert js2py.eval_js('2 ** 3 + 1', es7=True) == 9


def test_eval_js_auto_es7():
    assert js2py.eval_js('2 ** 10', es7='auto') == 1024


def test_eval_js7():
    assert js2py.eval_js7('3 ** 4') == 81


def test_array_includes():
    assert js2py.eval_js('[1, 2, 3].includes(2)') is True
    assert js2py.eval_js('[1, 2, 3].includes(4)') is False


def test_array_includes_from_index():
    assert js2py.eval_js('[1, 2, 3].includes(2, 2)') is False
    assert js2py.eval_js('[1, 2, 3].includes(3, 2)') is True


def test_array_includes_nan():
    assert js2py.eval_js('[1, NaN, 3].includes(NaN)') is True


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
