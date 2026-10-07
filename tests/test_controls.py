import json
import unittest
from pathlib import Path

from pal.controls import parse_control


class ControlParsingTests(unittest.TestCase):
    def test_frozen_target_cases_propose_action_without_resolving_targets(self):
        cases = json.loads((Path(__file__).parent / 'fixtures' /
                            'stable1_target_matrix_v1.json').read_text())['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                proposal = parse_control(case['text'])
                self.assertEqual(proposal['action'], case['action'])
                self.assertEqual(proposal['cue'], 'Cedar' if case['id'] in
                                 ('T05', 'T07', 'T08', 'T09') else
                                 'Birch' if case['id'] == 'T06' else None)
                self.assertNotIn('goal_id', proposal)

    def test_english_baseline_and_original_correction_payload(self):
        for text in ('stop that', 'cancel that', '止めて', '停止して'):
            self.assertEqual(parse_control(text), {'action': 'cancel', 'cue': None})
        self.assertEqual(parse_control('CORRECT THAT: Keep Cedar’s NAME.\nSecond line.'),
                         {'action': 'correct', 'cue': None,
                          'text': 'Keep Cedar’s NAME.\nSecond line.'})
        self.assertEqual(parse_control('その下書きを訂正して： 原文を保持'),
                         {'action': 'correct', 'cue': None, 'text': '原文を保持'})

    def test_quotes_reports_negation_unsupported_and_empty_do_not_control(self):
        for text in ('「その下書きを止めて」と言われた', 'その下書きを止めてほしくない',
                     'その下書きを止めた', '招待文を下書きにして', 'correct that:',
                     'その下書きを訂正して: ', 'Hello stop that', 'stop that and send it',
                     '2', '最初の作業', 'pause that', 'resume that', 'answer: yes',
                     'forget that', 'Cedarの下書きを止めて。その後に送信して',
                     'cancel "Cedar"', 'correct that without a colon'):
            with self.subTest(text=text):
                self.assertIsNone(parse_control(text))
