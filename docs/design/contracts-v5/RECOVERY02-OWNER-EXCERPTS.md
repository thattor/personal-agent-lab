# RECOVERY02 observed TSK owner excerpts

Source base: 85f3769 (identical owner source to73b209a).
Source SHA256: 498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f
Complete selected methods only; omitted TSK code is not inspected. RECOVERY01 recovery source is pending and absent here.

## _required

```python
    def _required(self, row):
        return tuple(dict.fromkeys((Ref.from_json(loads(row['origin_ref_json'])),
                                   *Brief.from_json(loads(row['brief_json'])).context_refs)))
```

## _steps

```python
    def _steps(self, row):
        return self._rows('SELECT * FROM v5_tsk_step WHERE goal=? AND revision=? ORDER BY idx', (row['goal_id'], row['revision']))
```

## _artifact_set

```python
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
```

## get_execution_context

```python
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

## finish_step

```python
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
```

## _old_calls

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

