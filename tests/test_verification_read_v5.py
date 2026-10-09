"""READ01 VER component tests; synthetic owner callbacks, no product evidence."""
from pathlib import Path
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import hashlib
import sqlite3
import unittest
from pal.contracts_v5 import Result, dumps, loads
from pal.verification_v5 import VerificationStore
import test_verification_v5 as fixture_module


class VerificationReadTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.VerificationStoreTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.conditions[0]['description'] = '保存された下書き\n確認'
        self.receipt = self.fixture.saved()
        self.ref = self.receipt['verification_ref']
        self.now = '2026-10-09T01:02:03Z'
        self.store = self.construct(clock=self.clock)

    def clock(self):
        self.assertTrue(self.fixture.conn.in_transaction)
        return self.now

    def construct(self, **kwargs):
        def context(connection, request, *, purpose):
            self.assertEqual(request, {'work_ref': self.fixture.work})
            self.assertEqual(purpose, 'status')
            return self.fixture.synthetic_context(connection, request, purpose=purpose)
        def artifact(connection, request):
            self.assertEqual(set(request), {'ref'})
            self.assertIn(request['ref'], self.fixture.artifacts)
            return self.fixture.synthetic_artifact(connection, request)
        return VerificationStore(self.fixture.conn, context=context,
            artifact_inspect=artifact, source_gate=self.fixture.synthetic_gate,
            id_factory=self.fixture.next_id, **kwargs)

    def read(self, purpose='user_view'):
        return self.store.read({'ref': self.ref}, purpose=purpose)

    def snapshot(self):
        return '\n'.join(self.fixture.conn.iterdump())

    def test_exact_historical_projection_utf8_hash_and_ordinary_readonly(self):
        before, changes = self.snapshot(), self.fixture.conn.total_changes
        for purpose in ('user_view', 'verification', 'model_context'):
            body = self.fixture.value(self.read(purpose))
            self.assertEqual(set(body), {'ref', 'content', 'media_type', 'hash', 'observed_at',
                                        'work_ref', 'source_refs', 'usable'})
            projection = {'work_ref': self.fixture.work, 'conditions': self.fixture.conditions,
                'artifact_refs': self.fixture.artifacts, 'checks': self.receipt['checks'],
                'source_refs': self.fixture.records,
                'artifacts': [{'artifact_ref': r, 'hash': 'a' * 64, 'bytes': 3} for r in self.fixture.artifacts]}
            self.assertEqual(body['content'], dumps(projection))
            self.assertEqual(body['hash'], hashlib.sha256(body['content'].encode('utf-8')).hexdigest())
            self.assertEqual(body['media_type'], 'application/json')
            self.assertEqual(body['observed_at'], self.now)
            self.assertTrue(body['usable'])
            self.assertEqual(body['ref'], self.ref)
            self.assertEqual(body['work_ref'], self.fixture.work)
            self.assertEqual(body['source_refs'], self.fixture.records)
        self.assertEqual(changes, self.fixture.conn.total_changes)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.fixture.conn.in_transaction)

    def test_changed_read_time_excluded_from_body_hash(self):
        first = self.fixture.value(self.read())
        self.now = '2026-10-10T00:00:00+00:00'
        later = self.fixture.value(self.read())
        self.assertNotEqual(first['observed_at'], later['observed_at'])
        self.assertEqual(first['content'], later['content'])
        self.assertEqual(first['hash'], later['hash'])
        self.assertNotIn('observed_at', loads(first['content']))

    def test_all_invalidation_causes_retain_history_and_deny_other_purposes(self):
        original = self.fixture.value(self.read())
        for cause in ('epoch', 'set', 'source'):
            self.fixture.context_error = 'stale' if cause == 'epoch' else None
            self.fixture.gate_state = 'denied' if cause == 'source' else 'available'
            if cause == 'set':
                self.fixture.artifacts.append({'kind': 'artifact', 'id': 'later'})
            history = self.fixture.value(self.read())
            self.assertFalse(history['usable'])
            self.assertEqual((history['content'], history['hash']), (original['content'], original['hash']))
            for purpose in ('verification', 'model_context'):
                self.fixture.error(self.read(purpose), 'denied')
            if cause == 'set':
                self.fixture.artifacts.pop()

    def test_unknown_checks_still_usable_and_epoch_only_history_is_not_met_claim(self):
        body = self.fixture.value(self.read())
        self.assertTrue(body['usable'])
        self.assertIn('unknown', [c['status'] for c in loads(body['content'])['checks']])
        self.fixture.context_error = 'stale'
        history = self.fixture.value(self.read())
        self.assertFalse(history['usable'])
        self.assertEqual(body['content'], history['content'])

    def test_closed_requests_purpose_kind_and_missing_identity(self):
        for request in ({}, {'ref': self.ref, 'extra': 1}, {'ref': {}}, {'ref': {'kind': 'nonsense', 'id': 'v'}}):
            self.fixture.error(self.store.read(request, purpose='user_view'), 'invalid_input')
        self.fixture.error(self.store.read({'ref': {'kind': 'verification', 'id': 'absent'}}, purpose='user_view'), 'not_found')
        self.fixture.error(self.store.read({'ref': {'kind': 'record', 'id': 'r'}}, purpose='user_view'), 'unavailable')
        for purpose in ('wrong', True, None):
            with self.assertRaises(ValueError):
                self.read(purpose)
        self.fixture.conn.execute('BEGIN')
        with self.assertRaises(ValueError):
            self.read()
        self.fixture.conn.rollback()

    def test_uncertain_or_corrupt_owner_evidence_is_error(self):
        for code in ('not_found', 'unavailable'):
            self.fixture.context_error = code
            self.fixture.error(self.read(), 'unavailable')
        self.fixture.context_error = None
        self.fixture.artifact_error = 'not_found'
        self.fixture.error(self.read(), 'unavailable')
        self.fixture.artifact_error = None
        self.fixture.gate_state = 'not_found'
        self.fixture.error(self.read(), 'unavailable')
        self.fixture.gate_state = 'available'
        self.fixture.synthetic_artifact = lambda connection, request: Result.success({})
        malformed = self.construct(clock=self.clock)
        self.fixture.error(malformed.read({'ref': self.ref}, purpose='user_view'), 'unavailable')

    def test_default_clock_and_invalid_utc_values(self):
        from datetime import datetime, timedelta
        default = self.fixture.value(self.construct().read({'ref': self.ref}, purpose='user_view'))
        observed = datetime.fromisoformat(default['observed_at'].replace('Z', '+00:00'))
        self.assertEqual(observed.utcoffset(), timedelta(0))
        for bad in ('', 'not time', '2026-10-09T00:00:00', '2026-10-09T00:00:00+09:00', True):
            store = self.construct(clock=lambda: bad)
            self.fixture.error(store.read({'ref': self.ref}, purpose='user_view'), 'unavailable')

    def test_mutating_clock_rejects_with_unchanged_durable_dump(self):
        before, changes = self.snapshot(), self.fixture.conn.total_changes
        def mutate():
            self.fixture.conn.execute('UPDATE v5_tsk_test_state SET budget=0')
            return self.now
        self.fixture.error(self.construct(clock=mutate).read({'ref': self.ref}, purpose='user_view'), 'unavailable')
        self.assertEqual(self.snapshot(), before)
        self.assertGreater(self.fixture.conn.total_changes, changes)
        self.assertFalse(self.fixture.conn.in_transaction)

    def test_clock_commit_limit_and_interrupt_cleanup(self):
        def committed():
            self.fixture.conn.execute('UPDATE v5_tsk_test_state SET budget=0')
            self.fixture.conn.commit()
            return self.now
        self.fixture.error(self.construct(clock=committed).read({'ref': self.ref}, purpose='user_view'), 'unavailable')
        self.assertEqual(self.fixture.conn.execute('SELECT budget FROM v5_tsk_test_state').fetchone()[0], 0)
        for failure in (RuntimeError, KeyboardInterrupt, SystemExit):
            def interrupted():
                raise failure('private clock diagnostic')
            store = self.construct(clock=interrupted)
            if issubclass(failure, Exception):
                self.fixture.error(store.read({'ref': self.ref}, purpose='user_view'), 'unavailable')
            else:
                with self.assertRaises(failure):
                    store.read({'ref': self.ref}, purpose='user_view')
            self.assertFalse(self.fixture.conn.in_transaction)

    def test_reopen_into_second_inmemory_connection_preserves_projection(self):
        original = self.fixture.value(self.read())
        reopened = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(reopened.close)
        self.fixture.conn.backup(reopened)
        self.fixture.conn = reopened
        self.store = self.construct(clock=self.clock)
        self.assertEqual(self.fixture.value(self.read()), original)


if __name__ == '__main__':
    unittest.main()
