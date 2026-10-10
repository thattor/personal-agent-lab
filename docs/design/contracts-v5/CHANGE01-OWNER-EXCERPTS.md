# CHANGE01 actual TSK owner excerpts

Exact source SHA256 `498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`, author b4baae24. Selected complete methods only, generated verbatim with original line numbers. Omitted methods/imports are outside this design evidence; the full implementation received separate Sol review. No restart-recovery method currently exists on TaskStore. Review may identify missing input rather than infer coverage.

### _transaction — source lines 114–128

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

### _current — source lines 130–136

```python
    def _current(self, work, epoch=True):
        row = self._one('SELECT * FROM v5_intake_work WHERE goal_id=? ORDER BY revision DESC LIMIT 1', (work.goal_id,))
        if row is None:
            _reject('not_found')
        if row['revision'] != work.revision or (epoch and row['epoch'] != work.epoch):
            _reject('stale')
        return row
```

### _flags — source lines 141–143

```python
    def _flags(self, row):
        return self._one('SELECT * FROM v5_tsk_control WHERE goal=? AND revision=?',
                         (row['goal_id'], row['revision'])) or {'pause': 0, 'drain': 0}
```

### _set_flags — source lines 145–147

```python
    def _set_flags(self, row, pause, drain):
        self._conn.execute('INSERT INTO v5_tsk_control VALUES (?,?,?,?) ON CONFLICT(goal,revision) DO UPDATE SET pause=excluded.pause,drain=excluded.drain',
                           (row['goal_id'], row['revision'], pause, drain))
```

### _authority — source lines 149–159

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

### _required — source lines 161–163

```python
    def _required(self, row):
        return tuple(dict.fromkeys((Ref.from_json(loads(row['origin_ref_json'])),
                                   *Brief.from_json(loads(row['brief_json'])).context_refs)))
```

### _registered — source lines 165–167

```python
    def _registered(self, row):
        return tuple(Ref(item['kind'], item['id']) for item in self._rows(
            'SELECT kind,id FROM v5_intake_source WHERE goal_id=? AND revision=? ORDER BY rowid', (row['goal_id'], row['revision'])))
```

### _gate — source lines 169–172

```python
    def _gate(self, refs):
        result = self._check_sources(refs)
        if result is not None:
            raise _Rejected(result)
```

### _steps — source lines 178–179

```python
    def _steps(self, row):
        return self._rows('SELECT * FROM v5_tsk_step WHERE goal=? AND revision=? ORDER BY idx', (row['goal_id'], row['revision']))
```

### _index — source lines 181–183

```python
    def _index(self, row):
        steps = self._steps(row)
        return steps[-1]['idx'] + 1 if steps else 0
```

### _remaining — source lines 185–192

```python
    def _remaining(self, row):
        limits = Grant.from_json(loads(row['grant_json'])).limits
        result = {}
        for kind, ceiling in [('model', limits.max_model_calls), ('step', limits.max_steps)]:
            host = self._one('SELECT * FROM v5_tsk_host WHERE kind=?', (kind,))
            used = self._one('SELECT used FROM v5_tsk_usage WHERE goal=? AND kind=?', (row['goal_id'], kind))
            result[kind] = {'work': max(0, ceiling - (used['used'] if used else 0)), 'host': max(0, host['ceiling'] - host['used'])}
        return result
```

### claim — source lines 237–263

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

### get_work — source lines 301–313

```python
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
```

### _change_mint — source lines 962–978

```python
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
```

### _change — source lines 980–1035

```python
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
```

### _old_calls — source lines 1037–1090

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

### control — source lines 1092–1161

```python
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
```

### release — source lines 1163–1228

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

### invalidate_by_refs — source lines 1230–1274

```python
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
```
