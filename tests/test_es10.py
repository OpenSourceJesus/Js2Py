"""Tests for ES10 (ES2019) JavaScript support."""
import js2py
from js2py.es10 import looks_like_es10, prepare_es10


def test_looks_like_es10():
    assert looks_like_es10('[1, [2]].flat()')
    assert looks_like_es10('" x".trimStart()')
    assert looks_like_es10('try {} catch {}')
    assert not looks_like_es10('var a = [1, 2]; a.join()')


def test_prepare_es10_optional_catch():
    out = prepare_es10('try { x(); } catch { y = 1; }')
    assert '__PyJsOptionalCatch' in out


def test_array_flat():
    ctx = js2py.EvalJs()
    ctx.execute('var a = [1, [2, 3], [[4]]]; var b = a.flat();', es10=True)
    assert list(ctx.b) == [1, 2, 3, [4]]


def test_array_flat_depth():
    ctx = js2py.EvalJs()
    ctx.execute('var a = [1, [2, [3]]]; var b = a.flat(2);', es10=True)
    assert list(ctx.b) == [1, 2, 3]


def test_array_flat_map():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var a = [1, 2, 3]; var b = a.flatMap(function(x) { return [x, x * 10]; });',
        es10=True)
    assert list(ctx.b) == [1, 10, 2, 20, 3, 30]


def test_array_flat_auto():
    ctx = js2py.EvalJs()
    ctx.execute('var out = [0, [1]].flat();', es10='auto')
    assert list(ctx.out) == [0, 1]


def test_string_trim_start():
    assert js2py.eval_js('"  hello".trimStart()', es10=True) == 'hello'
    assert js2py.eval_js('"  hello".trimLeft()', es10=True) == 'hello'


def test_string_trim_end():
    assert js2py.eval_js('"hello  ".trimEnd()', es10=True) == 'hello'
    assert js2py.eval_js('"hello  ".trimRight()', es10=True) == 'hello'


def test_optional_catch_binding():
    ctx = js2py.EvalJs()
    ctx.execute('''
        var ok = false;
        try { throw "boom"; } catch { ok = true; }
    ''', es10=True)
    assert ctx.ok is True


def test_eval_js10():
    assert js2py.eval_js10('[1, [2]].flat().length') == 2


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
