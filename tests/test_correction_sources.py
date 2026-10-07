import json
import tempfile
import unittest
from pathlib import Path

from pal.store import Store


class CorrectionSourceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name) / 'state.db')
        self.goal = self.store.ingress('draft', 'Cedar draft', 'draft')['goal']

    def test_ingress_correction_retains_real_source_and_forget_fences(self):
        result = self.store.ingress('fix', 'correct that: revised Cedar', 'control',
                                    self.goal['id'], {'action': 'correct', 'text': 'revised Cedar'})
        revision = self.store.inspect()['revisions'][-1]
        self.assertEqual(json.loads(revision['sources']), [result['record_id']])
        self.assertEqual(revision['criteria'], self.store.inspect()['revisions'][0]['criteria'])
        self.assertEqual(result, self.store.ingress('fix', 'correct that: revised Cedar', 'control',
                         self.goal['id'], {'action': 'correct', 'text': 'revised Cedar'}))
        self.store.forget('forget-fix', result['record_id'])
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.get_goal(self.goal['id'])['reason'], 'reference_stopped')
        self.assertEqual(self.store.inspect()['receipts'], [])

    def test_direct_control_remains_sourceless_and_cannot_forge_ingress_source(self):
        self.store.control('direct', self.goal['id'], 'correct', text='host correction')
        self.assertEqual(json.loads(self.store.inspect()['revisions'][-1]['sources']), [])
        before = self.store.inspect()
        with self.assertRaises(ValueError):
            self.store.ingress('forged', 'fake', 'control', self.goal['id'],
                               {'action': 'correct', 'text': 'fake',
                                'source_record_id': 'not-a-host-record'})
        self.assertEqual(self.store.inspect(), before)
