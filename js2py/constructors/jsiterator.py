from ..base import *


def _iterable_kind(iterable):
    obj = iterable.to_object()
    next_fn = obj.get('next')
    if next_fn.is_callable():
        return 'iterator', obj
    length = obj.get('length')
    if length.TYPE == 'Number':
        return 'array', obj
    raise MakeError('TypeError', 'Iterator.concat requires iterables')


@Js
def iterator_concat():
    specs = []
    for i in range(len(arguments)):
        specs.append(_iterable_kind(arguments[i]))
    state = {'spec_idx': 0, 'index': 0}

    @Js
    def next_method():
        while state['spec_idx'] < len(specs):
            kind, data = specs[state['spec_idx']]
            if kind == 'array':
                idx = state['index']
                length = data.get('length').to_uint32()
                if idx < length:
                    if data.has_property(str(idx)):
                        val = data.get(str(idx))
                    else:
                        val = undefined
                    state['index'] += 1
                    result = PyJsObject(prototype=ObjectPrototype)
                    result.put('value', val)
                    result.put('done', false)
                    return result
                state['spec_idx'] += 1
                state['index'] = 0
                continue
            result = data.callprop('next')
            if result.get('done').to_boolean().value:
                state['spec_idx'] += 1
                continue
            return result
        result = PyJsObject(prototype=ObjectPrototype)
        result.put('value', undefined)
        result.put('done', true)
        return result

    iterator = PyJsObject(prototype=ObjectPrototype)
    iterator.put('next', next_method)
    return iterator


Iterator = PyJsObject(prototype=ObjectPrototype)
Iterator.put('concat', Js(iterator_concat))
