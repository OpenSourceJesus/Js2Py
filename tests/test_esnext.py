"""Tests for ES.Next (staging) JavaScript support."""
import js2py
from js2py.esnext import looks_like_esnext, prepare_esnext


def test_looks_like_esnext():
    assert looks_like_esnext('Error.isError(new Error("x"))')
    assert looks_like_esnext('Iterator.concat([[1]])')
    assert looks_like_esnext('{ using x = foo(); }')
    assert not looks_like_esnext('Error("x")')


def test_prepare_esnext_using():
    out = prepare_esnext('{ using r = get(); x = 1; }')
    assert 'try {' in out
    assert 'finally {' in out
    assert 'r.dispose' in out
    assert 'using ' not in out


def test_error_is_error_true():
    assert js2py.eval_js('Error.isError(new Error("x"))', esnext=True) is True
    assert js2py.eval_js('Error.isError(new TypeError("x"))', esnext=True) is True


def test_error_is_error_false():
    assert js2py.eval_js('Error.isError({})', esnext=True) is False
    assert js2py.eval_js('Error.isError("err")', esnext=True) is False


def test_iterator_concat_arrays():
    js = '''
        var it = Iterator.concat([1, 2], [3]);
        var out = [];
        var step;
        while (!(step = it.next()).done) { out.push(step.value); }
        out.length
    '''
    assert js2py.eval_js(js, esnext=True) == 3


def test_iterator_concat_values():
    assert js2py.eval_js(
        'Iterator.concat([10, 20]).next().value', esnext=True) == 10


def test_iterator_concat_auto():
    assert js2py.eval_js(
        'Iterator.concat([5]).next().value', esnext='auto') == 5


def test_using_dispose():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var disposed = false;
        var result;
        {
            using r = { dispose: function() { disposed = true; } };
            result = 42;
        }
    ''', esnext=True)
    assert ctx.result == 42
    assert ctx.disposed is True


def test_using_dispose_on_throw():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var disposed = false;
        try {
            {
                using r = { dispose: function() { disposed = true; } };
                throw "fail";
            }
        } catch (e) {}
    ''', esnext=True)
    assert ctx.disposed is True


def test_eval_jsnext():
    assert js2py.eval_jsnext('Error.isError(new Error(1))') is True


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
