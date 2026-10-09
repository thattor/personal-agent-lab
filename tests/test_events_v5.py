"""TSK03/1 tests: EventReader read-only pagination over a real intake ledger.

CO sandbox verification failed before assertions. Root uses the already
authorized host temporary directory; the original failed result is retained.
"""
import os
import sqlite3
import tempfile
import unittest

from pal.contracts_v5 import Grant, Limits
from pal.events_v5 import EventReader
from pal.intake_v5 import IntakeStore

_REPO = 'thattor/personal-agent-lab'


def _grant():
    return Grant(('github.issue.read',), (_REPO,), Limits(10, 20, 20))


def _gate(_connection, _refs):
    return 'available'


def _event(key, session_id, text, *, work_ref=None, kind='progress', refs=()):
    request = {'key': key, 'session_id': session_id, 'kind': kind,
               'text': text, 'refs': list(refs)}
    if work_ref is not None:
        request['work_ref'] = work_ref
    return request


class _Ledger:
    def __init__(self, path):
        self.path = path
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.store = IntakeStore(self.connection, host_grant=_grant(),
                                 expert_id='expert-1', source_gate=_gate)

    def close(self):
        self.connection.close()


class EventReaderTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _open(self, name='ledger.sqlite3'):
        ledger = _Ledger(os.path.join(self._tmp.name, name))
        self.addCleanup(ledger.close)
        return ledger

    def _connect(self, path):
        connection = sqlite3.connect(path, isolation_level=None)
        self.addCleanup(connection.close)
        return connection

    def _create(self, ledger, key, session_id):
        request = {'key': key, 'session_id': session_id,
                   'origin_record_ref': {'kind': 'record', 'id': f'{key}-origin'},
                   'brief': {
                       'purpose': 'exercise the event ledger',
                       'target': {'repository': _REPO, 'issue_numbers': [7], 'files': []},
                       'constraints': [],
                       'conditions': [{'description': 'events readable',
                                       'check': 'semantic'}],
                       'context_refs': [],
                   }}
        result = ledger.store.create(request, request_scope=_grant())
        self.assertTrue(result.ok, result.to_json())
        return result.to_json()['value']['work_ref']

    def _append(self, ledger, request):
        connection = ledger.connection
        connection.execute('BEGIN IMMEDIATE')
        try:
            result = ledger.store.append_event(connection, request)
        except BaseException:
            connection.execute('ROLLBACK')
            raise
        if result.ok:
            connection.execute('COMMIT')
        else:
            connection.execute('ROLLBACK')
        self.assertTrue(result.ok, result.to_json())
        return result.to_json()['value']['event_id']

    def _ids(self, connection, session_id):
        rows = connection.execute('SELECT event_id FROM v5_intake_event'
                                  ' WHERE session_id = ? ORDER BY seq',
                                  (session_id,)).fetchall()
        return [row[0] for row in rows]

    def test_pages_resume_exactly_across_mixed_sessions(self):
        ledger = self._open()
        work_a = self._create(ledger, 'create-a', 'session-a')
        work_b = self._create(ledger, 'create-b', 'session-b')
        for index in range(4):
            self._append(ledger, _event(f'a-{index}', 'session-a', f'a text {index}',
                                        work_ref=work_a))
            self._append(ledger, _event(f'b-{index}', 'session-b', f'b text {index}',
                                        work_ref=work_b))
        expected = self._ids(ledger.connection, 'session-a')
        self.assertEqual(len(expected), 5)
        reader = EventReader(ledger.connection, page_size=2)
        seen = []
        cursor = None
        for _ in range(10):
            request = {'session_id': 'session-a'}
            if cursor is not None:
                request['after_event_id'] = cursor
            result = reader.get_events(request)
            self.assertTrue(result.ok, result.to_json())
            value = result.to_json()['value']
            self.assertEqual(set(value), {'events', 'next_cursor'})
            for event in value['events']:
                self.assertLessEqual(set(event),
                                     {'event_id', 'work_ref', 'kind', 'text', 'refs'})
                self.assertIn('work_ref', event)
            if not value['events']:
                self.assertEqual(value['next_cursor'], cursor)
                break
            self.assertLessEqual(len(value['events']), 2)
            self.assertEqual(value['next_cursor'], value['events'][-1]['event_id'])
            seen.extend(event['event_id'] for event in value['events'])
            cursor = value['next_cursor']
        else:
            self.fail('pagination did not terminate')
        self.assertEqual(seen, expected)
        self.assertEqual(len(seen), len(set(seen)))

    def test_initial_empty_session_returns_null_cursor(self):
        ledger = self._open()
        self._create(ledger, 'create', 'other-session')
        result = EventReader(ledger.connection).get_events({'session_id': 'session'})
        self.assertTrue(result.ok)
        self.assertEqual(result.to_json()['value'], {'events': [], 'next_cursor': None})

    def test_unknown_and_foreign_session_cursor_not_found(self):
        ledger = self._open()
        self._create(ledger, 'create-a', 'session-a')
        work_b = self._create(ledger, 'create-b', 'session-b')
        foreign = self._append(ledger, _event('b-1', 'session-b', 'b', work_ref=work_b))
        reader = EventReader(ledger.connection)
        for cursor in ('missing-cursor', '1', foreign):
            with self.subTest(cursor=cursor):
                result = reader.get_events({'session_id': 'session-a',
                                            'after_event_id': cursor})
                self.assertFalse(result.ok)
                self.assertEqual(result.to_json()['error']['code'], 'not_found')

    def test_unicode_empty_text_and_historical_workref(self):
        ledger = self._open()
        work = self._create(ledger, 'create', 'session')
        self._append(ledger, _event('unicode', 'session', '日本語の本文 🐈',
                                    work_ref=work, kind='result',
                                    refs=[{'kind': 'artifact', 'id': 'art-1'}]))
        self._append(ledger, _event('empty', 'session', '', kind='state'))
        ledger.connection.execute('UPDATE v5_intake_work SET epoch = 9 WHERE goal_id = ?',
                                  (work['goal_id'],))
        value = EventReader(ledger.connection).get_events(
            {'session_id': 'session'}).to_json()['value']
        accepted, unicode_event, empty_event = value['events']
        self.assertEqual(accepted['kind'], 'accepted')
        self.assertEqual(unicode_event['text'], '日本語の本文 🐈')
        self.assertEqual(unicode_event['kind'], 'result')
        self.assertEqual(unicode_event['work_ref'], work)
        self.assertEqual(unicode_event['refs'], [{'kind': 'artifact', 'id': 'art-1'}])
        self.assertEqual(empty_event['text'], '')
        self.assertNotIn('work_ref', empty_event)
        self.assertEqual(value['next_cursor'], empty_event['event_id'])

    def test_reopen_recovers_persisted_events(self):
        ledger = self._open('reopen.sqlite3')
        work = self._create(ledger, 'create', 'session')
        self._append(ledger, _event('one', 'session', 'first', work_ref=work))
        expected = self._ids(ledger.connection, 'session')
        ledger.close()
        connection = self._connect(ledger.path)
        value = EventReader(connection).get_events(
            {'session_id': 'session'}).to_json()['value']
        self.assertEqual([event['event_id'] for event in value['events']], expected)
        self.assertEqual(connection.total_changes, 0)

    def test_strict_request_validation(self):
        ledger = self._open()
        reader = EventReader(ledger.connection)
        bad_requests = (
            None, 42, 'session', [], {'unexpected': 1}, {},
            {'session_id': ''}, {'session_id': None}, {'session_id': 7},
            {'session_id': 's', 'after_event_id': None},
            {'session_id': 's', 'after_event_id': ''},
            {'session_id': 's', 'after_event_id': 3},
            {'session_id': 's', 'after_event_id': 'e', 'extra': 'x'},
            {'session_id': 's', 1: 'x'},
            {'session_id': '\ud800'},
            {'session_id': 's', 'after_event_id': '\ud800'},
        )
        for request in bad_requests:
            with self.subTest(request=repr(request)):
                result = reader.get_events(request)
                self.assertFalse(result.ok)
                self.assertEqual(result.to_json()['error']['code'], 'invalid_input')

    def test_constructor_rejects_bad_config(self):
        ledger = self._open()
        for bad in (None, 'dsn', object()):
            with self.subTest(connection=repr(bad)):
                with self.assertRaises(TypeError):
                    EventReader(bad)
        for bad in ('100', 1.5, True, None):
            with self.subTest(page_size=repr(bad)):
                with self.assertRaises(TypeError):
                    EventReader(ledger.connection, page_size=bad)
        for bad in (0, -1, 1001):
            with self.subTest(page_size=bad):
                with self.assertRaises(ValueError):
                    EventReader(ledger.connection, page_size=bad)
        EventReader(ledger.connection, page_size=1)
        EventReader(ledger.connection, page_size=1000)

    def test_missing_ledger_is_bounded_unavailable(self):
        connection = self._connect(os.path.join(self._tmp.name, 'empty.sqlite3'))
        reader = EventReader(connection)
        result = reader.get_events({'session_id': 'session'})
        self.assertFalse(result.ok)
        self.assertEqual(result.to_json()['error']['code'], 'unavailable')
        result = reader.get_events({'session_id': 'session', 'after_event_id': 'e-1'})
        self.assertFalse(result.ok)
        self.assertEqual(result.to_json()['error']['code'], 'unavailable')

    def test_corrupt_stored_rows_are_bounded_unavailable(self):
        corrupt_rows = (
            ('bad-work', '{"goal_id":1}', 'progress', 't', '[]'),
            ('bad-kind', None, 'bogus', 't', '[]'),
            ('bad-refs', None, 'progress', 't', 'not json'),
            ('refs-object', None, 'progress', 't', '{}'),
            ('refs-bad-item', None, 'progress', 't', '[{"kind":"bogus","id":"x"}]'),
            ('', None, 'progress', 't', '[]'),
        )
        for index, row in enumerate(corrupt_rows):
            with self.subTest(row=row[0]):
                ledger = self._open(f'corrupt-{index}.sqlite3')
                self._create(ledger, 'create', 'session')
                ledger.connection.execute(
                    'INSERT INTO v5_intake_event'
                    ' (event_id, session_id, work_ref_json, kind, text, refs_json)'
                    ' VALUES (?, ?, ?, ?, ?, ?)', (*row[:1], 'session', *row[1:]))
                result = EventReader(ledger.connection).get_events(
                    {'session_id': 'session'})
                self.assertFalse(result.ok)
                self.assertEqual(result.to_json()['error']['code'], 'unavailable')

    def test_reads_preserve_caller_transaction_and_writes(self):
        ledger = self._open()
        work = self._create(ledger, 'create', 'session')
        committed = self._ids(ledger.connection, 'session')
        connection = ledger.connection
        connection.execute('BEGIN IMMEDIATE')
        try:
            pending = ledger.store.append_event(
                connection, _event('pending', 'session', 'inside transaction',
                                   work_ref=work))
            self.assertTrue(pending.ok, pending.to_json())
            pending_id = pending.to_json()['value']['event_id']
            before = connection.total_changes
            value = EventReader(connection).get_events(
                {'session_id': 'session'}).to_json()['value']
            self.assertIn(pending_id, [event['event_id'] for event in value['events']])
            self.assertTrue(connection.in_transaction)
            self.assertEqual(connection.total_changes, before)
        finally:
            connection.execute('ROLLBACK')
        self.assertFalse(connection.in_transaction)
        value = EventReader(connection).get_events(
            {'session_id': 'session'}).to_json()['value']
        self.assertEqual([event['event_id'] for event in value['events']], committed)


if __name__ == '__main__':
    unittest.main()
