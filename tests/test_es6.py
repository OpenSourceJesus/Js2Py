"""Tests for ES6 JavaScript translation support."""
import js2py
from js2py.es6 import looks_like_es6


def test_looks_like_es6():
    assert looks_like_es6('let a = () => 1')
    assert looks_like_es6('class Foo {}')
    assert not looks_like_es6('var a = 1; function f() { return a; }')


def test_native_default_parameters():
    f = js2py.eval_js('function f(x, y) { y = (y === undefined) ? 2 : y; return x + y; }')
    assert f(1) == 3
    f2 = js2py.eval_js('function f(x, y=2) { return x + y; }')
    assert f2(1) == 3
    assert f2(1, 5) == 6


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
