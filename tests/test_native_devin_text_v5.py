"""NATIVE-ACP01 frozen public-owner doubles; never provider/cessation proof."""
import copy
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import hashlib
import importlib
import json
import os
from pathlib import Path
import pwd
import stat
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch


def record(**kw):
    return NS(**kw)


@dataclass(frozen=True)
class AttemptRef:
    run_id: str
    job_id: str
    attempt_id: str


@dataclass(frozen=True)
class Job:
    run_id: str
    job_id: str
    instructions: str
    acceptance_criteria: tuple
    context_json: str = '{}'
    output_candidate: bool = False


@dataclass(frozen=True)
class ExecutionConditions:
    model: str
    adapter: str
    workspace: str
    environment_ref: str
    control_evidence_refs: tuple = ()


@dataclass(frozen=True)
class ExecuteRequest:
    ref: AttemptRef
    job: Job
    conditions: ExecutionConditions


class State(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    ERROR = 'error'
    WAITING_HUMAN = 'waiting_human'


class OperationStatus(str, Enum):
    ACCEPTED = 'accepted'
    UNAVAILABLE = 'unavailable'
    ERROR = 'error'
    INVALID_STATE = 'invalid_state'
    UNSUPPORTED = 'unsupported'


class StopStatus(str, Enum):
    CONFIRMED = 'confirmed'
    UNCONFIRMED = 'unconfirmed'
    REQUESTED = 'requested'
    ERROR = 'error'
    UNSUPPORTED = 'unsupported'


@dataclass(frozen=True)
class NeverStarted:
    request: ExecuteRequest
    evidence_ref: str


@dataclass(frozen=True)
class OperationReply:
    ref: AttemptRef
    status: OperationStatus
    reason: str
    resume_state: object = None
    never_started: object = None


@dataclass(frozen=True)
class StopReply:
    ref: AttemptRef
    status: StopStatus
    reason: str
    evidence_ref: object = None


@dataclass(frozen=True)
class StatusEvent:
    ref: AttemptRef
    event_id: str
    state: State
    evidence_ref: object = None


@dataclass(frozen=True)
class Result:
    ref: AttemptRef
    status: State
    reason: object = None
    detail: str = ''
    artifact_refs: tuple = ()


@dataclass(frozen=True)
class ResultEvent:
    ref: AttemptRef
    event_id: str
    result: Result


class PublicOwners:
    """Only public method shapes; logs make ordering/capacity observable."""
    def __init__(self, case):
        self.case = case
        self.log = []
        self.host = self.adapter = self.pool = None
        self.mode = 'success'
        self.chunks = ['合成', ' 日本語\nsecond line']
        self.verify_error = self.observe_error = False
        self.ending_changes = {}
        self.pin = {'route': 'devin', 'model': 'swe-2-high', 'version': '3000.11.3',
                    'cost_tier': 'Free', 'measurement_digest': 'sha256:'+'1'*64,
                    'selection_digest':'sha256:'+'5'*64,
                    'runtime_hashes': {'co_v4/adapters/devin.py': '2'*64},
                    'wrapper_sha256':'6'*64,'capture_sha256':'7'*64,'executable_sha256':'8'*64}
        owner = self
        class Config:
            def __init__(self, **kw): self.__dict__.update(kw)
        class Host:
            def __init__(self, config, *, expected_response=None):
                owner.log.append('host_ctor'); owner.host = self
                self.config = config; self.observation = {}
                case.assertIsNone(expected_response)
            def verify(self, request, phase, native):
                owner.log.append('verify:'+phase)
                if phase == 'session' and owner.verify_error:
                    raise ValueError('VERIFY_CANARY')
            def observe_model(self, fields, *, current_update=False):
                owner.log.append(('observe', fields, current_update))
                if owner.observe_error: raise ValueError('OBSERVE_CANARY')
            def transport(self, request):
                raise AssertionError('Dummy adapter must not create native transport')
            def verify_text_cessation(self, request, session, prompt_rpc, stop_reason, drain):
                owner.log.append('original_cessation')
                ending = {'attempt_ref': vars(request.ref).copy(),
                          'guarantee_model':'native_handoff_v1','capability':'devin.text.only',
                          'native_stop_reason':'end_turn','native_mode':'plan',
                          'effective_model':'swe-2-high','effective_model_verified':True,
                          'stdout_eof_validated':True,'owned_pid':12345,'owned_exit_code':-15,
                          'tool_events':0,'pending_permissions':0,
                          'session_sha256':'3'*64,'prompt_rpc_sha256':'4'*64,
                          'native_version':'3000.11.3'}
                ending.update(owner.ending_changes)
                ending['evidence_ref']='devin.acp:text-only:end_turn:'+hashlib.sha256(
                    json.dumps(ending,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                self.observation['cessation'] = ending
                return ending['evidence_ref']
        class Adapter:
            def __init__(self, **kw):
                owner.log.append('adapter_ctor'); owner.adapter = self
                self.kw = kw; self.request = None; self.pumped = False
                case.assertEqual(kw['desired_mode'], 'plan')
                case.assertEqual(kw['transport_factory'], owner.host.transport)
                case.assertEqual(kw['verify_text_cessation'], owner.host.verify_text_cessation)
            def execute(self, request):
                owner.log.append('execute'); self.request = request
                self.kw['verify_host'](request, 'launch', None)
                return OperationReply(request.ref, OperationStatus.ACCEPTED, 'fixture')
            def events(self, ref, after=None):
                if owner.mode == 'timeout': return ()
                if not self.pumped:
                    self.pumped = True
                    self.kw['observe_model']({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':'PREPROMPT'}},current_update=True)
                    self.kw['verify_host'](self.request, 'session', {'sessionId':'fixture','modes':{'currentModeId':'plan'}})
                    self.kw['observe_model']({'sessionUpdate':'agent_thought_chunk','content':{'type':'text','text':'THOUGHT'}},current_update=True)
                    for text in owner.chunks:
                        content = {'type':'text','text':text} if isinstance(text,str) else text
                        self.kw['observe_model']({'sessionUpdate':'agent_message_chunk','content':content},current_update=True)
                    if owner.mode != 'missing_ending':
                        self.kw['verify_text_cessation'](self.request,'fixture','rpc','end_turn',lambda:None)
                    return (ResultEvent(ref,'ended',Result(ref,State.COMPLETED)),)
                return ()
            def status(self, ref):
                return StatusEvent(ref,'status',State.RUNNING if owner.mode=='timeout' else State.COMPLETED)
            def stop(self, ref):
                owner.log.append('child_stop')
                e = owner.host.observation.get('cessation',{}).get('evidence_ref')
                if owner.mode=='unconfirmed' or not e: return StopReply(ref,StopStatus.UNCONFIRMED,'fixture')
                if owner.mode=='wrong_stop': e='wrong-proof'
                return StopReply(ref,StopStatus.CONFIRMED,'fixture',e)
        class Ledger:
            def __init__(self, path):
                owner.log.append('ledger_ctor'); self.path=Path(path)
                case.assertEqual(self.path, case.ledger)
                case.assertTrue(self.path.is_file())
            def release(self,*a,**kw): raise AssertionError('Wrapper must not force ledger release')
        class Pool:
            def __init__(self, adapter, *, ledger, canonical_ledger, factory):
                owner.log.append('pool_ctor'); owner.pool=self
                case.assertEqual(adapter,'devin.acp'); case.assertEqual(Path(canonical_ledger),case.ledger)
                self.factory=factory; self.child=None; self.executions=0
            def reserve(self, request): owner.log.append('reserve'); return True
            def cancel_reservation(self,request): owner.log.append('cancel_reserved'); return True
            def execute(self,request):
                self.executions+=1; case.assertEqual(self.executions,1)
                if owner.mode=='never_started':
                    owner.log.append('never_started')
                    return OperationReply(request.ref,OperationStatus.UNAVAILABLE,'fixture',never_started=NeverStarted(request,'fixture:never-started'))
                self.child=self.factory(request); return self.child.execute(request)
            def events(self,*a,**kw): return self.child.events(*a,**kw)
            def status(self,*a,**kw): return self.child.status(*a,**kw)
            def stop(self,ref):
                owner.log.append('pool_stop'); return self.child.stop(ref)
        @contextmanager
        def gate(*a,**kw):
            owner.log.append('gate_enter'); yield NS()
            owner.log.append('gate_exit')
        def check(config): owner.log.append('check_template'); return ()
        contracts=NS(**{k:globals()[k] for k in ('AttemptRef','Job','ExecutionConditions','ExecuteRequest','State','OperationStatus','StopStatus','NeverStarted','OperationReply','StopReply','StatusEvent','Result','ResultEvent')})
        self.api=NS(contracts=contracts,DevinTextHost=Host,DevinHostConfig=Config,
                    DevinAdapter=Adapter,DelegatedScope=Config,CapacityLedger=Ledger,
                    PooledAdapter=Pool,gate=gate,check_launch_template=check,
                    launch_environment=lambda:{},NativeCandidates=Config)


class NativeDevinTextTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('tools.native_devin_text_v5')
        self.values=importlib.import_module('pal.native_call_v5')
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.home=self.root/'home'; self.home.mkdir()
        private=self.home/'.co-task-host'; private.mkdir(mode=0o700)
        self.ledger=private/'capacity.db'; self.ledger.touch(mode=0o600)
        self.runtime=self.root/'runtime'; self.runtime.mkdir()
        self.state=self.root/'state'; self.state.mkdir(mode=0o700)
        self.attempt_root=self.root/'attempts'; self.attempt_root.mkdir(mode=0o700)
        self.executable=self.root/'devin'; self.executable.write_text('fixture'); self.executable.chmod(0o700)
        self.credential=self.root/'credential'; self.credential.write_text('NEVER_READ_CREDENTIAL'); self.credential.chmod(0o600)
        self.owners=PublicOwners(self)
        envelope={'version':'NATIVE-ACP01/1','profile_id':'co-devin-acp-dynamic-text/1','pin':copy.deepcopy(self.owners.pin)}
        qualified=hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        self.profile=self.values.NativeProfile(model_id='swe-2-high',qualification_sha256=qualified,evidence_kind='fixture')
        self.request={'call_id':'fixture-call','reservation_id':'fixture-reservation','role':'primary',
                      'output_kind':'primary_proposal','messages':[{'role':'user','text':'RAW_CANARY 日本語'}],
                      'source_refs':[{'kind':'record','id':'fixture-record'}]}
        self.entered=[]
        self.addCleanup(patch.stopall)
        patch.object(self.module,'_load_runtime',return_value=self.owners.api).start()
        self.fresh=patch.object(self.module,'_fresh_pin',return_value=self.owners.pin).start()
        patch.object(pwd,'getpwuid',return_value=NS(pw_dir=str(self.home))).start()
        self.provider=self.module.NativeDevinText(runtime=self.runtime,state_dir=self.state,
            attempt_root=self.attempt_root,executable=self.executable,
            credential_files=(self.credential,),profile=self.profile)
    def invoke(self,hook=None):
        return self.provider.invoke(copy.deepcopy(self.request),on_enter=hook or self.entered.append)
    def unknown(self):
        with self.assertRaises(Exception) as caught: self.invoke()
        self.assertNotIsInstance(caught.exception,self.values.NativeNeverEntered)
        self.assertLessEqual(self.owners.log.count('pool_stop'),1)
        self.assertNotIn('cancel_reserved',self.owners.log)
        self.assertLessEqual(self.owners.log.count('execute'),1)
        self.assertNotIn('RAW_CANARY',str(caught.exception))

    def test_constructor_and_preflight_generate_nothing(self):
        self.assertFalse(callable(self.provider)); result=self.provider.preflight()
        self.assertEqual(result,self.owners.pin)
        result['runtime_hashes']['co_v4/adapters/devin.py']='0'*64
        self.assertEqual(self.owners.pin['runtime_hashes']['co_v4/adapters/devin.py'],'2'*64)
        self.assertFalse(self.entered); self.assertNotIn('execute',self.owners.log)
        self.assertNotIn('reserve',self.owners.log)
        self.assertFalse(any(self.attempt_root.iterdir()))
    def test_success_original_hooks_capture_ending_and_one_execute(self):
        out=self.invoke(); self.assertIsInstance(out,self.values.NativeReturned)
        self.assertEqual(out.text,''.join(self.owners.chunks)); self.assertEqual(len(self.entered),1)
        self.assertEqual(self.owners.log.count('execute'),1)
        self.assertEqual(self.owners.log.count('pool_stop'),1)
        self.assertLess(self.owners.log.index('verify:session'),self.owners.log.index('original_cessation'))
        req=self.owners.adapter.request
        self.assertEqual(vars(req.ref),dict(self.entered[0]))
        self.assertFalse(req.job.output_candidate); self.assertEqual(req.job.context_json,'{}')
        self.assertEqual(req.conditions.model,'swe-2-high'); self.assertEqual(req.conditions.adapter,'devin.acp')
        self.assertEqual(list(Path(req.conditions.workspace).iterdir()),[])
        self.assertEqual(self.owners.host.config.delegation.capability,'devin.text.only')
        from pal.contracts_v5 import dumps
        evidence=out.validate(request_sha256=hashlib.sha256(dumps(self.request).encode()).hexdigest(),profile=self.profile)
        self.assertEqual(evidence['evidence_kind'],'fixture'); self.assertNotIn(out.text,json.dumps(evidence))
    def test_original_verifier_failure_prevents_capture_adoption(self):
        self.owners.verify_error=True; self.unknown()
        self.assertNotIn('original_cessation',self.owners.log)
    def test_original_observer_failure_prevents_capture_adoption(self):
        self.owners.observe_error=True; self.unknown()
        self.assertNotIn('original_cessation',self.owners.log)
    def test_missing_ending_never_returns_text(self):
        self.owners.mode='missing_ending'; self.unknown()
    def test_completed_unconfirmed_stop_never_adopts(self):
        self.owners.mode='unconfirmed'; self.unknown()
    def test_wrong_stop_binding_never_adopts(self):
        self.owners.mode='wrong_stop'; self.unknown()
    def test_bad_ending_eof_model_or_attempt_is_rejected(self):
        self.owners.ending_changes={'stdout_eof_validated':False}; self.unknown()
    def test_nontext_chunk_is_unknown_and_no_retry(self):
        self.owners.chunks=[{'type':'image','data':'RAW_CANARY'}]; self.unknown()
    def test_over_cap_capture_is_unknown_and_no_retry(self):
        self.owners.chunks=['x'*32769]; self.unknown()
    def test_timeout_stops_once_and_never_reexecutes_or_releases(self):
        self.owners.mode='timeout'
        ticks=iter(range(0,100000,31))
        with patch('time.monotonic',side_effect=lambda:next(ticks)), patch('time.sleep'):
            self.unknown()
        self.assertEqual(self.owners.log.count('execute'),1)
        self.assertEqual(self.owners.log.count('pool_stop'),1)
    def test_known_exact_never_started_is_typed(self):
        self.owners.mode='never_started'
        with self.assertRaises(self.values.NativeNeverEntered): self.invoke()
        self.assertEqual(len(self.entered),1); self.assertNotIn('execute',self.owners.log)
    def test_on_enter_failure_never_executes(self):
        def fail(attempt): self.entered.append(attempt); raise RuntimeError('HOOK_CANARY')
        with self.assertRaises(Exception): self.invoke(fail)
        self.assertEqual(len(self.entered),1); self.assertNotIn('execute',self.owners.log)
    def test_fsync_failure_never_executes(self):
        with patch.object(os,'fsync',side_effect=OSError('FSYNC_CANARY')):
            with self.assertRaises(Exception): self.invoke()
        self.assertNotIn('execute',self.owners.log)
    def test_existing_ledger_required_before_constructor(self):
        self.ledger.unlink()
        with self.assertRaises(Exception): self.provider.preflight()
        self.assertNotIn('ledger_ctor',self.owners.log)
        self.assertFalse(self.ledger.exists())
    def test_private_artifacts_and_same_call_never_reenter(self):
        self.invoke(); before=self.owners.log.count('execute')
        for path in self.attempt_root.rglob('*'):
            if path.is_file(): self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            elif path.is_dir(): self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o700)
        with self.assertRaises(Exception): self.invoke()
        self.assertEqual(self.owners.log.count('execute'),before)

    def test_known_ending_persistence_failure_is_unknown_without_second_execute(self):
        original=os.fsync
        def fail_after_ending(fd):
            if 'original_cessation' in self.owners.log: raise OSError('TERMINAL_FSYNC_CANARY')
            return original(fd)
        with patch.object(os,'fsync',side_effect=fail_after_ending): self.unknown()
        self.assertEqual(self.owners.log.count('execute'),1)

    def test_changed_current_pin_refuses_before_reserve_and_entry(self):
        self.owners.pin['executable_sha256']='9'*64
        with self.assertRaises(Exception): self.provider.preflight()
        self.assertNotIn('reserve',self.owners.log); self.assertNotIn('execute',self.owners.log)
        self.assertFalse(self.entered)

    def test_malformed_pin_refuses_without_native_io(self):
        self.owners.pin['runtime_hashes']={}
        with self.assertRaises(Exception): self.provider.preflight()
        self.assertNotIn('execute',self.owners.log); self.assertFalse(self.entered)
