from tests.helpers import settled, work_settled
import tempfile
import unittest
from pathlib import Path
from pal.store import Store, PREVIEW_BANNER
from pal.runtime import Runtime
from tests.test_runtime_envelope import ScriptedProvider


class TemplateIntakeTests(unittest.TestCase):
    def test_explicit_template_only_and_correct_revision_eligibility(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp)/'state.db')
            goal = store.create_goal('g','Draft a blank template with {{date}}',{'kind':'local_draft','max_bytes':4096})
            first = store.claim()
            self.assertTrue(first['template_preview_allowed'])
            store.control('c',goal['id'],'correct','Draft a generic creative invitation')
            second = store.claim()
            self.assertFalse(second['template_preview_allowed'])
            self.assertEqual([r['template_preview_allowed'] for r in store.inspect()['revisions']], [1,0])
            store.control('c2',goal['id'],'correct','下書きのテンプレートを作成。日時は＿＿')
            self.assertTrue(store.claim()['template_preview_allowed'])

    def test_generic_and_unmarked_template_requests_do_not_enable_preview(self):
        for spec in ['Draft a generic invitation','Draft a creative story about templates',
                     'Draft a template invitation','Draft an invitation with {{date}}']:
            with self.subTest(spec=spec), tempfile.TemporaryDirectory() as temp:
                store = Store(Path(temp)/'state.db')
                store.create_goal('g',spec,{'kind':'local_draft','max_bytes':4096})
                self.assertFalse(store.claim()['template_preview_allowed'])

    def test_explicit_template_runtime_preview_is_never_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Runtime(Path(temp)/'state.db',provider=ScriptedProvider([
                {'kind':'incomplete_preview','content':'Date {{date}}','missing':'{{date}}','citations':[]}]))
            try:
                goal_id = settled(runtime, 'g','Make a draft blank template with {{date}}')['goal']['id']
                goal = work_settled(runtime, goal_id)
                receipt = runtime.store.inspect()['receipts'][0]
                self.assertEqual(receipt['role'], 'preview')
                self.assertTrue(runtime.store.artifact(receipt['artifact_id']).startswith(PREVIEW_BANNER.encode()))
                self.assertEqual(goal['state'], 'failed')
                self.assertEqual(goal['reason'], 'incomplete_template')
            finally:
                runtime.close()
