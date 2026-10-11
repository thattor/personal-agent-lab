"""MEM01/1 author tests; transactional callbacks here are synthetic, not TSK proof."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pal.contracts_v5 import Ref, Result, dumps, loads
from pal.memory_v5 import MemoryStore
from pal.sanitize import sanitize


class MemoryV5Tests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'memory.sqlite'
        self.conn = self.connect()
        self.conn.execute('CREATE TABLE test_events (key TEXT PRIMARY KEY, request TEXT)')
        self.conn.execute('CREATE TABLE test_invalidations (key TEXT PRIMARY KEY, request TEXT)')
        self.event_mode = 'ok'
        self.invalidate_mode = 'ok'
        self.next_id = 0
        self.event_calls = []
        self.invalidate_calls = []
        self.store = self.make_store()

    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=0)
        self.addCleanup(connection.close)
        return connection

    def make_store(self, **overrides):
        config = dict(sanitize_text=sanitize, append_event=self.event,
                      invalidate_by_refs=self.invalidate, id_factory=self.identifier,
                      clock=lambda: '2026-10-09T00:00:00+00:00')
        config.update(overrides)
        return MemoryStore(self.conn, **config)

    def identifier(self, prefix):
        self.next_id += 1
        return f'{prefix}:{self.next_id}'

    def event(self, connection, request):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.event_calls.append(request)
        connection.execute('INSERT INTO test_events VALUES (?,?)', (request['key'], dumps(request)))
        if self.event_mode == 'raise':
            raise RuntimeError('SENTINEL private exception')
        if self.event_mode == 'failure':
            return Result.failure('denied', 'event rejected')
        if self.event_mode != 'ok':
            return self.event_mode
        return Result.success({'event_id': 'event:' + str(len(self.event_calls))})

    def invalidate(self, connection, *, key, session_id, refs):
        self.assertIs(connection, self.conn)
        self.assertTrue(connection.in_transaction)
        self.assertIs(type(refs), tuple)
        self.assertTrue(all(type(ref) is Ref for ref in refs))
        body = {'session_id': session_id, 'refs': [ref.to_json() for ref in refs]}
        self.invalidate_calls.append((key, body))
        connection.execute('INSERT INTO test_invalidations VALUES (?,?)', (key, dumps(body)))
        if self.invalidate_mode == 'raise':
            raise RuntimeError('SENTINEL private exception')
        if self.invalidate_mode == 'failure':
            return Result.failure('unavailable', 'affected work not supported')
        if self.invalidate_mode != 'ok':
            return self.invalidate_mode
        return Result.success({'work_refs': []})

    def append(self, key='append', text='日本語の本文', session='session', role='user'):
        return self.store.append({'client_key': key, 'session_id': session, 'role': role, 'text': text})

    def ref(self, key='append', **kwargs):
        result = self.append(key, **kwargs)
        self.assertTrue(result.ok)
        return result.value.to_json()['record_ref']

    def stop(self, ref, key='stop', session='session'):
        return self.store.stop_reference({'key': key, 'source_ref': ref}, session_id=session)

    def snapshot(self):
        return {table: self.conn.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
                for table in ('v5_mem_record', 'v5_mem_replay', 'test_events', 'test_invalidations')}

    def assertFailure(self, result, code):
        self.assertIs(type(result), Result)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code.value, code)
        self.assertLessEqual(len(result.error.message), 200)
        self.assertNotIn('SENTINEL', dumps(result))
        self.assertFalse(self.conn.in_transaction)

    def test_durable_unicode_empty_whitespace_hash_and_host_metadata(self):
        refs = [self.ref(str(i), text=value, role='assistant')
                for i, value in enumerate(['日本語😀\n', '', ' \t\n'])]
        self.conn.close()
        self.conn = self.connect()
        self.store = self.make_store()
        for ref, text in zip(refs, ['日本語😀\n', '', ' \t\n']):
            result = self.store.read({'ref': ref}, purpose='model_context')
            value = result.value.to_json()
            self.assertEqual(set(value), {'ref', 'content', 'media_type', 'hash', 'observed_at',
                                         'source_refs', 'usable'})
            self.assertEqual(value, {'ref': ref, 'content': text, 'media_type': 'text/plain',
                                    'hash': hashlib.sha256(text.encode()).hexdigest(),
                                    'observed_at': '2026-10-09T00:00:00+00:00',
                                    'source_refs': [], 'usable': True})
        rows = self.conn.execute('SELECT seq, role, session_id FROM v5_mem_record ORDER BY seq').fetchall()
        self.assertEqual([row[0] for row in rows], [1, 2, 3])
        self.assertEqual([row[1:] for row in rows], [('assistant', 'session')] * 3)
        self.assertEqual(len(self.snapshot()['test_events']), 3)

    def test_sanitize_before_persistence_and_canonical_sanitized_replay(self):
        first = self.append(text='token=SENTINEL_FIRST')
        self.assertTrue(first.ok)
        before = self.snapshot()
        second = self.append(text='token=SENTINEL_SECOND')
        self.assertEqual(second, first)
        self.assertEqual(self.snapshot(), before)
        persisted = '\n'.join(self.conn.iterdump())
        self.assertNotIn('SENTINEL', persisted)
        self.assertNotIn(hashlib.sha256(b'token=SENTINEL_FIRST').hexdigest(), persisted)
        ref = first.value.to_json()['record_ref']
        self.assertEqual(self.store.read({'ref': ref}, purpose='user_view').value.to_json()['content'], '[REDACTED]')
        self.assertEqual(len(self.event_calls), 1)

    def test_append_reopen_replay_conflicts_and_no_id_or_clock_reissue(self):
        first = self.append()
        before = self.snapshot()
        self.conn.close()
        self.conn = self.connect()
        def forbidden(*args):
            raise AssertionError('must not issue replay IDs or timestamps')
        self.store = self.make_store(id_factory=forbidden, clock=forbidden)
        reordered = {'text': '日本語の本文', 'role': 'user', 'session_id': 'session', 'client_key': 'append'}
        self.assertEqual(self.store.append(reordered), first)
        for options in [dict(text='different'), dict(session='other'), dict(role='assistant')]:
            self.assertFailure(self.append(**options), 'conflict')
        self.assertEqual(self.snapshot(), before)

    def test_sanitizer_failure_and_invalid_returns_happen_before_begin(self):
        trace = []
        for bad in [None, 1, '\ud800']:
            self.store = self.make_store(sanitize_text=lambda text, bad=bad: bad)
            self.conn.set_trace_callback(trace.append)
            trace.clear()
            before = self.snapshot()
            self.assertFailure(self.append(), 'unavailable')
            self.assertEqual(self.snapshot(), before)
            self.assertNotIn('BEGIN IMMEDIATE', trace)
        def raising(text):
            raise RuntimeError('SENTINEL sanitizer exception')
        self.store = self.make_store(sanitize_text=raising)
        self.assertFailure(self.append(), 'unavailable')
        self.store = self.make_store()
        self.assertTrue(self.append().ok)

    def test_event_shape_namespaced_keys_and_no_optional_null_fields(self):
        ref = self.ref('opaque:key:[event]')
        request = self.event_calls[0]
        self.assertEqual(request, {'key': dumps(['C05.append', 'opaque:key:[event]', 'event']),
                                   'session_id': 'session', 'kind': 'accepted',
                                   'text': 'record saved', 'refs': [ref]})
        self.assertTrue(self.stop(ref, key='opaque:key:[event]', session='initiator').ok)
        invalidation_key, body = self.invalidate_calls[0]
        self.assertEqual(loads(invalidation_key), ['C05.stop_reference', 'opaque:key:[event]', 'invalidate'])
        self.assertEqual(body, {'session_id': 'initiator', 'refs': [ref]})
        self.assertEqual(self.event_calls[-1],
                         {'key': dumps(['C05.stop_reference', 'opaque:key:[event]', 'event']),
                          'session_id': 'initiator', 'kind': 'state',
                          'text': 'source use stopped', 'refs': [ref]})
        self.assertNotEqual(self.event_calls[0]['key'], self.event_calls[-1]['key'])

    def test_stop_current_reads_history_replay_and_new_key_no_duplicate_callbacks(self):
        ref = self.ref()
        before_content = self.store.read({'ref': ref}, purpose='user_view').value.to_json()
        result = self.stop(ref)
        self.assertEqual(result.to_json(), {'ok': True, 'value': {'affected_refs': [ref]}})
        after = self.snapshot()
        self.assertEqual(self.stop(ref), result)
        self.assertEqual(self.snapshot(), after)
        self.assertEqual(self.append().value.to_json()['record_ref'], ref)
        for purpose in ['model_context', 'verification']:
            self.assertFailure(self.store.read({'ref': ref}, purpose=purpose), 'denied')
        history = self.store.read({'ref': ref}, purpose='user_view').value.to_json()
        self.assertEqual(history, {**before_content, 'usable': False})
        self.assertTrue(self.stop(ref, key='new-key').ok)
        self.assertEqual(len(self.invalidate_calls), 1)
        self.assertEqual(len(self.event_calls), 2)
        self.assertEqual(len(self.snapshot()['v5_mem_replay']), 3)
        self.conn.close(); self.conn = self.connect(); self.store = self.make_store()
        self.assertEqual(self.stop(ref), result)
        self.assertFailure(self.store.read({'ref': ref}, purpose='verification'), 'denied')

    def test_stop_identity_contains_session_and_ref_missing_has_no_saved_failure(self):
        ref = self.ref()
        other = self.ref('other')
        self.assertTrue(self.stop(ref).ok)
        before = self.snapshot()
        self.assertFailure(self.stop(ref, session='other'), 'conflict')
        self.assertFailure(self.stop(other), 'conflict')
        self.assertFailure(self.stop({'kind': 'record', 'id': 'missing'}, key='missing'), 'not_found')
        self.assertEqual(self.snapshot(), before)

    def test_event_failure_exception_or_malformed_result_rolls_back_append_and_retry(self):
        self.ref('previous')
        before = self.snapshot()
        failures = [('raise', 'unavailable'), ('failure', 'denied'),
                    ({'event_id': 'raw'}, 'unavailable'),
                    (Result.success({'event_id': ''}), 'unavailable'),
                    (Result.success({'event_id': 'e', 'extra': 1}), 'unavailable'),
                    (Result.success(None), 'unavailable')]
        for mode, expected in failures:
            with self.subTest(mode=type(mode).__name__):
                self.event_mode = mode
                self.assertFailure(self.append(), expected)
                self.assertEqual(self.snapshot(), before)
        self.event_mode = 'ok'
        self.assertTrue(self.append().ok)

    def test_invalidation_failure_exception_and_malformed_result_restore_availability(self):
        ref = self.ref()
        before = self.snapshot()
        failures = [('raise', 'unavailable'), ('failure', 'unavailable'),
                    ({'work_refs': []}, 'unavailable'),
                    (Result.success({'work_refs': [None]}), 'unavailable'),
                    (Result.success({'work_refs': [] , 'extra': 1}), 'unavailable'),
                    (Result.success({'work_refs': [{'goal_id': 'g', 'revision': True, 'epoch': 0}]}), 'unavailable')]
        for mode, expected in failures:
            self.invalidate_mode = mode
            self.assertFailure(self.stop(ref), expected)
            self.assertEqual(self.snapshot(), before)
            self.assertTrue(self.store.read({'ref': ref}, purpose='model_context').ok)
        self.invalidate_mode = 'ok'
        self.assertTrue(self.stop(ref).ok)

    def test_failed_callback_payloads_are_bounded_without_secret_text_or_refs(self):
        ref = self.ref()
        before = self.snapshot()
        secret_failure = Result.failure('conflict', 'SENTINEL' * 1000,
                                        [Ref('record', 'SENTINEL-private-ref')])
        self.invalidate_mode = secret_failure
        result = self.stop(ref)
        self.assertFailure(result, 'conflict')
        self.assertEqual(result.error.refs, ())
        self.assertEqual(self.snapshot(), before)
        self.invalidate_mode = 'ok'
        self.event_mode = secret_failure
        self.assertFailure(self.append('new'), 'conflict')
        self.assertEqual(self.snapshot(), before)

    def test_stop_event_failure_rolls_back_prior_callback_writes(self):
        ref = self.ref()
        before = self.snapshot()
        self.event_mode = 'raise'
        self.assertFailure(self.stop(ref), 'unavailable')
        self.assertEqual(self.snapshot(), before)
        self.event_mode = 'ok'
        self.assertTrue(self.stop(ref).ok)

    def test_search_recent_literal_order_truncation_and_stopped_exclusion(self):
        first = self.ref('first', text='match 日本')
        second = self.ref('second', text='match %_')
        third = self.ref('third', text='match latest')
        self.ref('different-session', text='match', session='other')
        self.assertTrue(self.stop(third).ok)
        def search(query='', limit=1):
            return self.store.search({'query': query, 'session_id': 'session', 'limit': limit}).value.to_json()
        self.assertEqual(search(), {'summaries': [], 'record_refs': [second], 'truncated': True})
        self.assertEqual(search(limit=2), {'summaries': [], 'record_refs': [second, first], 'truncated': False})
        self.assertEqual(search('%_'), {'summaries': [], 'record_refs': [second], 'truncated': False})
        self.assertEqual(search('MATCH'), {'summaries': [], 'record_refs': [], 'truncated': False})
        self.assertEqual(search('日本'), {'summaries': [], 'record_refs': [first], 'truncated': False})
        self.assertEqual(search('absent'), {'summaries': [], 'record_refs': [], 'truncated': False})

    def test_search_bounds_and_unimplemented_work_filter_are_explicit(self):
        for limit in [0, -1, 51, True, 1.0, '1', None, 2 ** 80]:
            self.assertFailure(self.store.search({'query': '', 'session_id': 's', 'limit': limit}), 'invalid_input')
        base = {'query': '', 'session_id': 's', 'limit': 50}
        self.assertTrue(self.store.search(base).ok)
        self.assertFailure(self.store.search({**base, 'work_ref': {'goal_id': 'g', 'revision': 1, 'epoch': 0}}), 'unavailable')
        self.assertFailure(self.store.search({**base, 'work_ref': {'goal_id': 'g', 'revision': 0, 'epoch': 0}}), 'invalid_input')

    def test_source_gate_bound_connection_types_order_and_read_only(self):
        available = Ref.from_json(self.ref())
        stopped = Ref.from_json(self.ref('stopped'))
        self.assertTrue(self.stop(stopped.to_json()).ok)
        unknown = Ref('record', 'missing')
        foreign = Ref('source', 'other-owner')
        self.assertEqual(self.store.source_gate(self.conn, (available,)), 'unavailable')
        other = self.connect()
        self.conn.execute('BEGIN IMMEDIATE')
        before = self.snapshot()
        changes = self.conn.total_changes
        try:
            for refs, expected in [((), 'available'), ((available,), 'available'),
                                   ((unknown, stopped), 'not_found'), ((stopped, unknown), 'denied'),
                                   ((foreign, stopped), 'unavailable'), ([available], 'unavailable'),
                                   ((available.to_json(),), 'unavailable')]:
                self.assertEqual(self.store.source_gate(self.conn, refs), expected)
            self.assertEqual(self.store.source_gate(other, (available,)), 'unavailable')
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.conn.total_changes, changes)
            self.assertTrue(self.conn.in_transaction)
        finally:
            self.conn.rollback()

    def test_busy_mutations_return_unavailable_and_can_retry(self):
        ref = self.ref('previous')
        before = self.snapshot()
        other = self.connect()
        other.execute('BEGIN IMMEDIATE')
        self.assertFailure(self.append(), 'unavailable')
        self.assertFailure(self.stop(ref), 'unavailable')
        other.rollback()
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.append().ok)
        self.assertTrue(self.stop(ref).ok)

    def test_read_owner_missing_purpose_and_selection_does_not_cache_availability(self):
        ref = self.ref()
        selected = self.store.search({'query': '', 'session_id': 'session', 'limit': 1}).value.to_json()['record_refs'][0]
        self.assertTrue(self.stop(ref).ok)
        self.assertFailure(self.store.read({'ref': selected}, purpose='model_context'), 'denied')
        self.assertFailure(self.store.read({'ref': {'kind': 'record', 'id': 'missing'}}, purpose='user_view'), 'not_found')
        self.assertFailure(self.store.read({'ref': {'kind': 'note', 'id': 'x'}}, purpose='user_view'), 'unavailable')
        self.assertFailure(self.store.read({'ref': {'kind': 'Record', 'id': 'x'}}, purpose='user_view'), 'invalid_input')
        for purpose in [None, 'model', 1]:
            with self.assertRaises(ValueError):
                self.store.read({'ref': ref}, purpose=purpose)

    def test_strict_inputs_fail_before_effects_and_do_not_echo(self):
        valid = {'client_key': 'key', 'session_id': 's', 'role': 'user', 'text': ''}
        bad = [None, [], 'raw json', {**valid, 'SENTINEL': 1}]
        for key in valid:
            item = valid.copy(); del item[key]; bad.append(item)
        for key, value in [('client_key', ''), ('session_id', True), ('role', 'system'),
                           ('text', '\ud800'), ('text', b'bytes')]:
            bad.append({**valid, key: value})
        before = self.snapshot()
        for item in bad:
            self.assertFailure(self.store.append(item), 'invalid_input')
        self.assertFailure(self.store.stop_reference({'key': 'k', 'source_ref': {'kind': 'source', 'id': 'x'}}, session_id='s'), 'invalid_input')
        self.assertFailure(self.store.stop_reference({'key': 'k', 'source_ref': {'kind': 'record', 'id': 'x'}}, session_id=''), 'invalid_input')
        self.assertFailure(self.store.read({'ref': {'kind': 'record', 'id': ''}}, purpose='user_view'), 'invalid_input')
        self.assertFailure(self.store.search({'query': [], 'session_id': 's', 'limit': 1}), 'invalid_input')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.event_calls, [])

    def test_factory_collision_clock_failure_and_no_partial_append(self):
        ref = self.ref('previous')
        before = self.snapshot()
        for config in [dict(id_factory=lambda prefix: ref['id']), dict(id_factory=lambda prefix: ''),
                       dict(clock=lambda: ''), dict(clock=lambda: '\ud800'), dict(clock=lambda: 1)]:
            self.store = self.make_store(**config)
            self.assertFailure(self.append(), 'unavailable')
            self.assertEqual(self.snapshot(), before)
        self.store = self.make_store()
        self.assertTrue(self.append().ok)

    def test_constructor_and_nested_mutation_configuration_errors(self):
        for config in [dict(sanitize_text=None), dict(append_event=None), dict(invalidate_by_refs=None),
                       dict(id_factory=1), dict(clock=1)]:
            with self.assertRaises(TypeError):
                self.make_store(**config)
        self.conn.execute('BEGIN')
        try:
            with self.assertRaises(ValueError):
                self.make_store()
            with self.assertRaises(ValueError):
                self.append()
            self.assertTrue(self.conn.in_transaction)
        finally:
            self.conn.rollback()
        other = sqlite3.connect(':memory:')
        self.addCleanup(other.close)
        with self.assertRaises(ValueError):
            MemoryStore(other, sanitize_text=sanitize, append_event=self.event, invalidate_by_refs=self.invalidate)
        self.assertEqual(other.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])


if __name__ == '__main__':
    unittest.main()
