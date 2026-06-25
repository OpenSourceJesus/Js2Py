from ..base import *

PROMISE_STATES = {}


def _state(promise):
    return PROMISE_STATES[id(promise)]


def _unwrap_promise(value):
    if isinstance(value, PyJsObject) and getattr(value, 'Class', None) == 'Promise':
        return value
    return None


def _enqueue_reaction(reaction):
    from ..event_loop import queue_microtask
    queue_microtask(lambda: _run_reaction(reaction))


PromisePrototype = PyJsObject(prototype=ObjectPrototype)


def _create_promise(executor):
    promise = PyJsObject(prototype=PromisePrototype)
    promise.Class = 'Promise'
    PROMISE_STATES[id(promise)] = {
        'state': 'pending',
        'value': undefined,
        'reason': undefined,
        'reactions': [],
    }
    if executor is not None and executor.is_callable():
        resolving = {'done': False}

        @Js
        def resolve(value):
            if resolving['done']:
                return undefined
            resolving['done'] = True
            _resolve_promise(promise, value)
            return undefined

        @Js
        def reject(reason):
            if resolving['done']:
                return undefined
            resolving['done'] = True
            _reject_promise(promise, reason)
            return undefined

        try:
            executor.call(undefined, (resolve, reject))
        except PyJsException as exc:
            reject.call(undefined, (PyExceptionToJs(exc),))
        except Exception as exc:
            reject.call(undefined, (PyExceptionToJs(exc),))
    return promise


def _resolve_promise(promise, value):
    state = _state(promise)
    if state['state'] != 'pending':
        return
    nested = _unwrap_promise(value)
    if nested is not None:
        if nested is promise:
            _reject_promise(promise, MakeError(
                'TypeError', 'Cannot resolve promise with itself'))
            return

        @Js
        def on_fulfilled(val):
            _resolve_promise(promise, val)
            return undefined

        @Js
        def on_rejected(reason):
            _reject_promise(promise, reason)
            return undefined

        nested.callprop('then', on_fulfilled, on_rejected)
        return
    state['state'] = 'fulfilled'
    state['value'] = value
    reactions = state['reactions']
    state['reactions'] = []
    for reaction in reactions:
        _enqueue_reaction(reaction)


def _reject_promise(promise, reason):
    state = _state(promise)
    if state['state'] != 'pending':
        return
    state['state'] = 'rejected'
    state['reason'] = reason
    reactions = state['reactions']
    state['reactions'] = []
    for reaction in reactions:
        _enqueue_reaction(reaction)


def _run_reaction(reaction):
    parent, onFulfilled, onRejected, child = reaction
    parent_state = _state(parent)
    try:
        if parent_state['state'] == 'fulfilled':
            if onFulfilled.is_callable():
                val = onFulfilled.call(undefined, (parent_state['value'],))
            else:
                val = parent_state['value']
        else:
            if onRejected.is_callable():
                val = onRejected.call(undefined, (parent_state['reason'],))
            else:
                _reject_promise(child, parent_state['reason'])
                return
        nested = _unwrap_promise(val)
        if nested is not None:

            @Js
            def on_fulfilled(v):
                _resolve_promise(child, v)
                return undefined

            @Js
            def on_rejected(r):
                _reject_promise(child, r)
                return undefined

            nested.callprop('then', on_fulfilled, on_rejected)
        else:
            _resolve_promise(child, val)
    except PyJsException as exc:
        _reject_promise(child, PyExceptionToJs(exc))
    except Exception as exc:
        _reject_promise(child, PyExceptionToJs(exc))


def _chain_promise(promise, onFulfilled, onRejected):
    result = _create_promise(None)
    parent_state = _state(promise)
    reaction = (promise, onFulfilled, onRejected, result)
    if parent_state['state'] == 'pending':
        parent_state['reactions'].append(reaction)
    else:
        _enqueue_reaction(reaction)
    return result


class PromiseProtoMethods:
    def then(onFulfilled, onRejected):
        if len(arguments) < 2 or onRejected.is_undefined():
            onRejected = undefined
        return _chain_promise(this, onFulfilled, onRejected)

    def catch(onRejected):
        return this.callprop('then', undefined, onRejected)

    def finally_(onFinally):
        if not onFinally.is_callable():
            onFinally = undefined

        @Js
        def on_fulfilled(value):
            if onFinally.is_callable():
                cleanup = onFinally.call(undefined, ())
                nested = _unwrap_promise(cleanup)
                if nested is not None:

                    @Js
                    def cont():
                        return value

                    return nested.callprop('then', cont)
            return value

        @Js
        def on_rejected(reason):
            if onFinally.is_callable():
                cleanup = onFinally.call(undefined, ())
                nested = _unwrap_promise(cleanup)
                if nested is not None:

                    @Js
                    def cont():
                        raise JsToPyException(reason)

                    return nested.callprop('then', cont)
            raise JsToPyException(reason)

        return this.callprop('then', on_fulfilled, on_rejected)


@Js
def promise_constructor(executor):
    if len(arguments) and not executor.is_callable():
        raise MakeError('TypeError', 'Promise resolver is not a function')
    return _create_promise(executor if len(arguments) else None)


Promise = promise_constructor
Promise.create = promise_constructor


@Js
def promise_resolve(value):
    nested = _unwrap_promise(value)
    if nested is not None:
        return nested
    promise = _create_promise(None)
    _resolve_promise(promise, value)
    return promise


@Js
def promise_reject(reason):
    promise = _create_promise(None)
    _reject_promise(promise, reason)
    return promise


@Js
def promise_all_settled(iterable):
    arr = iterable.to_object()
    length = arr.get('length').to_uint32()
    result_promise = _create_promise(None)
    if length == 0:
        _resolve_promise(result_promise, [])
        return result_promise
    results = [undefined] * length
    remaining = {'count': length}

    def settle(index, status, payload):
        entry = PyJsObject(prototype=ObjectPrototype)
        entry.put('status', Js(status))
        if status == 'fulfilled':
            entry.put('value', payload)
        else:
            entry.put('reason', payload)
        results[index] = entry
        remaining['count'] -= 1
        if remaining['count'] == 0:
            out = Js([])
            for i, item in enumerate(results):
                out.put(str(i), item)
            _resolve_promise(result_promise, out)

    for i in range(length):
        p = promise_resolve(arr.get(str(i)))

        def make_handlers(idx):
            @Js
            def on_fulfilled(value):
                settle(idx, 'fulfilled', value)
                return undefined

            @Js
            def on_rejected(reason):
                settle(idx, 'rejected', reason)
                return undefined

            return on_fulfilled, on_rejected

        on_fulfilled, on_rejected = make_handlers(i)
        p.callprop('then', on_fulfilled, on_rejected)
    return result_promise


@Js
def promise_any(iterable):
    arr = iterable.to_object()
    length = arr.get('length').to_uint32()
    result_promise = _create_promise(None)
    if length == 0:
        _reject_promise(result_promise, MakeError(
            'Error', 'All promises were rejected'))
        return result_promise
    remaining = {'count': length}

    def on_any_reject():
        remaining['count'] -= 1
        if remaining['count'] == 0:
            state = _state(result_promise)
            if state['state'] == 'pending':
                _reject_promise(result_promise, MakeError(
                    'Error', 'All promises were rejected'))

    for i in range(length):
        p = promise_resolve(arr.get(str(i)))

        def make_handlers(idx):
            @Js
            def on_fulfilled(value):
                state = _state(result_promise)
                if state['state'] == 'pending':
                    _resolve_promise(result_promise, value)
                return undefined

            @Js
            def on_rejected(reason):
                on_any_reject()
                return undefined

            return on_fulfilled, on_rejected

        on_fulfilled, on_rejected = make_handlers(i)
        p.callprop('then', on_fulfilled, on_rejected)
    return result_promise


Promise.define_own_property('resolve', {
    'value': promise_resolve,
    'writable': True,
    'enumerable': False,
    'configurable': True
})
Promise.define_own_property('reject', {
    'value': promise_reject,
    'writable': True,
    'enumerable': False,
    'configurable': True
})
Promise.define_own_property('allSettled', {
    'value': promise_all_settled,
    'writable': True,
    'enumerable': False,
    'configurable': True
})
Promise.define_own_property('any', {
    'value': promise_any,
    'writable': True,
    'enumerable': False,
    'configurable': True
})
Promise.define_own_property(
    'prototype', {
        'value': PromisePrototype,
        'enumerable': False,
        'writable': False,
        'configurable': False
    })

PromisePrototype.define_own_property('constructor', {
    'value': Promise,
    'writable': True,
    'enumerable': False,
    'configurable': True
})

fill_prototype(PromisePrototype, PromiseProtoMethods, default_attrs)
PromisePrototype.define_own_property(
    'finally', PromisePrototype.own['finally_'])
