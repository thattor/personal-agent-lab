"""TSK01/1 isolated C03.create and C02.get_work preparation (PAL-contracts-v5).

Unused preparation, not a live service. The host supplies an open sqlite3
connection with isolation_level=None, a trusted Grant ceiling, the configured
expert_id and a trusted same-DB source_gate. This module opens no file, creates
only v5_intake_ tables. MEM01 adds host transaction-bound events and queued-source
invalidation; it does not implement execution, real PRI authority or other states.
"""
import sqlite3
import uuid

from pal.contracts_v5 import (
    Brief, Condition, ContractError, DraftBrief, ErrorCode, Grant, Limits, Ref,
    RefKind, Result, WorkRef, dumps, loads,
)

__all__ = ['IntakeStore', 'GATE_OUTCOMES']

_COMMAND = 'C03.create'
_SQLITE_INT_MAX = 2 ** 63 - 1
_GATE_ERRORS = {
    'not_found': (ErrorCode.NOT_FOUND, 'source not found'),
    'denied': (ErrorCode.DENIED, 'source denied'),
    'unavailable': (ErrorCode.UNAVAILABLE, 'source unavailable'),
}
GATE_OUTCOMES = frozenset({'available', *_GATE_ERRORS})
_EVENT_KINDS = frozenset({'accepted', 'progress', 'question', 'state', 'result', 'error'})

_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS v5_intake_work ('
    ' goal_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK (revision >= 1),'
    ' epoch INTEGER NOT NULL CHECK (epoch >= 0), state TEXT NOT NULL,'
    ' brief_json TEXT NOT NULL, grant_json TEXT NOT NULL, session_id TEXT NOT NULL,'
    ' origin_ref_json TEXT NOT NULL, expert_id TEXT NOT NULL,'
    ' PRIMARY KEY (goal_id, revision))',
    'CREATE TABLE IF NOT EXISTS v5_intake_event ('
    ' seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, session_id TEXT NOT NULL,'
    ' work_ref_json TEXT, kind TEXT NOT NULL, text TEXT NOT NULL, refs_json TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_intake_replay ('
    ' command TEXT NOT NULL, key TEXT NOT NULL, input_json TEXT NOT NULL,'
    ' result_json TEXT NOT NULL, PRIMARY KEY (command, key))',
    'CREATE TABLE IF NOT EXISTS v5_intake_source ('
    ' goal_id TEXT NOT NULL, revision INTEGER NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL,'
    ' PRIMARY KEY (goal_id, revision, kind, id))',
)


def _valid_id(value):
    if type(value) is not str or not value:
        return False
    try:
        value.encode('utf-8')
    except UnicodeError:
        return False
    return True


def _identifier(value):
    if type(value) is not str:
        raise ContractError('wrong type')
    if not value:
        raise ContractError('empty id')
    if not _valid_id(value):
        raise ContractError('invalid utf-8')
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


def _parse_create(request):
    _object(request, {'key', 'session_id', 'origin_record_ref', 'brief'})
    key = _identifier(request['key'])
    session_id = _identifier(request['session_id'])
    origin = Ref.from_json(request['origin_record_ref'])
    if origin.kind is not RefKind.RECORD:
        raise ContractError('invalid enum value')
    return key, session_id, origin, DraftBrief.from_json(request['brief'])


def _ordered_subset(values, allowed):
    allowed = set(allowed)
    return tuple(dict.fromkeys(value for value in values if value in allowed))


def _intersect(ceiling, scope):
    """Nonexpanding Grant: request order, no duplicates, minimum of every limit."""
    a, b = ceiling.limits, scope.limits
    return Grant(
        _ordered_subset(scope.capabilities, ceiling.capabilities),
        _ordered_subset(scope.repositories, ceiling.repositories),
        Limits(min(a.max_operations, b.max_operations), min(a.max_steps, b.max_steps),
               min(a.max_model_calls, b.max_model_calls)),
    )


def _invalid(error):
    return Result.failure(ErrorCode.INVALID_INPUT, f'invalid request: {error.reason}')


def _unavailable(message='intake store unavailable'):
    return Result.failure(ErrorCode.UNAVAILABLE, message)


def _uuid_id(prefix):
    return f'{prefix}-{uuid.uuid4().hex}'


class IntakeStore:
    """Host-owned C03.create / C02.get_work over one caller-owned sqlite3 connection.

    source_gate(connection, refs) is trusted host code that performs same-DB
    availability reads only and returns exactly one of GATE_OUTCOMES.
    id_factory(prefix) is an optional host ID source; models never supply IDs.
    """

    def __init__(self, connection, *, host_grant, expert_id, source_gate, id_factory=None):
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError('connection must be a sqlite3.Connection')
        if connection.isolation_level is not None:
            raise ValueError('connection must use isolation_level=None')
        if connection.in_transaction:
            raise ValueError('connection has a preexisting transaction')
        if type(host_grant) is not Grant:
            raise TypeError('host_grant must be a Grant')
        if type(expert_id) is not str:
            raise TypeError('expert_id must be str')
        if not _valid_id(expert_id):
            raise ValueError('expert_id must be a non-empty UTF-8 id')
        if not callable(source_gate):
            raise TypeError('source_gate is required and must be callable')
        if id_factory is not None and not callable(id_factory):
            raise TypeError('id_factory must be callable')
        self._conn = connection
        self._host_grant = host_grant
        self._expert_id = expert_id
        self._source_gate = source_gate
        self._id_factory = _uuid_id if id_factory is None else id_factory
        connection.execute('BEGIN IMMEDIATE')
        try:
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.execute('COMMIT')
        except BaseException:
            self._rollback()
            raise

    def create(self, request, *, request_scope):
        """C03.create: validate, lock, replay or check grant/sources, persist atomically."""
        if type(request_scope) is not Grant:
            raise TypeError('request_scope must be a trusted host Grant')
        self._require_idle()
        try:
            key, session_id, origin, draft = _parse_create(request)
        except ContractError as error:
            return _invalid(error)
        canonical = dumps({'key': key, 'session_id': session_id,
                           'origin_record_ref': origin.to_json(), 'brief': draft.to_json(),
                           'request_scope': request_scope.to_json()})
        try:
            self._conn.execute('BEGIN IMMEDIATE')
        except sqlite3.OperationalError:
            return _unavailable()
        try:
            result, write = self._create_locked(key, session_id, origin, draft,
                                                request_scope, canonical)
            if write:
                self._conn.execute('COMMIT')
                return result
        except Exception:
            result = _unavailable()
        except BaseException:
            self._rollback()
            raise
        self._rollback()
        return result

    def get_work(self, request):
        """C02.get_work: read-only view of the current or an exact stored revision."""
        try:
            _object(request, {'goal_id'}, {'revision'})
            probe = WorkRef(request['goal_id'], request.get('revision', 1), 0)
        except ContractError as error:
            return _invalid(error)
        not_found = Result.failure(ErrorCode.NOT_FOUND, 'work not found')
        if probe.revision > _SQLITE_INT_MAX:
            return not_found
        sql = ('SELECT goal_id, revision, epoch, state, brief_json, grant_json'
               ' FROM v5_intake_work WHERE goal_id = ?')
        params = (probe.goal_id,)
        if 'revision' in request:
            sql, params = sql + ' AND revision = ?', params + (probe.revision,)
        try:
            row = self._conn.execute(sql + ' ORDER BY revision DESC LIMIT 1', params).fetchone()
            if row is None:
                return not_found
            value = {'work_ref': WorkRef(row[0], row[1], row[2]).to_json(),
                     'brief': Brief.from_json(loads(row[4])).to_json(),
                     'grant': Grant.from_json(loads(row[5])).to_json(),
                     'state': row[3], 'current_artifact_refs': [], 'open_questions': []}
        except (sqlite3.Error, ContractError):
            return _unavailable()
        return Result.success(value)

    def append_event(self, connection, request):
        """C14 event mutation; caller owns this transaction and must roll back errors."""
        self._require_transaction(connection)
        try:
            _object(request, {'key', 'session_id', 'kind', 'text', 'refs'}, {'work_ref'})
            key = _identifier(request['key'])
            session = _identifier(request['session_id'])
            kind = _text(request['kind'])
            if kind not in _EVENT_KINDS:
                raise ContractError('invalid enum value')
            content = _text(request['text'])
            if type(request['refs']) is not list:
                raise ContractError('wrong type')
            refs = tuple(Ref.from_json(ref) for ref in request['refs'])
            work = WorkRef.from_json(request['work_ref']) if 'work_ref' in request else None
        except ContractError as error:
            return _invalid(error)
        canonical = dumps(request)
        replay = self._lookup_replay('C14.append_event', key, canonical)
        if replay is not None:
            return replay
        if work is not None:
            row = connection.execute('SELECT revision,epoch FROM v5_intake_work '
                                     'WHERE goal_id=? ORDER BY revision DESC LIMIT 1',
                                     (work.goal_id,)).fetchone()
            if row is None:
                return Result.failure(ErrorCode.NOT_FOUND, 'work not found')
            if row != (work.revision, work.epoch):
                return Result.failure(ErrorCode.STALE, 'work changed')
        event_id = self._append_event(session, work, kind, content, refs)
        result = Result.success({'event_id': event_id})
        self._save_replay('C14.append_event', key, canonical, result)
        return result

    def invalidate_by_refs(self, connection, *, key, session_id, refs):
        """Invalidate queued work only, within the MEM-owned source-stop transaction."""
        self._require_transaction(connection)
        try:
            _identifier(key)
            _identifier(session_id)
            if type(refs) is not tuple or any(type(ref) is not Ref for ref in refs):
                raise ContractError('wrong type')
        except ContractError as error:
            return _invalid(error)
        refs = tuple(dict.fromkeys(refs))
        canonical = dumps({'key': key, 'session_id': session_id,
                           'refs': [ref.to_json() for ref in refs]})
        command = 'TSK.invalidate_by_refs'
        replay = self._lookup_replay(command, key, canonical)
        if replay is not None:
            return replay
        rows = connection.execute(
            'SELECT w.goal_id,w.revision,w.epoch,w.state,w.origin_ref_json,w.brief_json '
            'FROM v5_intake_work w WHERE w.revision=(SELECT max(x.revision) '
            'FROM v5_intake_work x WHERE x.goal_id=w.goal_id) ORDER BY w.goal_id').fetchall()
        affected = []
        for goal_id, revision, epoch, state, origin_json, brief_json in rows:
            expected = {Ref.from_json(loads(origin_json)),
                        *Brief.from_json(loads(brief_json)).context_refs}
            stored = {Ref(kind, ident) for kind, ident in connection.execute(
                'SELECT kind,id FROM v5_intake_source WHERE goal_id=? AND revision=?',
                (goal_id, revision))}
            # Existing data without its owner index must not silently evade a stop.
            if not expected <= stored:
                return _unavailable('source dependencies unavailable')
            matched = tuple(ref for ref in refs if ref in stored)
            if matched:
                if state != 'queued' or epoch >= _SQLITE_INT_MAX:
                    return _unavailable('work invalidation unavailable')
                affected.append((WorkRef(goal_id, revision, epoch + 1), matched))
        for work, matched in affected:
            connection.execute('UPDATE v5_intake_work SET epoch=? WHERE goal_id=? AND revision=?',
                               (work.epoch, work.goal_id, work.revision))
            result = self.append_event(connection, {
                'key': dumps([command, key, 'event', work.goal_id]), 'session_id': session_id,
                'work_ref': work.to_json(), 'kind': 'state', 'text': 'source use stopped',
                'refs': [ref.to_json() for ref in matched]})
            if not result.ok:
                return result
        result = Result.success({'work_refs': [work.to_json() for work, _ in affected]})
        self._save_replay(command, key, canonical, result)
        return result

    def _lookup_replay(self, command, key, canonical):
        row = self._conn.execute('SELECT input_json,result_json FROM v5_intake_replay '
                                 'WHERE command=? AND key=?', (command, key)).fetchone()
        if row is None:
            return None
        if row[0] != canonical:
            return Result.failure(ErrorCode.CONFLICT, 'key reused with different input')
        return Result.from_json(loads(row[1]))

    def _save_replay(self, command, key, canonical, result):
        self._conn.execute('INSERT INTO v5_intake_replay VALUES (?,?,?,?)',
                           (command, key, canonical, dumps(result)))

    def _require_transaction(self, connection):
        if (connection is not self._conn or connection.isolation_level is not None
                or not connection.in_transaction):
            raise ValueError('callback requires the same active transaction')

    def _create_locked(self, key, session_id, origin, draft, scope, canonical):
        conn = self._conn
        row = conn.execute('SELECT input_json, result_json FROM v5_intake_replay'
                           ' WHERE command = ? AND key = ?', (_COMMAND, key)).fetchone()
        if row is not None:
            if row[0] != canonical:
                return Result.failure(ErrorCode.CONFLICT, 'key reused with different input'), False
            return Result.from_json(loads(row[1])), False
        grant = _intersect(self._host_grant, scope)
        if draft.target.repository not in grant.repositories:
            return Result.failure(ErrorCode.DENIED, 'target repository not granted'), False
        rejected = self._check_sources((origin, *draft.context_refs))
        if rejected is not None:
            return rejected, False
        goal_id = self._mint('goal')
        conditions = tuple(Condition(self._mint('condition'), item.description, item.check)
                           for item in draft.conditions)
        if len({item.id for item in conditions}) != len(conditions):
            raise ValueError('duplicate condition id')
        brief = Brief(draft.purpose, draft.target, draft.constraints, conditions,
                      draft.context_refs)
        work_ref = WorkRef(goal_id, 1, 0)
        result = Result.success({'work_ref': work_ref.to_json(), 'expert_id': self._expert_id,
                                 'state': 'queued', 'grant': grant.to_json()})
        conn.execute('INSERT INTO v5_intake_work (goal_id, revision, epoch, state, brief_json,'
                     ' grant_json, session_id, origin_ref_json, expert_id)'
                     ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (goal_id, 1, 0, 'queued', dumps(brief), dumps(grant), session_id,
                      dumps(origin), self._expert_id))
        conn.executemany('INSERT INTO v5_intake_source VALUES (?,?,?,?)',
                         [(goal_id, 1, ref.kind.value, ref.id)
                          for ref in dict.fromkeys((origin, *draft.context_refs))])
        self._append_event(session_id, work_ref, 'accepted', 'work accepted', (origin,))
        conn.execute('INSERT INTO v5_intake_replay (command, key, input_json, result_json)'
                     ' VALUES (?, ?, ?, ?)', (_COMMAND, key, canonical, dumps(result)))
        return result, True

    def _check_sources(self, refs):
        """Run the trusted gate inside this transaction; None means available."""
        conn = self._conn
        changes = conn.total_changes
        conn.execute('SAVEPOINT v5_intake_gate')
        try:
            outcome = self._source_gate(conn, refs)
        except Exception:
            outcome = None
        if not conn.in_transaction:
            return _unavailable('source unavailable')
        # Raises if the gate committed or rolled back and then opened a new transaction.
        conn.execute('RELEASE v5_intake_gate')
        if conn.total_changes != changes:
            return _unavailable('source unavailable')
        if type(outcome) is not str or outcome not in GATE_OUTCOMES:
            return _unavailable('source unavailable')
        if outcome == 'available':
            return None
        return Result.failure(*_GATE_ERRORS[outcome])

    def _append_event(self, session_id, work_ref, kind, text, refs):
        """Internal C14-shaped writer on the open transaction; it never commits."""
        event_id = self._mint('event')
        self._conn.execute('INSERT INTO v5_intake_event (event_id, session_id, work_ref_json,'
                           ' kind, text, refs_json) VALUES (?, ?, ?, ?, ?, ?)',
                           (event_id, session_id,
                            None if work_ref is None else dumps(work_ref), kind, text,
                            dumps([ref.to_json() for ref in refs])))
        return event_id

    def _mint(self, prefix):
        value = self._id_factory(prefix)
        if not _valid_id(value):
            raise ValueError('id_factory returned an invalid id')
        return value

    def _require_idle(self):
        if self._conn.isolation_level is not None or self._conn.in_transaction:
            raise ValueError('create requires an idle isolation_level=None connection')

    def _rollback(self):
        if self._conn.in_transaction:
            self._conn.execute('ROLLBACK')
