import json
import sqlite3
import unittest
import test_store
from pal.store import Conflict, InvalidTransition, StaleResult, EvidenceRejected


class ControlMemoryTests(unittest.TestCase):
    setUp = test_store.StoreTests.setUp
    goal = test_store.StoreTests.goal

    def test_pause_resume_dedupe_fences_old_attempt(self):
        goal = self.goal()
        attempt = self.store.claim()
        first = self.store.control('pause', goal['id'], 'pause')
        self.assertEqual(first, self.store.control('pause', goal['id'], 'pause'))
        with self.assertRaises(StaleResult):
            self.store.write_draft(attempt['id'], 'Late')
        self.store.control('resume', goal['id'], 'resume')
        fresh = self.store.claim()
        self.assertGreater(fresh['epoch'], attempt['epoch'])

    def test_correct_revision_reuses_or_replaces_immutable_acceptance(self):
        goal = self.goal()
        attempt = self.store.claim()
        first = self.store.control('fix', goal['id'], 'correct', text='Corrected draft')
        self.assertEqual(first['revision'], 2)
        self.assertEqual(first['acceptance_id'], goal['acceptance_id'])
        with self.assertRaises(StaleResult):
            self.store.write_draft(attempt['id'], 'Late')
        second = self.store.control('criteria', goal['id'], 'correct', text='Short draft', criteria={'kind': 'local_draft', 'max_bytes': 40})
        self.assertNotEqual(second['acceptance_id'], first['acceptance_id'])
        self.assertEqual(len(self.store.inspect()['acceptances']), 2)

    def test_input_question_epoch_dedupe_and_correction_invalidation(self):
        goal = self.goal()
        attempt = self.store.claim()
        waiting = self.store.waiting(attempt['id'], 'Need audience')
        with self.assertRaises(InvalidTransition):
            self.store.control('pause', goal['id'], 'pause')
        answer = dict(text='Colleagues', question_id=waiting['question_id'], epoch=waiting['epoch'])
        first = self.store.control('answer', goal['id'], 'input', **answer)
        self.assertEqual(first, self.store.control('answer', goal['id'], 'input', **answer))
        with self.assertRaises(InvalidTransition):
            self.store.control('answer2', goal['id'], 'input', **answer)
        attempt2 = self.store.claim()
        wait2 = self.store.waiting(attempt2['id'], 'Need title')
        self.store.control('correct', goal['id'], 'correct', text='Changed request')
        with self.assertRaises(InvalidTransition):
            self.store.control('staleanswer', goal['id'], 'input', text='Old answer', question_id=wait2['question_id'], epoch=wait2['epoch'])

    def test_forget_incidental_context_fences_but_does_not_pause(self):
        source = self.store.record('r1', 'user', 'Old context')
        other = self.store.record('r2', 'user', 'Kept context')
        self.store.note('n1', 'Derived note', [source['id'], other['id']])
        goal = self.goal()
        attempt = self.store.claim(self.store.context()['manifest'])
        receipt = self.store.write_draft(attempt['id'], 'Draft using old context')
        self.store.forget('forget', source['id'])
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'queued')
        self.assertEqual(self.store.context()['notes'], [])
        self.assertNotIn(source['id'], self.store.context()['manifest'])
        self.assertEqual(self.store.inspect()['records'][0]['content'], 'Old context')
        with self.assertRaises(StaleResult):
            self.store.complete(attempt['id'], receipt['id'])
        with self.assertRaises(StaleResult):
            self.store.record('reply', 'assistant', 'Old provider response', [source['id']])

    def test_forget_explicit_goal_source_requires_input(self):
        source = self.store.record('r', 'user', 'Task target')
        goal = self.store.create_goal('g', 'Draft this', {'kind': 'local_draft', 'max_bytes': 20}, [source['id']])
        self.store.claim()
        self.store.forget('f', source['id'])
        current = self.store.get_goal(goal['id'])
        self.assertEqual(current['state'], 'waiting_input')
        self.assertEqual(current['reason'], 'reference_stopped')

    def test_conversation_correction_supersedes_and_frees_inflight_slot(self):
        source = self.store.record('r1', 'user', 'Audience is old')
        self.store.note('n', 'Old audience', [source['id']])
        goal = self.goal()
        attempt = self.store.claim([source['id']])
        corrected = self.store.record('r2', 'user', 'Audience is new', supersedes=source['id'])
        self.assertEqual([r['id'] for r in self.store.context()['records']], [corrected['id']])
        self.assertEqual(self.store.context()['notes'], [])
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'queued')
        self.assertIsNotNone(self.store.claim())
        with self.assertRaises(StaleResult):
            self.store.write_draft(attempt['id'], 'Late')

    def test_unverified_budget_is_bounded_and_never_completes(self):
        goal = self.goal()
        for count in range(3):
            attempt = self.store.claim()
            self.store.fail(attempt['id'], 'verifier unavailable', check_status='unverified')
        current = self.store.get_goal(goal['id'])
        self.assertEqual(current['state'], 'waiting_input')
        self.assertEqual(current['budget'], 0)
        self.assertIsNone(self.store.claim())
        self.assertTrue(all(x['check_status'] == 'unverified' for x in self.store.inspect()['outcomes']))

    def test_repeated_restarts_consume_budget_and_fence(self):
        goal = self.goal()
        stale = None
        for count in range(3):
            attempt = self.store.claim()
            stale = stale or attempt
            self.store.recover()
        self.assertEqual(self.store.get_goal(goal['id'])['state'], 'waiting_input')
        self.assertEqual(self.store.get_goal(goal['id'])['budget'], 0)
        with self.assertRaises(StaleResult):
            self.store.write_draft(stale['id'], 'Late')

    def test_invalid_bytes_and_oversize_are_visible_rejections(self):
        self.goal()
        attempt = self.store.claim()
        for content in ('', 'x' * 4097, 'nul\x00', '\ufeffBOM', '\ud800'):
            with self.assertRaises(EvidenceRejected):
                self.store.write_draft(attempt['id'], content)
        self.assertGreaterEqual(len(self.store.inspect()['rejections']), 3)
        self.assertEqual(self.store.inspect()['receipts'], [])

    def test_fk_and_single_slot_constraints_on_fresh_connection(self):
        self.goal()
        attempt = self.store.claim()
        with self.store._connection() as db:
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA synchronous').fetchone()[0], 2)
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO acceptances VALUES (?,?,?)', ('orphan', 'no-goal', '{}'))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO attempts(id,goal_id,revision,acceptance_id,epoch,status,manifest) VALUES (?,?,?,?,?,'running','[]')", ('second', attempt['goal_id'], 1, attempt['acceptance_id'], 3))

    def test_secret_sanitization_precedes_persistence_and_context(self):
        canary = 'sk-' + 'PALCANARY' + 'ABCDEF0123456789'
        self.store.record('secret', 'user', 'api_key=' + canary)
        self.store.note('note', 'token=' + canary, [self.store.inspect()['records'][0]['id']])
        self.store.create_goal('secret_goal', 'password=' + canary, {'kind': 'local_draft', 'max_bytes': 400})
        attempt = self.store.claim(self.store.context()['manifest'])
        receipt = self.store.write_draft(attempt['id'], 'secret=' + canary)
        self.store.complete(attempt['id'], receipt['id'])
        self.store.deliver()
        self.assertNotIn(canary, json.dumps(self.store.inspect()))
        self.assertNotIn(canary, json.dumps(self.store.context()))
        for path in self.path.parent.iterdir():
            if path.is_file():
                self.assertNotIn(canary.encode(), path.read_bytes())
