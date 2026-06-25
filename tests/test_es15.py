"""Tests for ES15 (ES2024) JavaScript support."""
import js2py
from js2py.es15 import looks_like_es15
from js2py.event_loop import drain_event_loop


def test_looks_like_es15():
    assert looks_like_es15('Object.groupBy([], function() {})')
    assert looks_like_es15('Promise.withResolvers()')
    assert looks_like_es15('"x".isWellFormed()')
    assert looks_like_es15('Math.sumPrecise(1, 2)')
    assert not looks_like_es15('Object.keys({})')


def test_object_group_by():
    js = '''
        Object.groupBy([1, 2, 3, 4, 5, 6], function(x) {
            return x % 2 === 0 ? "even" : "odd";
        }).even.length
    '''
    assert js2py.eval_js(js, es15=True) == 3
    js2 = '''
        Object.groupBy([1, 2, 3, 4, 5, 6], function(x) {
            return x % 2 === 0 ? "even" : "odd";
        }).even[0]
    '''
    assert js2py.eval_js(js2, es15=True) == 2


def test_object_group_by_auto():
    assert js2py.eval_js(
        'Object.groupBy(["a", "b", "aa"], function(s) { return s.length; })["1"].length',
        es15='auto') == 2
    assert js2py.eval_js(
        'Object.groupBy(["a", "b", "aa"], function(s) { return s.length; })["2"][0]',
        es15='auto') == 'aa'


def test_promise_with_resolvers():
    ctx = js2py.EvalJs()
    ctx.execute('var r = Promise.withResolvers(); r.resolve(42);', es15=True)
    drain_event_loop()
    assert ctx.r.promise is not None


def test_promise_with_resolvers_value():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var out;
        var r = Promise.withResolvers();
        r.promise.then(function(v) { out = v; });
        r.resolve(99);
    ''', es15=True)
    drain_event_loop()
    assert ctx.out == 99


def test_string_is_well_formed_true():
    assert js2py.eval_js('"hello".isWellFormed()', es15=True) is True


def test_string_is_well_formed_false():
    assert js2py.eval_js('"\\uD800".isWellFormed()', es15=True) is False


def test_string_to_well_formed():
    assert js2py.eval_js('"\\uD800".toWellFormed()', es15=True) == '\ufffd'


def test_math_sum_precise():
    assert js2py.eval_js('Math.sumPrecise(1, 2, 3)', es15=True) == 6


def test_math_sum_precise_floats():
    assert js2py.eval_js('Math.sumPrecise(1e20, 1, -1e20)', es15=True) == 1


def test_eval_js15():
    assert js2py.eval_js15('Math.sumPrecise(10, 20)') == 30


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
