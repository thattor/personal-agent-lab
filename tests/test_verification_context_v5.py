"""Actual TSK readonly verification authority and stored-condition snapshots."""
import copy
import sqlite3
import unittest

from pal.contracts_v5 import Grant, Limits, dumps, loads
from pal.tasks_v5 import TaskStore


class VerificationContextTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(self.conn.close)
        self.grant = Grant(('github.issue.read',), ('repo',), Limits(0, 8, 8))
        self.tasks = TaskStore(self.conn, host_grant=self.grant, expert_id='expert',
            host_limits=Limits(0, 20, 20), source_gate=lambda c, refs: 'available')
        self.request = {'key': 'goal', 'session_id': 's',
            'origin_record_ref': {'kind': 'record', 'id': 'origin'},
            'brief': {'purpose': 'draft', 'target': {'repository': 'repo', 'issue_numbers': [], 'files': []},
                'constraints': [], 'context_refs': [{'kind': 'record', 'id': 'required'}],
                'conditions': [{'description': 'draft stored', 'check': 'artifact_saved'},
                               {'description': 'wording useful', 'check': 'semantic'}]}}
        self.work = self.value(self.tasks.create(self.request, request_scope=self.grant))['work_ref']

    def value(self, result):
        self.assertTrue(result.ok, result.to_json())
        return result.value.to_json()

    def error(self, result, code):
        self.assertFalse(result.ok, result.to_json())
        self.assertEqual(result.error.code, code)

    def snapshot(self, work=None, purpose='status'):
        self.conn.execute('BEGIN')
        try:
            return self.tasks.verification_context(self.conn, {'work_ref': work or self.work}, purpose=purpose)
        finally:
            self.assertTrue(self.conn.in_transaction)
            self.conn.rollback()

    def claim(self):
        claim = self.value(self.tasks.claim({'runner_id': 'ver-host'}))
        self.work = claim['work_ref']
        return claim

    def test_queued_status_is_readonly_but_does_not_grant_save(self):
        before = self.conn.total_changes
        current = self.value(self.snapshot())
        self.assertEqual(set(current), {'work_ref', 'conditions', 'artifact_refs', 'source_refs'})
        self.assertEqual(current['work_ref'], self.work)
        self.assertEqual([c['check'] for c in current['conditions']], ['artifact_saved', 'semantic'])
        self.assertEqual(len({c['id'] for c in current['conditions']}), 2)
        self.assertEqual(current['source_refs'], [self.request['origin_record_ref'], *self.request['brief']['context_refs']])
        self.assertEqual(current['artifact_refs'], [])
        self.assertEqual(before, self.conn.total_changes)
        self.error(self.snapshot(purpose='save'), 'denied')

    def test_running_snapshot_omits_registered_optional_input(self):
        self.claim()
        self.value(self.tasks.register_sources({'work_ref': self.work,
            'refs': [{'kind': 'record', 'id': 'optional'}]}))
        current = self.value(self.snapshot(purpose='save'))
        self.assertEqual(len(current['source_refs']), 2)
        self.assertNotIn({'kind': 'record', 'id': 'optional'}, current['source_refs'])
        self.assertEqual(current, self.value(self.snapshot()))

    def test_pause_and_release_preserve_factual_snapshot_and_deny_new_save(self):
        claim = self.claim()
        original = self.value(self.snapshot(purpose='save'))
        self.value(self.tasks.control({'key': 'pause', 'work_ref': self.work, 'command': 'pause'}))
        self.error(self.snapshot(purpose='save'), 'conflict')
        self.assertEqual(self.value(self.snapshot()), original)
        self.value(self.tasks.release({'lease_id': claim['lease_id'], 'work_ref': self.work,
            'outcome': 'yield', 'reason': 'pause'}))
        self.assertEqual(self.value(self.snapshot()), original)
        self.error(self.snapshot(purpose='save'), 'denied')

    def test_old_epoch_and_unknown_goal_keep_specific_errors(self):
        old = copy.deepcopy(self.work)
        self.claim()
        self.error(self.snapshot(old), 'stale')
        self.error(self.snapshot({**self.work, 'goal_id': 'missing'}), 'not_found')
        self.value(self.tasks.control({'key': 'cancel', 'work_ref': self.work, 'command': 'cancel'}))
        self.error(self.snapshot(), 'stale')

    def test_closed_request_and_host_purpose_are_validated(self):
        for purpose in ('future', None, True):
            self.error(self.snapshot(purpose=purpose), 'invalid_input')
        self.conn.execute('BEGIN')
        try:
            self.error(self.tasks.verification_context(self.conn,
                {'work_ref': self.work, 'extra': True}, purpose='status'), 'invalid_input')
            self.error(self.tasks.verification_context(self.conn,
                {'work_ref': {**self.work, 'epoch': True}}, purpose='status'), 'invalid_input')
        finally:
            self.conn.rollback()

    def test_collaborator_preconditions_preserve_caller_work(self):
        with self.assertRaises(ValueError):
            self.tasks.verification_context(self.conn, {'work_ref': self.work}, purpose='status')
        other = sqlite3.connect(':memory:', isolation_level=None)
        self.addCleanup(other.close)
        other.execute('BEGIN')
        with self.assertRaises(ValueError):
            self.tasks.verification_context(other, {'work_ref': self.work}, purpose='status')
        self.assertTrue(other.in_transaction)
        self.conn.execute('CREATE TABLE caller(value TEXT)')
        self.conn.execute('BEGIN')
        self.conn.execute("INSERT INTO caller VALUES ('retained')")
        changes = self.conn.total_changes
        self.value(self.tasks.verification_context(self.conn, {'work_ref': self.work}, purpose='status'))
        self.assertEqual(self.conn.total_changes, changes)
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        self.assertEqual(self.conn.execute('SELECT count(*) FROM caller').fetchone()[0], 0)

    def test_corrupt_stored_conditions_and_required_index_are_unavailable(self):
        original = self.conn.execute('SELECT brief_json FROM v5_intake_work').fetchone()[0]
        bad = loads(original)
        bad['conditions'][1]['id'] = bad['conditions'][0]['id']
        for stored in ('{', dumps(bad), dumps({**loads(original), 'conditions': [{'id': True}]})):
            self.conn.execute('UPDATE v5_intake_work SET brief_json=?', (stored,))
            self.error(self.snapshot(), 'unavailable')
        self.conn.execute('UPDATE v5_intake_work SET brief_json=?', (original,))
        self.conn.execute("DELETE FROM v5_intake_source WHERE id='required'")
        self.error(self.snapshot(), 'unavailable')

    def test_factual_status_rejects_unknown_saved_state(self):
        for state in ('queued', 'running', 'paused', 'waiting_input', 'completed', 'cancelled', 'failed'):
            self.conn.execute('UPDATE v5_intake_work SET state=?', (state,))
            self.value(self.snapshot())
        self.conn.execute("UPDATE v5_intake_work SET state='not-a-work-state'")
        self.error(self.snapshot(), 'unavailable')


if __name__ == '__main__':
    unittest.main()
