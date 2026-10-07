"""Await a committed Primary outcome; HTTP admission is deliberately asynchronous."""
def settled(runtime, key, text, **kwargs):
    admission = runtime.submit(key, text, **kwargs)
    admission['response'].result(timeout=3)
    fate = runtime.store.operation(key)
    assert fate['status'] == 'accepted', fate
    return dict(fate['result'], response=admission['response'])
