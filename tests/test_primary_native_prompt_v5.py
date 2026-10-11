"""Formatting boundary fixtures only; no real provider or native ending proof."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qualify_primary_native_v5 import qualify


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


class PromptCandidates:
    def __init__(self, *, trim_export=False, force_mismatch=False):
        self.trim_export = trim_export
        self.force_mismatch = force_mismatch
        self.prompts = []
        self.entries = 0
        self.pin = {'route': 'devin', 'model': 'swe-2-high',
                    'measurement_digest': 'sha256:' + '1' * 64}

    def selection(self, role, focus, policy=None):
        return copy.deepcopy(self.pin)

    def infer_selected(self, selection, role, prompt, call_dir, timeout=900,
                       before_launch=None):
        self.prompts.append(prompt)
        before_launch()
        self.entries += 1
        observed = prompt.strip() if self.trim_export else prompt
        if self.force_mismatch:
            observed += " changed"
        # Simulate strict original-user-message correlation, never normalize
        # both sides to hide a different submitted prompt.
        if observed != prompt:
            raise RuntimeError('strict original prompt mismatch')
        return {'text': '{"reply":"合成返答","proposal":{"kind":"none"}}',
                'model': 'swe-2-high', 'route': 'devin', 'tool_calls': 0,
                'evidence': {'version': '3000.11.3', 'cost_tier': 'Free',
                             'measurement_digest': self.pin['measurement_digest'],
                             'selection_digest': 'sha256:' + hashlib.sha256(canonical(selection)).hexdigest()}}


class NativePromptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.request = {'call_id': 'synthetic-call', 'reservation_id': 'synthetic-reservation',
                        'role': 'primary', 'output_kind': 'primary_proposal',
                        'source_refs': [{'kind': 'record', 'id': 'synthetic-record'}],
                        'messages': [{'role': 'system', 'text': 'Synthetic none-only'},
                                     {'role': 'user', 'text': ' \t合成入力 BODY_CANARY\n \t'}]}

    def test_submitted_prompt_has_no_formatting_edge_whitespace_but_preserves_input(self):
        original = copy.deepcopy(self.request)
        candidates = PromptCandidates()
        attempt = Path(self.tmp.name) / 'attempt'
        result = qualify(self.request, candidates=candidates, attempt_dir=attempt)
        self.assertEqual(result['status'], 'returned_correlated_export')
        self.assertEqual(len(candidates.prompts), 1)
        prompt = candidates.prompts[0]
        self.assertEqual(prompt, prompt.strip())
        self.assertEqual((attempt / 'prompt.txt').read_bytes(), prompt.encode('utf-8'))
        self.assertEqual((attempt / 'request.json').read_bytes(), canonical(original))
        embedded = prompt.split('request=', 1)[1]
        self.assertEqual(json.loads(embedded), original)
        self.assertEqual(self.request, original)
        self.assertEqual(json.loads(embedded)['messages'][1]['text'], ' \t合成入力 BODY_CANARY\n \t')

    def test_cli_trim_keeps_strict_identity_and_correct_builder_returns_fixture(self):
        candidates = PromptCandidates(trim_export=True)
        attempt = Path(self.tmp.name) / 'attempt'
        result = qualify(self.request, candidates=candidates, attempt_dir=attempt)
        self.assertEqual(candidates.entries, 1)
        self.assertEqual(result['status'], 'returned_correlated_export')
        self.assertEqual(result['evidence_kind'], 'fixture')
        self.assertNotIn('BODY_CANARY', json.dumps(result))
        self.assertNotIn('合成返答', json.dumps(result, ensure_ascii=False))
        journal = json.loads((attempt / 'journal.json').read_text())
        self.assertEqual(journal['status'], 'returned_correlated_export')
        # A different original message remains a post-entry unknown. Changing
        # builder formatting must not weaken strict correlation or wire parsing.
        mismatched = PromptCandidates(trim_export=True, force_mismatch=True)
        mismatch_dir = Path(self.tmp.name) / 'mismatch'
        unknown = qualify(self.request, candidates=mismatched, attempt_dir=mismatch_dir)
        self.assertEqual(unknown['status'], 'unknown')
        self.assertEqual(unknown['evidence_kind'], 'fixture')
        self.assertEqual(mismatched.entries, 1)
        self.assertEqual(json.loads((mismatch_dir / 'journal.json').read_text())['status'], 'unknown')



if __name__ == '__main__':
    unittest.main()
