import tempfile
import unittest
from pathlib import Path
from pal.store import Store, EvidenceRejected, StaleResult

class CitationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name) / 'state.db')
        self.record = self.store.record('source', 'user', 'Meeting Friday. token=sample-secret')
        self.note = self.store.note('note', 'Friday summary', [self.record['id']])
        self.goal = self.store.create_goal('goal', 'Draft invitation', {'kind':'local_draft','max_bytes':4096})
        self.attempt = self.store.claim([self.record['id'], 'note:' + self.note['id']])

    def test_unknown_raw_and_malformed_citations_reject_before_artifact(self):
        cases = [[{'source_id':'unknown','quote':'Friday'}],
                 [{'source_id':self.record['id'],'quote':'sample-secret'}],
                 [{'source_id':self.record['id'],'quote':'Monday'}],
                 [{'source_id':self.note['id'],'quote':'Friday'}],
                 [{'source_id':self.record['id'],'quote':''}],
                 [{'source_id':self.record['id'],'quote':'Friday','authority':'pass'}],
                 'Friday', [{'source_id':self.record['id'],'quote':'Friday'}] * 51]
        for citations in cases:
            with self.assertRaises(EvidenceRejected):
                self.store.write_draft(self.attempt['id'], 'Invitation Friday', citations=citations)
            self.assertEqual(self.store.inspect()['artifacts'], [])
        self.assertTrue(self.store.inspect()['rejections'])

    def test_exact_record_and_prefixed_note_match_stored_sanitized_text(self):
        receipt = self.store.write_draft(self.attempt['id'], 'Invitation Friday', citations=[
            {'source_id':self.record['id'],'quote':'Meeting Friday.'},
            {'source_id':'note:' + self.note['id'],'quote':'Friday summary'}])
        self.assertEqual(self.store.artifact(receipt['artifact_id']), b'Invitation Friday')
        self.store.complete(self.attempt['id'], receipt['id'])
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'completed')

    def test_forget_between_proposal_and_apply_rejects_with_no_bytes(self):
        proposal = [{'source_id':self.record['id'],'quote':'Meeting Friday.'}]
        self.store.forget('forget', self.record['id'])
        with self.assertRaises(StaleResult):
            self.store.write_draft(self.attempt['id'], 'Invitation Friday', citations=proposal)
        self.assertEqual(self.store.inspect()['artifacts'], [])

    def test_question_and_preview_validate_before_state_or_bytes(self):
        bad = [{'source_id':self.record['id'],'quote':'Monday'}]
        for call in (lambda: self.store.waiting(self.attempt['id'], 'What date?', citations=bad),
                     lambda: self.store.request_clarification(self.attempt['id'], 'What date?', citations=bad),
                     lambda: self.store.finish_preview(self.attempt['id'], 'clarification_exhausted', citations=bad)):
            with self.assertRaises(EvidenceRejected): call()
            self.assertEqual(self.store.inspect()['questions'], [])
            self.assertEqual(self.store.inspect()['artifacts'], [])
        self.store.request_clarification(self.attempt['id'], 'What date?', citations=[
            {'source_id':self.record['id'],'quote':'Meeting Friday.'}])
        self.assertEqual(self.store.get_goal(self.goal['id'])['state'], 'waiting_input')

    def test_claim_preserves_bound_answer_after_recent_context_truncation(self):
        goal = self.store.waiting(self.attempt['id'], 'What date?')
        self.store.control('answer', goal['id'], 'input', 'Saturday',
                           question_id=goal['question_id'], epoch=goal['epoch'])
        answer_id = self.store.inspect()['questions'][0]['answer_record_id']
        for index in range(35): self.store.record('chatter'+str(index), 'user', 'Unrelated greeting')
        context = self.store.context()
        self.assertNotIn(answer_id, context['manifest'])
        reopened = Store(self.store.path)
        next_attempt = reopened.claim(context['manifest'])
        binding = next_attempt['questions'][0]
        self.assertEqual((binding['prompt'],binding['answer'],binding['available']), ('What date?','Saturday',True))
        self.assertIn(answer_id, __import__('json').loads(next_attempt['manifest']))
        self.assertTrue(any(s['source_id']==answer_id and s['content']=='Saturday' for s in next_attempt['sources']))

    def test_forgotten_answer_is_metadata_only_and_never_prompt_source(self):
        goal = self.store.waiting(self.attempt['id'], 'What date?')
        self.store.control('answer', goal['id'], 'input', 'Saturday',
                           question_id=goal['question_id'], epoch=goal['epoch'])
        answer_id = self.store.inspect()['questions'][0]['answer_record_id']
        self.store.forget('forget-answer', answer_id)
        next_attempt = self.store.claim(self.store.context()['manifest'])
        binding = next_attempt['questions'][0]
        self.assertFalse(binding['available'])
        self.assertIsNone(binding['answer'])
        self.assertNotIn(answer_id, __import__('json').loads(next_attempt['manifest']))
        self.assertFalse(any(s['source_id']==answer_id for s in next_attempt['sources']))
