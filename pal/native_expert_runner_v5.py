"""Explicit native Expert orchestration through public TSK-owned evidence APIs."""
import copy
from contextlib import ExitStack
from pal.contracts_v5 import ContractError, ErrorCode, Result, dumps, parse_model_action
from pal.native_call_v5 import NativeProfile, NativeReturned, NativeNeverEntered
from pal.mock_runner_v5 import _RunnerCore, _failure, _value, _refs


class NativeExpertRunner(_RunnerCore):
    def __init__(self, tasks, memory, *, provider, artifacts=None, verifier=None):
        if (callable(provider) or type(getattr(provider, 'profile', None)) is not NativeProfile
                or not callable(getattr(provider, 'preflight', None))
                or not callable(getattr(provider, 'invoke', None))):
            raise TypeError('explicit native provider required')
        super().__init__(tasks, memory, artifacts=artifacts, verifications=verifier)
        self._provider = provider
        self._profile = provider.profile
        self._owned = set()

    @staticmethod
    def _call_shape(call):
        return (set(call) == {'call_id', 'lease_id', 'work_ref', 'index', 'status', 'may_enter',
                             'step_id', 'profile_id', 'native_phase'}
                and call['native_phase'] == 'returned')

    def execute_next(self):
        try:
            self._provider.preflight()
            if self._provider.profile != self._profile:
                return _failure(ErrorCode.UNAVAILABLE, 'native profile changed')
        except Exception:
            return _failure(ErrorCode.UNAVAILABLE, 'native preflight unavailable')
        return self._run_slice(None)

    @staticmethod
    def _persist(method, request, **kwargs):
        result = None
        for _ in range(3):
            try:
                result = method(copy.deepcopy(request), **kwargs)
                if type(result) is not Result:
                    return _failure(ErrorCode.UNAVAILABLE, 'native owner response unavailable')
                result = Result.from_json(result.to_json())
            except Exception:
                continue
            if result.ok or result.error.code is not ErrorCode.UNAVAILABLE:
                return result
        return result or _failure(ErrorCode.UNAVAILABLE, 'native persistence unavailable')

    def _register_exposure(self, work, refs):
        return self._tasks.register_sources({'work_ref': work, 'refs': refs})

    def _dispatch(self, admission, context, unused, excluded_refs, excluded_steps):
        guard = getattr(self._tasks, 'startup_guard', None)
        if guard is None:
            return _failure(ErrorCode.UNAVAILABLE, 'managed native owner required')
        with ExitStack() as lifetime:
            try:
                lifetime.enter_context(guard.activity())
            except RuntimeError:
                return _failure(ErrorCode.UNAVAILABLE, 'native host ownership unavailable')
            return self._native_dispatch(admission, context)

    def _native_dispatch(self, admission, context):
        call_id = admission['call_id']
        if call_id in self._owned:
            return _failure(ErrorCode.UNAVAILABLE, 'native call remains owned')
        self._owned.add(call_id)
        request = {'call_id': call_id, 'reservation_id': admission['reservation_id'],
                   'role': 'expert', 'work_ref': admission['work_ref'],
                   'messages': [{'role': 'system', 'text': 'Return exactly one closed JSON Action. No tools.'},
                                {'role': 'user', 'text': dumps(context)}],
                   'source_refs': admission['source_refs'], 'output_kind': 'expert_action'}
        admitted = self._tasks.admit_native_call(admission, c15_request=request, profile=self._profile)
        if not admitted.ok:
            return admitted
        entered = False

        def on_enter(attempt):
            nonlocal entered
            if entered:
                raise RuntimeError('native entry already attempted')
            entered = True
            result = self._tasks.enter_native_call({'call_id': call_id, 'attempt_ref': attempt})
            if type(result) is not Result or not result.ok:
                raise RuntimeError('native entry unavailable')

        try:
            ending = self._provider.invoke(copy.deepcopy(request), on_enter=on_enter)
        except BaseException as error:
            try:
                self._tasks.mark_native_unknown({'call_id': call_id})
            except BaseException:
                pass
            if not isinstance(error, Exception):
                raise
            return _failure(ErrorCode.UNAVAILABLE, 'native outcome unknown')
        if type(ending) not in (NativeReturned, NativeNeverEntered):
            self._tasks.mark_native_unknown({'call_id': call_id})
            return _failure(ErrorCode.UNAVAILABLE, 'native ending unavailable')
        ended = self._persist(self._tasks.end_native_call, {'call_id': call_id}, ending=ending)
        if not ended.ok:
            return ended
        output = self._persist(self._tasks.get_native_output,
            {'call_id': call_id, 'lease_id': admission['lease_id'], 'work_ref': admission['work_ref']})
        if not output.ok:
            return output
        try:
            value = _value(output)
            if (set(value) != {'call_id', 'status', 'content', 'model_id'}
                    or value['call_id'] != call_id or value['status'] != 'succeeded'
                    or value['model_id'] != self._profile.model_id):
                raise ContractError()
            action = parse_model_action(value['content'], allowed_refs=_refs(admission['source_refs'])).to_json()
        except (ContractError, KeyError, TypeError):
            return _failure(ErrorCode.INVALID_INPUT, 'native action could not be adopted')
        return Result.success({'call_id': call_id, 'action': action})
