"""Tests for async/await support."""
import js2py
from js2py.async_js import looks_like_async, downlevel_async_await
from js2py.event_loop import reset_event_loop


def _await_promise(ctx, expr, *args):
    arg_str = ', '.join(str(a).lower() if isinstance(a, bool) else repr(a)
                        for a in args)
    call = '%s(%s)' % (expr, arg_str) if arg_str else '%s()' % expr
    ctx.eval('var __v; %s.then(function(x){ __v = x; });' % call, async_js=True)
    return ctx.__v


def test_looks_like_async():
    assert looks_like_async('async function f() {}')
    assert looks_like_async('await Promise.resolve(1)')
    assert not looks_like_async('function f() { return 1; }')


def test_downlevel_return_await():
    code = downlevel_async_await(
        'async function f() { return await Promise.resolve(1); }')
    assert 'async' not in code
    assert 'Promise.resolve' in code


def test_promise_resolve():
    ctx = js2py.EvalJs()
    ctx.execute('var v; Promise.resolve(42).then(function(x){ v = x; });')
    assert ctx.v == 42


def test_promise_microtask_order():
    log = []
    ctx = js2py.EvalJs({'log': log.append})
    ctx.execute('''
log("sync1");
Promise.resolve().then(function(){ log("micro"); });
log("sync2");
''')
    assert log == ['sync1', 'sync2', 'micro']


def test_setTimeout_defers():
    log = []
    ctx = js2py.EvalJs({'log': log.append})
    ctx.execute('''
log("a");
setTimeout(function(){ log("b"); }, 0);
log("c");
''')
    assert log == ['a', 'c', 'b']


def test_async_return_await():
    ctx = js2py.EvalJs()
    ctx.execute(
        'async function f() { return await Promise.resolve(42); }', async_js=True)
    assert _await_promise(ctx, 'f') == 42


def test_async_sequential_await():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f() {
  var a = await Promise.resolve(10);
  var b = await Promise.resolve(32);
  return a + b;
}
''', async_js=True)
    assert _await_promise(ctx, 'f') == 42


def test_async_for_loop_await():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f() {
  var sum = 0;
  for (var i = 0; i < 4; i++) {
    sum += await Promise.resolve(i);
  }
  return sum;
}
''', async_js=True)
    assert _await_promise(ctx, 'f') == 6


def test_async_while_loop_await():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f() {
  var n = 3, sum = 0;
  while (n--) {
    sum += await Promise.resolve(1);
  }
  return sum;
}
''', async_js=True)
    assert _await_promise(ctx, 'f') == 3


def test_async_try_catch_await():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f() {
  try {
    return await Promise.reject("fail");
  } catch (e) {
    return 99;
  }
}
''', async_js=True)
    assert _await_promise(ctx, 'f') == 99


def test_async_try_catch_success():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f() {
  try {
    return await Promise.resolve(12);
  } catch (e) {
    return -1;
  }
}
''', async_js=True)
    assert _await_promise(ctx, 'f') == 12


def test_async_if_await():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function f(flag) {
  var r = 0;
  if (flag) {
    r = await Promise.resolve(5);
  } else {
    r = await Promise.resolve(1);
  }
  return r;
}
''', async_js=True)
    assert _await_promise(ctx, 'f', True) == 5
    assert _await_promise(ctx, 'f', False) == 1


def test_async_nested():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function inner(x) { return await Promise.resolve(x * 2); }
async function f() { return await inner(21); }
''', async_js=True)
    assert _await_promise(ctx, 'f') == 42


def test_async_deeply_nested():
    ctx = js2py.EvalJs()
    ctx.execute('''
async function c() { return await Promise.resolve(3); }
async function b() { return await c() + 1; }
async function a() { return await b() + 1; }
''', async_js=True)
    assert _await_promise(ctx, 'a') == 5


def test_async_arrow():
    ctx = js2py.EvalJs()
    ctx.execute(
        'var g = async function() { return await Promise.resolve(7); };',
        async_js=True)
    assert _await_promise(ctx, 'g') == 7


def test_eval_js_async():
    ctx = js2py.EvalJs()
    ctx.execute(
        'async function f(){ return await Promise.resolve(5);} '
        'var v; f().then(function(x){ v = x; });',
        async_js=True)
    assert ctx.v == 5


if __name__ == '__main__':
    import inspect
    import sys

    reset_event_loop()
    failed = 0
    for name, func in sorted(inspect.getmembers(sys.modules[__name__], inspect.isfunction)):
        if not name.startswith('test_'):
            continue
        try:
            func()
            reset_event_loop()
            print('ok', name)
        except Exception as exc:
            failed += 1
            reset_event_loop()
            print('FAIL', name, exc)
    sys.exit(1 if failed else 0)
