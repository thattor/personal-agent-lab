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
