import sqlite3
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, Conflict, InvalidTransition, StaleResult, EvidenceRejected


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.db'
        self.store = Store(self.path)

    def goal(self, key='g1'):
        return self.store.create_goal(key, 'Make a local draft', {'kind': 'local_draft', 'max_bytes': 4096})

    def test_duplicate_ingress_returns_original_and_conflicts_are_visible(self):
        first = self.store.record('m1', 'user', 'Hello')
        self.assertEqual(first, self.store.record('m1', 'user', 'Hello'))
        with self.assertRaises(Conflict):
            self.store.record('m1', 'user', 'Different')
        self.assertEqual(len(self.store.inspect()['records']), 1)
        self.assertEqual(self.goal(), self.goal())
        self.assertEqual(len(self.store.inspect()['goals']), 1)

    def test_goal_and_immutable_criteria_and_outbox_are_atomic(self):
        goal = self.goal()
        data = self.store.inspect()
        self.assertEqual(goal['state'], 'queued')
        self.assertEqual(data['revisions'][0]['revision'], 1)
        self.assertEqual(data['events'][0]['kind'], 'goal.queued')
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE revisions SET criteria='{}'")

    def test_single_task_slot_and_fifo_claim(self):
        first, second = self.goal(), self.goal('g2')
        attempt = self.store.claim()
        self.assertEqual(attempt['goal_id'], first['id'])
        self.assertIsNone(self.store.claim())
        self.store.fail(attempt['id'], 'executor failed')
        self.assertEqual(self.store.claim()['goal_id'], second['id'])

    def test_completion_requires_host_receipt_and_dedupes(self):
        goal = self.goal()
        attempt = self.store.claim()
        with self.assertRaises(EvidenceRejected):
            self.store.complete(attempt['id'], 'fabricated')
        receipt = self.store.write_draft(attempt['id'], 'A bounded local draft')
        first = self.store.complete(attempt['id'], receipt['id'])
        self.assertEqual(first, self.store.complete(attempt['id'], receipt['id']))
        self.assertEqual(first['check_status'], 'pass')
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'completed')
        self.assertEqual(len(self.store.inspect()['outcomes']), 1)
        completions = [e for e in self.store.inspect()['events'] if e['kind'] == 'goal.completed']
        self.assertEqual(len(completions), 1)

    def test_artifact_and_receipt_tamper_is_rejected_by_db(self):
        self.goal()
        attempt = self.store.claim()
        receipt = self.store.write_draft(attempt['id'], 'Original')
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE artifacts SET body=?", (b'Tampered',))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM receipts")
        self.assertEqual(self.store.complete(attempt['id'], receipt['id'])['check_status'], 'pass')

    def test_cancel_fences_result_and_invalid_transition(self):
        goal = self.goal()
        attempt = self.store.claim()
        receipt = self.store.write_draft(attempt['id'], 'Draft')
        self.store.control('c1', goal['id'], 'cancel')
        with self.assertRaises(StaleResult):
            self.store.complete(attempt['id'], receipt['id'])
        with self.assertRaises(InvalidTransition):
            self.store.control('r1', goal['id'], 'resume')
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'cancelled')

    def test_outbox_replay_reports_once(self):
        self.goal()
        self.assertEqual(self.store.deliver(), 1)
        reopened = Store(self.path)
        self.assertEqual(reopened.deliver(), 0)
        self.assertEqual(len(reopened.inspect()['records']), 1)

    def test_schema_version_mismatch_fails_closed(self):
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA user_version=900')
        with self.assertRaises(RuntimeError):
            Store(self.path)


if __name__ == '__main__':
    unittest.main()
