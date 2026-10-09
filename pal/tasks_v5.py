"""Transactional execution rights for a trusted local mock host (TSK02/1)."""
from functools import wraps

from pal.contracts_v5 import (Brief, ContractError, Grant, Limits, Ref, Result,
                              WorkRef, dumps, loads, parse_model_action)
from pal.intake_v5 import IntakeStore

_MAX = 2**63 - 1


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
    def __init__(self, connection, *, host_limits, **kwargs):
        if type(host_limits) is not Limits or any(x > _MAX for x in
                (host_limits.max_operations, host_limits.max_steps, host_limits.max_model_calls)):
            raise ValueError('finite SQLite host limits required')
        super().__init__(connection, **kwargs)
        schema = (
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
        except Exception:
            self._rollback()
            raise

    def _rows(self, sql, args=()):
        cursor = self._conn.execute(sql, args)
        names = [item[0] for item in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]

    def _one(self, sql, args=()):
        rows = self._rows(sql, args)
        return rows[0] if rows else None

    def _transaction(self, command, key, request, operation):
        self._require_idle()
        self._conn.execute('BEGIN IMMEDIATE')
        try:
            canonical = dumps(request)
            result = self._lookup_replay(command, key, canonical) if key is not None else None
            if result is None:
                result = Result.success(operation())
                if key is not None:
                    self._save_replay(command, key, canonical, result)
            self._conn.execute('COMMIT')
            return result
        except Exception:
            self._rollback()
            raise

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
        checkpoint = {'last_finished_index': -1, 'open_question_refs': []}
        if finished:
            last = finished[-1]
            checkpoint['last_finished_index'] = last['idx']
            if loads(last['wire'])['action']['kind'] == 'lookup':
                checkpoint.update(lookup_truncated=bool(last['truncated']), lookup_excluded_refs=loads(last['excluded']))
        return {'lease_id': lease['id'], 'work_ref': self._wr(row).to_json(), 'brief': loads(row['brief_json']),
                'grant': loads(row['grant_json']), 'checkpoint': checkpoint,
                'steps': [loads(step['wire']) for step in steps], 'pending_inputs': []}

    @_public
    def claim(self, request):
        data = _obj(request, {'runner_id'})
        runner = _id(data['runner_id'])
        def operation():
            lease = self._one('SELECT * FROM v5_tsk_lease WHERE active=1')
            if lease:
                if lease['runner'] != runner:
                    _reject('conflict')
                row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? AND revision=?', (lease['goal'], lease['revision']))
                return self._claim_wire(row, lease)
            row = self._one("SELECT * FROM v5_intake_work WHERE state='queued' ORDER BY rowid LIMIT 1")
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
            self._event(row, 'state', 'work running')
            return self._claim_wire(row, lease)
        return self._transaction('claim', None, data, operation)

    @_public
    def get_execution_context(self, request):
        data = _obj(request, {'lease_id', 'work_ref'})
        row, _ = self._authority(_work(data['work_ref']), _id(data['lease_id']))
        required = self._required(row)
        registered = self._registered(row)
        if not set(required) <= set(registered):
            _reject('unavailable')
        provenance = []
        for step in self._steps(row):
            call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (step['call'],))
            if call is None or call['step'] != step['id']:
                _reject('unavailable')
            refs = tuple(dict.fromkeys((*_refs(loads(call['sources'])), *_refs(loads(step['wire'])['result_refs']))))
            if not set(refs) <= set(registered) or not set(required) <= set(refs):
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
        may_enter = False
        if call['status'] == 'admitted':
            try:
                self._authority(_work(loads(call['work'])), call['lease'])
                may_enter = True
            except _Rejected:
                pass
        result = {'call_id': call['id'], 'lease_id': call['lease'], 'work_ref': loads(call['work']),
                  'index': call['idx'], 'status': call['status'], 'may_enter': may_enter}
        if call['step'] is not None:
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
            if action['kind'] not in ('report', 'lookup'):
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
            if step['status'] != 'started':
                _reject('conflict')
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

    @_public
    def control(self, request):
        data = _obj(request, {'key', 'work_ref', 'command'})
        key, work = _id(data['key']), _work(data['work_ref'])
        if data['command'] not in ('pause', 'resume', 'cancel'):
            raise ContractError()
        def operation():
            row = self._current(work, epoch=False)
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
            elif command == 'pause':
                if row['state'] == 'running':
                    flags['pause'] = 1
                elif row['state'] == 'queued':
                    row['state'] = 'paused'
                elif row['state'] != 'paused':
                    _reject('conflict')
            else:
                if row['state'] != 'paused':
                    _reject('conflict')
                row['state'] = 'queued'
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
            row = self._current(work, epoch=False)
            flags = self._flags(row)
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease_id,))
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
            state = ('cancelled' if row['state'] == 'cancelled' else 'paused' if flags['pause'] else
                     'queued' if flags['drain'] or data['outcome'] == 'yield' else 'failed')
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
            if row['state'] not in ('queued', 'running', 'paused') or row['epoch'] == _MAX:
                _reject('unavailable')
            affected.append(row)
        for row in affected:
            row['epoch'] += 1
            self._conn.execute('UPDATE v5_intake_work SET epoch=? WHERE goal_id=? AND revision=?', (row['epoch'], row['goal_id'], row['revision']))
            if row['state'] == 'running':
                self._set_flags(row, self._flags(row)['pause'], 1)
            self._event(row, 'state', 'work sources invalidated', tuple(refs))
        result = Result.success({'work_refs': [self._wr(row).to_json() for row in affected]})
        self._save_replay('TSK.invalidate_by_refs', key, canonical, result)
        return result
