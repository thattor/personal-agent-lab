"""Immutable native host values; validation establishes local consistency only."""
from dataclasses import dataclass
import hashlib
import json

from .native_text_v5 import NativeTextBuffer
from .native_claude_text_v5 import CLAUDE_PROFILE_ID, CLAUDE_MODEL_ID, validate_claude_ending

NATIVE_PROFILE_ID = 'co-devin-acp-dynamic-text/1'
_CAPTURE = frozenset(('text', 'output_sha256', 'utf8_bytes', 'chunks',
                      'request_sha256', 'profile_sha256', 'attempt_ref',
                      'cessation_sha256', 'evidence_ref'))
_EVIDENCE = (_CAPTURE - {'text'}) | frozenset(
    ('version', 'qualification_sha256', 'evidence_kind', 'model_id', 'cessation'))
_HEX = frozenset('0123456789abcdef')


def _hex(value):
    return type(value) is str and len(value) == 64 and set(value) <= _HEX


def _token(value):
    if type(value) is not str or not 0 < len(value) <= 512:
        return False
    try:
        value.encode('utf-8')
    except UnicodeError:
        return False
    return True


def _json_snapshot(value):
    # Reject non-JSON objects before invoking custom serialization or copying.
    def check(item, depth=0):
        if depth > 64:
            return False
        if item is None or type(item) in (bool, int):
            return True
        if type(item) is str:
            item.encode('utf-8')
            return True
        if type(item) is float:
            return True
        if type(item) is list:
            return all(check(v, depth + 1) for v in item)
        if type(item) is dict:
            return all(type(k) is str and check(k, depth + 1) and check(v, depth + 1)
                       for k, v in item.items())
        return False
    failed = False
    try:
        if not check(value):
            failed = True
        else:
            raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False)
    except Exception:
        failed = True
    if failed:
        raise ValueError('invalid native value')
    return raw


def _attempt(value):
    if (type(value) is not dict or set(value) != {'run_id', 'job_id', 'attempt_id'}
            or not all(_token(v) for v in value.values())):
        raise ValueError('invalid native attempt')


def _counts(value):
    if (type(value['utf8_bytes']) is not int or not 1 <= value['utf8_bytes'] <= 32768
            or type(value['chunks']) is not int or not 1 <= value['chunks'] <= 2048):
        raise ValueError('invalid native bounds')


def _bindings(value, request_sha256, profile):
    if type(profile) is not NativeProfile or not _hex(request_sha256):
        raise ValueError('invalid native binding')
    if (value['request_sha256'] != request_sha256
            or value['profile_sha256'] != profile.profile_sha256):
        raise ValueError('invalid native binding')
    for key in ('output_sha256', 'request_sha256', 'profile_sha256', 'cessation_sha256'):
        if not _hex(value[key]):
            raise ValueError('invalid native digest')
    _attempt(value['attempt_ref'])
    _counts(value)


def _ending(value, cessation, profile):
    if profile.id == CLAUDE_PROFILE_ID:
        checked = validate_claude_ending(
            cessation, request_sha256=value['request_sha256'],
            profile_sha256=profile.profile_sha256, attempt_ref=value['attempt_ref'],
            model_id=profile.model_id, output_sha256=value['output_sha256'],
            utf8_bytes=value['utf8_bytes'], chunks=value['chunks'])
        digest = hashlib.sha256(_json_snapshot(checked).encode('utf-8')).hexdigest()
        if (value['cessation_sha256'] != digest
                or value['evidence_ref'] != 'pal-claude-text:' + digest):
            raise ValueError('invalid native ending')
        return
    # Public buffer validation keeps the original whole receipt hash and facts.
    # A sentinel validates receipt consistency, never reconstructs output text.
    failed = False
    try:
        buffer = NativeTextBuffer(request_sha256=value['request_sha256'],
                                  profile_sha256=profile.profile_sha256,
                                  attempt_ref=value['attempt_ref'], model_id=profile.model_id)
        buffer.begin()
        buffer.observe({'sessionUpdate': 'agent_message_chunk',
                        'content': {'type': 'text', 'text': 'x'}})
        checked = buffer.finish(cessation)
    except Exception:
        failed = True
    if failed:
        raise ValueError('invalid native ending')
    if (value['cessation_sha256'] != checked['cessation_sha256']
            or value['evidence_ref'] != checked['evidence_ref']):
        raise ValueError('invalid native ending')


@dataclass(frozen=True, slots=True, kw_only=True)
class NativeProfile:
    model_id: str
    qualification_sha256: str
    evidence_kind: str
    profile_id: str = NATIVE_PROFILE_ID

    def __post_init__(self):
        if (type(self.model_id) is not str or type(self.profile_id) is not str
                or (self.profile_id, self.model_id) not in
                ((NATIVE_PROFILE_ID, 'swe-2-high'), (CLAUDE_PROFILE_ID, CLAUDE_MODEL_ID))
                or not _hex(self.qualification_sha256)
                or type(self.evidence_kind) is not str
                or self.evidence_kind not in ('fixture', 'native_profile')):
            raise ValueError('invalid native profile')

    @property
    def id(self):
        return self.profile_id

    @classmethod
    def from_json(cls, value):
        if type(value) is not dict or set(value) != {
                'id', 'model_id', 'qualification_sha256', 'evidence_kind', 'profile_sha256'}:
            raise ValueError('invalid native profile')
        profile = cls(profile_id=value['id'], model_id=value['model_id'],
                      qualification_sha256=value['qualification_sha256'],
                      evidence_kind=value['evidence_kind'])
        if not _hex(value['profile_sha256']) or value != profile.to_json():
            raise ValueError('invalid native profile')
        return profile

    @property
    def profile_sha256(self):
        return hashlib.sha256(_json_snapshot(self._body()).encode('utf-8')).hexdigest()

    def _body(self):
        return {'id': self.id, 'model_id': self.model_id,
                'qualification_sha256': self.qualification_sha256,
                'evidence_kind': self.evidence_kind}

    def to_json(self):
        return {**self._body(), 'profile_sha256': self.profile_sha256}


@dataclass(frozen=True, slots=True, init=False)
class NativeReturned:
    _capture_json: str
    _cessation_json: str

    def __init__(self, *, capture, cessation):
        if type(capture) is not dict or set(capture) != _CAPTURE:
            raise ValueError('invalid native capture')
        if type(cessation) is not dict:
            raise ValueError('invalid native ending')
        object.__setattr__(self, '_capture_json', _json_snapshot(capture))
        object.__setattr__(self, '_cessation_json', _json_snapshot(cessation))

    @property
    def text(self):
        return json.loads(self._capture_json)['text']

    def validate(self, *, request_sha256, profile):
        value = json.loads(self._capture_json)
        cessation = json.loads(self._cessation_json)
        _bindings(value, request_sha256, profile)
        text = value['text']
        if type(text) is not str:
            raise ValueError('invalid native text')
        raw = text.encode('utf-8')
        if (not 1 <= len(raw) <= 32768 or len(raw) != value['utf8_bytes']
                or hashlib.sha256(raw).hexdigest() != value['output_sha256']):
            raise ValueError('invalid native text')
        _ending(value, cessation, profile)
        evidence = {key: val for key, val in value.items() if key != 'text'}
        evidence.update(version='NATIVE-CALL01/1', qualification_sha256=profile.qualification_sha256,
                        evidence_kind=profile.evidence_kind, model_id=profile.model_id,
                        cessation=cessation)
        return validate_native_evidence(evidence, request_sha256=request_sha256, profile=profile)


def validate_native_evidence(evidence, *, request_sha256, profile):
    if type(evidence) is not dict or set(evidence) != _EVIDENCE:
        raise ValueError('invalid native evidence')
    value = json.loads(_json_snapshot(evidence))
    _bindings(value, request_sha256, profile)
    if (type(value['version']) is not str or value['version'] != 'NATIVE-CALL01/1'
            or type(value['qualification_sha256']) is not str
            or value['qualification_sha256'] != profile.qualification_sha256
            or type(value['evidence_kind']) is not str or value['evidence_kind'] != profile.evidence_kind
            or type(value['model_id']) is not str or value['model_id'] != profile.model_id
            or type(value['cessation']) is not dict):
        raise ValueError('invalid native evidence')
    _ending(value, value['cessation'], profile)
    return value


class NativeNeverEntered(Exception):
    def __init__(self, *, request_sha256, profile_sha256, evidence_ref):
        if not _hex(request_sha256) or not _hex(profile_sha256) or not _token(evidence_ref):
            raise ValueError('invalid native refusal')
        super().__init__('native call never entered')
        self.request_sha256 = request_sha256
        self.profile_sha256 = profile_sha256
        self.evidence_ref = evidence_ref
