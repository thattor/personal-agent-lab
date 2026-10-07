import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pal.store import Store, EvidenceRejected, StaleResult, Conflict, QuestionBudgetExhausted, PREVIEW_BANNER


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'state.db')
        self.source = self.store.record('source', 'user', 'Invitation context')
        self.goal = self.store.create_goal('goal', 'Draft invitation',
                                          {'kind': 'local_draft', 'max_bytes': 4096})

    def exhausted_attempt(self):
        for index in (1, 2):
            attempt = self.store.claim([self.source['id']])
            goal = self.store.waiting(attempt['id'], 'What date should it use?')
            self.store.control('answer' + str(index), goal['id'], 'input', 'Still undecided',
                               question_id=goal['question_id'], epoch=goal['epoch'])
        return self.store.claim([self.source['id']])

    def test_terminal_receipt_is_unverified_and_never_recovered_or_passed(self):
        attempt = self.exhausted_attempt()
        result = self.store.finish_preview(attempt['id'], 'clarification_exhausted')
        data = self.store.inspect()
        receipt = data['receipts'][0]
        body = self.store.artifact(receipt['artifact_id'])
        self.assertTrue(body.startswith(PREVIEW_BANNER.encode('utf-8')))
        self.assertIn(b'What date should it use?', body)
        self.assertEqual((receipt['role'], receipt['hash'], receipt['size']),
                         ('preview', hashlib.sha256(body).hexdigest(), len(body)))
        self.assertEqual(result['check_status'], 'unverified')
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'failed')
        self.assertEqual(self.store.get_goal(self.goal['id'])['reason'], 'clarification_exhausted')
        self.assertIsNone(self.store.claim())
        self.assertEqual(Store(self.store.path).recover(), [])
        with self.assertRaises((Conflict, EvidenceRejected)):
            self.store.complete(attempt['id'], receipt['id'])
        self.assertFalse(any(e['kind'] == 'goal.completed' for e in data['events']))
        self.assertEqual(sum(e['kind'] == 'goal.incomplete_preview' for e in data['events']), 1)
        self.assertEqual(self.store.finish_preview(attempt['id'], 'clarification_exhausted'), result)
        self.assertEqual(len(self.store.inspect()['artifacts']), 1)

    def test_early_unauthorized_template_and_nonexhausted_are_rejected(self):
        attempt = self.store.claim()
        for reason, content in [('incomplete_template', 'Invitation {{date}}'),
                                ('clarification_exhausted', None)]:
            with self.assertRaises(EvidenceRejected):
                self.store.finish_preview(attempt['id'], reason, content)
        self.assertEqual(self.store.inspect()['artifacts'], [])
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'running')

    def test_cancel_and_forget_fence_before_any_preview_bytes(self):
        attempt = self.exhausted_attempt()
        self.store.control('cancel', self.goal['id'], 'cancel')
        with self.assertRaises(StaleResult):
            self.store.finish_preview(attempt['id'], 'clarification_exhausted')
        self.assertEqual(self.store.inspect()['artifacts'], [])

    def test_forget_after_preview_retains_bytes_but_marks_reference_stopped(self):
        attempt = self.exhausted_attempt()
        self.store.finish_preview(attempt['id'], 'clarification_exhausted')
        receipt = self.store.inspect()['receipts'][0]
        before = self.store.artifact(receipt['artifact_id'])
        self.assertFalse(self.store.artifact_status(receipt['artifact_id'])['stale'])
        self.store.forget('forget', self.source['id'])
        self.assertEqual(self.store.artifact(receipt['artifact_id']), before)
        self.assertTrue(self.store.artifact_status(receipt['artifact_id'])['stale'])

    def test_forget_before_preview_rejects_all_artifact_writes(self):
        attempt = self.exhausted_attempt()
        self.store.forget('forget', self.source['id'])
        with self.assertRaises(StaleResult):
            self.store.finish_preview(attempt['id'], 'clarification_exhausted')
        self.assertEqual(self.store.inspect()['artifacts'], [])

    def test_process_kill_preview_is_atomic_and_retry_recovers_once(self):
        attempt = self.exhausted_attempt()
        before = self.store.inspect()
        child = '''import os,signal,sys
from pal.store import Store
def fault(point):
    if point == 'preview.mid_transaction': os.kill(os.getpid(), signal.SIGKILL)
s=Store(sys.argv[1],fault=fault)
s.finish_preview(sys.argv[2],'clarification_exhausted')
'''
        result = subprocess.run([sys.executable, '-c', child, self.store.path, attempt['id']],
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, -9, result.stderr)
        self.assertEqual(self.store.inspect(), before)
        first = self.store.finish_preview(attempt['id'], 'clarification_exhausted')
        self.assertEqual(self.store.finish_preview(attempt['id'], 'clarification_exhausted'), first)

    def test_kill_after_commit_replays_complete_terminal_transaction_once(self):
        attempt = self.exhausted_attempt()
        child = '''import os,signal,sys
from pal.store import Store
def fault(point):
    if point == 'preview.after_commit': os.kill(os.getpid(), signal.SIGKILL)
s=Store(sys.argv[1],fault=fault)
s.finish_preview(sys.argv[2],'clarification_exhausted')
'''
        killed = subprocess.run([sys.executable, '-c', child, self.store.path, attempt['id']],
                                capture_output=True, timeout=15)
        self.assertEqual(killed.returncode, -9, killed.stderr)
        reopened = Store(self.store.path)
        self.assertEqual(reopened.recover(), [])
        before = reopened.inspect()
        result = reopened.finish_preview(attempt['id'], 'clarification_exhausted')
        self.assertEqual(result, before['outcomes'][0])
        self.assertEqual(reopened.inspect(), before)
        self.assertEqual(len(before['artifacts']), 1)
        self.assertEqual(len(before['receipts']), 1)

    def test_exhaustion_fallback_accepts_no_model_content_or_banner_spoof(self):
        attempt = self.exhausted_attempt()
        with self.assertRaises(EvidenceRejected):
            self.store.finish_preview(attempt['id'], 'clarification_exhausted', 'Model final claim')
        self.assertEqual(self.store.inspect()['artifacts'], [])

    def template_fixture(self):
        # Authored immutable host-eligible revision, not an intake classifier or live DB.
        with sqlite3.connect(self.store.path) as db:
            db.execute("INSERT INTO revisions(goal_id,revision,acceptance_id,specification,sources,criteria,template_preview_allowed) SELECT goal_id,2,acceptance_id,'Blank template',sources,criteria,1 FROM revisions WHERE goal_id=? AND revision=1", (self.goal['id'],))
            db.execute('UPDATE goals SET revision=2 WHERE id=?', (self.goal['id'],))
        return self.store.claim()

    def test_template_role_literal_placeholders_bounds_and_conflicting_replay(self):
        attempt = self.template_fixture()
        for content, missing in [('Invitation {{date}}', 'Date missing'),
                                 ('Invitation {{date', 'Date missing'),
                                 (PREVIEW_BANNER + 'Invitation', 'Date missing'),
                                 ('x' * 4096, 'Date missing')]:
            with self.assertRaises(EvidenceRejected):
                self.store.finish_preview(attempt['id'], 'incomplete_template', content, missing)
        self.assertEqual(self.store.inspect()['artifacts'], [])
        result = self.store.finish_preview(attempt['id'], 'incomplete_template',
                                          'Invitation {{date}}', 'Date: {{date}}')
        self.assertEqual(self.store.finish_preview(attempt['id'], 'incomplete_template',
                                                   'Invitation {{date}}', 'Date: {{date}}'), result)
        with self.assertRaises(Conflict):
            self.store.finish_preview(attempt['id'], 'incomplete_template',
                                      'Other {{date}}', 'Date: {{date}}')
        self.assertEqual(len(self.store.inspect()['artifacts']), 1)

    def test_last_claim_eligibility_is_not_a_fabricated_answer(self):
        for index in (1, 2):
            attempt = self.store.claim()
            self.store.fail(attempt['id'], 'check' + str(index), 'unverified')
        final = self.store.claim()
        self.assertEqual(self.store.get_goal(self.goal['id'])['budget'], 0)
        before = self.store.inspect()
        with self.assertRaises(QuestionBudgetExhausted):
            self.store.waiting(final['id'], 'Unanswerable last-claim question')
        self.assertEqual(self.store.inspect(), before)
        result = self.store.finish_preview(final['id'], 'clarification_exhausted')
        self.assertEqual(result['check_status'], 'unverified')
        self.assertEqual(self.store.inspect()['questions'], [])

    def test_atomic_dispatch_asks_then_finishes_without_third_question(self):
        first = self.store.claim([self.source['id']])
        self.store.request_clarification(first['id'], 'What date should it use?')
        goal = self.store.get_goal(self.goal['id'])
        self.assertEqual(goal['state'], 'waiting_input')
        self.assertEqual(len(self.store.inspect()['questions']), 1)
        before = self.store.inspect()
        self.store.request_clarification(first['id'], 'What date should it use?')
        self.assertEqual(self.store.inspect(), before)
        for index in (1, 2):
            self.store.control('answer' + str(index), goal['id'], 'input', 'Still undecided',
                               question_id=goal['question_id'], epoch=goal['epoch'])
            attempt = self.store.claim([self.source['id']])
            self.store.request_clarification(attempt['id'], 'What date should it use?')
            goal = self.store.get_goal(self.goal['id'])
        self.assertEqual(goal['state'], 'failed')
        data = self.store.inspect()
        self.assertEqual(len(data['questions']), 2)
        self.assertEqual(len(data['receipts']), 1)
        before = self.store.inspect()
        self.store.request_clarification(attempt['id'], 'What date should it use?')
        self.assertEqual(self.store.inspect(), before)

    def test_atomic_dispatch_kill_at_exhaustion_has_no_stranded_question(self):
        attempt = self.exhausted_attempt()
        child = "import os,signal,sys\nfrom pal.store import Store\ndef fault(point):\n    if point == 'preview.mid_transaction': os.kill(os.getpid(), signal.SIGKILL)\ns=Store(sys.argv[1],fault=fault)\ns.request_clarification(sys.argv[2],'Another question')\n"
        before = self.store.inspect()
        killed = subprocess.run([sys.executable, '-c', child, self.store.path, attempt['id']],
                                capture_output=True, timeout=15)
        self.assertEqual(killed.returncode, -9, killed.stderr)
        self.assertEqual(self.store.inspect(), before)
        self.store.request_clarification(attempt['id'], 'Another question')
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'failed')
        self.assertEqual(len(self.store.inspect()['questions']), 2)

    def test_concurrent_dispatch_is_one_question_or_one_preview(self):
        from concurrent.futures import ThreadPoolExecutor
        attempt = self.store.claim([self.source['id']])
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.store.request_clarification(attempt['id'], 'What date?'), range(2)))
        self.assertEqual(len(self.store.inspect()['questions']), 1)
        goal = self.store.get_goal(self.goal['id'])
        for index in (1, 2):
            self.store.control('answer' + str(index), goal['id'], 'input', 'Still undecided',
                               question_id=goal['question_id'], epoch=goal['epoch'])
            attempt = self.store.claim([self.source['id']])
            if index == 1:
                self.store.request_clarification(attempt['id'], 'What date?')
                goal = self.store.get_goal(self.goal['id'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: self.store.request_clarification(attempt['id'], 'Another question'), range(2)))
        data = self.store.inspect()
        self.assertEqual(len(data['questions']), 2)
        self.assertEqual(len(data['receipts']), 1)
        self.assertEqual(sum(e['kind'] == 'goal.incomplete_preview' for e in data['events']), 1)
