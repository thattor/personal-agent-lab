"""Frozen CHANGE01 owner acceptance: actual disposable SQLite, no provider."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy
import unittest
from unittest.mock import patch
from pal.contracts_v5 import Grant, Limits, Ref, dumps, loads
import test_tasks_ask_v5 as ask_fixture

MAX = 2**63 - 1


class ChangeTests(unittest.TestCase):
    def setUp(self):
        self.f = ask_fixture.TaskAskTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.t, self.conn = self.f.tasks, self.f.conn
        self.correction = self.f.record('Deterministic trusted-host correction: independent replacement.')
        # The fixture explicitly binds this saved correction to the changed draft;
        # it does not claim natural-language Primary authorization.
        self.draft = {'purpose': 'corrected local draft',
            'target': {'repository': 'repo', 'issue_numbers': [7], 'files': [{'path': 'draft.md', 'ref': 'main'}]},
            'constraints': ['local only'], 'conditions': [
                {'description': 'corrected output', 'check': 'artifact_saved'},
                {'description': 'source retained', 'check': 'source_fetched'}], 'context_refs': []}

    def value(self, result):
        return self.f.value(result)

    def error(self, result, code):
        self.f.error(result, code)
        self.assertEqual(result.error.refs, ())

    def work(self, revision=None):
        request = {'goal_id': self.f.goal}
        if revision is not None:
            request['revision'] = revision
        return self.value(self.t.get_work(request))

    def request(self, *, work=None, origin=None, draft=None, key=None):
        work = work or self.work()['work_ref']
        origin = origin or self.correction
        return {'key': key or dumps(['C10.change', work['goal_id'], work['revision'], origin]),
                'work_ref': copy.deepcopy(work), 'command': {'kind': 'change',
                'brief': copy.deepcopy(draft or self.draft), 'origin_record_ref': copy.deepcopy(origin)}}

    def change(self, **kwargs):
        return self.value(self.t.control(self.request(**kwargs)))

    def control(self, command, work=None):
        return self.t.control({'key': self.f.key(), 'work_ref': work or self.work()['work_ref'], 'command': command})

    def release(self, *, outcome='yield', claim=None):
        claim = claim or self.f.lease
        return self.t.release({'lease_id': claim['lease_id'], 'work_ref': claim['work_ref'],
                               'outcome': outcome, 'reason': 'settle old owned call'})

    def queued(self):
        self.value(self.release())

    def state(self, name):
        if name == 'queued': self.queued()
        elif name == 'waiting_input': self.f.ask()
        elif name == 'paused':
            self.value(self.control('pause')); self.value(self.release())

    def assert_unchanged(self, request, code):
        before = self.f.dump()
        self.error(self.t.control(request), code)
        self.assertEqual(self.f.dump(), before)
        self.assertFalse(self.conn.in_transaction)

    def test_closed_command_and_shared_strict_parsers_do_not_burn_key(self):
        mutations = ('extra_top', 'grant', 'scope', 'limits', 'extra_command', 'nonrecord',
                     'bool_revision', 'negative_epoch', 'extra_brief', 'empty_conditions',
                     'bool_issue', 'invalid_check', 'bad_ref_context', 'bad_utf8')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.setUp(); req = self.request(key='same-valid-key')
                if mutation == 'extra_top': req['authority'] = 'model'
                elif mutation in ('grant', 'scope', 'limits'): req['command'][mutation] = {}
                elif mutation == 'extra_command': req['command']['state'] = 'queued'
                elif mutation == 'nonrecord': req['command']['origin_record_ref']['kind'] = 'artifact'
                elif mutation == 'bool_revision': req['work_ref']['revision'] = True
                elif mutation == 'negative_epoch': req['work_ref']['epoch'] = -1
                elif mutation == 'extra_brief': req['command']['brief']['grant'] = {}
                elif mutation == 'empty_conditions': req['command']['brief']['conditions'] = []
                elif mutation == 'bool_issue': req['command']['brief']['target']['issue_numbers'] = [True]
                elif mutation == 'invalid_check': req['command']['brief']['conditions'][0]['check'] = 'done'
                elif mutation == 'bad_ref_context': req['command']['brief']['context_refs'] = [{'kind': 'invalid-kind', 'id': 'a'}]
                else: req['command']['brief']['purpose'] = '\ud800'
                self.assert_unchanged(req, 'invalid_input')
                self.change(key='same-valid-key')

    def test_all_four_states_preserve_identity_and_empty_new_execution_history(self):
        for state, expected in [('queued', 'queued'), ('waiting_input', 'queued'), ('paused', 'paused'), ('running', 'running')]:
            with self.subTest(state=state):
                self.setUp(); self.state(state)
                old = self.work(); identity = self.conn.execute('SELECT session_id,expert_id FROM v5_intake_work').fetchone()
                usage = self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall()
                out = self.change()
                expected_ref = {**old['work_ref'], 'revision': 2, 'epoch': old['work_ref']['epoch'] + 1}
                self.assertEqual(out, {'work_ref': expected_ref, 'state': expected,
                                      'control_status': 'draining' if state == 'running' else 'none'})
                current, historical = self.work(), self.work(1)
                self.assertEqual(historical['state'], 'superseded')
                self.assertEqual((historical['brief'], historical['grant']), (old['brief'], old['grant']))
                self.assertEqual(current['current_artifact_refs'], [])
                self.assertEqual(current['open_questions'], [])
                self.assertEqual(self.conn.execute('SELECT session_id,expert_id FROM v5_intake_work WHERE revision=2').fetchone(), identity)
                self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall(), usage)
                ids = [c['id'] for c in current['brief']['conditions']]
                self.assertEqual(len(set(ids)), 2)
                self.assertFalse(set(ids) & {c['id'] for c in old['brief']['conditions']})
                projected = copy.deepcopy(current['brief'])
                projected['conditions'] = [{k: v for k, v in c.items() if k != 'id'} for c in projected['conditions']]
                self.assertEqual(projected, self.draft)
                sources = self.conn.execute('SELECT kind,id FROM v5_intake_source WHERE revision=2 ORDER BY rowid').fetchall()
                self.assertEqual(sources, [('record', self.correction['id'])])
                for table in ('v5_tsk_step', 'v5_tsk_artifact_set', 'v5_tsk_question'):
                    self.assertEqual(self.conn.execute('SELECT count(*) FROM ' + table + ' WHERE revision=2').fetchone()[0], 0)
                self.assertEqual(self.conn.execute('SELECT pause,drain FROM v5_tsk_control WHERE revision=1').fetchone(), (0, 0))
                if state == 'running': self.value(self.release())
                if expected == 'paused': self.value(self.control('resume'))
                claim = self.value(self.t.claim({'runner_id': 'new'}))
                self.assertEqual((claim['steps'], claim['pending_inputs']), ([], []))

    def test_one_changed_event_uses_new_workref_origin_and_own_session(self):
        before = self.conn.execute('SELECT count(*) FROM v5_intake_event').fetchone()[0]
        out = self.change()
        rows = self.conn.execute('SELECT session_id,work_ref_json,kind,text,refs_json FROM v5_intake_event ORDER BY rowid').fetchall()
        self.assertEqual(len(rows), before + 1)
        self.assertEqual(rows[-1], ('session', dumps(out['work_ref']), 'state', 'work changed', dumps([self.correction])))

    def test_prior_grant_narrowing_survives_host_widening_and_usage_does_not_reset(self):
        self.f.call([self.f.origin, self.f.extra])
        step = self.value(self.t.begin_step({'key': self.f.key(), 'work_ref': self.f.lease['work_ref'],
                                           'action': {'kind': 'report', 'summary': 'already consumed'}}))
        self.value(self.t.finish_step({'work_ref': self.f.lease['work_ref'], 'step_id': step['step_id'], 'result_refs': []}))
        usage = self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY kind').fetchall()
        host_usage = self.conn.execute('SELECT kind,used FROM v5_tsk_host ORDER BY kind').fetchall()
        self.t._host_grant = Grant((), ('repo',), Limits(0, 0, 1))
        self.change()
        narrow = self.work()['grant']
        self.assertEqual(narrow, {'capabilities': [], 'repositories': ['repo'],
                                 'limits': {'max_operations': 0, 'max_steps': 0, 'max_model_calls': 1}})
        self.t._host_grant = Grant(('read', 'write'), ('repo', 'other'), Limits(10, 100, 100))
        self.change(origin=self.f.record('second independent correction'))
        self.assertEqual(self.work()['grant'], narrow)
        self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_usage ORDER BY kind').fetchall(), usage)
        self.assertEqual(self.conn.execute('SELECT kind,used FROM v5_tsk_host ORDER BY kind').fetchall(), host_usage)
        self.value(self.release())
        claim = self.value(self.t.claim({'runner_id': 'next'}))
        metadata = self.value(self.t.get_execution_context({'lease_id': claim['lease_id'], 'work_ref': claim['work_ref']}))
        self.assertEqual((metadata['remaining_budget']['model']['work'], metadata['remaining_budget']['step']['work']), (0, 0))

    def test_grant_preserves_previous_order_and_intersection_denies_repository(self):
        prior = Grant(('read', 'write'), ('repo', 'other'), Limits(0, 20, 20))
        self.conn.execute('UPDATE v5_intake_work SET grant_json=?', (dumps(prior),))
        self.t._host_grant = Grant(('write', 'read'), ('other', 'repo'), Limits(0, 20, 20))
        self.change()
        self.assertEqual(self.work()['grant'], prior.to_json())
        self.t._host_grant = Grant(('read',), ('other',), Limits(0, 20, 20))
        self.assert_unchanged(self.request(origin=self.f.record('third correction')), 'denied')

    def test_replay_is_original_after_more_change_stop_and_terminal_not_current_state(self):
        req = self.request(); first = self.value(self.t.control(req))
        self.change(origin=self.f.record('new correction'))
        self.f.stop(self.f.origin)
        self.value(self.control('cancel'))
        self.value(self.release())
        before = self.f.dump()
        self.assertEqual(self.value(self.t.control(req)), first)
        self.assertEqual(self.f.dump(), before)
        for mutation in ('epoch', 'brief', 'origin'):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(req)
                if mutation == 'epoch': changed['work_ref']['epoch'] += 1
                elif mutation == 'brief': changed['command']['brief']['purpose'] += ' different'
                else: changed['command']['origin_record_ref'] = self.f.history
                self.assert_unchanged(changed, 'conflict')

    def test_epoch_tolerant_fresh_control_old_revision_stale_and_missing_goal(self):
        req = self.request(); req['work_ref']['epoch'] = 0
        out = self.value(self.t.control(req))
        self.assertEqual(out['work_ref']['revision'], 2)
        self.assert_unchanged({**req, 'key': 'fresh-old'}, 'stale')
        missing = self.request(); missing['work_ref']['goal_id'] = 'absent'
        self.assert_unchanged(missing, 'not_found')

    def test_reused_origin_conflicts_but_same_brief_with_fresh_origin_can_advance(self):
        for origin in (self.f.origin, self.correction):
            with self.subTest(origin=origin):
                if origin == self.correction: self.change()
                self.assert_unchanged(self.request(origin=origin, key=self.f.key()), 'conflict')
        third = self.change(origin=self.f.record('fresh correction same exact draft'))
        self.assertEqual(third['work_ref']['revision'], 3)

    def test_origin_and_condition_freshness_are_goal_local_not_global_registry(self):
        other = self.value(self.t.create({'key': self.f.key(), 'session_id': 'other-session',
            'origin_record_ref': self.correction, 'brief': self.draft}, request_scope=self.f.grant))
        other_brief = self.value(self.t.get_work({'goal_id': other['work_ref']['goal_id']}))['brief']
        allowed_id = other_brief['conditions'][0]['id']
        original = self.t._id_factory
        minted = []
        def factory(prefix):
            if prefix == 'condition' and not minted:
                minted.append(allowed_id); return allowed_id
            return original(prefix)
        self.t._id_factory = factory
        self.change()
        self.assertEqual(self.work()['brief']['conditions'][0]['id'], allowed_id)
        self.assertEqual(self.value(self.t.get_work({'goal_id': other['work_ref']['goal_id']}))['brief'], other_brief)

    def test_terminal_changes_conflict_without_burning_key(self):
        for state in ('completed', 'cancelled', 'failed'):
            with self.subTest(state=state):
                self.setUp()
                self.conn.execute('UPDATE v5_intake_work SET state=?', (state,))
                self.conn.execute('UPDATE v5_tsk_lease SET active=0')
                self.assert_unchanged(self.request(), 'conflict')

    def test_old_questions_are_history_not_transferred_and_original_receipts_replay(self):
        for status in ('open', 'answered', 'closed'):
            with self.subTest(status=status):
                self.setUp(); receipt = self.f.ask(); ask_request = copy.deepcopy(self.f.request)
                answer_request = answer_receipt = None
                if status == 'answered':
                    answer_request = self.f.answer_request(receipt)
                    answer_receipt = self.value(self.t.control(answer_request))
                elif status == 'closed': self.f.stop(self.f.extra)
                before_answer = self.conn.execute('SELECT answer_ref FROM v5_tsk_question').fetchone()[0]
                self.change()
                self.assertEqual(self.conn.execute('SELECT status,answer_ref FROM v5_tsk_question').fetchone(),
                                 ('superseded' if status == 'open' else status, before_answer))
                old = self.work(1)
                self.assertEqual((old['state'], old['open_questions']), ('superseded', []))
                self.assertEqual(self.value(self.t.ask(ask_request)), receipt)
                self.assertEqual(self.value(self.t.get_question_by_key({'key': ask_request['key']})), receipt)
                if answer_request:
                    self.assertEqual(self.value(self.t.control(answer_request)), answer_receipt)
                    self.assert_unchanged({**answer_request, 'key': self.f.key()}, 'stale')
                claim = self.value(self.t.claim({'runner_id': 'replacement'}))
                self.assertEqual((claim['pending_inputs'], claim['steps']), ([], []))

    def test_latest_superseded_and_question_row_corruption_fail_closed(self):
        for mutation in ('latest_superseded', 'missing_question', 'question_text', 'waiting_without_open'):
            with self.subTest(mutation=mutation):
                self.setUp(); self.f.ask()
                if mutation == 'latest_superseded': self.conn.execute("UPDATE v5_intake_work SET state='superseded'")
                elif mutation == 'missing_question': self.conn.execute('DELETE FROM v5_tsk_question')
                elif mutation == 'question_text': self.conn.execute("UPDATE v5_tsk_question SET question='forged'")
                else: self.conn.execute("UPDATE v5_tsk_question SET status='closed'")
                before = self.f.dump()
                self.error(self.t.get_work({'goal_id': self.f.goal}), 'unavailable')
                self.assert_unchanged(self.request(work=self.f.lease['work_ref']), 'unavailable')
                self.assertEqual(self.f.dump(), before)

    def test_source_stop_before_change_depends_on_explicit_new_provenance(self):
        for mode in ('old_only', 'reused', 'new_origin', 'terminal_failed'):
            with self.subTest(mode=mode):
                self.setUp(); self.f.stop(self.f.origin)
                req = self.request()
                if mode == 'reused': req['command']['brief']['context_refs'] = [self.f.origin]
                elif mode == 'new_origin': self.f.stop(self.correction)
                elif mode == 'terminal_failed': self.value(self.release(outcome='failed'))
                if mode in ('reused', 'new_origin'): self.assert_unchanged(req, 'denied')
                elif mode == 'terminal_failed':
                    # drain release queues; actual required-source failure settles
                    # after a fresh claim rather than pretending stop itself failed.
                    claim = self.value(self.t.claim({'runner_id': 'required-denied'}))
                    self.error(self.t.register_sources({'work_ref': claim['work_ref'], 'refs': [self.f.origin]}), 'denied')
                    self.value(self.release(claim=claim, outcome='failed'))
                    self.assert_unchanged(self.request(), 'conflict')
                else: self.assertEqual(self.value(self.t.control(req))['work_ref']['revision'], 2)

    def test_old_only_stop_after_change_is_noop_but_shared_and_new_sources_fence_latest(self):
        draft = copy.deepcopy(self.draft); draft['context_refs'] = [self.f.extra]
        self.change(draft=draft)
        before = self.work()['work_ref']
        self.f.stop(self.f.origin)
        self.assertEqual(self.work()['work_ref'], before)
        self.f.stop(self.f.extra)
        shared = self.work()['work_ref']
        self.assertEqual(shared['epoch'], before['epoch'] + 1)
        self.f.stop(self.correction)
        self.assertEqual(self.work()['work_ref']['epoch'], shared['epoch'] + 1)

    def test_same_transaction_gate_outcomes_are_preserved_without_new_rows_or_key(self):
        for outcome in ('not_found', 'denied', 'unavailable'):
            with self.subTest(outcome=outcome):
                self.setUp(); observations = []
                def gate(connection, refs):
                    observations.append((connection is self.conn, connection.in_transaction, refs))
                    return outcome
                original = self.t._source_gate
                self.t._source_gate = gate
                req = self.request()
                self.assert_unchanged(req, outcome)
                self.assertEqual(observations, [(True, True, (Ref.from_json(self.correction),))])
                self.t._source_gate = original
                self.change()

    def admitted(self):
        work = self.f.lease['work_ref']
        reservation = self.value(self.t.reserve_budget({'key': self.f.key(), 'work_ref': work, 'kind': 'model', 'role': 'expert'}))['reservation_id']
        request = {'call_id': dumps(['C15.call', self.f.lease['lease_id'], 0]), 'lease_id': self.f.lease['lease_id'],
                   'work_ref': work, 'reservation_id': reservation, 'source_refs': [self.f.origin]}
        self.value(self.t.admit_call(request)); return request

    def test_admitted_multichange_latest_pause_stop_and_cancel_win_after_actual_end(self):
        for intent in ('pause', 'cancel', 'none'):
            with self.subTest(intent=intent):
                self.setUp(); call = self.admitted()
                self.change()
                if intent == 'pause': self.value(self.control('pause'))
                second = self.change(origin=self.f.record('second correction'))
                self.f.stop(self.conn_origin(3))
                if intent == 'cancel': self.value(self.control('cancel'))
                before = self.f.dump()
                self.error(self.release(outcome='failed'), 'conflict')
                self.assertEqual(self.f.dump(), before)
                self.value(self.t.end_call({'call_id': call['call_id'], 'outcome': 'returned'}))
                current = self.work()['work_ref']
                out = self.value(self.release(outcome='failed'))
                self.assertEqual(out, {'work_ref': current, 'state': {'pause': 'paused', 'cancel': 'cancelled', 'none': 'queued'}[intent], 'control_status': 'none'})
                self.assertEqual(self.conn.execute('SELECT active FROM v5_tsk_lease').fetchone()[0], 0)
                self.assertEqual(self.conn.execute('SELECT pause,drain FROM v5_tsk_control WHERE revision=3').fetchone(), (0, 0))
                if intent == 'pause': self.assertEqual(second['control_status'], 'pause_requested')

    def conn_origin(self, revision):
        return loads(self.conn.execute('SELECT origin_ref_json FROM v5_intake_work WHERE revision=?', (revision,)).fetchone()[0])

    def test_ended_returned_raised_notentered_old_calls_can_settle_without_step(self):
        for outcome in ('returned', 'raised', 'not_entered'):
            with self.subTest(outcome=outcome):
                self.setUp(); call = self.admitted(); self.change()
                self.value(self.t.end_call({'call_id': call['call_id'], 'outcome': outcome}))
                self.assertEqual(self.value(self.release(outcome='failed'))['state'], 'queued')

    def test_old_started_step_abandoned_release_replay_is_historical_and_strict(self):
        self.f.call([self.f.origin]); old_step = self.value(self.t.begin_step({'key': self.f.key(), 'work_ref': self.f.lease['work_ref'], 'action': {'kind': 'report', 'summary': 'old'}}))
        self.change(); self.change(origin=self.f.record('third revision'))
        request = {'lease_id': self.f.lease['lease_id'], 'work_ref': self.f.lease['work_ref'], 'outcome': 'yield', 'reason': 'settled'}
        out = self.value(self.t.release(request))
        step = loads(self.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?', (old_step['step_id'],)).fetchone()[0])
        self.assertEqual(step['status'], 'abandoned')
        self.change(origin=self.f.record('fourth revision'))
        self.assertEqual(self.value(self.t.release(request)), out)
        before = self.f.dump()
        self.error(self.t.release({**request, 'reason': 'different'}), 'conflict')
        self.assertEqual(self.f.dump(), before)

    def test_release_lease_identity_and_paused_outcome_do_not_guess_authority(self):
        self.change()
        before = self.f.dump()
        self.error(self.release(outcome='paused'), 'conflict')
        for lease_id, work, code in [('missing', self.f.lease['work_ref'], 'not_found'),
                                     (self.f.lease['lease_id'], self.work()['work_ref'], 'stale')]:
            self.error(self.t.release({'lease_id': lease_id, 'work_ref': work, 'outcome': 'yield', 'reason': 'x'}), code)
        self.assertEqual(self.f.dump(), before)

    def test_latest_only_claim_and_retained_claim_never_authorize_old_work(self):
        self.change()
        self.assertEqual(self.value(self.t.claim({'runner_id': 'runner'}))['work_ref']['revision'], 1)
        self.assert_unchanged(self.request(work=self.f.lease['work_ref'], key='old-change'), 'stale')
        self.error(self.t.reserve_budget({'key': self.f.key(), 'work_ref': self.f.lease['work_ref'], 'kind': 'model', 'role': 'expert'}), 'stale')
        self.error(self.t.begin_step({'key': self.f.key(), 'work_ref': self.f.lease['work_ref'], 'action': {'kind': 'report', 'summary': 'no'}}), 'stale')
        self.value(self.release())
        # Even a historical queued row must not be selected ahead of latest.
        self.conn.execute("UPDATE v5_intake_work SET state='queued' WHERE revision=1")
        claimed = self.value(self.t.claim({'runner_id': 'new'}))
        self.assertEqual(claimed['work_ref']['revision'], 2)

    def test_prepared_old_admission_is_stale_and_may_enter_false_after_change(self):
        call = self.admitted(); self.change()
        self.assertFalse(self.value(self.t.get_call({'call_id': call['call_id']}))['may_enter'])
        other = {**call, 'call_id': 'different'}
        self.error(self.t.admit_call(other), 'stale')

    def test_cross_revision_release_rejects_corrupt_call_or_reservation_without_writes(self):
        cases = [('call', 'status', None), ('call', 'status', 'unknown'), ('call', 'idx', -1),
                 ('call', 'idx', MAX + 1), ('call', 'work', dumps({'goal_id': 'foreign', 'revision': 1, 'epoch': 1})),
                 ('call', 'work', dumps({'goal_id': 'g', 'revision': 1, 'epoch': False})),
                 ('call', 'reservation', 'absent'), ('reservation', 'lease', 'foreign'),
                 ('reservation', 'work', dumps({'goal_id': 'foreign', 'revision': 1, 'epoch': 1})),
                 ('reservation', 'idx', -1), ('reservation', 'kind', 'step'),
                 ('reservation', 'role', 'primary'), ('reservation', 'binding', 'another-call')]
        for table, field, value in cases:
            with self.subTest(table=table, field=field, value=value):
                self.setUp(); call = self.admitted()
                self.value(self.t.end_call({'call_id': call['call_id'], 'outcome': 'returned'})); self.change()
                # SQLite cannot bind > signed64 as integer; persist a REAL to test
                # the owner's strict bounded integer check rather than Python bind.
                if field == 'idx' and value == MAX + 1: value = float(value)
                identifier = call['call_id'] if table == 'call' else call['reservation_id']
                self.conn.execute('UPDATE v5_tsk_' + table + ' SET ' + field + '=? WHERE id=?', (value, identifier))
                before = self.f.dump(); self.error(self.release(), 'unavailable')
                self.assertEqual(self.f.dump(), before); self.assertFalse(self.conn.in_transaction)

    def test_step_binding_corruption_and_bool_wire_index_cannot_free_old_slot(self):
        for mutation in ('bool_index', 'negative_index', 'foreign_work', 'future_epoch', 'wrong_id', 'sql_goal', 'sql_index', 'sql_call', 'sql_call_lease', 'result_shape', 'unknown_status', 'error_type'):
            with self.subTest(mutation=mutation):
                self.setUp(); self.f.call([self.f.origin]); step = self.value(self.t.begin_step({'key': self.f.key(), 'work_ref': self.f.lease['work_ref'], 'action': {'kind': 'report', 'summary': 'old'}})); self.change()
                wire = copy.deepcopy(step)
                if mutation == 'bool_index': wire['index'] = False
                elif mutation == 'negative_index': wire['index'] = -1
                elif mutation == 'foreign_work': wire['work_ref']['goal_id'] = 'foreign'
                elif mutation == 'future_epoch': wire['work_ref']['epoch'] += 1
                elif mutation == 'wrong_id': wire['step_id'] = 'foreign'
                elif mutation == 'result_shape': wire['result_refs'] = {}
                elif mutation == 'unknown_status': wire['status'] = 'unknown'
                elif mutation == 'error_type': wire['error'] = 1
                elif mutation == 'sql_call_lease': self.conn.execute("UPDATE v5_tsk_call SET lease='foreign' WHERE step=?", (step['step_id'],))
                else:
                    column, value = {'sql_goal': ('goal', 'foreign'), 'sql_index': ('idx', 2), 'sql_call': ('call', 'foreign')}[mutation]
                    self.conn.execute('UPDATE v5_tsk_step SET ' + column + '=? WHERE id=?', (value, step['step_id']))
                self.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(wire), step['step_id']))
                before = self.f.dump(); self.error(self.release(), 'unavailable')
                self.assertEqual(self.f.dump(), before)

    def test_state_lease_inconsistency_rejects_change_without_writes(self):
        for mutation in ('running_no_lease', 'queued_has_lease', 'unknown_state', 'old_lease_no_drain'):
            with self.subTest(mutation=mutation):
                self.setUp(); target = self.f.lease['work_ref']
                if mutation == 'running_no_lease': self.conn.execute('UPDATE v5_tsk_lease SET active=0')
                elif mutation == 'queued_has_lease': self.conn.execute("UPDATE v5_intake_work SET state='queued'")
                elif mutation == 'unknown_state': self.conn.execute("UPDATE v5_intake_work SET state='unknown'")
                else:
                    target = self.change()['work_ref']; self.conn.execute('UPDATE v5_tsk_control SET drain=0 WHERE revision=2')
                self.assert_unchanged(self.request(work=target, origin=self.f.record('another correction')), 'unavailable')

    def test_revision_and_epoch_overflow_reject_before_mint(self):
        for field in ('revision', 'epoch'):
            with self.subTest(field=field):
                self.setUp(); self.queued()
                self.conn.execute('UPDATE v5_intake_work SET ' + field + '=?', (MAX,))
                if field == 'revision':
                    self.conn.execute('UPDATE v5_intake_source SET revision=?', (MAX,))
                called = []
                original = self.t._id_factory
                self.t._id_factory = lambda prefix: called.append(prefix) or original(prefix)
                self.assert_unchanged(self.request(), 'unavailable')
                self.assertEqual(called, [])

    def test_prewrite_condition_and_event_mints_cannot_lose_or_mutate_owned_transaction(self):
        for prefix in ('condition', 'event'):
            for action in ('COMMIT', 'ROLLBACK', 'COMMIT_BEGIN', 'ROLLBACK_BEGIN', 'WRITE', 'EXCEPTION', 'INTERRUPT'):
                with self.subTest(prefix=prefix, action=action):
                    self.setUp(); before = self.f.dump(); original = self.t._id_factory
                    def mint(kind):
                        if kind == prefix:
                            if action == 'EXCEPTION': raise RuntimeError('private injected failure')
                            if action == 'INTERRUPT': raise KeyboardInterrupt('private injected interrupt')
                            if action == 'WRITE': self.conn.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'")
                            else:
                                self.conn.execute(action.split('_')[0])
                                if action.endswith('_BEGIN'): self.conn.execute('BEGIN IMMEDIATE')
                        return original(kind)
                    self.t._id_factory = mint
                    if action == 'INTERRUPT':
                        with self.assertRaises(KeyboardInterrupt): self.t.control(self.request())
                    else: self.error(self.t.control(self.request()), 'unavailable')
                    self.assertEqual(self.f.dump(), before); self.assertFalse(self.conn.in_transaction)
                    self.t._id_factory = original
                    self.change()

    def test_condition_collisions_with_same_brief_or_prior_goal_history_fail_atomically(self):
        for collision in ('same_new', 'prior', 'old_history'):
            with self.subTest(collision=collision):
                self.setUp(); existing = self.work()['brief']['conditions'][0]['id']; original = self.t._id_factory
                origin = self.correction
                if collision == 'old_history':
                    self.change(); origin = self.f.record('later correction collision')
                self.t._id_factory = lambda prefix: (existing if collision != 'same_new' else 'duplicate-new') if prefix == 'condition' else original(prefix)
                self.assert_unchanged(self.request(origin=origin), 'unavailable')
                self.t._id_factory = original; self.change(origin=origin)

    def test_owned_write_and_event_replay_failures_roll_back_including_baseexception(self):
        for target in ('first_write', 'event', 'replay'):
            for exception in (RuntimeError, KeyboardInterrupt):
                with self.subTest(target=target, exception=exception):
                    self.setUp(); before = self.f.dump(); execute = ask_fixture.FaultConnection.execute
                    triggered = []
                    def fault(conn, sql, parameters=()):
                        result = execute(conn, sql, parameters)
                        statement = sql.lstrip().upper()
                        matches = (statement.startswith(('INSERT', 'UPDATE', 'DELETE')) if target == 'first_write'
                                   else statement.startswith('INSERT') and ('V5_INTAKE_' + target.upper()) in statement)
                        if matches and not triggered:
                            triggered.append(True); raise exception('private post-write failure')
                        return result
                    with patch.object(ask_fixture.FaultConnection, 'execute', fault):
                        if exception is KeyboardInterrupt:
                            with self.assertRaises(KeyboardInterrupt): self.t.control(self.request())
                        else: self.error(self.t.control(self.request()), 'unavailable')
                    self.assertTrue(triggered, 'fault must reach an owned write, not fail in fixture setup')
                    self.assertEqual(self.f.dump(), before); self.assertFalse(self.conn.in_transaction)
                    self.change()


if __name__ == '__main__':
    unittest.main()
