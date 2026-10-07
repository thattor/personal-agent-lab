import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pal.runtime import Runtime, MockProvider
from pal.classification import classify, VERSION, UNSUPPORTED_REPLY
from pal.store import Store


class IngressClassificationTests(unittest.TestCase):
    def test_typography_report_and_unknown_compound_are_conservative(self):
        for text in ('Ｍａｋｅ ａ ｄｒａｆｔ', 'Make a dr\u200baft', '下書きを作って'):
            self.assertEqual(classify(text), 'draft')
        for text in ('"Make a draft"', "'下書きを作って'", '「下書きを作って」', 'Make a draft "unclosed',
                     '下書きに「『作って』」と書いて', '下書きを作りたいんだけど'):
            self.assertEqual(classify(text), 'conversation')
        self.assertEqual(classify('Make a draft and book a flight.'), 'unsupported')
        self.assertEqual(classify("Make a draft saying 'send it'."), 'draft')
        for text in ('昨日下書きを作成しました。', '下書きを作っていました。',
                     '下書きをお願いしました。', '下書きを作ってみたい。'):
            self.assertEqual(classify(text), 'conversation')
        cases = json.loads((Path(__file__).with_name('fixtures') / 'stable1_ingress_v1.json').read_text())['cases']
        for case in cases[:16]:
            self.assertEqual(classify('He said: "' + case['text'] + '"'), 'conversation')
        for case in cases[16:]:
            if not any(q in case['text'] for q in ('"', '「', '」')):
                self.assertEqual(classify('Make a draft saying "' + case['text'] + '"'), 'draft')

    def test_first_heldout_failures_remain_regression_cases(self):
        cases = json.loads((Path(__file__).parents[1] / 'evidence/reviews/stable1-classification/heldout-sealed.json').read_text())
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(classify(case['text']), case['expected'])

    def test_second_heldout_safe_misses_remain_regression_cases(self):
        cases = json.loads((Path(__file__).parents[1] / 'evidence/reviews/stable1-classification/heldout2-sealed.json').read_text())
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(classify(case['text']), case['expected'])

    def test_persisted_classification_dominates_new_grammar_after_reply_gap(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.db'
            text = 'Send this email.'
            store = Store(path)
            original = {'text': text, 'goal_id': None, 'control': None}
            old = store.ingress('gap', text, request=original,
                                classification='unsupported', classifier_version=VERSION)
            self.assertEqual(old['classification'], 'unsupported')
            with patch('pal.runtime.classify', return_value='draft'):
                runtime = Runtime(path)
                try:
                    result = runtime.submit('gap', text)
                    self.assertIsNone(result['goal'])
                    self.assertEqual(result['classifier_version'], VERSION)
                    self.assertEqual(result['response'].result(timeout=2)['content'], UNSUPPORTED_REPLY)
                    self.assertEqual(runtime.store.inspect()['goals'], [])
                finally:
                    runtime.close()

    def test_ingress_fault_does_not_leave_classification_or_partial_work(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.db'
            def fault(point):
                if point == 'ingress.mid_transaction':
                    raise RuntimeError('injected rollback')
            store = Store(path, fault=fault)
            with self.assertRaisesRegex(RuntimeError, 'injected rollback'):
                store.ingress('fault', 'Make a draft', 'draft',
                              classification='draft', classifier_version=VERSION)
            self.assertEqual(store.inspect()['records'], [])
            self.assertEqual(store.inspect()['goals'], [])
            fresh = Store(path)
            one = fresh.ingress('fault', 'Make a draft', 'draft',
                                classification='draft', classifier_version=VERSION)
            two = fresh.ingress('fault', 'Make a draft', 'draft',
                                classification='draft', classifier_version=VERSION)
            self.assertEqual(one, two)
            self.assertEqual(len(fresh.inspect()['goals']), 1)

    def test_frozen_corpus_creates_only_requested_local_goals(self):
        fixture = Path(__file__).with_name('fixtures') / 'stable1_ingress_v1.json'
        cases = json.loads(fixture.read_text())['cases']
        self.assertEqual(len(cases), 40)
        self.assertEqual(sum(c['expected'] == 'draft' for c in cases), 16)
        cases += json.loads(fixture.with_name('stable1_ingress_edges_v1.json').read_text())['cases']
        for case in cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as temp:
                runtime = Runtime(Path(temp) / 'state.db')
                try:
                    result = runtime.submit(case['id'], case['text'])
                    reply = result['response'].result(timeout=2)
                    goals = runtime.store.inspect()['goals']
                    if case['expected'] == 'draft':
                        self.assertEqual(len(goals), 1)
                        self.assertEqual(result['goal']['id'], goals[0]['id'])
                        duplicate = runtime.submit(case['id'], case['text'])
                        self.assertEqual(duplicate['goal']['id'], goals[0]['id'])
                        self.assertEqual(len(runtime.store.inspect()['goals']), 1)
                    else:
                        self.assertEqual(goals, [])
                        self.assertIsNone(result['goal'])
                        if case['expected'] == 'unsupported':
                            self.assertIn('cannot send', reply['content'])
                            self.assertIn('送信', reply['content'])
                finally:
                    runtime.close()

    def test_unsupported_reply_replayed_without_provider_or_work(self):
        class NoProvider(MockProvider):
            def complete(self, prompt):
                raise AssertionError('unsupported request must not call provider')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.db'
            text = 'Make a draft invitation and send it.'
            runtime = Runtime(path, provider=NoProvider())
            try:
                first = runtime.submit('send', text)['response'].result(timeout=2)
                self.assertIn('cannot send', first['content'])
                self.assertEqual(runtime.store.inspect()['goals'], [])
            finally:
                runtime.close()
            runtime = Runtime(path, provider=NoProvider())
            try:
                second = runtime.submit('send', text)['response'].result(timeout=2)
                self.assertEqual(first['id'], second['id'])
                self.assertEqual(runtime.store.inspect()['goals'], [])
            finally:
                runtime.close()
