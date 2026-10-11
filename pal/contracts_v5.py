"""Pure PAL-v5-common-wire / INT00/1 values; no service or authority checks.

>>> dumps(WorkRef.from_json(loads('{"goal_id":"g1","revision":1,"epoch":0}')))
'{"epoch":0,"goal_id":"g1","revision":1}'
>>> action = parse_model_action('{"kind":"report","summary":"done"}', allowed_refs=[])
>>> action.to_json()
{'kind': 'report', 'summary': 'done'}
"""
from dataclasses import dataclass, fields
from enum import StrEnum
from functools import wraps
import json
import math
from types import MappingProxyType
from typing import ClassVar


_REASONS = frozenset({
    'wrong type', 'missing key', 'unexpected key', 'empty id', 'out of range',
    'invalid enum value', 'empty conditions', 'unprovided ref', 'duplicate key',
    'non-finite number', 'invalid utf-8', 'invalid json', 'invalid value decoder',
})


class ContractError(ValueError):
    """Bounded public error. Neither input data nor caught exceptions are attached."""
    code = 'invalid_input'
    path = '$'

    def __init__(self, reason='invalid json'):
        self.reason = reason if type(reason) is str and reason in _REASONS else 'invalid json'
        super().__init__(f'invalid_input: $: {self.reason}')


class _Invalid(Exception):
    pass


def _fail(reason):
    raise _Invalid(reason)


def _boundary(function):
    @wraps(function)
    def checked(*args, **kwargs):
        reason = 'invalid json'
        try:
            return function(*args, **kwargs)
        except _Invalid as exc:
            reason = exc.args[0]
        except ContractError as exc:
            reason = exc.reason
        except UnicodeError:
            reason = 'invalid utf-8'
        except (ValueError, TypeError, RecursionError, OverflowError):
            pass
        # Raising outside the handler releases JSONDecodeError.doc and its context.
        raise ContractError(reason)
    return checked


class RefKind(StrEnum):
    RECORD = 'record'
    NOTE = 'note'
    SOURCE = 'source'
    RECEIPT = 'receipt'
    ARTIFACT = 'artifact'
    VERIFICATION = 'verification'


class CheckKind(StrEnum):
    SEMANTIC = 'semantic'
    ARTIFACT_SAVED = 'artifact_saved'
    SOURCE_FETCHED = 'source_fetched'


class ErrorCode(StrEnum):
    INVALID_INPUT = 'invalid_input'
    NOT_FOUND = 'not_found'
    AMBIGUOUS = 'ambiguous'
    STALE = 'stale'
    DENIED = 'denied'
    UNAVAILABLE = 'unavailable'
    LIMIT = 'limit'
    CONFLICT = 'conflict'


class ActionKind(StrEnum):
    LOOKUP = 'lookup'
    OPERATE = 'operate'
    ASK = 'ask'
    COMPOSE = 'compose'
    VERIFY = 'verify'
    REPORT = 'report'


class MediaType(StrEnum):
    PLAIN = 'text/plain'
    MARKDOWN = 'text/markdown'


def _text(value, *, identifier=False):
    if type(value) is not str:
        _fail('wrong type')
    value.encode('utf-8', 'strict')
    if identifier and not value:
        _fail('empty id')
    return value


def _integer(value, minimum=None):
    if type(value) is not int:
        _fail('wrong type')
    if minimum is not None and value < minimum:
        _fail('out of range')
    # Apply the interpreter's JSON integer digit limit to host-created values too.
    str(value)
    return value


def _enum(value, enum):
    if type(value) is enum:
        return value
    _text(value)
    if value not in {item.value for item in enum}:
        _fail('invalid enum value')
    return enum(value)


def _keys(value, required, optional=()):
    if type(value) is not dict:
        _fail('wrong type')
    if any(type(key) is not str for key in value):
        _fail('wrong type')
    if set(value) - set(required) - set(optional):
        _fail('unexpected key')
    if set(required) - set(value):
        _fail('missing key')
    return value


def _array(value, parse):
    if type(value) is not list:
        _fail('wrong type')
    return tuple(parse(item) for item in value)


def _sequence(value, parse):
    if type(value) not in (tuple, list):
        _fail('wrong type')
    return tuple(parse(item) for item in value)


def _instance(value, cls):
    if type(value) is not cls:
        _fail('wrong type')
    return value


def _refs(value):
    return _sequence(value, lambda item: _instance(item, Ref))


def _jsoncopy(value):
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        return _integer(value)
    if type(value) is str:
        return _text(value)
    if type(value) is float:
        if not math.isfinite(value):
            _fail('non-finite number')
        return value
    if type(value) is list:
        return [_jsoncopy(item) for item in value]
    if type(value) is dict:
        return {_text(key): _jsoncopy(item) for key, item in value.items()}
    _fail('wrong type')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate key')
        result[key] = value
    return result


def _constant(_value):
    _fail('non-finite number')


@_boundary
def loads(raw):
    """Decode exact str/UTF-8 bytes, rejecting duplicates, nonfinite and non-JSON data."""
    if type(raw) is bytes:
        raw = raw.decode('utf-8', 'strict')
    _text(raw)
    return _jsoncopy(json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant))


def _normalized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def _frozen(value):
    if type(value) is dict:
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_frozen(item) for item in value)
    return value


@dataclass(frozen=True, slots=True, init=False)
class JsonValue:
    """Immutable JSON snapshot; numeric types and signed floating zero stay distinct."""
    _text: str

    @_boundary
    def __init__(self, value):
        object.__setattr__(self, '_text', _normalized(_jsoncopy(value)))

    @property
    def data(self):
        return _frozen(self.to_json())

    def to_json(self):
        return json.loads(self._text)


def _wire(value):
    if isinstance(value, (_Value, JsonValue)):
        return value.to_json()
    if isinstance(value, StrEnum):
        return value.value
    if type(value) is tuple:
        return [_wire(item) for item in value]
    return value


@_boundary
def dumps(value):
    """Serialize a contract value or exact plain JSON to normalized UTF-8 text."""
    wire = value.to_json() if type(value) in _VALUE_TYPES or type(value) is JsonValue else value
    return _normalized(_jsoncopy(wire))


class _Value:
    __slots__ = ()

    @classmethod
    @_boundary
    def from_json(cls, data):
        return cls._from_json(_jsoncopy(data))

    def to_json(self):
        return {field.name: _wire(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class WorkRef(_Value):
    goal_id: str
    revision: int
    epoch: int

    @_boundary
    def __post_init__(self):
        _text(self.goal_id, identifier=True)
        _integer(self.revision, 1)
        _integer(self.epoch, 0)

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('goal_id', 'revision', 'epoch')))


@dataclass(frozen=True, slots=True)
class Ref(_Value):
    kind: RefKind
    id: str

    @_boundary
    def __post_init__(self):
        object.__setattr__(self, 'kind', _enum(self.kind, RefKind))
        _text(self.id, identifier=True)

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('kind', 'id')))


@dataclass(frozen=True, slots=True)
class DraftCondition(_Value):
    description: str
    check: CheckKind

    @_boundary
    def __post_init__(self):
        _text(self.description)
        object.__setattr__(self, 'check', _enum(self.check, CheckKind))

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('description', 'check')))


@dataclass(frozen=True, slots=True)
class Condition(_Value):
    id: str
    description: str
    check: CheckKind

    @_boundary
    def __post_init__(self):
        _text(self.id, identifier=True)
        _text(self.description)
        object.__setattr__(self, 'check', _enum(self.check, CheckKind))

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('id', 'description', 'check')))


@dataclass(frozen=True, slots=True)
class TargetFile(_Value):
    path: str
    ref: str

    @_boundary
    def __post_init__(self):
        _text(self.path)
        _text(self.ref)

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('path', 'ref')))


@dataclass(frozen=True, slots=True)
class Target(_Value):
    repository: str
    issue_numbers: tuple[int, ...]
    files: tuple[TargetFile, ...]

    @_boundary
    def __post_init__(self):
        _text(self.repository)
        object.__setattr__(self, 'issue_numbers', _sequence(self.issue_numbers, _integer))
        object.__setattr__(self, 'files', _sequence(self.files, lambda x: _instance(x, TargetFile)))

    @classmethod
    def _from_json(cls, data):
        _keys(data, ('repository', 'issue_numbers', 'files'))
        return cls(data['repository'], _array(data['issue_numbers'], _integer),
                   _array(data['files'], TargetFile._from_json))


def _brief_fields(value, condition_type):
    _text(value.purpose)
    _instance(value.target, Target)
    object.__setattr__(value, 'constraints', _sequence(value.constraints, _text))
    conditions = _sequence(value.conditions, lambda x: _instance(x, condition_type))
    if not conditions:
        _fail('empty conditions')
    object.__setattr__(value, 'conditions', conditions)
    object.__setattr__(value, 'context_refs', _refs(value.context_refs))


def _brief_from_json(cls, data, condition_type):
    _keys(data, ('purpose', 'target', 'constraints', 'conditions', 'context_refs'))
    return cls(data['purpose'], Target._from_json(data['target']),
               _array(data['constraints'], _text),
               _array(data['conditions'], condition_type._from_json),
               _array(data['context_refs'], Ref._from_json))


@dataclass(frozen=True, slots=True)
class DraftBrief(_Value):
    purpose: str
    target: Target
    constraints: tuple[str, ...]
    conditions: tuple[DraftCondition, ...]
    context_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        _brief_fields(self, DraftCondition)

    @classmethod
    def _from_json(cls, data):
        return _brief_from_json(cls, data, DraftCondition)


@dataclass(frozen=True, slots=True)
class Brief(_Value):
    purpose: str
    target: Target
    constraints: tuple[str, ...]
    conditions: tuple[Condition, ...]
    context_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        _brief_fields(self, Condition)

    @classmethod
    def _from_json(cls, data):
        return _brief_from_json(cls, data, Condition)


@dataclass(frozen=True, slots=True)
class Limits(_Value):
    max_operations: int
    max_steps: int
    max_model_calls: int

    @_boundary
    def __post_init__(self):
        _integer(self.max_operations, 0)
        _integer(self.max_steps, 0)
        _integer(self.max_model_calls, 0)

    @classmethod
    def _from_json(cls, data):
        return cls(**_keys(data, ('max_operations', 'max_steps', 'max_model_calls')))


@dataclass(frozen=True, slots=True)
class Grant(_Value):
    capabilities: tuple[str, ...]
    repositories: tuple[str, ...]
    limits: Limits

    @_boundary
    def __post_init__(self):
        object.__setattr__(self, 'capabilities', _sequence(self.capabilities, _text))
        object.__setattr__(self, 'repositories', _sequence(self.repositories, _text))
        _instance(self.limits, Limits)

    @classmethod
    def _from_json(cls, data):
        _keys(data, ('capabilities', 'repositories', 'limits'))
        return cls(_array(data['capabilities'], _text), _array(data['repositories'], _text),
                   Limits._from_json(data['limits']))


@dataclass(frozen=True, slots=True)
class ErrorInfo(_Value):
    code: ErrorCode
    message: str
    refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        object.__setattr__(self, 'code', _enum(self.code, ErrorCode))
        _text(self.message)
        object.__setattr__(self, 'refs', _refs(self.refs))

    @classmethod
    def _from_json(cls, data):
        _keys(data, ('code', 'message', 'refs'))
        return cls(data['code'], data['message'], _array(data['refs'], Ref._from_json))


_MISSING = object()


@dataclass(frozen=True, slots=True)
class Result(_Value):
    ok: bool
    value: object = _MISSING
    error: ErrorInfo | None = None

    @_boundary
    def __post_init__(self):
        if type(self.ok) is not bool:
            _fail('wrong type')
        if self.ok:
            if self.value is _MISSING or self.error is not None:
                _fail('missing key' if self.value is _MISSING else 'unexpected key')
            if type(self.value) not in _VALUE_TYPES and type(self.value) is not JsonValue:
                object.__setattr__(self, 'value', JsonValue(self.value))
        else:
            if self.value is not _MISSING:
                _fail('unexpected key')
            _instance(self.error, ErrorInfo)

    @classmethod
    @_boundary
    def from_json(cls, data, *, value_decoder=None):
        data = _jsoncopy(data)
        _keys(data, ('ok',), ('value', 'error'))
        if type(data['ok']) is not bool:
            _fail('wrong type')
        if not data['ok']:
            _keys(data, ('ok', 'error'))
            return cls(False, error=ErrorInfo._from_json(data['error']))
        _keys(data, ('ok', 'value'))
        snapshot = JsonValue(data['value'])
        if value_decoder is None:
            return cls(True, snapshot)
        valid = False
        try:
            value = value_decoder(snapshot.to_json())
            valid = (type(value) in _VALUE_TYPES or type(value) is JsonValue)
            if valid:
                valid = JsonValue(value.to_json()) == snapshot
        except Exception:
            pass
        if not valid:
            _fail('invalid value decoder')
        return cls(True, value)

    @classmethod
    def success(cls, value):
        return cls(True, value)

    @classmethod
    def failure(cls, code, message, refs=()):
        return cls(False, error=ErrorInfo(code, message, refs))

    def to_json(self):
        if self.ok:
            return {'ok': True, 'value': _wire(self.value)}
        return {'ok': False, 'error': self.error.to_json()}


class _Action(_Value):
    __slots__ = ()
    kind: ClassVar[ActionKind]

    @classmethod
    @_boundary
    def from_json(cls, data):
        value = action_from_json(data)
        if type(value) is not cls:
            _fail('invalid enum value')
        return value

    def to_json(self):
        result = {'kind': self.kind.value, **super().to_json()}
        if self.kind is ActionKind.LOOKUP and self.source_refs is None:
            del result['source_refs']
        return result


@dataclass(frozen=True, slots=True)
class LookupAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.LOOKUP
    query: str
    source_refs: tuple[Ref, ...] | None = None

    @_boundary
    def __post_init__(self):
        _text(self.query)
        if self.source_refs is not None:
            object.__setattr__(self, 'source_refs', _refs(self.source_refs))


@dataclass(frozen=True, slots=True)
class OperateAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.OPERATE
    capability: str
    arguments: JsonValue
    source_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        _text(self.capability)
        args = self.arguments if type(self.arguments) is JsonValue else JsonValue(self.arguments)
        if type(args.to_json()) is not dict:
            _fail('wrong type')
        object.__setattr__(self, 'arguments', args)
        object.__setattr__(self, 'source_refs', _refs(self.source_refs))


@dataclass(frozen=True, slots=True)
class AskAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.ASK
    question: str
    missing_fact: str
    source_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        _text(self.question)
        _text(self.missing_fact)
        object.__setattr__(self, 'source_refs', _refs(self.source_refs))


@dataclass(frozen=True, slots=True)
class ComposeAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.COMPOSE
    content: str
    media_type: MediaType
    source_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        _text(self.content)
        object.__setattr__(self, 'media_type', _enum(self.media_type, MediaType))
        object.__setattr__(self, 'source_refs', _refs(self.source_refs))


@dataclass(frozen=True, slots=True)
class VerifyAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.VERIFY
    artifact_refs: tuple[Ref, ...]

    @_boundary
    def __post_init__(self):
        object.__setattr__(self, 'artifact_refs', _refs(self.artifact_refs))


@dataclass(frozen=True, slots=True)
class ReportAction(_Action):
    kind: ClassVar[ActionKind] = ActionKind.REPORT
    summary: str

    @_boundary
    def __post_init__(self):
        _text(self.summary)


Action = LookupAction | OperateAction | AskAction | ComposeAction | VerifyAction | ReportAction
_VALUE_TYPES = (WorkRef, Ref, DraftCondition, Condition, TargetFile, Target, DraftBrief,
                Brief, Limits, Grant, ErrorInfo, Result, LookupAction, OperateAction,
                AskAction, ComposeAction, VerifyAction, ReportAction)


@_boundary
def action_from_json(data):
    """Decode host-held Action data. Model outputs must use parse_model_action."""
    data = _jsoncopy(data)
    _keys(data, ('kind',), ('query', 'source_refs', 'capability', 'arguments', 'question',
                          'missing_fact', 'content', 'media_type', 'artifact_refs', 'summary'))
    kind = _enum(data['kind'], ActionKind)
    if kind is ActionKind.LOOKUP:
        _keys(data, ('kind', 'query'), ('source_refs',))
        refs = _array(data['source_refs'], Ref._from_json) if 'source_refs' in data else None
        return LookupAction(data['query'], refs)
    if kind is ActionKind.OPERATE:
        _keys(data, ('kind', 'capability', 'arguments', 'source_refs'))
        return OperateAction(data['capability'], data['arguments'],
                             _array(data['source_refs'], Ref._from_json))
    if kind is ActionKind.ASK:
        _keys(data, ('kind', 'question', 'missing_fact', 'source_refs'))
        return AskAction(data['question'], data['missing_fact'],
                         _array(data['source_refs'], Ref._from_json))
    if kind is ActionKind.COMPOSE:
        _keys(data, ('kind', 'content', 'media_type', 'source_refs'))
        return ComposeAction(data['content'], data['media_type'],
                             _array(data['source_refs'], Ref._from_json))
    if kind is ActionKind.VERIFY:
        _keys(data, ('kind', 'artifact_refs'))
        return VerifyAction(_array(data['artifact_refs'], Ref._from_json))
    _keys(data, ('kind', 'summary'))
    return ReportAction(data['summary'])


def _allowed(allowed_refs):
    result = set()
    for ref in allowed_refs:
        if type(ref) is not Ref:
            raise TypeError('allowed_refs must contain Ref values')
        result.add(ref)
    return result


def _membership(refs, allowed):
    if any(ref not in allowed for ref in refs):
        raise ContractError('unprovided ref')


def parse_model_draft_brief(raw, *, allowed_refs):
    """Parse model data and require exact (kind, id) membership in supplied refs.

    This does not authorize resources/capabilities, prove availability or semantic
    scope, or replace host transaction revision/epoch/state checks.
    """
    allowed = _allowed(allowed_refs)
    value = DraftBrief.from_json(loads(raw))
    _membership(value.context_refs, allowed)
    return value


def parse_model_action(raw, *, allowed_refs):
    """Parse model Action with mandatory source membership, not authority proof.

    Availability, provenance, grant/scope and transaction fencing remain host duties.
    References in opaque arguments are adapter data, not C12 Ref selections.
    """
    allowed = _allowed(allowed_refs)
    value = action_from_json(loads(raw))
    refs = value.artifact_refs if type(value) is VerifyAction else getattr(value, 'source_refs', ())
    _membership(refs or (), allowed)
    return value


__all__ = [
    'ContractError', 'RefKind', 'CheckKind', 'ErrorCode', 'ActionKind', 'MediaType',
    'JsonValue', 'WorkRef', 'Ref', 'DraftCondition', 'Condition', 'TargetFile',
    'Target', 'DraftBrief', 'Brief', 'Limits', 'Grant', 'ErrorInfo', 'Result',
    'Action', 'LookupAction', 'OperateAction', 'AskAction', 'ComposeAction',
    'VerifyAction', 'ReportAction', 'loads', 'dumps', 'action_from_json',
    'parse_model_draft_brief', 'parse_model_action',
]
