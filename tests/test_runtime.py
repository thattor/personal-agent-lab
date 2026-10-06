import dataclasses
import tempfile
import threading
import unittest
from pathlib import Path
from pal.runtime import Runtime, MockProvider, WorkOrder, ProviderExecutor
from pal.store import Store, StaleResult


class BlockingExecutor:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.orders = []

    def execute(self, order):
        self.orders.append(order)
        self.started.set()
        if not self.release.wait(5):
            raise RuntimeError('test barrier timeout')
        return {'goal_id':order.goal_id,'attempt_id':order.attempt_id,'epoch':order.epoch,'action':'local_draft','content':'A local draft'}

    def stop(self):
        self.release.set()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.db'

    def runtime(self, executor=None, provider=None):
        runtime = Runtime(self.path, executor=executor, provider=provider)
        self.addCleanup(runtime.close)
        return runtime

    def test_conversation_independent_of_slow_attempt_and_controls_immediate(self):
        executor = BlockingExecutor()
        runtime = self.runtime(executor)
        handoff = runtime.submit('draft', 'Make a draft, do not send it')
        self.assertTrue(executor.started.wait(2))
        reply = runtime.submit('chat', 'How are you?')['response'].result(timeout=2)
        self.assertTrue(reply['content'])
        self.assertEqual(len(runtime.store.inspect()['goals']), 1)
        cancelled = runtime.submit('cancel', 'Stop that', goal_id=handoff['goal']['id'], control={'action':'cancel'})
        self.assertEqual(cancelled['goal']['state'], 'cancelled')
        executor.release.set()
        self.assertTrue(runtime.idle.wait(2))
        self.assertEqual(runtime.store.get_goal(handoff['goal']['id'])['state'], 'cancelled')
        self.assertEqual(runtime.store.inspect()['receipts'], [])

    def test_default_mock_local_draft_end_to_end(self):
        runtime = self.runtime()
        submitted = runtime.submit('draft', 'Make a draft about synthetic apples; do not send')
        self.assertTrue(runtime.idle.wait(2))
        self.assertEqual(runtime.store.get_goal(submitted['goal']['id'])['state'], 'completed')
        self.assertEqual(len(runtime.store.inspect()['receipts']), 1)
        duplicate = runtime.submit('draft', 'Make a draft about synthetic apples; do not send')
        self.assertEqual(duplicate['goal']['id'], submitted['goal']['id'])
        self.assertEqual(len(runtime.store.inspect()['goals']), 1)

    def test_negative_capability_and_canonical_mutation_proposals(self):
        for payload in ({'action':'send','content':'bad'}, {'action':'local_draft','content':'draft','goal_state':'completed'}, {'action':'shell','content':'rm'}, {'action':'local_draft','content':'draft','criteria':{}}, {'action':'local_draft','content':'draft','approval':True}, {'action':'local_draft','content':'draft','reference_usable':True}, {'action':'local_draft','content':'draft','receipt':'fabricated'}, {'action':'local_draft','content': 42}):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                class BadExecutor:
                    def execute(self, order):
                        return dict(goal_id=order.goal_id, attempt_id=order.attempt_id, epoch=order.epoch, **payload)
                runtime = Runtime(Path(temp)/'state.db',executor=BadExecutor())
                try:
                    submitted = runtime.submit('draft','Make a draft')
                    self.assertTrue(runtime.idle.wait(2))
                    goal = runtime.store.get_goal(submitted['goal']['id'])
                    self.assertEqual(goal['state'], 'failed')
                    self.assertEqual(goal['reason'], 'capability_violation')
                    self.assertEqual(runtime.store.inspect()['receipts'], [])
                finally:
                    runtime.close()

    def test_second_host_fails_fast_and_recovery_runs_only_at_startup(self):
        executor = BlockingExecutor()
        runtime = self.runtime(executor)
        runtime.submit('draft', 'Make a draft')
        self.assertTrue(executor.started.wait(2))
        with self.assertRaises(RuntimeError):
            Runtime(self.path)
        self.assertEqual(Store(self.path).inspect()['attempts'][0]['status'], 'running')
        executor.release.set()
        self.assertTrue(runtime.idle.wait(2))

    def test_workorder_has_no_store_path_credentials_or_mutation(self):
        executor = BlockingExecutor()
        runtime = self.runtime(executor)
        runtime.submit('draft', 'Make a draft')
        self.assertTrue(executor.started.wait(2))
        order = executor.orders[0]
        self.assertNotIn('store', vars(order))
        self.assertNotIn('path', vars(order))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            order.epoch = 99
        executor.release.set()

    def test_forgotten_source_excludes_transitive_derived_responses(self):
        runtime = self.runtime()
        source = runtime.store.record('old', 'user', 'Old secret-free preference')
        response = runtime.store.record('derived', 'assistant', 'Derived from preference', [source['id']])
        runtime.store.note('note', 'Derived note', [response['id']])
        runtime.store.forget('forget', source['id'])
        context = runtime.store.context()
        self.assertEqual(context['records'], [])
        self.assertEqual(context['notes'], [])
        self.assertEqual(len(runtime.store.inspect()['records']), 2)

    def test_normal_conversation_and_explicit_limits_do_not_create_goals(self):
        runtime = self.runtime()
        for i,text in enumerate(('Hello','What is a draft?', 'Record only: make a draft later','Not yet: make a draft')):
            result = runtime.submit(str(i),text)
            result['response'].result(timeout=2)
            self.assertIsNone(result['goal'])
        self.assertEqual(runtime.store.inspect()['goals'], [])

    def test_secret_canary_is_absent_from_captured_provider_prompts(self):
        class CaptureProvider(MockProvider):
            def __init__(self):
                self.prompts=[]
            def complete(self,prompt):
                self.prompts.append(prompt)
                return super().complete(prompt)
        provider=CaptureProvider()
        runtime=self.runtime(provider=provider)
        canary='sk-'+'TESTPROMPT'+'0123456789ABCDE'
        runtime.submit('secret','api_key='+canary)['response'].result(timeout=2)
        runtime.submit('draft','Make a draft. password='+canary)
        self.assertTrue(runtime.idle.wait(2))
        self.assertNotIn(canary,str(provider.prompts))
        self.assertNotIn(canary,str(runtime.store.inspect()))
