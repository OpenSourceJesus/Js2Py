# coding=utf-8
from .translators import translate_js, DEFAULT_HEADER
from .translators.translator import _prepare_js_source
from .event_loop import drain_event_loop
import sys
import time
import json
import six
import os
import hashlib
import codecs

__all__ = [
    'EvalJs', 'translate_js', 'import_js', 'eval_js', 'translate_file',
    'eval_js6', 'translate_js6', 'eval_js7', 'translate_js7',
    'eval_js8', 'translate_js8', 'eval_js9', 'translate_js9',
    'eval_js10', 'translate_js10', 'eval_js11', 'translate_js11',
    'eval_js12', 'translate_js12', 'eval_js13', 'translate_js13',
    'eval_js14', 'translate_js14', 'eval_js15', 'translate_js15',
    'eval_js16', 'translate_js16', 'eval_jsnext', 'translate_jsnext',
    'run_file', 'disable_pyimport', 'drain_event_loop',
    'get_file_contents', 'write_file_contents'
]
DEBUG = False


def _strip_leading_use_strict(code):
    code = code.lstrip('\ufeff')
    while True:
        stripped = code.lstrip()
        for quote in ('"', "'"):
            directive = quote + 'use strict' + quote
            if stripped.startswith(directive):
                rest = stripped[len(directive):].lstrip()
                if rest.startswith(';'):
                    code = rest[1:].lstrip()
                    break
                return code
        else:
            return code


def _split_top_level_statements(code):
    parts = []
    current = []
    depth = 0
    in_single = in_double = in_template = False
    escape = False
    for char in code:
        if escape:
            escape = False
            current.append(char)
            continue
        if char == '\\' and (in_single or in_double):
            escape = True
            current.append(char)
            continue
        if not in_single and not in_double and not in_template:
            if char == "'":
                in_single = True
            elif char == '"':
                in_double = True
            elif char == '`':
                in_template = True
            elif char in '({[':
                depth += 1
            elif char in ')}]':
                depth = max(0, depth - 1)
            elif char == ';' and depth == 0:
                part = ''.join(current).strip()
                if part:
                    parts.append(part)
                current = []
                continue
            elif char == '\n' and depth == 0:
                part = ''.join(current).strip()
                if part:
                    parts.append(part)
                    current = []
                continue
        elif in_single and char == "'":
            in_single = False
        elif in_double and char == '"':
            in_double = False
        elif in_template and char == '`':
            in_template = False
        current.append(char)
    remainder = ''.join(current).strip()
    if remainder:
        parts.append(remainder)
    return parts


def _wrap_js_for_eval(prepared):
    """Wrap prepared JS so the last statement's value becomes PyJsEvalResult."""
    prepared = _strip_leading_use_strict(prepared).strip()
    if not prepared:
        return 'PyJsEvalResult = undefined'
    parts = _split_top_level_statements(prepared)
    if len(parts) == 1:
        return 'PyJsEvalResult = (%s)' % parts[0]
    body = ';\n'.join(parts[:-1])
    return '%s;\nPyJsEvalResult = %s' % (body, parts[-1])


def disable_pyimport():
    import pyjsparser.parser
    pyjsparser.parser.ENABLE_PYIMPORT = False


def path_as_local(path):
    if os.path.isabs(path):
        return path
    # relative to cwd
    return os.path.join(os.getcwd(), path)


def import_js(path, lib_name, globals):
    """Imports from javascript source file.
      globals is your globals()"""
    with codecs.open(path_as_local(path), "r", "utf-8") as f:
        js = f.read()
    e = EvalJs()
    e.execute(js)
    var = e.context['var']
    globals[lib_name] = var.to_python()


def get_file_contents(path_or_file):
    if hasattr(path_or_file, 'read'):
        js = path_or_file.read()
    else:
        with codecs.open(path_as_local(path_or_file), "r", "utf-8") as f:
            js = f.read()
    return js


def write_file_contents(path_or_file, contents):
    if hasattr(path_or_file, 'write'):
        path_or_file.write(contents)
    else:
        with codecs.open(path_as_local(path_or_file), "w", "utf-8") as f:
            f.write(contents)


def translate_file(input_path, output_path, es6=False, es7=False, es8=False, es9=False, es10=False,
                   es11=False, es12=False, es13=False, es14=False, es15=False, es16=False, esnext=False):
    '''
    Translates input JS file to python and saves the it to the output path.
    It appends some convenience code at the end so that it is easy to import JS objects.

    es6: False, True, or 'auto' — transpile ES6 via Babel before translation.
    es7: False, True, or 'auto' — enable ES2016 features (**, includes).
    es8: False, True, or 'auto' — enable ES2017 features (padStart, Object.values).
    es9: False, True, or 'auto' — enable ES2018 features (object spread/rest, etc.).
    es10: False, True, or 'auto' — enable ES2019 features (flat, trimStart, etc.).
    es11: False, True, or 'auto' — enable ES2020 features (??, ?., globalThis).
    es12: False, True, or 'auto' — enable ES2021 features (&&=, numeric separators).
    es13: False, True, or 'auto' — enable ES2022 features (at, Object.hasOwn).
    es14: False, True, or 'auto' — enable ES2023 features (findLast, hashbang).
    es15: False, True, or 'auto' — enable ES2024 features (groupBy, withResolvers).
    es16: False, True, or 'auto' — enable ES2025 features (RegExp.escape, Promise.try).
    esnext: False, True, or 'auto' — enable ES.Next staging features (isError, using).

    For example we have a file 'example.js' with:   var a = function(x) {return x}
    translate_file('example.js', 'example.py')

    Now example.py can be easily importend and used:
    >>> from example import example
    >>> example.a(30)
    30
    '''
    js = get_file_contents(input_path)

    py_code = translate_js(js, es6=es6, es7=es7, es8=es8, es9=es9, es10=es10, es11=es11,
                           es12=es12, es13=es13, es14=es14, es15=es15, es16=es16, esnext=esnext)
    lib_name = os.path.basename(output_path).split('.')[0]
    head = '__all__ = [%s]\n\n# Don\'t look below, you will not understand this Python code :) I don\'t.\n\n' % repr(
        lib_name)
    tail = '\n\n# Add lib to the module scope\n%s = var.to_python()' % lib_name
    out = head + py_code + tail
    write_file_contents(output_path, out)


def run_file(path_or_file, context=None):
    ''' Context must be EvalJS object. Runs given path as a JS program. Returns (eval_value, context).
    '''
    if context is None:
        context = EvalJs()
    if not isinstance(context, EvalJs):
        raise TypeError('context must be the instance of EvalJs')
    eval_value = context.eval(get_file_contents(path_or_file))
    return eval_value, context


def eval_js(js, es6=False, es7=False, es8=False, es9=False, es10=False, es11=False, es12=False,
            es13=False, es14=False, es15=False, es16=False, esnext=False):
    """Just like javascript eval. Translates javascript to python,
       executes and returns python object.
       js is javascript source code

       es6: False, True, or 'auto' — see translate_js.
       es7: False, True, or 'auto' — enable ES2016 features.
       es8: False, True, or 'auto' — enable ES2017 features.
       es9: False, True, or 'auto' — enable ES2018 features.
       es10: False, True, or 'auto' — enable ES2019 features.
       es11: False, True, or 'auto' — enable ES2020 features.
       es12: False, True, or 'auto' — enable ES2021 features.
       es13: False, True, or 'auto' — enable ES2022 features.
       es14: False, True, or 'auto' — enable ES2023 features.
       es15: False, True, or 'auto' — enable ES2024 features.
       es16: False, True, or 'auto' — enable ES2025 features.
       esnext: False, True, or 'auto' — enable ES.Next staging features.

       EXAMPLE:
        >>> import js2py
        >>> add = js2py.eval_js('function add(a, b) {return a + b}')
        >>> add(1, 2) + 3
        6
        >>> add('1', 2, 3)
        u'12'
        >>> add.constructor
        function Function() { [python code] }

       NOTE: For Js Number, String, Boolean and other base types returns appropriate python BUILTIN type.
       For Js functions and objects, returns Python wrapper - basically behaves like normal python object.
       If you really want to convert object to python dict you can use to_dict method.
       """
    e = EvalJs()
    result = e.eval(js, es6=es6, es7=es7, es8=es8, es9=es9, es10=es10, es11=es11, es12=es12,
                    es13=es13, es14=es14, es15=es15, es16=es16, esnext=esnext)
    drain_event_loop()
    return result


def eval_jsnext(js):
    """Like eval_js with ES.Next staging support enabled."""
    return eval_js(js, esnext=True)


def translate_jsnext(js):
    """Like translate_js with ES.Next staging support enabled."""
    return translate_js(js, esnext=True)


def eval_js16(js):
    """Like eval_js with ES2025 support enabled."""
    return eval_js(js, es16=True)


def translate_js16(js):
    """Like translate_js with ES2025 support enabled."""
    return translate_js(js, es16=True)


def eval_js15(js):
    """Like eval_js with ES2024 support enabled."""
    return eval_js(js, es15=True)


def translate_js15(js):
    """Like translate_js with ES2024 support enabled."""
    return translate_js(js, es15=True)


def eval_js14(js):
    """Like eval_js with ES2023 support enabled."""
    return eval_js(js, es14=True)


def translate_js14(js):
    """Like translate_js with ES2023 support enabled."""
    return translate_js(js, es14=True)


def eval_js13(js):
    """Like eval_js with ES2022 support enabled."""
    return eval_js(js, es13=True)


def translate_js13(js):
    """Like translate_js with ES2022 support enabled."""
    return translate_js(js, es13=True)


def eval_js12(js):
    """Like eval_js with ES2021 support enabled."""
    return eval_js(js, es12=True)


def translate_js12(js):
    """Like translate_js with ES2021 support enabled."""
    return translate_js(js, es12=True)


def eval_js11(js):
    """Like eval_js with ES2020 support enabled."""
    return eval_js(js, es11=True)


def translate_js11(js):
    """Like translate_js with ES2020 support enabled."""
    return translate_js(js, es11=True)


def eval_js10(js):
    """Like eval_js with ES2019 support enabled."""
    return eval_js(js, es10=True)


def translate_js10(js):
    """Like translate_js with ES2019 support enabled."""
    return translate_js(js, es10=True)


def eval_js9(js):
    """Like eval_js with ES2018 support enabled."""
    return eval_js(js, es9=True)


def translate_js9(js):
    """Like translate_js with ES2018 support enabled."""
    return translate_js(js, es9=True)


def eval_js6(js):
    """Just like eval_js but with experimental support for js6 via babel."""
    return eval_js(js, es6=True)


def translate_js6(js):
    """Just like translate_js but with experimental support for js6 via babel."""
    return translate_js(js, es6=True)


def eval_js7(js):
    """Like eval_js with ES2016 support enabled."""
    return eval_js(js, es7=True)


def translate_js7(js):
    """Like translate_js with ES2016 support enabled."""
    return translate_js(js, es7=True)


def eval_js8(js):
    """Like eval_js with ES2017 support enabled."""
    return eval_js(js, es8=True)


def translate_js8(js):
    """Like translate_js with ES2017 support enabled."""
    return translate_js(js, es8=True)


class EvalJs(object):
    """This class supports continuous execution of javascript under same context.

        >>> ctx = EvalJs()
        >>> ctx.execute('var a = 10;function f(x) {return x*x};')
        >>> ctx.f(9)
        81
        >>> ctx.a
        10

        context is a python dict or object that contains python variables that should be available to JavaScript
        For example:
        >>> ctx = EvalJs({'a': 30})
        >>> ctx.execute('var x = a')
        >>> ctx.x
        30

        You can enable JS require function via enable_require. With this feature enabled you can use js modules
        from npm, for example:
        >>> ctx = EvalJs(enable_require=True)
        >>> ctx.execute("var esprima = require('esprima');")
        >>> ctx.execute("esprima.parse('var a = 1')")

       You can run interactive javascript console with console method!"""

    def __init__(self, context={}, enable_require=False):
        self.__dict__['_context'] = {}
        exec (DEFAULT_HEADER, self._context)
        self.__dict__['_var'] = self._context['var'].to_python()

        if enable_require:
            def _js_require_impl(npm_module_name):
                from .node_import import require
                from .base import to_python
                return require(to_python(npm_module_name), context=self._context)
            setattr(self._var, 'require', _js_require_impl)

        if not isinstance(context, dict):
            try:
                context = context.__dict__
            except:
                raise TypeError(
                    'context has to be either a dict or have __dict__ attr')
        for k, v in six.iteritems(context):
            setattr(self._var, k, v)

    def execute(self, js=None, use_compilation_plan=False, es6=False, es7=False, es8=False, es9=False,
                es10=False, es11=False, es12=False, es13=False, es14=False, es15=False, es16=False, esnext=False):
        """executes javascript js in current context

        es6: False, True, or 'auto' — transpile ES6 via Babel before translation.
        es7: False, True, or 'auto' — enable ES2016 features.
        es8: False, True, or 'auto' — enable ES2017 features.
        es9: False, True, or 'auto' — enable ES2018 features.
        es10: False, True, or 'auto' — enable ES2019 features.
        es11: False, True, or 'auto' — enable ES2020 features.
        es12: False, True, or 'auto' — enable ES2021 features.
        es13: False, True, or 'auto' — enable ES2022 features.
        es14: False, True, or 'auto' — enable ES2023 features.
        es15: False, True, or 'auto' — enable ES2024 features.
        es16: False, True, or 'auto' — enable ES2025 features.
        esnext: False, True, or 'auto' — enable ES.Next staging features.

        During initial execute() the converted js is cached for re-use. That means next time you
        run the same javascript snippet you save many instructions needed to parse and convert the
        js code to python code.

        This cache causes minor overhead (a cache dicts is updated) but the Js=>Py conversion process
        is typically expensive compared to actually running the generated python code.

        Note that the cache is just a dict, it has no expiration or cleanup so when running this
        in automated situations with vast amounts of snippets it might increase memory usage.
        """
        try:
            cache = self.__dict__['cache']
        except KeyError:
            cache = self.__dict__['cache'] = {}
        cache_key = (hashlib.md5(js.encode('utf-8')).digest(), es6, es7, es8, es9, es10,
                     es11, es12, es13, es14, es15, es16, esnext)
        try:
            compiled = cache[cache_key]
        except KeyError:
            code = translate_js(
                js, '', use_compilation_plan=use_compilation_plan,
                es6=es6, es7=es7, es8=es8, es9=es9, es10=es10, es11=es11, es12=es12,
                es13=es13, es14=es14, es15=es15, es16=es16, esnext=esnext)
            compiled = cache[cache_key] = compile(code, '<EvalJS snippet>',
                                                'exec')
        exec (compiled, self._context)
        drain_event_loop()

    def eval(self, expression, use_compilation_plan=False, es6=False, es7=False, es8=False, es9=False,
             es10=False, es11=False, es12=False, es13=False, es14=False, es15=False, es16=False, esnext=False):
        """evaluates expression in current context and returns its value"""
        expression = _prepare_js_source(
            expression, es6=es6, es7=es7, es8=es8, es9=es9, es10=es10, es11=es11, es12=es12,
            es13=es13, es14=es14, es15=es15, es16=es16, esnext=esnext)
        code = _wrap_js_for_eval(expression)
        self.execute(code, use_compilation_plan=use_compilation_plan,
                     es6=es6, es7=es7, es8=es8, es9=es9, es10=es10, es11=es11, es12=es12,
                     es13=es13, es14=es14, es15=es15, es16=es16, esnext=esnext)
        return self['PyJsEvalResult']

    def execute_debug(self, js):
        """executes javascript js in current context
        as opposed to the (faster) self.execute method, you can use your regular debugger
        to set breakpoints and inspect the generated python code
        """
        code = translate_js(js, '')
        # make sure you have a temp folder:
        filename = 'temp' + os.sep + '_' + hashlib.md5(
            code.encode("utf-8")).hexdigest() + '.py'
        try:
            with open(filename, mode='w') as f:
                f.write(code)
            with open(filename, "r") as f:
                pyCode = compile(f.read(), filename, 'exec')
                exec(pyCode, self._context)
                
        except Exception as err:
            raise err
        finally:
            os.remove(filename)
            try:
                os.remove(filename + 'c')
            except:
                pass

    def eval_debug(self, expression):
        """evaluates expression in current context and returns its value
        as opposed to the (faster) self.execute method, you can use your regular debugger
        to set breakpoints and inspect the generated python code
        """
        code = 'PyJsEvalResult = eval(%s)' % json.dumps(expression)
        self.execute_debug(code)
        return self['PyJsEvalResult']

    @property
    def context(self):
        return self._context
    
    def __getattr__(self, var):
        return getattr(self._var, var)

    def __getitem__(self, var):
        return getattr(self._var, var)

    def __setattr__(self, var, val):
        return setattr(self._var, var, val)

    def __setitem__(self, var, val):
        return setattr(self._var, var, val)

    def console(self):
        """starts to interact (starts interactive console) Something like code.InteractiveConsole"""
        while True:
            if six.PY2:
                code = raw_input('>>> ')
            else:
                code = input('>>>')
            try:
                print(self.eval(code))
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                if DEBUG:
                    sys.stderr.write(traceback.format_exc())
                else:
                    sys.stderr.write('EXCEPTION: ' + str(e) + '\n')
                time.sleep(0.01)
