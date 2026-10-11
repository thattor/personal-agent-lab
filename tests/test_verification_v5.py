"""VER public acceptance with synthetic owner callbacks, not product evidence."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import sqlite3
import unittest

from pal.contracts_v5 import Ref, Result, dumps
from pal.verification_v5 import VerificationStore


class FaultConnection(sqlite3.Connection):
    fault = None

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if self.fault and sql.lstrip().upper().startswith('INSERT') and 'v5_ver_' in sql:
            failure, self.fault = self.fault, None
            raise failure('private synthetic insert fault')
        return result


class VerificationStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None, factory=FaultConnection)
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE v5_tsk_test_state (state TEXT, budget INTEGER)')
        self.conn.execute("INSERT INTO v5_tsk_test_state VALUES ('running',7)")
        self.work = {'goal_id': 'g', 'revision': 1, 'epoch': 2}
        self.artifacts = [{'kind': 'artifact', 'id': 'a1'}, {'kind': 'artifact', 'id': 'a2'}]
        self.records = [{'kind': 'record', 'id': 'required'}, {'kind': 'record', 'id': 'unselected'}]
        self.conditions = [{'id': 'saved', 'description': 'Draft exists', 'check': 'artifact_saved'},
                           {'id': 'meaning', 'description': 'Meaning fits', 'check': 'semantic'},
                           {'id': 'fetched', 'description': 'Fetched', 'check': 'source_fetched'}]
        self.context_error = self.artifact_error = None
        self.gate_state = 'available'
        self.context_calls = []
        self.serial = 0
        self.store = self.construct()
        self.request = {'key': 'verify-one', 'work_ref': copy.deepcopy(self.work),
                        'artifact_refs': copy.deepcopy(self.artifacts)}

    def synthetic_context(self, connection, request, *, purpose):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.assertEqual(set(request), {'work_ref'})
        self.assertIn(purpose, ('save', 'status'))
        self.context_calls.append(purpose)
        if self.context_error:
            return Result.failure(self.context_error, 'private context diagnosis')
        return Result.success({'work_ref': self.work, 'conditions': self.conditions,
                               'artifact_refs': self.artifacts, 'source_refs': self.records[:1]})

    def synthetic_artifact(self, connection, request):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.assertEqual(set(request), {'ref'})
        if self.artifact_error:
            return Result.failure(self.artifact_error, 'private artifact diagnosis')
        return Result.success({'artifact_ref': request['ref'], 'work_ref': self.work,
            'step_id': 'step-' + request['ref']['id'], 'hash': 'a' * 64, 'bytes': 3,
            'source_refs': self.records})

    def synthetic_gate(self, connection, refs):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.assertIs(type(refs), tuple)
        self.assertTrue(all(type(ref) is Ref and ref.kind.value == 'record' for ref in refs))
        self.assertEqual(set(refs), {Ref.from_json(r) for r in self.records})
        return self.gate_state

    def next_id(self, prefix):
        self.serial += 1
        return prefix + '-' + str(self.serial)

    def construct(self, **overrides):
        options = {'context': self.synthetic_context, 'artifact_inspect': self.synthetic_artifact,
                   'source_gate': self.synthetic_gate, 'id_factory': self.next_id}
        return VerificationStore(self.conn, **{**options, **overrides})

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        self.assertLess(len(result.error.message), 160)
        self.assertNotIn('private', result.error.message)

    def saved(self):
        receipt = self.value(self.store.verify(self.request))
        self.assertEqual(set(receipt), {'verification_ref', 'checks'})
        self.assertEqual(Ref.from_json(receipt['verification_ref']).kind.value, 'verification')
        return receipt

    def status(self, receipt):
        return self.store.get_verification({'verification_ref': receipt['verification_ref']})

    def test_fixed_conditions_met_unknown_and_no_task_or_budget_change(self):
        receipt = self.saved()
        self.assertEqual([c['condition_id'] for c in receipt['checks']], ['saved', 'meaning', 'fetched'])
        self.assertEqual([c['status'] for c in receipt['checks']], ['met', 'unknown', 'unknown'])
        for check in receipt['checks']:
            self.assertEqual(set(check), {'condition_id', 'status', 'reason', 'evidence_refs'})
            self.assertIs(type(check['reason']), str)
            self.assertTrue(check['reason'])
            self.assertLess(len(check['reason']), 160)
            self.assertTrue(all(ref in self.artifacts + self.records for ref in check['evidence_refs']))
        typed = self.value(self.status(receipt))
        self.assertEqual(set(typed), {'work_ref', 'artifact_refs', 'checks', 'source_refs', 'status'})
        self.assertEqual(typed['checks'], receipt['checks'])
        self.assertEqual(typed['artifact_refs'], self.artifacts)
        self.assertEqual(set(dumps(r) for r in typed['source_refs']), set(dumps(r) for r in self.records))
        self.assertEqual(typed['status'], 'valid')
        self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_test_state').fetchall(), [('running', 7)])

    def test_empty_set_is_unmet_not_missing_evidence(self):
        self.artifacts = []
        self.records = self.records[:1]
        self.request['artifact_refs'] = []
        self.assertEqual([c['status'] for c in self.saved()['checks']], ['unmet', 'unknown', 'unknown'])

    def test_exact_ordered_whole_set_required(self):
        for refs in (self.artifacts[:1], list(reversed(self.artifacts)), self.artifacts * 2,
                     self.artifacts + [{'kind': 'artifact', 'id': 'extra'}]):
            self.error(self.store.verify({**self.request, 'artifact_refs': refs}), 'conflict')
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')
        self.saved()

    def test_closed_shape_types_bounds_and_nonartifact_input(self):
        for request in (None, {**self.request, 'extra': 1}, {**self.request, 'key': ''},
                        {**self.request, 'key': True}, {**self.request, 'artifact_refs': self.records},
                        {**self.request, 'artifact_refs': ()},
                        {**self.request, 'work_ref': {**self.work, 'epoch': True}},
                        {**self.request, 'work_ref': {**self.work, 'revision': 2**63}},
                        {**self.request, 'work_ref': {**self.work, 'goal_id': '\ud800'}}):
            self.error(self.store.verify(request), 'invalid_input')
        self.error(self.store.get_by_key({'key': 'absent'}), 'not_found')

    def test_original_replay_precedes_authority_after_invalidation(self):
        receipt = self.saved()
        calls = len(self.context_calls)
        self.context_error = 'stale'
        self.assertEqual(self.value(self.store.verify(dict(reversed(list(self.request.items()))))), receipt)
        self.assertEqual(len(self.context_calls), calls)
        self.assertEqual(self.value(self.store.get_by_key({'key': self.request['key']})), receipt)
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.error(self.store.verify({**self.request, 'artifact_refs': []}), 'conflict')

    def test_context_authority_failures_are_preserved_without_key(self):
        for code in ('not_found', 'stale', 'denied', 'conflict', 'unavailable'):
            self.context_error = code
            self.error(self.store.verify(self.request), code)
            self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')

    def test_required_artifact_missing_and_source_uncertainty_are_unavailable(self):
        for code in ('not_found', 'unavailable', 'denied'):
            self.artifact_error = code
            self.error(self.store.verify(self.request), 'denied' if code == 'denied' else 'unavailable')
        self.artifact_error = None
        for state in ('not_found', 'unavailable', 'denied'):
            self.gate_state = state
            self.error(self.store.verify(self.request), 'denied' if state == 'denied' else 'unavailable')
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')

    def test_older_artifact_epoch_allowed_but_wrong_revision_or_goal_stale(self):
        def artifact_with_work(work):
            def callback(conn, request):
                result = self.value(self.synthetic_artifact(conn, request))
                return Result.success({**result, 'work_ref': work})
            return callback
        older = self.construct(artifact_inspect=artifact_with_work({**self.work, 'epoch': 0}))
        self.assertEqual(self.value(older.verify(self.request))['checks'][0]['status'], 'met')
        for work in ({**self.work, 'revision': 2}, {**self.work, 'goal_id': 'different'}):
            store = self.construct(artifact_inspect=artifact_with_work(work))
            self.error(store.verify({**self.request, 'key': 'wrong-' + dumps(work)}), 'stale')

    def test_epoch_append_and_denied_dependency_invalidate_historical_fact(self):
        receipt = self.saved()
        self.context_error = 'stale'
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.context_error = None
        self.artifacts.append({'kind': 'artifact', 'id': 'later'})
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.artifacts.pop()
        self.gate_state = 'denied'
        self.assertEqual(self.value(self.status(receipt))['status'], 'invalidated')
        self.assertEqual(self.value(self.store.get_by_key({'key': self.request['key']})), receipt)

    def test_unchanged_pause_valid_and_status_uncertainty_not_invalidated(self):
        receipt = self.saved()
        self.conn.execute("UPDATE v5_tsk_test_state SET state='paused'")
        self.assertEqual(self.value(self.status(receipt))['status'], 'valid')
        self.assertEqual(self.context_calls[-1], 'status')
        for code in ('not_found', 'unavailable'):
            self.context_error = code
            self.error(self.status(receipt), code)
        self.context_error = None
        self.gate_state = 'not_found'
        self.error(self.status(receipt), 'unavailable')
        self.gate_state = 'available'
        self.artifact_error = 'not_found'
        self.error(self.status(receipt), 'unavailable')

    def test_malformed_callbacks_and_duplicate_condition_ids_fail_closed(self):
        for callback in (lambda c, r, **kw: None, lambda c, r, **kw: Result.success({})):
            store = self.construct(context=callback)
            self.error(store.verify(self.request), 'unavailable')
        self.conditions.append(dict(self.conditions[0]))
        self.error(self.store.verify(self.request), 'unavailable')
        self.conditions.pop()
        for callback in (lambda c, r: Result.success({}), lambda c, r: None):
            self.error(self.construct(artifact_inspect=callback).verify(self.request), 'unavailable')
        for change in ({'bytes': True}, {'hash': 'bad'}, {'artifact_ref': self.artifacts[1]}):
            def malformed(conn, request):
                value = self.value(self.synthetic_artifact(conn, request))
                return Result.success({**value, **change})
            self.error(self.construct(artifact_inspect=malformed).verify(self.request), 'unavailable')
        self.error(self.construct(source_gate=lambda c, refs: True).verify(self.request), 'unavailable')

    def test_mutating_and_committing_callbacks_fail_without_false_rollback_claim(self):
        def mutating(conn, request, *, purpose):
            conn.execute('UPDATE v5_tsk_test_state SET budget=0')
            return self.synthetic_context(conn, request, purpose=purpose)
        self.error(self.construct(context=mutating).verify(self.request), 'unavailable')
        self.assertEqual(self.conn.execute('SELECT budget FROM v5_tsk_test_state').fetchone()[0], 7)
        def committing(conn, request, *, purpose):
            conn.commit()
            return Result.success({})
        self.error(self.construct(context=committing).verify(self.request), 'unavailable')
        self.assertFalse(self.conn.in_transaction)
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')

    def test_post_insert_fault_and_interrupt_rollback_and_key_retry(self):
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            self.conn.fault = failure
            if issubclass(failure, Exception):
                self.error(self.store.verify(self.request), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.store.verify(self.request)
            self.assertIsNone(self.conn.fault, 'must reach an actual v5_ver_ INSERT')
            self.assertFalse(self.conn.in_transaction)
            self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')
        self.saved()

    def test_readonly_inspect_preserves_caller_transaction_and_writes(self):
        receipt = self.saved()
        typed = self.value(self.status(receipt))
        self.conn.execute('BEGIN')
        self.conn.execute('UPDATE v5_tsk_test_state SET budget=6')
        changes = self.conn.total_changes
        self.assertEqual(self.value(self.store.inspect(self.conn,
            {'verification_ref': receipt['verification_ref']})), typed)
        self.assertTrue(self.conn.in_transaction)
        self.assertEqual(self.conn.total_changes, changes)
        self.assertEqual(self.conn.execute('SELECT budget FROM v5_tsk_test_state').fetchone()[0], 6)
        self.conn.rollback()

    def test_caller_configuration_and_active_connection_preconditions(self):
        with self.assertRaises(ValueError):
            self.store.inspect(self.conn, {'verification_ref': {'kind': 'verification', 'id': 'x'}})
        self.conn.execute('BEGIN')
        for operation in (self.construct, lambda: self.store.verify(self.request),
                          lambda: self.store.get_by_key({'key': 'x'}),
                          lambda: self.store.get_verification({'verification_ref': {'kind': 'verification', 'id': 'x'}})):
            with self.assertRaises(ValueError):
                operation()
            self.assertTrue(self.conn.in_transaction)
        other = sqlite3.connect(':memory:', isolation_level=None)
        try:
            other.execute('BEGIN')
            with self.assertRaises(ValueError):
                self.store.inspect(other, {'verification_ref': {'kind': 'verification', 'id': 'x'}})
        finally:
            other.close()
        self.conn.rollback()

    def test_unknown_verification_and_malformed_read_requests(self):
        self.error(self.store.get_verification({'verification_ref': {'kind': 'verification', 'id': 'missing'}}), 'not_found')
        self.error(self.store.get_verification({'verification_ref': {}}), 'invalid_input')
        self.error(self.store.get_by_key({'key': 'x', 'extra': 1}), 'invalid_input')


if __name__ == '__main__':
    unittest.main()
