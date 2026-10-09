"""READ01/1 bounded saved-result consumer over public C14, C02 and C11 owners.

Stdlib-only and read-only: it follows C14 pages, reads each selected result event's
work (C02) and every event Ref (C11, purpose='user_view' only), and returns a
structured inspection plus a plain-text rendering. Each owner read has its own
snapshot; there is no cross-owner atomic claim, no cache, and no completion,
dispatch or semantic-quality authority.
"""
from pal.contracts_v5 import ContractError, ErrorCode, Ref, Result, WorkRef, dumps, loads
from pal.host_read_v5 import checked_result

__all__ = ['NOTICE', 'inspect_session', 'render']

NOTICE = 'a source registered for this completed work was stopped; completion is historical'
_EVENT_KINDS = frozenset({'accepted', 'progress', 'question', 'state', 'result', 'error'})
_MAX_PAGES = 64


def _unavailable(message):
    return Result.failure(ErrorCode.UNAVAILABLE, message)


def _identifier(value):
    if type(value) is not str or not value:
        return False
    try:
        value.encode('utf-8')
    except UnicodeError:
        return False
    return True


def _valid_request(request):
    return (type(request) is dict and 'session_id' in request
            and set(request) <= {'session_id', 'after_event_id'}
            and all(_identifier(value) for value in request.values()))


def _json_copy(value):
    try:
        return loads(dumps(value))
    except Exception:
        return value


def _ref_key(value):
    """(kind, id) when value is a valid Ref JSON object, else None."""
    try:
        ref = Ref.from_json(value)
    except ContractError:
        return None
    return ref.kind.value, ref.id


def _parse_event(data):
    """Strict C14 event copy, or None when malformed. Refs stay deep-copied JSON
    values in original order; a malformed ref becomes a visible per-ref error
    later, never a page failure here."""
    try:
        base = {'event_id', 'kind', 'text', 'refs'}
        if type(data) is not dict or not base <= set(data) <= base | {'work_ref'}:
            return None
        if not _identifier(data['event_id']) or type(data['kind']) is not str:
            return None
        if data['kind'] not in _EVENT_KINDS or type(data['text']) is not str:
            return None
        data['text'].encode('utf-8')
        if type(data['refs']) is not list:
            return None
        event = {'event_id': data['event_id'], 'kind': data['kind'], 'text': data['text'],
                 'refs': [_json_copy(item) for item in data['refs']]}
        if 'work_ref' in data:
            event['work_ref'] = WorkRef.from_json(data['work_ref']).to_json()
        return event
    except (ContractError, UnicodeError):
        return None


def _page(result, cursor):
    """(events, next_cursor) for a well-formed page, else None."""
    try:
        value = result.value.to_json()
        if type(value) is not dict or set(value) != {'events', 'next_cursor'}:
            return None
        if type(value['events']) is not list:
            return None
        events = [_parse_event(item) for item in value['events']]
        if any(event is None for event in events):
            return None
        # A nonempty page ends at its last event; an empty page keeps its cursor.
        expected = events[-1]['event_id'] if events else cursor
        if value['next_cursor'] != expected:
            return None
        return events, expected
    except Exception:
        return None


def _scan(request, events, max_pages):
    """Follow C14 pages through unselected events. -> (failure, scan)."""
    cursor = request.get('after_event_id')
    seen = {cursor}
    selected, notices = [], []
    for _ in range(max_pages):
        page_request = {'session_id': request['session_id']}
        if cursor is not None:
            page_request['after_event_id'] = cursor
        try:
            result = events.get_events(page_request)
        except Exception:
            return _unavailable('event page unavailable'), None
        if type(result) is not Result:
            return _unavailable('malformed event page'), None
        if not result.ok:
            return result, None
        page = _page(result, cursor)
        if page is None:
            return _unavailable('malformed event page'), None
        batch, following = page
        if not batch:
            return None, (selected, notices, following, False)
        if following in seen:
            return _unavailable('event cursor did not advance'), None
        seen.add(following)
        cursor = following
        for event in batch:
            notice = event['kind'] == 'progress' and event['text'] == NOTICE
            if event['kind'] == 'result' or notice:
                selected.append(event)
            if notice and 'work_ref' in event:
                work = event['work_ref']
                named = {key for key in (_ref_key(item) for item in event['refs'])
                         if key is not None}
                notices.append(((work['goal_id'], work['revision']), named))
    return None, (selected, notices, cursor, True)


def _work(tasks, work_ref):
    if work_ref is None:
        return _unavailable('event has no work reference').to_json()
    try:
        result = tasks.get_work({'goal_id': work_ref['goal_id'], 'revision': work_ref['revision']})
        if type(result) is not Result:
            return _unavailable('malformed work result').to_json()
        if result.ok and type(result.value.to_json()) is not dict:
            return _unavailable('malformed work result').to_json()
        return result.to_json()
    except Exception:
        return _unavailable('work unavailable').to_json()


def _read(reader, ref, work_ref, notices):
    try:
        result = checked_result(reader.read({'ref': ref}, purpose='user_view'), ref)
    except Exception:
        result = _unavailable('read unavailable')
    data = result.to_json()
    validity = None
    if result.ok and type(ref) is dict and ref.get('kind') == 'verification':
        body = data['value']
        if body['usable']:
            validity = 'current'
        else:
            work = body.get('work_ref') or work_ref
            goal = (work['goal_id'], work['revision']) if work else None
            sources = {_ref_key(item) for item in body['source_refs']} - {None}
            stopped = goal is not None and any(
                notice_goal == goal and named & sources for notice_goal, named in notices)
            validity = 'source stopped' if stopped else 'not current'
    return {'ref': ref, 'result': data, 'validity': validity}


def inspect_session(request, *, events, tasks, reader, max_pages=_MAX_PAGES):
    """Inspect saved results of a session. Returns Result({session_id, items,
    next_cursor, truncated}); max_pages is a trusted host integer in 1..64."""
    if type(max_pages) is not int or not 1 <= max_pages <= _MAX_PAGES:
        raise ValueError('max_pages must be an integer in 1..64')
    if not _valid_request(request):
        return Result.failure(ErrorCode.INVALID_INPUT, 'invalid request')
    failure, scanned = _scan(dict(request), events, max_pages)
    if failure is not None:
        return failure
    selected, notices, cursor, truncated = scanned
    items = []
    for event in selected:
        work_ref = event.get('work_ref')
        items.append({'event': event, 'work': _work(tasks, work_ref),
                      'reads': [_read(reader, ref, work_ref, notices) for ref in event['refs']]})
    try:
        return Result.success({'session_id': request['session_id'], 'items': items,
                               'next_cursor': cursor, 'truncated': truncated})
    except ContractError:
        return _unavailable('inspection could not be serialized')


def _indent(text, prefix):
    return [prefix + line for line in text.split('\n')]


def _name(ref):
    """'kind:id' for a valid Ref JSON value; a safe dumps rendering otherwise."""
    key = _ref_key(ref)
    if key is not None:
        return f'{key[0]}:{key[1]}'
    try:
        return dumps(ref)
    except Exception:
        return repr(ref)


def _verification_lines(content):
    """Display the fixed historical projection; display only, never authority."""
    pad = '      '
    try:
        data = loads(content)
        lines = [pad + 'Fixed Conditions:']
        for item in data['conditions']:
            lines.append(f"{pad}  - {item['id']} [{item['check']}]: {item['description']}")
        lines.append(pad + 'Original checks (historical; structural, not a semantic judgement):')
        for check in data['checks']:
            evidence = ', '.join(_name(ref) for ref in check['evidence_refs']) or 'none'
            lines.append(f"{pad}  - {check['condition_id']}: {check['status']}"
                         f" - {check['reason']} (evidence: {evidence})")
        lines.append(pad + 'Saved artifact bindings, in order:')
        for item in data['artifacts']:
            lines.append(f"{pad}  - {_name(item['artifact_ref'])} hash={item['hash']} bytes={item['bytes']}")
        lines.append(f"{pad}Dependencies: {', '.join(_name(ref) for ref in data['source_refs']) or 'none'}")
        return lines
    except (ContractError, KeyError, TypeError, AttributeError):
        return [pad + '(saved verification content could not be displayed)']


def _read_lines(read):
    ref, result = read['ref'], read['result']
    lines = [f'  Ref {_name(ref)}']
    if not result['ok']:
        error = result['error']
        lines.append(f"    Read failed: {error['code']}: {error['message']}")
        return lines
    body = result['value']
    is_verification = type(ref) is dict and ref.get('kind') == 'verification'
    if is_verification:
        lines.append(f"    Read at: {body['observed_at']} (time of this read, not creation time)")
    else:
        lines.append(f"    Observed at: {body['observed_at']} (stored observation time)")
    lines.append(f"    Media type: {body['media_type']}  hash: {body['hash']}")
    if is_verification:
        lines.append('    Saved verification (historical, separate from current usability):')
        lines.extend(_verification_lines(body['content']))
        lines.append(f"    Current usability: {read['validity']}")
    else:
        lines.append(f"    Usable: {'yes' if body['usable'] else 'no'}")
        lines.append('    Content:')
        lines.extend(_indent(body['content'], '      '))
    return lines


def render(inspection):
    """Plain-text rendering of an inspect_session success value."""
    lines = ['Saved-result inspection (read-only; not completion authority)',
             'Model: mock (no real model call; saved drafts are mock output)',
             'Verification: structural only (no semantic quality judgement)',
             f"Session: {inspection['session_id']}"]
    if not inspection['items']:
        lines.append('No result events found.')
    for number, item in enumerate(inspection['items'], 1):
        event = item['event']
        lines.append(f"Event {number} ({event['kind']}): {event['event_id']} ({event['text']})")
        work_ref = event.get('work_ref')
        if work_ref:
            lines.append(f"  Work ref: goal {work_ref['goal_id']} revision {work_ref['revision']}"
                         f" epoch {work_ref['epoch']}")
        else:
            lines.append('  Work ref: none')
        work = item['work']
        if work['ok']:
            lines.append(f"  Work state (TSK, separate from result usability): {work['value'].get('state')}")
        else:
            lines.append(f"  Work unavailable: {work['error']['code']}: {work['error']['message']}")
        for read in item['reads']:
            lines.extend(_read_lines(read))
    lines.append(f"Next cursor: {inspection['next_cursor']}")
    if inspection['truncated']:
        lines.append('Page scan truncated: the page limit was reached; more events may exist after the cursor.')
    else:
        lines.append('Page scan truncated: no')
    return '\n'.join(lines) + '\n'
