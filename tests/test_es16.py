"""Tests for ES16 (ES2025) JavaScript support."""
import js2py
from js2py.es16 import looks_like_es16
from js2py.event_loop import drain_event_loop


def test_looks_like_es16():
    assert looks_like_es16('RegExp.escape("x")')
    assert looks_like_es16('Promise.try(function() {})')
    assert looks_like_es16('JSON.rawJSON("1")')
    assert looks_like_es16('JSON.isRawJSON({})')
    assert not looks_like_es16('JSON.parse("{}")')


def test_regexp_escape_literal():
    assert js2py.eval_js('RegExp.escape("hello")', es16=True) == '\\x68ello'


def test_regexp_escape_syntax():
    assert js2py.eval_js('RegExp.escape("(a|b)")', es16=True) == '\\(a\\|b\\)'


def test_regexp_escape_match():
    assert js2py.eval_js(
        'new RegExp(RegExp.escape("a*b")).test("a*b")', es16=True) is True


def test_regexp_escape_auto():
    assert js2py.eval_js('RegExp.escape("x.y").indexOf("\\\\.") >= 0', es16='auto') is True


def test_promise_try_success():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var out;
        Promise.try(function() { return 7; }).then(function(v) { out = v; });
    ''', es16=True)
    drain_event_loop()
    assert ctx.out == 7


def test_promise_try_with_args():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var out;
        Promise.try(function(a, b) { return a + b; }, 3, 4).then(function(v) { out = v; });
    ''', es16=True)
    drain_event_loop()
    assert ctx.out == 7


def test_promise_try_reject():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var err;
        Promise.try(function() { throw "boom"; }).catch(function(e) { err = e; });
    ''', es16=True)
    drain_event_loop()
    assert ctx.err == 'boom'


def test_json_raw_json_stringify():
    assert js2py.eval_js('JSON.stringify(JSON.rawJSON("1"))', es16=True) == '1'
    assert js2py.eval_js('JSON.stringify(JSON.rawJSON("\\"hi\\""))', es16=True) == '"hi"'


def test_json_raw_json_embedded():
    assert js2py.eval_js(
        'JSON.stringify({x: JSON.rawJSON("\\"hi\\"")})', es16=True) == '{"x":"hi"}'


def test_json_is_raw_json():
    assert js2py.eval_js('JSON.isRawJSON(JSON.rawJSON("1"))', es16=True) is True
    assert js2py.eval_js('JSON.isRawJSON(1)', es16=True) is False


def test_eval_js16():
    assert js2py.eval_js16('RegExp.escape("test")') == '\\x74est'


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
