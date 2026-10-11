# RECOVERY01 actual TSK owner excerpts

Complete selected methods from `pal/tasks_v5.py`, SHA256 `498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`.
Omitted methods are not supplied/claimed inspected; full RUN and shared contract accompany this input.

## TaskStore.__init__ — original lines 70–103

```python
    def __init__(self, connection, *, host_limits, artifact_inspect=None, verification_inspect=None, **kwargs):
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
```

## TaskStore._transaction — original lines 114–128

```python
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
        except BaseException:
            self._rollback()
            raise
```

## TaskStore._current — original lines 130–136

```python
    def _current(self, work, epoch=True):
        row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? ORDER BY revision DESC LIMIT 1', (work.goal_id,))
        if row is None:
            _reject('not_found')
        if row['revision'] != work.revision or (epoch and row['epoch'] != work.epoch):
            _reject('stale')
        return row
```

## TaskStore._flags — original lines 141–143

```python
    def _flags(self, row):
        return self._one('SELECT * FROM v5_tsk_control WHERE goal=? AND revision=?',
                         (row['goal_id'], row['revision'])) or {'pause': 0, 'drain': 0}
```

## TaskStore._authority — original lines 149–159

```python
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
```

## TaskStore._index — original lines 181–183

```python
    def _index(self, row):
        steps = self._steps(row)
        return steps[-1]['idx'] + 1 if steps else 0
```

## TaskStore._event — original lines 218–219

```python
    def _event(self, row, kind, text, refs=()):
        self._append_event(row['session_id'], self._wr(row), kind, text, refs)
```

## TaskStore._claim_wire — original lines 221–235

```python
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
```

## TaskStore.claim — original lines 237–263

```python
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
            self._event(row, 'state', 'work running')
            return self._claim_wire(row, lease)
        return self._transaction('claim', None, data, operation)
```

## TaskStore.admit_call — original lines 381–410

```python
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
```

## TaskStore.end_call — original lines 412–426

```python
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
```

## TaskStore.get_call — original lines 428–445

```python
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
```

## TaskStore._questions — original lines 813–860

```python
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
```

## TaskStore._old_calls — original lines 1037–1090

```python
    def _old_calls(self, row, lease):
        try:
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease['id'],))
            linked, indexes = set(), set()
            required, registered = set(self._required(row)), set(self._registered(row))
            for call in calls:
                _id(call['id'])
                _id(call['reservation'])
                sources = set(_refs(loads(call['sources'])))
                if not required <= sources <= registered:
                    raise ContractError()
                work = _work(loads(call['work']))
                if (call['status'] not in ('admitted', 'returned', 'raised', 'not_entered') or
                        (work.goal_id, work.revision) != (row['goal_id'], row['revision']) or
                        work.epoch > row['epoch'] or type(call['idx']) is not int or not 0 <= call['idx'] <= _MAX):
                    raise ContractError()
                if call['id'] != dumps(['C15.call', lease['id'], call['idx']]):
                    raise ContractError()
                if call['idx'] in indexes:
                    raise ContractError()
                indexes.add(call['idx'])
                reservation = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (call['reservation'],))
                if (reservation is None or type(reservation['idx']) is not int or
                        (reservation['lease'], _work(loads(reservation['work'])), reservation['idx'],
                         reservation['kind'], reservation['role'], reservation['binding']) !=
                        (lease['id'], work, call['idx'], 'model', 'expert', call['id'])):
                    raise ContractError()
                if call['step'] is not None:
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
                    linked.add(saved['id'])
            # Other leases may have finished historical Steps, but no dangling owned linkage.
            for saved in self._steps(row):
                call = self._one('SELECT * FROM v5_tsk_call WHERE id=?', (saved['call'],))
                if call is None or call['step'] != saved['id']:
                    raise ContractError()
                if loads(saved['wire'])['status'] == 'started' and saved['id'] not in linked:
                    raise ContractError()
        except (ContractError, KeyError, TypeError):
            _reject('unavailable')
        if any(call['status'] == 'admitted' for call in calls):
            _reject('conflict')
```

## TaskStore.release — original lines 1163–1228

```python
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
                state = 'cancelled' if row['state'] == 'cancelled' else 'paused' if flags['pause'] else 'queued'
                row['state'] = state
                self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?', (state, row['goal_id'], row['revision']))
                self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
                self._set_flags(row, 0, 0)
                self._event(row, 'state', data['reason'])
                return {'work_ref': self._wr(row).to_json(), 'state': state, 'control_status': 'none'}
            calls = self._rows('SELECT * FROM v5_tsk_call WHERE lease=?', (lease_id,))
            if any(call['status'] not in ('admitted', 'returned', 'raised', 'not_entered') for call in calls):
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
            state = (row['state'] if row['state'] in ('completed', 'cancelled', 'failed') else 'paused' if flags['pause'] else
                     'queued' if flags['drain'] or data['outcome'] == 'yield' else 'failed')
            row['state'] = state
            self._conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=? AND revision=?', (state, work.goal_id, work.revision))
            self._conn.execute('UPDATE v5_tsk_lease SET active=0 WHERE id=?', (lease_id,))
            self._set_flags(row, 0, 0)
            self._event(row, 'state', data['reason'])
            return {'work_ref': self._wr(row).to_json(), 'state': state, 'control_status': 'none'}
        return self._transaction('release', lease_id, data, operation)
```

