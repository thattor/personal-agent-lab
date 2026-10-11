"""ART public boundary tests using explicitly synthetic trusted collaborators."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Ref, Result, dumps, parse_model_action


class FaultConnection(sqlite3.Connection):
    fault = None

    def execute(self, sql, parameters=()):
        result = super().execute(sql, parameters)
        if self.fault and sql.startswith('INSERT INTO v5_art_'):
            failure, self.fault = self.fault, None
            raise failure('private injected diagnostic')
        return result


class ArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None, factory=FaultConnection)
        self.addCleanup(self.conn.close)
        self.refs = [{'kind': 'record', 'id': 'r1'}, {'kind': 'record', 'id': 'r2'}]
        self.work = {'goal_id': 'g', 'revision': 1, 'epoch': 0}
        self.authorizations = 0
        self.gate_state = 'available'
        self.store = self.construct(self.conn)
        self.request = {'work_ref': self.work, 'step_id': 's', 'content': '日本語\n\r\n',
                        'media_type': 'text/markdown', 'source_refs': self.refs[:1]}
        self.request['key'] = dumps(['C08.save', self.work, 's'])

    def synthetic_authorize(self, conn, request):
        self.assertIs(conn, self.conn)
        self.assertTrue(conn.in_transaction)
        self.assertEqual(set(request), {'work_ref', 'step_id', 'action'})
        self.assertEqual(request['action']['kind'], 'compose')
        self.authorizations += 1
        return Result.success({'source_refs': self.refs})

    def synthetic_gate(self, conn, refs):
        self.assertTrue(conn.in_transaction)
        self.assertIs(type(refs), tuple)
        return self.gate_state

    def construct(self, conn):
        return ArtifactStore(conn, authorize_save=self.synthetic_authorize,
                             source_gate=self.synthetic_gate, id_factory=lambda prefix: 'a',
                             clock=lambda: '2026-10-09T00:00:00+00:00')

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)
        self.assertNotIn('private', result.error.message)

    def saved(self):
        return self.value(self.store.save(self.request))

    def read(self, ref, purpose='verification'):
        return self.store.read({'ref': ref}, purpose=purpose)

    def test_exact_body_receipt_provenance_and_readonly_inspect(self):
        receipt = self.saved()
        data = self.request['content'].encode()
        self.assertEqual(receipt, {'artifact_ref': {'kind': 'artifact', 'id': 'a'},
                                  'hash': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        changes = self.conn.total_changes
        body = self.value(self.read(receipt['artifact_ref']))
        self.assertEqual(set(body), {'ref', 'content', 'media_type', 'hash', 'observed_at',
                                    'work_ref', 'source_refs', 'usable'})
        self.assertEqual(body['content'].encode(), data)
        self.assertEqual(body['source_refs'], self.refs)
        self.conn.execute('BEGIN IMMEDIATE')
        inspected = self.value(self.store.inspect(self.conn, {'ref': receipt['artifact_ref']}))
        self.assertEqual(set(inspected), {'artifact_ref', 'work_ref', 'step_id', 'hash', 'bytes', 'source_refs'})
        self.assertEqual(inspected['step_id'], 's')
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        self.assertEqual(changes, self.conn.total_changes)

    def test_original_replay_after_stop_and_exact_input_conflicts(self):
        receipt = self.saved()
        self.gate_state = 'denied'
        for purpose in ('model_context', 'verification'):
            self.error(self.read(receipt['artifact_ref'], purpose), 'denied')
        self.assertFalse(self.value(self.read(receipt['artifact_ref'], 'user_view'))['usable'])
        self.conn.execute('BEGIN')
        self.error(self.store.inspect(self.conn, {'ref': receipt['artifact_ref']}), 'denied')
        self.conn.rollback()
        self.assertEqual(self.value(self.store.save(dict(reversed(list(self.request.items()))))), receipt)
        self.assertEqual(self.authorizations, 1)
        self.assertEqual(self.value(self.store.get_by_key({'key': self.request['key']})), receipt)
        for changed in ({'content': 'changed'}, {'key': 'other'}, {'source_refs': list(reversed(self.refs))}):
            self.error(self.store.save({**self.request, **changed}), 'conflict')

    def test_empty_unicode_newlines_and_inclusive_bound(self):
        for content in ('', 'é\n\r\n', 'x' * 1048576):
            with self.subTest(content_size=len(content)):
                self.conn.execute('DELETE FROM v5_art_body')
                self.conn.execute('DELETE FROM v5_art_replay')
                receipt = self.value(self.store.save({**self.request, 'content': content}))
                self.assertEqual(self.value(self.read(receipt['artifact_ref']))['content'], content)

    def test_strict_requests_and_no_key_burn(self):
        bad = [None, {**self.request, 'extra': 1}, {**self.request, 'content': True},
               {**self.request, 'content': '\ud800'},
               {**self.request, 'media_type': 'text/html'}, {**self.request, 'key': ''},
               {**self.request, 'work_ref': {**self.work, 'epoch': True}},
               {**self.request, 'work_ref': {**self.work, 'revision': 2**63}}]
        for request in bad:
            self.error(self.store.save(request), 'invalid_input')
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')
        self.saved()

    def test_content_limit_error_is_preserved_without_burning_key(self):
        self.error(self.store.save({**self.request, 'content': 'x' * 1048577}), 'limit')
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')
        self.saved()

    def test_shared_compose_duplicate_refs_remain_exact_input_identity(self):
        action = parse_model_action(dumps({'kind': 'compose', 'content': 'shared draft',
            'media_type': 'text/plain', 'source_refs': self.refs[:1] * 2}),
            allowed_refs=[Ref.from_json(ref) for ref in self.refs]).to_json()
        request = {**self.request, **{k: v for k, v in action.items() if k != 'kind'}}
        self.assertEqual(request['source_refs'], self.refs[:1] * 2)
        receipt = self.value(self.store.save(request))
        self.assertEqual(self.value(self.store.save(request)), receipt)
        self.error(self.store.save({**request, 'source_refs': self.refs[:1]}), 'conflict')
        self.assertEqual(self.value(self.read(receipt['artifact_ref']))['source_refs'], self.refs)

    def test_inspect_exception_cleans_only_its_savepoint(self):
        ref = self.saved()['artifact_ref']
        self.conn.execute('CREATE TABLE synthetic_caller (x)')
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            def broken_gate(conn, refs):
                raise failure('synthetic gate failure')
            self.store._source_gate = broken_gate
            self.conn.execute('BEGIN')
            self.conn.execute('INSERT INTO synthetic_caller VALUES (1)')
            self.conn.execute('SAVEPOINT synthetic_owner')
            if issubclass(failure, Exception):
                self.error(self.store.inspect(self.conn, {'ref': ref}), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.store.inspect(self.conn, {'ref': ref})
            self.assertTrue(self.conn.in_transaction)
            self.assertEqual(self.conn.execute('SELECT count(*) FROM synthetic_caller').fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                self.conn.execute('RELEASE v5_art_callback')
            self.conn.execute('RELEASE synthetic_owner')
            self.conn.rollback()

    def test_missing_and_unsupported_refs_and_invalid_read_shape(self):
        self.error(self.read({'kind': 'artifact', 'id': 'missing'}), 'not_found')
        self.error(self.read({'kind': 'record', 'id': 'r1'}), 'unavailable')
        self.error(self.store.read({'ref': {}, 'extra': 1}, purpose='user_view'), 'invalid_input')
        self.error(self.store.get_by_key({'key': True}), 'invalid_input')

    def test_authority_failure_codes_and_corrupt_authority(self):
        for code in ('not_found', 'stale', 'denied', 'conflict', 'unavailable'):
            self.store._authorize = lambda c, r: Result.failure(code, 'private diagnosis')
            self.error(self.store.save(self.request), code)
        for value in (None, Result.success({}), Result.success({'source_refs': []}),
                      Result.success({'source_refs': [{'kind': 'artifact', 'id': 'x'}]}),
                      Result.success({'source_refs': self.refs[1:]})):
            self.store._authorize = lambda c, r: value
            self.error(self.store.save(self.request), 'unavailable')
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')

    def test_source_gate_failures_and_missing_dependency_history(self):
        for state in ('denied', 'not_found', 'unavailable'):
            self.gate_state = state
            self.error(self.store.save(self.request), state)
        self.gate_state = 'available'
        ref = self.saved()['artifact_ref']
        for state in ('not_found', 'unavailable', 'bad', True):
            self.gate_state = state
            self.error(self.read(ref, 'user_view'), 'unavailable')
            self.conn.execute('BEGIN')
            self.error(self.store.inspect(self.conn, {'ref': ref}), 'unavailable')
            self.conn.rollback()

    def test_fault_after_write_and_baseexception_roll_back(self):
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            self.conn.fault = failure
            if issubclass(failure, Exception):
                self.error(self.store.save(self.request), 'unavailable')
            else:
                with self.assertRaises(failure):
                    self.store.save(self.request)
            self.assertFalse(self.conn.in_transaction)
            self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_art_body').fetchone()[0], 0)
            self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')
        self.saved()

    def test_id_collision_rolls_back_second_step(self):
        self.saved()
        self.error(self.store.save({**self.request, 'key': 'second', 'step_id': 'second'}), 'unavailable')
        self.error(self.store.get_by_key({'key': 'second'}), 'not_found')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM v5_art_body').fetchone()[0], 1)

    def test_mutating_and_committing_collaborators_fail_closed(self):
        self.conn.execute('CREATE TABLE synthetic_probe (x)')
        def mutate(conn, request):
            conn.execute('INSERT INTO synthetic_probe VALUES (1)')
            return Result.success({'source_refs': self.refs})
        self.store._authorize = mutate
        self.error(self.store.save(self.request), 'unavailable')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM synthetic_probe').fetchone()[0], 0)
        def commit(conn, request):
            conn.execute('INSERT INTO synthetic_probe VALUES (2)')
            conn.commit()
            return Result.success({'source_refs': self.refs})
        self.store._authorize = commit
        self.error(self.store.save(self.request), 'unavailable')
        # This intentionally proves the documented limit of trusted callbacks.
        self.assertEqual(self.conn.execute('SELECT x FROM synthetic_probe').fetchall(), [(2,)])
        self.error(self.store.get_by_key({'key': self.request['key']}), 'not_found')

    def test_caller_transaction_and_host_configuration_preconditions(self):
        with self.assertRaises(ValueError):
            self.store.inspect(self.conn, {'ref': {'kind': 'artifact', 'id': 'a'}})
        with self.assertRaises(ValueError):
            self.store.read({'ref': {}}, purpose='wrong')
        self.conn.execute('BEGIN')
        for call in (lambda: self.store.save(self.request),
                     lambda: self.store.get_by_key({'key': 'x'}),
                     lambda: self.read({'kind': 'artifact', 'id': 'a'}),
                     lambda: self.construct(self.conn)):
            with self.assertRaises(ValueError):
                call()
            self.assertTrue(self.conn.in_transaction)
        other = sqlite3.connect(':memory:', isolation_level=None)
        try:
            other.execute('BEGIN')
            with self.assertRaises(ValueError):
                self.store.inspect(other, {'ref': {}})
            self.assertTrue(other.in_transaction)
        finally:
            other.close()
        self.conn.rollback()

    def test_metadata_body_and_provenance_tampering_are_unavailable(self):
        ref = self.saved()['artifact_ref']
        original = self.conn.execute('SELECT * FROM v5_art_body').fetchone()
        columns = [r[1] for r in self.conn.execute('PRAGMA table_info(v5_art_body)')]
        changes = {'body': b'wrong', 'media_type': 'text/html', 'hash': 'f' * 64,
                   'byte_count': 0, 'step_id': 'different', 'work_json': dumps({**self.work, 'epoch': 1}),
                   'observed_at': '', 'sources_json': dumps(self.refs[:1]), 'binding_json': '{}'}
        for column, value in changes.items():
            with self.subTest(column=column):
                self.conn.execute('UPDATE v5_art_body SET ' + column + '=?', (value,))
                self.error(self.read(ref), 'unavailable')
                self.conn.execute('BEGIN')
                self.error(self.store.inspect(self.conn, {'ref': ref}), 'unavailable')
                self.conn.rollback()
                self.conn.execute('UPDATE v5_art_body SET ' + column + '=?', (original[columns.index(column)],))
        self.conn.execute('DELETE FROM v5_art_replay')
        self.error(self.read(ref), 'unavailable')

    def test_array_order_is_input_identity_and_receipt_metadata_matches_input(self):
        self.request['source_refs'] = list(self.refs)
        receipt = self.saved()
        self.error(self.store.save({**self.request, 'source_refs': list(reversed(self.refs))}), 'conflict')
        altered = {**receipt, 'hash': '0' * 64}
        self.conn.execute('UPDATE v5_art_replay SET result_json=?', (dumps(altered),))
        self.error(self.store.get_by_key({'key': self.request['key']}), 'unavailable')
        self.error(self.store.save(self.request), 'unavailable')

    def test_inspect_interrupt_preserves_caller_transaction_for_owner_rollback(self):
        ref = self.saved()['artifact_ref']
        def interrupt(conn, refs):
            raise SystemExit()
        self.store._source_gate = interrupt
        self.conn.execute('BEGIN')
        with self.assertRaises(SystemExit):
            self.store.inspect(self.conn, {'ref': ref})
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()

    def test_bad_replay_metadata_unavailable_without_authority(self):
        self.saved()
        self.conn.execute('UPDATE v5_art_replay SET result_json=?', ('{}',))
        self.error(self.store.get_by_key({'key': self.request['key']}), 'unavailable')
        self.error(self.store.save(self.request), 'unavailable')
        self.assertEqual(self.authorizations, 1)

    def test_gate_mutation_and_interrupt_read_rollback(self):
        ref = self.saved()['artifact_ref']
        def mutate(conn, refs):
            conn.execute('UPDATE v5_art_body SET observed_at=observed_at')
            return 'available'
        self.store._source_gate = mutate
        self.error(self.read(ref), 'unavailable')
        self.assertFalse(self.conn.in_transaction)
        def interrupt(conn, refs):
            raise KeyboardInterrupt()
        self.store._source_gate = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.read(ref)
        self.assertFalse(self.conn.in_transaction)

    def test_reopen_and_busy_lock_do_not_burn_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'draft.sqlite'
            conn = sqlite3.connect(path, isolation_level=None, timeout=0)
            other = sqlite3.connect(path, isolation_level=None, timeout=0)
            self.addCleanup(conn.close)
            self.addCleanup(other.close)
            self.conn = conn
            store = self.construct(conn)
            other.execute('BEGIN IMMEDIATE')
            self.error(store.save(self.request), 'unavailable')
            self.assertFalse(conn.in_transaction)
            other.rollback()
            receipt = self.value(store.save(self.request))
            conn.close()
            conn = sqlite3.connect(path, isolation_level=None, timeout=0)
            self.addCleanup(conn.close)
            self.conn = conn
            store = self.construct(conn)
            self.assertEqual(self.value(store.get_by_key({'key': self.request['key']})), receipt)
            self.assertEqual(self.value(store.read({'ref': receipt['artifact_ref']}, purpose='verification'))['content'],
                             self.request['content'])


if __name__ == '__main__':
    unittest.main()
