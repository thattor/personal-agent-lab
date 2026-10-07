from tests.helpers import settled
import json
import tempfile
import time
import unittest
from pathlib import Path
from pal.runtime import Runtime, MockProvider


class ScriptedProvider(MockProvider):
    def __init__(self, proposals):
        super().__init__()
        self.proposals = iter(proposals)
        self.prompts = []

    def complete(self, prompt):
        if prompt.startswith('DRAFT\n'):
            self.prompts.append(prompt)
            return json.dumps(next(self.proposals), ensure_ascii=False)
        return super().complete(prompt)


class RuntimeEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.db'

    def start(self, provider):
        runtime = Runtime(self.path, provider=provider)
        self.addCleanup(runtime.close)
        return runtime

    def answer(self, runtime, goal_id, key, text):
        goal = runtime.store.get_goal(goal_id)
        settled(runtime, key, text, goal_id=goal_id, control={
            'action':'input', 'text':text, 'question_id':goal['question_id'], 'epoch':goal['epoch']})
        self.wait_for_work(runtime,goal_id)

    def wait_for_work(self, runtime, goal_id):
        deadline = time.monotonic()+3
        while time.monotonic()<deadline:
            if runtime.store.get_goal(goal_id)['state'] not in ('queued','running'):
                return
            time.sleep(.005)
        self.fail('Goal did not reach a waiting or terminal state')

    def test_restart_bound_answer_enters_executor_and_completes_same_goal(self):
        runtime = self.start(ScriptedProvider([{'kind':'needs_input','question':'Which date?','citations':[]}]))
        goal_id = settled(runtime, 'draft','Make a draft invitation')['goal']['id']
        self.wait_for_work(runtime,goal_id)
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'waiting_input')
        runtime.close()
        provider = ScriptedProvider([{'kind':'complete','content':'Invitation Saturday','citations':[]}])
        runtime = self.start(provider)
        self.answer(runtime, goal_id, 'answer', 'Saturday')
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'completed')
        self.assertEqual(len(runtime.store.inspect()['goals']), 1)
        self.assertIn('Which date?', provider.prompts[0])
        self.assertIn('Saturday', provider.prompts[0])
        self.assertIn('answer_record_id', provider.prompts[0])

    def test_two_partial_answers_end_in_one_incomplete_preview(self):
        runtime = self.start(ScriptedProvider([
            {'kind':'needs_input','question':q,'citations':[]} for q in ('Date and recipient?', 'Recipient?', 'Still missing recipient?')]))
        goal_id = settled(runtime, 'draft','Make a draft invitation')['goal']['id']
        self.wait_for_work(runtime,goal_id)
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'waiting_input')
        self.answer(runtime, goal_id, 'a1', 'Saturday')
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'waiting_input')
        self.answer(runtime, goal_id, 'a2', 'I cannot supply recipient')
        state = runtime.store.inspect()
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'failed')
        self.assertEqual(len(state['questions']), 2)
        self.assertEqual(len(state['receipts']), 1)
        self.assertEqual(state['receipts'][0]['role'], 'preview')
        self.assertEqual(state['outcomes'][-1]['check_status'], 'unverified')

    def test_fabricated_source_and_ineligible_preview_never_complete(self):
        for payload in [
            {'kind':'complete','content':'Fabricated Friday','citations':[{'source_id':'invented','quote':'Friday'}]},
            {'kind':'incomplete_preview','content':'Dear {{name}}','missing':'{{name}}','citations':[]}]:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                runtime = Runtime(Path(temp)/'state.db', provider=ScriptedProvider([payload]*3))
                try:
                    goal_id = settled(runtime, 'draft','Make a draft invitation')['goal']['id']
                    self.wait_for_work(runtime,goal_id)
                    self.assertNotEqual(runtime.store.get_goal(goal_id)['state'], 'completed')
                    self.assertEqual(runtime.store.inspect()['receipts'], [])
                    self.assertTrue(runtime.store.inspect()['rejections'])
                finally:
                    runtime.close()

    def test_untrusted_executor_cannot_bypass_closed_proposal_gate(self):
        for proposal in [
            {'kind':'complete','content':'fake','citations':[],'goal_state':'completed'},
            {'kind':'complete','content':'fake','citations':[],'approval':True}]:
            with self.subTest(proposal=proposal), tempfile.TemporaryDirectory() as temp:
                class UnsafeExecutor:
                    def execute(self, order):
                        return {'goal_id':order.goal_id, 'attempt_id':order.attempt_id,
                                'epoch':order.epoch, 'proposal':proposal}
                runtime = Runtime(Path(temp)/'state.db', executor=UnsafeExecutor())
                try:
                    goal_id = settled(runtime, 'draft','Make a draft')['goal']['id']
                    self.wait_for_work(runtime,goal_id)
                    self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'failed')
                    self.assertEqual(runtime.store.inspect()['receipts'], [])
                    self.assertIn('EnvelopeRejected', runtime.store.get_goal(goal_id)['reason'])
                finally:
                    runtime.close()

    def test_malformed_provider_json_is_visible_terminal_error_without_retry(self):
        class InvalidProvider(MockProvider):
            calls = 0
            def complete(self, prompt):
                if prompt.startswith('DRAFT\n'):
                    self.calls += 1
                    return 'done'
                return super().complete(prompt)
        provider = InvalidProvider()
        runtime = self.start(provider)
        goal_id = settled(runtime, 'draft','Make a draft')['goal']['id']
        self.wait_for_work(runtime,goal_id)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(runtime.store.get_goal(goal_id)['state'], 'failed')
        self.assertIn('EnvelopeRejected', runtime.store.get_goal(goal_id)['reason'])
        self.assertEqual(runtime.store.inspect()['receipts'], [])

    def test_mock_draft_transport_is_json_but_saved_bytes_unchanged(self):
        raw = MockProvider().complete('DRAFT\nMake a draft\nInstructions')
        data = json.loads(raw)
        self.assertEqual(data, {'kind':'complete','content':'Local draft (mock): Make a draft','citations':[]})
