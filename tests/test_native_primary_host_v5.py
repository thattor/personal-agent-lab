"""Native Primary lifetime with actual temporary owners and fixture endings only."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, Result, dumps, loads
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.native_text_v5 import NativeTextBuffer
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


class Provider:
    """Non-callable synthetic provider; cannot acquire native authority."""
    def __init__(self, owner):
        self.owner = owner
        self.profile = owner.native.NativeProfile(model_id='swe-2-high',
            qualification_sha256='2'*64,evidence_kind='fixture')
        self.calls=[]; self.preflights=0; self.behavior=None; self.preflight_error=None; self.proposal={'kind':'none'}
    def preflight(self):
        self.preflights+=1
        self.owner.assertFalse(self.owner.conn.in_transaction)
        if self.preflight_error:raise self.preflight_error
    def invoke(self, request, *, on_enter):
        self.owner.assertFalse(self.owner.conn.in_transaction)
        self.calls.append(copy.deepcopy(request))
        if self.behavior:return self.behavior(request,on_enter)
        attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'fixture-'+str(len(self.calls))}
        on_enter(attempt)
        return self.returned(request,attempt)
    def returned(self,request,attempt):
        text=dumps({'reply':'fixture reply','proposal':self.proposal})
        cessation={'attempt_ref':copy.deepcopy(attempt),'guarantee_model':'native_handoff_v1',
            'capability':'devin.text.only','native_stop_reason':'end_turn','native_mode':'plan',
            'effective_model':'swe-2-high','effective_model_verified':True,'stdout_eof_validated':True,
            'owned_pid':123,'owned_exit_code':-15,'tool_events':0,'pending_permissions':0,
            'session_sha256':'3'*64,'prompt_rpc_sha256':'4'*64}
        raw=json.dumps(cessation,sort_keys=True,separators=(',',':'),allow_nan=False)
        cessation['evidence_ref']='devin.acp:text-only:end_turn:'+hashlib.sha256(raw.encode()).hexdigest()
        buffer=NativeTextBuffer(request_sha256=self.request_hash(request),profile_sha256=self.profile.profile_sha256,
            attempt_ref=attempt,model_id='swe-2-high')
        buffer.begin();buffer.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text}})
        return self.owner.native.NativeReturned(capture=buffer.finish(cessation),cessation=cessation)
    @staticmethod
    def request_hash(request):return hashlib.sha256(dumps(request).encode()).hexdigest()


class NativePrimaryTests(unittest.TestCase):
    def setUp(self):
        self.native=importlib.import_module('pal.native_call_v5')
        self.Host=importlib.import_module('pal.primary_host_v5').NativePrimaryHost
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'work.sqlite';self.serial=0
        self.grant=Grant((),('repo',),Limits(0,20,20))
        self.connect(True);self.provider=Provider(self);self.host=self.make_host()
    def connect(self,ready):
        self.guard=MockHostSession.open(self.path)
        self.addCleanup(lambda g=self.guard:g.close() if g.phase!='closed' else None)
        self.conn=sqlite3.connect(self.path,isolation_level=None,timeout=0)
        self.addCleanup(self.conn.close)
        self.tasks=TaskStore(self.conn,startup_guard=self.guard,host_grant=self.grant,
            host_limits=Limits(0,100,100),expert_id='expert',source_gate=lambda c,r:self.mem.source_gate(c,r),
            artifact_inspect=lambda c,r:self.art.inspect(c,r),verification_inspect=lambda c,r:self.ver.inspect(c,r),
            artifact_lookup=lambda c,r:self.art.lookup_saved(c,r))
        self.mem=MemoryStore(self.conn,sanitize_text=sanitize,append_event=self.tasks.append_event,
            invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art=ArtifactStore(self.conn,authorize_save=self.tasks.authorize_artifact_save,source_gate=self.mem.source_gate)
        self.ver=VerificationStore(self.conn,context=self.tasks.verification_context,
            artifact_inspect=self.art.inspect,source_gate=self.mem.source_gate)
        self.ok(self.tasks.register_host())
        if ready:self.ok(self.tasks.finish_startup())
    def make_host(self):return self.Host(self.conn,guard=self.guard,memory=self.mem,tasks=self.tasks,
        request_scope=self.grant,provider=self.provider)
    def ok(self,result):
        self.assertIs(type(result),Result);self.assertTrue(result.ok,result.to_json());return result.value.to_json()
    def key(self):self.serial+=1;return 'key-'+str(self.serial)
    def submit(self):return self.ok(self.host.submit({'client_key':self.key(),'session_id':'session','text':'合成依頼'}))['turn_id']
    def run_turn(self,turn):return self.ok(self.host.run_turn({'turn_id':turn}))
    def used(self):return self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0]
    def get(self,turn):return self.ok(self.host.get_turn({'turn_id':turn}))
    def held(self,result):
        self.assertEqual(result,{'status':'held','effect_refs':[]})
        self.assertNotIn('SECRET_CANARY',dumps(result))
    def side(self):return self.conn.execute('SELECT * FROM v5_pri_native').fetchall()
    def snapshot(self):return tuple(self.conn.iterdump())
    def unknown(self,request,hook):
        hook({'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'fixture-unknown'})
        raise RuntimeError('SECRET_CANARY')
    def restart(self):
        self.conn.close();self.guard.close();self.connect(False);self.host=self.make_host()

    def test_noncallable_native_object_refused_by_mock_constructor(self):
        Mock=importlib.import_module('pal.primary_host_v5').PrimaryHost
        before=self.used()
        with self.assertRaises((ValueError,RuntimeError,TypeError)):
            Mock(self.conn,guard=self.guard,memory=self.mem,tasks=self.tasks,request_scope=self.grant,
                 invoke=self.provider,model_id='swe-2-high')
        self.assertEqual(self.used(),before);self.assertEqual(self.provider.calls,[])

    def test_preflight_failure_before_reservation_has_no_charge(self):
        turn=self.submit();before=self.used();self.provider.preflight_error=RuntimeError('SECRET_CANARY')
        result=self.run_turn(turn)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['effect_refs'],[])
        self.assertEqual(self.used(),before);self.assertEqual(self.provider.calls,[])

    def test_valid_fixture_ending_terminal_once_and_one_charge(self):
        turn=self.submit();before=self.used();result=self.run_turn(turn)
        self.assertEqual(result,{'status':'committed','effect_refs':[],'reply':'fixture reply'})
        self.assertEqual(self.used(),before+1);self.assertEqual(len(self.provider.calls),1)
        self.assertEqual(self.run_turn(turn),result);self.assertEqual(len(self.provider.calls),1)
        side=self.conn.execute('SELECT profile_json,phase,ending_json FROM v5_pri_native').fetchone()
        self.assertEqual(loads(side[0])['evidence_kind'],'fixture');self.assertEqual(side[1],'returned')
        self.assertNotIn('fixture reply',side[2]);self.assertEqual(loads(side[2])['evidence_kind'],'fixture')

    def test_return_without_entry_hook_is_held_not_adopted(self):
        self.provider.behavior=lambda r,h:self.provider.returned(r,{'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'unentered'})
        turn=self.submit();self.held(self.run_turn(turn));self.assertEqual(self.used(),1)
        self.held(self.run_turn(turn));self.assertEqual(len(self.provider.calls),1)

    def test_generic_failure_is_held_and_same_turn_readonly_no_retry(self):
        self.provider.behavior=self.unknown;turn=self.submit();self.held(self.run_turn(turn))
        saved=self.snapshot();before=self.used();self.held(self.run_turn(turn))
        self.assertEqual(self.snapshot(),saved);self.assertEqual(self.used(),before)
        self.assertEqual(len(self.provider.calls),1)

    def test_distinct_explicit_turn_progresses_while_original_is_held(self):
        self.provider.behavior=self.unknown;old=self.submit();self.held(self.run_turn(old))
        self.provider.behavior=None;new=self.submit();self.assertEqual(self.run_turn(new)['status'],'committed')
        self.held(self.get(old));self.assertEqual(self.used(),2);self.assertEqual(len(self.provider.calls),2)

    def test_matching_never_entered_settles_without_refund(self):
        def refused(request,hook):
            raise self.native.NativeNeverEntered(request_sha256=self.provider.request_hash(request),
                profile_sha256=self.provider.profile.profile_sha256,evidence_ref='fixture:never-entered')
        self.provider.behavior=refused;turn=self.submit();result=self.run_turn(turn)
        self.assertEqual(result['status'],'failed');self.assertEqual(self.used(),1)
        side=self.conn.execute('SELECT phase,ending_json FROM v5_pri_native').fetchone()
        self.assertEqual(side[0],'not_entered');self.assertEqual(loads(side[1])['kind'],'not_entered')
        self.run_turn(turn);self.assertEqual(len(self.provider.calls),1)

    def test_wrong_never_entered_binding_stays_held(self):
        def refused(request,hook):
            raise self.native.NativeNeverEntered(request_sha256='0'*64,
                profile_sha256=self.provider.profile.profile_sha256,evidence_ref='fixture:wrong')
        self.provider.behavior=refused;turn=self.submit();self.held(self.run_turn(turn))
        self.held(self.run_turn(turn));self.assertEqual(len(self.provider.calls),1)

    def test_duplicate_entry_hook_cannot_release_a_returned_value(self):
        def duplicate(request,hook):
            attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'duplicate'}
            hook(attempt)
            try:hook(attempt)
            except Exception:pass
            return self.provider.returned(request,attempt)
        self.provider.behavior=duplicate;turn=self.submit();self.held(self.run_turn(turn))
        self.assertEqual(len(self.provider.calls),1)

    def test_side_deletion_or_tamper_fails_closed_without_reentry(self):
        turn=self.submit();self.provider.behavior=self.unknown;self.held(self.run_turn(turn))
        original=self.conn.execute('SELECT request_hash FROM v5_pri_native').fetchone()[0]
        for mutation in ("UPDATE v5_pri_native SET request_hash='broken'", "DELETE FROM v5_pri_native"):
            self.conn.execute(mutation)
            result=self.host.run_turn({'turn_id':turn})
            self.assertFalse(result.ok);self.assertEqual(result.error.code.value,'unavailable')
            self.assertEqual(len(self.provider.calls),1)
            if mutation.startswith('UPDATE'):
                self.conn.execute('UPDATE v5_pri_native SET request_hash=?',(original,))

    def test_source_stop_before_hook_suppresses_entry_and_adoption(self):
        entered=[]
        def stopped(request,hook):
            self.ok(self.mem.stop_reference({'key':self.key(),'source_ref':request['source_refs'][0]},session_id='session'))
            hook({'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'stopped'})
            entered.append(1)
            return self.provider.returned(request,{'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'stopped'})
        self.provider.behavior=stopped;turn=self.submit();result=self.run_turn(turn)
        self.assertIn(result['status'],('failed','held'));self.assertEqual(result['effect_refs'],[])
        self.assertNotIn('reply',result);self.assertEqual(entered,[])

    def test_source_stop_after_known_return_suppresses_reply(self):
        def stopped(request,hook):
            attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'stopped-return'}
            hook(attempt);returned=self.provider.returned(request,attempt)
            self.ok(self.mem.stop_reference({'key':self.key(),'source_ref':request['source_refs'][0]},session_id='session'))
            return returned
        self.provider.behavior=stopped;turn=self.submit();result=self.run_turn(turn)
        self.assertEqual(result['status'],'failed');self.assertNotIn('reply',result)
        self.assertEqual(result['effect_refs'],[])

    def test_separate_connection_control_remains_responsive_during_invoke(self):
        origin=self.ok(self.mem.append({'client_key':self.key(),'session_id':'session','role':'user','text':'origin'}))['record_ref']
        brief={'purpose':'draft','target':{'repository':'repo','issue_numbers':[],'files':[]},'constraints':[],
               'conditions':[{'description':'saved','check':'artifact_saved'}],'context_refs':[]}
        work=self.ok(self.tasks.create({'key':self.key(),'session_id':'session','origin_record_ref':origin,'brief':brief},request_scope=self.grant))['work_ref']
        def controlled(request,hook):
            conn=sqlite3.connect(self.path,isolation_level=None,timeout=0)
            self.addCleanup(conn.close)
            with conn:
                tasks=TaskStore(conn,startup_guard=self.guard,host_grant=self.grant,host_limits=Limits(0,100,100),expert_id='expert')
                out=self.ok(tasks.control({'key':self.key(),'work_ref':work,'command':'pause'}))
                self.assertEqual(out['state'],'paused')
            attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'control'}
            hook(attempt);return self.provider.returned(request,attempt)
        self.provider.behavior=controlled;turn=self.submit();self.assertEqual(self.run_turn(turn)['status'],'committed')

    def test_startup_native_unknown_is_held_never_mock_interrupted(self):
        self.provider.behavior=self.unknown;turn=self.submit();self.held(self.run_turn(turn));before=self.used()
        self.restart();self.ok(self.host.recover_turns());self.ok(self.tasks.finish_startup())
        self.held(self.get(turn));self.held(self.run_turn(turn))
        self.assertEqual(self.used(),before);self.assertEqual(len(self.provider.calls),1)

    def test_ending_transaction_failure_never_commits_returned_side(self):
        def fault(request,hook):
            attempt={'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'ending-fault'}
            hook(attempt)
            self.conn.execute("CREATE TEMP TRIGGER block_native_ending BEFORE UPDATE ON v5_pri_native WHEN NEW.phase='returned' BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
            return self.provider.returned(request,attempt)
        self.provider.behavior=fault;turn=self.submit();result=self.host.run_turn({'turn_id':turn})
        if result.ok:self.assertIn(result.value.to_json()['status'],('held','pending'))
        else:self.assertEqual(result.error.code.value,'unavailable')
        self.assertFalse(self.conn.in_transaction)
        row=self.conn.execute('SELECT phase,ending_json FROM v5_pri_native').fetchone()
        self.assertNotEqual(row[0],'returned');self.assertIsNone(row[1])
        self.assertEqual(len(self.provider.calls),1);self.assertEqual(self.used(),1)

    def test_unknown_owner_lookup_retains_applying_without_redispatch(self):
        self.provider.proposal={'kind':'new_work','brief':{'purpose':'draft',
            'target':{'repository':'repo','issue_numbers':[],'files':[]},'constraints':[],
            'conditions':[{'description':'saved','check':'artifact_saved'}],'context_refs':[]}}
        dispatched=[]
        def uncertain(*args,**kwargs):
            dispatched.append(1);return Result.failure('unavailable','owner unavailable')
        self.tasks.create=uncertain
        turn=self.submit();self.assertEqual(self.run_turn(turn)['status'],'pending')
        self.restart();self.tasks.get_create_by_key=lambda req:Result.failure('unavailable','owner unavailable')
        recovery=self.ok(self.host.recover_turns());self.assertIn(turn,recovery['held_turn_ids'])
        self.assertEqual(len(dispatched),1);self.assertEqual(len(self.provider.calls),1)
        self.assertNotIn('reply',self.get(turn))

    def test_returned_before_intent_startup_fails_local_adoption_preserves_ending(self):
        from unittest.mock import patch
        with patch('pal.primary_host_v5.parse_primary_output',side_effect=KeyboardInterrupt('fixture interruption')):
            turn=self.submit()
            with self.assertRaises(KeyboardInterrupt):self.host.run_turn({'turn_id':turn})
        self.assertEqual(self.conn.execute('SELECT phase FROM v5_pri_native').fetchone()[0],'returned')
        self.restart();self.ok(self.host.recover_turns())
        result=self.get(turn);self.assertEqual(result['status'],'failed');self.assertNotIn('reply',result)
        self.assertEqual(self.conn.execute('SELECT phase FROM v5_pri_native').fetchone()[0],'returned')
        self.assertEqual(len(self.provider.calls),1)


if __name__=='__main__':unittest.main()
