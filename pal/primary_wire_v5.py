"""Frozen PRI01-WIRE/1 pure Primary output parser; stdlib only, no authority."""
from pal.contracts_v5 import ContractError, DraftBrief, Ref, RefKind, WorkRef, loads

_MAX_TEXT_BYTES = 32768
_MAX_REPLY_BYTES = 8192
_MAX_CANDIDATES = 20

_CODES = frozenset({'invalid_input', 'denied', 'unavailable', 'limit'})
_TSK_STATES = frozenset({
    'queued', 'running', 'waiting_input', 'paused',
    'completed', 'cancelled', 'failed',
})
_FUTURE_TOP_KINDS = frozenset({'continue', 'attach'})
_FUTURE_MEMORY_OPERATIONS = frozenset({'remember', 'correct'})
_SIMPLE_COMMANDS = frozenset({'pause', 'resume', 'cancel'})
_CANDIDATE_KEYS = frozenset({
    'work_ref', 'brief_summary', 'expert_id', 'state',
    'open_questions', 'dependency_refs', 'text_withheld',
})
_QUESTION_KEYS = frozenset({'id', 'text', 'revision'})
_MISSING = object()


class PrimaryProposalError(ValueError):
    """Bounded rejection. The fixed message carries no source data."""

    code = 'invalid_input'

    def __init__(self, code='invalid_input'):
        self.code = code if code in _CODES else 'invalid_input'
        super().__init__('%s: primary proposal rejected' % self.code)


def _invalid():
    raise PrimaryProposalError('invalid_input')


def _denied():
    raise PrimaryProposalError('denied')


def _unavailable():
    raise PrimaryProposalError('unavailable')


def _limit():
    raise PrimaryProposalError('limit')


def _encoded(value):
    if type(value) is not str:
        return None
    try:
        return value.encode('utf-8', 'strict')
    except UnicodeError:
        return None


def _text(value):
    if _encoded(value) is None:
        _invalid()
    return value


def _parsed(parser, data):
    try:
        return parser(data)
    except ContractError:
        return _MISSING


def _ref(data):
    value = _parsed(Ref.from_json, data)
    if value is _MISSING:
        _invalid()
    return value


def _work_ref(data):
    value = _parsed(WorkRef.from_json, data)
    if value is _MISSING:
        _invalid()
    return value


def _closed(data, keys):
    if type(data) is not dict or set(data) != set(keys):
        _invalid()


def _candidate(data):
    _closed(data, _CANDIDATE_KEYS)
    wref = _work_ref(data['work_ref'])
    summary = _text(data['brief_summary'])
    _text(data['expert_id'])
    state = _text(data['state'])
    if state not in _TSK_STATES:
        _invalid()
    withheld = data['text_withheld']
    if type(withheld) is not bool:
        _invalid()
    dependency_refs = data['dependency_refs']
    if type(dependency_refs) is not list:
        _invalid()
    for item in dependency_refs:
        if _ref(item).kind is not RefKind.RECORD:
            _invalid()
    questions = data['open_questions']
    if type(questions) is not list:
        _invalid()
    question_ids = set()
    hidden_free = summary == ''
    for question in questions:
        _closed(question, _QUESTION_KEYS)
        question_id = _text(question['id'])
        if not question_id or question_id in question_ids:
            _invalid()
        question_ids.add(question_id)
        if _text(question['text']) != '':
            hidden_free = False
        revision = question['revision']
        if type(revision) is not int or revision < 1 or revision != wref.revision:
            _invalid()
    if withheld and not hidden_free:
        _invalid()
    return wref, withheld, frozenset(question_ids)


def _trusted(current_record_ref, candidates, allowed_record_refs):
    if type(current_record_ref) is not Ref or current_record_ref.kind is not RefKind.RECORD:
        _invalid()
    if type(allowed_record_refs) not in (list, tuple):
        _invalid()
    allowed = set()
    for ref in allowed_record_refs:
        if type(ref) is not Ref or ref.kind is not RefKind.RECORD:
            _invalid()
        allowed.add(ref)
    if current_record_ref not in allowed:
        _invalid()
    if type(candidates) is not list or len(candidates) > _MAX_CANDIDATES:
        _invalid()
    works = {}
    goals = set()
    for item in candidates:
        wref, withheld, question_ids = _candidate(item)
        if wref.goal_id in goals:
            _invalid()
        goals.add(wref.goal_id)
        works[wref] = (withheld, question_ids)
    return frozenset(allowed), works


def _draft_brief(data, allowed):
    brief = _parsed(DraftBrief.from_json, data)
    if brief is _MISSING:
        _invalid()
    for ref in brief.context_refs:
        if ref not in allowed:
            _invalid()
    return brief


def _proposal(data, current, allowed, works):
    if type(data) is not dict:
        _invalid()
    kind = data.get('kind')
    if type(kind) is not str:
        _invalid()
    if kind in _FUTURE_TOP_KINDS:
        _unavailable()
    if kind == 'none':
        _closed(data, ('kind',))
        return {'kind': 'none'}
    if kind == 'new_work':
        _closed(data, ('kind', 'brief'))
        return {'kind': 'new_work', 'brief': _draft_brief(data['brief'], allowed).to_json()}
    if kind == 'answer':
        _closed(data, ('kind', 'work_ref', 'question_id', 'record_ref'))
        wref = _work_ref(data['work_ref'])
        entry = works.get(wref)
        if entry is None:
            _invalid()
        withheld, question_ids = entry
        record_ref = _ref(data['record_ref'])
        if record_ref != current:
            _invalid()
        question_id = data['question_id']
        if type(question_id) is not str or question_id not in question_ids:
            _invalid()
        if withheld:
            _denied()
        return {'kind': 'answer', 'work_ref': wref.to_json(),
                'question_id': question_id, 'record_ref': record_ref.to_json()}
    if kind == 'control':
        _closed(data, ('kind', 'work_ref', 'command'))
        wref = _work_ref(data['work_ref'])
        command = data['command']
        if type(command) is str:
            if command == 'complete':
                _unavailable()
            if command not in _SIMPLE_COMMANDS:
                _invalid()
            if wref not in works:
                _invalid()
            return {'kind': 'control', 'work_ref': wref.to_json(), 'command': command}
        if type(command) is dict:
            command_kind = command.get('kind')
            if type(command_kind) is not str:
                _invalid()
            if command_kind == 'complete':
                _unavailable()
            if command_kind != 'change':
                _invalid()
            _closed(command, ('kind', 'brief', 'origin_record_ref'))
            brief = _draft_brief(command['brief'], allowed)
            origin = _ref(command['origin_record_ref'])
            if origin != current:
                _invalid()
            entry = works.get(wref)
            if entry is None:
                _invalid()
            if entry[0]:
                _denied()
            return {'kind': 'control', 'work_ref': wref.to_json(),
                    'command': {'kind': 'change', 'brief': brief.to_json(),
                                'origin_record_ref': origin.to_json()}}
        _invalid()
    if kind == 'memory':
        _closed(data, ('kind', 'operation'))
        operation = data['operation']
        if type(operation) is not dict:
            _invalid()
        operation_kind = operation.get('kind')
        if type(operation_kind) is not str:
            _invalid()
        if operation_kind in _FUTURE_MEMORY_OPERATIONS:
            _unavailable()
        if operation_kind != 'stop_reference':
            _invalid()
        _closed(operation, ('kind', 'source_ref'))
        source_ref = _ref(operation['source_ref'])
        if source_ref not in allowed:
            _invalid()
        return {'kind': 'memory',
                'operation': {'kind': 'stop_reference', 'source_ref': source_ref.to_json()}}
    _invalid()


def parse_primary_output(text, *, current_record_ref, candidates, allowed_record_refs):
    """Decode one strict JSON {reply,proposal} and normalize the closed proposal."""
    raw = _encoded(text)
    if raw is None:
        _invalid()
    if len(raw) > _MAX_TEXT_BYTES:
        _limit()
    document = _parsed(loads, text)
    if document is _MISSING:
        _invalid()
    _closed(document, ('reply', 'proposal'))
    reply = document['reply']
    encoded = _encoded(reply)
    if encoded is None:
        _invalid()
    if len(encoded) > _MAX_REPLY_BYTES:
        _limit()
    allowed, works = _trusted(current_record_ref, candidates, allowed_record_refs)
    proposal = _proposal(document['proposal'], current_record_ref, allowed, works)
    return {'reply': reply, 'proposal': proposal}


__all__ = ['parse_primary_output', 'PrimaryProposalError']
