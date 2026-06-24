"""JavaScript-style event loop: microtasks (Promises) and macrotasks (timers)."""

import heapq
import time

_microtasks = []
_macrotasks = []  # (due_time, seq, callback)
_macrotask_seq = 0
_timers = {}
_next_timer_id = 1
_MAX_DRAIN_ITERATIONS = 100000


def queue_microtask(callback):
    """Schedule a microtask (Promise reaction, etc.)."""
    _microtasks.append(callback)


def _schedule_macrotask(callback, delay_ms=0):
    global _macrotask_seq
    due = time.monotonic() + max(0.0, float(delay_ms)) / 1000.0
    _macrotask_seq += 1
    heapq.heappush(_macrotasks, (due, _macrotask_seq, callback))


def schedule_timer(callback, delay_ms, repeat_ms=None):
    """Schedule setTimeout/setInterval; returns timer handle id."""
    global _next_timer_id
    timer_id = _next_timer_id
    _next_timer_id += 1
    _timers[timer_id] = {
        'cancelled': False,
        'repeat_ms': repeat_ms,
    }

    def fire():
        info = _timers.get(timer_id)
        if info is None or info['cancelled']:
            return
        callback()
        if info['cancelled']:
            return
        repeat = info.get('repeat_ms')
        if repeat is not None:
            _schedule_macrotask(fire, repeat)

    _schedule_macrotask(fire, delay_ms)
    return timer_id


def clear_timer(timer_id):
    info = _timers.pop(int(timer_id), None)
    if info is not None:
        info['cancelled'] = True


def drain_event_loop(timeout=None):
    """Run microtasks and due macrotasks until idle or timeout (seconds)."""
    deadline = time.monotonic() + timeout if timeout is not None else None
    iterations = 0
    while iterations < _MAX_DRAIN_ITERATIONS:
        iterations += 1
        while _microtasks:
            batch = _microtasks[:]
            _microtasks.clear()
            for callback in batch:
                callback()

        if not _macrotasks:
            return

        now = time.monotonic()
        if _macrotasks[0][0] > now:
            if deadline is not None and now >= deadline:
                return
            wait = _macrotasks[0][0] - now
            if deadline is not None:
                wait = min(wait, max(0.0, deadline - now))
            if wait > 0:
                time.sleep(wait)
            continue

        _, _, callback = heapq.heappop(_macrotasks)
        callback()

        if deadline is not None and time.monotonic() >= deadline:
            return

    raise RuntimeError('Event loop drain exceeded maximum iterations')


def reset_event_loop():
    """Clear all queued tasks (mainly for tests)."""
    _microtasks[:] = []
    _macrotasks[:] = []
    _timers.clear()
