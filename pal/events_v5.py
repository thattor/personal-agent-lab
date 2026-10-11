"""TSK03/1 isolated read-only C14 event pagination (PAL-contracts-v5).

Unused preparation, not a live service. The host supplies an open sqlite3
connection and owns every write to the existing v5_intake_event ledger. This
module opens no file or replacement connection, creates no schema, runs no
PRAGMA, and never issues BEGIN/COMMIT/ROLLBACK or any write, so preexisting
data and caller-owned transactions are preserved. Malformed stored rows, a
missing ledger or any SQLite read error is a bounded unavailable, never a
partial page or a repair attempt. Reading an event is never execution,
reference or completion authority.
"""
import sqlite3

from pal.contracts_v5 import (
    ContractError, ErrorCode, Ref, Result, WorkRef, loads,
)

__all__ = ['EventReader']

_MAX_PAGE_SIZE = 1000
_EVENT_KINDS = frozenset({'accepted', 'progress', 'question', 'state', 'result', 'error'})
_CURSOR_SQL = 'SELECT seq, session_id FROM v5_intake_event WHERE event_id = ?'
_FIRST_SQL = ('SELECT event_id, work_ref_json, kind, text, refs_json'
              ' FROM v5_intake_event WHERE session_id = ? ORDER BY seq ASC LIMIT ?')
_PAGE_SQL = ('SELECT event_id, work_ref_json, kind, text, refs_json'
             ' FROM v5_intake_event WHERE session_id = ? AND seq > ?'
             ' ORDER BY seq ASC LIMIT ?')


def _identifier(value):
    if type(value) is not str:
        raise ContractError('wrong type')
    if not value:
        raise ContractError('empty id')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ContractError('invalid utf-8') from None
    return value


def _text(value):
    if type(value) is not str:
        raise ContractError('wrong type')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ContractError('invalid utf-8') from None
    return value


def _object(value, required, optional=frozenset()):
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise ContractError('wrong type')
    if set(value) - required - optional:
        raise ContractError('unexpected key')
    if required - set(value):
        raise ContractError('missing key')


def _stored_event(row):
    event_id, work_ref_json, kind, text, refs_json = row
    _identifier(event_id)
    _text(kind)
    if kind not in _EVENT_KINDS:
        raise ContractError('invalid enum value')
    _text(text)
    _text(refs_json)
    data = loads(refs_json)
    if type(data) is not list:
        raise ContractError('wrong type')
    event = {'event_id': event_id, 'kind': kind, 'text': text,
             'refs': [Ref.from_json(item).to_json() for item in data]}
    if work_ref_json is not None:
        _text(work_ref_json)
        event['work_ref'] = WorkRef.from_json(loads(work_ref_json)).to_json()
    return event


def _parse_request(request):
    _object(request, {'session_id'}, {'after_event_id'})
    session_id = _identifier(request['session_id'])
    cursor = _identifier(request['after_event_id']) if 'after_event_id' in request else None
    return session_id, cursor


def _invalid(error):
    return Result.failure(ErrorCode.INVALID_INPUT, f'invalid request: {error.reason}')


def _unavailable():
    return Result.failure(ErrorCode.UNAVAILABLE, 'event store unavailable')


class EventReader:
    """Read-only C14 get_events over a caller-owned sqlite3 connection."""

    def __init__(self, connection, *, page_size=100):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('connection must be a sqlite3.Connection')
        if type(page_size) is not int:
            raise TypeError('page_size must be a strict int')
        if not 1 <= page_size <= _MAX_PAGE_SIZE:
            raise ValueError('page_size must be in 1..1000')
        self._conn = connection
        self._page_size = page_size

    def get_events(self, request):
        """C14 read: at most page_size rows strictly after an opaque cursor."""
        try:
            session_id, cursor = _parse_request(request)
        except ContractError as error:
            return _invalid(error)
        try:
            if cursor is None:
                rows = self._conn.execute(
                    _FIRST_SQL, (session_id, self._page_size)).fetchall()
            else:
                anchor = self._conn.execute(_CURSOR_SQL, (cursor,)).fetchone()
                if anchor is None or anchor[1] != session_id:
                    return Result.failure(ErrorCode.NOT_FOUND, 'cursor not found')
                rows = self._conn.execute(
                    _PAGE_SQL, (session_id, anchor[0], self._page_size)).fetchall()
            events = [_stored_event(row) for row in rows]
        except (sqlite3.Error, ContractError):
            return _unavailable()
        return Result.success({'events': events,
                               'next_cursor': events[-1]['event_id'] if events else cursor})
