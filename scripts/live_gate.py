"""Test-run ownership and per-input permits; no product or proof authority.

The runner owns one real provider and supplied access proof. Runtime.close() may
stop this facade, but only close_run() stops that shared owner. A new permit is
granted only after the runner validates the prior phase's canonical evidence.
"""
import hashlib
import threading
import time

from pal.native import ProviderUnavailable
from pal.sanitize import sanitize


class GatedProvider:
    def __init__(self, provider, sink, deadline, clock=time.monotonic, max_calls=20):
        if type(max_calls) is not int or not 1 <= max_calls <= 20:
            raise ValueError('live gate total cap must be 1..20')
        self.provider = provider
        self.identity = provider.identity
        self.sink = sink
        self.deadline = deadline
        self.clock = clock
        self.max_calls = max_calls
        self.attempts = 0
        self._lock = threading.Lock()
        self._permit = None
        self._active = False
        self._closed = False

    def status(self):
        status = dict(self.provider.status())
        with self._lock:
            status['run_gate_closed'] = self._closed
            status['run_attempts'] = self.attempts
        return status

    def stop(self):
        # A Runtime is a borrower. Teardown must not silently replace the owner.
        pass

    def close_run(self, reason):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._permit = None
        try:
            self.provider.stop()
        finally:
            self.sink({'event':'run.closed', 'reason':reason,
                       'monotonic':self.clock(), 'attempts':self.attempts})

    def grant(self, case, phase, kind):
        if kind not in ('DRAFT','CONVERSATION') or not case or not phase:
            raise ValueError('invalid live phase permit')
        with self._lock:
            denied = (self._closed or self.clock() >= self.deadline or
                      self.attempts >= self.max_calls or self._active or
                      self._permit is not None)
            if not denied:
                self._permit = (case,phase,kind)
        if denied:
            self.close_run('permit_denied')
            raise ProviderUnavailable('live phase permit denied')

    def complete(self, prompt):
        with self._lock:
            permit = self._permit
            denied = (self._closed or self.clock() >= self.deadline or
                      self.attempts >= self.max_calls or self._active or
                      permit is None or not prompt.startswith(permit[2]+'\n'))
            if not denied:
                self._permit = None
                self._active = True
                self.attempts += 1
                sequence = self.attempts
        if denied:
            self.close_run('unplanned_or_expired_call')
            raise ProviderUnavailable('live generation gate closed')
        started = self.clock()
        event = {'case':permit[0], 'phase':permit[1], 'kind':permit[2],
                 'sequence':sequence, 'monotonic':started}
        try:
            safe_prompt = sanitize(prompt)
            raw = safe_prompt.encode('utf-8', errors='strict')
            self.sink(dict(event, event='call.started', prompt=safe_prompt,
                           prompt_sha256=hashlib.sha256(raw).hexdigest()))
            response = self.provider.complete(safe_prompt)
            safe_response = sanitize(response)
            response_hash = hashlib.sha256(safe_response.encode('utf-8', errors='strict')).hexdigest()
            if self.clock() >= self.deadline:
                self.close_run('deadline_at_return')
            with self._lock:
                closed = self._closed
            self.sink(dict(event, event='call.returned', response_sha256=response_hash,
                           duration=self.clock()-started, discarded=closed))
            if closed:
                raise ProviderUnavailable('live run stopped before return')
            return safe_response
        except BaseException as error:
            try:
                self.sink(dict(event, event='call.failed', error_type=type(error).__name__,
                               duration=self.clock()-started))
            finally:
                self.close_run('call_failed')
            raise
        finally:
            with self._lock:
                self._active = False
