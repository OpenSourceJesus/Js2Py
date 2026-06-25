"""Tests for ES11 (ES2020) JavaScript support."""
import js2py
from js2py.es11 import looks_like_es11, prepare_es11
from js2py.event_loop import reset_event_loop


def test_looks_like_es11():
    assert looks_like_es11('a?.b')
    assert looks_like_es11('x ?? y')
    assert looks_like_es11('globalThis')
    assert looks_like_es11('Promise.allSettled([])')
    assert not looks_like_es11('var a = 1; a.b')


def test_prepare_es11_nullish():
    out = prepare_es11('a ?? b')
    assert '!== null' in out and '!== undefined' in out


def test_prepare_es11_optional_chain():
    out = prepare_es11('obj?.prop')
    assert '_r' in out and '== null' in out


def test_nullish_coalescing():
    assert js2py.eval_js('0 ?? 1', es11=True) == 0
    assert js2py.eval_js('null ?? 2', es11=True) == 2
    assert js2py.eval_js('undefined ?? 3', es11=True) == 3


def test_nullish_coalescing_chain():
    assert js2py.eval_js('null ?? null ?? 4', es11=True) == 4


def test_optional_chaining_property():
    ctx = js2py.EvalJs({'obj': {'x': 9}})
    ctx.execute('var v = obj?.x;', es11=True)
    assert ctx.v == 9


def test_optional_chaining_null():
    assert js2py.eval_js('null?.missing', es11=True) is None


def test_optional_chaining_nested():
    ctx = js2py.EvalJs({'obj': {'inner': {'y': 5}}})
    ctx.execute('var v = obj?.inner?.y;', es11=True)
    assert ctx.v == 5


def test_optional_chaining_auto():
    ctx = js2py.EvalJs({'a': {'b': 7}})
    ctx.execute('var v = a?.b;', es11='auto')
    assert ctx.v == 7


def test_global_this():
    ctx = js2py.EvalJs()
    ctx.execute('var same = (globalThis === window);', es11=True)
    assert ctx.same is True


def test_promise_all_settled():
    reset_event_loop()
    ctx = js2py.EvalJs()
    ctx.execute('''
        var out;
        Promise.allSettled([
            Promise.resolve(1),
            Promise.reject("no")
        ]).then(function(r) { out = r; });
    ''', es11=True)
    assert list(ctx.out)[0]['status'] == 'fulfilled'
    assert list(ctx.out)[0]['value'] == 1
    assert list(ctx.out)[1]['status'] == 'rejected'
    assert list(ctx.out)[1]['reason'] == 'no'


def test_eval_js11():
    assert js2py.eval_js11('(null ?? 5) + 1') == 6


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
