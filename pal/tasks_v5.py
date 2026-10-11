"""Transactional execution rights for a trusted local mock host (TSK02/1)."""
from functools import wraps
from contextlib import contextmanager
import hashlib
import uuid
import sqlite3

from pal.contracts_v5 import (Brief, Condition, DraftBrief, ContractError, Grant, Limits, Ref, Result,
                              WorkRef, dumps, loads, parse_model_action, action_from_json)
from pal.intake_v5 import IntakeStore, _intersect
from pal.artifacts_v5 import artifact_save_key
from pal.native_call_v5 import NativeProfile, NativeReturned, NativeNeverEntered, validate_native_evidence

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
                 startup_guard=None, artifact_lookup=None, **kwargs):
        if artifact_lookup is not None and not callable(artifact_lookup):
            raise TypeError('artifact_lookup must be callable')
        self._artifact_lookup = artifact_lookup
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
            'CREATE TABLE IF NOT EXISTS v5_tsk_primary_reservation (reservation TEXT PRIMARY KEY,session TEXT NOT NULL,reserve_key TEXT NOT NULL UNIQUE)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_recovery_adoption (step_id TEXT PRIMARY KEY,call_id TEXT NOT NULL UNIQUE,lease_id TEXT NOT NULL UNIQUE,artifact_id TEXT NOT NULL UNIQUE,origin_work_json TEXT NOT NULL,adopted_work_json TEXT NOT NULL,recover_key TEXT NOT NULL,event_id TEXT NOT NULL UNIQUE)',
            'CREATE TABLE IF NOT EXISTS v5_tsk_recovery_replay (recover_key TEXT PRIMARY KEY,adopted_step_id TEXT UNIQUE,event_id TEXT NOT NULL UNIQUE,result_json TEXT NOT NULL)',
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
            'CREATE TABLE IF NOT EXISTS v5_tsk_call (id TEXT PRIMARY KEY,lease TEXT,work TEXT,idx INTEGER,reservation TEXT,sources TEXT NOT NULL,status TEXT,step TEXT,native TEXT NOT NULL DEFAULT \"mock\",native_hash TEXT,UNIQUE(lease,idx))',
            'CREATE TABLE IF NOT EXISTS v5_tsk_native (call_id TEXT PRIMARY KEY,wire TEXT NOT NULL)',
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
        if command == 'admit_native_call':
            return self._execution_request('admit_call', request['admission'])
        if command in ('enter_native_call', 'end_native_call', 'mark_native_unknown'):
            return self._execution_request('end_call', request)
        execution = command in ('claim', 'admit_call', 'end_call', 'begin_step', 'finish_step',
                                'C04.ask', 'release', 'reserve_budget', 'consume', 'register')
        if command == 'control':
            execution = type(request['command']) is dict and request['command'].get('kind') == 'complete'
        if not execution:
            return
        if command == 'reserve_budget' and 'work_ref' not in request:
            self._own_session(ready=True)
            saved = self._one("SELECT input_json,result_json FROM v5_intake_replay WHERE command='reserve_budget' AND key=?", (request['key'],))
            if saved is not None:
                try:
                    original = _obj(loads(saved['input_json']), {'key', 'kind'}, {'work_ref', 'role'})
                    if dumps(original) != saved['input_json'] or original['key'] != request['key']:
                        raise ContractError()
                    if 'work_ref' in original:
                        _work(original['work_ref'])
                        return
                    result = Result.from_json(loads(saved['result_json']))
                    value = _obj(result.value.to_json(), {'reservation_id', 'remaining'})
                    remaining = _obj(value['remaining'], {'host'})
                    if not result.ok or type(remaining['host']) is not int or not 0 <= remaining['host'] <= _MAX:
                        raise ContractError()
                    self._primary_reservation(self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (_id(value['reservation_id']),)))
                except (ContractError, KeyError, TypeError, AttributeError):
                    _reject('unavailable')
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
            if reservation is not None and (reservation['lease'] is None or reservation['role'] == 'primary' or
                    self._one('SELECT session FROM v5_tsk_primary_reservation WHERE reservation=?', (reservation['id'],))):
                self._primary_reservation(reservation)
                return
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
                self._native_integrity()
                self._execution_request(command, request)
                if command == 'recover':
                    self._recovery_integrity()
                if command in ('admit_call', 'end_call'):
                    saved_call = self._one('SELECT native FROM v5_tsk_call WHERE id=?', (request['call_id'],))
                    if saved_call is not None and saved_call['native'] != 'mock':
                        _reject('conflict')
                canonical = dumps(request)
                result = self._lookup_replay(command, key, canonical) if key is not None else None
                if result is None:
                    value = operation()
                    result = Result.success(value)
                    if key is not None and not (command == 'recover' and value.get('disposition') == 'held'):
                        self._save_replay(command, key, canonical, result)
                        if command == 'recover':
                            self._recovery_integrity()
                self._native_integrity()
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
            return self._transaction('recover', key, data, lambda: self._recover(lease_id, key))

    def _recover(self, lease_id, key):
        try:
            return self._recover_owned(lease_id, key)
        except (ContractError, KeyError, TypeError, ValueError):
            _reject('unavailable')

    def _recover_owned(self, lease_id, key):
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
        for call in calls:
            if call['native'] == 'native' and call['status'] == 'admitted':
                _, side = self._native_side(call['id'])
                return {'disposition': 'held', 'work_ref': self._wr(row).to_json(), 'state': row['state'],
                    'control_status': 'pause_requested' if flags['pause'] else 'draining' if flags['drain'] else 'none',
                    'lease_id': lease_id, 'call_id': call['id'], 'phase': side['phase'], 'reason': 'native_unknown'}
        started = []
        for call in calls:
            if call['step'] is not None:
                step = loads(self._one('SELECT wire FROM v5_tsk_step WHERE id=?', (call['step'],))['wire'])
                if step['status'] == 'started':
                    started.append(step)
        adopted = None
        for step in started:
            kind = step['action']['kind']
            if kind not in ('compose', 'operate'):
                continue
            held = {'disposition': 'held', 'work_ref': self._wr(row).to_json(), 'state': row['state'],
                'control_status': 'pause_requested' if flags['pause'] else 'draining' if flags['drain'] else 'none',
                'lease_id': lease_id, 'step_id': step['step_id'],
                'reason': 'artifact_tail' if kind == 'compose' else 'external_tail'}
            if kind == 'operate':
                return held
            call = next(c for c in calls if c['step'] == step['step_id'])
            sources = loads(call['sources'])
            refs = _refs(sources)
            parse_model_action(dumps(step['action']), allowed_refs=refs)
            if (step['result_refs'] != [] or 'error' in step or call['status'] != 'returned' or
                    not refs or len(refs) != len(sources) or
                    any(q['status'] == 'open' for q in questions)):
                _reject('unavailable')
            if (old['revision'] != row['revision'] or
                    row['state'] in ('completed', 'cancelled', 'failed', 'paused') or flags['pause']):
                continue
            if self._artifact_lookup is None:
                return held
            gate = self._recovery_read(lambda: self._check_sources(tuple(dict.fromkeys((*self._required(row), *refs)))))
            if gate is not None:
                if type(gate) is Result and not gate.ok and gate.error.code.value == 'denied':
                    continue
                return held
            outcome = self._recovery_read(lambda: self._artifact_lookup(self._conn, {
                'key': artifact_save_key(step['work_ref'], step['step_id']),
                'work_ref': step['work_ref'], 'step_id': step['step_id'], 'action': step['action']}))
            try:
                if type(outcome) is not Result:
                    return held
                outcome = Result.from_json(outcome.to_json())
                if not outcome.ok:
                    if outcome.error.code.value == 'not_found':
                        continue
                    return held
                metadata = _obj(outcome.value.to_json(), {'artifact_ref', 'work_ref', 'step_id', 'hash', 'bytes', 'source_refs'})
                artifact = Ref.from_json(metadata['artifact_ref'])
                if (artifact.kind.value != 'artifact' or _work(metadata['work_ref']) != claim or
                        metadata['step_id'] != step['step_id'] or metadata['source_refs'] != sources or
                        type(metadata['hash']) is not str or len(metadata['hash']) != 64 or
                        any(c not in '0123456789abcdef' for c in metadata['hash']) or
                        type(metadata['bytes']) is not int or not 0 <= metadata['bytes'] <= 1048576 or
                        self._one('SELECT step_id FROM v5_tsk_artifact_set WHERE artifact_id=? OR step_id=?', (artifact.id, step['step_id'])) or
                        self._one('SELECT step_id FROM v5_tsk_recovery_adoption WHERE artifact_id=? OR step_id=?', (artifact.id, step['step_id']))):
                    return held
            except (ContractError, KeyError, TypeError, ValueError):
                return held
            if adopted is not None:
                _reject('unavailable')
            adopted = (step, call, artifact)
        if row['state'] not in ('completed', 'cancelled', 'failed'):
            if type(row['epoch']) is not int or not 0 <= row['epoch'] < _MAX:
                _reject('unavailable')
            row['epoch'] += 1
        event_id = self._change_mint('event')
        interrupted = [call['id'] for call in calls if call['status'] == 'admitted']
        for call_id in interrupted:
            self._conn.execute("UPDATE v5_tsk_call SET status='interrupted' WHERE id=?", (call_id,))
        for step in started:
            step['status'] = 'finished' if adopted is not None and step is adopted[0] else 'abandoned'
            if step['status'] == 'finished':
                step['result_refs'] = [adopted[2].to_json()]
                self._conn.execute('INSERT INTO v5_tsk_artifact_set(goal,revision,artifact_id,step_id) VALUES (?,?,?,?)',
                    (row['goal_id'], row['revision'], adopted[2].id, step['step_id']))
            self._conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?', (dumps(step), step['step_id']))
        opened = any(q['status'] == 'open' for q in questions)
        state = 'paused' if row['state'] == 'paused' else self._latest_intent(row, flags, fallback='queued', opened=opened)
        row['state'] = state
        self._conn.execute('UPDATE v5_intake_work SET state=?,epoch=? WHERE goal_id=? AND revision=?',
                           (state, row['epoch'], row['goal_id'], row['revision']))
        self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
        self._set_flags(row, 0, 0)
        refs = [] if adopted is None else [adopted[2].to_json()]
        text = self._recovery_text(lease_id, None if adopted is None else adopted[0]['step_id'])
        self._conn.execute('INSERT INTO v5_intake_event (event_id,session_id,work_ref_json,kind,text,refs_json) VALUES (?,?,?,?,?,?)',
            (event_id, row['session_id'], dumps(self._wr(row)), 'state', text, dumps(refs)))
        value = {'disposition': 'settled', 'work_ref': self._wr(row).to_json(), 'state': state,
                 'control_status': 'none', 'recovered_lease_id': lease_id, 'interrupted_call_ids': interrupted}
        if self._native_unadopted(lease_id):
            value['reason'] = 'native_returned_unadopted'
        self._conn.execute('INSERT INTO v5_tsk_recovery_replay VALUES (?,?,?,?)',
            (key, None if adopted is None else adopted[0]['step_id'], event_id, dumps(Result.success(value))))
        if adopted is not None:
            step, call, artifact = adopted
            self._conn.execute('INSERT INTO v5_tsk_recovery_adoption VALUES (?,?,?,?,?,?,?,?)',
                (step['step_id'], call['id'], lease_id, artifact.id, dumps(claim), dumps(self._wr(row)), key, event_id))
        return value

    def _recovery_read(self, operation):
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_tsk_recovery_read')
        try:
            try:
                result = operation()
            except Exception:
                result = Result.failure('unavailable', 'recovery source unavailable')
            self._conn.execute('RELEASE v5_tsk_recovery_read')
            if not self._conn.in_transaction or self._conn.total_changes != changes:
                _reject('unavailable')
            return result
        except BaseException:
            try:
                self._conn.execute('ROLLBACK TO v5_tsk_recovery_read')
                self._conn.execute('RELEASE v5_tsk_recovery_read')
            except sqlite3.Error:
                pass
            raise


    def _native_unadopted(self, lease_id):
        return self._one("SELECT id FROM v5_tsk_call WHERE lease=? AND native='native' AND status='returned' AND step IS NULL", (lease_id,)) is not None

    def _recovery_text(self, lease_id, step_id):
        native = self._one("SELECT id FROM v5_tsk_call WHERE lease=? AND native='native'", (lease_id,))
        if native:
            return 'Execution recovered' if step_id is None else 'Saved draft recovered'
        return 'mock execution recovered' if step_id is None else 'mock saved draft recovered'

    def _recovery_integrity(self):
        self._native_integrity()
        try:
            receipts = {}
            for saved in self._rows("SELECT * FROM v5_intake_replay WHERE command='recover'"):
                key = _id(saved['key'])
                request = _obj(loads(saved['input_json']), {'key', 'lease_id'})
                if _id(request['key']) != key or dumps(request) != saved['input_json']:
                    raise ContractError()
                lease_id = _id(request['lease_id'])
                result = Result.from_json(loads(saved['result_json']))
                if not result.ok:
                    raise ContractError()
                value = _obj(result.value.to_json(), {'disposition', 'work_ref', 'state', 'control_status',
                            'recovered_lease_id', 'interrupted_call_ids'}, {'reason'})
                work = _work(value['work_ref'])
                lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (lease_id,))
                interrupted = value['interrupted_call_ids']
                if ('reason' in value) != self._native_unadopted(lease_id) or (
                        'reason' in value and value['reason'] != 'native_returned_unadopted'):
                    raise ContractError()
                if (value['disposition'] != 'settled' or value['control_status'] != 'none' or
                        value['state'] not in ('queued', 'paused', 'waiting_input', 'completed', 'cancelled', 'failed') or
                        value['recovered_lease_id'] != lease_id or lease is None or type(lease['active']) is not int or lease['active'] != 0 or
                        work.goal_id != lease['goal'] or work.revision < lease['revision'] or
                        type(interrupted) is not list or len(set(interrupted)) != len(interrupted)):
                    raise ContractError()
                self._lease_binding(lease, self._enrollment())
                historical = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
                if historical is None or work.epoch > historical['epoch']:
                    raise ContractError()
                actual = self._rows("SELECT id FROM v5_tsk_call WHERE lease=? AND status='interrupted'", (lease_id,))
                if set(interrupted) != {call['id'] for call in actual}:
                    raise ContractError()
                for identity in interrupted:
                    call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (_id(identity),))
                    if call is None or call['lease'] != lease_id or call['status'] != 'interrupted':
                        raise ContractError()
                receipts[key] = (saved, request, value, work, lease)
            bindings = {}
            for binding in self._rows('SELECT * FROM v5_tsk_recovery_replay'):
                key, event_id = _id(binding['recover_key']), _id(binding['event_id'])
                if key not in receipts:
                    raise ContractError()
                saved, request, value, work, lease = receipts[key]
                if binding['result_json'] != saved['result_json']:
                    raise ContractError()
                step_id = binding['adopted_step_id']
                if step_id is not None:
                    _id(step_id)
                event = self._one('SELECT * FROM v5_intake_event WHERE event_id=?', (event_id,))
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
                if (event is None or row is None or work.epoch > row['epoch'] or
                        event['session_id'] != row['session_id'] or event['kind'] != 'state' or
                        _work(loads(event['work_ref_json'])) != work or
                        event['text'] != self._recovery_text(lease['id'], step_id)):
                    raise ContractError()
                if step_id is None and loads(event['refs_json']) != []:
                    raise ContractError()
                bindings[key] = (binding, event)
            adopted_steps = set()
            for adoption in self._rows('SELECT * FROM v5_tsk_recovery_adoption'):
                for name in ('step_id', 'call_id', 'lease_id', 'artifact_id', 'recover_key', 'event_id'):
                    _id(adoption[name])
                key = adoption['recover_key']
                if key not in bindings:
                    raise ContractError()
                binding, event = bindings[key]
                saved_replay, request, value, adopted_work, lease = receipts[key]
                origin = _work(loads(adoption['origin_work_json']))
                if (binding['adopted_step_id'] != adoption['step_id'] or binding['event_id'] != adoption['event_id'] or
                        request['lease_id'] != adoption['lease_id'] or
                        _work(loads(adoption['adopted_work_json'])) != adopted_work or
                        (origin.goal_id, origin.revision) != (adopted_work.goal_id, adopted_work.revision) or
                        adopted_work.epoch <= origin.epoch or value['interrupted_call_ids'] != []):
                    raise ContractError()
                _, claim = self._lease_binding(lease, self._enrollment())
                if claim != origin:
                    raise ContractError()
                call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (adoption['call_id'],))
                saved = self._one('SELECT * FROM v5_tsk_step WHERE id=?', (adoption['step_id'],))
                if call is None or saved is None:
                    raise ContractError()
                step = _obj(loads(saved['wire']), {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'})
                action = action_from_json(step['action'])
                refs = [{'kind': 'artifact', 'id': adoption['artifact_id']}]
                if (step['status'] != 'finished' or step['action']['kind'] != 'compose' or step['result_refs'] != refs or
                        step['step_id'] != saved['id'] or saved['call'] != call['id'] or call['step'] != saved['id'] or
                        call['lease'] != lease['id'] or call['status'] != 'returned' or
                        _work(loads(call['work'])) != origin or _work(step['work_ref']) != origin or
                        type(call['idx']) is not int or not 0 <= call['idx'] <= _MAX or
                        type(step['index']) is not int or type(saved['idx']) is not int or
                        step['index'] != call['idx'] or saved['idx'] != call['idx'] or
                        (saved['goal'], saved['revision']) != (origin.goal_id, origin.revision) or
                        call['id'] != dumps(['C15.call', lease['id'], call['idx']]) or loads(event['refs_json']) != refs):
                    raise ContractError()
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (origin.goal_id, origin.revision))
                sources = loads(call['sources'])
                dependencies = _refs(sources)
                if (not dependencies or len(dependencies) != len(sources) or
                        any(ref.kind.value != 'record' for ref in dependencies) or
                        not set(self._required(row)) <= set(dependencies) <= set(self._registered(row))):
                    raise ContractError()
                parse_model_action(dumps(action), allowed_refs=dependencies)
                model = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (_id(call['reservation']),))
                steps = self._rows("SELECT * FROM v5_tsk_reservation WHERE kind='step' AND binding=?", (saved['id'],))
                if model is None or len(steps) != 1:
                    raise ContractError()
                for reservation, kind, role, identity in ((model, 'model', 'expert', call['id']), (steps[0], 'step', None, saved['id'])):
                    _id(reservation['id'])
                    if (type(reservation['idx']) is not int or
                            (reservation['lease'], _work(loads(reservation['work'])), reservation['idx'], reservation['kind'], reservation['role'], reservation['binding']) !=
                            (lease['id'], origin, call['idx'], kind, role, identity)):
                        raise ContractError()
                items = self._rows('SELECT * FROM v5_tsk_artifact_set WHERE step_id=? OR artifact_id=?', (saved['id'], adoption['artifact_id']))
                if (len(items) != 1 or (items[0]['goal'], items[0]['revision'], items[0]['step_id'], items[0]['artifact_id']) !=
                        (origin.goal_id, origin.revision, saved['id'], adoption['artifact_id'])):
                    raise ContractError()
                adopted_steps.add(saved['id'])
            if {item[0]['adopted_step_id'] for item in bindings.values() if item[0]['adopted_step_id'] is not None} != adopted_steps:
                raise ContractError()
        except (ContractError, KeyError, TypeError, ValueError):
            _reject('unavailable')

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
        self._native_integrity()
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

    def _candidate_gate(self, refs):
        changes = self._conn.total_changes
        self._conn.execute('SAVEPOINT v5_tsk_candidate_gate')
        try:
            outcome = self._source_gate(self._conn, refs)
            self._conn.execute('RELEASE v5_tsk_candidate_gate')
            if (not self._conn.in_transaction or self._conn.total_changes != changes or
                    type(outcome) is not str or outcome not in ('available', 'denied', 'not_found', 'unavailable')):
                _reject('unavailable')
            return outcome == 'available'
        except BaseException:
            try:
                self._conn.execute('ROLLBACK TO v5_tsk_candidate_gate')
                self._conn.execute('RELEASE v5_tsk_candidate_gate')
            except sqlite3.Error:
                pass
            raise

    @_public
    def list_candidates(self, request):
        data = _obj(request, {'session_id', 'limit'}, {'goal_ids', 'query'})
        _id(data['session_id'])
        limit = data['limit']
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ContractError()
        ids = data.get('goal_ids')
        if 'goal_ids' in data:
            if type(ids) is not list or len(ids) > 20:
                raise ContractError()
            ids = [_id(value) for value in ids]
            if len(ids) != len(set(ids)):
                raise ContractError()
        if 'query' in data:
            _reject('unavailable')
        self._require_idle()
        self._conn.execute('BEGIN')
        try:
            rows = self._rows('SELECT w.* FROM v5_intake_work w WHERE revision=(SELECT MAX(revision) FROM v5_intake_work WHERE goal_id=w.goal_id)')
            if ids is not None:
                rows = [row for row in rows if row['goal_id'] in ids]
            activity = {}
            for event in self._rows('SELECT seq,work_ref_json FROM v5_intake_event WHERE work_ref_json IS NOT NULL'):
                work = _work(loads(event['work_ref_json']))
                activity[work.goal_id] = max(activity.get(work.goal_id, 0), event['seq'])
            rows.sort(key=lambda row: (-activity.get(row['goal_id'], 0), row['goal_id']))
            values = []
            for row in rows[:limit]:
                work = self._wr(row)
                _work(work.to_json())
                brief = Brief.from_json(loads(row['brief_json']))
                grant = Grant.from_json(loads(row['grant_json']))
                _id(row['session_id'])
                _id(row['expert_id'])
                if brief.target.repository not in grant.repositories:
                    raise ContractError()
                if (row['state'] not in ('queued', 'running', 'waiting_input', 'paused', 'completed', 'cancelled', 'failed') or
                        len({c.id for c in brief.conditions}) != len(brief.conditions)):
                    raise ContractError()
                refs = self._registered(row)
                if (any(ref.kind.value != 'record' for ref in refs) or
                        not set(self._required(row)) <= set(refs)):
                    raise ContractError()
                questions = [q for q in self._questions(row) if q['status'] == 'open']
                if any(not set(q['dependencies']) <= set(refs) for q in questions):
                    raise ContractError()
                visible = self._candidate_gate(refs)
                values.append({'work_ref': work.to_json(), 'brief_summary': brief.purpose.encode('utf-8')[:512].decode('utf-8', 'ignore') if visible else '',
                    'expert_id': row['expert_id'], 'state': row['state'],
                    'open_questions': [{'id': q['id'], 'text': q['question'].encode('utf-8')[:1024].decode('utf-8', 'ignore') if visible else '',
                                        'revision': q['revision']} for q in questions],
                    'dependency_refs': _wire(refs), 'text_withheld': not visible})
            result = Result.success({'works': values, 'truncated': len(rows) > limit})
            if len(dumps(result).encode('utf-8')) > 131072:
                _reject('limit')
            self._conn.execute('COMMIT')
            return result
        except BaseException as error:
            self._rollback()
            if isinstance(error, ContractError):
                _reject('unavailable')
            raise

    @staticmethod
    def _receipt_brief(draft, saved):
        expected = draft.to_json()
        actual = saved.to_json()
        if len({c.id for c in saved.conditions}) != len(saved.conditions):
            raise ContractError()
        actual['conditions'] = [{k: v for k, v in c.items() if k != 'id'} for c in actual['conditions']]
        if actual != expected:
            raise ContractError()

    def _original_receipt(self, namespace, key):
        saved = self._one('SELECT input_json,result_json FROM v5_intake_replay WHERE command=? AND key=?', (namespace, key))
        if saved is None:
            _reject('not_found')
        try:
            request = loads(saved['input_json'])
            if dumps(request) != saved['input_json'] or request['key'] != key:
                raise ContractError()
            result = Result.from_json(loads(saved['result_json']))
            if not result.ok:
                raise ContractError()
            if namespace == 'C03.create':
                request = _obj(request, {'key', 'session_id', 'origin_record_ref', 'brief', 'request_scope'})
                value = _obj(result.value.to_json(), {'work_ref', 'expert_id', 'state', 'grant'})
                work = _work(value['work_ref'])
                scope = Grant.from_json(request['request_scope'])
                grant = Grant.from_json(value['grant'])
                origin = Ref.from_json(request['origin_record_ref'])
                draft = DraftBrief.from_json(request['brief'])
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=1', (work.goal_id,))
                if (row is None or work.revision != 1 or work.epoch != 0 or value['state'] != 'queued' or
                        origin.kind.value != 'record' or _id(request['session_id']) != row['session_id'] or
                        origin != Ref.from_json(loads(row['origin_ref_json'])) or
                        _id(value['expert_id']) != row['expert_id'] or grant != Grant.from_json(loads(row['grant_json'])) or
                        _intersect(grant, scope) != grant or draft.target.repository not in grant.repositories):
                    raise ContractError()
                self._receipt_brief(draft, Brief.from_json(loads(row['brief_json'])))
            else:
                request = _obj(request, {'key', 'work_ref', 'command'})
                value = _obj(result.value.to_json(), {'work_ref', 'state', 'control_status'})
                target, work = _work(request['work_ref']), _work(value['work_ref'])
                command = request['command']
                kind = command.get('kind') if type(command) is dict else command
                if kind not in ('pause', 'resume', 'cancel', 'answer', 'change', 'complete'):
                    raise ContractError()
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
                prior = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (target.goal_id, target.revision))
                if (row is None or prior is None or work.goal_id != target.goal_id or
                        work.revision != target.revision + (1 if kind == 'change' else 0) or work.epoch > row['epoch'] or
                        value['state'] not in ('queued', 'running', 'waiting_input', 'paused', 'completed', 'cancelled') or
                        value['control_status'] not in ('none', 'pause_requested', 'draining')):
                    raise ContractError()
                for stored_row in (prior, row):
                    Brief.from_json(loads(stored_row['brief_json']))
                    Grant.from_json(loads(stored_row['grant_json']))
                    if Ref.from_json(loads(stored_row['origin_ref_json'])).kind.value != 'record':
                        raise ContractError()
                    _id(stored_row['session_id'])
                    _id(stored_row['expert_id'])
                if kind in ('pause', 'resume', 'cancel'):
                    if type(command) is not str or value['state'] not in {'pause': ('paused', 'running'), 'resume': ('queued', 'waiting_input'), 'cancel': ('cancelled',)}[kind]:
                        raise ContractError()
                    if kind == 'pause' and value['state'] == 'running' and value['control_status'] != 'pause_requested':
                        raise ContractError()
                elif kind == 'change':
                    _obj(command, {'kind', 'brief', 'origin_record_ref'})
                    origin = Ref.from_json(command['origin_record_ref'])
                    if origin.kind.value != 'record' or origin != Ref.from_json(loads(row['origin_ref_json'])):
                        raise ContractError()
                    self._receipt_brief(DraftBrief.from_json(command['brief']), Brief.from_json(loads(row['brief_json'])))
                    old_grant, grant = Grant.from_json(loads(prior['grant_json'])), Grant.from_json(loads(row['grant_json']))
                    if (_intersect(grant, old_grant) != grant or row['session_id'] != prior['session_id'] or
                            row['expert_id'] != prior['expert_id'] or value['state'] not in ('queued', 'running', 'paused')):
                        raise ContractError()
                elif kind == 'answer':
                    _obj(command, {'kind', 'question_id', 'answer_record_ref'})
                    answer = Ref.from_json(command['answer_record_ref'])
                    question = next((q for q in self._questions(row) if q['id'] == _id(command['question_id'])), None)
                    if (answer.kind.value != 'record' or question is None or question['answer'] != answer.to_json() or
                            value['state'] not in ('queued', 'paused') or value['control_status'] != 'none'):
                        raise ContractError()
                else:
                    _obj(command, {'kind', 'verification_ref'})
                    verification = Ref.from_json(command['verification_ref'])
                    if verification.kind.value != 'verification' or value['state'] != 'completed' or value['control_status'] != 'none':
                        raise ContractError()
                    events = self._rows("SELECT refs_json,session_id FROM v5_intake_event WHERE kind='result' AND text='work completed from saved verification' AND work_ref_json=?", (dumps(work),))
                    expected = [{'kind': 'artifact', 'id': item['artifact_id']} for item in self._artifact_set(work)] + [verification.to_json()]
                    if not any(loads(event['refs_json']) == expected and event['session_id'] == row['session_id'] for event in events):
                        raise ContractError()
            return result
        except (ContractError, KeyError, TypeError, ValueError):
            _reject('unavailable')

    @_public
    def get_create_by_key(self, request):
        return self._original_receipt('C03.create', _id(_obj(request, {'key'})['key']))

    @_public
    def get_control_by_key(self, request):
        return self._original_receipt('control', _id(_obj(request, {'key'})['key']))

    def _primary_reservation(self, item):
        session = self._own_session(ready=True)
        try:
            if item is None:
                raise ContractError()
            _id(item['id'])
            if (item['lease'], item['work'], item['idx'], item['kind'], item['role']) != (None, None, None, 'model', 'primary'):
                raise ContractError()
            if item['binding'] is not None:
                _id(item['binding'])
            binding = self._one('SELECT * FROM v5_tsk_primary_reservation WHERE reservation=?', (item['id'],))
            if binding is None:
                raise ContractError()
            owner = self._session(_id(binding['session']), self._enrollment())
            key = _id(binding['reserve_key'])
            replay = self._one("SELECT input_json,result_json FROM v5_intake_replay WHERE command='reserve_budget' AND key=?", (key,))
            if replay is None or replay['input_json'] != dumps({'key': key, 'kind': 'model', 'role': 'primary'}):
                raise ContractError()
            reserved = Result.from_json(loads(replay['result_json']))
            value = _obj(reserved.value.to_json(), {'reservation_id', 'remaining'})
            remaining = _obj(value['remaining'], {'host'})
            if (not reserved.ok or value['reservation_id'] != item['id'] or
                    type(remaining['host']) is not int or not 0 <= remaining['host'] <= _MAX):
                raise ContractError()
            consumed = self._one("SELECT input_json,result_json FROM v5_intake_replay WHERE command='consume' AND key=?", (item['id'],))
            if consumed is None:
                if item['binding'] is not None:
                    raise ContractError()
            else:
                expected = {'reservation_id': item['id'], 'call_or_operation_id': _id(item['binding'])}
                if consumed['input_json'] != dumps(expected) or Result.from_json(loads(consumed['result_json'])).to_json() != Result.success(expected).to_json():
                    raise ContractError()
        except (ContractError, KeyError, TypeError, AttributeError):
            _reject('unavailable')
        if owner['id'] != session['id']:
            _reject('denied')

    def _reserve_primary(self, key):
        session = self._own_session(ready=True)
        row = self._one("SELECT * FROM v5_tsk_host WHERE kind='model'")
        if (row is None or any(type(row[k]) is not int or not 0 <= row[k] <= _MAX for k in ('used', 'ceiling')) or
                row['used'] > row['ceiling']):
            _reject('unavailable')
        if row['used'] == row['ceiling']:
            _reject('limit')
        reservation = self._change_mint('reservation')
        self._conn.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'")
        self._conn.execute("INSERT INTO v5_tsk_reservation VALUES (?,NULL,NULL,NULL,'model','primary',NULL)", (reservation,))
        self._conn.execute('INSERT INTO v5_tsk_primary_reservation VALUES (?,?,?)', (reservation, session['id'], key))
        return {'reservation_id': reservation, 'remaining': {'host': row['ceiling'] - row['used'] - 1}}

    def _artifact_set(self, work):
        self._native_integrity()
        self._recovery_integrity()
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
        if 'work_ref' not in data:
            if data['kind'] != 'model' or data.get('role') != 'primary':
                raise ContractError()
            return self._transaction('reserve_budget', key, data, lambda: self._reserve_primary(key))
        if data['kind'] == 'operation':
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

    @staticmethod
    def _native_token(value):
        _id(value)
        if len(value.encode('utf-8')) > 512:
            raise ContractError()
        return value

    @staticmethod
    def _digest(value):
        return hashlib.sha256(dumps(value).encode('utf-8')).hexdigest()

    def _native_request(self, admission, request, profile):
        if type(profile) is not NativeProfile:
            raise ContractError()
        data = _obj(request, {'call_id', 'reservation_id', 'role', 'work_ref', 'messages', 'source_refs', 'output_kind'})
        if len(dumps(data).encode('utf-8')) > 65536:
            raise ContractError()
        if data['role'] != 'expert' or data['output_kind'] != 'expert_action':
            raise ContractError()
        for name in ('call_id', 'reservation_id', 'work_ref', 'source_refs'):
            if data[name] != admission[name]:
                _reject('conflict')
        for name in ('call_id', 'reservation_id', 'lease_id'):
            self._native_token(admission[name])
        work = _work(data['work_ref'])
        self._native_token(work.goal_id)
        refs = _refs(data['source_refs'])
        if len(refs) != len(data['source_refs']) or len(refs) > 64 or any(r.kind.value != 'record' for r in refs):
            raise ContractError()
        for ref in refs:
            self._native_token(ref.id)
        if type(data['messages']) is not list or not 1 <= len(data['messages']) <= 64:
            raise ContractError()
        for message in data['messages']:
            message = _obj(message, {'role', 'text'})
            if message['role'] not in ('system', 'user', 'assistant') or type(message['text']) is not str:
                raise ContractError()
        return data

    def _native_hash(self, call, side):
        # The mutable Step backlink is checked separately, so ordinary finish needs no re-seal.
        return self._digest({'call': {k: call[k] for k in
            ('id', 'lease', 'work', 'idx', 'reservation', 'sources', 'status', 'native')},
            'side': side})

    def _native_save(self, call_id, side, status):
        self._conn.execute('UPDATE v5_tsk_native SET wire=? WHERE call_id=?', (dumps(side), call_id))
        call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (call_id,))
        call['status'] = status
        self._conn.execute('UPDATE v5_tsk_call SET status=?,native_hash=? WHERE id=?',
            (status, self._native_hash(call, side), call_id))

    def _native_integrity(self):
        """Validate storage facts only; source stops never erase original cessation."""
        try:
            sides = {r['call_id']: r['wire'] for r in self._rows('SELECT * FROM v5_tsk_native')}
            admissions = {r['key']: r for r in self._rows(
                "SELECT * FROM v5_intake_replay WHERE command='admit_native_call'")}
            for call in self._rows('SELECT * FROM v5_tsk_call'):
                if call['native'] == 'mock':
                    if call['native_hash'] is not None or call['id'] in sides or call['id'] in admissions:
                        raise ContractError()
                    continue
                if call['native'] != 'native' or call['id'] not in sides:
                    raise ContractError()
                side = _obj(loads(sides.pop(call['id'])), {'admission', 'request', 'profile', 'request_hash',
                    'session', 'phase', 'attempt', 'ending', 'ending_hash', 'text', 'text_hash'})
                admission = _obj(side['admission'], {'call_id', 'lease_id', 'work_ref', 'reservation_id', 'source_refs'})
                p = _obj(side['profile'], {'id', 'model_id', 'qualification_sha256', 'evidence_kind', 'profile_sha256'})
                profile = NativeProfile.from_json(p)
                if profile.to_json() != p:
                    raise ContractError()
                request = self._native_request(admission, side['request'], profile)
                replay = admissions.pop(call['id'], None)
                if (replay is None or replay['input_json'] != dumps({'admission': admission, 'request': request, 'profile': p}) or
                        replay['result_json'] != dumps(Result.success({'call_id': call['id'], 'status': 'admitted'}))):
                    raise ContractError()
                work = _work(admission['work_ref'])
                if (call['id'] != admission['call_id'] or call['lease'] != admission['lease_id'] or
                        call['work'] != dumps(work) or call['reservation'] != admission['reservation_id'] or
                        call['sources'] != dumps(admission['source_refs']) or type(call['idx']) is not int or not 0 <= call['idx'] <= _MAX or
                        call['id'] != dumps(['C15.call', call['lease'], call['idx']]) or
                        side['request_hash'] != self._digest(request) or call['native_hash'] != self._native_hash(call, side)):
                    raise ContractError()
                lease = self._one('SELECT * FROM v5_tsk_lease WHERE id=?', (call['lease'],))
                if lease is None:
                    raise ContractError()
                owner, claim = self._lease_binding(lease, self._enrollment())
                if claim != work or side['session'] != owner['id']:
                    raise ContractError()
                reserved = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (call['reservation'],))
                if reserved is None or (reserved['lease'], reserved['work'], reserved['idx'], reserved['kind'], reserved['role'], reserved['binding']) != (
                        call['lease'], call['work'], call['idx'], 'model', 'expert', call['id']):
                    raise ContractError()
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (work.goal_id, work.revision))
                refs = _refs(admission['source_refs'])
                if row is None or not set(self._required(row)) <= set(refs) <= set(self._registered(row)):
                    raise ContractError()
                phase = side['phase']
                if side['attempt'] is not None:
                    attempt = _obj(side['attempt'], {'run_id', 'job_id', 'attempt_id'})
                    for value in attempt.values():
                        self._native_token(value)
                if phase in ('prepared', 'entering', 'unknown'):
                    if (call['status'] != 'admitted' or call['step'] is not None or
                            any(side[k] is not None for k in ('ending', 'ending_hash', 'text', 'text_hash')) or
                            (phase == 'prepared' and side['attempt'] is not None) or
                            (phase == 'entering' and side['attempt'] is None)):
                        raise ContractError()
                elif phase in ('returned', 'not_entered'):
                    if (call['status'] != phase or side['ending_hash'] != self._digest(side['ending']) or
                            len(dumps(side['ending']).encode('utf-8')) > 65536):
                        raise ContractError()
                    if phase == 'returned':
                        evidence = validate_native_evidence(side['ending'], request_sha256=side['request_hash'], profile=profile)
                        if (side['attempt'] is None or evidence['attempt_ref'] != side['attempt'] or
                                type(side['text']) is not str or len(side['text'].encode('utf-8')) != evidence['utf8_bytes'] or
                                hashlib.sha256(side['text'].encode('utf-8')).hexdigest() != evidence['output_sha256'] or
                                side['text_hash'] != evidence['output_sha256']):
                            raise ContractError()
                    else:
                        ending = _obj(side['ending'], {'request_sha256', 'profile_sha256', 'evidence_ref'})
                        NativeNeverEntered(**ending)
                        if (ending['request_sha256'] != side['request_hash'] or ending['profile_sha256'] != profile.profile_sha256 or
                                side['text'] is not None or side['text_hash'] is not None or call['step'] is not None):
                            raise ContractError()
                else:
                    raise ContractError()
                linked = self._rows('SELECT * FROM v5_tsk_step WHERE call=?', (call['id'],))
                if call['step'] is None:
                    if linked:
                        raise ContractError()
                else:
                    if len(linked) != 1 or linked[0]['id'] != call['step'] or phase != 'returned':
                        raise ContractError()
                    saved = linked[0]
                    step = _obj(loads(saved['wire']), {'step_id', 'work_ref', 'index', 'action', 'status', 'result_refs'}, {'error'})
                    self._native_token(saved['id'])
                    _refs(step['result_refs'])
                    if 'error' in step and type(step['error']) is not str:
                        raise ContractError()
                    if (saved['goal'], saved['revision'], saved['idx']) != (work.goal_id, work.revision, call['idx']) or (
                            step['step_id'] != saved['id'] or step['work_ref'] != work.to_json() or
                            type(step['index']) is not int or step['index'] != call['idx'] or
                            step['status'] not in ('started', 'finished', 'abandoned') or
                            step['action'] != parse_model_action(side['text'], allowed_refs=refs).to_json()):
                        raise ContractError()
            # Admission receipts also identify native producers if both mutable rows were cleared.
            if sides or admissions:
                raise ContractError()
        except (ContractError, _Rejected, ValueError, TypeError, KeyError, AttributeError):
            _reject('unavailable')

    def _native_side(self, call_id, *, owned=False):
        self._native_integrity()
        call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (call_id,))
        if call is None:
            _reject('not_found')
        if call['native'] != 'native':
            _reject('conflict')
        side = loads(self._one('SELECT wire FROM v5_tsk_native WHERE call_id=?', (call_id,))['wire'])
        if owned:
            session = self._own_session(ready=True)
            if side['session'] != session['id']:
                _reject('denied')
        return call, side

    @_public
    def admit_native_call(self, admission, *, c15_request, profile):
        data = _obj(admission, {'call_id', 'lease_id', 'work_ref', 'reservation_id', 'source_refs'})
        request = self._native_request(data, c15_request, profile)
        canonical = {'admission': data, 'request': request, 'profile': profile.to_json()}
        def operation():
            session = self._own_session(ready=True)
            result = self._admit_call(data)
            side = dict(canonical, request_hash=self._digest(request), session=session['id'], phase='prepared',
                        attempt=None, ending=None, ending_hash=None, text=None, text_hash=None)
            self._conn.execute('INSERT INTO v5_tsk_native VALUES (?,?)', (data['call_id'], dumps(side)))
            self._conn.execute("UPDATE v5_tsk_call SET native='native' WHERE id=?", (data['call_id'],))
            self._native_save(data['call_id'], side, 'admitted')
            return result
        return self._transaction('admit_native_call', data['call_id'], canonical, operation)

    @_public
    def enter_native_call(self, request):
        data = _obj(request, {'call_id', 'attempt_ref'})
        call_id = self._native_token(data['call_id'])
        attempt = _obj(data['attempt_ref'], {'run_id', 'job_id', 'attempt_id'})
        for value in attempt.values():
            self._native_token(value)
        def operation():
            call, side = self._native_side(call_id, owned=True)
            if side['phase'] != 'prepared':
                _reject('conflict')
            self._authority(_work(loads(call['work'])), call['lease'])
            self._gate(_refs(loads(call['sources'])))
            side.update(phase='entering', attempt=attempt)
            self._native_save(call_id, side, 'admitted')
            return {'call_id': call_id, 'status': 'entered'}
        return self._transaction('enter_native_call', None, data, operation)

    @_public
    def mark_native_unknown(self, request):
        data = _obj(request, {'call_id'})
        call_id = self._native_token(data['call_id'])
        def operation():
            call, side = self._native_side(call_id, owned=True)
            if side['phase'] not in ('prepared', 'entering', 'unknown'):
                _reject('conflict')
            if side['phase'] != 'unknown':
                side['phase'] = 'unknown'
                self._native_save(call_id, side, 'admitted')
            return {'call_id': call_id, 'status': 'admitted', 'phase': 'unknown'}
        return self._transaction('mark_native_unknown', None, data, operation)

    @_public
    def end_native_call(self, request, *, ending):
        data = _obj(request, {'call_id'})
        call_id = self._native_token(data['call_id'])
        def operation():
            call, side = self._native_side(call_id, owned=True)
            p = side['profile']
            profile = NativeProfile.from_json(p)
            text = text_hash = None
            if type(ending) is NativeReturned:
                evidence = ending.validate(request_sha256=side['request_hash'], profile=profile)
                if side['attempt'] is None or evidence['attempt_ref'] != side['attempt']:
                    _reject('conflict')
                phase, text, text_hash = 'returned', ending.text, evidence['output_sha256']
            elif type(ending) is NativeNeverEntered:
                if ending.request_sha256 != side['request_hash'] or ending.profile_sha256 != profile.profile_sha256:
                    _reject('conflict')
                phase = 'not_entered'
                evidence = {'request_sha256': ending.request_sha256, 'profile_sha256': ending.profile_sha256,
                            'evidence_ref': ending.evidence_ref}
                NativeNeverEntered(**evidence)
            else:
                raise ContractError()
            if len(dumps(evidence).encode('utf-8')) > 65536:
                raise ContractError()
            updated = dict(side, phase=phase, ending=evidence, ending_hash=self._digest(evidence), text=text, text_hash=text_hash)
            if side['phase'] in ('returned', 'not_entered'):
                if side != updated:
                    _reject('conflict')
            else:
                self._native_save(call_id, updated, phase)
            return {'call_id': call_id, 'status': phase}
        return self._transaction('end_native_call', None, data, operation)

    @_public
    def get_native_output(self, request):
        data = _obj(request, {'call_id', 'lease_id', 'work_ref'})
        def operation():
            call, side = self._native_side(self._native_token(data['call_id']))
            work = _work(data['work_ref'])
            if call['lease'] != _id(data['lease_id']) or call['work'] != dumps(work):
                _reject('stale')
            self._authority(work, call['lease'])
            self._gate(_refs(loads(call['sources'])))
            if side['phase'] != 'returned':
                _reject('unavailable')
            return {'call_id': call['id'], 'status': 'succeeded', 'content': side['text'], 'model_id': side['profile']['model_id']}
        return self._transaction('get_native_output', None, data, operation)

    @_public
    def admit_call(self, request):
        data = _obj(request, {'call_id', 'lease_id', 'work_ref', 'reservation_id', 'source_refs'})
        call_id, lease_id, reservation = (_id(data[name]) for name in ('call_id', 'lease_id', 'reservation_id'))
        work, refs = _work(data['work_ref']), _refs(data['source_refs'])
        return self._transaction('admit_call', call_id, data, lambda: self._admit_call(data))

    def _admit_call(self, data):
        call_id, lease_id, reservation = (_id(data[name]) for name in ('call_id', 'lease_id', 'reservation_id'))
        work, refs = _work(data['work_ref']), _refs(data['source_refs'])
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
        self._conn.execute('INSERT INTO v5_tsk_call(id,lease,work,idx,reservation,sources,status,step) VALUES (?,?,?,?,?,?,?,NULL)',
                           (call_id, lease_id, dumps(work), index, reservation, dumps(_wire(refs)), 'admitted'))
        return {'call_id': call_id, 'status': 'admitted'}

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
        self._native_integrity()
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
        if call['native'] == 'native':
            _, side = self._native_side(call['id'])
            result.update(profile_id=side['profile']['id'], native_phase=side['phase'], may_enter=False)
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
            if call['native'] == 'native':
                _, side = self._native_side(call['id'])
                if parse_model_action(side['text'], allowed_refs=refs).to_json() != action:
                    _reject('conflict')
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
        self._native_integrity()
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
                if call['native'] == 'native':
                    self._gate(_refs(loads(call['sources'])))
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
            enrollment = self._enrollment() if claim is not None else None
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
                source_wire = loads(call['sources'])
                source_refs = _refs(source_wire)
                if claim is not None and (not source_refs or len(source_refs) != len(source_wire)):
                    raise ContractError()
                sources = set(source_refs)
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
                if enrollment is not None:
                    _, original_claim = self._lease_binding(call_lease, enrollment)
                    if work != original_claim:
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
