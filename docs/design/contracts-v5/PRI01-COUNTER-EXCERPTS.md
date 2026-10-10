# PRI01 actual counter and transaction excerpts

Verbatim selected methods only, not full-source review. Source SHA256 8f20d02d132b3a70a811919a262b928b0904cc30de8479a977c0c204b95c1670. All unshown methods are omitted; current code has no Primary workless reservation/candidate listing. Astra separately inspected whole source; its proposal is not implementation.

## _execution_request
```python
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
```

## _transaction
```python
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
```

## _remaining
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

## _reserve
```python
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
```

## _bind
```python
    def _bind(self, reservation, binding):
        item = self._one('SELECT * FROM v5_tsk_reservation WHERE id=?', (reservation,))
        if item is None:
            _reject('not_found')
        if item['binding'] is not None and item['binding'] != binding:
            _reject('conflict')
        self._conn.execute('UPDATE v5_tsk_reservation SET binding=? WHERE id=?', (binding, reservation))
        return {'reservation_id': reservation, 'call_or_operation_id': binding}
```

## reserve_budget
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

## consume
```python
    @_public
    def consume(self, request):
        data = _obj(request, {'reservation_id', 'call_or_operation_id'})
        reservation, binding = _id(data['reservation_id']), _id(data['call_or_operation_id'])
        return self._transaction('consume', reservation, data, lambda: self._bind(reservation, binding))
```

