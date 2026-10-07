import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, InvalidTransition, QuestionBudgetExhausted


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'state.db')
        self.source = self.store.record('source', 'user', 'Invitation context')
        self.goal = self.store.create_goal('goal', 'Make an invitation',
                                          {'kind': 'local_draft', 'max_bytes': 4096})

    def ask(self):
        attempt = self.store.claim([self.source['id']])
        goal = self.store.waiting(attempt['id'], 'What date should it use?')
        return attempt, goal

    def answer(self, goal, key='answer'):
        return self.store.control(key, goal['id'], 'input', 'Friday',
                                  question_id=goal['question_id'], epoch=goal['epoch'])

    def test_question_answer_restart_and_replay_provenance(self):
        attempt, goal = self.ask()
        row = self.store.inspect()['questions'][0]
        before_replay = self.store.inspect()
        self.assertEqual(self.store.waiting(attempt['id'], 'What date should it use?'), goal)
        self.assertEqual(self.store.inspect(), before_replay)
        self.assertEqual((row['id'], row['attempt_id'], row['revision'], row['epoch']),
                         (goal['question_id'], attempt['id'], goal['revision'], goal['epoch']))
        restarted = Store(self.store.path)
        self.assertEqual(restarted.recover(), [])
        self.assertEqual(restarted.get_goal(goal['id']), goal)
        first = self.answer(goal)
        self.assertEqual(self.answer(goal), first)
        data = restarted.inspect()
        question = data['questions'][0]
        self.assertEqual(question['status'], 'answered')
        answer = next(r for r in data['records'] if r['id'] == question['answer_record_id'])
        self.assertEqual((answer['role'], answer['content']), ('user', 'Friday'))
        self.assertEqual(data['attempts'][0]['status'], 'fenced')

    def test_two_answers_bound_and_third_request_creates_no_question(self):
        for round_number in (1, 2):
            _, goal = self.ask()
            self.assertEqual(self.store.inspect()['questions'][-1]['round'], round_number)
            self.answer(goal, 'answer' + str(round_number))
        attempt = self.store.claim([self.source['id']])
        before = self.store.inspect()
        with self.assertRaises(QuestionBudgetExhausted):
            self.store.waiting(attempt['id'], 'Another question')
        self.assertEqual(self.store.inspect(), before)
        self.assertEqual(self.store.get_goal(goal['id'])['total_claims'], 3)

    def test_closed_question_round_not_reused_after_correction(self):
        _, old = self.ask()
        self.store.control('correct', old['id'], 'correct', 'Make a different invitation')
        _, new = self.ask()
        rows = self.store.inspect()['questions']
        self.assertEqual([(r['round'], r['status']) for r in rows], [(1, 'closed'), (2, 'open')])
        with self.assertRaises(InvalidTransition):
            self.answer(old)
        self.assertEqual(self.store.get_goal(new['id']), new)

    def test_forget_incidental_waiting_context_closes_question(self):
        _, old = self.ask()
        self.store.forget('forget', self.source['id'])
        data = self.store.inspect()
        self.assertEqual(data['questions'][0]['status'], 'closed')
        self.assertEqual(data['attempts'][0]['status'], 'fenced')
        with self.assertRaises(InvalidTransition):
            self.answer(old)
        self.assertEqual(self.store.inspect(), data)

    def test_binding_immutable_and_one_open_question_per_goal(self):
        _, goal = self.ask()
        with sqlite3.connect(self.store.path) as db:
            row = self.store.inspect()['questions'][0]
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('UPDATE questions SET prompt=? WHERE id=?', ('Tampered', row['id']))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO questions(id,goal_id,attempt_id,revision,epoch,round,prompt,status) VALUES ('other',?,?,?,?,99,'Other','open')",
                           (goal['id'], row['attempt_id'], row['revision'], row['epoch']))

    def test_changed_question_and_stale_answer_never_rebind(self):
        from pal.store import Conflict, StaleResult
        attempt, goal = self.ask()
        before = self.store.inspect()
        with self.assertRaises(Conflict):
            self.store.waiting(attempt['id'], 'A different question')
        self.assertEqual(self.store.inspect(), before)
        self.answer(goal)
        with self.assertRaises(StaleResult):
            self.store.waiting(attempt['id'], 'What date should it use?')
        self.assertEqual(self.store.inspect()['questions'][0]['status'], 'answered')
        with self.assertRaises(InvalidTransition):
            self.answer(goal, 'other answer')

    def test_diagnostic_waits_do_not_fabricate_clarification(self):
        attempt = self.store.claim()
        self.store.fail(attempt['id'], 'not verified', 'unverified')
        attempt = self.store.claim()
        self.store.fail(attempt['id'], 'not verified', 'unverified')
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'waiting_input')
        self.assertEqual(self.store.inspect()['questions'], [])

    def test_question_and_answer_process_kill_roll_back_whole_transaction(self):
        attempt = self.store.claim([self.source['id']])
        child = '''import os, signal, sys
from pal.store import Store
def fault(point):
    if point == sys.argv[2]: os.kill(os.getpid(), signal.SIGKILL)
s = Store(sys.argv[1], fault=fault)
if sys.argv[2] == 'question.mid_transaction':
    s.waiting(sys.argv[3], 'What date?')
else:
    g = s.get_goal(sys.argv[3])
    s.control('answer', g['id'], 'input', 'Friday', question_id=g['question_id'], epoch=g['epoch'])
'''
        for point, identity in [('question.mid_transaction', attempt['id']),
                                ('answer.mid_transaction', self.goal['id'])]:
            before = self.store.inspect()
            result = subprocess.run([sys.executable, '-c', child, self.store.path, point, identity],
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, -9, result.stderr)
            self.assertEqual(self.store.inspect(), before)
            if point.startswith('question'):
                self.store.waiting(attempt['id'], 'What date?')

    def test_preview_receipt_is_not_completion_evidence(self):
        from pal.store import EvidenceRejected
        attempt = self.store.claim()
        with sqlite3.connect(self.store.path) as db:
            # Authored fixture representing a future host-minted preview receipt.
            db.execute("INSERT INTO artifacts VALUES ('preview',?, 'fixture-hash',7)", (b'preview',))
            db.execute("INSERT INTO receipts(id,attempt_id,artifact_id,hash,size,revision,epoch,role) VALUES ('receipt',?,'preview','fixture-hash',7,?,?,'preview')",
                       (attempt['id'], attempt['revision'], attempt['epoch']))
        with self.assertRaisesRegex(EvidenceRejected, 'preview receipt'):
            self.store.complete(attempt['id'], 'receipt')
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'running')
        self.assertEqual(self.store.inspect()['outcomes'], [])
