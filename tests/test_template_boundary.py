from tests.helpers import settled
import tempfile
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pal.store import Store, EvidenceRejected
from pal.runtime import Runtime, MockProvider


class TemplateBoundaryTests(unittest.TestCase):
    def test_runtime_complete_markers_end_visible_without_completion(self):
        class InvalidTemplate(MockProvider):
            def complete(self, prompt):
                if not prompt.startswith('DRAFT\n'): return super().complete(prompt)
                return json.dumps({'kind':'complete','content':'Date {{date}}', 'citations':[]})
        with tempfile.TemporaryDirectory() as temp:
            runtime = Runtime(Path(temp)/'state.db',provider=InvalidTemplate())
            try:
                goal_id = settled(runtime, 'template','Make a draft template with {{date}}')['goal']['id']
                deadline = time.monotonic()+3
                while time.monotonic()<deadline:
                    goal = runtime.store.get_goal(goal_id)
                    if goal['state'] in ('waiting_input','failed','completed'): break
                    time.sleep(.01)
                self.assertIn(goal['state'], ('waiting_input','failed'))
                self.assertTrue(goal['reason'])
                state = runtime.store.inspect()
                self.assertEqual(state['receipts'], [])
                self.assertTrue(state['rejections'])
                self.assertFalse(any(o['check_status']=='pass' for o in state['outcomes']))
            finally: runtime.close()

    def new_attempt(self, specification='Make a draft template with {{date}} and {{place}}'):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name)/'state.db')
        goal = store.create_goal('goal', specification, {'kind':'local_draft','max_bytes':4096})
        return store, goal, store.claim()

    def test_eligible_markers_reject_before_bytes_then_preview_remains_valid(self):
        for text in ('Date {{date}}', 'Date {{time}}', 'Date {{date}', 'Date {date}}',
                     'Date ｛｛date｝｝', 'Date ___', 'Date ＿＿'):
            with self.subTest(text=text):
                store, goal, attempt = self.new_attempt()
                with self.assertRaises(EvidenceRejected): store.write_draft(attempt['id'], text)
                self.assertEqual(store.inspect()['artifacts'], [])
                self.assertEqual(store.inspect()['receipts'], [])
                self.assertEqual(store.inspect()['outcomes'], [])
                store.finish_preview(attempt['id'],'incomplete_template','Date {{date}}','{{date}}')
                self.assertNotEqual(store.get_goal(goal['id'])['state'],'completed')
                self.assertEqual(store.inspect()['receipts'][0]['role'],'preview')

    def test_defensive_complete_gate_and_historical_replay(self):
        store, goal, attempt = self.new_attempt()
        # Simulate a receipt minted by the pre-fix capability; no DB row repair.
        with patch('pal.store.has_unresolved_markers', return_value=False):
            receipt = store.write_draft(attempt['id'],'Date {{date}}')
        with self.assertRaises(EvidenceRejected): store.complete(attempt['id'], receipt['id'])
        self.assertNotEqual(store.get_goal(goal['id'])['state'],'completed')
        self.assertEqual(store.inspect()['outcomes'], [])
        with patch('pal.store.has_unresolved_markers', return_value=False):
            old = store.complete(attempt['id'], receipt['id'])
        self.assertEqual(store.complete(attempt['id'], receipt['id']), old)

    def test_filled_template_and_noneligible_literal_braces_are_unchanged(self):
        for spec, text in [('Make a draft template with {{date}}','Date Saturday'),
                           ('Make a draft about literal code','Literal {{date}}')]:
            with self.subTest(spec=spec):
                store, goal, attempt = self.new_attempt(spec)
                receipt = store.write_draft(attempt['id'],text)
                store.complete(attempt['id'],receipt['id'])
                self.assertEqual(store.get_goal(goal['id'])['state'],'completed')
                self.assertEqual(store.artifact(receipt['artifact_id']).decode(),text)

    def test_correction_uses_new_revision_eligibility(self):
        store, goal, old = self.new_attempt()
        store.control('correct',goal['id'],'correct','Make a draft about literal code')
        attempt = store.claim()
        self.assertFalse(attempt['template_preview_allowed'])
        receipt = store.write_draft(attempt['id'],'Literal {{date}}')
        store.complete(attempt['id'],receipt['id'])
        self.assertTrue(store.inspect()['revisions'][0]['template_preview_allowed'])
