"""Actual MEM/TSK/mock/ART owners on a reopened and contended temporary database."""
import copy
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, dumps
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.mock_runner_v5 import MockInvoker
from pal.tasks_v5 import TaskStore


class FaultConnection(sqlite3.Connection):
    artifact_fault = None

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if self.artifact_fault and sql.lstrip().upper().startswith('INSERT') and 'v5_art_' in sql:
            failure, self.artifact_fault = self.artifact_fault, None
            raise failure('injected after actual artifact write')
        return result


class ArtifactConnectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'draft.sqlite'
        self.conn, self.tasks, self.memory, self.artifacts = self.connect()
        self.serial = 0
        self.calls = 0

    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=0,
                                     factory=FaultConnection)
        self.addCleanup(connection.close)
        memory = None
        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        tasks = TaskStore(connection, host_limits=Limits(0, 50, 50), host_grant=grant,
                          expert_id='expert', source_gate=lambda c, refs: memory.source_gate(c, refs))
        memory = MemoryStore(connection, sanitize_text=lambda text: text,
                             append_event=tasks.append_event,
                             invalidate_by_refs=tasks.invalidate_by_refs)
        artifacts = ArtifactStore(connection, authorize_save=tasks.authorize_artifact_save,
                                  source_gate=memory.source_gate)
        return connection, tasks, memory, artifacts

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        self.assertLess(len(result.error.message), 150)

    def record(self, key, text):
        return self.value(self.memory.append({'client_key': key, 'session_id': 'draft-session',
                                              'role': 'user', 'text': text}))['record_ref']

    def stage(self):
        self.serial += 1
        prefix = str(self.serial)
        origin = self.record(prefix + '-origin', '下書きを作り、送信せず保存してください。')
        extra = self.record(prefix + '-extra', '確認した会議日程は月曜日です。')
        request = {'key': prefix, 'session_id': 'draft-session', 'origin_record_ref': origin,
                   'brief': {'purpose': 'Prepare a local draft',
                             'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                             'constraints': ['Do not send'], 'context_refs': [],
                             'conditions': [{'description': 'Draft saved', 'check': 'artifact_saved'}]}}
        grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        self.value(self.tasks.create(request, request_scope=grant))
        lease = self.value(self.tasks.claim({'runner_id': 'artifact-' + prefix}))
        work = lease['work_ref']
        refs = [origin, extra]
        self.value(self.tasks.register_sources({'work_ref': work, 'refs': refs}))
        bodies = [self.value(self.memory.read({'ref': ref}, purpose='model_context')) for ref in refs]
        reservation = self.value(self.tasks.reserve_budget({
            'key': 'model-' + prefix, 'work_ref': work, 'kind': 'model', 'role': 'expert'}))
        call_id = dumps(['C15.call', lease['lease_id'], 0])
        def expert():
            self.calls += 1
            self.assertFalse(self.conn.in_transaction)
            return {'kind': 'compose', 'content': '下書き\n' + bodies[1]['content'] + '\r\n',
                    'media_type': 'text/markdown', 'source_refs': [origin]}
        returned = self.value(MockInvoker().invoke(self.tasks, {
            'call_id': call_id, 'lease_id': lease['lease_id'], 'work_ref': work,
            'reservation_id': reservation['reservation_id'], 'source_refs': refs}, expert))
        action = returned['action']
        step = self.value(self.tasks.begin_step({
            'key': 'begin-' + prefix, 'work_ref': work, 'action': action}))
        save = {'key': dumps(['C08.save', work, step['step_id']]), 'work_ref': work,
                'step_id': step['step_id'], **{k: v for k, v in action.items() if k != 'kind'}}
        return lease, save, refs

    def stop_on_another_connection(self, ref):
        _, _, memory, _ = self.connect()
        return self.value(memory.stop_reference({'key': 'stop-' + ref['id'], 'source_ref': ref},
                                                session_id='control-session'))

    def test_saved_bytes_reopen_and_receipt_do_not_complete_or_attach_work(self):
        lease, request, refs = self.stage()
        receipt = self.value(self.artifacts.save(request))
        data = request['content'].encode('utf-8')
        self.assertEqual(receipt['hash'], hashlib.sha256(data).hexdigest())
        self.assertEqual(receipt['bytes'], len(data))
        self.assertEqual(set(receipt), {'artifact_ref', 'hash', 'bytes'})
        self.assertEqual(self.value(self.artifacts.save(request)), receipt)
        self.conn.close()
        self.conn, self.tasks, self.memory, self.artifacts = self.connect()
        self.assertEqual(self.value(self.artifacts.get_by_key({'key': request['key']})), receipt)
        changes = self.conn.total_changes
        content = self.value(self.artifacts.read({'ref': receipt['artifact_ref']}, purpose='verification'))
        self.assertEqual(set(content), {'ref', 'content', 'media_type', 'hash', 'observed_at',
                                       'work_ref', 'source_refs', 'usable'})
        self.assertEqual(content['content'].encode('utf-8'), data)
        self.assertEqual(content['source_refs'], refs)
        self.assertEqual(content['work_ref'], lease['work_ref'])
        self.assertTrue(content['usable'])
        self.assertEqual(changes, self.conn.total_changes)
        self.assertFalse(self.conn.in_transaction)
        current = self.value(self.tasks.get_work({'goal_id': lease['work_ref']['goal_id']}))
        self.assertEqual(current['state'], 'running')
        self.assertEqual(current['current_artifact_refs'], [])
        self.error(self.tasks.finish_step({'work_ref': lease['work_ref'],
                   'step_id': request['step_id'], 'result_refs': [receipt['artifact_ref']]}), 'unavailable')
        self.assertEqual(self.calls, 1)

    def test_stop_after_save_blocks_unselected_dependency_but_preserves_history_and_receipt(self):
        lease, request, refs = self.stage()
        receipt = self.value(self.artifacts.save(request))
        self.assertNotIn(refs[1], request['source_refs'])
        self.stop_on_another_connection(refs[1])
        for purpose in ('model_context', 'verification'):
            self.error(self.artifacts.read({'ref': receipt['artifact_ref']}, purpose=purpose), 'denied')
        history = self.value(self.artifacts.read({'ref': receipt['artifact_ref']}, purpose='user_view'))
        self.assertFalse(history['usable'])
        self.assertEqual(history['content'], request['content'])
        self.assertEqual(self.value(self.artifacts.get_by_key({'key': request['key']})), receipt)
        changes = self.conn.total_changes
        self.assertEqual(self.value(self.artifacts.save(request)), receipt)
        self.assertEqual(changes, self.conn.total_changes)
        released = self.value(self.tasks.release({'lease_id': lease['lease_id'],
            'work_ref': lease['work_ref'], 'outcome': 'yield', 'reason': 'source stopped'}))
        self.assertEqual(released['state'], 'queued')
        events = self.value(EventReader(self.conn).get_events({'session_id': 'draft-session'}))['events']
        self.assertTrue(any(event['kind'] == 'state' and event['text'] == 'source use stopped'
                            for event in events))

    def test_stop_committed_before_save_rejects_old_authority_without_artifact(self):
        _, request, refs = self.stage()
        self.stop_on_another_connection(refs[1])
        self.error(self.artifacts.save(request), 'stale')
        self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
        self.assertFalse(self.conn.in_transaction)

    def test_pause_and_cancel_before_save_preserve_latest_owner_intent(self):
        for command, code, state in [('pause', 'conflict', 'paused'), ('cancel', 'stale', 'cancelled')]:
            with self.subTest(command=command):
                lease, request, _ = self.stage()
                self.value(self.tasks.control({'key': command, 'work_ref': lease['work_ref'],
                                               'command': command}))
                self.error(self.artifacts.save(request), code)
                self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
                released = self.value(self.tasks.release({'lease_id': lease['lease_id'],
                    'work_ref': lease['work_ref'], 'outcome': 'yield', 'reason': command}))
                self.assertEqual(released['state'], state)

    def test_actual_step_action_and_source_membership_are_checked_before_saving(self):
        _, request, _ = self.stage()
        for field, value, code in [('content', 'different', 'conflict'),
                                   ('step_id', 'absent', 'not_found'),
                                   ('source_refs', [{'kind': 'record', 'id': 'never supplied'}], 'denied')]:
            with self.subTest(field=field):
                changed = copy.deepcopy(request)
                changed[field] = value
                self.error(self.artifacts.save(changed), code)
                self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
        receipt = self.value(self.artifacts.save(request))
        self.error(self.artifacts.save({**request, 'key': 'different key same step'}), 'conflict')
        self.assertEqual(self.value(self.artifacts.get_by_key({'key': request['key']})), receipt)

    def test_busy_database_does_not_burn_key_or_save_partial_content(self):
        _, request, _ = self.stage()
        other = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(other.close)
        other.execute('BEGIN IMMEDIATE')
        try:
            self.error(self.artifacts.save(request), 'unavailable')
            self.assertFalse(self.conn.in_transaction)
        finally:
            other.rollback()
        self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
        self.value(self.artifacts.save(request))

    def test_fault_after_actual_artifact_insert_rolls_back_and_key_can_retry(self):
        _, request, _ = self.stage()
        self.conn.artifact_fault = RuntimeError
        self.error(self.artifacts.save(request), 'unavailable')
        self.assertIsNone(self.conn.artifact_fault, 'fault did not reach an actual ART INSERT')
        self.assertFalse(self.conn.in_transaction)
        self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
        self.value(self.artifacts.save(request))

    def test_process_interrupt_after_artifact_write_releases_transaction_not_execution_lease(self):
        lease, request, _ = self.stage()
        for interrupt in (KeyboardInterrupt, SystemExit):
            with self.subTest(interrupt=interrupt):
                self.conn.artifact_fault = interrupt
                with self.assertRaises(interrupt):
                    self.artifacts.save(request)
                self.assertFalse(self.conn.in_transaction)
                self.error(self.artifacts.get_by_key({'key': request['key']}), 'not_found')
                other = sqlite3.connect(self.path, isolation_level=None, timeout=0)
                try:
                    other.execute('BEGIN IMMEDIATE')
                    other.rollback()
                finally:
                    other.close()
        self.error(self.tasks.claim({'runner_id': 'fresh-process'}), 'conflict')
        self.assertEqual(self.value(self.tasks.get_work({'goal_id': lease['work_ref']['goal_id']}))['state'],
                         'running')
        self.value(self.artifacts.save(request))


if __name__ == '__main__':
    unittest.main()
