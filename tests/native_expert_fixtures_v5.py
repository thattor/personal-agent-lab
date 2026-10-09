"""Actual managed temporary owners and local typed native ending fixtures."""
import copy
import hashlib
import json
from pal.contracts_v5 import dumps, Limits
from pal.native_call_v5 import NativeProfile, NativeReturned
from pal.native_text_v5 import NativeTextBuffer
import test_tasks_recovery_v5 as managed


class NativeFixture:
    def __init__(self,case):
        self.case=case;self.f=managed.RecoveryTests(methodName='runTest');self.f.setUp()
        case.addCleanup(self.f.doCleanups)
        self.profile=NativeProfile(model_id='swe-2-high',qualification_sha256='2'*64,evidence_kind='fixture')
        self.attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'fixture-attempt'}
        self.action={'kind':'report','summary':'RAW_NATIVE_CANARY 日本語'}
    @property
    def t(self):return self.f.t
    @property
    def work(self):return copy.deepcopy(self.f.lease['work_ref'])
    def prepare(self,refs=None):
        refs=copy.deepcopy(refs if refs is not None else [self.f.origin,self.f.optional])
        self.f.value(self.t.register_sources({'work_ref':self.work,'refs':refs}))
        context=self.f.value(self.t.get_execution_context({'lease_id':self.f.lease['lease_id'],'work_ref':self.work}))
        reservation=self.f.value(self.t.reserve_budget({'key':self.f.key(),'work_ref':self.work,'kind':'model','role':'expert'}))
        self.admission={'call_id':dumps(['C15.call',self.f.lease['lease_id'],context['next_step_index']]),
                        'lease_id':self.f.lease['lease_id'],'work_ref':self.work,
                        'reservation_id':reservation['reservation_id'],'source_refs':refs}
        self.request={'call_id':self.admission['call_id'],'reservation_id':reservation['reservation_id'],
                      'role':'expert','work_ref':self.work,'output_kind':'expert_action',
                      'messages':[{'role':'system','text':'Fixture Action only'},
                                  {'role':'user','text':dumps({'fixture':'full supplied closure'})}],
                      'source_refs':copy.deepcopy(refs)}
        return self.admission
    @property
    def call_id(self):return self.admission['call_id']
    def admit(self):
        if not hasattr(self,'admission'):self.prepare()
        return self.t.admit_native_call(copy.deepcopy(self.admission),c15_request=copy.deepcopy(self.request),profile=self.profile)
    def enter(self):return self.t.enter_native_call({'call_id':self.call_id,'attempt_ref':copy.deepcopy(self.attempt)})
    def returned(self,*,text=None,request=None,profile=None,attempt=None,extra=None):
        request=self.request if request is None else request;profile=self.profile if profile is None else profile
        attempt=copy.deepcopy(self.attempt if attempt is None else attempt)
        text=dumps(self.action) if text is None else text
        ending={'attempt_ref':attempt,'guarantee_model':'native_handoff_v1','capability':'devin.text.only',
                'native_stop_reason':'end_turn','native_mode':'plan','effective_model':'swe-2-high',
                'effective_model_verified':True,'stdout_eof_validated':True,'owned_pid':123,'owned_exit_code':-15,
                'tool_events':0,'pending_permissions':0,'session_sha256':'3'*64,'prompt_rpc_sha256':'4'*64}
        if extra:ending.update(extra)
        ending['evidence_ref']='devin.acp:text-only:end_turn:'+hashlib.sha256(
            json.dumps(ending,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        buffer=NativeTextBuffer(request_sha256=hashlib.sha256(dumps(request).encode()).hexdigest(),
            profile_sha256=profile.profile_sha256,attempt_ref=attempt,model_id='swe-2-high')
        buffer.begin();buffer.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text}})
        return NativeReturned(capture=buffer.finish(ending),cessation=ending)
    def end(self,ending=None):return self.t.end_native_call({'call_id':self.call_id},ending=self.returned() if ending is None else ending)
    def output(self):return self.t.get_native_output({'call_id':self.call_id,'lease_id':self.f.lease['lease_id'],'work_ref':self.work})
    def begin(self,action=None):return self.t.begin_step({'key':self.f.key(),'work_ref':self.work,'action':self.action if action is None else action})
    def control(self,command):return self.t.control({'key':self.f.key(),'work_ref':self.work,'command':command})
    def stop(self,ref=None):return self.f.mem.stop_reference({'key':self.f.key(),'source_ref':self.f.optional if ref is None else ref},session_id='session')
    def release(self,outcome='yield'):return self.t.release({'lease_id':self.f.lease['lease_id'],'work_ref':self.work,'outcome':outcome,'reason':'fixture release'})

    def connect_owned(self):
        import sqlite3
        from pal.tasks_v5 import TaskStore
        from pal.memory_v5 import MemoryStore
        from pal.artifacts_v5 import ArtifactStore
        from pal.verification_v5 import VerificationStore
        conn=sqlite3.connect(self.f.path,isolation_level=None,timeout=0,check_same_thread=False)
        tasks=TaskStore(conn,startup_guard=self.f.guard,host_grant=self.f.grant,
            host_limits=Limits(0,100,100),expert_id='expert',
            source_gate=lambda c,r:memory.source_gate(c,r),artifact_inspect=lambda c,r:art.inspect(c,r),
            verification_inspect=lambda c,r:ver.inspect(c,r))
        memory=MemoryStore(conn,sanitize_text=lambda x:x,append_event=tasks.append_event,invalidate_by_refs=tasks.invalidate_by_refs)
        art=ArtifactStore(conn,authorize_save=tasks.authorize_artifact_save,source_gate=memory.source_gate)
        ver=VerificationStore(conn,context=tasks.verification_context,artifact_inspect=art.inspect,source_gate=memory.source_gate)
        return conn,tasks,memory,art,ver
