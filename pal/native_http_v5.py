"""Loopback native-owner connection with explicit synthetic providers only."""
from contextlib import contextmanager
from pathlib import Path
import queue
import sqlite3
import tempfile
import threading
import time
import uuid

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import ErrorCode, Grant, Limits, Result
from pal.http_v5 import _closed, _token, failure
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.native_call_v5 import NativeProfile
from pal.native_expert_runner_v5 import NativeExpertRunner
from pal.primary_host_v5 import NativePrimaryHost
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


def _limits(value):
    return (type(value) is Limits and value.max_operations == 0
            and all(type(x) is int and 0 <= x <= 20
                    for x in (value.max_steps, value.max_model_calls)))


class LocalNativeApp:
    """Fresh managed fixture DB, retained on close; never a qualified launcher."""
    def __init__(self, *, provider, request_scope, host_limits, session_id=None):
        if (callable(provider) or type(getattr(provider, 'profile', None)) is not NativeProfile
                or getattr(provider, 'fixture_only', None) is not True
                or not callable(getattr(provider, 'preflight', None))
                or not callable(getattr(provider, 'invoke', None))
                or type(request_scope) is not Grant or request_scope.capabilities
                or not _limits(request_scope.limits) or not _limits(host_limits)):
            raise ValueError('invalid native fixture configuration')
        if session_id is not None:
            try:
                _token(session_id)
            except (ValueError, UnicodeError):
                raise ValueError('invalid native fixture session') from None
        self.session_id = session_id if session_id is not None else 'ui-fixture-' + uuid.uuid4().hex
        self._provider = provider
        self._profile = provider.profile
        self._grant, self._limits = request_scope, host_limits
        self._directory = Path(tempfile.mkdtemp(prefix='pal-v5-native-fixture-'))
        self._directory.chmod(0o700)
        self._path = self._directory / 'work.sqlite'
        self._guard = MockHostSession.open(self._path)
        self._lock = threading.RLock()
        self._queue = queue.Queue(maxsize=16)
        self._scheduled = set()
        self._slots = self._admissions = self._active_handlers = 0
        self._held = self._closing = self._closed = self._running = False
        self._stop = threading.Event()
        self._idle = threading.Event(); self._idle.set()
        try:
            with self.owners() as (_, tasks, memory, artifacts, verifier, host):
                if host is None:
                    raise RuntimeError('native fixture startup unavailable')
                recovered = self._result(host.recover_turns())
                recovery = recovered.value.to_json() if recovered.ok else None
                keys = {'interrupted_turn_ids', 'committed_turn_ids',
                        'held_turn_ids', 'failed_turn_ids'}
                if (type(recovery) is not dict or set(recovery) != keys
                        or any(type(recovery[key]) is not list for key in keys)
                        or recovery['held_turn_ids']):
                    raise RuntimeError('native fixture startup unavailable')
                ready = self._result(tasks.finish_startup())
                if not ready.ok or ready.value.to_json().get('status') != 'ready':
                    raise RuntimeError('native fixture startup unavailable')
        except BaseException:
            self._held = True
            self._guard.close()
            raise
        self._path.chmod(0o600)
        self._worker = threading.Thread(target=self._work, name='pal-v5-native-fixture', daemon=True)
        self._worker.start()

    def _unchanged(self):
        return (getattr(self._provider, 'fixture_only', None) is True
                and type(getattr(self._provider, 'profile', None)) is NativeProfile
                and self._provider.profile == self._profile
                and not callable(self._provider)
                and callable(getattr(self._provider, 'preflight', None))
                and callable(getattr(self._provider, 'invoke', None)))

    def _hold(self):
        with self._lock:
            self._held = True

    @property
    def database_path(self):
        return self._path

    @contextmanager
    def owners(self):
        with self._lock:
            if self._closed:
                raise RuntimeError('application closed')
            self._active_handlers += 1
        conn = None
        try:
            conn = sqlite3.connect(self._path, isolation_level=None, timeout=1)
            memory = artifacts = verifier = None
            tasks = TaskStore(conn, startup_guard=self._guard, host_grant=self._grant,
                host_limits=self._limits, expert_id='expert',
                source_gate=lambda c, r: memory.source_gate(c, r),
                artifact_inspect=lambda c, r: artifacts.inspect(c, r),
                artifact_lookup=lambda c, r: artifacts.lookup_saved(c, r),
                verification_inspect=lambda c, r: verifier.inspect(c, r))
            memory = MemoryStore(conn, sanitize_text=sanitize, append_event=tasks.append_event,
                                 invalidate_by_refs=tasks.invalidate_by_refs)
            artifacts = ArtifactStore(conn, authorize_save=tasks.authorize_artifact_save,
                                      source_gate=memory.source_gate)
            verifier = VerificationStore(conn, context=tasks.verification_context,
                artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
            if self._guard.phase == 'owned':
                registered = tasks.register_host()
                if type(registered) is not Result or not registered.ok:
                    raise RuntimeError('native fixture startup unavailable')
            host = None
            if self._unchanged():
                host = NativePrimaryHost(conn, guard=self._guard, memory=memory,
                    tasks=tasks, request_scope=self._grant, provider=self._provider)
            else:
                # Core controls/read do not depend on constructing a changed host.
                self._hold()
            yield conn, tasks, memory, artifacts, verifier, host
        finally:
            if conn is not None:
                conn.close()
            with self._lock:
                self._active_handlers -= 1

    def _reserve_slot(self):
        with self._lock:
            if not self._unchanged():
                self._held = True
            if self._held or self._closing or self._slots >= 16:
                return False
            self._slots += 1
            self._admissions += 1
            return True

    def _release_slot(self):
        with self._lock:
            self._slots -= 1
            self._admissions -= 1

    def _enqueue_reserved(self, kind, identity):
        with self._lock:
            self._admissions -= 1
            marker = (kind, identity)
            if self._held or self._closing or marker in self._scheduled:
                self._slots -= 1
                return
            self._scheduled.add(marker)
            self._queue.put_nowait(marker)
            self._idle.clear()

    def submit(self, data):
        _closed(data, ('client_key', 'text')); _token(data['client_key'])
        if type(data['text']) is not str or len(data['text'].encode('utf-8')) > 32768:
            raise ValueError()
        if not self._reserve_slot():
            return failure(ErrorCode.UNAVAILABLE), 503
        retained = False
        try:
            with self.owners() as (_, tasks, memory, artifacts, verifier, host):
                if host is None:
                    return failure(ErrorCode.UNAVAILABLE), 503
                result = host.submit({**data, 'session_id': self.session_id})
                if type(result) is not Result:
                    self._hold()
                    return failure(ErrorCode.UNAVAILABLE), 503
                if result.ok and result.value.to_json().get('status') == 'pending':
                    retained = True
                    self._enqueue_reserved('turn', result.value.to_json()['turn_id'])
                elif not result.ok and result.error.code is ErrorCode.UNAVAILABLE:
                    self._hold()
                return result.to_json(), 200
        finally:
            if not retained:
                self._release_slot()

    @staticmethod
    def _result(result):
        if type(result) is not Result:
            raise ValueError('owner response unavailable')
        return Result.from_json(result.to_json())

    def _slice(self, kind, identity):
        with self._lock:
            if not self._unchanged():
                self._held = True
            if self._held or self._closing:
                return
        with self.owners() as (_, tasks, memory, artifacts, verifier, host):
            if host is None:
                self._hold(); return
            if kind == 'turn':
                result = self._result(host.run_turn({'turn_id': identity}))
                if not result.ok:
                    if result.error.code is ErrorCode.UNAVAILABLE:
                        self._hold()
                    return
                status = result.value.to_json().get('status')
                if status == 'held' or status not in {'committed', 'failed', 'interrupted', 'pending'}:
                    self._hold(); return
                if status != 'committed':
                    return
            with self._lock:
                if not self._unchanged():
                    self._held = True
                if self._held or self._closing:
                    return
            result = self._result(NativeExpertRunner(tasks, memory, provider=self._provider,
                                   artifacts=artifacts, verifier=verifier).execute_next())
            if not result.ok:
                if result.error.code is ErrorCode.UNAVAILABLE:
                    self._hold()
            elif result.value.to_json().get('status') not in {'released', 'completed', 'waiting', 'empty'}:
                self._hold()

    def _discard_queue(self):
        with self._lock:
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
                self._queue.task_done()
                self._slots -= 1
            if not self._running:
                self._idle.set()

    def _work(self):
        while not self._stop.is_set():
            try:
                kind, identity = self._queue.get(timeout=.05)
            except queue.Empty:
                continue
            with self._lock:
                self._running = True
            try:
                self._slice(kind, identity)
            except BaseException:
                # The owner, not an HTTP worker exception, determines call ending.
                self._hold()
            finally:
                self._queue.task_done()
                with self._lock:
                    self._running = False
                    self._slots -= 1
                    if self._held or self._closing:
                        self._discard_queue()
                    if self._queue.empty():
                        self._idle.set()
        self._discard_queue()

    def status(self):
        with self._lock:
            if not self._unchanged():
                self._held = True
            state = ('closed' if self._closed else 'held' if self._held
                     else 'closing' if self._closing else 'running'
                     if self._running or not self._queue.empty() else 'idle')
        return {'mode': 'native_fixture', 'native_available': False, 'qualification': 'NOT_RUN',
                'profile_id': self._profile.id, 'model_id': self._profile.model_id,
                'session_id': self.session_id, 'worker_status': state}

    def wait_idle(self, timeout=5.0):
        return self._idle.wait(timeout)

    def close(self, timeout=5.0):
        with self._lock:
            if self._closed:
                return True
            self._closing = True
            self._stop.set()
        deadline = time.monotonic() + max(0, timeout)
        self._worker.join(max(0, deadline - time.monotonic()))
        while time.monotonic() < deadline:
            with self._lock:
                busy = self._active_handlers + self._admissions
            if not busy:
                break
            time.sleep(.01)
        with self._lock:
            if self._worker.is_alive() or self._active_handlers or self._admissions:
                return False
            self._guard.close()
            self._closed = True
            self._idle.set()
        # Native fixture evidence/UNKNOWN must survive application closure.
        return True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
