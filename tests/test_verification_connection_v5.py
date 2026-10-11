"""Real local owners: immutable verification, invalidation, and atomic ordering."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, Result, dumps
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockInvoker
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


class FaultConnection(sqlite3.Connection):
    verification_fault = None

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if (self.verification_fault and sql.lstrip().upper().startswith('INSERT')
                and 'v5_ver_' in sql):
            failure, self.verification_fault = self.verification_fault, None
            raise failure('injected after actual verification write')
        return result


class VerificationConnectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'verification.sqlite'
        self.conn, self.tasks, self.memory, self.artifacts, self.verifications = self.connect()
        self.calls = 0
        self.refs = []
        self.saved_refs = []

    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=0,
                                     factory=FaultConnection)
        self.addCleanup(connection.close)
        memory = artifacts = None
        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        tasks = TaskStore(connection, host_limits=Limits(0, 50, 50), host_grant=grant,
            expert_id='expert', source_gate=lambda c, refs: memory.source_gate(c, refs),
            artifact_inspect=lambda c, request: artifacts.inspect(c, request))
        memory = MemoryStore(connection, sanitize_text=lambda text: text,
            append_event=tasks.append_event, invalidate_by_refs=tasks.invalidate_by_refs)
        artifacts = ArtifactStore(connection, authorize_save=tasks.authorize_artifact_save,
                                  source_gate=memory.source_gate)
        verifications = VerificationStore(connection, context=tasks.verification_context,
            artifact_inspect=artifacts.inspect, source_gate=memory.source_gate)
        return connection, tasks, memory, artifacts, verifications

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)

    def stage(self, *, all_kinds=False):
        for key, text in [('origin', '会議の下書きを保存'), ('extra', '確認済み日程は月曜日')]:
            self.refs.append(self.value(self.memory.append({'client_key': key,
                'session_id': 'draft-session', 'role': 'user', 'text': text}))['record_ref'])
        checks = ['artifact_saved', 'semantic', 'source_fetched'] if all_kinds else ['artifact_saved']
        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        self.value(self.tasks.create({'key': 'create', 'session_id': 'draft-session',
            'origin_record_ref': self.refs[0], 'brief': {'purpose': 'Saved local draft',
            'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
            'constraints': ['Do not send'], 'context_refs': [],
            'conditions': [{'description': kind, 'check': kind} for kind in checks]}},
            request_scope=grant))
        self.lease = self.value(self.tasks.claim({'runner_id': 'verify-host'}))
        self.work = self.lease['work_ref']
        self.value(self.tasks.register_sources({'work_ref': self.work, 'refs': self.refs}))

    def compose(self, *, finish=True):
        index = self.calls
        reservation = self.value(self.tasks.reserve_budget({'key': 'model-' + str(index),
            'work_ref': self.work, 'kind': 'model', 'role': 'expert'}))
        bodies = [self.value(self.memory.read({'ref': ref}, purpose='model_context')) for ref in self.refs]
        def expert():
            self.calls += 1
            self.assertFalse(self.conn.in_transaction)
            return {'kind': 'compose', 'content': '下書き' + str(index) + '\n' + bodies[1]['content'],
                    'media_type': 'text/plain', 'source_refs': [self.refs[0]]}
        action = self.value(MockInvoker().invoke(self.tasks, {'call_id': dumps(['C15.call', self.lease['lease_id'], index]),
            'lease_id': self.lease['lease_id'], 'work_ref': self.work,
            'reservation_id': reservation['reservation_id'], 'source_refs': self.refs}, expert))['action']
        step = self.value(self.tasks.begin_step({'key': 'begin-' + str(index),
            'work_ref': self.work, 'action': action}))
        receipt = self.value(self.artifacts.save({'key': dumps(['C08.save', self.work, step['step_id']]), 'work_ref': self.work,
            'step_id': step['step_id'], **{k: v for k, v in action.items() if k != 'kind'}}))
        request = {'work_ref': self.work, 'step_id': step['step_id'],
                   'result_refs': [receipt['artifact_ref']]}
        if finish:
            self.value(self.tasks.finish_step(request))
            self.saved_refs.append(receipt['artifact_ref'])
        return request

    def request(self, key='verify'):
        return {'key': key, 'work_ref': copy.deepcopy(self.work),
                'artifact_refs': copy.deepcopy(self.saved_refs)}

    def verify(self, key='verify'):
        return self.value(self.verifications.verify(self.request(key)))

    def status(self, receipt):
        return self.verifications.get_verification({'verification_ref': receipt['verification_ref']})

    def current(self):
        return self.value(self.tasks.get_work({'goal_id': self.work['goal_id']}))

    def stop(self, memory, ref):
        return memory.stop_reference({'key': 'stop-' + ref['id'], 'source_ref': ref}, session_id='control-session')

    def usage(self):
        return dict(self.conn.execute('SELECT kind,used FROM v5_tsk_usage WHERE goal=?',
                                     (self.work['goal_id'],)).fetchall())

    def test_actual_saved_draft_verifies_without_completion_or_extra_budget(self):
        self.stage(all_kinds=True)
        self.compose()
        before = self.usage()
        receipt = self.verify()
        self.assertEqual([c['status'] for c in receipt['checks']], ['met', 'unknown', 'unknown'])
        self.assertEqual([c['condition_id'] for c in receipt['checks']],
                         [c['id'] for c in self.current()['brief']['conditions']])
        typed = self.value(self.status(receipt))
        self.assertEqual((typed['status'], typed['artifact_refs']), ('valid', self.saved_refs))
        self.assertEqual({dumps(ref) for ref in typed['source_refs']}, {dumps(ref) for ref in self.refs})
        self.assertEqual((self.current()['state'], self.calls, self.usage()), ('running', 1, before))
        self.conn.close()
        self.conn, self.tasks, self.memory, self.artifacts, self.verifications = self.connect()
        self.assertEqual(self.value(self.status(receipt)), typed)
        self.assertEqual(self.verify(), receipt)
        self.assertEqual(self.value(self.verifications.get_by_key({'key': 'verify'})), receipt)

    def test_empty_set_is_unmet_and_unknown_without_a_model_call(self):
        self.stage(all_kinds=True)
        receipt = self.verify()
        self.assertEqual([c['status'] for c in receipt['checks']], ['unmet', 'unknown', 'unknown'])
        self.assertEqual((self.calls, self.usage(), self.current()['state']), (0, {}, 'running'))

    def test_exact_whole_ordered_set_and_original_input_identity(self):
        self.stage()
        self.compose()
        self.compose()
        for refs in (self.saved_refs[:1], list(reversed(self.saved_refs)), self.saved_refs * 2):
            self.error(self.verifications.verify({**self.request(), 'artifact_refs': refs}), 'conflict')
        receipt = self.verify()
        self.assertEqual(self.verify(), receipt)
        self.error(self.verifications.verify({**self.request(), 'artifact_refs': []}), 'conflict')

    def test_next_epoch_invalidates_but_new_verification_accepts_older_saved_artifact(self):
        self.stage()
        self.compose()
        old_request, receipt = self.request(), self.verify()
        self.value(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.work,
                                      'outcome': 'yield', 'reason': 'draft prepared'}))
        self.lease = self.value(self.tasks.claim({'runner_id': 'next'}))
        self.work = self.lease['work_ref']
        self.assertGreater(self.work['epoch'], old_request['work_ref']['epoch'])
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.assertEqual(self.value(self.verifications.verify(old_request)), receipt)
        current = self.verify('next-epoch')
        self.assertEqual(self.value(self.status(current))['status'], 'valid')
        self.assertEqual((self.calls, self.usage()), (1, {'model': 1, 'step': 1}))

    def test_later_attachment_invalidates_old_whole_set_snapshot(self):
        self.stage()
        self.compose()
        receipt = self.verify()
        self.compose()
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.assertEqual(self.value(self.status(self.verify('two-artifacts')))['status'], 'valid')

    def test_selected_and_unselected_source_stops_invalidate_and_preserve_history(self):
        for selected in (True, False):
            with self.subTest(selected=selected):
                if not selected:
                    self.setUp()
                self.stage()
                self.compose()
                request, receipt = self.request(), self.verify()
                _, _, memory, _, _ = self.connect()
                self.value(self.stop(memory, self.refs[0 if selected else 1]))
                self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
                self.assertEqual(self.value(self.verifications.verify(request)), receipt)
                self.assertEqual(self.value(self.verifications.get_by_key({'key': 'verify'})), receipt)
                self.error(self.artifacts.read({'ref': self.saved_refs[0]}, purpose='verification'), 'denied')
                self.assertFalse(self.value(self.artifacts.read({'ref': self.saved_refs[0]}, purpose='user_view'))['usable'])
                self.assertNotEqual(self.current()['state'], 'completed')

    def test_pause_keeps_factual_status_valid_while_refusing_new_save(self):
        self.stage()
        self.compose()
        receipt = self.verify()
        self.value(self.tasks.control({'key': 'pause', 'work_ref': self.work, 'command': 'pause'}))
        self.assertEqual(self.value(self.status(receipt))['status'], 'valid')
        self.error(self.verifications.verify(self.request('during-pause')), 'conflict')
        self.value(self.tasks.release({'lease_id': self.lease['lease_id'], 'work_ref': self.work,
                                      'outcome': 'yield', 'reason': 'pause'}))
        self.assertEqual(self.value(self.status(receipt))['status'], 'valid')
        self.error(self.verifications.verify(self.request('after-pause')), 'denied')

    def test_missing_owner_evidence_and_corrupt_bytes_are_unavailable(self):
        for corruption in ('artifact', 'body', 'memory', 'set'):
            with self.subTest(corruption=corruption):
                if corruption != 'artifact':
                    self.setUp()
                self.stage()
                self.compose()
                receipt = self.verify()
                if corruption == 'artifact':
                    self.conn.execute('DELETE FROM v5_art_body')
                elif corruption == 'body':
                    self.conn.execute("UPDATE v5_art_body SET body=X'616263'")
                elif corruption == 'memory':
                    self.conn.execute('DELETE FROM v5_mem_record WHERE id=?', (self.refs[1]['id'],))
                else:
                    self.conn.execute('DELETE FROM v5_tsk_artifact_set')
                self.error(self.status(receipt), 'unavailable')
                self.error(self.verifications.verify(self.request('corrupt-evidence')), 'unavailable')

    def test_verify_write_lock_orders_source_stop_and_never_mixes_snapshots(self):
        self.stage()
        self.compose()
        _, _, memory, _, _ = self.connect()
        attempts = []
        def context(conn, request, *, purpose):
            if purpose == 'save':
                attempts.append(self.stop(memory, self.refs[1]))
            return self.tasks.verification_context(conn, request, purpose=purpose)
        store = VerificationStore(self.conn, context=context, artifact_inspect=self.artifacts.inspect,
                                  source_gate=self.memory.source_gate)
        receipt = self.value(store.verify(self.request()))
        self.assertEqual(len(attempts), 1)
        self.error(attempts[0], 'unavailable')
        self.assertEqual(self.value(self.status(receipt))['status'], 'valid')
        self.value(self.stop(memory, self.refs[1]))
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.error(store.verify(self.request('stop-first')), 'stale')
        self.error(store.get_by_key({'key': 'stop-first'}), 'not_found')

    def test_verify_write_lock_orders_artifact_attachment(self):
        self.stage()
        self.compose()
        finish = self.compose(finish=False)
        _, tasks, _, _, _ = self.connect()
        attempts = []
        def context(conn, request, *, purpose):
            if purpose == 'save':
                attempts.append(tasks.finish_step(finish))
            return self.tasks.verification_context(conn, request, purpose=purpose)
        store = VerificationStore(self.conn, context=context, artifact_inspect=self.artifacts.inspect,
                                  source_gate=self.memory.source_gate)
        receipt = self.value(store.verify(self.request()))
        self.assertEqual(len(attempts), 1)
        self.error(attempts[0], 'unavailable')
        self.assertEqual(self.value(self.status(receipt))['status'], 'valid')
        self.value(tasks.finish_step(finish))
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.error(self.verifications.verify(self.request('attachment-first')), 'conflict')

    def test_actual_verification_write_faults_and_interrupts_leave_no_partial_key(self):
        self.stage()
        self.compose()
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            self.conn.verification_fault = failure
            if issubclass(failure, Exception):
                self.error(self.verifications.verify(self.request()), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.verifications.verify(self.request())
            self.assertIsNone(self.conn.verification_fault)
            self.assertFalse(self.conn.in_transaction)
            _, _, _, _, reopened = self.connect()
            self.error(reopened.get_by_key({'key': 'verify'}), 'not_found')
        self.assertEqual(self.value(self.status(self.verify()))['status'], 'valid')
        self.assertEqual((self.calls, self.usage()), (1, {'model': 1, 'step': 1}))

    def test_actual_inspect_is_readonly_and_callback_failure_preserves_caller_writes(self):
        self.stage()
        self.compose()
        receipt = self.verify()
        typed = self.value(self.status(receipt))
        self.conn.execute('CREATE TABLE caller (value INTEGER)')
        self.conn.execute('INSERT INTO caller VALUES (7)')
        def mutating(conn, request, *, purpose):
            conn.execute('UPDATE caller SET value=0')
            return self.tasks.verification_context(conn, request, purpose=purpose)
        bad = VerificationStore(self.conn, context=mutating, artifact_inspect=self.artifacts.inspect,
                                source_gate=self.memory.source_gate)
        self.conn.execute('BEGIN')
        self.conn.execute('UPDATE caller SET value=6')
        changes = self.conn.total_changes
        request = {'verification_ref': receipt['verification_ref']}
        self.assertEqual(self.value(self.verifications.inspect(self.conn, request)), typed)
        self.assertEqual(self.conn.total_changes, changes)
        self.error(bad.inspect(self.conn, request), 'unavailable')
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(self.conn.execute('SELECT value FROM caller').fetchone()[0], 6)
        self.conn.rollback()
        self.assertEqual(self.conn.execute('SELECT value FROM caller').fetchone()[0], 7)


if __name__ == '__main__':
    unittest.main()
