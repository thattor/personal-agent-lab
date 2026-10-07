"""One controlled delivery probe; model generation itself is never held or replaced."""
import argparse
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from pal.native import AccessProof, NativeClaude
from pal.runtime import Runtime
from pal.server import build_provider, make_server
from scripts.live_evidence import EvidenceJournal, RunWatchdog
from scripts.live_operator import clean_candidate
from scripts.live_runner import RunRejected
from scripts.primary_qualification import QualificationPin, validate_freeze

PRODUCT_FREEZE = 'evidence/reviews/judgment-boundary/expert-commitment-candidate-freeze.json'
REQUEST = 'Mapleの招待文の下書きを作成してください。外部には送らないでください。'
CANCEL = 'Mapleの下書きを止めて'
HARNESS = {'scripts/'+name+'.py' for name in (
    'live_cancel_probe', 'live_evidence', 'live_operator', 'live_runner',
    'live_gate', 'primary_qualification')}
_LIVE = object()


class DeliveryHold:
    def __init__(self):
        self.held = threading.Event()
        self.released = threading.Event()
        self.runtime = None
        self._taken = False

    def __call__(self, point):
        if point != 'worker.after_executor_before_apply' or self._taken:
            return
        self._taken = True
        self.held.set()
        # Returning permits apply. A local timeout must never grant that permission.
        while not self.released.wait(.05):
            if self.runtime is not None and self.runtime.health()['stopping']:
                return


class CancelProbe:
    def __init__(self, directory, provider, *, scope='scripted', deadline=None,
                 pin=None, metadata=None, executor=None, _live_token=None):
        if scope not in ('scripted', 'live_synthetic'):
            raise ValueError('unsupported probe scope')
        if scope == 'live_synthetic' and (_live_token is not _LIVE or
                type(provider) is not NativeClaude or executor is not None):
            raise ValueError('live probe requires checked official construction')
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.provider, self.scope, self.pin = provider, scope, pin
        self.deadline = deadline if deadline is not None else time.monotonic()+600
        self.hold = DeliveryHold()
        self.binding = self.runtime = self.server = self.server_thread = None
        self.journal = self.watchdog = None
        self.closed = threading.Event()
        self.close_done = threading.Event()
        self._close_lock = threading.Lock()
        self._close_errors = []
        self.close_reason = ''
        self.released = False
        try:
            self.journal = EvidenceJournal(self.directory/'journal.jsonl', scope)
            self.journal.append({'event':'run.opened', 'metadata':metadata or {},
                                 'human_evaluation':False, 'provider':provider.identity,
                                 'claim':'Controlled delivery after actual Executor return; no upstream-cancel claim'})
            self.runtime = Runtime(self.directory/'state.sqlite', provider=provider,
                                   executor=executor, fault=self.hold)
            self.hold.runtime = self.runtime
            self.server = make_server(self.runtime, 0)
            self.url = 'http://127.0.0.1:'+str(self.server.server_port)
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, kwargs={'poll_interval':.05}, daemon=True)
            self.server_thread.start()
            self.watchdog = RunWatchdog(self, self.deadline)
            self.watchdog.start()
            self.journal.append({'event':'host.ready', 'url':self.url,
                                 'health':self.runtime.health()})
        except BaseException:
            self.close()
            raise

    def _check(self):
        if self.closed.is_set() or time.monotonic() >= self.deadline:
            raise RunRejected('probe closed or expired')
        if self.pin is not None:
            self.pin.check()

    def snapshot(self):
        return self.runtime.store.inspect()

    @staticmethod
    def _empty_effects(data):
        return all(not data[key] for key in ('artifacts','receipts','outcomes','questions','approvals'))

    def bind(self):
        self._check()
        if self.binding is not None:
            return self.binding
        data = self.snapshot()
        if (not self.hold.held.is_set() or len(data['goals']) != 1 or
                len(data['attempts']) != 1 or not self._empty_effects(data) or data['rejections']):
            raise RunRejected('hold lacks a unique unfinished binding')
        goal, attempt = data['goals'][0], data['attempts'][0]
        if (goal['state'] != 'running' or attempt['status'] != 'running' or
                attempt['goal_id'] != goal['id'] or any(
                    attempt[k] != goal[k] for k in ('revision','epoch','acceptance_id'))):
            raise RunRejected('hold binding is not current running work')
        self.binding = data
        self.journal.append({'event':'result.held', 'snapshot':data})
        return data

    def _cancelled(self, data):
        before = self.binding
        if before is None:
            raise RunRejected('result has not been bound')
        goal = dict(before['goals'][0], state='cancelled',
                    epoch=before['goals'][0]['epoch']+1, reason='user_cancelled', question_id=None)
        attempt = dict(before['attempts'][0], status='fenced')
        if data['goals'] != [goal] or data['attempts'] != [attempt]:
            raise RunRejected('cancel changed wrong state, identity or epoch')
        for key in ('revisions','acceptances','notes'):
            if data[key] != before[key]:
                raise RunRejected('cancel changed fixed criteria or sources')
        current = {row['id']:row for row in data['records']}
        if any(current.get(row['id']) != row for row in before['records']):
            raise RunRejected('bound source changed')
        if not self._empty_effects(data):
            raise RunRejected('unexpected result or question accepted')

    def release(self):
        with self._close_lock:
            self._check()
            if self.released:
                raise RunRejected('result already released')
            if self.binding is None:
                self.bind()
            data = self.snapshot()
            if data['goals'] == self.binding['goals'] and data['attempts'] == self.binding['attempts']:
                self.journal.append({'event':'release.refused', 'reason':'cancel not yet committed'})
                return False
            self._cancelled(data)
            self._live_inputs(data)
            self._check()
            self.journal.append({'event':'release.granted', 'snapshot':data})
            self.released = True
            self.hold.released.set()
            return True

    def _live_inputs(self, data):
        if self.scope == 'live_synthetic':
            users = [r['content'] for r in data['records'] if r['role']=='user']
            if users != [REQUEST, CANCEL] or len(data['primary_turns']) != 2:
                raise RunRejected('live input sequence differs from frozen two turns')

    def result(self, timeout=10):
        if not self.released:
            raise RunRejected('result delivery not released')
        until = min(self.deadline, time.monotonic()+timeout)
        attempt_id = self.binding['attempts'][0]['id']
        while time.monotonic() < until and not self.closed.is_set():
            self._check()
            data = self.snapshot()
            self._cancelled(data)
            matching = [r for r in data['rejections'] if r['attempt_id']==attempt_id]
            if matching:
                break
            time.sleep(.01)
        # A deadline close cannot race a PASS publication after the closed record.
        with self._close_lock:
            self._check()
            data = self.snapshot()
            self._cancelled(data)
            self._live_inputs(data)
            matching = [r for r in data['rejections'] if r['attempt_id']==attempt_id]
            passed = len(matching)==1 and matching[0]['reason']=='stale artifact'
            result = {'status':'PASS' if passed else 'NOT_VERIFIED',
                      'rejection':matching, 'snapshot':data,
                      'provider_status':self.provider.status() if hasattr(self.provider,'status') else {},
                      'scope':self.scope, 'human_evaluation':False}
            if self.scope == 'live_synthetic' and result['provider_status'].get('calls_remaining') != 0:
                result['status'] = 'NOT_VERIFIED'
            self._check()
            self.journal.append({'event':'result.observed', 'result':result})
            return result

    def close_run(self, reason):
        with self._close_lock:
            if self.closed.is_set():
                return
            self.closed.set()
            self.close_reason = reason
            errors = self._close_errors
            def stop_runtime():
                try:
                    self.runtime.close()
                except BaseException as error:
                    errors.append(type(error).__name__)
            try:
                if self.runtime is not None:
                    closer = threading.Thread(target=stop_runtime, daemon=True)
                    closer.start()
                    until = time.monotonic()+2
                    while not self.runtime.health()['stopping'] and time.monotonic()<until:
                        time.sleep(.005)
                    if self.runtime.health()['stopping']:
                        self.hold.released.set()
                    else:
                        errors.append('RuntimeStoppingNotObserved')
                    closer.join(10)
                    if closer.is_alive():
                        errors.append('RuntimeCloseTimeout')
                else:
                    self.provider.stop()
            except BaseException as error:
                errors.append(type(error).__name__)
            finally:
                try:
                    if self.server is not None:
                        if self.server_thread is not None and self.server_thread.is_alive():
                            self.server.shutdown()
                            self.server_thread.join(2)
                        self.server.server_close()
                except BaseException as error:
                    errors.append(type(error).__name__)
                try:
                    if self.journal is not None:
                        self.journal.append({'event':'run.closed', 'reason':reason,
                                             'cleanup_errors':list(errors),
                                             'health':self.runtime.health() if self.runtime else None})
                except BaseException as error:
                    errors.append(type(error).__name__)
                finally:
                    self.close_done.set()

    def close(self):
        try:
            self.close_run('operator_close')
        finally:
            try:
                if self.watchdog is not None:
                    self.watchdog.close()
            finally:
                if self.journal is not None:
                    self.journal.close()
        if self._close_errors:
            raise RuntimeError('probe cleanup failed: '+','.join(self._close_errors))


def build_live(root, directory, proof_path, candidate, contract_path):
    root, directory, contract_path = Path(root).resolve(), Path(directory), Path(contract_path)
    try:
        clean_candidate(root, candidate)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RunRejected('candidate checkout is unverified') from error
    if directory.is_symlink() or directory.exists() or directory.parent.resolve() != root/'runtime':
        raise RunRejected('run must be a fresh direct runtime child')
    contract_path.resolve().relative_to(root)
    contract = json.loads(contract_path.read_text())
    if (contract.get('id') != 'C047-CONTROLLED-CANCEL-v1' or contract.get('max_calls') != 3 or
            contract.get('wall_seconds') != 600 or contract.get('inputs') != [REQUEST,CANCEL] or
            set(contract.get('harness_files',{})) != HARNESS):
        raise RunRejected('unexpected cancellation contract')
    for rel, digest in contract['harness_files'].items():
        if hashlib.sha256((root/rel).read_bytes()).hexdigest() != digest:
            raise RunRejected('probe script differs from frozen source')
    product = validate_freeze(root, PRODUCT_FREEZE)
    if contract.get('product_identity') != product['candidate']:
        raise RunRejected('probe product identity mismatch')
    pin = QualificationPin(root, contract_path, PRODUCT_FREEZE)
    proof = AccessProof.load(proof_path)
    deadline = min(time.monotonic()+600,
                   time.monotonic()+max(0,900-(time.time()-proof.verified_at)))
    pin.check()
    provider = build_provider(argparse.Namespace(provider='official_claude_pro',
        access_proof=str(proof_path), native_call_limit=3, mock_task_delay=0),
        marker_dir=root/'runtime/native-proof-use')
    try:
        pin.check()
        return CancelProbe(directory, provider, scope='live_synthetic', deadline=deadline,
                           pin=pin, _live_token=_LIVE, metadata={'candidate':candidate,
                           'contract':str(contract_path.relative_to(root)), 'hashes':pin.hashes,
                           'max_calls':3, 'product_identity':product['candidate']})
    except BaseException:
        provider.stop()
        raise


def serve_operator(probe, input_fd=None):
    input_fd = sys.stdin.fileno() if input_fd is None else input_fd
    interrupted = threading.Event()
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: interrupted.set())
    def emit(value):
        print(json.dumps(value, ensure_ascii=False), flush=True)
    pending = b''
    try:
        emit({'event':'operator.ready', 'url':probe.url})
        while not probe.closed.is_set():
            if interrupted.is_set():
                probe.close_run('signal')
                break
            probe._check()
            if probe.hold.held.is_set() and probe.binding is None:
                bound = probe.bind()
                emit({'event':'ready_to_cancel', 'goal_id':bound['goals'][0]['id'],
                      'attempt_id':bound['attempts'][0]['id']})
            elif probe.binding is None:
                state = probe.snapshot()
                if (any(g['state'] not in ('queued','running') for g in state['goals']) or
                        (state['primary_turns'] and not state['goals'] and
                         all(t['status']!='pending' for t in state['primary_turns']))):
                    emit({'status':'NOT_VERIFIED','reason':'no held running result'})
                    probe.close_run('no_hold')
                    break
            readable, _, _ = select.select([input_fd], [], [], .05)
            if not readable:
                continue
            chunk = os.read(input_fd, 1024)
            if not chunk:
                probe.close_run('stdin_eof')
                break
            pending += chunk
            if len(pending)>256:
                raise RunRejected('operator command bound')
            while b'\n' in pending and not probe.closed.is_set():
                command, pending = pending.split(b'\n',1)
                command = command.strip()
                if command == b'status':
                    emit({'event':'status', 'snapshot':probe.snapshot()})
                elif command == b'release':
                    if probe.release():
                        emit(probe.result())
                        probe.close_run('result_observed')
                    else:
                        emit({'event':'release.refused'})
                elif command == b'finish':
                    probe.close_run('operator_finish')
                else:
                    raise RunRejected('unknown operator command')
    except BaseException as error:
        probe.journal.append({'event':'operator.failed', 'error':type(error).__name__})
        raise
    finally:
        try:
            probe.close()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','proof','candidate','contract'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    probe = build_live(root, Path(args.directory), args.proof, args.candidate, Path(args.contract))
    serve_operator(probe)


if __name__ == '__main__':
    main()
