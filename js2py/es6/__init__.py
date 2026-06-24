INITIALISED = False
babel = None
babelPresetEs2015 = None

import re

# Patterns for ES6+ syntax that pyjsparser rejects or that needs Babel downleveling.
_ES6_SYNTAX_RE = re.compile(
    r'(?:'
    r'=>|'                          # arrow functions
    r'\bclass\b|'                  # classes
    r'`|'                           # template literals
    r'\.\.\.|'                      # spread/rest
    r'\bfor\s*\([^)]*\bof\b|'      # for...of
    r'\bimport\b|\bexport\b|'      # modules
    r'\basync\b|\bawait\b|'        # async/await
    r'\bfunction\s*\*'              # generators
    r')',
    re.MULTILINE)


def looks_like_es6(code):
    """Return True if source likely contains ES6+ syntax needing transpilation."""
    return bool(_ES6_SYNTAX_RE.search(code))


def js6_to_js5(code):
    global INITIALISED, babel, babelPresetEs2015
    if not INITIALISED:
        import signal, warnings, time
        warnings.warn(
            '\nImporting babel.py for the first time - this can take some time. \nPlease note that currently Javascript 6 in Js2Py is unstable and slow. Use only for tiny scripts!'
        )

        from .babel import babel as _babel
        babel = _babel.Object.babel
        babelPresetEs2015 = _babel.Object.babelPresetEs2015

        # very weird hack. Somehow this helps babel to initialise properly!
        try:
            babel.transform('warmup', {'presets': {}})
            signal.alarm(2)

            def kill_it(a, b):
                raise KeyboardInterrupt('Better work next time!')

            signal.signal(signal.SIGALRM, kill_it)
            babel.transform('stuckInALoop', {
                'presets': babelPresetEs2015
            }).code
            for n in range(3):
                time.sleep(1)
        except:
            print("Initialised babel!")
        INITIALISED = True
    return babel.transform(code, {'presets': babelPresetEs2015}).code


if __name__ == '__main__':
    print(js6_to_js5('obj={}; obj.x = function() {return () => this}'))
    print()
    print(js6_to_js5('const a = 1;'))
