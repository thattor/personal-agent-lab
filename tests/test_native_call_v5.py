"""NATIVE-CALL01 local consistency fixtures, never provider/cessation proof."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.contracts_v5 import dumps
from pal.native_text_v5 import NativeTextBuffer

PROFILE_ID = 'co-devin-acp-dynamic-text/1'
ATTEMPT = {'run_id': 'fixture-run', 'job_id': 'fixture-job', 'attempt_id': 'fixture-attempt'}
TEXT = '日本語\nRAW_OUTPUT_CANARY 🙂'
REQUEST = {'call_id': 'synthetic-call', 'reservation_id': 'synthetic-reservation',
           'role': 'primary', 'output_kind': 'primary_proposal',
           'messages': [{'role': 'user', 'text': '合成入力'}],
           'source_refs': [{'kind': 'record', 'id': 'synthetic-record'}]}
REQUEST_HASH = hashlib.sha256(dumps(REQUEST).encode()).hexdigest()
QUALIFICATION = '2' * 64


def ending(**changes):
    value = {'attempt_ref': copy.deepcopy(ATTEMPT), 'guarantee_model': 'native_handoff_v1',
             'capability': 'devin.text.only', 'native_stop_reason': 'end_turn',
             'native_mode': 'plan', 'effective_model': 'swe-2-high',
             'effective_model_verified': True, 'stdout_eof_validated': True,
             'owned_pid': 123, 'owned_exit_code': -15, 'tool_events': 0,
             'pending_permissions': 0, 'session_sha256': '3' * 64,
             'prompt_rpc_sha256': '4' * 64, 'host_extra': {'text': '日本語 host metadata'}}
    value.update(changes)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    value['evidence_ref'] = 'devin.acp:text-only:end_turn:' + hashlib.sha256(raw.encode()).hexdigest()
    return value


class NativeCallTests(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module('pal.native_call_v5')
        self.profile = self.api.NativeProfile(model_id='swe-2-high',
                                             qualification_sha256=QUALIFICATION,
                                             evidence_kind='fixture')
        self.cessation = ending()
        self.capture = self.make_capture()

    def make_capture(self, text=TEXT, chunks=1):
        buffer = NativeTextBuffer(request_sha256=REQUEST_HASH,
                                  profile_sha256=self.profile.profile_sha256,
                                  attempt_ref=ATTEMPT, model_id='swe-2-high')
        buffer.begin()
        buffer.observe({'sessionUpdate': 'agent_message_chunk',
                        'content': {'type': 'text', 'text': text}})
        for _ in range(chunks - 1):
            buffer.observe({'sessionUpdate': 'agent_message_chunk',
                            'content': {'type': 'text', 'text': ''}})
        return buffer.finish(self.cessation)

    def returned(self, capture=None, cessation=None):
        return self.api.NativeReturned(capture=self.capture if capture is None else capture,
                                       cessation=self.cessation if cessation is None else cessation)

    def evidence(self):
        return self.returned().validate(request_sha256=REQUEST_HASH, profile=self.profile)

    def refused(self, callback):
        with self.assertRaises(ValueError) as caught:
            callback()
        for canary in ('RAW_OUTPUT_CANARY', 'SECRET_CANARY', TEXT):
            self.assertNotIn(canary, str(caught.exception))
        return caught.exception

    def reject_capture(self, value, cessation=None):
        self.refused(lambda: self.returned(value, cessation).validate(
            request_sha256=REQUEST_HASH, profile=self.profile))

    def test_profile_closed_hash_identity_and_fixture_label(self):
        self.assertEqual(self.api.NATIVE_PROFILE_ID, PROFILE_ID)
        base = {'id': PROFILE_ID, 'model_id': 'swe-2-high',
                'qualification_sha256': QUALIFICATION, 'evidence_kind': 'fixture'}
        sha = hashlib.sha256(json.dumps(base, sort_keys=True, separators=(',', ':'),
                                       ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        self.assertEqual(self.profile.id, PROFILE_ID)
        self.assertEqual(self.profile.profile_sha256, sha)
        self.assertEqual(self.profile.to_json(), {**base, 'profile_sha256': sha})
        native = self.api.NativeProfile(model_id='swe-2-high', qualification_sha256=QUALIFICATION,
                                        evidence_kind='native_profile')
        self.assertNotEqual(native.profile_sha256, sha)

    def test_profile_immutable_and_json_is_defensive(self):
        first = self.profile.to_json(); first['model_id'] = 'changed'
        self.assertEqual(self.profile.to_json()['model_id'], 'swe-2-high')
        with self.assertRaises((AttributeError, TypeError)):
            self.profile.model_id = 'changed'
        with self.assertRaises((AttributeError, TypeError)):
            self.profile.profile_sha256 = '0' * 64

    def test_profile_rejects_wrong_types_model_hash_and_authority_flags(self):
        variants = ({'model_id': 'other'}, {'model_id': True}, {'qualification_sha256': 'A' * 64},
                    {'qualification_sha256': '2' * 63}, {'qualification_sha256': True},
                    {'evidence_kind': 'verified'}, {'evidence_kind': True})
        for change in variants:
            with self.subTest(change=change):
                args = {'model_id': 'swe-2-high', 'qualification_sha256': QUALIFICATION,
                        'evidence_kind': 'fixture', **change}
                self.refused(lambda: self.api.NativeProfile(**args))
        with self.assertRaises((TypeError, ValueError)):
            self.api.NativeProfile(model_id='swe-2-high', qualification_sha256=QUALIFICATION,
                                   evidence_kind='fixture', verified=True)

    def test_returned_valid_exact_closed_evidence_without_raw_output(self):
        returned = self.returned()
        self.assertEqual(returned.text, TEXT)
        expected = {'version': 'NATIVE-CALL01/1', 'request_sha256': REQUEST_HASH,
                    'profile_sha256': self.profile.profile_sha256,
                    'qualification_sha256': QUALIFICATION, 'evidence_kind': 'fixture',
                    'model_id': 'swe-2-high', 'attempt_ref': ATTEMPT,
                    'output_sha256': self.capture['output_sha256'],
                    'utf8_bytes': len(TEXT.encode()), 'chunks': 1,
                    'cessation': self.cessation, 'cessation_sha256': self.capture['cessation_sha256'],
                    'evidence_ref': self.capture['evidence_ref']}
        result = returned.validate(request_sha256=REQUEST_HASH, profile=self.profile)
        self.assertEqual(result, expected)
        self.assertNotIn('RAW_OUTPUT_CANARY', json.dumps(result))
        self.assertNotIn('text', set(result))
        self.assertEqual(self.api.validate_native_evidence(result,
                         request_sha256=REQUEST_HASH, profile=self.profile), expected)

    def test_returned_constructor_and_validation_snapshot_nested_inputs(self):
        capture, cessation = copy.deepcopy(self.capture), copy.deepcopy(self.cessation)
        returned = self.returned(capture, cessation)
        capture['text'] = 'changed'; capture['attempt_ref']['run_id'] = 'changed'
        cessation['host_extra']['text'] = 'changed'
        result = returned.validate(request_sha256=REQUEST_HASH, profile=self.profile)
        result['attempt_ref']['run_id'] = 'changed'
        result['cessation']['host_extra']['text'] = 'changed'
        again = returned.validate(request_sha256=REQUEST_HASH, profile=self.profile)
        self.assertEqual(returned.text, TEXT)
        with self.assertRaises((AttributeError, TypeError)):
            returned.text = 'changed'
        self.assertEqual(again['attempt_ref'], ATTEMPT)
        self.assertEqual(again['cessation'], self.cessation)

    def test_persisted_validation_returns_defensive_snapshot(self):
        original = self.evidence()
        result = self.api.validate_native_evidence(original, request_sha256=REQUEST_HASH,
                                                   profile=self.profile)
        original['cessation']['host_extra']['text'] = 'changed'
        original['attempt_ref']['job_id'] = 'changed'
        self.assertEqual(result['cessation'], self.cessation)
        self.assertEqual(result['attempt_ref'], ATTEMPT)

    def test_capture_closed_missing_extra_and_wrong_types_refuse(self):
        for field in self.capture:
            with self.subTest(missing=field):
                capture = copy.deepcopy(self.capture); del capture[field]
                self.reject_capture(capture)
        capture = copy.deepcopy(self.capture); capture['verified'] = True
        self.reject_capture(capture)
        for field, value in (('text', 1), ('utf8_bytes', True), ('chunks', True),
                             ('attempt_ref', []), ('output_sha256', 'A' * 64)):
            with self.subTest(field=field):
                capture = copy.deepcopy(self.capture); capture[field] = value
                self.reject_capture(capture)

    def test_text_exact_hash_utf8_and_bounds_refuse_partial_claims(self):
        for field, value in (('text', ''), ('text', '\ud800'), ('text', '日' * 10923),
                             ('text', TEXT + 'changed'), ('output_sha256', '0' * 64),
                             ('utf8_bytes', len(TEXT)), ('chunks', 0), ('chunks', 2049)):
            with self.subTest(field=field, value=repr(value)):
                capture = copy.deepcopy(self.capture); capture[field] = value
                self.reject_capture(capture)

    def test_exact_byte_and_chunk_caps_are_accepted(self):
        capture = self.make_capture('日' * 10922 + 'ab', 2048)
        result = self.returned(capture).validate(request_sha256=REQUEST_HASH, profile=self.profile)
        self.assertEqual((result['utf8_bytes'], result['chunks']), (32768, 2048))

    def test_request_profile_and_attempt_cross_binding_refuse(self):
        for field, value in (('request_sha256', '0' * 64), ('profile_sha256', '0' * 64),
                             ('attempt_ref', {**ATTEMPT, 'attempt_id': 'other'}),
                             ('cessation_sha256', '0' * 64), ('evidence_ref', 'SECRET_CANARY')):
            with self.subTest(field=field):
                capture = copy.deepcopy(self.capture); capture[field] = value
                self.reject_capture(capture)
        self.refused(lambda: self.returned().validate(request_sha256='0' * 64, profile=self.profile))
        other = self.api.NativeProfile(model_id='swe-2-high', qualification_sha256='5' * 64,
                                       evidence_kind='fixture')
        self.refused(lambda: self.returned().validate(request_sha256=REQUEST_HASH, profile=other))
        self.refused(lambda: self.returned().validate(request_sha256=REQUEST_HASH,
                                                      profile=self.profile.to_json()))

    def test_ending_required_facts_and_counterfeit_booleans_refuse(self):
        variants = (('guarantee_model', 'other'), ('capability', 'other'),
                    ('native_stop_reason', 'cancelled'), ('native_mode', 'act'),
                    ('effective_model', 'other'), ('effective_model_verified', 1),
                    ('stdout_eof_validated', 1), ('owned_pid', True), ('owned_pid', 0),
                    ('owned_exit_code', True), ('tool_events', False), ('tool_events', 1),
                    ('pending_permissions', False), ('pending_permissions', 1),
                    ('session_sha256', 'A' * 64), ('prompt_rpc_sha256', '4' * 63))
        for field, value in variants:
            with self.subTest(field=field):
                cessation = ending(**{field: value})
                capture = copy.deepcopy(self.capture)
                capture['evidence_ref'] = cessation['evidence_ref']
                capture['cessation_sha256'] = cessation['evidence_ref'].split(':')[-1]
                self.reject_capture(capture, cessation)
        for field in ('owned_pid', 'owned_exit_code', 'stdout_eof_validated', 'evidence_ref'):
            cessation = copy.deepcopy(self.cessation); del cessation[field]
            self.reject_capture(copy.deepcopy(self.capture), cessation)

    def test_full_optional_ending_hash_tamper_refuses_and_negative_exit_remains_valid(self):
        cessation = copy.deepcopy(self.cessation); cessation['host_extra']['text'] = 'changed'
        self.reject_capture(copy.deepcopy(self.capture), cessation)
        result = self.evidence()
        self.assertEqual(result['cessation']['owned_exit_code'], -15)
        self.assertEqual(result['cessation_sha256'], self.cessation['evidence_ref'].split(':')[-1])

    def test_persisted_closed_schema_missing_and_extra_records_refuse(self):
        original = self.evidence()
        for field in original:
            with self.subTest(missing=field):
                changed = copy.deepcopy(original); del changed[field]
                self.refused(lambda: self.api.validate_native_evidence(changed,
                             request_sha256=REQUEST_HASH, profile=self.profile))
        for extra in ('text', 'verified', 'provider_stopped'):
            changed = copy.deepcopy(original); changed[extra] = 'RAW_OUTPUT_CANARY'
            self.refused(lambda: self.api.validate_native_evidence(changed,
                         request_sha256=REQUEST_HASH, profile=self.profile))

    def test_persisted_tamper_types_bounds_binding_and_fixture_label_refuse(self):
        original = self.evidence()
        variants = (('version', 'other'), ('request_sha256', '0' * 64),
                    ('profile_sha256', '0' * 64), ('qualification_sha256', '0' * 64),
                    ('evidence_kind', 'native_profile'), ('model_id', 'other'),
                    ('output_sha256', 'A' * 64), ('utf8_bytes', True), ('utf8_bytes', 0),
                    ('utf8_bytes', 32769), ('chunks', True), ('chunks', 2049),
                    ('cessation_sha256', '0' * 64), ('evidence_ref', 'SECRET_CANARY'),
                    ('attempt_ref', {**ATTEMPT, 'job_id': 'other'}))
        for field, value in variants:
            with self.subTest(field=field):
                changed = copy.deepcopy(original); changed[field] = value
                self.refused(lambda: self.api.validate_native_evidence(changed,
                             request_sha256=REQUEST_HASH, profile=self.profile))
        changed = copy.deepcopy(original); changed['cessation']['host_extra']['text'] = 'changed'
        self.refused(lambda: self.api.validate_native_evidence(changed,
                     request_sha256=REQUEST_HASH, profile=self.profile))

    def test_never_entered_is_bounded_exception_with_only_host_bindings(self):
        error = self.api.NativeNeverEntered(request_sha256=REQUEST_HASH,
                                            profile_sha256=self.profile.profile_sha256,
                                            evidence_ref='fixture:pre-entry-refusal')
        self.assertIsInstance(error, Exception)
        self.assertEqual(error.request_sha256, REQUEST_HASH)
        self.assertEqual(error.profile_sha256, self.profile.profile_sha256)
        self.assertEqual(error.evidence_ref, 'fixture:pre-entry-refusal')
        for field, value in (('request_sha256', 'A' * 64), ('profile_sha256', True),
                             ('evidence_ref', ''), ('evidence_ref', 'SECRET_CANARY' * 1000)):
            args = {'request_sha256': REQUEST_HASH, 'profile_sha256': self.profile.profile_sha256,
                    'evidence_ref': 'fixture:pre-entry-refusal', **{field: value}}
            self.refused(lambda: self.api.NativeNeverEntered(**args))


if __name__ == '__main__':
    unittest.main()
