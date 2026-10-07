"""Await a committed Primary outcome; HTTP admission is deliberately asynchronous."""
import time


def settled(runtime, key, text, **kwargs):
    admission = runtime.submit(key, text, **kwargs)
    admission['response'].result(timeout=3)
    fate = runtime.store.operation(key)
    assert fate['status'] == 'accepted', fate
    return dict(fate['result'], response=admission['response'])


def work_settled(runtime, goal_id, timeout=3):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        goal = runtime.store.get_goal(goal_id)
        if goal['state'] not in ('queued','running'):
            return goal
        time.sleep(.005)
    raise AssertionError('Goal did not reach a waiting or terminal state')
