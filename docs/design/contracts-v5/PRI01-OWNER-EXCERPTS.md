# PRI01 actual TSK owner excerpts

Complete selected methods from `pal/tasks_v5.py`, SHA256 `498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f`.
Omitted methods are not supplied/claimed inspected; current full MEM/intake owners accompany this input.

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

## TaskStore.get_work — original lines 301–313

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

## TaskStore.get_execution_context — original lines 315–345

```python
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
```

## TaskStore.reserve_budget — original lines 358–373

```python
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
```

## TaskStore.consume — original lines 375–379

```python
    @_public
    def consume(self, request):
        data = _obj(request, {'reservation_id', 'call_or_operation_id'})
        reservation, binding = _id(data['reservation_id']), _id(data['call_or_operation_id'])
        return self._transaction('consume', reservation, data, lambda: self._bind(reservation, binding))
```

## TaskStore.verification_context — original lines 480–483

```python
    def verification_context(self, connection, request, *, purpose):
        """Readonly VER snapshot; factual status is independent of execution rights."""
        self._require_transaction(connection)
        return self._verification_context(request, purpose=purpose)
```

## TaskStore._answer — original lines 942–960

```python
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
```

## TaskStore._change — original lines 980–1035

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

## TaskStore.control — original lines 1092–1161

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

