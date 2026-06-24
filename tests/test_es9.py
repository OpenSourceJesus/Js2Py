"""Tests for ES9 (ES2018) JavaScript support."""
import js2py
from js2py.es9 import looks_like_es9, prepare_es9
from js2py.event_loop import reset_event_loop


def test_looks_like_es9():
    assert looks_like_es9('var x = {...a};')
    assert looks_like_es9('Promise.resolve(1).finally(function() {})')
    assert looks_like_es9('Object.fromEntries([])')
    assert not looks_like_es9('var a = 1; Object.keys({})')


def test_prepare_es9_object_spread():
    out = prepare_es9('var x = {...a, b: 2};')
    assert '__o' in out
    assert 'b = 2' in out or 'b=2' in out.replace(' ', '')


def test_object_assign():
    ctx = js2py.EvalJs()
    ctx.execute('var a = {x: 1}; var b = {y: 2}; var c = Object.assign({}, a, b);')
    assert ctx.c.x == 1
    assert ctx.c.y == 2


def test_object_spread_literal():
    ctx = js2py.EvalJs({'src': {'a': 1, 'b': 2}})
    ctx.execute('var merged = {...src, c: 3};', es9=True)
    assert ctx.merged.a == 1
    assert ctx.merged.b == 2
    assert ctx.merged.c == 3


def test_object_spread_auto():
    ctx = js2py.EvalJs({'base': {'x': 9}})
    ctx.execute('var out = {...base, y: 1};', es9='auto')
    assert ctx.out.x == 9
    assert ctx.out.y == 1


def test_object_rest_destructuring():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var obj = {a: 1, b: 2, c: 3}; var {a, ...rest} = obj;', es9=True)
    assert ctx.a == 1
    assert ctx.rest.b == 2
    assert ctx.rest.c == 3
    assert ctx.rest.a is None or str(getattr(ctx.rest, 'a', None)) in ('undefined', 'None')


def test_object_from_entries():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var o = Object.fromEntries([["a", 1], ["b", 2]]);', es9=True)
    assert ctx.o.a == 1
    assert ctx.o.b == 2


def test_object_entries_roundtrip():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var src = {p: 4, q: 5}; var copy = Object.fromEntries(Object.entries(src));',
        es9=True)
    assert ctx.copy.p == 4
    assert ctx.copy.q == 5


def test_promise_finally_fulfilled():
    reset_event_loop()
    ctx = js2py.EvalJs()
    ctx.execute('''
        var log = [];
        Promise.resolve(10).finally(function() { log.push("done"); }).then(function(v) {
            log.push(v);
        });
    ''', es9=True)
    assert list(ctx.log) == ['done', 10]


def test_promise_finally_rejected():
    reset_event_loop()
    ctx = js2py.EvalJs()
    ctx.execute('''
        var log = [];
        Promise.reject("err").finally(function() { log.push("cleanup"); }).catch(function(e) {
            log.push(e);
        });
    ''', es9=True)
    assert list(ctx.log) == ['cleanup', 'err']


def test_eval_js9():
    assert js2py.eval_js9('Object.assign({a:1}, {b:2}).b') == 2


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
