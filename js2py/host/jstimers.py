from ..base import *
from ..event_loop import schedule_timer, clear_timer


@Js
def setTimeout(callback, delay):
    if not callback.is_callable():
        raise MakeError('TypeError',
                        'setTimeout callback must be a function')
    delay_ms = 0 if len(arguments) < 2 else arguments[1].to_number().value
    if delay_ms != delay_ms:  # NaN
        delay_ms = 0
    delay_ms = max(0, delay_ms)

    @Js
    def run():
        callback.call(undefined, ())
        return undefined

    return Js(schedule_timer(run, delay_ms))


@Js
def setInterval(callback, delay):
    if not callback.is_callable():
        raise MakeError('TypeError',
                        'setInterval callback must be a function')
    if len(arguments) < 2:
        raise MakeError('TypeError', 'setInterval requires a delay')
    delay_ms = arguments[1].to_number().value
    if delay_ms != delay_ms or delay_ms < 0:
        delay_ms = 0

    @Js
    def run():
        callback.call(undefined, ())
        return undefined

    return Js(schedule_timer(run, delay_ms, repeat_ms=delay_ms))


@Js
def clearTimeout(handle):
    if len(arguments) and not handle.is_undefined():
        clear_timer(handle.to_number().value)


@Js
def clearInterval(handle):
    if len(arguments) and not handle.is_undefined():
        clear_timer(handle.to_number().value)
