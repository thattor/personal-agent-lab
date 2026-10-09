"""Transactional execution rights for a trusted local mock host (TSK02/1)."""
from functools import wraps
from contextlib import contextmanager
import uuid
import sqlite3

from pal.contracts_v5 import (Brief, Condition, DraftBrief, ContractError, Grant, Limits, Ref, Result,
                              WorkRef, dumps, loads, parse_model_action, action_from_json)
from pal.intake_v5 import IntakeStore, _intersect

_MAX = 2**63 - 1
_PROFILE = "managed-inprocess-mock/1"
_CALL_STATES = ("admitted", "returned", "raised", "not_entered", "interrupted")


class _Rejected(Exception):
    def __init__(self, result):
        self.result = result


def _reject(code):
    raise _Rejected(Result.failure(code, 'task request ' + code))


def _public(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except ContractError:
            return Result.failure('invalid_input', 'invalid task request')
        except _Rejected as error:
            return error.result
        except Exception:
            return Result.failure('unavailable', 'task store unavailable')
    return wrapped


def _obj(value, required, optional=()):
    value = loads(dumps(value))
    if type(value) is not dict or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise ContractError()
    return value


def _id(value):
    if type(value) is not str or not value:
        raise ContractError()
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ContractError('invalid utf-8') from None
    return value


def _work(value):
    work = WorkRef.from_json(value)
    if max(work.revision, work.epoch) > _MAX:
        raise ContractError()
    return work


def _refs(value):
    if type(value) is not list:
        raise ContractError()
    return tuple(dict.fromkeys(Ref.from_json(item) for item in value))


def _wire(refs):
    return [ref.to_json() for ref in refs]


class TaskStore(IntakeStore):
    def __init__(self, connection, *, host_limits, artifact_inspect=None, verification_inspect=None,
                 startup_guard=None, **kwargs):
        self._startup_guard = startup_guard
        if startup_guard is not None:
            from pal.mock_host_v5 import MockHostSession
            if type(startup_guard) is not MockHostSession:
                raise TypeError('exact mock host required')
            startup_guard.check_connection(connection)
            with startup_guard.operation():
                self._initialize(connection, host_limits, artifact_inspect, verification_inspect, kwargs)
        else:
            self._initialize(connection, host_limits, artifact_inspect, verification_inspect, kwargs)

    @property
    def startup_guard(self):
        return self._startup_guard

    def _initialize(self, connection, host_limits, artifact_inspect, verification_inspect, kwargs):
        if type(host_limits) is not Limits or any(x > _MAX for x in
                (host_limits.max_operations, host_limits.max_steps, host_limits.max_model_calls)):
            raise ValueError('finite SQLite host limits required')
        if artifact_inspect is not None and not callable(artifact_inspect):
            raise TypeError('artifact_inspect must be callable')
        if verification_inspect is not None and not callable(verification_inspect):
            raise TypeError('verification_inspect must be callable')
        self._verification_inspect = verification_inspect
        self._artifact_inspect = artifact_inspect
        super().__init__(connection, **kwargs)
        schema = (
            'CREATE TABLE IF NOT EXISTS v5_tsk_enrollment (singleton INTEGER PRIMARY KEY CHECK(singleton=1),db_uuid TEXT NOT NULL,profile TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_session (id TEXT PRIMARY KEY,runner TEXT NOT NULL UNIQUE,db_uuid TEXT NOT NULL,profile TEXT NOT NULL,orphan TEXT)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_lease_owner (lease TEXT PRIMARY KEY,session TEXT NOT NULL,claim_work TEXT NOT NULL)',

            "CREATE TABLE IF NOT EXISTS v5_tsk_question (id TEXT PRIMARY KEY,goal TEXT NOT NULL,revision INTEGER NOT NULL,step_id TEXT NOT NULL UNIQUE,question TEXT NOT NULL,missing_fact TEXT NOT NULL,sources TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('open','answered','closed','superseded')),answer_ref TEXT)",
            "CREATE UNIQUE INDEX IF NOT EXISTS v5_tsk_one_question ON v5_tsk_question(goal) WHERE status='open'",
            'CREATE TABLE IF NOT EXISTS v5_tsk_artifact_set (seq INTEGER PRIMARY KEY,goal TEXT NOT NULL,revision INTEGER NOT NULL,artifact_id TEXT NOT NULL,step_id TEXT NOT NULL,UNIQUE(goal,revision,artifact_id),UNIQUE(goal,revision,step_id))',
            'CREATE TABLE IF NOT EXISTS v5_tsk_lease (id TEXT PRIMARY KEY,runner TEXT NOT NULL,goal TEXT NOT NULL,revision INTEGER NOT NULL,active INTEGER NOT NULL)',
            'CREATE UNIQUE INDEX IF NOT EXISTS v5_tsk_one_lease ON v5_tsk_lease(active) WHERE active=1',
            'CREATE TABLE IF NOT EXISTS v5_tsk_control (goal TEXT,revision INTEGER,pause INTEGER NOT NULL,drain INTEGER NOT NULL,PRIMARY KEY(goal,revision))',
            'CREATE TABLE IF NOT EXISTS v5_tsk_host (kind TEXT PRIMARY KEY,ceiling INTEGER NOT NULL,used INTEGER NOT NULL)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_usage (goal TEXT,kind TEXT,used INTEGER NOT NULL,PRIMARY KEY(goal,kind))',
            'CREATE TABLE IF NOT EXISTS v5_tsk_reservation (id TEXT PRIMARY KEY,lease TEXT,work TEXT,idx INTEGER,kind TEXT,role TEXT,binding TEXT)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_call (id TEXT PRIMARY KEY,lease TEXT,work TEXT,idx INTEGER,reservation TEXT,sources TEXT NOT NULL,status TEXT,step TEXT,UNIQUE(lease,idx))',
            'CREATE TABLE IF NOT EXISTS v5_tsk_step (id TEXT PRIMARY KEY,goal TEXT,revision INTEGER,idx INTEGER,call TEXT UNIQUE,wire TEXT NOT NULL,truncated INTEGER NOT NULL,excluded TEXT NOT NULL,UNIQUE(goal,revision,idx))',
        )
        connection.execute('BEGIN IMMEDIATE')
        try:
            for statement in schema:
                connection.execute(statement)
            for kind, ceiling in [('model', host_limits.max_model_calls), ('step', host_limits.max_steps)]:
                connection.execute('INSERT INTO v5_tsk_host VALUES (?,?,0) ON CONFLICT(kind) DO UPDATE SET ceiling=excluded.ceiling', (kind, ceiling))
            connection.execute('COMMIT')
        except BaseException:
            self._rollback()
            raise

    def _rows(self, sql, args=()):
        cursor = self._conn.execute(sql, args)
        names = [item[0] for item in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]

    def _one(self, sql, args=()):
        rows = self._rows(sql, args)
        return rows[0] if rows else None

    @contextmanager
    def _host_permit(self):
        guard = self._startup_guard
        if guard is None:
            yield
        else:
            guard.check_connection(self._conn)
            with guard.operation():
                guard.check_connection(self._conn)
                yield

    def _enrollment(self):
        rows = self._rows('SELECT * FROM v5_tsk_enrollment')
        if not rows:
            if (self._one('SELECT id FROM v5_tsk_session LIMIT 1') or
                    self._one('SELECT lease FROM v5_tsk_lease_owner LIMIT 1') or
                    (self._startup_guard is not None and self._startup_guard.db_uuid is not None)):
                _reject('unavailable')
            return None
        if len(rows) != 1:
            _reject('unavailable')
        row = rows[0]
        try:
            if (row['singleton'] != 1 or row['profile'] != _PROFILE or
                    type(row['db_uuid']) is not str or uuid.UUID(row['db_uuid']).hex != row['db_uuid']):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            _reject('unavailable')
        guard = self._startup_guard
        if guard is not None and guard.db_uuid is not None and guard.db_uuid != row['db_uuid']:
            _reject('unavailable')
        return row

    def _session(self, identity, enrollment):
        session = self._one('SELECT * FROM v5_tsk_session WHERE id=?', (identity,))
        try:
            if session is None or enrollment is None:
                raise ContractError()
            _id(session['id'])
            _id(session['runner'])
            if session['orphan'] is not None:
                _id(session['orphan'])
            if (session['db_uuid'], session['profile']) != (enrollment['db_uuid'], _PROFILE):
                raise ContractError()
        except ContractError:
            _reject('unavailable')
        return session

    def _own_session(self, *, ready=False):
        guard = self._startup_guard
        if guard is None:
            _reject('unavailable')
        guard.check_connection(self._conn)
        if ready and guard.phase != 'ready':
            _reject('conflict')
        enrollment = self._enrollment()
        session = self._session(guard.session_id, enrollment)
        if (session['runner'] != guard.runner_id or guard.db_uuid != session['db_uuid'] or
                guard.orphan_lease_id != session['orphan']):
            _reject('unavailable')
        return session

    def _lease_binding(self, lease, enrollment):
        try:
            _id(lease['id'])
            _id(lease['runner'])
            if type(lease['active']) is not int or lease['active'] not in (0, 1):
                raise ContractError()
            binding = self._one('SELECT * FROM v5_tsk_lease_owner WHERE lease=?', (lease['id'],))
            if binding is None:
                raise ContractError()
            _id(binding['session'])
            claim = _work(loads(binding['claim_work']))
            if claim.epoch < 1 or (claim.goal_id, claim.revision) != (lease['goal'], lease['revision']):
                raise ContractError()
            session = self._session(binding['session'], enrollment)
            if lease['runner'] != session['runner']:
                raise ContractError()
        except ContractError:
            _reject('unavailable')
        return session, claim

    def _execution(self, lease=None):
        enrollment = self._enrollment()
        if enrollment is None and self._startup_guard is None:
            return
        session = self._own_session(ready=True)
        if lease is not None:
            owner, _ = self._lease_binding(lease, enrollment)
            if owner['id'] != session['id']:
                _reject('denied')

    def _execution_request(self, command, request):
        execution = command in ('claim', 'admit_call', 'end_call', 'begin_step', 'finish_step',
                                'C04.ask', 'release', 'reserve_budget', 'consume', 'register')
        if command == 'control':
            execution = type(request['command']) is dict and request['command'].get('kind') == 'complete'
        if not execution:
            return
        data = request['request'] if command == 'finish_step' else request
        self._execution()
        lease = None
        if 'lease_id' in data:
            lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (data['lease_id'],))
        elif command == 'end_call':
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (data['call_id'],))
            if call is not None:
                lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (call['lease'],))
                if lease is None:
                    _reject('unavailable')
        elif command == 'consume':
            reservation = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (data['reservation_id'],))
            if reservation is not None:
                lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (reservation['lease'],))
                if lease is None:
                    _reject('unavailable')
        elif 'work_ref' in data:
            work = _work(data['work_ref'])
            if self._enrollment() is not None:
                owners = self._rows('SELECT lease FROM v5_tsk_lease_owner WHERE claim_work=?', (dumps(work),))
                if len(owners) > 1:
                    _reject('unavailable')
                if owners:
                    lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (owners[0]['lease'],))
                    if lease is None:
                        _reject('unavailable')
            if lease is None:
                lease = self._one('SELECT * FROM v5_tsk_lease WHERE goal=? AND revision=? AND active=1',
                                  (work.goal_id, work.revision))
        if lease is not None:
            self._execution(lease)

    def _transaction(self, command, key, request, operation):
        with self._host_permit():
            self._require_idle()
            self._conn.execute('BEGIN IMMEDIATE')
            try:
                if command == 'recover':
                    self._own_session()
                    if self._startup_guard.phase != 'startup':
                        _reject('conflict')
                self._execution_request(command, request)
                canonical = dumps(request)
                result = self._lookup_replay(command, key, canonical) if key is not None else None
                if result is None:
                    value = operation()
                    result = Result.success(value)
                    if key is not None and not (command == 'recover' and value.get('disposition') == 'held'):
                        self._save_replay(command, key, canonical, result)
                self._conn.execute('COMMIT')
                return result
            except BaseException:
                self._rollback()
                raise

    @_public
    def register_host(self):
        guard = self._startup_guard
        if guard is None:
            _reject('unavailable')
        def operation():
            if guard.phase not in ('owned', 'startup'):
                _reject('conflict')
            enrollment = self._enrollment()
            if enrollment is None:
                enrollment = {'db_uuid': uuid.uuid4().hex, 'profile': _PROFILE}
                self._conn.execute('INSERT INTO v5_tsk_enrollment VALUES (1,?,?)',
                                   (enrollment['db_uuid'], _PROFILE))
            saved = self._one('SELECT * FROM v5_tsk_session WHERE id=?', (guard.session_id,))
            if saved is None:
                if guard.phase != 'owned' or guard.db_uuid is not None:
                    _reject('unavailable')
                leases = self._rows('SELECT * FROM v5_tsk_lease WHERE active=1')
                if len(leases) > 1:
                    _reject('unavailable')
                orphan = leases[0]['id'] if leases else None
                self._conn.execute('INSERT INTO v5_tsk_session VALUES (?,?,?,?,?)',
                    (guard.session_id, guard.runner_id, enrollment['db_uuid'], _PROFILE, orphan))
            saved = self._session(guard.session_id, enrollment)
            if saved['runner'] != guard.runner_id:
                _reject('unavailable')
            return {'session_id': saved['id'], 'runner_id': saved['runner'], 'orphan_lease_id': saved['orphan']}
        with self._host_permit():
            result = self._transaction('register_host', None, {}, operation)
            value = result.value.to_json()
            guard.mark_registered(self._enrollment()['db_uuid'], value['orphan_lease_id'])
            return result

    @_public
    def finish_startup(self):
        def operation():
            session = self._own_session()
            if self._startup_guard.phase not in ('startup', 'ready'):
                _reject('conflict')
            if self._startup_guard.phase != 'ready' and self._one('SELECT id FROM v5_tsk_lease WHERE active=1'):
                _reject('conflict')
            return {'session_id': session['id'], 'runner_id': session['runner'], 'status': 'ready'}
        with self._host_permit():
            result = self._transaction('finish_startup', None, {}, operation)
            if self._startup_guard.phase != 'ready':
                self._startup_guard.activate()
            return result

    @staticmethod
    def _latest_intent(row, flags, *, fallback, opened=False):
        if row['state'] in ('completed', 'cancelled', 'failed'):
            return row['state']
        if flags['pause'] or (opened and row['state'] == 'paused'):
            return 'paused'
        return 'waiting_input' if opened else fallback

    @_public
    def recover(self, request):
        data = _obj(request, {'key', 'lease_id'})
        key, lease_id = _id(data['key']), _id(data['lease_id'])
        with self._host_permit():
            if self._startup_guard is None:
                _reject('unavailable')
            if self._startup_guard.phase != 'startup':
                _reject('conflict')
            return self._transaction('recover', key, data, lambda: self._recover(lease_id))

    def _recover(self, lease_id):
        try:
            return self._recover_owned(lease_id)
        except (ContractError, KeyError, TypeError, ValueError):
            _reject('unavailable')

    def _recover_owned(self, lease_id):
        session = self._own_session()
        lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (lease_id,))
        if lease is None:
            _reject('not_found')
        if lease['active'] == 0:
            _reject('conflict')
        if lease_id != session['orphan']:
            _reject('conflict')
        owner, claim = self._lease_binding(lease, self._enrollment())
        if owner['id'] == session['id']:
            _reject('unavailable')
        old = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (lease['goal'], lease['revision']))
        row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? ORDER BY revision DESC LIMIT 1', (lease['goal'],))
        if (old is None or row is None or claim.epoch > old['epoch'] or
                (old['revision'] != row['revision'] and old['state'] != 'superseded') or
                row['state'] not in ('queued', 'running', 'waiting_input', 'paused', 'completed', 'cancelled', 'failed')):
            _reject('unavailable')
        flags = self._flags(row)
        if any(type(flags[k]) is not int or flags[k] not in (0, 1) for k in ('pause', 'drain')):
            _reject('unavailable')
        self._questions(old)
        questions = self._questions(row)
        self._artifact_set(self._wr(old))
        self._artifact_set(self._wr(row))
        calls = self._old_calls(old, lease, claim=claim)
        started = []
        for call in calls:
            if call['step'] is not None:
                step = loads(self._one('SELECT wire FROM v5_tsk_step WHERE id=?', (call['step'],))['wire'])
                if step['status'] == 'started':
                    started.append(step)
        for step in started:
            if step['action']['kind'] in ('compose', 'operate'):
                return {'disposition': 'held', 'work_ref': self._wr(row).to_json(), 'state': row['state'],
                    'control_status': 'pause_requested' if flags['pause'] else 'draining' if flags['drain'] else 'none',
                    'lease_id': lease_id, 'step_id': step['step_id'],
                    'reason': 'artifact_tail' if step['action']['kind'] == 'compose' else 'external_tail'}
        if row['state'] not in ('completed', 'cancelled', 'failed'):
            if type(row['epoch']) is not int or not 0 <= row['epoch'] < _MAX:
                _reject('unavailable')
            row['epoch'] += 1
        event_id = self._change_mint('event')
        interrupted = [call['id'] for call in calls if call['status'] == 'admitted']
        for call_id in interrupted:
            self._conn.execute("UPDATE v5_tsk_call SET status='interrupted' WHERE id=?", (call_id,))
        for step in started:
            step['status'] = 'abandoned'
            self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), step['step_id']))
        opened = any(q['status'] == 'open' for q in questions)
        state = 'paused' if row['state'] == 'paused' else self._latest_intent(row, flags, fallback='queued', opened=opened)
        row['state'] = state
        self._conn.execute('UPDATE v5_intake_work SET state=?,epoch=? WHERE goal_id=? AND revision=?',
                           (state, row['epoch'], row['goal_id'], row['revision']))
        self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
        self._set_flags(row, 0, 0)
        self._conn.execute('INSERT INTO v5_intake_event (event_id,session_id,work_ref_json,kind,text,refs_json) VALUES (?,?,?,?,?,?)',
            (event_id, row['session_id'], dumps(self._wr(row)), 'state', 'mock execution recovered', '[]'))
        return {'disposition': 'settled', 'work_ref': self._wr(row).to_json(), 'state': state,
                'control_status': 'none', 'recovered_lease_id': lease_id, 'interrupted_call_ids': interrupted}

    def _current(self, work, epoch=True):
        row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? ORDER BY revision DESC LIMIT 1', (work.goal_id,))
        if row is None:
            _reject('not_found')
        if row['revision'] != work.revision or (epoch and row['epoch'] != work.epoch):
            _reject('stale')
        return row

    def _wr(self, row):
        return WorkRef(row['goal_id'], row['revision'], row['epoch'])

    def _flags(self, row):
        return self._one('SELECT * FROM v5_tsk_control WHERE goal=? AND revision=?',
                         (row['goal_id'], row['revision'])) or {'pause': 0, 'drain': 0}

    def _set_flags(self, row, pause, drain):
        self._conn.execute('INSERT INTO v5_tsk_control VALUES (?,?,?,?) ON CONFLICT(goal,revision) DO UPDATE SET pause=excluded.pause,drain=excluded.drain',
                           (row['goal_id'], row['revision'], pause, drain))

    def _authority(self, work, lease_id=None):
        row = self._current(work)
        lease = self._one('SELECT * FROM v5_tsk_lease WHERE active=1')
        if lease_id is not None and self._one('SELECT id FROM v5_tsk_lease WHERE id=?', (lease_id,)) is None:
            _reject('not_found')
        if lease is None or (lease_id is not None and lease['id'] != lease_id) or (lease['goal'], lease['revision']) != (work.goal_id, work.revision):
            _reject('denied')
        self._execution(lease)
        flags = self._flags(row)
        if row['state'] != 'running' or flags['pause'] or flags['drain']:
            _reject('conflict')
        return row, lease

    def _required(self, row):
        return tuple(dict.fromkeys((Ref.from_json(loads(row['origin_ref_json'])),
                                   *Brief.from_json(loads(row['brief_json'])).context_refs)))

    def _registered(self, row):
        return tuple(Ref(item['kind'], item['id']) for item in self._rows(
            'SELECT kind,id FROM v5_intake_source WHERE goal_id=? AND revision=? ORDER BY rowid', (row['goal_id'], row['revision'])))

    def _gate(self, refs):
        result = self._check_sources(refs)
        if result is not None:
            raise _Rejected(result)

    def _register(self, row, refs):
        self._conn.executemany('INSERT OR IGNORE INTO v5_intake_source VALUES (?,?,?,?)',
            [(row['goal_id'], row['revision'], ref.kind.value, ref.id) for ref in refs])

    def _steps(self, row):
        return self._rows('SELECT * FROM v5_tsk_step WHERE goal=? AND revision=? ORDER BY idx', (row['goal_id'], row['revision']))

    def _index(self, row):
        steps = self._steps(row)
        return steps[-1]['idx'] + 1 if steps else 0

    def _remaining(self, row):
        limits = Grant.from_json(loads(row['grant_json'])).limits
        result = {}
        for kind, ceiling in [('model', limits.max_model_calls), ('step', limits.max_steps)]:
            host = self._one('SELECT * FROM v5_tsk_host WHERE kind=?', (kind,))
            used = self._one('SELECT used FROM v5_tsk_usage WHERE goal=? AND kind=?', (row['goal_id'], kind))
            result[kind] = {'work': max(0, ceiling - (used['used'] if used else 0)), 'host': max(0, host['ceiling'] - host['used'])}
        return result

    def _headroom(self, row, kind):
        if min(self._remaining(row)[kind].values()) <= 0:
            _reject('limit')

    def _reserve(self, row, lease, kind, role):
        self._headroom(row, kind)
        if kind == 'model':
            self._headroom(row, 'step')
        reservation = self._mint('reservation')
        self._conn.execute('UPDATE v5_tsk_host SET used=used+1 WHERE kind=?', (kind,))
        self._conn.execute('INSERT INTO v5_tsk_usage VALUES (?,?,1) ON CONFLICT(goal,kind) DO UPDATE SET used=used+1', (row['goal_id'], kind))
        self._conn.execute('INSERT INTO v5_tsk_reservation VALUES (?,?,?,?,?,?,NULL)',
                           (reservation, lease['id'], dumps(self._wr(row)), self._index(row), kind, role))
        return {'reservation_id': reservation, 'remaining': self._remaining(row)[kind]}

    def _bind(self, reservation, binding):
        item = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (reservation,))
        if item is None:
            _reject('not_found')
        if item['binding'] is not None and item['binding'] != binding:
            _reject('conflict')
        self._conn.execute('UPDATE v5_tsk_reservation SET binding=? WHERE id=?', (binding, reservation))
        return {'reservation_id': reservation, 'call_or_operation_id': binding}

    def _event(self, row, kind, text, refs=()):
        self._append_event(row['session_id'], self._wr(row), kind, text, refs)

    def _claim_wire(self, row, lease):
        steps = self._steps(row)
        finished = [step for step in steps if loads(step['wire'])['status'] == 'finished']
        questions = self._questions(row)
        checkpoint = {'last_finished_index': -1, 'open_question_refs': [q['id'] for q in questions if q['status'] == 'open']}
        if finished:
            last = finished[-1]
            checkpoint['last_finished_index'] = last['idx']
            if loads(last['wire'])['action']['kind'] == 'lookup':
                checkpoint.update(lookup_truncated=bool(last['truncated']), lookup_excluded_refs=loads(last['excluded']))
        return {'lease_id': lease['id'], 'work_ref': self._wr(row).to_json(), 'brief': loads(row['brief_json']),
                'grant': loads(row['grant_json']), 'checkpoint': checkpoint,
                'steps': [loads(step['wire']) for step in steps], 'pending_inputs': [
                    {'question_id': q['id'], 'step_id': q['step_id'], 'answer_record_ref': q['answer']}
                    for q in questions if q['status'] == 'answered']}

    @_public
    def claim(self, request):
        data = _obj(request, {'runner_id'})
        runner = _id(data['runner_id'])
        def operation():
            if self._enrollment() is not None and runner != self._startup_guard.runner_id:
                _reject('denied')
            lease = self._one('SELECT * FROM v5_tsk_lease WHERE active=1')
            if lease is not None:
                self._execution(lease)
            if lease:
                if lease['runner'] != runner:
                    _reject('conflict')
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (lease['goal'], lease['revision']))
                return self._claim_wire(row, lease)
            row = self._one("SELECT * FROM v5_intake_work w WHERE state='queued' AND revision=(SELECT MAX(revision) FROM v5_intake_work WHERE goal_id=w.goal_id) ORDER BY rowid LIMIT 1")
            if row is None:
                return {'status': 'empty'}
            for host in self._rows('SELECT * FROM v5_tsk_host'):
                if host['used'] >= host['ceiling']:
                    _reject('limit')
            if row['epoch'] == _MAX:
                _reject('unavailable')
            row.update(epoch=row['epoch'] + 1, state='running')
            self._conn.execute('UPDATE v5_intake_work SET state=?,epoch=? WHERE goal_id=? AND revision=?',
                               ('running', row['epoch'], row['goal_id'], row['revision']))
            lease = {'id': self._mint('lease')}
            self._conn.execute('INSERT INTO v5_tsk_lease VALUES (?,?,?,?,1)', (lease['id'], runner, row['goal_id'], row['revision']))
            if self._enrollment() is not None:
                self._conn.execute('INSERT INTO v5_tsk_lease_owner VALUES (?,?,?)',
                    (lease['id'], self._startup_guard.session_id, dumps(self._wr(row))))
            self._event(row, 'state', 'work running')
            return self._claim_wire(row, lease)
        return self._transaction('claim', None, data, operation)

    def _artifact_set(self, work):
        rows = self._rows('SELECT * FROM v5_tsk_artifact_set WHERE goal=? AND revision=? ORDER BY seq',
                          (work.goal_id, work.revision))
        try:
            for item in rows:
                _id(item['artifact_id'])
                _id(item['step_id'])
                if type(item['seq']) is not int or item['seq'] < 1:
                    raise ContractError()
                saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (item['step_id'],))
                if saved is None or (saved['goal'], saved['revision']) != (work.goal_id, work.revision):
                    raise ContractError()
                step = loads(saved['wire'])
                if (step['step_id'] != item['step_id'] or step['status'] != 'finished' or
                        step['action']['kind'] != 'compose' or
                        step['result_refs'] != [{'kind': 'artifact', 'id': item['artifact_id']}]):
                    raise ContractError()
                binding = _work(step['work_ref'])
                if (binding.goal_id, binding.revision) != (work.goal_id, work.revision):
                    raise ContractError()
            expected = {}
            for saved in self._rows('SELECT id,wire FROM v5_tsk_step WHERE goal=? AND revision=?',
                                    (work.goal_id, work.revision)):
                step = loads(saved['wire'])
                if step['status'] == 'finished' and step['action']['kind'] == 'compose':
                    results = _refs(step['result_refs'])
                    if (step['step_id'] != saved['id'] or len(step['result_refs']) != 1 or
                            results[0].kind.value != 'artifact'):
                        raise ContractError()
                    expected[saved['id']] = results[0].id
            if expected != {item['step_id']: item['artifact_id'] for item in rows}:
                raise ContractError()
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')
        return rows

    @_public
    def get_work(self, request):
        result = super().get_work(request)
        if not result.ok:
            return result
        value = result.value.to_json()
        rows = self._artifact_set(_work(value['work_ref']))
        row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?',
                        (value['work_ref']['goal_id'], value['work_ref']['revision']))
        value['open_questions'] = [{'id': q['id'], 'text': q['question'], 'revision': q['revision']}
                                   for q in self._questions(row) if q['status'] == 'open']
        value['current_artifact_refs'] = [{'kind': 'artifact', 'id': row['artifact_id']} for row in rows]
        return Result.success(value)

    @_public
    def get_execution_context(self, request):
        data = _obj(request, {'lease_id', 'work_ref'})
        row, _ = self._authority(_work(data['work_ref']), _id(data['lease_id']))
        required = self._required(row)
        registered = self._registered(row)
        if not set(required) <= set(registered):
            _reject('unavailable')
        attached = {item['step_id']: item['artifact_id'] for item in self._artifact_set(self._wr(row))}
        provenance = []
        for step in self._steps(row):
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (step['call'],))
            if call is None or call['step'] != step['id']:
                _reject('unavailable')
            inputs = _refs(loads(call['sources']))
            wire = loads(step['wire'])
            results = _refs(wire['result_refs'])
            refs = tuple(dict.fromkeys((*inputs, *results)))
            if (any(ref.kind.value != 'record' for ref in inputs) or
                    not set(inputs) <= set(registered) or not set(required) <= set(inputs)):
                _reject('unavailable')
            if wire['action']['kind'] == 'compose' and wire['status'] == 'finished':
                if (len(wire['result_refs']) != 1 or step['id'] not in attached or
                        results != (Ref('artifact', attached[step['id']]),)):
                    _reject('unavailable')
            elif any(ref.kind.value == 'artifact' for ref in results) or not set(results) <= set(registered):
                _reject('unavailable')
            provenance.append({'step_id': step['id'], 'refs': _wire(refs)})
        return Result.success({'session_id': row['session_id'], 'required_refs': _wire(required),
            'optional_refs': _wire(ref for ref in registered if ref not in required),
            'remaining_budget': self._remaining(row), 'next_step_index': self._index(row), 'step_sources': provenance})

    @_public
    def register_sources(self, request):
        data = _obj(request, {'work_ref', 'refs'})
        work, refs = _work(data['work_ref']), _refs(data['refs'])
        def operation():
            row, _ = self._authority(work)
            self._gate(refs)
            self._register(row, refs)
            return {'refs': _wire(refs)}
        return self._transaction('register', None, data, operation)

    @_public
    def reserve_budget(self, request):
        data = _obj(request, {'key', 'kind'}, {'work_ref', 'role'})
        key = _id(data['key'])
        if data['kind'] not in ('model', 'step', 'operation'):
            raise ContractError()
        if 'work_ref' not in data or data['kind'] == 'operation':
            _reject('unavailable')
        work = _work(data['work_ref'])
        role = data.get('role')
        if data['kind'] == 'model' and role != 'expert' or data['kind'] == 'step' and role is not None:
            raise ContractError()
        def operation():
            row, lease = self._authority(work)
            return self._reserve(row, lease, data['kind'], role)
        return self._transaction('reserve_budget', key, data, operation)

    @_public
    def consume(self, request):
        data = _obj(request, {'reservation_id', 'call_or_operation_id'})
        reservation, binding = _id(data['reservation_id']), _id(data['call_or_operation_id'])
        return self._transaction('consume', reservation, data, lambda: self._bind(reservation, binding))

    @_public
    def admit_call(self, request):
        data = _obj(request, {'call_id', 'lease_id', 'work_ref', 'reservation_id', 'source_refs'})
        call_id, lease_id, reservation = (_id(data[name]) for name in ('call_id', 'lease_id', 'reservation_id'))
        work, refs = _work(data['work_ref']), _refs(data['source_refs'])
        def operation():
            row, lease = self._authority(work, lease_id)
            index = self._index(row)
            if call_id != dumps(['C15.call', lease_id, index]):
                _reject('conflict')
            for call in self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease_id,)):
                step = self._one('SELECT wire FROM v5_tsk_step WHERE id=?', (call['step'],))
                if call['status'] != 'returned' or step is None or loads(step['wire'])['status'] != 'finished':
                    _reject('conflict')
            if any(loads(step['wire'])['status'] == 'started' for step in self._steps(row)):
                _reject('conflict')
            if not set(self._required(row)) <= set(refs) <= set(self._registered(row)):
                _reject('denied')
            item = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (reservation,))
            if item is None:
                _reject('not_found')
            if (item['lease'], item['work'], item['idx'], item['kind'], item['role']) != (lease_id, dumps(work), index, 'model', 'expert'):
                _reject('conflict')
            self._headroom(row, 'step')
            self._gate(refs)
            self._bind(reservation, call_id)
            self._conn.execute('INSERT INTO v5_tsk_call VALUES (?,?,?,?,?,?,?,NULL)',
                               (call_id, lease_id, dumps(work), index, reservation, dumps(_wire(refs)), 'admitted'))
            return {'call_id': call_id, 'status': 'admitted'}
        return self._transaction('admit_call', call_id, data, operation)

    @_public
    def end_call(self, request):
        data = _obj(request, {'call_id', 'outcome'})
        call_id = _id(data['call_id'])
        if data['outcome'] not in ('returned', 'raised', 'not_entered'):
            raise ContractError()
        def operation():
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (call_id,))
            if call is None:
                _reject('not_found')
            if call['status'] != 'admitted':
                _reject('conflict')
            self._conn.execute('UPDATE v5_tsk_call SET status=? WHERE id=?', (data['outcome'], call_id))
            return {'call_id': call_id, 'status': data['outcome']}
        return self._transaction('end_call', call_id, data, operation)

    @_public
    def get_call(self, request):
        data = _obj(request, {'call_id'})
        call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (_id(data['call_id']),))
        if call is None:
            _reject('not_found')
        if call['status'] not in _CALL_STATES or (call['status'] == 'interrupted' and call['step'] is not None):
            _reject('unavailable')
        may_enter = False
        if call['status'] == 'admitted':
            try:
                self._authority(_work(loads(call['work'])), call['lease'])
                may_enter = True
            except _Rejected:
                pass
        result = {'call_id': call['id'], 'lease_id': call['lease'], 'work_ref': loads(call['work']),
                  'index': call['idx'], 'status': call['status'], 'may_enter': may_enter}
        if call['step'] is not None or call['status'] == 'interrupted':
            result['step_id'] = call['step']
        return Result.success(result)

    @_public
    def begin_step(self, request):
        data = _obj(request, {'key', 'work_ref', 'action'})
        key, work = _id(data['key']), _work(data['work_ref'])
        def operation():
            row, lease = self._authority(work)
            index = self._index(row)
            call = self._one('SELECT * FROM v5_tsk_call WHERE lease=? AND idx=?', (lease['id'], index))
            if call is None or call['status'] != 'returned' or call['step'] is not None:
                _reject('conflict')
            refs = _refs(loads(call['sources']))
            action = parse_model_action(dumps(data['action']), allowed_refs=refs).to_json()
            if action['kind'] not in ('report', 'lookup', 'compose', 'ask'):
                _reject('unavailable')
            if action['kind'] == 'compose' and self._artifact_inspect is None:
                _reject('unavailable')
            self._gate(refs)
            reservation = self._reserve(row, lease, 'step', None)['reservation_id']
            step_id = self._mint('step')
            self._bind(reservation, step_id)
            step = {'step_id': step_id, 'work_ref': work.to_json(), 'index': index, 'action': action,
                    'status': 'started', 'result_refs': []}
            self._conn.execute('INSERT INTO v5_tsk_step VALUES (?,?,?,?,?,?,0,?)',
                               (step_id, work.goal_id, work.revision, index, call['id'], dumps(step), '[]'))
            self._conn.execute('UPDATE v5_tsk_call SET step=? WHERE id=?', (step_id, call['id']))
            return step
        return self._transaction('begin_step', key, data, operation)

    def authorize_artifact_save(self, connection, request):
        """Read-only ART collaborator; the artifact owner controls this transaction."""
        self._require_transaction(connection)
        with self._host_permit():
            return self._authorize_artifact_save(request)

    def verification_context(self, connection, request, *, purpose):
        """Readonly VER snapshot; factual status is independent of execution rights."""
        self._require_transaction(connection)
        with self._host_permit():
            return self._verification_context(request, purpose=purpose)

    @_public
    def _verification_context(self, request, *, purpose):
        data = _obj(request, {'work_ref'})
        work = _work(data['work_ref'])
        if purpose not in ('save', 'status'):
            raise ContractError()
        row = self._authority(work)[0] if purpose == 'save' else self._current(work)
        try:
            if row['state'] not in ('queued', 'running', 'paused', 'waiting_input',
                                    'completed', 'cancelled', 'failed'):
                raise ContractError()
            brief = Brief.from_json(loads(row['brief_json']))
            required = self._required(row)
            if (len({item.id for item in brief.conditions}) != len(brief.conditions) or
                    any(ref.kind.value != 'record' for ref in required) or
                    not set(required) <= set(self._registered(row))):
                raise ContractError()
            artifacts = self._artifact_set(work)
        except ContractError:
            _reject('unavailable')
        return Result.success({'work_ref': work.to_json(),
            'conditions': [item.to_json() for item in brief.conditions],
            'artifact_refs': [{'kind': 'artifact', 'id': item['artifact_id']} for item in artifacts],
            'source_refs': _wire(required)})

    @_public
    def _authorize_artifact_save(self, request):
        data = _obj(request, {'work_ref', 'step_id', 'action'})
        work, step_id = _work(data['work_ref']), _id(data['step_id'])
        action = _obj(data['action'], {'kind', 'content', 'media_type', 'source_refs'})
        requested_refs = _refs(action['source_refs'])
        if action['kind'] != 'compose':
            raise ContractError()
        action = parse_model_action(dumps(action), allowed_refs=requested_refs).to_json()
        row, lease = self._authority(work)
        saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (step_id,))
        if saved is None:
            _reject('not_found')
        call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
        if call is None:
            _reject('unavailable')
        try:
            step = _obj(loads(saved['wire']),
                        {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'}, {'error'})
            _id(step['step_id'])
            _refs(step['result_refs'])
            if (type(step['index']) is not int or not 0 <= step['index'] <= _MAX or
                    step['status'] not in ('started', 'finished', 'abandoned') or
                    ('error' in step and type(step['error']) is not str)):
                raise ContractError()
            step_work, call_work = _work(step['work_ref']), _work(loads(call['work']))
            refs = _refs(loads(call['sources']))
            stored_action = parse_model_action(dumps(step['action']), allowed_refs=refs).to_json()
        except ContractError:
            _reject('unavailable')
        if (step['step_id'] != step_id or call['step'] != step_id or
                step['index'] != saved['idx'] or step['index'] != call['idx'] or
                (saved['goal'], saved['revision']) != (step_work.goal_id, step_work.revision)):
            _reject('unavailable')
        if step_work != work or call_work != work:
            _reject('stale')
        if call['lease'] != lease['id']:
            _reject('denied')
        if step['status'] != 'started' or call['status'] != 'returned':
            _reject('conflict')
        if not set(requested_refs) <= set(refs):
            _reject('denied')
        if dumps(action) != dumps(stored_action) or stored_action['kind'] != 'compose':
            _reject('conflict')
        if (not refs or any(ref.kind.value != 'record' for ref in refs) or
                not set(self._required(row)) <= set(refs) <= set(self._registered(row))):
            _reject('unavailable')
        self._gate(refs)
        return Result.success({'source_refs': _wire(refs)})

    def _inspect_artifact(self, ref):
        if self._artifact_inspect is None:
            _reject('unavailable')
        self._require_transaction(self._conn)
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_tsk_artifact_inspect')
        result = self._artifact_inspect(self._conn, {'ref': ref.to_json()})
        if not self._conn.in_transaction:
            _reject('unavailable')
        self._conn.execute('RELEASE v5_tsk_artifact_inspect')
        if self._conn.total_changes != changes or type(result) is not Result:
            _reject('unavailable')
        try:
            result = Result.from_json(result.to_json())
        except ContractError:
            _reject('unavailable')
        if not result.ok:
            _reject(result.error.code)
        try:
            data = _obj(result.value.to_json(), {'artifact_ref', 'work_ref', 'step_id', 'hash', 'bytes', 'source_refs'})
            inspected = Ref.from_json(data['artifact_ref'])
            _work(data['work_ref'])
            _id(data['step_id'])
            deps = _refs(data['source_refs'])
            if (inspected != ref or type(data['hash']) is not str or len(data['hash']) != 64 or
                    any(char not in '0123456789abcdef' for char in data['hash']) or
                    type(data['bytes']) is not int or not 0 <= data['bytes'] <= 1048576 or
                    not deps or any(item.kind.value != 'record' for item in deps)):
                raise ContractError()
        except ContractError:
            _reject('unavailable')
        return data, deps

    def _finish_compose(self, row, step, data, refs, truncated, excluded_refs):
        if (len(data['result_refs']) != 1 or refs[0].kind.value != 'artifact' or
                'error' in data or truncated or excluded_refs):
            raise ContractError()
        authorized = self.authorize_artifact_save(self._conn, {
            'work_ref': data['work_ref'], 'step_id': data['step_id'], 'action': step['action']})
        if not authorized.ok:
            raise _Rejected(authorized)
        metadata, deps = self._inspect_artifact(refs[0])
        if metadata['work_ref'] != data['work_ref']:
            _reject('stale')
        if metadata['step_id'] != data['step_id']:
            _reject('conflict')
        if set(deps) != set(_refs(authorized.value.to_json()['source_refs'])):
            _reject('unavailable')
        self._gate(deps)
        self._artifact_set(self._wr(row))
        step.update(status='finished', result_refs=_wire(refs))
        self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), data['step_id']))
        self._conn.execute('INSERT INTO v5_tsk_artifact_set(goal,revision,artifact_id,step_id) VALUES (?,?,?,?)',
                           (row['goal_id'], row['revision'], refs[0].id, data['step_id']))
        self._register(row, deps)
        self._event(row, 'progress', 'draft saved and attached', refs)
        return step

    @_public
    def finish_step(self, request, *, truncated=False, excluded_refs=()):
        data = _obj(request, {'work_ref', 'step_id', 'result_refs'}, {'error'})
        work, step_id, refs = _work(data['work_ref']), _id(data['step_id']), _refs(data['result_refs'])
        if type(truncated) is not bool or type(excluded_refs) is not tuple or any(type(ref) is not Ref for ref in excluded_refs):
            raise ContractError()
        if 'error' in data and type(data['error']) is not str:
            raise ContractError()
        canonical = {'request': data, 'truncated': truncated, 'excluded_refs': _wire(excluded_refs)}
        def operation():
            row, lease = self._authority(work)
            saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (step_id,))
            if saved is None:
                _reject('not_found')
            step = loads(saved['wire'])
            if step['work_ref'] != work.to_json():
                _reject('stale')
            if step['action']['kind'] == 'ask':
                _reject('conflict')
            if step['status'] != 'started':
                _reject('conflict')
            if step['action']['kind'] == 'compose':
                return self._finish_compose(row, step, data, refs, truncated, excluded_refs)
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
            if call is None or call['lease'] != lease['id']:
                _reject('unavailable')
            self._gate(_refs(loads(call['sources'])))
            if step['action']['kind'] == 'report' and (refs or truncated or excluded_refs):
                raise ContractError()
            usable, excluded = [], list(excluded_refs)
            for ref in refs:
                checked = self._check_sources((ref,))
                if checked is None:
                    usable.append(ref)
                elif checked.error.code in ('denied', 'not_found'):
                    excluded.append(ref)
                else:
                    raise _Rejected(checked)
            excluded = tuple(dict.fromkeys(excluded))
            if set(usable) & set(excluded):
                raise ContractError()
            self._register(row, usable)
            step.update(status='finished', result_refs=_wire(usable))
            if 'error' in data:
                step['error'] = data['error']
            self._conn.execute('UPDATE v5_tsk_step SET wire=?,truncated=?,excluded=? WHERE id=?',
                               (dumps(step), int(truncated), dumps(_wire(excluded)), step_id))
            metadata = {'step_id': step_id, 'lookup_truncated': truncated, 'lookup_excluded_refs': _wire(excluded)}
            text = step['action']['summary'] if step['action']['kind'] == 'report' else dumps(metadata)
            if 'error' in data:
                text = data['error']
            self._event(row, 'error' if 'error' in data else 'progress', text, tuple(usable))
            return step
        return self._transaction('finish_step', step_id, canonical, operation)

    def _inspect_verification(self, ref):
        if self._verification_inspect is None:
            _reject('unavailable')
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_tsk_verification_inspect')
        try:
            result = self._verification_inspect(self._conn, {'verification_ref': ref.to_json()})
            if not self._conn.in_transaction or self._conn.total_changes != changes:
                _reject('unavailable')
            self._conn.execute('RELEASE v5_tsk_verification_inspect')
        except BaseException:
            if self._conn.in_transaction:
                try:
                    self._conn.execute('ROLLBACK TO v5_tsk_verification_inspect')
                    self._conn.execute('RELEASE v5_tsk_verification_inspect')
                except sqlite3.Error:
                    # Trusted host COMMIT cannot be undone by our former savepoint.
                    pass
            raise
        try:
            if type(result) is not Result:
                raise ContractError()
            result = Result.from_json(result.to_json())
            if not result.ok:
                _reject('not_found' if result.error.code.value == 'not_found' else 'unavailable')
            data = _obj(result.value.to_json(), {'work_ref', 'artifact_refs', 'checks', 'source_refs', 'status'})
            _work(data['work_ref'])
            for name, kind in (('artifact_refs', 'artifact'), ('source_refs', 'record')):
                if type(data[name]) is not list or any(Ref.from_json(r).kind.value != kind for r in data[name]):
                    raise ContractError()
            if data['status'] not in ('valid', 'invalidated') or type(data['checks']) is not list:
                raise ContractError()
            available = set(_refs(data['artifact_refs']) + _refs(data['source_refs']))
            for check in data['checks']:
                _obj(check, {'condition_id', 'status', 'reason', 'evidence_refs'})
                _id(check['condition_id'])
                if (check['status'] not in ('met', 'unmet', 'unknown') or
                        type(check['reason']) is not str or len(check['reason']) > 1024 or
                        not set(_refs(check['evidence_refs'])) <= available):
                    raise ContractError()
            return data
        except ContractError:
            _reject('unavailable')

    def _ready_to_close(self, row, lease, work, asking=None):
        try:
            saved_steps = {saved['id']: saved for saved in self._steps(row)}
            steps = {key: loads(saved['wire']) for key, saved in saved_steps.items()}
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease['id'],))
            for key, step in steps.items():
                saved = saved_steps[key]
                binding = _work(step['work_ref'])
                if (step['status'] not in ('started', 'finished', 'abandoned') or
                        step['step_id'] != key or
                        (binding.goal_id, binding.revision) != (work.goal_id, work.revision) or
                        type(step['index']) is not int or not 0 <= step['index'] <= _MAX or
                        type(saved['idx']) is not int or step['index'] != saved['idx']):
                    raise ContractError()
            for call in calls:
                if (call['status'] not in _CALL_STATES or
                        (call['status'] == 'interrupted' and call['step'] is not None) or
                        _work(loads(call['work'])) != work or
                        type(call['idx']) is not int or not 0 <= call['idx'] <= _MAX):
                    raise ContractError()
                if call['step'] in steps:
                    saved, step = saved_steps[call['step']], steps[call['step']]
                    if (saved['call'] != call['id'] or step['index'] != call['idx'] or
                            _work(step['work_ref']) != work):
                        raise ContractError()
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')
        if (any(step['status'] == 'started' and key != asking for key, step in steps.items()) or
                any(call['status'] == 'admitted' or (call['status'] == 'returned' and
                    (call['step'] not in steps or (steps[call['step']]['status'] != 'finished' and call['step'] != asking))) for call in calls)):
            _reject('conflict')

    def _complete(self, work, verification):
        row, lease = self._authority(work)
        data = self._inspect_verification(verification)
        inspected = _work(data['work_ref'])
        if (inspected.goal_id, inspected.revision) != (work.goal_id, work.revision):
            _reject('conflict')
        if inspected.epoch != work.epoch:
            _reject('stale')
        context = self._verification_context({'work_ref': work.to_json()}, purpose='status')
        if not context.ok:
            raise _Rejected(context)
        current = context.value.to_json()
        if data['artifact_refs'] != current['artifact_refs']:
            _reject('stale')
        if [c['condition_id'] for c in data['checks']] != [c['id'] for c in current['conditions']]:
            _reject('unavailable')
        sources = _refs(data['source_refs'])
        if not set(_refs(current['source_refs'])) <= set(sources) <= set(self._registered(row)):
            _reject('unavailable')
        self._gate(sources)
        if data['status'] != 'valid':
            _reject('unavailable')
        if any(c['status'] != 'met' for c in data['checks']):
            _reject('conflict')
        self._ready_to_close(row, lease, work)
        row['state'] = 'completed'
        self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?',
                           ('completed', work.goal_id, work.revision))
        self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease['id'],))
        self._set_flags(row, 0, 0)
        self._event(row, 'result', 'work completed from saved verification',
                    (*_refs(data['artifact_refs']), verification))
        return {'work_ref': work.to_json(), 'state': 'completed', 'control_status': 'none'}

    def _question_step(self, saved):
        try:
            step = _obj(loads(saved['wire']), {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'}, {'error'})
            binding = _work(step['work_ref'])
            action = action_from_json(step['action']).to_json()
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
            if (step['step_id'] != saved['id'] or
                    (binding.goal_id, binding.revision) != (saved['goal'], saved['revision']) or
                    type(step['index']) is not int or not 0 <= step['index'] <= _MAX or
                    type(saved['idx']) is not int or step['index'] != saved['idx'] or
                    step['status'] not in ('started', 'finished', 'abandoned') or call is None or
                    call['status'] not in _CALL_STATES or call['status'] == 'interrupted' or
                    _work(loads(call['work'])) != binding or type(call['idx']) is not int or
                    call['idx'] != step['index'] or call['step'] != saved['id']):
                raise ContractError()
            lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (call['lease'],))
            if lease is None or (lease['goal'], lease['revision']) != (binding.goal_id, binding.revision):
                raise ContractError()
            refs = _refs(loads(call['sources']))
            if any(ref.kind.value != 'record' for ref in refs):
                raise ContractError()
            _refs(step['result_refs'])
            if 'error' in step and type(step['error']) is not str:
                raise ContractError()
            if action['kind'] == 'ask':
                if step['result_refs'] or 'error' in step or not set(_refs(action['source_refs'])) <= set(refs):
                    raise ContractError()
            return step, call, refs
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')

    def _questions(self, row):
        try:
            latest = self._one('SELECT MAX(revision) AS revision FROM v5_intake_work WHERE goal_id=?', (row['goal_id'],))
            historical = row['revision'] < latest['revision']
            if (row['state'] == 'superseded') != historical:
                raise ContractError()
            items = self._rows('SELECT * FROM v5_tsk_question WHERE goal=? AND revision=?',
                               (row['goal_id'], row['revision']))
            required, registered = set(self._required(row)), set(self._registered(row))
            result, by_step = [], set()
            for item in items:
                _id(item['id'])
                saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (item['step_id'],))
                if saved is None:
                    raise ContractError()
                step, call, refs = self._question_step(saved)
                action = {'kind': 'ask', 'question': item['question'], 'missing_fact': item['missing_fact'],
                          'source_refs': loads(item['sources'])}
                action_from_json(action)
                if ((saved['goal'], saved['revision']) != (row['goal_id'], row['revision']) or
                        _work(step['work_ref']).epoch > row['epoch'] or
                        step['status'] != 'finished' or call['status'] != 'returned' or
                        action != step['action'] or not required <= set(refs) <= registered or
                        item['status'] not in ('open', 'answered', 'closed', 'superseded') or
                        (item['status'] == 'superseded' and not historical)):
                    raise ContractError()
                answer = None if item['answer_ref'] is None else Ref.from_json(loads(item['answer_ref']))
                if ((item['status'] == 'answered') != (answer is not None) or
                        (answer is not None and (answer.kind.value != 'record' or answer not in registered))):
                    raise ContractError()
                item.update(dependencies=tuple(refs), work_ref=step['work_ref'], index=step['index'], answer=answer.to_json() if answer else None)
                result.append(item)
                by_step.add(item['step_id'])
            finished = {saved['id'] for saved in self._steps(row)
                        if (wire := loads(saved['wire']))['status'] == 'finished' and wire['action']['kind'] == 'ask'}
            if finished != by_step:
                raise ContractError()
            opened = [q for q in result if q['status'] == 'open']
            if (historical and opened) or len(opened) > 1 or (opened and row['state'] not in ('waiting_input', 'paused')):
                raise ContractError()
            if opened and self._one('SELECT id FROM v5_tsk_lease WHERE goal=? AND revision=? AND active=1',
                                    (row['goal_id'], row['revision'])):
                raise ContractError()
            if row['state'] == 'waiting_input' and not opened:
                raise ContractError()
            return sorted(result, key=lambda q: q['index'])
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')

    @_public
    def ask(self, request):
        data = _obj(request, {'key', 'work_ref', 'step_id', 'question', 'missing_fact', 'source_refs'})
        key, work, step_id = _id(data['key']), _work(data['work_ref']), _id(data['step_id'])
        action = action_from_json({'kind': 'ask', **{name: data[name] for name in ('question', 'missing_fact', 'source_refs')}}).to_json()
        if any(ref.kind.value != 'record' for ref in _refs(data['source_refs'])):
            raise ContractError()
        def operation():
            row, lease = self._authority(work)
            saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (step_id,))
            if saved is None:
                _reject('not_found')
            step, call, refs = self._question_step(saved)
            if step['work_ref'] != work.to_json():
                _reject('stale')
            if step['status'] != 'started' or step['action'] != action:
                _reject('conflict')
            if call['lease'] != lease['id']:
                _reject('denied')
            if call['status'] != 'returned':
                _reject('conflict')
            self._ready_to_close(row, lease, work, asking=step_id)
            try:
                if not set(self._required(row)) <= set(refs) <= set(self._registered(row)):
                    raise ContractError()
            except ContractError:
                _reject('unavailable')
            self._gate(refs)
            self._questions(row)
            if self._one("SELECT id FROM v5_tsk_question WHERE goal=? AND status='open'", (work.goal_id,)):
                _reject('unavailable')
            changes = self._conn.total_changes
            self._conn.execute('SAVEPOINT v5_tsk_question_mint')
            try:
                question_id = self._mint('question')
                if not self._conn.in_transaction or self._conn.total_changes != changes:
                    _reject('unavailable')
                self._conn.execute('RELEASE v5_tsk_question_mint')
            except BaseException:
                if self._conn.in_transaction:
                    try:
                        self._conn.execute('ROLLBACK TO v5_tsk_question_mint')
                        self._conn.execute('RELEASE v5_tsk_question_mint')
                    except sqlite3.Error:
                        # Lost transaction ownership is detected, not reversible.
                        pass
                raise
            step['status'] = 'finished'
            self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), step_id))
            self._conn.execute('INSERT INTO v5_tsk_question VALUES (?,?,?,?,?,?,?,?,NULL)',
                (question_id, work.goal_id, work.revision, step_id, data['question'], data['missing_fact'], dumps(data['source_refs']), 'open'))
            self._conn.execute("UPDATE v5_intake_work SET state='waiting_input' WHERE goal_id=? AND revision=?", (work.goal_id, work.revision))
            self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease['id'],))
            self._set_flags(row, 0, 0)
            self._event(row, 'question', data['question'], tuple(Ref.from_json(ref) for ref in data['source_refs']))
            return {'question_id': question_id, 'state': 'waiting_input', 'work_ref': work.to_json()}
        return self._transaction('C04.ask', key, data, operation)

    @_public
    def get_question_by_key(self, request):
        data = _obj(request, {'key'})
        key = _id(data['key'])
        saved = self._one("SELECT input_json,result_json FROM v5_intake_replay WHERE command='C04.ask' AND key=?", (key,))
        if saved is None:
            _reject('not_found')
        try:
            original = _obj(loads(saved['input_json']), {'key', 'work_ref', 'step_id', 'question', 'missing_fact', 'source_refs'})
            result = Result.from_json(loads(saved['result_json']))
            receipt = _obj(result.value.to_json(), {'question_id', 'state', 'work_ref'})
            work = _work(receipt['work_ref'])
            if not result.ok or original['key'] != key or receipt['state'] != 'waiting_input' or original['work_ref'] != work.to_json():
                raise ContractError()
            row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
            match = [q for q in self._questions(row) if q['id'] == receipt['question_id']]
            if len(match) != 1 or match[0]['work_ref'] != work.to_json() or any(original[name] != match[0][name] for name in ('step_id', 'question', 'missing_fact')) or original['source_refs'] != loads(match[0]['sources']):
                raise ContractError()
            return result
        except (ContractError, KeyError, TypeError, AttributeError):
            _reject('unavailable')

    def _answer(self, work, command):
        row = self._current(work, epoch=False)
        target = self._one('SELECT * FROM v5_tsk_question WHERE id=?', (command['question_id'],))
        if target is None or target['goal'] != work.goal_id:
            _reject('not_found')
        if target['revision'] != work.revision:
            _reject('stale')
        questions = self._questions(row)
        question = next(q for q in questions if q['id'] == command['question_id'])
        if question['status'] != 'open':
            _reject('conflict')
        answer = Ref.from_json(command['answer_record_ref'])
        self._gate(tuple(dict.fromkeys((*question['dependencies'], answer))))
        self._conn.execute("UPDATE v5_tsk_question SET status='answered',answer_ref=? WHERE id=?", (dumps(answer), question['id']))
        self._register(row, (answer,))
        row['state'] = 'queued' if row['state'] == 'waiting_input' else 'paused'
        self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?', (row['state'], work.goal_id, work.revision))
        self._event(row, 'state', 'question answered', (answer,))
        return {'work_ref': self._wr(row).to_json(), 'state': row['state'], 'control_status': 'none'}

    def _change_mint(self, prefix):
        before = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_tsk_change_mint')
        try:
            identifier = self._mint(prefix)
            if not self._conn.in_transaction or self._conn.total_changes != before:
                _reject('unavailable')
            self._conn.execute('RELEASE v5_tsk_change_mint')
            return identifier
        except BaseException:
            if self._conn.in_transaction:
                try:
                    self._conn.execute('ROLLBACK TO v5_tsk_change_mint')
                    self._conn.execute('RELEASE v5_tsk_change_mint')
                except sqlite3.Error:
                    pass
            raise

    def _change(self, work, draft, origin):
        row = self._current(work, epoch=False)
        if row['state'] in ('completed', 'cancelled', 'failed'):
            _reject('conflict')
        if row['state'] not in ('queued', 'waiting_input', 'paused', 'running'):
            _reject('unavailable')
        self._questions(row)
        flags = self._flags(row)
        if any(type(flags[name]) is not int or flags[name] not in (0, 1) for name in ('pause', 'drain')):
            _reject('unavailable')
        lease = self._one('SELECT * FROM v5_tsk_lease WHERE goal=? AND active=1', (work.goal_id,))
        if ((row['state'] == 'running') != (lease is not None) or
                (lease is not None and (lease['revision'] > row['revision'] or
                 (lease['revision'] != row['revision'] and not flags['drain'])))):
            _reject('unavailable')
        try:
            history = self._rows('SELECT origin_ref_json,brief_json FROM v5_intake_work WHERE goal_id=?', (work.goal_id,))
            origins = [Ref.from_json(loads(item['origin_ref_json'])) for item in history]
            old_ids = {condition.id for item in history for condition in Brief.from_json(loads(item['brief_json'])).conditions}
            prior = Grant.from_json(loads(row['grant_json']))
        except ContractError:
            _reject('unavailable')
        if origin in origins:
            _reject('conflict')
        grant = _intersect(self._host_grant, prior)
        if draft.target.repository not in grant.repositories:
            _reject('denied')
        refs = tuple(dict.fromkeys((origin, *draft.context_refs)))
        self._gate(refs)
        if row['revision'] == _MAX or row['epoch'] == _MAX:
            _reject('unavailable')
        conditions = []
        for condition in draft.conditions:
            identifier = self._change_mint('condition')
            if identifier in old_ids:
                _reject('unavailable')
            old_ids.add(identifier)
            conditions.append(Condition(identifier, condition.description, condition.check))
        event_id = self._change_mint('event')
        brief = Brief(draft.purpose, draft.target, draft.constraints, tuple(conditions), draft.context_refs)
        current = dict(row, revision=row['revision'] + 1, epoch=row['epoch'] + 1,
                       state='queued' if row['state'] == 'waiting_input' else row['state'])
        self._conn.execute('INSERT INTO v5_intake_work VALUES (?,?,?,?,?,?,?,?,?)',
            (work.goal_id, current['revision'], current['epoch'], current['state'], dumps(brief),
             dumps(grant), row['session_id'], dumps(origin), row['expert_id']))
        self._register(current, refs)
        self._conn.execute("UPDATE v5_intake_work SET state='superseded' WHERE goal_id=? AND revision=?", (work.goal_id, row['revision']))
        self._set_flags(row, 0, 0)
        self._conn.execute("UPDATE v5_tsk_question SET status='superseded' WHERE goal=? AND revision=? AND status='open'", (work.goal_id, row['revision']))
        pause, drain = (flags['pause'], 1) if current['state'] == 'running' else (0, 0)
        self._set_flags(current, pause, drain)
        # Premint only this event: the shared writer mints after owned writes.
        self._conn.execute('INSERT INTO v5_intake_event (event_id,session_id,work_ref_json,kind,text,refs_json) VALUES (?,?,?,?,?,?)',
            (event_id, row['session_id'], dumps(self._wr(current)), 'state', 'work changed', dumps([origin.to_json()])))
        return {'work_ref': self._wr(current).to_json(), 'state': current['state'],
                'control_status': 'pause_requested' if pause else 'draining' if drain else 'none'}

    def _old_calls(self, row, lease, *, claim=None):
        try:
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease['id'],))
            inspected = list(calls)
            if claim is not None:
                seen = {call['id'] for call in calls}
                for saved in self._steps(row):
                    if saved['call'] not in seen:
                        historic = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
                        if historic is None:
                            raise ContractError()
                        inspected.append(historic)
                        seen.add(historic['id'])
            linked, indexes = set(), set()
            required, registered = set(self._required(row)), set(self._registered(row))
            for call in inspected:
                call_lease = lease if call['lease'] == lease['id'] else self._one(
                    'SELECT * FROM v5_tsk_lease WHERE id=?', (call['lease'],))
                if (call_lease is None or (call_lease['goal'], call_lease['revision']) !=
                        (row['goal_id'], row['revision'])):
                    raise ContractError()
                _id(call_lease['id'])
                _id(call['id'])
                _id(call['reservation'])
                sources = set(_refs(loads(call['sources'])))
                if not required <= sources <= registered or any(ref.kind.value != 'record' for ref in sources):
                    raise ContractError()
                work = _work(loads(call['work']))
                if (call['status'] not in _CALL_STATES or
                        (call['status'] == 'interrupted' and call['step'] is not None) or
                        (work.goal_id, work.revision) != (row['goal_id'], row['revision']) or
                        work.epoch > row['epoch'] or type(call['idx']) is not int or not 0 <= call['idx'] <= _MAX):
                    raise ContractError()
                if claim is not None and call['lease'] == lease['id'] and work != claim:
                    raise ContractError()
                if call['id'] != dumps(['C15.call', call_lease['id'], call['idx']]):
                    raise ContractError()
                if (call_lease['id'], call['idx']) in indexes:
                    raise ContractError()
                indexes.add((call_lease['id'], call['idx']))
                reservation = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (call['reservation'],))
                if (reservation is None or type(reservation['idx']) is not int or
                        (reservation['lease'], _work(loads(reservation['work'])), reservation['idx'],
                         reservation['kind'], reservation['role'], reservation['binding']) !=
                        (call_lease['id'], work, call['idx'], 'model', 'expert', call['id'])):
                    raise ContractError()
                if call['step'] is not None:
                    if call['status'] == 'interrupted' or (claim is not None and call['status'] != 'returned'):
                        raise ContractError()
                    _id(call['step'])
                    saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (call['step'],))
                    if saved is None or saved['id'] in linked:
                        raise ContractError()
                    step = _obj(loads(saved['wire']), {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'}, {'error'})
                    action_from_json(step['action'])
                    _refs(step['result_refs'])
                    if (step['status'] not in ('started', 'finished', 'abandoned') or
                            ('error' in step and type(step['error']) is not str) or
                            type(step['index']) is not int or type(saved['idx']) is not int or
                            (saved['goal'], saved['revision'], saved['idx'], saved['call'], step['step_id'],
                             _work(step['work_ref']), step['index']) !=
                            (work.goal_id, work.revision, call['idx'], call['id'], saved['id'], work, call['idx'])):
                        raise ContractError()
                    if claim is not None:
                        reservations = self._rows('SELECT * FROM v5_tsk_reservation WHERE kind=? AND binding=?',
                                                  ('step', saved['id']))
                        if len(reservations) != 1:
                            raise ContractError()
                        reserved = reservations[0]
                        _id(reserved['id'])
                        if (type(reserved['idx']) is not int or
                                (reserved['lease'], _work(loads(reserved['work'])), reserved['idx'], reserved['role']) !=
                                (call_lease['id'], work, call['idx'], None)):
                            raise ContractError()
                    linked.add(saved['id'])
            # Other leases may have finished historical Steps, but no dangling owned linkage.
            for saved in self._steps(row):
                call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
                if call is None or call['step'] != saved['id']:
                    raise ContractError()
                if loads(saved['wire'])['status'] == 'started' and (saved['id'] not in linked or call['lease'] != lease['id']):
                    raise ContractError()
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')
        if claim is None and any(call['status'] == 'admitted' for call in calls):
            _reject('conflict')
        return calls

    @_public
    def control(self, request):
        data = _obj(request, {'key', 'work_ref', 'command'})
        key, work = _id(data['key']), _work(data['work_ref'])
        command = data['command']
        change = None
        verification = None
        answer = None
        if type(command) is dict:
            if command.get('kind') == 'change':
                _obj(command, {'kind', 'brief', 'origin_record_ref'})
                draft = DraftBrief.from_json(command['brief'])
                origin = Ref.from_json(command['origin_record_ref'])
                if origin.kind.value != 'record':
                    raise ContractError()
                change = (draft, origin)
            elif command.get('kind') == 'answer':
                _obj(command, {'kind', 'question_id', 'answer_record_ref'})
                _id(command['question_id'])
                if Ref.from_json(command['answer_record_ref']).kind.value != 'record':
                    raise ContractError()
                answer = command
            else:
                _obj(command, {'kind', 'verification_ref'})
                verification = Ref.from_json(command['verification_ref'])
                if command['kind'] != 'complete' or verification.kind.value != 'verification':
                    raise ContractError()
        elif command not in ('pause', 'resume', 'cancel'):
            raise ContractError()
        def operation():
            if change is not None:
                return self._change(work, *change)
            if answer is not None:
                return self._answer(work, answer)
            if verification is not None:
                return self._complete(work, verification)
            row = self._current(work, epoch=False)
            questions = self._questions(row)
            opened = [q for q in questions if q['status'] == 'open']
            flags = self._flags(row)
            before = (row['state'], row['epoch'], flags['pause'])
            command = data['command']
            if command == 'cancel':
                if row['state'] != 'cancelled':
                    if row['state'] in ('completed', 'failed'):
                        _reject('conflict')
                    if row['epoch'] == _MAX:
                        _reject('unavailable')
                    row.update(state='cancelled', epoch=row['epoch'] + 1)
                    self._conn.execute("UPDATE v5_tsk_question SET status='closed' WHERE goal=? AND status='open'", (work.goal_id,))
            elif command == 'pause':
                if row['state'] == 'running':
                    flags['pause'] = 1
                elif row['state'] in ('queued', 'waiting_input'):
                    row['state'] = 'paused'
                elif row['state'] != 'paused':
                    _reject('conflict')
            else:
                if row['state'] != 'paused':
                    _reject('conflict')
                row['state'] = 'waiting_input' if opened else 'queued'
                flags['pause'] = 0
            if before != (row['state'], row['epoch'], flags['pause']):
                self._conn.execute('UPDATE v5_intake_work SET state=?,epoch=? WHERE goal_id=? AND revision=?',
                                   (row['state'], row['epoch'], row['goal_id'], row['revision']))
                self._set_flags(row, flags['pause'], flags['drain'])
                self._event(row, 'state', 'work ' + command)
            return {'work_ref': self._wr(row).to_json(), 'state': row['state'],
                    'control_status': 'pause_requested' if flags['pause'] else 'draining' if flags['drain'] else 'none'}
        return self._transaction('control', key, data, operation)

    @_public
    def release(self, request):
        data = _obj(request, {'lease_id', 'work_ref', 'outcome', 'reason'})
        lease_id, work = _id(data['lease_id']), _work(data['work_ref'])
        if data['outcome'] not in ('yield', 'paused', 'failed') or type(data['reason']) is not str:
            raise ContractError()
        def operation():
            lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (lease_id,))
            if lease is None:
                _reject('not_found')
            if not lease['active']:
                _reject('denied')
            if (lease['goal'], lease['revision']) != (work.goal_id, work.revision):
                _reject('stale')
            old = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
            row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? ORDER BY revision DESC LIMIT 1', (work.goal_id,))
            if old is None or row is None:
                _reject('unavailable')
            flags = self._flags(row)
            if old['revision'] != row['revision']:
                if any(type(flags[name]) is not int or flags[name] not in (0, 1) for name in ('pause', 'drain')):
                    _reject('unavailable')
                if old['state'] != 'superseded' or not (row['state'] == 'cancelled' or (row['state'] == 'running' and flags['drain'])):
                    _reject('unavailable')
                self._old_calls(old, lease)
                if data['outcome'] == 'paused' and not flags['pause']:
                    _reject('conflict')
                for saved in self._steps(old):
                    step = loads(saved['wire'])
                    if step['status'] == 'started':
                        step['status'] = 'abandoned'
                        self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), saved['id']))
                state = self._latest_intent(row, flags, fallback='queued')
                row['state'] = state
                self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?', (state, row['goal_id'], row['revision']))
                self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
                self._set_flags(row, 0, 0)
                self._event(row, 'state', data['reason'])
                return {'work_ref': self._wr(row).to_json(), 'state': state, 'control_status': 'none'}
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease_id,))
            if any(call['status'] not in _CALL_STATES or
                   (call['status'] == 'interrupted' and call['step'] is not None) for call in calls):
                _reject('unavailable')
            if any(call['status'] == 'admitted' for call in calls):
                _reject('conflict')
            if data['outcome'] == 'paused' and not flags['pause']:
                _reject('conflict')
            fenced = row['state'] == 'cancelled' or flags['pause'] or flags['drain']
            if data['outcome'] == 'yield' and not fenced:
                for call in calls:
                    step = self._one('SELECT wire FROM v5_tsk_step WHERE id=?', (call['step'],))
                    if call['status'] == 'returned' and (step is None or loads(step['wire'])['status'] != 'finished'):
                        _reject('conflict')
            for saved in self._steps(row):
                step = loads(saved['wire'])
                if step['status'] == 'started':
                    step['status'] = 'abandoned'
                    self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), saved['id']))
            state = self._latest_intent(row, flags,
                fallback='queued' if flags['drain'] or data['outcome'] == 'yield' else 'failed')
            row['state'] = state
            self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?', (state, work.goal_id, work.revision))
            self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
            self._set_flags(row, 0, 0)
            self._event(row, 'state', data['reason'])
            return {'work_ref': self._wr(row).to_json(), 'state': state, 'control_status': 'none'}
        return self._transaction('release', lease_id, data, operation)

    @_public
    def invalidate_by_refs(self, connection, *, key, session_id, refs):
        self._require_transaction(connection)
        _id(key)
        _id(session_id)
        if type(refs) is not tuple or any(type(ref) is not Ref for ref in refs):
            raise ContractError()
        refs = tuple(dict.fromkeys(refs))
        data = {'key': key, 'session_id': session_id, 'refs': _wire(refs)}
        canonical = dumps(data)
        replay = self._lookup_replay('TSK.invalidate_by_refs', key, canonical)
        if replay is not None:
            return replay
        affected = []
        for row in self._rows('SELECT * FROM v5_intake_work w WHERE revision=(SELECT MAX(revision) FROM v5_intake_work WHERE goal_id=w.goal_id)'):
            registered = set(self._registered(row))
            if not set(self._required(row)) <= registered:
                _reject('unavailable')
            if not set(refs) & registered or row['state'] in ('cancelled', 'failed'):
                continue
            if row['state'] == 'completed':
                self._event(row, 'progress',
                    'a source registered for this completed work was stopped; completion is historical',
                    tuple(ref for ref in refs if ref in registered))
                continue
            questions = self._questions(row)
            row['open_question'] = next((q for q in questions if q['status'] == 'open'), None)
            if row['state'] not in ('queued', 'running', 'paused', 'waiting_input') or row['epoch'] == _MAX:
                _reject('unavailable')
            affected.append(row)
        for row in affected:
            question = row['open_question']
            if question is not None and set(refs) & set(question['dependencies']):
                self._conn.execute("UPDATE v5_tsk_question SET status='closed' WHERE id=?", (question['id'],))
                if row['state'] == 'waiting_input':
                    row['state'] = 'queued'
                    self._conn.execute("UPDATE v5_intake_work SET state='queued' WHERE goal_id=? AND revision=?", (row['goal_id'], row['revision']))
            row['epoch'] += 1
            self._conn.execute('UPDATE v5_intake_work SET epoch=? WHERE goal_id=? AND revision=?', (row['epoch'], row['goal_id'], row['revision']))
            if row['state'] == 'running':
                self._set_flags(row, self._flags(row)['pause'], 1)
            self._event(row, 'state', 'work sources invalidated', tuple(refs))
        result = Result.success({'work_refs': [self._wr(row).to_json() for row in affected]})
        self._save_replay('TSK.invalidate_by_refs', key, canonical, result)
        return result
