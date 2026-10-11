"""NATIVE-TEXT01 pure fixtures; matching receipts do not prove native cessation."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ATTEMPT = {'run_id': 'fixture-run', 'job_id': 'fixture-job', 'attempt_id': 'fixture-attempt'}
REQUEST = '1' * 64
PROFILE = '2' * 64
PREFIX = 'devin.acp:text-only:end_turn:'


def chunk(text, **extra):
    return {'sessionUpdate': 'agent_message_chunk',
            'content': {'type': 'text', 'text': text}, **extra}


def receipt(**changes):
    value = {'attempt_ref': copy.deepcopy(ATTEMPT), 'guarantee_model': 'native_handoff_v1',
             'capability': 'devin.text.only', 'native_stop_reason': 'end_turn',
             'native_mode': 'plan', 'effective_model': 'swe-2-high',
             'effective_model_verified': True, 'stdout_eof_validated': True,
             'owned_pid': 12345, 'owned_exit_code': 0, 'tool_events': 0,
             'pending_permissions': 0, 'session_sha256': '3' * 64,
             'prompt_rpc_sha256': '4' * 64, 'native_version': 'fixture-日本語',
             'host_optional': {'text': '合成 ending metadata'}}
    value.update(changes)
    value['evidence_ref'] = PREFIX + receipt_hash(value)
    return value


def receipt_hash(value):
    body = {key: item for key, item in value.items() if key != 'evidence_ref'}
    # Installed receipt canonicalization uses ensure_ascii default true.
    raw = json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class NativeTextTests(unittest.TestCase):
    def setUp(self):
        self.buffer_type = importlib.import_module('pal.native_text_v5').NativeTextBuffer
        self.binding = {'request_sha256': REQUEST, 'profile_sha256': PROFILE,
                        'attempt_ref': copy.deepcopy(ATTEMPT), 'model_id': 'swe-2-high'}
        self.buffer = self.buffer_type(**self.binding)

    def started(self):
        self.buffer.begin()
        return self.buffer

    def refusal(self, callback):
        with self.assertRaises(ValueError) as caught:
            callback()
        self.assertNotIn('TEXT_CANARY', str(caught.exception))
        self.assertNotIn('合成 ending metadata', str(caught.exception))
        return caught.exception

    def poisoned_by(self, fields):
        try:
            self.buffer.observe(fields)
        except ValueError:
            pass
        try:
            self.buffer.observe(chunk('recovery TEXT_CANARY'))
        except ValueError:
            pass
        self.refusal(lambda: self.buffer.finish(receipt()))

    def test_ordered_japanese_fragments_exact_bytes_hash_and_closed_result(self):
        self.started()
        for text in ('日本', '', '語\n', 'draft 🙂'):
            self.buffer.observe(chunk(text))
        text = '日本語\ndraft 🙂'
        ending = receipt()
        result = self.buffer.finish(ending)
        self.assertEqual(set(result), {'text', 'output_sha256', 'utf8_bytes', 'chunks',
                                      'request_sha256', 'profile_sha256', 'attempt_ref',
                                      'cessation_sha256', 'evidence_ref'})
        self.assertEqual(result, {'text': text,
                                 'output_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                 'utf8_bytes': len(text.encode()), 'chunks': 4,
                                 'request_sha256': REQUEST, 'profile_sha256': PROFILE,
                                 'attempt_ref': ATTEMPT, 'cessation_sha256': receipt_hash(ending),
                                 'evidence_ref': ending['evidence_ref']})

    def test_pre_begin_text_and_non_output_updates_add_no_output(self):
        self.buffer.observe(chunk('TEXT_CANARY'))
        self.started()
        for tag in ('agent_thought_chunk', 'user_message_chunk', 'current_mode_update',
                    'available_commands_update', 'unknown'):
            self.buffer.observe({'sessionUpdate': tag,
                                 'content': {'type': 'text', 'text': 'TEXT_CANARY'}})
        self.buffer.observe(chunk('kept', metadata={'text': 'TEXT_CANARY'}))
        result = self.buffer.finish(receipt())
        self.assertEqual((result['text'], result['chunks']), ('kept', 1))

    def test_constructor_binding_is_copied_and_return_has_no_alias(self):
        self.binding['attempt_ref']['run_id'] = 'mutated'
        self.started().observe(chunk('x'))
        ending = receipt()
        result = self.buffer.finish(ending)
        ending['attempt_ref']['job_id'] = 'mutated'
        self.assertEqual(result['attempt_ref'], ATTEMPT)
        self.assertEqual(result['request_sha256'], REQUEST)
        self.assertEqual(result['profile_sha256'], PROFILE)
        self.assertIsNot(result['attempt_ref'], ending['attempt_ref'])

    def test_invalid_constructor_digest_attempt_and_model_types(self):
        changes = [('request_sha256', 'A' * 64), ('profile_sha256', '1' * 63),
                   ('request_sha256', True), ('attempt_ref', {**ATTEMPT, 'extra': 'TEXT_CANARY'}),
                   ('attempt_ref', {**ATTEMPT, 'job_id': ''}), ('attempt_ref', []),
                   ('model_id', ''), ('model_id', 1), ('model_id', '\ud800')]
        for field, value in changes:
            with self.subTest(field=field, value=repr(value)):
                binding = copy.deepcopy(self.binding); binding[field] = value
                self.refusal(lambda: self.buffer_type(**binding))

    def test_exact_utf8_byte_cap_accepts_32768(self):
        text = '日' * 10922 + 'ab'
        self.assertEqual(len(text.encode()), 32768)
        self.started().observe(chunk(text))
        self.assertEqual(self.buffer.finish(receipt())['utf8_bytes'], 32768)

    def test_one_byte_overflow_poison_never_releases_partial_output(self):
        self.started().observe(chunk('日' * 10922 + 'ab'))
        self.poisoned_by(chunk('x'))

    def test_exact_chunk_cap_including_empty_chunks(self):
        self.started().observe(chunk('x'))
        for _ in range(2047):
            self.buffer.observe(chunk(''))
        self.assertEqual(self.buffer.finish(receipt())['chunks'], 2048)

    def test_empty_chunk_2049_poison(self):
        self.started().observe(chunk('x'))
        for _ in range(2047):
            self.buffer.observe(chunk(''))
        self.poisoned_by(chunk(''))

    def test_malformed_text_utf8_and_content_poison(self):
        fields = (chunk('\ud800'), chunk(1),
                  {'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text'}},
                  {'sessionUpdate': 'agent_message_chunk', 'content': None},
                  {'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'image', 'text': 'x'}})
        for field in fields:
            with self.subTest(field=repr(field)):
                self.buffer = self.buffer_type(**self.binding)
                self.started().observe(chunk('partial TEXT_CANARY'))
                self.poisoned_by(field)

    def test_duplicate_begin_permanently_poison(self):
        self.started().observe(chunk('partial TEXT_CANARY'))
        try:
            self.buffer.begin()
        except ValueError:
            pass
        self.refusal(lambda: self.buffer.finish(receipt()))

    def test_finish_requires_begin_and_nonempty_output(self):
        self.refusal(lambda: self.buffer.finish(receipt()))
        self.buffer = self.buffer_type(**self.binding)
        self.started().observe(chunk(''))
        self.refusal(lambda: self.buffer.finish(receipt()))

    def test_finish_seals_once_and_late_text_cannot_change_original(self):
        self.started().observe(chunk('original'))
        result = self.buffer.finish(receipt())
        try:
            self.buffer.observe(chunk('late TEXT_CANARY'))
        except ValueError:
            pass
        self.refusal(lambda: self.buffer.finish(receipt()))
        self.assertEqual(result['text'], 'original')
        self.assertEqual(result['output_sha256'], hashlib.sha256(b'original').hexdigest())

    def test_wrong_correlation_or_missing_ending_facts_refuse(self):
        changes = [('attempt_ref', {**ATTEMPT, 'attempt_id': 'other'}),
                   ('guarantee_model', 'other'), ('capability', 'other'),
                   ('native_stop_reason', 'cancelled'), ('native_mode', 'act'),
                   ('effective_model', 'other'), ('effective_model_verified', False),
                   ('stdout_eof_validated', False), ('owned_pid', 0), ('owned_pid', True),
                   ('owned_exit_code', False), ('tool_events', 1), ('tool_events', False),
                   ('pending_permissions', 1), ('pending_permissions', False),
                   ('session_sha256', 'A' * 64), ('prompt_rpc_sha256', '4' * 63)]
        for field, value in changes:
            with self.subTest(field=field):
                buffer = self.buffer_type(**self.binding); buffer.begin(); buffer.observe(chunk('x'))
                self.refusal(lambda: buffer.finish(receipt(**{field: value})))
        for field in ('owned_pid', 'owned_exit_code', 'stdout_eof_validated', 'evidence_ref'):
            with self.subTest(missing=field):
                buffer = self.buffer_type(**self.binding); buffer.begin(); buffer.observe(chunk('x'))
                ending = receipt(); del ending[field]
                self.refusal(lambda: buffer.finish(ending))

    def test_full_receipt_hash_includes_optional_japanese_fields_and_detects_tamper(self):
        for edit in ('metadata', 'prefix', 'digest'):
            with self.subTest(edit=edit):
                buffer = self.buffer_type(**self.binding); buffer.begin(); buffer.observe(chunk('x'))
                ending = receipt()
                if edit == 'metadata':
                    ending['host_optional']['text'] = 'changed'
                elif edit == 'prefix':
                    ending['evidence_ref'] = 'other:' + receipt_hash(ending)
                else:
                    ending['evidence_ref'] = PREFIX + '0' * 64
                self.refusal(lambda: buffer.finish(ending))
        ending = receipt()
        alternate = json.dumps({k: v for k, v in ending.items() if k != 'evidence_ref'},
                               sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        self.assertNotEqual(receipt_hash(ending), hashlib.sha256(alternate.encode()).hexdigest())

    def test_negative_owned_exit_with_correlated_receipt_is_allowed(self):
        self.started().observe(chunk('x'))
        ending = receipt(owned_exit_code=-15)
        result = self.buffer.finish(ending)
        self.assertEqual(result['cessation_sha256'], receipt_hash(ending))
        self.assertEqual(result['evidence_ref'], ending['evidence_ref'])


if __name__ == '__main__':
    unittest.main()
