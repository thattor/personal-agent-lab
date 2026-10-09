"""NATIVE-TEXT01/1 bounded dynamic text capture.

Pure standard library component. It is not a provider, a routing
authority, or a cessation verifier; receipt checks here establish local
consistency only.
"""

import hashlib
import json
from collections.abc import Mapping
from types import MappingProxyType

_MAX_UTF8_BYTES = 32768
_MAX_CHUNKS = 2048
_MAX_BOUND_LEN = 512
_ATTEMPT_KEYS = frozenset(('run_id', 'job_id', 'attempt_id'))
_EVIDENCE_PREFIX = 'devin.acp:text-only:end_turn:'
_MISSING = object()
_HEX64 = frozenset('0123456789abcdef')


def _refuse(message):
    raise ValueError(message)


def _encodable(value):
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def _is_hex64(value):
    return (isinstance(value, str) and len(value) == 64
            and all(char in _HEX64 for char in value))


def _is_bounded_token(value):
    return (isinstance(value, str) and 0 < len(value) <= _MAX_BOUND_LEN
            and _encodable(value))


class NativeTextBuffer:
    """Bounded agent_message_chunk text capture bound to one attempt."""

    def __init__(self, *, request_sha256, profile_sha256, attempt_ref,
                 model_id):
        if not _is_hex64(request_sha256):
            _refuse('invalid request binding')
        if not _is_hex64(profile_sha256):
            _refuse('invalid profile binding')
        if not _is_bounded_token(model_id):
            _refuse('invalid model binding')
        if (not isinstance(attempt_ref, Mapping)
                or set(attempt_ref) != _ATTEMPT_KEYS
                or not all(_is_bounded_token(attempt_ref[key])
                           for key in _ATTEMPT_KEYS)):
            _refuse('invalid attempt binding')
        self._request_sha256 = request_sha256
        self._profile_sha256 = profile_sha256
        self._attempt_ref = MappingProxyType(
            {key: attempt_ref[key] for key in _ATTEMPT_KEYS})
        self._model_id = model_id
        self._begun = False
        self._sealed = False
        self._poisoned = False
        self._chunks = []
        self._utf8_bytes = 0

    def _poison(self):
        self._poisoned = True
        self._chunks = []
        self._utf8_bytes = 0

    def unqualified_snapshot(self):
        """Observe retained text without granting capture or ending authority."""
        phase = ('poisoned' if self._poisoned else 'sealed' if self._sealed
                 else 'capturing' if self._begun else 'not_begun')
        text = ''.join(self._chunks)
        return {'version': 'NATIVE-TEXT-DIAGNOSTIC/1',
                'authority': 'unqualified', 'phase': phase,
                'text': text,
                'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'utf8_bytes': self._utf8_bytes, 'chunks': len(self._chunks),
                'request_sha256': self._request_sha256,
                'profile_sha256': self._profile_sha256,
                'attempt_ref': dict(self._attempt_ref),
                'requested_model_id': self._model_id}

    def begin(self):
        if self._begun or self._sealed or self._poisoned:
            self._poison()
            _refuse('capture already opened')
        self._begun = True

    def observe(self, fields, *, current_update=False):
        if self._poisoned:
            _refuse('capture poisoned')
        if self._sealed:
            _refuse('capture sealed')
        if not self._begun:
            return
        if not isinstance(fields, Mapping):
            self._poison()
            _refuse('malformed update')
        if fields.get('sessionUpdate') != 'agent_message_chunk':
            return
        content = fields.get('content')
        if not isinstance(content, Mapping) or content.get('type') != 'text':
            self._poison()
            _refuse('nontext chunk content')
        text = content.get('text', _MISSING)
        if not isinstance(text, str) or not _encodable(text):
            self._poison()
            _refuse('malformed chunk text')
        size = len(text.encode('utf-8'))
        if (self._utf8_bytes + size > _MAX_UTF8_BYTES
                or len(self._chunks) + 1 > _MAX_CHUNKS):
            self._poison()
            _refuse('capture overflow')
        self._chunks.append(text)
        self._utf8_bytes += size

    def finish(self, cessation):
        if not self._begun or self._sealed or self._poisoned:
            _refuse('capture not finishable')
        if not self._chunks or self._utf8_bytes == 0:
            _refuse('empty output')
        digest, evidence = self._validated_cessation(cessation)
        text = ''.join(self._chunks)
        self._sealed = True
        return {'text': text,
                'output_sha256':
                    hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'utf8_bytes': self._utf8_bytes,
                'chunks': len(self._chunks),
                'request_sha256': self._request_sha256,
                'profile_sha256': self._profile_sha256,
                'attempt_ref': dict(self._attempt_ref),
                'cessation_sha256': digest,
                'evidence_ref': evidence}

    def _validated_cessation(self, cessation):
        if not isinstance(cessation, Mapping):
            _refuse('invalid cessation')

        def field(name):
            value = cessation.get(name, _MISSING)
            if value is _MISSING:
                _refuse('missing cessation field')
            return value

        attempt = field('attempt_ref')
        if (not isinstance(attempt, Mapping)
                or dict(attempt) != dict(self._attempt_ref)):
            _refuse('attempt mismatch')
        if field('guarantee_model') != 'native_handoff_v1':
            _refuse('guarantee mismatch')
        if field('capability') != 'devin.text.only':
            _refuse('capability mismatch')
        if field('native_stop_reason') != 'end_turn':
            _refuse('stop mismatch')
        if field('native_mode') != 'plan':
            _refuse('mode mismatch')
        if field('effective_model') != self._model_id:
            _refuse('model mismatch')
        if field('effective_model_verified') is not True:
            _refuse('model unverified')
        if field('stdout_eof_validated') is not True:
            _refuse('eof unvalidated')
        if type(field('owned_pid')) is not int or field('owned_pid') <= 0:
            _refuse('invalid owner')
        if type(field('owned_exit_code')) is not int:
            _refuse('invalid exit')
        if type(field('tool_events')) is not int or field('tool_events') != 0:
            _refuse('invalid tool events')
        if (type(field('pending_permissions')) is not int
                or field('pending_permissions') != 0):
            _refuse('invalid permissions')
        if not _is_hex64(field('session_sha256')):
            _refuse('invalid session binding')
        if not _is_hex64(field('prompt_rpc_sha256')):
            _refuse('invalid rpc binding')
        evidence = field('evidence_ref')
        if not isinstance(evidence, str):
            _refuse('invalid evidence')
        body = {key: value for key, value in cessation.items()
                if key != 'evidence_ref'}
        try:
            raw = json.dumps(body, sort_keys=True, separators=(',', ':'),
                             allow_nan=False)
        except (TypeError, ValueError):
            _refuse('invalid cessation')
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        if evidence != _EVIDENCE_PREFIX + digest:
            _refuse('evidence mismatch')
        return digest, evidence
