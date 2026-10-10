"""Local native-Expert lifetime verifier; all provider endings are fixtures.

The killed PIDs belong only to this verifier. Their exit is never provider
cessation evidence and cannot settle a real native call or shared capacity slot.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, dumps
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.native_call_v5 import NativeProfile, NativeReturned
from pal.native_expert_runner_v5 import NativeExpertRunner
from pal.native_text_v5 import NativeTextBuffer
from pal.read_consumer_v5 import inspect_session
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore

REPORTS = []


def value(result):
    if not result.ok:
        raise AssertionError('owner refused: ' + result.error.code.value)
    return result.value.to_json()


def digest(value):
    return hashlib.sha256(dumps(value).encode('utf-8')).hexdigest()


class Provider:
    def __init__(self):
        self.profile = NativeProfile(model_id='swe-2-high', qualification_sha256='2'*64, evidence_kind='fixture')
        self.calls = []
        self.behavior = None
        self.forbid_entry = False
        self.owners = None

    def preflight(self):
        assert not self.owners.conn.in_transaction

    def invoke(self, request, *, on_enter):
        assert not self.owners.conn.in_transaction
        assert not self.forbid_entry, 'fixture provider must not be re-entered'
        assert request['role'] == 'expert' and request['output_kind'] == 'expert_action'
        self.calls.append(request)
        attempt = {'run_id': 'fixture-run', 'job_id': 'expert', 'attempt_id': 'fixture-'+str(len(self.calls))}
        on_enter(attempt)
        assert not self.owners.conn.in_transaction
        if self.behavior:
            self.behavior(request, attempt)
        text = dumps({'kind': 'compose', 'content': '保存済み合成下書き', 'media_type': 'text/plain',
                      'source_refs': request['source_refs']})
        ending = {'attempt_ref': attempt, 'guarantee_model': 'native_handoff_v1', 'capability': 'devin.text.only',
                  'native_stop_reason': 'end_turn', 'native_mode': 'plan', 'effective_model': 'swe-2-high',
                  'effective_model_verified': True, 'stdout_eof_validated': True,
                  'owned_pid': 123, 'owned_exit_code': -15, 'tool_events': 0, 'pending_permissions': 0,
                  'session_sha256': '3'*64, 'prompt_rpc_sha256': '4'*64}
        ending['evidence_ref'] = 'devin.acp:text-only:end_turn:' + hashlib.sha256(
            json.dumps(ending, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        buffer = NativeTextBuffer(request_sha256=digest(request), profile_sha256=self.profile.profile_sha256,
                                  attempt_ref=attempt, model_id='swe-2-high')
        buffer.begin()
        buffer.observe({'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': text}})
        return NativeReturned(capture=buffer.finish(ending), cessation=ending)


class Owners:
    def __init__(self, path, guard, provider):
        self.conn = sqlite3.connect(path, isolation_level=None, timeout=1)
        self.guard = guard
        self.grant = Grant((), ('repo',), Limits(0, 8, 8))
        self.lookup_requests = []
        self.tasks = TaskStore(self.conn, startup_guard=guard, host_grant=self.grant,
            host_limits=Limits(0, 40, 40), expert_id='expert',
            source_gate=lambda c, r: self.mem.source_gate(c, r),
            artifact_inspect=lambda c, r: self.art.inspect(c, r),
            verification_inspect=lambda c, r: self.ver.inspect(c, r),
            artifact_lookup=self.lookup)
        self.mem = MemoryStore(self.conn, sanitize_text=lambda text: text,
            append_event=self.tasks.append_event, invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art = ArtifactStore(self.conn, authorize_save=self.tasks.authorize_artifact_save,
                                 source_gate=self.mem.source_gate)
        self.ver = VerificationStore(self.conn, context=self.tasks.verification_context,
            artifact_inspect=self.art.inspect, source_gate=self.mem.source_gate)
        if guard.phase == 'owned':
            value(self.tasks.register_host())
        provider.owners = self
        self.provider = provider
        self.runner = NativeExpertRunner(self.tasks, self.mem, provider=provider, artifacts=self.art, verifier=self.ver)

    def lookup(self, connection, request):
        self.lookup_requests.append(json.loads(dumps(request)))
        return self.art.lookup_saved(connection, request)

    def native_hash(self):
        row = self.conn.execute('SELECT wire FROM v5_tsk_native').fetchone()
        assert row is not None
        return hashlib.sha256(row[0].encode('utf-8')).hexdigest()

    def ready(self):
        value(self.tasks.finish_startup())

    def setup(self):
        self.ready()
        origin = value(self.mem.append({'client_key': 'origin', 'session_id': 'session',
                                       'role': 'user', 'text': '合成下書き依頼'}))['record_ref']
        brief = {'purpose': 'fixture draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                 'constraints': [], 'conditions': [{'description': 'saved', 'check': 'artifact_saved'}], 'context_refs': []}
        work = value(self.tasks.create({'key': 'work', 'session_id': 'session', 'origin_record_ref': origin,
                                       'brief': brief}, request_scope=self.grant))['work_ref']
        return work, origin

    def counters(self):
        # Observation only: all writes remain in public owner methods.
        return {'host': [list(r) for r in self.conn.execute('SELECT kind,used FROM v5_tsk_host ORDER BY kind')],
                'work': [list(r) for r in self.conn.execute('SELECT goal,kind,used FROM v5_tsk_usage ORDER BY goal,kind')]}

    def snapshot(self):
        return digest(list(self.conn.iterdump()))

    def call(self):
        row = self.conn.execute('SELECT id FROM v5_tsk_call').fetchone()
        assert row is not None
        return value(self.tasks.get_call({'call_id': row[0]}))

    def current(self, work):
        return value(self.tasks.get_work({'goal_id': work['goal_id']}))

    def close(self):
        self.conn.close()


def barrier(owners, work, mode, **extra):
    assert not owners.conn.in_transaction
    checkpoint = {'mode': mode, 'pid': os.getpid(), 'work_ref': work, 'call': owners.call(),
                  'counters': owners.counters(), 'native_side_sha256': owners.native_hash(), 'provider_invocations': len(owners.provider.calls), **extra}
    print(json.dumps(checkpoint), flush=True)
    sys.stdin.buffer.read(1)
    raise AssertionError('parent must kill the owned fixture at its barrier')


def child(path, mode):
    guard = MockHostSession.open(path)
    owners = None
    try:
        provider = Provider()
        owners = Owners(path, guard, provider)
        work, _ = owners.setup()
        if mode == 'prepared':
            original = owners.tasks.admit_native_call
            def admit(*args, **kwargs):
                result = original(*args, **kwargs)
                value(result)
                barrier(owners, work, mode)
            owners.tasks.admit_native_call = admit
        elif mode == 'entering':
            provider.behavior = lambda request, attempt: barrier(owners, work, mode)
        elif mode == 'returned':
            original = owners.tasks.end_native_call
            def end(*args, **kwargs):
                result = original(*args, **kwargs)
                value(result)
                call = owners.call()
                output = value(owners.tasks.get_native_output({k: call[k] for k in ('call_id', 'lease_id', 'work_ref')}))
                barrier(owners, work, mode, output_sha256=hashlib.sha256(output['content'].encode()).hexdigest())
            owners.tasks.end_native_call = end
        elif mode == 'saved':
            original = owners.art.save
            def save(request):
                receipt = value(original(request))
                body = value(owners.art.read({'ref': receipt['artifact_ref']}, purpose='user_view'))
                barrier(owners, work, mode, save_key=request['key'], receipt=receipt, artifact_sha256=body['hash'])
            owners.art.save = save
        else:
            raise AssertionError('unknown fixture mode')
        owners.runner.execute_next()
        raise AssertionError('child did not reach the owned barrier')
    finally:
        if owners:
            owners.close()
        guard.close()


class LifetimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pal-expert-lifetime-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'work.sqlite'
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.report = {'case': self._testMethodName, 'passed': False, 'fixture_only': True,
                       'real_provider_calls': 0, 'external_effects': 0}
        REPORTS.append(self.report)

    def open(self):
        guard = MockHostSession.open(self.path)
        self.stack.callback(guard.close)
        provider = Provider()
        owners = Owners(self.path, guard, provider)
        self.stack.callback(owners.close)
        return owners, provider

    def crash(self, mode):
        proc = subprocess.Popen([sys.executable, '-E', '-s', '-B', str(Path(__file__).resolve()),
                                 '--child', str(self.path), mode], cwd=ROOT,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout], [], [], 10)[0], 'child barrier timeout')
        line = proc.stdout.readline(65537)
        self.assertTrue(line and len(line) <= 65536, 'missing or oversized child checkpoint')
        checkpoint = json.loads(line)
        self.assertEqual(checkpoint['pid'], proc.pid)
        self.assertEqual(checkpoint['mode'], mode)
        self.assertIsNone(proc.poll())
        proc.kill()
        code = proc.wait(timeout=5)
        self.assertEqual(code, -signal.SIGKILL)
        self.report.update(pid=proc.pid, killed=True, reaped=True, returncode=code, setup=checkpoint,
                           action='owned SIGKILL then wait and fresh managed reopen')
        return checkpoint

    def recover_case(self, mode):
        old = self.crash(mode)
        owners, provider = self.open()
        provider.forbid_entry = True
        before = owners.snapshot()
        result = value(owners.tasks.recover({'key': 'recover', 'lease_id': old['call']['lease_id']}))
        self.assertEqual(owners.counters(), old['counters'])
        self.assertEqual(provider.calls, [])
        self.assertEqual(owners.native_hash(), old['native_side_sha256'])
        call = owners.call()
        self.report['recovery'] = result
        if mode in ('prepared', 'entering'):
            self.assertEqual(result['disposition'], 'held')
            self.assertEqual(owners.snapshot(), before)
            self.assertEqual((call['status'], call['native_phase']), ('admitted', mode))
            self.assertFalse(owners.tasks.finish_startup().ok)
            self.assertEqual(owners.guard.phase, 'startup')
            self.assertFalse(owners.tasks.reserve_budget({'key': 'blocked-primary', 'kind': 'model', 'role': 'primary'}).ok)
            self.assertFalse(owners.runner.execute_next().ok)
            self.assertEqual(owners.snapshot(), before)
            self.assertEqual(old['provider_invocations'], 0 if mode == 'prepared' else 1)
            value(owners.tasks.control({'key': 'cancel', 'work_ref': call['work_ref'], 'command': 'cancel'}))
            self.assertEqual(owners.current(old['work_ref'])['state'], 'cancelled')
            self.assertEqual(value(owners.tasks.recover({'key': 'recover', 'lease_id': call['lease_id']}))['disposition'], 'held')
            self.assertFalse(owners.tasks.finish_startup().ok)
        else:
            self.assertEqual(result['disposition'], 'settled')
            self.assertEqual(result['interrupted_call_ids'], [])
            self.assertEqual(call['status'], 'returned')
            self.assertEqual(old['provider_invocations'], 1)
            owners.ready()
            self.assertFalse(owners.tasks.get_native_output({k: old['call'][k] for k in ('call_id', 'lease_id', 'work_ref')}).ok)
            if mode == 'returned':
                self.assertEqual(result['reason'], 'native_returned_unadopted')
                self.assertEqual(owners.current(old['work_ref'])['current_artifact_refs'], [])
                self.assertEqual(owners.conn.execute('SELECT COUNT(*) FROM v5_tsk_step').fetchone()[0], 0)
            else:
                self.assertEqual(len(owners.lookup_requests), 1)
                self.assertEqual(owners.lookup_requests[0]['key'], old['save_key'])
                current = owners.current(old['work_ref'])
                self.assertEqual(current['current_artifact_refs'], [old['receipt']['artifact_ref']])
                self.assertEqual(value(owners.art.get_by_key({'key': old['save_key']})), old['receipt'])
                body = value(owners.art.read({'ref': old['receipt']['artifact_ref']}, purpose='user_view'))
                self.assertEqual(body['hash'], old['artifact_sha256'])
                self.assertEqual(owners.conn.execute('SELECT COUNT(*) FROM v5_tsk_step').fetchone()[0], 1)
                def refuse_save(*args, **kwargs):
                    raise AssertionError('saved tail must not dispatch save again')
                owners.art.save = refuse_save
                completed = value(owners.runner.execute_next())
                self.assertEqual(completed['state'], 'completed')
                self.assertEqual(owners.counters(), old['counters'])
                view = value(inspect_session({'session_id': 'session'}, events=EventReader(owners.conn),
                    tasks=owners.tasks, reader=HostReader(owners.mem, owners.art, owners.ver)))
                self.assertTrue(view['items'])
                self.report['fresh_verification_completed'] = True
                self.report['artifact_sha256'] = body['hash']
        self.assertEqual(provider.calls, [])
        self.assertEqual(owners.counters(), old['counters'])
        self.report.update(passed=True, post_restart_invocations=0, counters=owners.counters(),
                           result_call=owners.call(), native_side_sha256=owners.native_hash(),
                           artifact_lookup_count=len(owners.lookup_requests), native_cessation_proven=False)

    def test_sigkill_prepared_orphan_held(self):
        self.recover_case('prepared')

    def test_sigkill_entering_orphan_held(self):
        self.recover_case('entering')

    def test_sigkill_returned_without_step_settles_only_lease(self):
        self.recover_case('returned')

    def test_sigkill_saved_artifact_tail_lookup_fresh_verification(self):
        self.recover_case('saved')

    def race(self, kind):
        owners, provider = self.open()
        work, origin = owners.setup()
        entered = threading.Event()
        release = threading.Event()
        out, errors, calls = [], [], []
        def worker():
            local = None
            try:
                p = Provider()
                local = Owners(self.path, owners.guard, p)
                def blocked(request, attempt):
                    calls.append(request)
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError('fixture release timeout')
                p.behavior = blocked
                out.append(local.runner.execute_next())
            except BaseException as exc:
                errors.append(type(exc).__name__)
            finally:
                if local:
                    local.close()
        thread = threading.Thread(target=worker, name='native-expert-fixture')
        thread.start()
        try:
            self.assertTrue(entered.wait(5), 'entry barrier absent')
            self.assertFalse(owners.conn.in_transaction)
            call = owners.call()
            reservation = value(owners.tasks.reserve_budget({'key': 'parallel-primary', 'kind': 'model', 'role': 'primary'}))
            value(owners.tasks.consume({'reservation_id': reservation['reservation_id'], 'call_or_operation_id': 'fixture-primary'}))
            if kind == 'pause':
                control = value(owners.tasks.control({'key': 'pause', 'work_ref': call['work_ref'], 'command': 'pause'}))
                self.assertEqual(control['control_status'], 'pause_requested')
            else:
                control = value(owners.mem.stop_reference({'key': 'stop', 'source_ref': origin}, session_id='session'))
            self.assertTrue(thread.is_alive())
            self.assertFalse(release.is_set())
        finally:
            release.set()
            thread.join(6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(owners.call()['status'], 'returned')
        self.assertEqual(owners.current(work)['current_artifact_refs'], [])
        self.assertEqual(owners.conn.execute('SELECT COUNT(*) FROM v5_tsk_step').fetchone()[0], 0)
        self.assertEqual(dict(owners.counters()['host']), {'model': 2, 'step': 0})
        self.assertEqual(owners.guard.phase, 'ready')
        if kind == 'pause':
            self.assertEqual(owners.current(work)['state'], 'paused')
        self.report.update(passed=True, pid=os.getpid(), worker_thread_joined=True, killed=False,
            reaped=False, action='second connection '+kind+' before fixture callback returned', control=control,
            provider_invocations=1, result=out[0].to_json(), result_call=owners.call(), counters=owners.counters(),
            primary_same_session_reservation_allowed=True, native_cessation_proven=False)

    def test_two_connections_pause_during_owned_callback(self):
        self.race('pause')

    def test_two_connections_source_stop_during_owned_callback(self):
        self.race('stop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new local JSON receipt path')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; preserve the original receipt')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LifetimeTests))
    sources = ['tools/verify_native_expert_lifetime_v5.py', 'pal/tasks_v5.py', 'pal/native_expert_runner_v5.py',
               'pal/mock_runner_v5.py', 'pal/native_call_v5.py', 'pal/native_text_v5.py', 'pal/mock_host_v5.py',
               'pal/artifacts_v5.py', 'pal/memory_v5.py', 'pal/verification_v5.py', 'pal/read_consumer_v5.py']
    receipt = {'version': 'PRI03-LIFETIME-FIXTURE/1', 'passed': result.wasSuccessful(),
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'cases': REPORTS, 'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'limits': ['fixture endings only', 'SIGKILL proves only this owned local fixture exit',
                   'no provider/CO/native capacity operation', 'no actual native qualification or product completion']}
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps({'passed': receipt['passed'], 'tests_run': result.testsRun, 'output': str(args.output)}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--child':
        child(Path(sys.argv[2]), sys.argv[3])
    else:
        raise SystemExit(main())
