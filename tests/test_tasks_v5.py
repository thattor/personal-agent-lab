"""TSK02 owner tests: durable rights, finite budgets and transaction boundaries."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from pal.contracts_v5 import Grant, Limits, Ref, dumps
from pal.tasks_v5 import TaskStore
from pal.memory_v5 import MemoryStore


def intake(key='create', origin='origin'):
    return {'key': key, 'session_id': 'session', 'origin_record_ref': {'kind': 'record', 'id': origin},
            'brief': {'purpose': 'test', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                      'constraints': [], 'conditions': [{'description': 'useful', 'check': 'semantic'}], 'context_refs': []}}


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.sqlite'
        self.conn = self.connect()
        self.conn.execute('CREATE TABLE test_sources(id TEXT PRIMARY KEY,status TEXT)')
        self.conn.executemany('INSERT INTO test_sources VALUES (?,?)', [('origin', 'available'), ('extra', 'available')])
        self.grant = Grant(('read',), ('repo',), Limits(0, 10, 10))
        self.host = Limits(0, 20, 20)
        self.store = self.make_store()
        self.serial = 0

    def connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(conn.close)
        return conn

    def gate(self, conn, refs):
        self.assertTrue(conn.in_transaction)
        self.assertIs(type(refs), tuple)
        for ref in refs:
            row = conn.execute('SELECT status FROM test_sources WHERE id=?', (ref.id,)).fetchone()
            if row is None:
                return 'not_found'
            if row[0] != 'available':
                return row[0]
        return 'available'

    def make_store(self, conn=None, **kwargs):
        options = dict(host_limits=self.host, host_grant=self.grant, expert_id='expert', source_gate=self.gate)
        options.update(kwargs)
        return TaskStore(conn or self.conn, **options)

    def key(self):
        self.serial += 1
        return str(self.serial)

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.to_json()['value']

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        self.assertLess(len(result.error.message), 100)
        self.assertEqual(result.error.refs, ())
        self.assertNotIn('SECRET', dumps(result))
        return result

    def create(self, **kwargs):
        return self.value(self.store.create(intake(**kwargs), request_scope=self.grant))['work_ref']

    def claim(self, runner='runner'):
        return self.value(self.store.claim({'runner_id': runner}))

    def start(self):
        self.create()
        return self.claim()

    def reserve(self, claim, **kwargs):
        data = dict(key=self.key(), work_ref=claim['work_ref'], kind='model', role='expert')
        data.update(kwargs)
        return self.store.reserve_budget(data)

    def admit_request(self, claim, refs=None, reservation=None):
        context = self.value(self.store.get_execution_context({'lease_id': claim['lease_id'], 'work_ref': claim['work_ref']}))
        reservation = reservation or self.value(self.reserve(claim))['reservation_id']
        return {'call_id': dumps(['C15.call', claim['lease_id'], context['next_step_index']]),
                'lease_id': claim['lease_id'], 'work_ref': claim['work_ref'], 'reservation_id': reservation,
                'source_refs': context['required_refs'] if refs is None else refs}

    def returned(self, claim, refs=None):
        request = self.admit_request(claim, refs)
        self.value(self.store.admit_call(request))
        self.value(self.store.end_call({'call_id': request['call_id'], 'outcome': 'returned'}))
        return request

    def begin(self, claim, action=None):
        return self.store.begin_step({'key': self.key(), 'work_ref': claim['work_ref'],
                                     'action': action or {'kind': 'report', 'summary': 'a summary'}})

    def finish(self, claim, step, **kwargs):
        data = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': []}
        data.update(kwargs)
        return self.store.finish_step(data)

    def release(self, claim, outcome='yield', **kwargs):
        data = {'lease_id': claim['lease_id'], 'work_ref': claim['work_ref'], 'outcome': outcome, 'reason': 'done'}
        data.update(kwargs)
        return self.store.release(data)

    def control(self, claim, command, **kwargs):
        data = {'key': self.key(), 'work_ref': claim['work_ref'], 'command': command}
        data.update(kwargs)
        return self.store.control(data)

    def snapshot(self):
        tables = [row[0] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'v5_%' ORDER BY name")]
        return {table: self.conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall() for table in tables}

    def invalidate(self, refs=None, key=None):
        return self.store.invalidate_by_refs(self.conn, key=key or self.key(), session_id='other',
             refs=tuple(Ref.from_json(ref) for ref in (refs or [{'kind': 'record', 'id': 'origin'}])))

    def test_real_memory_stop_callback_signature_and_atomic_work_invalidation(self):
        memory = MemoryStore(self.conn, sanitize_text=lambda text: text,
                             append_event=self.store.append_event,
                             invalidate_by_refs=self.store.invalidate_by_refs)
        record = self.value(memory.append({'client_key': 'actual', 'session_id': 'actual-session',
                                          'role': 'user', 'text': 'original content'}))['record_ref']
        self.store._source_gate = memory.source_gate
        request = intake()
        request['origin_record_ref'] = record
        self.value(self.store.create(request, request_scope=self.grant))
        claim = self.claim()
        call = self.returned(claim)
        stopped = self.value(memory.stop_reference({'key': 'actual-stop', 'source_ref': record}, session_id='stop-session'))
        self.error(self.begin(claim), 'stale')
        self.assertEqual(self.value(self.release(claim))['state'], 'queued')
        reclaimed = self.claim('another-runner')
        self.error(self.store.register_sources({'work_ref': reclaimed['work_ref'], 'refs': [record]}), 'denied')
        self.assertEqual(self.value(self.release(reclaimed, 'failed'))['state'], 'failed')
        self.assertEqual(self.value(memory.stop_reference({'key': 'actual-stop', 'source_ref': record}, session_id='stop-session')), stopped)
        self.assertFalse(self.conn.in_transaction)

    def test_compose_save_authorization_is_read_only_and_keeps_all_call_sources(self):
        self.store = self.make_store(artifact_inspect=lambda *args: self.fail('unused inspector'))
        claim = self.start()
        all_refs = [{'kind': 'record', 'id': 'origin'}, {'kind': 'record', 'id': 'extra'}]
        self.value(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': all_refs}))
        self.returned(claim, all_refs)
        action = {'kind': 'compose', 'content': '本文\n', 'media_type': 'text/markdown',
                  'source_refs': [all_refs[0]]}
        step = self.value(self.begin(claim, action))
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'action': action}
        with self.assertRaises(ValueError):
            self.store.authorize_artifact_save(self.conn, request)
        other = self.connect()
        other.execute('BEGIN')
        try:
            with self.assertRaises(ValueError):
                self.store.authorize_artifact_save(other, request)
        finally:
            other.rollback()
        before = self.snapshot()
        self.conn.execute('BEGIN IMMEDIATE')
        changes = self.conn.total_changes
        try:
            self.assertEqual(self.value(self.store.authorize_artifact_save(self.conn, request)),
                             {'source_refs': all_refs})
            self.assertTrue(self.conn.in_transaction)
            self.assertEqual(changes, self.conn.total_changes)
            changed = copy.deepcopy(request)
            changed['action']['content'] = 'changed'
            self.error(self.store.authorize_artifact_save(self.conn, changed), 'conflict')
            for field, value in [('content', 1), ('media_type', False), ('media_type', 'application/json')]:
                malformed = copy.deepcopy(request)
                malformed['action'][field] = value
                self.error(self.store.authorize_artifact_save(self.conn, malformed), 'invalid_input')
            changed = copy.deepcopy(request)
            changed['action']['source_refs'] = [{'kind': 'record', 'id': 'never supplied'}]
            self.error(self.store.authorize_artifact_save(self.conn, changed), 'denied')
            self.error(self.store.authorize_artifact_save(self.conn, {**request, 'extra': 1}), 'invalid_input')
        finally:
            self.conn.rollback()
        self.assertEqual(before, self.snapshot())
        self.error(self.finish(claim, step), 'invalid_input')
        self.error(self.release(claim), 'conflict')
        self.assertEqual(self.value(self.store.get_work({'goal_id': claim['work_ref']['goal_id']}))[
            'current_artifact_refs'], [])
        self.value(self.control(claim, 'pause'))
        self.conn.execute('BEGIN')
        try:
            self.error(self.store.authorize_artifact_save(self.conn, request), 'conflict')
        finally:
            self.conn.rollback()
        self.assertEqual(self.value(self.release(claim))['state'], 'paused')

    def test_compose_save_authority_denies_stopped_inputs_and_corrupt_call_metadata(self):
        self.store = self.make_store(artifact_inspect=lambda *args: self.fail('unused inspector'))
        claim = self.start()
        call = self.returned(claim)
        action = {'kind': 'compose', 'content': '', 'media_type': 'text/plain', 'source_refs': []}
        step = self.value(self.begin(claim, action))
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'action': action}
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
            self.error(self.store.authorize_artifact_save(self.conn, request), 'denied')
        finally:
            self.conn.rollback()
        for column, value in [('sources', '{}'), ('sources', '[]'), ('work', '{}')]:
            self.conn.execute('BEGIN IMMEDIATE')
            try:
                self.conn.execute('UPDATE v5_tsk_call SET ' + column + '=? WHERE id=?',
                                  (value, call['call_id']))
                self.error(self.store.authorize_artifact_save(self.conn, request), 'unavailable')
            finally:
                self.conn.rollback()
        for field, value in [('index', False), ('index', -1), ('status', 'unknown'),
                             ('result_refs', {}), ('error', 1)]:
            malformed = copy.deepcopy(step)
            malformed[field] = value
            self.conn.execute('BEGIN IMMEDIATE')
            try:
                self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?',
                                  (dumps(malformed), step['step_id']))
                self.error(self.store.authorize_artifact_save(self.conn, request), 'unavailable')
            finally:
                self.conn.rollback()
        self.value(self.control(claim, 'cancel'))
        self.conn.execute('BEGIN')
        try:
            self.error(self.store.authorize_artifact_save(self.conn, request), 'stale')
        finally:
            self.conn.rollback()

    def test_empty_claim_and_strict_inputs(self):
        self.assertEqual(self.claim(), {'status': 'empty'})
        for request in ({}, {'runner_id': ''}, {'runner_id': True}, {'runner_id': '\ud800'}, {'runner_id': 'r', 'extra': 1}, []):
            with self.subTest(request=repr(request)):
                self.error(self.store.claim(request), 'invalid_input')
        claim = self.start()
        for epoch in (True, -1, 2**63, 1.0):
            bad = dict(claim['work_ref'], epoch=epoch)
            self.error(self.store.get_execution_context({'lease_id': claim['lease_id'], 'work_ref': bad}), 'invalid_input')
        self.assertFalse(self.conn.in_transaction)

    def test_claim_oldest_retry_occupied_reopen(self):
        first = self.create()
        self.create(key='second')
        claim = self.claim()
        self.assertEqual(claim['work_ref']['goal_id'], first['goal_id'])
        self.assertEqual(claim['work_ref']['epoch'], 1)
        self.assertEqual(set(claim), {'lease_id', 'work_ref', 'brief', 'grant', 'checkpoint', 'steps', 'pending_inputs'})
        self.assertEqual(claim['checkpoint'], {'last_finished_index': -1, 'open_question_refs': []})
        before = self.snapshot()
        self.assertEqual(self.claim(), claim)
        self.assertEqual(before, self.snapshot())
        self.error(self.store.claim({'runner_id': 'other'}), 'conflict')
        reopened = self.make_store(self.connect())
        self.error(reopened.claim({'runner_id': 'new-process'}), 'conflict')

    def test_report_roundtrip_replays_next_call_and_checkpoint(self):
        claim = self.start()
        call = self.returned(claim)
        request = {'key': 'step', 'work_ref': claim['work_ref'], 'action': {'kind': 'report', 'summary': 'hello'}}
        step = self.value(self.store.begin_step(request))
        self.assertEqual(step['index'], 0)
        self.assertEqual(set(step), {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'})
        before = self.snapshot()
        self.assertEqual(self.value(self.store.begin_step(request)), step)
        self.assertEqual(before, self.snapshot())
        self.error(self.begin(claim), 'conflict')
        finished = self.value(self.finish(claim, step))
        self.assertEqual(finished['status'], 'finished')
        self.assertEqual(self.conn.execute("SELECT text FROM v5_intake_event WHERE kind='progress'").fetchone()[0], 'hello')
        before = self.snapshot()
        self.assertEqual(self.value(self.finish(claim, step)), finished)
        self.assertEqual(before, self.snapshot())
        current = self.claim()
        self.assertEqual(current['checkpoint']['last_finished_index'], 0)
        context = self.value(self.store.get_execution_context({'lease_id': claim['lease_id'], 'work_ref': claim['work_ref']}))
        self.assertEqual(context['next_step_index'], 1)
        self.assertEqual(context['step_sources'], [{'step_id': step['step_id'], 'refs': call['source_refs']}])
        second = self.returned(claim)
        self.assertNotEqual(call['call_id'], second['call_id'])
        step2 = self.value(self.begin(claim))
        self.value(self.finish(claim, step2))
        released = self.value(self.release(claim))
        self.assertEqual(released['state'], 'queued')
        self.assertEqual(self.value(self.release(claim)), released)
        self.error(self.release(claim, reason='different'), 'conflict')
        self.assertEqual(self.claim('next')['work_ref']['epoch'], 2)

    def test_returned_or_started_output_cannot_be_silently_yielded(self):
        claim = self.start()
        self.returned(claim)
        self.error(self.release(claim), 'conflict')
        step = self.value(self.begin(claim))
        self.error(self.release(claim), 'conflict')
        request = self.admit_request(claim)
        self.error(self.store.admit_call(request), 'conflict')
        self.assertEqual(self.value(self.release(claim, 'failed'))['state'], 'failed')
        saved = self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (step['step_id'],)).fetchone()[0]
        self.assertIn('abandoned', saved)

    def test_admission_replay_is_historical_end_call_is_canonical(self):
        claim = self.start()
        request = self.admit_request(claim)
        admitted = self.value(self.store.admit_call(request))
        self.assertTrue(self.value(self.store.get_call({'call_id': request['call_id']}))['may_enter'])
        self.value(self.control(claim, 'cancel'))
        self.assertFalse(self.value(self.store.get_call({'call_id': request['call_id']}))['may_enter'])
        before = self.snapshot()
        self.assertEqual(self.value(self.store.admit_call(request)), admitted)
        self.assertEqual(before, self.snapshot())
        self.error(self.release(claim), 'conflict')
        end = {'call_id': request['call_id'], 'outcome': 'not_entered'}
        receipt = self.value(self.store.end_call(end))
        self.assertEqual(self.value(self.store.end_call(end)), receipt)
        self.error(self.store.end_call(dict(end, outcome='returned')), 'conflict')
        self.assertEqual(self.value(self.release(claim))['state'], 'cancelled')

    def test_pause_fences_while_retaining_lease_until_actual_end(self):
        claim = self.start()
        call = self.admit_request(claim)
        self.value(self.store.admit_call(call))
        paused = self.value(self.control(claim, 'pause'))
        self.assertEqual(paused['work_ref'], claim['work_ref'])
        self.assertEqual(paused['control_status'], 'pause_requested')
        self.error(self.release(claim, 'paused'), 'conflict')
        self.error(self.store.claim({'runner_id': 'next'}), 'conflict')
        self.value(self.store.end_call({'call_id': call['call_id'], 'outcome': 'returned'}))
        self.error(self.begin(claim), 'conflict')
        self.assertEqual(self.value(self.release(claim))['state'], 'paused')
        self.assertEqual(self.value(self.control(claim, 'resume'))['state'], 'queued')

    def test_old_owned_epoch_release_and_wrong_lease(self):
        claim = self.start()
        self.error(self.release(claim, lease_id='missing'), 'not_found')
        wrong = dict(claim['work_ref'], goal_id='another')
        self.error(self.release(claim, work_ref=wrong), 'stale')
        self.value(self.control(claim, 'cancel'))
        ancient = dict(claim['work_ref'], epoch=54321)
        self.assertEqual(self.value(self.release(claim, work_ref=ancient))['state'], 'cancelled')
        self.error(self.release(claim, work_ref=ancient, reason='changed'), 'conflict')

    def test_control_ignores_old_epoch_but_checks_revision_and_dedupes(self):
        work = self.create()
        claim = self.claim()
        request = {'key': 'p', 'work_ref': work, 'command': 'pause'}
        paused = self.value(self.store.control(request))
        before = self.snapshot()
        self.assertEqual(self.value(self.store.control(request)), paused)
        self.assertEqual(before, self.snapshot())
        events = len(before['v5_intake_event'])
        self.value(self.control(claim, 'pause'))
        self.assertEqual(len(self.snapshot()['v5_intake_event']), events)
        self.error(self.control(claim, 'resume'), 'conflict')
        self.error(self.control(claim, 'cancel', work_ref=dict(work, revision=2)), 'stale')
        self.value(self.control(claim, 'cancel'))
        self.error(self.control(claim, 'pause'), 'conflict')
        self.error(self.control(claim, 'resume'), 'conflict')

    def test_queued_pause_resume_cancel_and_terminal_failure(self):
        work = self.create()
        claim = {'work_ref': work}
        self.assertEqual(self.value(self.control(claim, 'pause'))['state'], 'paused')
        self.assertEqual(self.claim(), {'status': 'empty'})
        self.assertEqual(self.value(self.control(claim, 'resume'))['state'], 'queued')
        claimed = self.claim()
        self.assertEqual(self.value(self.release(claimed, 'failed'))['state'], 'failed')
        self.error(self.control(claimed, 'cancel'), 'conflict')

    def test_zero_host_budgets_leave_work_unclaimed(self):
        self.create()
        for limits in (Limits(0, 0, 2), Limits(0, 2, 0)):
            self.store = self.make_store(host_limits=limits)
            before = self.snapshot()
            self.error(self.store.claim({'runner_id': 'runner'}), 'limit')
            self.assertEqual(before, self.snapshot())

    def test_last_model_unit_admits_and_step_headroom_blocks_before_debit(self):
        self.store = self.make_store(host_limits=Limits(0, 1, 1))
        claim = self.start()
        reserved = self.value(self.reserve(claim))
        self.assertEqual(reserved['remaining']['host'], 0)
        request = self.admit_request(claim, reservation=reserved['reservation_id'])
        self.value(self.store.admit_call(request))
        self.value(self.store.end_call({'call_id': request['call_id'], 'outcome': 'returned'}))
        step = self.value(self.begin(claim))
        self.value(self.finish(claim, step))
        self.store = self.make_store(host_limits=Limits(0, 1, 9))
        before = self.snapshot()
        self.error(self.reserve(claim), 'limit')
        self.assertEqual(before, self.snapshot())

    def test_work_budget_and_host_counts_survive_release_reopen_and_limit_changes(self):
        self.grant = Grant(('read',), ('repo',), Limits(0, 1, 1))
        self.store = self.make_store()
        claim = self.start()
        self.returned(claim)
        step = self.value(self.begin(claim))
        self.value(self.finish(claim, step))
        self.value(self.release(claim))
        self.store = self.make_store(self.connect(), host_limits=Limits(0, 30, 30))
        next_claim = self.claim('next')
        self.error(self.reserve(next_claim), 'limit')
        context = self.value(self.store.get_execution_context({'lease_id': next_claim['lease_id'], 'work_ref': next_claim['work_ref']}))
        self.assertEqual(context['remaining_budget'], {'model': {'work': 0, 'host': 29}, 'step': {'work': 0, 'host': 29}})

    def test_reservation_binding_wrong_kind_epoch_index_and_replay(self):
        claim = self.start()
        key = 'reserve'
        reserved = self.value(self.reserve(claim, key=key))
        self.assertEqual(self.value(self.reserve(claim, key=key)), reserved)
        self.error(self.reserve(claim, key=key, kind='step', role=None), 'conflict')
        request = self.admit_request(claim, reservation=reserved['reservation_id'])
        self.value(self.store.consume({'reservation_id': reserved['reservation_id'], 'call_or_operation_id': request['call_id']}))
        self.error(self.store.consume({'reservation_id': reserved['reservation_id'], 'call_or_operation_id': 'other'}), 'conflict')
        wrong = self.value(self.reserve(claim, kind='step', role=None))['reservation_id']
        self.error(self.store.admit_call(dict(request, reservation_id=wrong)), 'conflict')
        self.value(self.store.admit_call(request))
        self.value(self.store.end_call({'call_id': request['call_id'], 'outcome': 'returned'}))
        step = self.value(self.begin(claim))
        self.value(self.finish(claim, step))
        next_request = self.admit_request(claim, reservation=reserved['reservation_id'])
        self.error(self.store.admit_call(next_request), 'conflict')

    def test_reservation_from_old_lease_never_authorizes_new_epoch(self):
        claim = self.start()
        reservation = self.value(self.reserve(claim))['reservation_id']
        self.value(self.release(claim))
        next_claim = self.claim('next')
        self.error(self.store.admit_call(self.admit_request(next_claim, reservation=reservation)), 'conflict')

    def test_required_supplied_registered_membership_and_live_gate(self):
        claim = self.start()
        request = self.admit_request(claim)
        self.error(self.store.admit_call(dict(request, source_refs=[])), 'denied')
        extra = {'kind': 'record', 'id': 'extra'}
        self.error(self.store.admit_call(dict(request, source_refs=request['source_refs'] + [extra])), 'denied')
        self.value(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': [extra]}))
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
        self.error(self.store.admit_call(request), 'denied')
        self.assertEqual(self.value(self.release(claim, 'failed'))['state'], 'failed')

    def test_lookup_exclusions_truncation_and_provenance_without_copied_body(self):
        claim = self.start()
        self.returned(claim)
        step = self.value(self.begin(claim, {'kind': 'lookup', 'query': 'query'}))
        missing = Ref('record', 'missing')
        read_excluded = Ref('record', 'excluded-during-read')
        extra = Ref('record', 'extra')
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': [extra.to_json(), missing.to_json()]}
        result = self.value(self.store.finish_step(request, truncated=True, excluded_refs=(read_excluded,)))
        self.assertEqual(result['result_refs'], [extra.to_json()])
        self.assertNotIn('truncated', result)
        self.assertEqual(self.value(self.store.finish_step(request, truncated=True, excluded_refs=(read_excluded,))), result)
        self.error(self.store.finish_step(request), 'conflict')
        checkpoint = self.claim()['checkpoint']
        self.assertTrue(checkpoint['lookup_truncated'])
        self.assertEqual(checkpoint['lookup_excluded_refs'], [read_excluded.to_json(), missing.to_json()])
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='extra'")
        context = self.value(self.store.get_execution_context({'work_ref': claim['work_ref'], 'lease_id': claim['lease_id']}))
        self.assertEqual(context['optional_refs'], [extra.to_json()])
        self.assertEqual(context['step_sources'][0]['refs'], [{'kind': 'record', 'id': 'origin'}, extra.to_json()])
        self.returned(claim)  # stopped optional ref is omitted, not blanket-gated

    def test_missing_step_provenance_fails_closed(self):
        claim = self.start()
        call = self.returned(claim)
        step = self.value(self.begin(claim))
        self.value(self.finish(claim, step))
        self.conn.execute('DELETE FROM v5_tsk_call WHERE id=?', (call['call_id'],))
        self.error(self.store.get_execution_context({'work_ref': claim['work_ref'], 'lease_id': claim['lease_id']}), 'unavailable')

    def test_lookup_unavailable_rolls_back_all_results_and_event(self):
        claim = self.start()
        self.returned(claim)
        step = self.value(self.begin(claim, {'kind': 'lookup', 'query': ''}))
        self.conn.execute("INSERT INTO test_sources VALUES ('broken','unavailable')")
        before = self.snapshot()
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': [{'kind': 'record', 'id': name} for name in ('extra', 'broken')]}
        self.error(self.store.finish_step(request), 'unavailable')
        self.assertEqual(before, self.snapshot())

    def test_current_sources_are_rechecked_before_begin_and_finish(self):
        claim = self.start()
        self.returned(claim)
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
        self.error(self.begin(claim), 'denied')
        self.conn.execute("UPDATE test_sources SET status='available' WHERE id='origin'")
        step = self.value(self.begin(claim))
        self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
        self.error(self.finish(claim, step), 'denied')

    def test_source_stop_pause_cancel_precedence_and_clear_drain(self):
        for command in (None, 'pause', 'cancel'):
            with self.subTest(command=command):
                self.create(key=self.key())
                claim = self.claim(self.key())
                call = self.admit_request(claim)
                self.value(self.store.admit_call(call))
                self.conn.execute('BEGIN IMMEDIATE')
                self.value(self.invalidate())
                self.conn.execute('COMMIT')
                if command:
                    self.value(self.control(claim, command))
                self.error(self.begin(claim), 'stale')
                self.error(self.release(claim), 'conflict')
                self.value(self.store.end_call({'call_id': call['call_id'], 'outcome': 'returned'}))
                result = self.value(self.release(claim))
                self.assertEqual(result['state'], {'pause': 'paused', 'cancel': 'cancelled', None: 'queued'}[command])
                flags = self.conn.execute('SELECT pause,drain FROM v5_tsk_control WHERE goal=?', (claim['work_ref']['goal_id'],)).fetchone()
                self.assertEqual(flags, (0, 0))
                if command is None:
                    next_claim = self.claim(self.key())
                    self.conn.execute("UPDATE test_sources SET status='denied' WHERE id='origin'")
                    self.error(self.store.register_sources({'work_ref': next_claim['work_ref'], 'refs': [{'kind': 'record', 'id': 'origin'}]}), 'denied')
                    self.assertEqual(self.value(self.release(next_claim, 'failed'))['state'], 'failed')
                    self.conn.execute("UPDATE test_sources SET status='available' WHERE id='origin'")

    def test_pause_then_source_stop_retains_pause(self):
        claim = self.start()
        self.value(self.control(claim, 'pause'))
        self.conn.execute('BEGIN IMMEDIATE')
        self.value(self.invalidate())
        self.conn.execute('COMMIT')
        self.assertEqual(self.value(self.release(claim))['state'], 'paused')

    def test_mixed_invalidation_prechecks_coverage_states_and_routes_sessions(self):
        first = self.create()
        running = self.claim()
        second = self.create(key='two')
        third = self.create(key='three')
        self.value(self.control({'work_ref': third}, 'pause'))
        fourth = self.create(key='four')
        self.value(self.control({'work_ref': fourth}, 'cancel'))
        self.conn.execute("UPDATE v5_intake_work SET session_id='other-session' WHERE goal_id=?", (second['goal_id'],))
        before = self.snapshot()
        self.conn.execute('BEGIN IMMEDIATE')
        result = self.value(self.invalidate(key='stop'))
        self.assertEqual(len(result['work_refs']), 3)
        self.conn.execute('ROLLBACK')
        self.assertEqual(before, self.snapshot())
        self.conn.execute("UPDATE v5_intake_work SET state='completed' WHERE goal_id=?", (third['goal_id'],))
        before = self.snapshot()
        self.conn.execute('BEGIN IMMEDIATE')
        completed_stop = self.value(self.invalidate())
        self.assertEqual({work['goal_id'] for work in completed_stop['work_refs']},
                         {first['goal_id'], second['goal_id']})
        self.assertEqual(self.conn.execute('SELECT state,epoch FROM v5_intake_work WHERE goal_id=?',
                                          (third['goal_id'],)).fetchone(), ('completed', third['epoch']))
        notices = self.conn.execute("SELECT session_id,refs_json FROM v5_intake_event WHERE text=?",
            ('a source registered for this completed work was stopped; completion is historical',)).fetchall()
        self.assertEqual(notices, [('session', dumps([{'kind': 'record', 'id': 'origin'}]))])
        self.conn.execute('ROLLBACK')
        self.assertEqual(before, self.snapshot())
        self.conn.execute("UPDATE v5_intake_work SET state='paused' WHERE goal_id=?", (third['goal_id'],))
        self.conn.execute('BEGIN IMMEDIATE')
        receipt = self.value(self.invalidate(key='stop'))
        self.conn.execute('COMMIT')
        self.conn.execute('BEGIN IMMEDIATE')
        before = self.snapshot()
        self.assertEqual(self.value(self.invalidate(key='stop')), receipt)
        self.assertEqual(before, self.snapshot())
        self.conn.execute('COMMIT')
        session = self.conn.execute("SELECT session_id FROM v5_intake_event WHERE text='work sources invalidated' AND work_ref_json LIKE ?", ('%' + second['goal_id'] + '%',)).fetchone()[0]
        self.assertEqual(session, 'other-session')
        self.conn.execute('DELETE FROM v5_intake_source WHERE goal_id=?', (first['goal_id'],))
        self.conn.execute('BEGIN IMMEDIATE')
        self.error(self.invalidate(), 'unavailable')
        self.conn.execute('ROLLBACK')

    def test_event_failure_rolls_back_claim_control_finish_release_and_invalidation(self):
        self.create()
        with patch.object(self.store, '_append_event', side_effect=RuntimeError('SECRET')):
            before = self.snapshot()
            self.error(self.store.claim({'runner_id': 'r'}), 'unavailable')
            self.assertEqual(before, self.snapshot())
        claim = self.claim()
        self.returned(claim)
        step = self.value(self.begin(claim))
        with patch.object(self.store, '_append_event', side_effect=RuntimeError('SECRET')):
            for operation in (lambda: self.control(claim, 'cancel'), lambda: self.finish(claim, step), lambda: self.release(claim, 'failed')):
                before = self.snapshot()
                self.error(operation(), 'unavailable')
                self.assertEqual(before, self.snapshot())
            before = self.snapshot()
            self.conn.execute('BEGIN IMMEDIATE')
            self.error(self.invalidate(), 'unavailable')
            self.conn.execute('ROLLBACK')
            self.assertEqual(before, self.snapshot())

    def test_reservation_and_step_insert_failure_roll_back_debit(self):
        claim = self.start()
        self.conn.execute("CREATE TRIGGER fail_res BEFORE INSERT ON v5_tsk_reservation BEGIN SELECT RAISE(ABORT,'SECRET'); END")
        before = self.snapshot()
        self.error(self.reserve(claim), 'unavailable')
        self.assertEqual(before, self.snapshot())
        self.conn.execute('DROP TRIGGER fail_res')
        self.returned(claim)
        self.conn.execute("CREATE TRIGGER fail_step BEFORE INSERT ON v5_tsk_step BEGIN SELECT RAISE(ABORT,'SECRET'); END")
        before = self.snapshot()
        self.error(self.begin(claim), 'unavailable')
        self.assertEqual(before, self.snapshot())

    def test_source_gate_errors_do_not_leak_or_commit_mutations(self):
        claim = self.start()
        for gate in (lambda *_: {'message': 'SECRET'}, lambda *_: (_ for _ in ()).throw(RuntimeError('SECRET'))):
            with patch.object(self.store, '_source_gate', gate):
                before = self.snapshot()
                self.error(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': []}), 'unavailable')
                self.assertEqual(before, self.snapshot())
        def writes(conn, refs):
            conn.execute("UPDATE test_sources SET status='denied'")
            return 'available'
        with patch.object(self.store, '_source_gate', writes):
            self.error(self.store.register_sources({'work_ref': claim['work_ref'], 'refs': []}), 'unavailable')
        self.assertEqual(self.conn.execute("SELECT status FROM test_sources WHERE id='origin'").fetchone()[0], 'available')

    def test_busy_locking_and_idle_connection_requirements(self):
        self.create()
        other = self.connect()
        other.execute('BEGIN IMMEDIATE')
        before = self.snapshot()
        self.error(self.store.claim({'runner_id': 'r'}), 'unavailable')
        self.assertEqual(before, self.snapshot())
        other.execute('ROLLBACK')
        self.conn.execute('BEGIN IMMEDIATE')
        self.error(self.store.claim({'runner_id': 'r'}), 'unavailable')
        self.assertTrue(self.conn.in_transaction)
        self.conn.execute('ROLLBACK')
        self.claim()

    def test_raised_calls_require_release_and_do_not_refund(self):
        claim = self.start()
        request = self.admit_request(claim)
        self.value(self.store.admit_call(request))
        self.value(self.store.end_call({'call_id': request['call_id'], 'outcome': 'raised'}))
        self.error(self.begin(claim), 'conflict')
        new = self.admit_request(claim)
        self.error(self.store.admit_call(new), 'conflict')
        self.value(self.release(claim, 'failed'))
        self.assertEqual(self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0], 2)

    def test_model_action_closed_shape_membership_and_unimplemented_action(self):
        claim = self.start()
        self.returned(claim)
        before = self.snapshot()
        for action in ({'kind': 'report', 'summary': 1},
                       {'kind': 'report', 'summary': 'text', 'extra': 1},
                       {'kind': 'lookup', 'query': 'q', 'source_refs': [{'kind': 'record', 'id': 'extra'}]}):
            self.error(self.begin(claim, action), 'invalid_input')
            self.assertEqual(before, self.snapshot())
        self.error(self.begin(claim, {'kind': 'verify', 'artifact_refs': []}), 'unavailable')
        self.assertEqual(before, self.snapshot())
        step = self.value(self.begin(claim))
        request = {'work_ref': claim['work_ref'], 'step_id': step['step_id'], 'result_refs': []}
        self.error(self.store.finish_step(request, truncated=1), 'invalid_input')
        self.error(self.store.finish_step(request, excluded_refs=[]), 'invalid_input')
        self.error(self.store.finish_step(request, excluded_refs=({'kind': 'record', 'id': 'extra'},)), 'invalid_input')
        self.error(self.finish(claim, step, result_refs=[{'kind': 'record', 'id': 'extra'}]), 'invalid_input')
        self.error(self.finish(claim, step, error=False), 'invalid_input')
        self.value(self.finish(claim, step, error='bounded host explanation'))

    def test_cessation_write_failure_keeps_occupancy_and_retry_can_finish(self):
        claim = self.start()
        call = self.admit_request(claim)
        self.value(self.store.admit_call(call))
        self.conn.execute("CREATE TRIGGER fail_end BEFORE UPDATE ON v5_tsk_call BEGIN SELECT RAISE(ABORT,'SECRET'); END")
        before = self.snapshot()
        end = {'call_id': call['call_id'], 'outcome': 'raised'}
        self.error(self.store.end_call(end), 'unavailable')
        self.assertEqual(before, self.snapshot())
        self.error(self.release(claim, 'failed'), 'conflict')
        self.conn.execute('DROP TRIGGER fail_end')
        self.value(self.store.end_call(end))
        self.value(self.release(claim, 'failed'))

    def test_claim_and_reservation_identifier_collisions_roll_back(self):
        self.create()
        self.store._id_factory = lambda prefix: 'same-id'
        self.claim()
        before = self.snapshot()
        # The event identity collides during release, after the state/slot changes.
        claim = self.claim()
        self.error(self.release(claim), 'unavailable')
        self.assertEqual(before, self.snapshot())
        self.value(self.reserve(claim))
        before = self.snapshot()
        self.error(self.reserve(claim), 'unavailable')
        self.assertEqual(before, self.snapshot())

    def test_baseexception_after_claim_writes_rolls_back_and_propagates(self):
        self.create()
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption.__name__):
                before = self.snapshot()
                original = self.store._id_factory
                def interrupt_event(prefix):
                    if prefix == 'event':
                        self.assertTrue(self.conn.in_transaction)
                        self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease').fetchone()[0], 1)
                        raise interruption()
                    return original(prefix)
                try:
                    with patch.object(self.store, '_id_factory', interrupt_event):
                        with self.assertRaises(interruption):
                            self.store.claim({'runner_id': 'interrupted'})
                    self.assertFalse(self.conn.in_transaction)
                    self.assertEqual(before, self.snapshot())
                    other = self.connect()
                    other.execute('BEGIN IMMEDIATE')
                    other.execute('ROLLBACK')
                finally:
                    if self.conn.in_transaction:
                        self.conn.execute('ROLLBACK')
        self.claim()

    def test_baseexception_during_constructor_rolls_back_schema_and_host_setup(self):
        class InterruptConnection(sqlite3.Connection):
            interrupt_prefix = None
            interruption = None

            def execute(connection, sql, parameters=()):
                result = super().execute(sql, parameters)
                if connection.interrupt_prefix and sql.startswith(connection.interrupt_prefix):
                    raise connection.interruption()
                return result

        for index, prefix in enumerate(('CREATE TABLE IF NOT EXISTS v5_tsk_lease',
                                        'INSERT INTO v5_tsk_host')):
            for interruption in (KeyboardInterrupt, SystemExit):
                with self.subTest(prefix=prefix, interruption=interruption.__name__):
                    path = Path(self.temp.name) / f'interruption-{index}-{interruption.__name__}.sqlite'
                    conn = sqlite3.connect(path, isolation_level=None, factory=InterruptConnection)
                    self.addCleanup(conn.close)
                    conn.interrupt_prefix = prefix
                    conn.interruption = interruption
                    try:
                        with self.assertRaises(interruption):
                            self.make_store(conn)
                        self.assertFalse(conn.in_transaction)
                        self.assertEqual(conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'v5_tsk_%'").fetchall(), [])
                        other = sqlite3.connect(path, isolation_level=None, timeout=0)
                        self.addCleanup(other.close)
                        other.execute('BEGIN IMMEDIATE')
                        other.execute('ROLLBACK')
                    finally:
                        if conn.in_transaction:
                            conn.execute('ROLLBACK')

    def test_malformed_public_shapes_are_bounded_and_nonmutating(self):
        claim = self.start()
        methods = [(self.store.reserve_budget, {'key': 'r', 'work_ref': claim['work_ref'], 'kind': 'model', 'role': 'primary'}),
                   (self.store.register_sources, {'work_ref': claim['work_ref'], 'refs': ()}),
                   (self.store.end_call, {'call_id': 'x', 'outcome': 'stopped'}),
                   (self.store.release, {'lease_id': claim['lease_id'], 'work_ref': claim['work_ref'], 'outcome': 'yield', 'reason': False}),
                   (self.store.get_call, {'call_id': 'x', 'extra': None})]
        for method, request in methods:
            before = self.snapshot()
            self.error(method(request), 'invalid_input')
            self.assertEqual(before, self.snapshot())
        self.error(self.store.reserve_budget({'key': 'r', 'kind': 'model', 'role': 'expert'}), 'invalid_input')
        self.error(self.store.reserve_budget({'key': 'r', 'kind': 'operation', 'work_ref': claim['work_ref']}), 'unavailable')
        self.error(self.store.get_call({'call_id': 'unknown'}), 'not_found')
        with self.assertRaises(ValueError):
            self.make_store(host_limits=Limits(0, 2**63, 1))


if __name__ == '__main__':
    unittest.main()
