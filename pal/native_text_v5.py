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


class _ModelMalformed(Exception):
    pass


class _ModelOverflow(Exception):
    def __init__(self, reason, site, unit, limit):
        self.marker = {'reason': reason, 'site': site, 'unit': unit,
                       'limit': limit, 'observed_at_least': limit + 1}
        super().__init__('model diagnostic overflow')


def _model_token(value, maximum=256, *, nonempty=True, site=None):
    if not isinstance(value, str) or (nonempty and not value):
        raise _ModelMalformed
    # Avoid encoding unbounded input, while malformed UTF8 remains recoverable.
    if len(value) > maximum:
        raise _ModelOverflow('token_length', site, 'codepoints', maximum)
    try:
        encoded = value.encode('utf-8')
    except UnicodeEncodeError:
        raise _ModelMalformed from None
    if len(encoded) > maximum:
        raise _ModelOverflow('token_length', site, 'utf8_bytes', maximum)
    return value


class NativeModelDiagnostic:
    """Bounded modern callback projections without model authority."""

    _limits = {'max_observations': 32, 'max_options': 16, 'max_values': 32,
               'max_string_bytes': 256, 'max_record_bytes': 32768}

    def __init__(self, *, request_sha256, profile_sha256, attempt_ref, model_id):
        if not _is_hex64(request_sha256) or not _is_hex64(profile_sha256):
            raise ValueError('invalid hash binding')
        if not isinstance(attempt_ref, dict) or set(attempt_ref) != _ATTEMPT_KEYS:
            raise ValueError('invalid attempt binding')
        try:
            model_id = _model_token(model_id, 512)
            attempt = {key: _model_token(attempt_ref[key], 512)
                       for key in _ATTEMPT_KEYS}
        except (_ModelMalformed, _ModelOverflow):
            raise ValueError('invalid token binding') from None
        self._record = {'version': 'PRI02-MODEL-DIAGNOSTIC/1',
                        'authority': 'unqualified',
                        'request_sha256': request_sha256,
                        'profile_sha256': profile_sha256,
                        'attempt_ref': attempt, 'requested_model_id': model_id,
                        'status': 'complete', 'observations': [],
                        'limits': dict(self._limits)}
        self._first_overflow = None

    @staticmethod
    def _canonical(record):
        return json.dumps(record, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False)

    def snapshot(self):
        return json.loads(self._canonical(self._record))

    def overflow_snapshot(self):
        record = {key: self._record[key] for key in
                  ('authority', 'request_sha256', 'profile_sha256',
                   'attempt_ref', 'requested_model_id')}
        record.update(version='PRI02-MODEL-OVERFLOW/1',
                      status='overflow' if self._first_overflow is not None else 'not_observed',
                      first_overflow=self._first_overflow,
                      limits={**self._limits, 'max_marker_record_bytes': 4096})
        raw = self._canonical(record)
        if len(raw.encode('utf-8')) > 4096:
            raise ValueError('model overflow marker exceeds bound')
        return json.loads(raw)

    def _overflow(self, row, reason, site, unit, limit):
        self._record['status'] = 'incomplete'
        if self._first_overflow is None:
            self._first_overflow = {
                'retained_index': len(self._record['observations']),
                **{key: row[key] for key in
                   ('hook', 'shape', 'original_hook', 'current_update')},
                'reason': reason, 'site': site, 'unit': unit, 'limit': limit,
                'observed_at_least': limit + 1,
                'valid_hint_retained': any(
                    item['projection_status'] == 'valid'
                    and item['effective_model_hint'] is not None
                    for item in self._record['observations'])}

    @staticmethod
    def _values(entries):
        if not isinstance(entries, list) or not entries:
            raise _ModelMalformed
        if len(entries) > 32:
            raise _ModelOverflow('value_count', 'select_options', 'count', 32)
        values = []
        grouped = None
        for entry in entries:
            if not isinstance(entry, dict):
                raise _ModelMalformed
            is_group = 'group' in entry
            if grouped is not None and grouped != is_group:
                raise _ModelMalformed
            grouped = is_group
            if is_group:
                _model_token(entry['group'], site='group_id')
                children = entry.get('options')
                if not isinstance(children, list) or not children:
                    raise _ModelMalformed
                if len(children) > 32:
                    raise _ModelOverflow('value_count', 'group_options', 'count', 32)
                if len(values) + len(children) > 32:
                    raise _ModelOverflow('value_count', 'flattened_options', 'count', 32)
            else:
                children = [entry]
            for child in children:
                if not isinstance(child, dict) or 'group' in child:
                    raise _ModelMalformed
                values.append(_model_token(child.get('value'), site='available_value'))
        return values

    @classmethod
    def _options(cls, fields, shape):
        if 'configOptions' not in fields:
            if shape == 'config_option_update':
                raise _ModelMalformed
            return []
        raw = fields['configOptions']
        if not isinstance(raw, list):
            raise _ModelMalformed
        if len(raw) > 16:
            raise _ModelOverflow('option_count', 'configOptions', 'count', 16)
        options = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise _ModelMalformed
            option_id = _model_token(entry.get('id'), site='option_id')
            category = (_model_token(entry['category'], nonempty=False, site='category')
                        if 'category' in entry else None)
            kind = entry.get('type')
            current = entry.get('currentValue')
            if kind == 'select':
                current = _model_token(current, site='current_value')
                values = cls._values(entry.get('options'))
            elif kind == 'boolean':
                if type(current) is not bool or 'options' in entry:
                    raise _ModelMalformed
                values = []
            else:
                raise _ModelMalformed
            options.append({'id': option_id, 'category': category, 'type': kind,
                            'current_value': current, 'available_values': values})
        return options

    def observe(self, fields, *, hook, current_update=False,
                original_hook='returned'):
        if self._record['status'] == 'incomplete':
            return
        metadata_valid = (hook in ('observe', 'verify_session')
                          and type(current_update) is bool
                          and original_hook in ('returned', 'raised'))
        if metadata_valid and hook == 'observe' and isinstance(fields, dict):
            if ('configOptions' not in fields and 'sessionId' not in fields
                    and fields.get('sessionUpdate') != 'config_option_update'):
                return
        shape = ('preprompt_snapshot' if hook == 'verify_session' else
                 'config_option_update' if isinstance(fields, dict)
                 and fields.get('sessionUpdate') == 'config_option_update' else
                 'field_snapshot')
        row = {'delivery_index': len(self._record['observations']),
               'hook': hook if metadata_valid else 'observe',
               'shape': shape if metadata_valid else 'field_snapshot',
               'original_hook': original_hook if metadata_valid else 'raised',
               'session_sha256': None,
               'current_update': current_update if metadata_valid else False,
               'projection_status': 'valid', 'options': [],
               'effective_model_hint': None}
        if len(self._record['observations']) >= 32:
            self._overflow(row, 'observation_count', 'observations', 'count', 32)
            return
        try:
            if not metadata_valid or not isinstance(fields, dict):
                raise _ModelMalformed
            if 'sessionId' in fields:
                try:
                    session = _model_token(fields['sessionId'], 512)
                except _ModelOverflow:
                    raise _ModelMalformed from None
                row['session_sha256'] = hashlib.sha256(session.encode('utf-8')).hexdigest()
            row['options'] = self._options(fields, shape)
            models = [opt for opt in row['options'] if opt['id'] == 'model']
            if (len(models) == 1 and models[0]['type'] == 'select'
                    and models[0]['current_value'] in models[0]['available_values']):
                row['effective_model_hint'] = {
                    'option_id': 'model', 'current_value': models[0]['current_value']}
        except _ModelOverflow as error:
            marker = error.marker
            self._overflow(row, marker['reason'], marker['site'],
                           marker['unit'], marker['limit'])
            return
        except _ModelMalformed:
            row['projection_status'] = 'malformed'
            row['options'] = []
            row['effective_model_hint'] = None
        candidate = {**self._record, 'status': 'incomplete',
                     'observations': self._record['observations'] + [row]}
        if len(self._canonical(candidate).encode('utf-8')) > 32768:
            self._overflow(row, 'record_bytes', 'snapshot', 'utf8_bytes', 32768)
            return
        self._record['observations'].append(row)
