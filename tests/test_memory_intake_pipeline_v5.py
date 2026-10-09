"""Real MEM/TSK connection on isolated SQLite; no provider, runner or live DB."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.contracts_v5 import Grant, Limits, Ref
from pal.intake_v5 import IntakeStore
from pal.memory_v5 import MemoryStore
from pal.sanitize import sanitize


class MemoryIntakePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'connected.sqlite'
        self.grant = Grant(('github.issue.read',), ('thattor/personal-agent-lab',), Limits(2, 4, 5))
        self.conn, self.intake, self.memory = self.connect()
        shared = Path(__file__).resolve().parents[1] / 'docs/design/contracts-v5/SHARED-EXAMPLES.json'
        self.example = next(x for x in json.loads(shared.read_text())['cases'] if x['id'] == 'CT-20-intake')

    def connect(self, *, append_wrapper=None, invalidate_wrapper=None):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(conn.close)
        memory = None
        intake = IntakeStore(conn, host_grant=self.grant, expert_id='expert',
                             source_gate=lambda c, refs: memory.source_gate(c, refs))
        append = intake.append_event
        invalidate = intake.invalidate_by_refs
        memory = MemoryStore(conn, sanitize_text=sanitize,
                             append_event=append if append_wrapper is None else append_wrapper(append),
                             invalidate_by_refs=invalidate if invalidate_wrapper is None else invalidate_wrapper(invalidate))
        return conn, intake, memory

    def record(self, key='shared-record', text=None):
        request = dict(self.example['append_request'], client_key=key)
        if text is not None:
            request['text'] = text
        result = self.memory.append(request)
        self.assertTrue(result.ok, result)
        return result.value.to_json()['record_ref']

    def create(self, origin, *, key='shared-intake', context=()):
        request = copy.deepcopy(self.example['intake_template'])
        request['key'] = key
        request['origin_record_ref'] = origin
        request['brief']['context_refs'] = list(context)
        result = self.intake.create(request, request_scope=self.grant)
        self.assertTrue(result.ok, result)
        return request, result

    def read(self, ref, purpose='model_context'):
        return self.memory.read({'ref': ref}, purpose=purpose)

    def snapshot(self):
        return '\n'.join(self.conn.iterdump())

    def stop(self, ref, key='stop'):
        return self.memory.stop_reference({'key': key, 'source_ref': ref}, session_id='control')

    def test_shared_append_search_intake_stop_read_and_historical_replay(self):
        ref = self.record()
        candidates = self.memory.search(self.example['search_request']).value.to_json()
        self.assertEqual(candidates, {'summaries': [], 'record_refs': [ref], 'truncated': False})
        request, accepted = self.create(ref)
        old = accepted.value.to_json()['work_ref']
        self.assertEqual(old['epoch'], self.example['expected']['initial_epoch'])
        self.assertTrue(self.stop(ref).ok)
        current = self.intake.get_work({'goal_id': old['goal_id']}).value.to_json()
        self.assertEqual(current['work_ref'], dict(old, epoch=1))
        self.assertEqual(current['state'], 'queued')
        snapshot = self.snapshot()
        self.assertEqual(self.intake.create(request, request_scope=self.grant), accepted)
        self.assertTrue(self.stop(ref).ok)
        self.assertEqual(self.snapshot(), snapshot)
        denied = self.intake.create(dict(request, key='fresh'), request_scope=self.grant)
        self.assertEqual(denied.error.code.value, 'denied')
        self.assertEqual(self.snapshot(), snapshot)
        self.assertEqual(self.read(ref).error.code.value, 'denied')
        self.assertEqual(self.read(ref, 'verification').error.code.value, 'denied')
        history = self.read(ref, 'user_view').value.to_json()
        self.assertFalse(history['usable'])
        self.assertEqual(history['content'], self.example['append_request']['text'])
        self.assertEqual(self.memory.search(self.example['search_request']).value.to_json()['record_refs'], [])
        rows = self.conn.execute('SELECT kind,work_ref_json FROM v5_intake_event ORDER BY seq').fetchall()
        self.assertEqual([row[0] for row in rows], ['accepted', 'accepted', 'state', 'state'])
        self.assertEqual(json.loads(rows[2][1]), dict(old, epoch=1))
        self.assertIsNone(rows[3][1])

    def test_context_source_stop_invalidates_only_dependent_work_and_survives_reopen(self):
        origin, context, other = self.record(), self.record('context', '参考'), self.record('other', '別件')
        _, accepted = self.create(origin, context=(context,))
        _, untouched = self.create(other, key='other')
        old = accepted.value.to_json()['work_ref']
        other_work = untouched.value.to_json()['work_ref']
        self.assertTrue(self.stop(context).ok)
        self.conn.close()
        self.conn, self.intake, self.memory = self.connect()
        self.assertEqual(self.intake.get_work({'goal_id': old['goal_id']}).value.to_json()['work_ref'], dict(old, epoch=1))
        self.assertEqual(self.intake.get_work({'goal_id': other_work['goal_id']}).value.to_json()['work_ref'], other_work)
        self.assertTrue(self.read(origin).ok)
        self.assertEqual(self.read(context).error.code.value, 'denied')

    def test_unsupported_work_state_rolls_back_source_stop(self):
        ref = self.record()
        _, accepted = self.create(ref)
        goal_id = accepted.value.to_json()['work_ref']['goal_id']
        for state in ('running', 'paused', 'waiting_input', 'completed'):
            with self.subTest(state=state):
                self.conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=?', (state, goal_id))
                before = self.snapshot()
                self.assertEqual(self.stop(ref).error.code.value, 'unavailable')
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.read(ref).ok)
        self.conn.execute("UPDATE v5_intake_work SET state='queued'")
        self.assertTrue(self.stop(ref).ok)

    def test_failure_after_real_invalidation_or_event_rolls_back_all_owners(self):
        ref = self.record()
        self.create(ref)
        before = self.snapshot()
        def failing(callback):
            def invoke(*args, **kwargs):
                callback(*args, **kwargs)
                raise RuntimeError('PRIVATE_FAILURE_PAYLOAD')
            return invoke
        for kind in ('invalidate_wrapper', 'append_wrapper'):
            with self.subTest(kind=kind):
                conn, _, memory = self.connect(**{kind: failing})
                result = memory.stop_reference({'key': 'failure', 'source_ref': ref}, session_id='control')
                self.assertEqual(result.error.code.value, 'unavailable')
                self.assertNotIn('PRIVATE_FAILURE_PAYLOAD', str(result))
                self.assertFalse(conn.in_transaction)
                self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.memory.stop_reference({'key': 'failure', 'source_ref': ref}, session_id='control').ok)

    def test_stop_first_commits_before_intake_and_intake_first_is_invalidated(self):
        ref = self.record()
        conn2, intake2, mem2 = self.connect()
        request = copy.deepcopy(self.example['intake_template'])
        request['origin_record_ref'] = ref
        observed = []
        real_append = self.intake.append_event
        def gate_event(conn, event):
            result = real_append(conn, event)
            if event['text'] == 'source use stopped':
                observed.append(intake2.create(request, request_scope=self.grant).error.code.value)
                self.assertTrue(mem2.read({'ref': ref}, purpose='model_context').ok)
            return result
        memory = MemoryStore(self.conn, sanitize_text=sanitize, append_event=gate_event,
                             invalidate_by_refs=self.intake.invalidate_by_refs)
        self.assertTrue(memory.stop_reference({'key': 'first', 'source_ref': ref}, session_id='s').ok)
        self.assertEqual(observed, ['unavailable'])
        self.assertEqual(intake2.create(request, request_scope=self.grant).error.code.value, 'denied')
        ref2 = self.record('second', '第二の入力')
        first_attempt = []
        def intake_gate(conn, refs):
            first_attempt.append(mem2.stop_reference({'key': 'after', 'source_ref': ref2}, session_id='s').error.code.value)
            return self.memory.source_gate(conn, refs)
        intake = IntakeStore(self.conn, host_grant=self.grant, expert_id='expert', source_gate=intake_gate)
        second = copy.deepcopy(request)
        second.update(key='second', origin_record_ref=ref2)
        accepted = intake.create(second, request_scope=self.grant)
        self.assertTrue(accepted.ok)
        self.assertEqual(first_attempt, ['unavailable'])
        self.assertTrue(mem2.stop_reference({'key': 'after', 'source_ref': ref2}, session_id='s').ok)
        old = accepted.value.to_json()['work_ref']
        self.assertEqual(intake.get_work({'goal_id': old['goal_id']}).value.to_json()['work_ref'], dict(old, epoch=1))


if __name__ == '__main__':
    unittest.main()
