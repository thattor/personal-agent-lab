"""Independent probes for malformed owner snapshots and immutable VER bindings."""
import copy
import unittest

from pal.contracts_v5 import Result, dumps, loads
import test_verification_v5 as fixtures


class VerificationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.VerificationStoreTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_wrong_ref_kind_is_invalid_input_in_both_read_apis(self):
        request = {'verification_ref': {'kind': 'record', 'id': 'not-verification'}}
        self.f.error(self.f.store.get_verification(request), 'invalid_input')
        self.f.conn.execute('BEGIN')
        try:
            self.f.error(self.f.store.inspect(self.f.conn, request), 'invalid_input')
        finally:
            self.f.conn.rollback()

    def test_empty_or_duplicate_owner_context_is_unavailable_without_saving(self):
        changes = ({'conditions': []}, {'source_refs': []},
                   {'source_refs': self.f.records * 2},
                   {'artifact_refs': self.f.artifacts * 2})
        for index, change in enumerate(changes):
            with self.subTest(change=change):
                def context(conn, request, *, purpose):
                    value = self.f.value(self.f.synthetic_context(conn, request, purpose=purpose))
                    return Result.success({**value, **change})
                store = self.f.construct(context=context, source_gate=lambda c, refs: 'available')
                request = {**self.f.request, 'key': 'context-' + str(index)}
                self.f.error(store.verify(request), 'unavailable')
                self.f.error(store.get_by_key({'key': request['key']}), 'not_found')

    def test_missing_artifact_provenance_and_oversized_metadata_are_unavailable(self):
        for index, change in enumerate(({'source_refs': []}, {'source_refs': self.f.records * 2},
                                        {'bytes': 1048577})):
            with self.subTest(change=change):
                def artifact(conn, request):
                    return Result.success({**self.f.value(self.f.synthetic_artifact(conn, request)), **change})
                store = self.f.construct(artifact_inspect=artifact, source_gate=lambda c, refs: 'available')
                self.f.error(store.verify({**self.f.request, 'key': 'artifact-' + str(index)}), 'unavailable')

    def test_impossible_same_revision_context_changes_are_not_legitimate_invalidation(self):
        receipt = self.f.saved()
        mutations = [
            {'conditions': [{**self.f.conditions[0], 'description': 'changed'}, *self.f.conditions[1:]]},
            {'source_refs': self.f.records},
            {'artifact_refs': self.f.artifacts[:1]},
            {'artifact_refs': list(reversed(self.f.artifacts))},
            {'artifact_refs': [self.f.artifacts[1], self.f.artifacts[0], {'kind': 'artifact', 'id': 'later'}]},
            {'work_ref': {**self.f.work, 'epoch': self.f.work['epoch'] + 1}},
        ]
        for change in mutations:
            with self.subTest(change=change):
                def context(conn, request, *, purpose):
                    return Result.success({**self.f.value(self.f.synthetic_context(conn, request, purpose=purpose)), **change})
                store = self.f.construct(context=context)
                self.f.error(store.get_verification({'verification_ref': receipt['verification_ref']}), 'unavailable')

    def test_uncertain_owner_errors_do_not_create_successful_invalidation(self):
        receipt = self.f.saved()
        self.f.context_error = 'denied'
        self.f.error(self.f.status(receipt), 'unavailable')
        self.f.context_error = None
        self.f.artifact_error = 'stale'
        self.f.error(self.f.status(receipt), 'unavailable')
        self.f.artifact_error = 'denied'
        self.assertEqual(self.f.value(self.f.status(receipt))['status'], 'invalidated')

    def test_unexpected_save_callback_error_is_unavailable(self):
        for code in ('limit', 'invalid_input', 'ambiguous'):
            self.f.context_error = code
            self.f.error(self.f.store.verify(self.f.request), 'unavailable')
        self.f.context_error = None
        self.f.artifact_error = 'stale'
        self.f.error(self.f.store.verify(self.f.request), 'unavailable')

    def test_artifact_epoch_cannot_change_after_its_immutable_snapshot(self):
        receipt = self.f.saved()
        for epoch in (0, self.f.work['epoch'] + 100):
            def artifact(conn, request):
                value = self.f.value(self.f.synthetic_artifact(conn, request))
                return Result.success({**value, 'work_ref': {**value['work_ref'], 'epoch': epoch}})
            store = self.f.construct(artifact_inspect=artifact)
            self.f.error(store.get_verification({'verification_ref': receipt['verification_ref']}), 'unavailable')

    def test_empty_conditions_and_forged_checks_in_storage_fail_even_historical_replay(self):
        self.f.saved()
        original = self.f.conn.execute('SELECT record_json FROM v5_ver_body').fetchone()[0]
        for corruption in ('empty', 'semantic_met', 'duplicate', 'required_empty'):
            with self.subTest(corruption=corruption):
                record = loads(original)
                if corruption == 'empty':
                    record['conditions'] = []
                    record['checks'] = []
                elif corruption == 'semantic_met':
                    record['checks'][1]['status'] = 'met'
                elif corruption == 'duplicate':
                    record['conditions'][1]['id'] = record['conditions'][0]['id']
                else:
                    record['required_refs'] = []
                record['receipt']['checks'] = copy.deepcopy(record['checks'])
                self.f.conn.execute('UPDATE v5_ver_body SET record_json=?', (dumps(record),))
                self.f.conn.execute('UPDATE v5_ver_replay SET result_json=?', (dumps(record['receipt']),))
                self.f.error(self.f.store.get_by_key({'key': 'verify-one'}), 'unavailable')

    def test_id_factory_transaction_replacement_is_detected_before_verification_writes(self):
        def commit(prefix):
            self.f.conn.commit()
            return prefix + '-premature'
        store = self.f.construct(id_factory=commit)
        self.f.error(store.verify(self.f.request), 'unavailable')
        self.assertFalse(self.f.conn.in_transaction)
        self.assertEqual(self.f.conn.execute('SELECT count(*) FROM v5_ver_body').fetchone()[0], 0)
        self.f.error(store.get_by_key({'key': 'verify-one'}), 'not_found')


if __name__ == '__main__':
    unittest.main()
