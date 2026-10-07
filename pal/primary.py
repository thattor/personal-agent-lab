"""Closed, untrusted Primary proposals. Only the host Store can apply effects."""
import json


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate Primary field')
        result[key] = value
    return result


def _text(value, limit):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('empty Primary text')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError as exc:
        raise ValueError('invalid Primary text') from exc
    if size > limit:
        raise ValueError('oversized Primary text')


def validate_primary(value):
    if not isinstance(value, dict) or set(value) != {'reply', 'action'}:
        raise ValueError('invalid Primary envelope')
    _text(value['reply'], 8192)
    action = value['action']
    if not isinstance(action, dict):
        raise ValueError('invalid Primary action')
    kind = action.get('kind')
    fields = {
        'none': {'kind'},
        'local_draft': {'kind', 'spec', 'source_ids'},
        'answer': {'kind', 'question_id'},
        'control': {'kind', 'op', 'goal_id'},
        'remember': {'kind', 'source_id'},
        'forget': {'kind', 'source_id'},
    }
    if not isinstance(kind, str) or kind not in fields:
        raise ValueError('unsupported Primary action')
    expected = fields[kind]
    if kind == 'control':
        if action.get('op') not in ('cancel', 'pause', 'resume', 'correct'):
            raise ValueError('unsupported Primary control')
        if action['op'] == 'correct':
            expected = expected | {'spec', 'source_ids'}
    if set(action) != expected:
        raise ValueError('unsupported Primary fields')
    for field in ('question_id', 'goal_id', 'source_id'):
        if field in action:
            _text(action[field], 200)
    if 'spec' in action:
        _text(action['spec'], 8192)
        sources = action['source_ids']
        if not isinstance(sources, list) or len(sources) > 128:
            raise ValueError('invalid Primary sources')
        for source in sources:
            _text(source, 200)
        if len(set(sources)) != len(sources):
            raise ValueError('duplicate Primary source')
    return value


def decode_primary(raw):
    _text(raw, 65536)
    try:
        value = json.loads(raw, object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid Primary JSON') from exc
    return validate_primary(value)
