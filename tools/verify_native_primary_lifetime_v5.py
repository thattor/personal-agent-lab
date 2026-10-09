"""Owned-process NativePrimary local lifetime fixtures, never native proof."""
import contextlib
import hashlib
import json
from pathlib import Path
import select
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, Result, dumps
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockRunner
from pal.native_call_v5 import NativeProfile, NativeReturned
from pal.native_text_v5 import NativeTextBuffer
from pal.primary_host_v5 import NativePrimaryHost
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


def value(result):
    if not result.ok: raise AssertionError(result.error.code.value)
    return result.value.to_json()


def draft():
    return {'purpose':'fixture draft','target':{'repository':'repo','issue_numbers':[],'files':[]},
            'constraints':[],'conditions':[{'description':'saved','check':'artifact_saved'}],'context_refs':[]}


class Provider:
    def __init__(self):
        self.profile = NativeProfile(model_id='swe-2-high',qualification_sha256='2'*64,evidence_kind='fixture')
        self.calls = []; self.behavior = None; self.proposal = {'kind':'none'}; self.owners = None
    def preflight(self):
        assert not self.owners.conn.in_transaction
    def invoke(self, request, *, on_enter):
        assert not self.owners.conn.in_transaction
        self.calls.append(request)
        attempt = {'run_id':'fixture-run','job_id':'fixture-job','attempt_id':'fixture-'+str(len(self.calls))}
        on_enter(attempt)
        assert not self.owners.conn.in_transaction
        if self.behavior: self.behavior(request, attempt)
        text = dumps({'reply':'fixture reply','proposal':self.proposal})
        ending = {'attempt_ref':attempt,'guarantee_model':'native_handoff_v1','capability':'devin.text.only',
                  'native_stop_reason':'end_turn','native_mode':'plan','effective_model':'swe-2-high',
                  'effective_model_verified':True,'stdout_eof_validated':True,'owned_pid':123,'owned_exit_code':-15,
                  'tool_events':0,'pending_permissions':0,'session_sha256':'3'*64,'prompt_rpc_sha256':'4'*64}
        ending['evidence_ref']='devin.acp:text-only:end_turn:'+hashlib.sha256(
            json.dumps(ending,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        buffer=NativeTextBuffer(request_sha256=hashlib.sha256(dumps(request).encode()).hexdigest(),
            profile_sha256=self.profile.profile_sha256,attempt_ref=attempt,model_id='swe-2-high')
        buffer.begin();buffer.observe({'sessionUpdate':'agent_message_chunk','content':{'type':'text','text':text}})
        return NativeReturned(capture=buffer.finish(ending),cessation=ending)


class Owners:
    def __init__(self,path,guard,provider):
        self.conn=sqlite3.connect(path,isolation_level=None,timeout=0)
        self.guard=guard;self.grant=Grant((),('repo',),Limits(0,20,20))
        self.tasks=TaskStore(self.conn,startup_guard=guard,host_grant=self.grant,host_limits=Limits(0,50,50),
            expert_id='fixture-expert',source_gate=lambda c,r:self.mem.source_gate(c,r),
            artifact_inspect=lambda c,r:self.art.inspect(c,r),verification_inspect=lambda c,r:self.ver.inspect(c,r),
            artifact_lookup=lambda c,r:self.art.lookup_saved(c,r))
        self.mem=MemoryStore(self.conn,sanitize_text=sanitize,append_event=self.tasks.append_event,
            invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art=ArtifactStore(self.conn,authorize_save=self.tasks.authorize_artifact_save,source_gate=self.mem.source_gate)
        self.ver=VerificationStore(self.conn,context=self.tasks.verification_context,
            artifact_inspect=self.art.inspect,source_gate=self.mem.source_gate)
        if guard.phase in ('owned','startup'):value(self.tasks.register_host())
        provider.owners=self
        self.host=NativePrimaryHost(self.conn,guard=guard,memory=self.mem,tasks=self.tasks,
            request_scope=self.grant,provider=provider)
        self.runner=MockRunner(self.tasks,self.mem,artifacts=self.art,verifications=self.ver)
    def ready(self):value(self.tasks.finish_startup())
    def used(self):return self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0]
    def submit(self):return value(self.host.submit({'client_key':'turn','session_id':'session','text':'fixture input'}))['turn_id']
    def ending(self):return self.conn.execute('SELECT phase,ending_json,ending_hash FROM v5_pri_native').fetchone()
    def close(self):self.conn.close()


def barrier(owners,data):
    assert not owners.conn.in_transaction
    print(json.dumps(data),flush=True)
    sys.stdin.buffer.read(1)
    raise AssertionError('owned parent must SIGKILL child')


def child(path,mode):
    guard=MockHostSession.open(path);provider=Provider();owners=Owners(path,guard,provider);owners.ready()
    turn=owners.submit()
    if mode=='entry':
        provider.behavior=lambda r,a:barrier(owners,{'turn_id':turn})
    elif mode=='returned':
        from pal.primary_host_v5 import parse_primary_output as original_parse
        def after_return(*args,**kwargs):
            ending=owners.ending()
            if ending is not None and ending[0]=='returned':
                barrier(owners,{'turn_id':turn,'ending':ending})
            return original_parse(*args,**kwargs)
        with patch('pal.primary_host_v5.parse_primary_output',side_effect=after_return):
            owners.host.run_turn({'turn_id':turn})
    elif mode=='owner':
        provider.proposal={'kind':'new_work','brief':draft()}
        create=owners.tasks.create
        def after_owner(request,*,request_scope):
            receipt=value(create(request,request_scope=request_scope))
            barrier(owners,{'turn_id':turn,'receipt':receipt,'ending':owners.ending()})
        owners.tasks.create=after_owner
    else:raise AssertionError('unknown fixture mode')
    owners.host.run_turn({'turn_id':turn})
    raise AssertionError('missing child barrier')


class NativeLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='pal-native-lifetime-');self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'work.sqlite'
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
    def open(self,ready=False):
        guard=MockHostSession.open(self.path)
        self.stack.callback(lambda:guard.close() if guard.phase!='closed' else None)
        provider=Provider();owners=Owners(self.path,guard,provider);self.stack.callback(owners.close)
        if ready:owners.ready()
        return owners,provider
    def crash(self,mode):
        proc=subprocess.Popen([sys.executable,'-E','-s','-B',str(Path(__file__).resolve()),'--child',str(self.path),mode],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=5)
            for stream in (proc.stdin,proc.stdout,proc.stderr):stream.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout],[],[],10)[0],'child barrier timeout')
        line=proc.stdout.readline()
        if not line:self.fail('child barrier absent: '+proc.stderr.read().decode()[-1200:])
        checkpoint=json.loads(line);self.assertIsNone(proc.poll())
        proc.kill();self.assertEqual(proc.wait(timeout=5),-signal.SIGKILL)
        return checkpoint
    def run_turn(self,owners,turn):return value(owners.host.run_turn({'turn_id':turn}))
    def test_sigkill_after_entry_retains_unknown_no_retry_or_refund(self):
        old=self.crash('entry');owners,provider=self.open();before=owners.used()
        recovered=value(owners.host.recover_turns())
        self.assertEqual(recovered['held_turn_ids'],[old['turn_id']]);self.assertEqual(recovered['interrupted_turn_ids'],[])
        owners.ready();snapshot=tuple(owners.conn.iterdump())
        self.assertEqual(self.run_turn(owners,old['turn_id']),{'status':'held','effect_refs':[]})
        self.assertEqual(tuple(owners.conn.iterdump()),snapshot)
        self.assertEqual((before,owners.used(),provider.calls),(1,1,[]))
        self.assertEqual(owners.conn.execute('SELECT status FROM v5_pri_call').fetchone()[0],'unknown')
    def test_sigkill_known_return_before_intent_fails_only_local_adoption(self):
        old=self.crash('returned');owners,provider=self.open()
        recovered=value(owners.host.recover_turns());self.assertEqual(recovered['failed_turn_ids'],[old['turn_id']])
        owners.ready();result=self.run_turn(owners,old['turn_id'])
        self.assertEqual(result['status'],'failed');self.assertNotIn('reply',result)
        self.assertEqual(list(owners.ending()),old['ending']);self.assertEqual((owners.used(),provider.calls),(1,[]))
    def test_sigkill_after_owner_commit_adopts_original_lookup_once(self):
        old=self.crash('owner');owners,provider=self.open()
        owners.tasks.create=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('never redispatch'))
        recovered=value(owners.host.recover_turns());self.assertEqual(recovered['committed_turn_ids'],[old['turn_id']])
        owners.ready();result=self.run_turn(owners,old['turn_id']);self.assertEqual(result['status'],'committed')
        works=value(owners.tasks.list_candidates({'session_id':'session','limit':10}))['works']
        self.assertEqual([w['work_ref'] for w in works],[old['receipt']['work_ref']])
        self.assertEqual(list(owners.ending()),old['ending']);self.assertEqual((owners.used(),provider.calls),(1,[]))
        events=value(EventReader(owners.conn).get_events({'session_id':'session'}))['events']
        self.assertEqual(sum(e['kind']=='result' for e in events),1)
    def test_uncertain_original_lookup_holds_then_adopts_without_redispatch(self):
        old=self.crash('owner');owners,provider=self.open();lookup=owners.tasks.get_create_by_key
        owners.tasks.create=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('never redispatch'))
        owners.tasks.get_create_by_key=lambda req:Result.failure('unavailable','fixture')
        snapshot=tuple(owners.conn.iterdump());recovered=value(owners.host.recover_turns())
        self.assertEqual(recovered['held_turn_ids'],[old['turn_id']]);self.assertEqual(tuple(owners.conn.iterdump()),snapshot)
        owners.tasks.get_create_by_key=lookup
        recovered=value(owners.host.recover_turns());self.assertEqual(recovered['committed_turn_ids'],[old['turn_id']])
        self.assertEqual((owners.used(),provider.calls),(1,[]));self.assertEqual(list(owners.ending()),old['ending'])
    def test_two_connections_control_stop_while_blocked_fences_effect(self):
        owners,provider=self.open(ready=True)
        origin=value(owners.mem.append({'client_key':'origin','session_id':'session','role':'user','text':'prior'}))['record_ref']
        work=value(owners.tasks.create({'key':'prior','session_id':'session','origin_record_ref':origin,'brief':draft()},request_scope=owners.grant))['work_ref']
        turn=owners.submit();entered=threading.Event();release=threading.Event();out=[];errors=[];calls=[]
        def worker():
            local=None
            try:
                p=Provider();p.proposal={'kind':'new_work','brief':draft()}
                local=Owners(self.path,owners.guard,p)
                def blocked(request,attempt):
                    calls.append(request);entered.set()
                    if not release.wait(5):raise AssertionError('owned release timeout')
                p.behavior=blocked
                out.append(self.run_turn(local,turn))
            except BaseException as exc:errors.append(exc)
            finally:
                if local:local.close()
        thread=threading.Thread(target=worker,name='native-fixture-owned');thread.start()
        try:
            self.assertTrue(entered.wait(5),'native entry barrier absent')
            self.assertFalse(owners.conn.in_transaction)
            value(owners.host.control({'client_key':'cancel','session_id':'session','work_ref':work,'command':'cancel'}))
            value(owners.host.stop_reference({'client_key':'stop','session_id':'session','source_ref':calls[0]['source_refs'][0]}))
            self.assertTrue(thread.is_alive());self.assertFalse(release.is_set())
            self.assertEqual(value(owners.tasks.get_work({'goal_id':work['goal_id']}))['state'],'cancelled')
        finally:release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
        self.assertEqual(len(calls),1);self.assertEqual(owners.used(),1)
        self.assertEqual(out[0]['status'],'failed');self.assertNotIn('reply',out[0])
        works=value(owners.tasks.list_candidates({'session_id':'session','limit':10}))['works']
        self.assertFalse(any(w['work_ref']['goal_id']!=work['goal_id'] for w in works))
        self.assertEqual(owners.ending()[0],'returned')


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--child':child(Path(sys.argv[2]),sys.argv[3])
    else:unittest.main()
