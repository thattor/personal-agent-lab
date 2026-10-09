"""PRI03 native runner fixed tests: actual fresh owners, fixture provider only."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, Result, dumps, loads
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockInvoker, MockRunner
from pal.native_call_v5 import NativeProfile, NativeReturned
from pal.native_text_v5 import NativeTextBuffer
from pal.read_consumer_v5 import inspect_session
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


class TaskBoundary:
    """Logs public orchestration only; owner still performs every mutation."""
    def __init__(self,owner):self.owner=owner;self.log=[];self.reservations=[]
    def __getattr__(self,name):
        method=getattr(self.owner,name)
        if not callable(method):return method
        def call(*args,**kwargs):
            self.log.append(name)
            if name=='reserve_budget':self.reservations.append(copy.deepcopy(args[0]))
            return method(*args,**kwargs)
        return call


class FixtureProvider:
    def __init__(self,case):
        self.case=case;self.profile=NativeProfile(model_id='swe-2-high',qualification_sha256='2'*64,evidence_kind='fixture')
        self.requests=[];self.contexts=[];self.preflight_error=None;self.behavior=None;self.action=None
    def preflight(self):
        self.case.assertFalse(self.case.conn.in_transaction)
        self.case.boundary.log.append('preflight')
        if self.preflight_error:raise self.preflight_error
    def invoke(self,request,*,on_enter):
        case=self.case;case.assertFalse(case.conn.in_transaction)
        case.assertEqual(set(request),{'call_id','reservation_id','role','work_ref','messages','source_refs','output_kind'})
        case.assertEqual((request['role'],request['output_kind']),('expert','expert_action'))
        case.assertTrue(all(set(m)=={'role','text'} for m in request['messages']))
        user=[m for m in request['messages'] if m['role']=='user'];case.assertEqual(len(user),1)
        context=loads(user[0]['text']);self.contexts.append(context)
        case.assertTrue({'work_ref','brief','grant_summary','context','steps','remaining_budget'}<=set(context))
        case.assertEqual(context['work_ref'],request['work_ref'])
        case.assertTrue(all(r['kind']=='record' for r in request['source_refs']))
        case.assertLessEqual(len(dumps(request).encode()),65536)
        self.requests.append(copy.deepcopy(request))
        if self.behavior:return self.behavior(request,on_enter)
        attempt={'run_id':'fixture-run','job_id':'expert','attempt_id':'fixture-'+str(len(self.requests))}
        on_enter(attempt)
        action=self.action or {'kind':'compose','content':'保存した合成下書き','media_type':'text/plain','source_refs':request['source_refs']}
        return self.ending(request,attempt,dumps(action))
    def ending(self,request,attempt,text):
        ending={'attempt_ref':copy.deepcopy(attempt),'guarantee_model':'native_handoff_v1','capability':'devin.text.only',
            'native_stop_reason':'end_turn','native_mode':'plan','effective_model':'swe-2-high','effective_model_verified':True,
            'stdout_eof_validated':True,'owned_pid':123,'owned_exit_code':-15,'tool_events':0,'pending_permissions':0,
            'session_sha256':'3'*64,'prompt_rpc_sha256':'4'*64}
        raw=json.dumps(ending,sort_keys=True,separators=(',',':'),allow_nan=False)
        ending['evidence_ref']='devin.acp:text-only:end_turn:'+hashlib.sha256(raw.encode()).hexdigest()
        buffer=NativeTextBuffer(request_sha256=hashlib.sha256(dumps(request).encode()).hexdigest(),
            profile_sha256=self.profile.profile_sha256,attempt_ref=attempt,model_id='swe-2-high')
        buffer.begin();buffer.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text}})
        return NativeReturned(capture=buffer.finish(ending),cessation=ending)


class NativeExpertRunnerTests(unittest.TestCase):
    def setUp(self):
        self.Runner=importlib.import_module('pal.native_expert_runner_v5').NativeExpertRunner
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'work.sqlite';self.serial=0
        self.guard=MockHostSession.open(self.path);self.addCleanup(self.guard.close)
        self.conn=sqlite3.connect(self.path,isolation_level=None,timeout=0);self.addCleanup(self.conn.close)
        self.grant=Grant((),('repo',),Limits(0,8,8))
        self.tasks=TaskStore(self.conn,startup_guard=self.guard,host_grant=self.grant,host_limits=Limits(0,40,40),
            expert_id='expert',source_gate=lambda c,r:self.mem.source_gate(c,r),
            artifact_inspect=lambda c,r:self.art.inspect(c,r),verification_inspect=lambda c,r:self.ver.inspect(c,r),
            artifact_lookup=lambda c,r:self.art.lookup_saved(c,r))
        self.mem=MemoryStore(self.conn,sanitize_text=sanitize,append_event=self.tasks.append_event,invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art=ArtifactStore(self.conn,authorize_save=self.tasks.authorize_artifact_save,source_gate=self.mem.source_gate)
        self.ver=VerificationStore(self.conn,context=self.tasks.verification_context,artifact_inspect=self.art.inspect,source_gate=self.mem.source_gate)
        self.ok(self.tasks.register_host());self.ok(self.tasks.finish_startup())
        self.origin=self.record('依頼');self.optional=self.record('追加資料')
        brief={'purpose':'draft','target':{'repository':'repo','issue_numbers':[],'files':[]},'constraints':[],
            'conditions':[{'description':'saved','check':'artifact_saved'}],'context_refs':[self.optional]}
        self.work=self.ok(self.tasks.create({'key':self.key(),'session_id':'session','origin_record_ref':self.origin,
            'brief':brief},request_scope=self.grant))['work_ref']
        self.boundary=TaskBoundary(self.tasks);self.provider=FixtureProvider(self)
        self.runner=self.Runner(self.boundary,self.mem,provider=self.provider,artifacts=self.art,verifier=self.ver)
    def key(self):self.serial+=1;return 'key-'+str(self.serial)
    def ok(self,result):
        self.assertIs(type(result),Result);self.assertTrue(result.ok,result.to_json());return result.value.to_json()
    def record(self,text):return self.ok(self.mem.append({'client_key':self.key(),'session_id':'session','role':'user','text':text}))['record_ref']
    def current(self):return self.ok(self.tasks.get_work({'goal_id':self.work['goal_id']}))
    def execute(self):
        result=self.runner.execute_next();self.assertIs(type(result),Result);return result
    def call(self):return self.ok(self.tasks.get_call({'call_id':self.provider.requests[-1]['call_id']}))
    def no_effects(self):self.assertEqual(self.current()['current_artifact_refs'],[])
    def control(self,command):
        with sqlite3.connect(self.path,isolation_level=None,timeout=0) as conn:
            owner=TaskStore(conn,startup_guard=self.guard,host_grant=self.grant,host_limits=Limits(0,40,40),expert_id='expert',
                source_gate=lambda c,r:self.mem.source_gate(c,r))
            result=self.ok(owner.control({'key':self.key(),'work_ref':self.current()['work_ref'],'command':command}))
        conn.close();return result
    def stop(self):return self.ok(self.mem.stop_reference({'key':self.key(),'source_ref':self.origin},session_id='session'))

    def test_explicit_provider_and_no_native_under_mock_entry(self):
        self.assertFalse(callable(self.provider))
        with self.assertRaises(TypeError):self.runner.execute_next(lambda:None)
        result=MockRunner(self.tasks,self.mem,artifacts=self.art).run_once(self.provider)
        self.assertFalse(result.ok);self.assertEqual(self.provider.requests,[])
        result=MockInvoker().invoke(self.tasks,{'call_id':'not-admitted'},self.provider)
        self.assertFalse(result.ok);self.assertEqual(self.provider.requests,[])

    def test_preflight_failure_precedes_model_reservation_and_entry(self):
        self.provider.preflight_error=RuntimeError('PRIVATE_CANARY')
        result=self.execute();self.assertFalse(result.ok)
        self.assertIn(result.error.code.value,('denied','unavailable'))
        self.assertEqual(self.current()['state'],'queued')
        self.assertEqual(self.boundary.reservations,[]);self.assertEqual(self.provider.requests,[])
        self.no_effects();self.assertNotIn('PRIVATE_CANARY',dumps(result))

    def test_exact_exposed_sources_and_owner_output_read_before_action_effect(self):
        self.ok(self.execute())
        request=self.provider.requests[0]
        self.assertEqual(request['source_refs'],[self.origin,self.optional])
        log=self.boundary.log
        self.assertLess(log.index('preflight'),log.index('reserve_budget'))
        self.assertLess(log.index('end_native_call'),log.index('get_native_output'))
        self.assertLess(log.index('get_native_output'),log.index('begin_step'))
        self.assertEqual(sum(r['kind']=='model' for r in self.boundary.reservations),1)
        self.assertEqual(len(self.provider.requests),1)
        self.assertEqual(self.call()['native_phase'],'returned')
        self.assertEqual(self.call()['profile_id'],self.provider.profile.id)

    def test_generic_provider_failure_keeps_unknown_lease_and_controls_usable(self):
        def failure(request,hook):
            hook({'run_id':'fixture-run','job_id':'expert','attempt_id':'unknown'})
            raise RuntimeError('PRIVATE_CANARY')
        self.provider.behavior=failure;result=self.execute()
        self.assertNotIn('PRIVATE_CANARY',dumps(result));self.no_effects()
        self.assertEqual((self.call()['status'],self.call()['native_phase']),('admitted','unknown'))
        paused=self.control('pause');self.assertEqual(paused['control_status'],'pause_requested')
        self.execute();self.assertEqual(len(self.provider.requests),1)
        self.assertEqual(sum(r['kind']=='model' for r in self.boundary.reservations),1)
        self.assertEqual(self.call()['status'],'admitted')

    def test_foreign_attempt_ending_has_no_step_or_artifact_effect(self):
        def foreign(request,hook):
            hook({'run_id':'fixture-run','job_id':'expert','attempt_id':'original'})
            return self.provider.ending(request,{'run_id':'fixture-run','job_id':'expert','attempt_id':'foreign'},
                dumps({'kind':'report','summary':'not adoptable','source_refs':request['source_refs']}))
        self.provider.behavior=foreign;self.execute();self.no_effects()
        self.assertNotIn('begin_step',self.boundary.log);self.assertEqual(self.call()['status'],'admitted')
        self.execute();self.assertEqual(len(self.provider.requests),1)

    def test_known_return_after_pause_is_recorded_but_not_adopted(self):
        def pause(request,hook):
            attempt={'run_id':'fixture-run','job_id':'expert','attempt_id':'pause'};hook(attempt)
            returned=self.provider.ending(request,attempt,dumps({'kind':'compose','content':'draft','media_type':'text/plain','source_refs':request['source_refs']}))
            self.control('pause');return returned
        self.provider.behavior=pause;self.execute();self.no_effects()
        self.assertEqual(self.call()['status'],'returned');self.assertEqual(self.current()['state'],'paused')
        self.assertNotIn('begin_step',self.boundary.log);self.assertEqual(len(self.provider.requests),1)

    def test_known_return_after_source_stop_is_stored_without_body_adoption(self):
        def stop(request,hook):
            attempt={'run_id':'fixture-run','job_id':'expert','attempt_id':'stop'};hook(attempt)
            returned=self.provider.ending(request,attempt,dumps({'kind':'compose','content':'draft','media_type':'text/plain','source_refs':request['source_refs']}))
            self.stop();return returned
        self.provider.behavior=stop;self.execute();self.no_effects()
        self.assertEqual(self.call()['status'],'returned');self.assertNotIn('begin_step',self.boundary.log)
        self.assertEqual(len(self.provider.requests),1)

    def test_compose_attach_fresh_structural_verify_complete_and_user_readback(self):
        self.ok(self.execute());current=self.current();self.assertEqual(current['state'],'completed')
        self.assertEqual(len(current['current_artifact_refs']),1)
        artifact=self.ok(self.art.read({'ref':current['current_artifact_refs'][0]},purpose='user_view'))
        self.assertEqual(artifact['content'],'保存した合成下書き')
        self.assertEqual(artifact['hash'],hashlib.sha256(artifact['content'].encode()).hexdigest())
        view=self.ok(inspect_session({'session_id':'session'},events=EventReader(self.conn),tasks=self.tasks,
            reader=HostReader(self.mem,self.art,self.ver)))
        self.assertTrue(view['items']);self.assertEqual(self.provider.profile.evidence_kind,'fixture')
        self.execute();self.assertEqual(len(self.provider.requests),1)

    def test_ask_answer_link_full_exposure_then_one_fresh_compose(self):
        self.provider.action={'kind':'ask','question':'日時は？','missing_fact':'date','source_refs':[self.origin]}
        self.ok(self.execute());waiting=self.current();self.assertEqual(waiting['state'],'waiting_input')
        question=waiting['open_questions'][0];answer=self.record('10月12日')
        self.ok(self.tasks.control({'key':self.key(),'work_ref':waiting['work_ref'],'command':{'kind':'answer',
            'question_id':question['id'],'answer_record_ref':answer}}))
        self.provider.action=None;self.ok(self.execute())
        context=self.provider.contexts[-1];self.assertTrue(context['pending_inputs'])
        self.assertEqual(context['pending_inputs'][0]['answer_record_ref'],answer)
        self.assertIn(answer,self.provider.requests[-1]['source_refs'])
        self.assertIn(self.origin,self.provider.requests[-1]['source_refs'])
        self.assertEqual(self.current()['state'],'completed');self.assertEqual(len(self.provider.requests),2)

    def test_known_ended_malformed_action_never_repair_infers(self):
        def malformed(request,hook):
            attempt={'run_id':'fixture-run','job_id':'expert','attempt_id':'malformed'};hook(attempt)
            return self.provider.ending(request,attempt,'{"kind":"compose","grant":true}')
        self.provider.behavior=malformed;self.execute();self.no_effects()
        self.assertEqual(self.call()['status'],'returned');self.assertNotIn('begin_step',self.boundary.log)
        self.execute();self.assertEqual(len(self.provider.requests),1)


if __name__=='__main__':unittest.main()
