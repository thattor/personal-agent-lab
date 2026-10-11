"""PRI02-T public duck fixtures: no native process, provider or product proof."""
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return 'sha256:' + hashlib.sha256(encoded(value)).hexdigest()


class Candidates:
    """Only public CO method shape; neither preflight nor cessation evidence."""
    def __init__(self, owner):
        self.owner = owner
        self.pin = {'route': 'devin', 'model': 'swe-2-high',
                    'measurement_digest': 'sha256:' + '1' * 64}
        self.selection_calls = []
        self.inference_calls = []
        self.behavior = None
        self.selection_error = None
        self.result_edit = None

    def selection(self, role, focus, policy=None):
        self.selection_calls.append((role, focus, copy.deepcopy(policy)))
        self.owner.assertEqual(self.owner.journal()['phase'], 'prepared')
        if self.selection_error:
            raise self.selection_error
        return copy.deepcopy(self.pin)

    def infer_selected(self, selection, role, prompt, call_dir, timeout=900,
                       before_launch=None):
        self.inference_calls.append((copy.deepcopy(selection), role, prompt,
                                     Path(call_dir), timeout))
        self.owner.assertEqual(selection, self.pin)
        self.owner.assertEqual(role, 'implement')
        self.owner.assertEqual(timeout, 60)
        self.owner.assertIsInstance(prompt, str)
        self.owner.assertTrue(prompt)
        self.owner.assertTrue(Path(call_dir).is_relative_to(self.owner.attempt))
        self.owner.assertEqual(self.owner.journal()['phase'], 'prepared')
        if self.behavior:
            return self.behavior(before_launch)
        before_launch()
        self.owner.assertEqual(self.owner.journal()['phase'], 'entering')
        result = self.good_result()
        if self.result_edit:
            self.result_edit(result)
        return result

    def good_result(self):
        return {'text': json.dumps({'reply': '普通の返答', 'proposal': {'kind': 'none'}},
                                   ensure_ascii=False),
                'model': 'swe-2-high', 'route': 'devin', 'tool_calls': 0,
                'evidence': {'version': '3000.11.3', 'cost_tier': 'Free',
                             'measurement_digest': self.pin['measurement_digest'],
                             'selection_digest': digest(self.pin),
                             'known_context': {'account': 'CONTEXT_CANARY'},
                             'api_key_source': '/private/SECRET_PATH_CANARY'}}


class NativeQualificationTests(unittest.TestCase):
    def setUp(self):
        self.qualify = importlib.import_module('tools.qualify_primary_native_v5').qualify
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.attempt = Path(self.tmp.name) / 'attempt'
        self.candidates = Candidates(self)
        self.request = {'call_id': 'synthetic-call', 'reservation_id': 'synthetic-reservation',
                        'role': 'primary', 'output_kind': 'primary_proposal',
                        'messages': [{'role': 'system', 'text': 'Synthetic none-only fixture'},
                                     {'role': 'user', 'text': 'BODY_CANARY 合成入力'}],
                        'source_refs': [{'kind': 'record', 'id': 'synthetic-record'}]}

    def journal(self):
        return json.loads((self.attempt / 'journal.json').read_text())

    def invoke(self, request=None):
        return self.qualify(self.request if request is None else request,
                            candidates=self.candidates, attempt_dir=self.attempt)

    def assert_minimized(self, result):
        text = json.dumps(result, ensure_ascii=False)
        for canary in ('BODY_CANARY', 'CONTEXT_CANARY', 'SECRET_PATH_CANARY',
                       'ERROR_CANARY', self.tmp.name, '普通の返答'):
            self.assertNotIn(canary, text)
        self.assertEqual(result['evidence_kind'], 'fixture')
        self.assertNotIn('EOF', text)

    def refused(self, request):
        try:
            result = self.invoke(request)
        except ValueError as error:
            self.assertNotIn('BODY_CANARY', str(error))
        else:
            self.assertEqual(result['status'], 'not_entered')
            self.assert_minimized(result)
        self.assertEqual(self.candidates.inference_calls, [])

    def test_valid_fixture_exact_pin_timeout_and_minimized_terminal(self):
        original = copy.deepcopy(self.request)
        result = self.invoke()
        self.assertEqual(result['status'], 'returned_correlated_export')
        self.assert_minimized(result)
        self.assertEqual(self.request, original)
        self.assertEqual(self.candidates.selection_calls,
                         [('implement', 'coding', {'mode': 'fixed', 'targets': {
                             'implement': {'route': 'devin', 'model': 'swe-2-high'}}})])
        self.assertEqual(len(self.candidates.inference_calls), 1)
        self.assertEqual(stat.S_IMODE(self.attempt.stat().st_mode), 0o700)
        self.assertEqual(self.journal()['phase'], 'terminal')
        self.assertEqual(self.journal()['status'], result['status'])

    def test_journal_binds_original_request_prompt_pin_and_process(self):
        self.invoke()
        journal = self.journal()
        flattened = json.dumps(journal)
        self.assertIn(digest(self.request).split(':')[-1], flattened)
        self.assertIn(digest(self.candidates.pin).split(':')[-1], flattened)
        prompt = self.candidates.inference_calls[0][2]
        self.assertIn(hashlib.sha256(prompt.encode()).hexdigest(), flattened)
        self.assertIn(str(os.getpid()), flattened)
        self.assertIn(str(os.getppid()), flattened)
        self.assertTrue(journal['profile'])
        self.assertTrue(journal['nonce'])

    def test_existing_directory_never_selects_or_invokes(self):
        self.attempt.mkdir()
        self.refused(self.request)
        self.assertEqual(self.candidates.selection_calls, [])

    def test_same_attempt_cannot_reenter_after_success(self):
        self.invoke()
        saved = (self.attempt / 'journal.json').read_bytes()
        try:
            result = self.invoke()
        except ValueError:
            pass
        else:
            self.assertEqual(result['status'], 'not_entered')
        self.assertEqual(len(self.candidates.inference_calls), 1)
        self.assertEqual((self.attempt / 'journal.json').read_bytes(), saved)

    def test_closed_request_and_roles_are_rejected_before_entry(self):
        variants = []
        for key, value in [('extra', 1), ('role', 'expert'), ('output_kind', 'action'),
                           ('call_id', ''), ('reservation_id', 3), ('messages', []),
                           ('source_refs', [{'kind': 'artifact', 'id': 'x'}])]:
            item = copy.deepcopy(self.request); item[key] = value; variants.append(item)
        item = copy.deepcopy(self.request); del item['source_refs']; variants.append(item)
        for index, item in enumerate(variants):
            with self.subTest(index=index):
                self.attempt = Path(self.tmp.name) / str(index)
                self.refused(item)

    def test_message_closed_shape_role_and_utf8_are_rejected(self):
        for index, message in enumerate(({'role': 'assistant', 'text': 'x'},
                                         {'role': 'user', 'text': 'x', 'grant': 1},
                                         {'role': 'user', 'text': 1},
                                         {'role': 'user', 'text': '\ud800'})):
            with self.subTest(index=index):
                self.attempt = Path(self.tmp.name) / str(index)
                item = copy.deepcopy(self.request); item['messages'] = [message]
                self.refused(item)

    def test_request_limit_counts_utf8_bytes(self):
        item = copy.deepcopy(self.request)
        item['messages'][1]['text'] = '日' * 12000
        self.assertGreater(len(encoded(item)), 32768)
        self.refused(item)

    def test_wrong_selection_route_or_model_never_enters(self):
        for index, field in enumerate(('route', 'model', 'measurement_digest')):
            with self.subTest(field=field):
                self.attempt = Path(self.tmp.name) / str(index)
                self.candidates = Candidates(self); self.candidates.pin[field] = 'wrong'
                result = self.invoke()
                self.assertEqual(result['status'], 'not_entered')
                self.assertEqual(self.candidates.inference_calls, [])
                self.assert_minimized(result)

    def test_selection_exception_is_not_entered_and_minimized(self):
        self.candidates.selection_error = RuntimeError('ERROR_CANARY')
        result = self.invoke()
        self.assertEqual(result['status'], 'not_entered')
        self.assert_minimized(result)
        self.assertEqual(self.candidates.inference_calls, [])

    def test_pre_hook_failure_is_not_entered(self):
        def fail(hook):
            raise TimeoutError('ERROR_CANARY')
        self.candidates.behavior = fail
        result = self.invoke()
        self.assertEqual(result['status'], 'not_entered')
        self.assert_minimized(result)
        self.assertEqual(self.journal()['status'], 'not_entered')

    def test_post_hook_failure_is_unknown_without_retry(self):
        def fail(hook):
            hook(); raise TimeoutError('ERROR_CANARY')
        self.candidates.behavior = fail
        result = self.invoke()
        self.assertEqual(result['status'], 'unknown')
        self.assert_minimized(result)
        self.assertEqual(len(self.candidates.inference_calls), 1)
        self.assertEqual(self.journal()['status'], 'unknown')

    def test_duplicate_hook_refuses_even_if_candidate_catches_it(self):
        def duplicate(hook):
            hook()
            with self.assertRaises(Exception):
                hook()
            return self.candidates.good_result()
        self.candidates.behavior = duplicate
        result = self.invoke()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(len(self.candidates.inference_calls), 1)

    def test_normal_return_without_hook_cannot_claim_entry_proof(self):
        self.candidates.behavior = lambda hook: self.candidates.good_result()
        result = self.invoke()
        self.assertNotEqual(result['status'], 'returned_correlated_export')
        self.assert_minimized(result)

    def test_effective_result_mismatch_is_returned_invalid(self):
        changes = [('model', 'other'), ('route', 'other'), ('tool_calls', 1),
                   ('tool_calls', False), ('version', 'wrong'), ('cost_tier', 'Paid'),
                   ('measurement_digest', 'sha256:' + '2' * 64),
                   ('selection_digest', 'sha256:' + '3' * 64)]
        for index, (field, value) in enumerate(changes):
            with self.subTest(field=field):
                self.attempt = Path(self.tmp.name) / str(index)
                self.candidates = Candidates(self)
                def edit(result, field=field, value=value):
                    target = result if field in ('model', 'route', 'tool_calls') else result['evidence']
                    target[field] = value
                self.candidates.result_edit = edit
                result = self.invoke()
                self.assertEqual(result['status'], 'returned_invalid')
                self.assert_minimized(result)

    def test_invalid_wire_nonfinite_duplicate_and_non_none_do_not_apply(self):
        outputs = ('not json', '{"reply":"a","reply":"b","proposal":{"kind":"none"}}',
                   '{"reply":"a","proposal":{"kind":"none"},"n":NaN}',
                   '{"reply":"a","proposal":{"kind":"continue"}}',
                   '{"reply":"a","proposal":{"kind":"none","grant":true}}')
        for index, output in enumerate(outputs):
            with self.subTest(index=index):
                self.attempt = Path(self.tmp.name) / str(index)
                self.candidates = Candidates(self)
                self.candidates.result_edit = lambda result, text=output: result.update(text=text)
                self.assertEqual(self.invoke()['status'], 'returned_invalid')

    def test_wire_and_reply_byte_limits_are_checked_after_return(self):
        for index, text in enumerate(('', '\ud800', 'x' * 32769,
                                      json.dumps({'reply': '日' * 3000,
                                                  'proposal': {'kind': 'none'}}, ensure_ascii=False))):
            with self.subTest(index=index):
                self.attempt = Path(self.tmp.name) / str(index)
                self.candidates = Candidates(self)
                self.candidates.result_edit = lambda result, text=text: result.update(text=text)
                self.assertEqual(self.invoke()['status'], 'returned_invalid')

    def test_terminal_durability_failure_stays_unknown_with_entering_journal(self):
        def fail_persistence(hook):
            hook()
            failure = patch('os.fsync', side_effect=OSError('ERROR_CANARY'))
            failure.start(); self.addCleanup(failure.stop)
            return self.candidates.good_result()
        self.candidates.behavior = fail_persistence
        result = self.invoke()
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(self.journal()['phase'], 'entering')
        self.assert_minimized(result)
        self.assertEqual(len(self.candidates.inference_calls), 1)

    def test_base_exception_after_hook_never_creates_success(self):
        def interrupt(hook):
            hook(); raise KeyboardInterrupt('ERROR_CANARY')
        self.candidates.behavior = interrupt
        try:
            result = self.invoke()
        except KeyboardInterrupt:
            pass
        else:
            self.assertEqual(result['status'], 'unknown')
            self.assert_minimized(result)
        self.assertNotEqual(self.journal().get('status'), 'returned_correlated_export')
        self.assertEqual(len(self.candidates.inference_calls), 1)

    def test_optional_pin_context_affects_digest_but_never_summary(self):
        self.candidates.pin['known_context'] = {'account': 'CONTEXT_CANARY'}
        result = self.invoke()
        self.assertEqual(result['status'], 'returned_correlated_export')
        self.assert_minimized(result)
        self.assertIn(digest(self.candidates.pin).split(':')[-1],
                      json.dumps(self.journal()))


if __name__ == '__main__':
    unittest.main()
