"""Tests for ES12 (ES2021) JavaScript support."""
import js2py
from js2py.es12 import looks_like_es12, prepare_es12
from js2py.event_loop import reset_event_loop


def test_looks_like_es12():
    assert looks_like_es12('a &&= 1')
    assert looks_like_es12('1_000')
    assert looks_like_es12('"a".replaceAll("a","b")')
    assert looks_like_es12('Promise.any([])')
    assert not looks_like_es12('var x = 1; x + 2')


def test_prepare_es12_logical_assign():
    out = prepare_es12('count &&= 1')
    assert 'count = (count &&' in out
    assert '1' in out


def test_prepare_es12_numeric_separator():
    assert prepare_es12('var n = 1_000_000;') == 'var n = 1000000;'


def test_numeric_separator():
    assert js2py.eval_js('1_000 + 2', es12=True) == 1002


def test_logical_and_assign():
    ctx = js2py.EvalJs()
    ctx.execute('var x = 1; x &&= 2; var y = x;', es12=True)
    assert ctx.y == 2


def test_logical_or_assign():
    ctx = js2py.EvalJs()
    ctx.execute('var x = 0; x ||= 5; var y = x;', es12=True)
    assert ctx.y == 5


def test_nullish_assign():
    ctx = js2py.EvalJs()
    ctx.execute('var x = null; x ??= 7; var y = x;', es12=True)
    assert ctx.y == 7
    ctx.execute('var z = 0; z ??= 9;', es12=True)
    assert ctx.z == 0


def test_string_replace_all():
    assert js2py.eval_js('"a-a-a".replaceAll("-", "+")', es12=True) == 'a+a+a'


def test_promise_any_fulfilled():
    reset_event_loop()
    ctx = js2py.EvalJs()
    ctx.execute('''
        var out;
        Promise.any([
            Promise.reject("nope"),
            Promise.resolve(42)
        ]).then(function(v) { out = v; });
    ''', es12=True)
    assert ctx.out == 42


def test_promise_any_all_rejected():
    reset_event_loop()
    ctx = js2py.EvalJs()
    ctx.execute('''
        var err = null;
        Promise.any([
            Promise.reject("a"),
            Promise.reject("b")
        ]).catch(function(e) { err = e; });
    ''', es12=True)
    assert ctx.err is not None


def test_eval_js12():
    assert js2py.eval_js12('1_00 * 2') == 200


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
