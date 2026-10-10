"""Managed restart through actual temporary owners; no provider or old DB."""
import contextlib
import json
import select
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, dumps
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockInvoker, MockRunner
from pal.read_consumer_v5 import inspect_session
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore

ROOT = Path(__file__).resolve().parents[1]


def value(result):
    if not result.ok:
        raise AssertionError(result.error.code.value)
    return result.value.to_json()


class Owners:
    def __init__(self, path, guard=None):
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.guard = guard
        self.memory = self.artifacts = self.verifications = None
        self.grant = Grant((), ('demo',), Limits(0, 8, 8))
        self.tasks = TaskStore(self.conn, host_limits=Limits(0, 30, 30),
            startup_guard=guard, host_grant=self.grant, expert_id='mock-expert',
            source_gate=lambda c, refs: self.memory.source_gate(c, refs),
            artifact_inspect=lambda c, req: self.artifacts.inspect(c, req),
            verification_inspect=lambda c, req: self.verifications.inspect(c, req))
        self.memory = MemoryStore(self.conn, sanitize_text=lambda s: s,
            append_event=self.tasks.append_event, invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.artifacts = ArtifactStore(self.conn, authorize_save=self.tasks.authorize_artifact_save,
                                      source_gate=self.memory.source_gate)
        self.verifications = VerificationStore(self.conn, context=self.tasks.verification_context,
            artifact_inspect=self.artifacts.inspect, source_gate=self.memory.source_gate)

    def startup(self):
        registration = value(self.tasks.register_host())
        if registration['orphan_lease_id'] is not None:
            recovered = value(self.tasks.recover({'key': 'restart',
                'lease_id': registration['orphan_lease_id']}))
            if recovered['disposition'] == 'held':
                return recovered
        value(self.tasks.finish_startup())
        return registration

    def create(self):
        origin = value(self.memory.append({'client_key': 'request', 'session_id': 'restart-demo',
            'role': 'user', 'text': '打合せの案内の下書きを保存する。送信しない。'}))['record_ref']
        created = value(self.tasks.create({'key': 'create', 'session_id': 'restart-demo',
            'origin_record_ref': origin, 'brief': {
                'purpose': '案内の下書きを保存する',
                'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
                'constraints': ['送信しない'], 'context_refs': [],
                'conditions': [{'description': '下書きが保存されている', 'check': 'artifact_saved'}]}},
            request_scope=self.grant))
        return created['work_ref'], origin

    def runner(self):
        return MockRunner(self.tasks, self.memory, artifacts=self.artifacts,
                          verifications=self.verifications)

    def close(self):
        self.conn.close()
        if self.guard is not None and self.guard.phase != 'closed':
            self.guard.close()


def _old_owner(path):
    from pal.mock_host_v5 import MockHostSession
    guard = MockHostSession.open(path)
    owners = Owners(path, guard)
    owners.startup()
    owners.create()
    def blocked(context, **diagnostics):
        lease = owners.conn.execute('SELECT id FROM v5_tsk_lease WHERE active=1').fetchone()[0]
        print(json.dumps({'lease_id': lease, 'work_ref': context['work_ref']}), flush=True)
        sys.stdin.buffer.read(1)
        return {'kind': 'report', 'summary': 'old callback returned'}
    owners.runner().run_once(blocked)
    owners.close()


class MockRecoveryConnectionTests(unittest.TestCase):
    def setUp(self):
        from pal.mock_host_v5 import MockHostSession
        self.Host = MockHostSession
        self.directory = tempfile.TemporaryDirectory(prefix='pal-managed-connection-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'work.sqlite'
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)

    def open(self, *, startup=True):
        guard = self.Host.open(self.path)
        self.stack.callback(lambda: guard.close() if guard.phase != 'closed' else None)
        owners = Owners(self.path, guard)
        self.stack.callback(owners.close)
        if startup:
            owners.startup()
        return owners

    def stage(self, owners, action=None):
        work, origin = owners.create()
        lease = value(owners.tasks.claim({'runner_id': owners.guard.runner_id}))
        reservation = value(owners.tasks.reserve_budget({'key': 'model',
            'work_ref': lease['work_ref'], 'kind': 'model', 'role': 'expert'}))
        admission = {'call_id': dumps(['C15.call', lease['lease_id'], 0]),
            'lease_id': lease['lease_id'], 'work_ref': lease['work_ref'],
            'reservation_id': reservation['reservation_id'], 'source_refs': [origin]}
        if action is not None:
            value(MockInvoker().invoke(owners.tasks, admission, lambda: action(origin)))
        return lease, origin, admission

    def stopped_host(self, owners):
        owners.close()

    def restart(self, lease):
        owners = self.open(startup=False)
        registration = value(owners.tasks.register_host())
        self.assertEqual(registration['orphan_lease_id'], lease['lease_id'])
        recovered = value(owners.tasks.recover({'key': 'restart', 'lease_id': lease['lease_id']}))
        return owners, recovered

    def test_real_process_death_interrupts_old_call_and_runs_one_fresh_saved_checked_draft(self):
        code = 'import sys;sys.path.insert(0,sys.argv[2]);from test_mock_recovery_connection_v5 import _old_owner;_old_owner(sys.argv[1])'
        proc = subprocess.Popen([sys.executable, '-E', '-s', '-B', '-c', code,
            str(self.path), str(ROOT / 'tests')], cwd=ROOT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout], [], [], 10)[0], 'old callback not entered')
        line = proc.stdout.readline()
        self.assertTrue(line, 'old host exited before callback')
        old = json.loads(line)
        with self.assertRaises((RuntimeError, ValueError, OSError)):
            self.Host.open(self.path)
        proc.kill()
        proc.wait(timeout=5)
        owners, recovered = self.restart(old)
        self.assertEqual(recovered['disposition'], 'settled')
        self.assertEqual(recovered['work_ref']['epoch'], old['work_ref']['epoch'] + 1)
        old_call = owners.conn.execute('SELECT id,status FROM v5_tsk_call').fetchone()
        self.assertEqual((old_call[1], recovered['interrupted_call_ids']), ('interrupted', [old_call[0]]))
        self.assertEqual(owners.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0], 1)
        value(owners.tasks.finish_startup())
        calls = []
        def fresh(context, **diagnostics):
            calls.append(context['work_ref'])
            return {'kind': 'compose', 'content': '案内の下書き。送信前に確認してください。',
                'media_type': 'text/plain', 'source_refs': [body['ref'] for body in context['context']]}
        result = value(owners.runner().run_once(fresh))
        self.assertEqual((result['status'], len(calls)), ('completed', 1))
        self.assertEqual(calls[0]['goal_id'], old['work_ref']['goal_id'])
        self.assertEqual(owners.conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0], 1)
        self.assertEqual(owners.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0], 2)
        reader = HostReader(memory=owners.memory, artifacts=owners.artifacts,
                            verifications=owners.verifications)
        displayed = inspect_session({'session_id': 'restart-demo'},
            events=EventReader(owners.conn), tasks=owners.tasks, reader=reader)
        self.assertTrue(displayed.ok)

    def test_close_refuses_through_callback_and_end_record_attempt(self):
        owners = self.open()
        lease, origin, admission = self.stage(owners)
        original_end = owners.tasks.end_call
        def end(request):
            with self.assertRaises(RuntimeError):
                owners.guard.close()
            return original_end(request)
        owners.tasks.end_call = end
        def callback():
            with self.assertRaises(RuntimeError):
                owners.guard.close()
            return {'kind': 'report', 'summary': 'ended'}
        value(MockInvoker().invoke(owners.tasks, admission, callback))
        self.assertEqual(value(owners.tasks.get_call({'call_id': admission['call_id']}))['status'], 'returned')
        self.stopped_host(owners)
        restarted, recovered = self.restart(lease)
        self.assertEqual(recovered['interrupted_call_ids'], [])
        value(restarted.tasks.finish_startup())

    def test_baseexception_saves_raised_and_releases_lifetime_permit(self):
        class Abort(BaseException):
            pass
        owners = self.open()
        lease, origin, admission = self.stage(owners)
        def callback():
            with self.assertRaises(RuntimeError):
                owners.guard.close()
            raise Abort()
        with self.assertRaises(Abort):
            MockInvoker().invoke(owners.tasks, admission, callback)
        self.assertEqual(value(owners.tasks.get_call({'call_id': admission['call_id']}))['status'], 'raised')
        self.stopped_host(owners)
        restarted, recovered = self.restart(lease)
        self.assertEqual(recovered['disposition'], 'settled')
        value(restarted.tasks.finish_startup())

    def test_immediate_other_connection_cancel_during_activity_fences_output(self):
        owners = self.open()
        owners.create()
        control = Owners(self.path)
        self.stack.callback(control.close)
        calls = []
        def callback(context, **diagnostics):
            calls.append(context['work_ref'])
            value(control.tasks.control({'key': 'cancel', 'work_ref': context['work_ref'], 'command': 'cancel'}))
            with self.assertRaises(RuntimeError):
                owners.guard.close()
            return {'kind': 'compose', 'content': 'late output', 'media_type': 'text/plain',
                'source_refs': [body['ref'] for body in context['context']]}
        result = value(owners.runner().run_once(callback))
        self.assertEqual((result['state'], len(calls)), ('cancelled', 1))
        self.assertEqual(owners.conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0], 0)

    def test_saved_compose_unfinished_tail_is_held_without_another_save_or_callback(self):
        owners = self.open()
        lease, origin, admission = self.stage(owners, lambda ref: {
            'kind': 'compose', 'content': 'saved orphan body', 'media_type': 'text/plain', 'source_refs': [ref]})
        step = value(owners.tasks.begin_step({'key': 'begin', 'work_ref': lease['work_ref'],
            'action': {'kind': 'compose', 'content': 'saved orphan body',
                       'media_type': 'text/plain', 'source_refs': [origin]}}))
        key = dumps(['C08.save', lease['work_ref'], step['step_id']])
        receipt = value(owners.artifacts.save({'key': key, 'work_ref': lease['work_ref'],
            'step_id': step['step_id'], 'content': 'saved orphan body',
            'media_type': 'text/plain', 'source_refs': [origin]}))
        self.stopped_host(owners)
        restarted = self.open(startup=False)
        value(restarted.tasks.register_host())
        before = list(restarted.conn.iterdump())
        recovered = value(restarted.tasks.recover({'key': 'restart', 'lease_id': lease['lease_id']}))
        self.assertEqual((recovered['disposition'], recovered['reason'], recovered['step_id']),
                         ('held', 'artifact_tail', step['step_id']))
        self.assertEqual(list(restarted.conn.iterdump()), before)
        self.assertEqual(value(restarted.artifacts.get_by_key({'key': key})), receipt)
        self.assertFalse(restarted.tasks.finish_startup().ok)
        called = []
        result = restarted.runner().run_once(lambda *a, **kw: called.append(1))
        self.assertFalse(result.ok)
        self.assertEqual(called, [])
        self.assertEqual(restarted.conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0], 1)

    def test_finished_compose_recovery_reverifies_current_epoch_without_reinference(self):
        owners = self.open()
        lease, origin, admission = self.stage(owners, lambda ref: {
            'kind': 'compose', 'content': 'retained draft', 'media_type': 'text/plain', 'source_refs': [ref]})
        action = {'kind': 'compose', 'content': 'retained draft', 'media_type': 'text/plain', 'source_refs': [origin]}
        step = value(owners.tasks.begin_step({'key': 'begin', 'work_ref': lease['work_ref'], 'action': action}))
        saved = value(owners.artifacts.save({'key': dumps(['C08.save', lease['work_ref'], step['step_id']]),
            'work_ref': lease['work_ref'], 'step_id': step['step_id'],
            **{k: v for k, v in action.items() if k != 'kind'}}))
        value(owners.tasks.finish_step({'work_ref': lease['work_ref'], 'step_id': step['step_id'],
                                     'result_refs': [saved['artifact_ref']]}))
        old_verification = value(owners.verifications.verify({'key': dumps(['C09.verify',
            lease['work_ref'], [saved['artifact_ref']]]), 'work_ref': lease['work_ref'],
            'artifact_refs': [saved['artifact_ref']]}))
        self.stopped_host(owners)
        restarted, recovered = self.restart(lease)
        value(restarted.tasks.finish_startup())
        called = []
        result = value(restarted.runner().run_once(lambda *a, **kw: called.append(1)))
        self.assertEqual((result['status'], called), ('completed', []))
        self.assertNotEqual(result['verification']['verification_ref'], old_verification['verification_ref'])
        self.assertEqual(restarted.conn.execute('SELECT COUNT(*) FROM v5_art_body').fetchone()[0], 1)
        self.assertEqual(restarted.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
