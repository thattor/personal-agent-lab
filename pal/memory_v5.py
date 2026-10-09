"""MEM01/1 record-only preparation on a caller-owned SQLite connection.

Collaborators are required trusted host code. No provider, filesystem, runner or
model activity is implemented here. Invalidation and events belong to TSK.
"""
from datetime import datetime, timezone
import hashlib
import sqlite3
import uuid

from pal.contracts_v5 import ContractError, Ref, RefKind, Result, WorkRef, dumps, loads

__all__ = ['MemoryStore']

_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS v5_mem_record ('
    ' seq INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE, session_id TEXT NOT NULL,'
    ' role TEXT NOT NULL, text TEXT NOT NULL, hash TEXT NOT NULL,'
    ' observed_at TEXT NOT NULL, usable INTEGER NOT NULL CHECK (usable IN (0,1)))',
    'CREATE TABLE IF NOT EXISTS v5_mem_replay ('
    ' command TEXT NOT NULL, key TEXT NOT NULL, input_json TEXT NOT NULL,'
    ' result_json TEXT NOT NULL, PRIMARY KEY(command,key))',
)


def _text(value, nonempty=False):
    if type(value) is not str:
        raise ContractError('wrong type')
    # Public INT00 serialization checks UTF-8 without retaining decoder exceptions.
    dumps(value)
    if nonempty and not value:
        raise ContractError('empty id')
    return value


def _object(value, required, optional=()):
    value = loads(dumps(value))
    if type(value) is not dict:
        raise ContractError('wrong type')
    if set(value) - set(required) - set(optional):
        raise ContractError('unexpected key')
    if set(required) - set(value):
        raise ContractError('missing key')
    return value


def _failure(code, message):
    return Result.failure(code, message)


def _unavailable():
    return _failure('unavailable', 'memory operation unavailable')


def _invalid():
    return _failure('invalid_input', 'invalid memory request')


def _default_id(prefix):
    return f'{prefix}-{uuid.uuid4().hex}'


def _default_clock():
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """Owns only record/replay tables; host callbacks participate in its transaction."""

    def __init__(self, connection, *, sanitize_text, append_event, invalidate_by_refs,
                 id_factory=None, clock=None):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('connection must be sqlite3.Connection')
        if connection.isolation_level is not None or connection.in_transaction:
            raise ValueError('connection must be idle with isolation_level=None')
        if not all(callable(value) for value in (sanitize_text, append_event, invalidate_by_refs)):
            raise TypeError('sanitizer, event writer and invalidator are required callables')
        if id_factory is not None and not callable(id_factory):
            raise TypeError('id_factory must be callable')
        if clock is not None and not callable(clock):
            raise TypeError('clock must be callable')
        self._conn = connection
        self._sanitize = sanitize_text
        self._append_event = append_event
        self._invalidate = invalidate_by_refs
        self._id_factory = _default_id if id_factory is None else id_factory
        self._clock = _default_clock if clock is None else clock
        connection.execute('BEGIN IMMEDIATE')
        try:
            for sql in _SCHEMA:
                connection.execute(sql)
            connection.execute('COMMIT')
        except BaseException:
            self._rollback()
            raise

    def append(self, request):
        """Sanitize before locking or persistence; replay compares sanitized input."""
        self._require_idle()
        try:
            data = _object(request, ('client_key', 'session_id', 'role', 'text'))
            _text(data['client_key'], True)
            _text(data['session_id'], True)
            _text(data['role'])
            _text(data['text'])
            if data['role'] not in ('user', 'assistant'):
                raise ContractError('invalid enum value')
        except ContractError:
            return _invalid()
        try:
            sanitized = _text(self._sanitize(data['text']))
        except Exception:
            return _unavailable()
        data['text'] = sanitized
        return self._mutate('C05.append', data['client_key'], dumps(data),
                            lambda: self._append_locked(data))

    def stop_reference(self, request, *, session_id):
        """Stop a record, queued dependents and notification in one host transaction."""
        self._require_idle()
        try:
            data = _object(request, ('key', 'source_ref'))
            _text(data['key'], True)
            _text(session_id, True)
            ref = Ref.from_json(data['source_ref'])
            if ref.kind is not RefKind.RECORD:
                raise ContractError('invalid enum value')
        except ContractError:
            return _invalid()
        canonical = dumps({**data, 'session_id': session_id})
        return self._mutate('C05.stop_reference', data['key'], canonical,
                            lambda: self._stop_locked(data['key'], ref, session_id))

    def read(self, request, *, purpose):
        """Current C11 availability; user_view is a trusted host-only purpose."""
        if type(purpose) is not str or purpose not in ('model_context', 'verification', 'user_view'):
            raise ValueError('invalid host read purpose')
        try:
            data = _object(request, ('ref',))
            ref = Ref.from_json(data['ref'])
        except ContractError:
            return _invalid()
        if ref.kind is not RefKind.RECORD:
            return _unavailable()
        try:
            row = self._conn.execute('SELECT text, hash, observed_at, usable FROM v5_mem_record'
                                     ' WHERE id=?', (ref.id,)).fetchone()
            if row is None:
                return _failure('not_found', 'record not found')
            if not row[3] and purpose != 'user_view':
                return _failure('denied', 'record use stopped')
            return Result.success({'ref': ref.to_json(), 'content': row[0],
                                   'media_type': 'text/plain', 'hash': row[1],
                                   'observed_at': row[2], 'source_refs': [], 'usable': bool(row[3])})
        except (sqlite3.Error, ContractError):
            return _unavailable()

    def search(self, request):
        """Same-session literal substring candidates, newest first; no note generation."""
        try:
            data = _object(request, ('query', 'session_id', 'limit'), ('work_ref',))
            _text(data['query'])
            _text(data['session_id'], True)
            limit = data['limit']
            if type(limit) is not int or not 1 <= limit <= 50:
                raise ContractError('out of range')
            if 'work_ref' in data:
                WorkRef.from_json(data['work_ref'])
                return _unavailable()
        except ContractError:
            return _invalid()
        try:
            rows = self._conn.execute(
                'SELECT id FROM v5_mem_record WHERE session_id=? AND usable=1'
                ' AND instr(text,?)>0 ORDER BY seq DESC LIMIT ?',
                (data['session_id'], data['query'], limit + 1)).fetchall()
            return Result.success({'summaries': [],
                                   'record_refs': [Ref('record', row[0]).to_json() for row in rows[:limit]],
                                   'truncated': len(rows) > limit})
        except (sqlite3.Error, ContractError):
            return _unavailable()

    def source_gate(self, connection, refs):
        """Read-only TSK gate, bound to this connection and its existing transaction."""
        if connection is not self._conn or type(refs) is not tuple:
            return 'unavailable'
        try:
            if not connection.in_transaction or any(type(ref) is not Ref for ref in refs):
                return 'unavailable'
            for ref in refs:
                if ref.kind is not RefKind.RECORD:
                    return 'unavailable'
                row = connection.execute('SELECT usable FROM v5_mem_record WHERE id=?',
                                          (ref.id,)).fetchone()
                if row is None:
                    return 'not_found'
                if not row[0]:
                    return 'denied'
            return 'available'
        except sqlite3.Error:
            return 'unavailable'

    def _append_locked(self, data):
        ref = Ref('record', _text(self._id_factory('record'), True))
        observed = _text(self._clock(), True)
        digest = hashlib.sha256(data['text'].encode('utf-8')).hexdigest()
        self._conn.execute(
            'INSERT INTO v5_mem_record (id,session_id,role,text,hash,observed_at,usable)'
            ' VALUES (?,?,?,?,?,?,1)',
            (ref.id, data['session_id'], data['role'], data['text'], digest, observed))
        notification = self._event('C05.append', data['client_key'], data['session_id'],
                                   'accepted', 'record saved', ref)
        if not notification.ok:
            return notification
        return Result.success({'record_ref': ref.to_json()})

    def _stop_locked(self, key, ref, session_id):
        row = self._conn.execute('SELECT usable FROM v5_mem_record WHERE id=?', (ref.id,)).fetchone()
        if row is None:
            return _failure('not_found', 'record not found')
        if row[0]:
            self._conn.execute('UPDATE v5_mem_record SET usable=0 WHERE id=?', (ref.id,))
            invalidation = self._callback(
                'invalidate', lambda: self._invalidate(
                    self._conn, key=dumps(['C05.stop_reference', key, 'invalidate']),
                    session_id=session_id, refs=(ref,)))
            if not invalidation.ok:
                return invalidation
            notification = self._event('C05.stop_reference', key, session_id,
                                       'state', 'source use stopped', ref)
            if not notification.ok:
                return notification
        return Result.success({'affected_refs': [ref.to_json()]})

    def _event(self, command, key, session_id, kind, text, ref):
        request = {'key': dumps([command, key, 'event']), 'session_id': session_id,
                   'kind': kind, 'text': text, 'refs': [ref.to_json()]}
        return self._callback('event', lambda: self._append_event(self._conn, request))

    def _callback(self, kind, call):
        # A savepoint detects transaction replacement, not a malicious callback sandbox.
        self._conn.execute('SAVEPOINT v5_mem_callback')
        result = call()
        if not self._conn.in_transaction:
            return _unavailable()
        self._conn.execute('RELEASE v5_mem_callback')
        if type(result) is not Result:
            return _unavailable()
        result = Result.from_json(result.to_json())
        if not result.ok:
            # Business failure codes propagate; callback payloads are not public diagnostics.
            return _failure(result.error.code, 'memory collaborator rejected operation')
        value = result.value.to_json()
        if kind == 'event':
            value = _object(value, ('event_id',))
            _text(value['event_id'], True)
        else:
            value = _object(value, ('work_refs',))
            if type(value['work_refs']) is not list:
                raise ContractError('wrong type')
            for work_ref in value['work_refs']:
                WorkRef.from_json(work_ref)
        return result

    def _mutate(self, command, key, canonical, operation):
        try:
            self._conn.execute('BEGIN IMMEDIATE')
        except sqlite3.Error:
            return _unavailable()
        try:
            previous = self._conn.execute(
                'SELECT input_json,result_json FROM v5_mem_replay WHERE command=? AND key=?',
                (command, key)).fetchone()
            if previous is not None:
                if previous[0] != canonical:
                    result = _failure('conflict', 'key reused with different input')
                else:
                    result = Result.from_json(loads(previous[1]))
                self._rollback()
                return result
            result = operation()
            if result.ok:
                self._conn.execute(
                    'INSERT INTO v5_mem_replay (command,key,input_json,result_json) VALUES (?,?,?,?)',
                    (command, key, canonical, dumps(result)))
                self._conn.execute('COMMIT')
                return result
        except Exception:
            result = _unavailable()
        except BaseException:
            self._rollback()
            raise
        self._rollback()
        return result

    def _require_idle(self):
        if self._conn.isolation_level is not None or self._conn.in_transaction:
            raise ValueError('mutation requires an idle isolation_level=None connection')

    def _rollback(self):
        if self._conn.in_transaction:
            self._conn.execute('ROLLBACK')
