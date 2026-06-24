"""Tests for ES6 JavaScript translation support."""
import js2py
from js2py.es6 import looks_like_es6


def test_looks_like_es6():
    assert looks_like_es6('let a = () => 1')
    assert looks_like_es6('class Foo {}')
    assert not looks_like_es6('var a = 1; function f() { return a; }')


def test_native_default_parameters():
    ctx = js2py.EvalJs()
    ctx.execute('function f(x, y) { y = (y === undefined) ? 2 : y; return x + y; }')
    assert ctx.f(1) == 3
    ctx2 = js2py.EvalJs()
    ctx2.execute('function f(x, y=2) { return x + y; }')
    assert ctx2.f(1) == 3
    assert ctx2.f(1, 5) == 6


def test_native_object_shorthand():
    assert js2py.eval_js('var x = 10; ({x}).x') == 10


def test_native_computed_property():
    assert js2py.eval_js('var k = "foo"; ({[k]: 42}).foo') == 42


def test_eval_js_auto_es6():
    assert js2py.eval_js('(() => 11)()', es6=True) == 11


def test_eval_js6_arrow_this():
    result = js2py.eval_js6('''
const v = 11;
obj = {value: v};
obj.x = function() {
    return () => this
};
obj.x()()
''')
    assert result.value == 11


def test_eval_js6_for_of():
    assert js2py.eval_js6('''
var x;
for (let a of [1,2,3]) {
    x = a
}
typeof a === 'undefined' && x === 3
''')


def test_eval_js6_class():
    shape = js2py.eval_js6('''
class Shape {
    constructor (id, x, y) {
        this.id = id
        this.move(x, y)
    }
    move (x, y) {
        this.x = x
        this.y = y
    }
};
new Shape(1,2,3)
''')
    assert shape.x == 2


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
