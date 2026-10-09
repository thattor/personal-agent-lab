"""RUN01/2 bounded mock composition; no provider, persistent runner state or recovery.

The host owns exactly one invoker per process and mints a new runner identity on
restart. This is trusted Python coordination, not a boundary for arbitrary code.
Only callback return/exception proves cessation here; no remote process is modeled.
"""
import copy
import threading
import uuid

from pal.contracts_v5 import ContractError, ErrorCode, Ref, Result, dumps


def _value(result):
    return result.value.to_json()


def _failure(code, message):
    return Result.failure(code, message)


def _refs(values):
    return tuple(dict.fromkeys(Ref.from_json(value) for value in values))


class MockInvoker:
    """One local owner per call identity; a receipt is never a dispatch permit."""

    def __init__(self):
        self._owned = set()
        self._lock = threading.Lock()

    @staticmethod
    def _end(tasks, call_id, outcome):
        request = {'call_id': call_id, 'outcome': outcome}
        for _ in range(3):
            result = tasks.end_call(request)
            if result.ok or result.error.code is not ErrorCode.UNAVAILABLE:
                return result
        return result

    def invoke(self, tasks, admission, callback):
        if not callable(callback):
            return _failure(ErrorCode.INVALID_INPUT, 'mock callable required')
        call_id = admission.get('call_id') if type(admission) is dict else None
        if type(call_id) is not str or not call_id:
            return _failure(ErrorCode.INVALID_INPUT, 'call identity required')
        with self._lock:
            if call_id in self._owned:
                return _failure(ErrorCode.CONFLICT, 'mock call already owned')
            self._owned.add(call_id)

        existing = tasks.get_call({'call_id': call_id})
        if existing.ok:
            return _failure(ErrorCode.CONFLICT, 'stored call cannot be dispatched again')
        if existing.error.code is not ErrorCode.NOT_FOUND:
            return existing
        admitted = tasks.admit_call(admission)
        if not admitted.ok:
            return admitted
        current = tasks.get_call({'call_id': call_id})
        if not current.ok or not _value(current)['may_enter']:
            ended = self._end(tasks, call_id, 'not_entered')
            if not ended.ok:
                return ended
            return current if not current.ok else _failure(
                ErrorCode.CONFLICT, 'mock call stopped before entry')

        try:
            action = callback()
        except BaseException as error:
            ended = self._end(tasks, call_id, 'raised')
            if not isinstance(error, Exception):
                raise
            return ended if not ended.ok else _failure(
                ErrorCode.UNAVAILABLE, 'mock callable failed')
        ended = self._end(tasks, call_id, 'returned')
        if not ended.ok:
            return ended
        try:
            return Result.success({'call_id': call_id, 'action': action})
        except ContractError:
            return _failure(ErrorCode.INVALID_INPUT, 'mock output is not JSON data')


class MockRunner:
    """Run a finite report/lookup slice on supplied same-thread TSK/MEM owners.

    expert receives the C12 object and two mock-only diagnostic keyword arguments:
    excluded_refs and excluded_step_ids. They contain identities, never stopped bodies.
    The object must not be reused across processes or concurrent runner threads.
    Structured controls use another connection and never acquire an invoker lock.
    """

    def __init__(self, tasks, memory):
        self._tasks = tasks
        self._memory = memory
        self.runner_id = 'mock-runner-' + uuid.uuid4().hex
        self.invoker = MockInvoker()

    def _read_context(self, required, optional):
        values, excluded = [], []
        required_set = set(required)
        for ref in dict.fromkeys((*required, *optional)):
            read = self._memory.read({'ref': ref.to_json()}, purpose='model_context')
            if read.ok:
                values.append(_value(read))
            elif ref not in required_set and read.error.code in (
                    ErrorCode.DENIED, ErrorCode.NOT_FOUND):
                excluded.append(ref)
            else:
                return read, [], []
        return None, values, excluded

    def run_once(self, expert, *, max_steps=1):
        if not callable(expert) or type(max_steps) is not int or not 1 <= max_steps <= 100:
            return _failure(ErrorCode.INVALID_INPUT, 'invalid mock slice configuration')
        claimed = self._tasks.claim({'runner_id': self.runner_id})
        if not claimed.ok:
            return claimed
        lease = _value(claimed)
        if lease.get('status') == 'empty':
            return claimed
        work = lease['work_ref']
        lease_id = lease['lease_id']
        steps = list(lease['steps'])
        finished, calls, excluded_steps_all = [], [], []
        excluded_all = list(_refs(lease['checkpoint'].get('lookup_excluded_refs', [])))

        def release(outcome, reason, error_code=None):
            result = self._tasks.release({'lease_id': lease_id, 'work_ref': work,
                                           'outcome': outcome, 'reason': reason})
            if not result.ok:
                return result
            value = dict(_value(result), status='released', lease_id=lease_id,
                         steps=finished, call_ids=calls,
                         excluded_refs=[ref.to_json() for ref in dict.fromkeys(excluded_all)],
                         excluded_step_ids=list(dict.fromkeys(excluded_steps_all)))
            if error_code is not None:
                value['reason_code'] = error_code.value
            return Result.success(value)

        output_pending = False

        def failed(result, reason):
            if result.error.code is ErrorCode.UNAVAILABLE:
                if output_pending:
                    return _failure(ErrorCode.UNAVAILABLE, 'local result persistence unresolved')
                return release('yield', reason, result.error.code)
            return release('failed', reason, result.error.code)

        def persist(method, request, **kwargs):
            for _ in range(3):
                result = method(request, **kwargs)
                if result.ok or result.error.code is not ErrorCode.UNAVAILABLE:
                    return result
            return result

        # A returned output has no durable MOD body to recover here. A fresh run
        # must not turn a retained lease into permission for another model unit.
        if any(step['status'] == 'started' for step in steps):
            return _failure(ErrorCode.UNAVAILABLE, 'unfinished step requires recovery')
        next_index = max((step['index'] for step in steps), default=-1) + 1
        existing = self._tasks.get_call({'call_id': dumps(['C15.call', lease_id, next_index])})
        if existing.ok:
            return _failure(ErrorCode.UNAVAILABLE, 'owned call requires recovery')
        if existing.error.code is not ErrorCode.NOT_FOUND:
            return failed(existing, 'call readiness unavailable')

        for _ in range(max_steps):
            context_result = self._tasks.get_execution_context(
                {'lease_id': lease_id, 'work_ref': work})
            if not context_result.ok:
                return failed(context_result, 'execution context unavailable')
            metadata = _value(context_result)
            required, optional = _refs(metadata['required_refs']), _refs(metadata['optional_refs'])
            registered = self._tasks.register_sources(
                {'work_ref': work, 'refs': [ref.to_json() for ref in required]})
            if not registered.ok:
                return failed(registered, 'required source unavailable')
            error, context, excluded = self._read_context(required, optional)
            if error is not None:
                return failed(error, 'source context unavailable')
            excluded_all.extend(excluded)
            available = {Ref.from_json(item['ref']) for item in context}
            provenance = {item['step_id']: set(_refs(item['refs']))
                          for item in metadata['step_sources']}
            eligible_steps, excluded_steps = [], []
            for step in steps:
                if step['status'] != 'finished':
                    continue
                sources = provenance.get(step['step_id'])
                if sources is None:
                    return failed(_failure(ErrorCode.UNAVAILABLE, 'step provenance missing'),
                                  'step provenance unavailable')
                if sources <= available:
                    eligible_steps.append(step)
                else:
                    excluded_steps.append(step['step_id'])
            excluded_steps_all.extend(excluded_steps)
            remaining = metadata['remaining_budget']
            if any(remaining[kind]['work'] <= 0 for kind in ('model', 'step')):
                return release('failed', 'work budget exhausted', ErrorCode.LIMIT)
            if any(remaining[kind]['host'] <= 0 for kind in ('model', 'step')):
                return release('yield', 'host budget exhausted', ErrorCode.LIMIT)
            index = metadata['next_step_index']
            reservation = self._tasks.reserve_budget({
                'key': dumps(['RUN01.model', lease_id, index]), 'work_ref': work,
                'kind': 'model', 'role': 'expert'})
            if not reservation.ok:
                return failed(reservation, 'model reservation unavailable')
            call_id = dumps(['C15.call', lease_id, index])
            c12 = {'work_ref': work, 'brief': lease['brief'], 'grant_summary': lease['grant'],
                   'context': context, 'steps': eligible_steps, 'remaining_budget': remaining}
            called = self.invoker.invoke(self._tasks, {
                'call_id': call_id, 'lease_id': lease_id, 'work_ref': work,
                'reservation_id': _value(reservation)['reservation_id'],
                'source_refs': [item['ref'] for item in context]},
                lambda: expert(copy.deepcopy(c12),
                               excluded_refs=tuple(ref.to_json() for ref in dict.fromkeys(excluded_all)),
                               excluded_step_ids=tuple(excluded_steps)))
            calls.append(call_id)
            if not called.ok:
                if called.error.code is ErrorCode.UNAVAILABLE:
                    status = self._tasks.get_call({'call_id': call_id})
                    if status.ok and _value(status)['status'] == 'raised':
                        return release('failed', 'mock callable raised', ErrorCode.UNAVAILABLE)
                    if (status.ok and _value(status)['status'] in ('admitted', 'returned')) or (
                            not status.ok and status.error.code is not ErrorCode.NOT_FOUND):
                        return _failure(ErrorCode.UNAVAILABLE, 'owned call outcome unresolved')
                return failed(called, 'mock call unavailable or stopped')
            output_pending = True
            begun = persist(self._tasks.begin_step, {
                'key': dumps(['C13.begin_step', call_id]), 'work_ref': work,
                'action': _value(called)['action']})
            if not begun.ok:
                return failed(begun, 'mock action could not be adopted')
            step = _value(begun)
            result_refs, lookup_excluded, truncated = [], [], False
            if step['action']['kind'] == 'lookup':
                found = self._memory.search({'session_id': metadata['session_id'],
                                             'query': step['action']['query'], 'limit': 50})
                if not found.ok:
                    return failed(found, 'lookup unavailable')
                found_value = _value(found)
                truncated = found_value['truncated']
                candidates = _refs([*(step['action'].get('source_refs') or []),
                                    *found_value['record_refs']])
                read_error, usable, lookup_excluded = self._read_context((), candidates)
                if read_error is not None:
                    return failed(read_error, 'lookup source unavailable')
                result_refs = [item['ref'] for item in usable]
                excluded_all.extend(lookup_excluded)
            ended_step = persist(self._tasks.finish_step,
                {'work_ref': work, 'step_id': step['step_id'], 'result_refs': result_refs},
                truncated=truncated, excluded_refs=tuple(lookup_excluded))
            if not ended_step.ok:
                return failed(ended_step, 'mock step could not be saved')
            finished.append(_value(ended_step))
            steps.append(_value(ended_step))
            output_pending = False
        return release('yield', 'bounded mock slice yielded')
