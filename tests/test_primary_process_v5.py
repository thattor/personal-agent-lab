"""Owned process gaps and actual whole mock path; no provider/semantic proof."""
import contextlib
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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant,Limits,dumps,loads
from pal.events_v5 import EventReader
from pal.host_read_v5 import HostReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockRunner
from pal.read_consumer_v5 import inspect_session
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore
ROOT=Path(__file__).resolve().parents[1]


def value(result):
    if not result.ok:raise AssertionError(result.error.code.value)
    return result.value.to_json()


def draft():
    return {'purpose':'案内の下書き','target':{'repository':'repo','issue_numbers':[],'files':[]},
        'constraints':['送信しない'],'conditions':[{'description':'saved','check':'artifact_saved'}],
        'context_refs':[]}


class Owners:
    def __init__(self,path,guard,invoke):
        from pal.primary_host_v5 import PrimaryHost
        self.conn=sqlite3.connect(path,isolation_level=None,timeout=0)
        self.guard=guard;self.grant=Grant((),('repo',),Limits(0,20,20))
        self.mem=self.art=self.ver=None
        self.tasks=TaskStore(self.conn,startup_guard=guard,host_grant=self.grant,
            host_limits=Limits(0,50,50),expert_id='mock-expert',
            source_gate=lambda c,r:self.mem.source_gate(c,r),
            artifact_inspect=lambda c,r:self.art.inspect(c,r),
            verification_inspect=lambda c,r:self.ver.inspect(c,r),
            artifact_lookup=lambda c,r:self.art.lookup_saved(c,r))
        self.mem=MemoryStore(self.conn,sanitize_text=sanitize,append_event=self.tasks.append_event,
                             invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art=ArtifactStore(self.conn,authorize_save=self.tasks.authorize_artifact_save,source_gate=self.mem.source_gate)
        self.ver=VerificationStore(self.conn,context=self.tasks.verification_context,
            artifact_inspect=self.art.inspect,source_gate=self.mem.source_gate)
        value(self.tasks.register_host())
        self.host=PrimaryHost(self.conn,guard=guard,memory=self.mem,tasks=self.tasks,
                              request_scope=self.grant,invoke=invoke,model_id='mock-process-primary')
    def ready(self):value(self.tasks.finish_startup())
    def used(self):return self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0]
    def submit(self,key='turn',text='案内を作ってください'):
        return value(self.host.submit({'client_key':key,'session_id':'session','text':text}))['turn_id']
    def record(self,key,text):return value(self.mem.append({'client_key':key,'session_id':'session','role':'user','text':text}))['record_ref']
    def runner(self):return MockRunner(self.tasks,self.mem,artifacts=self.art,verifications=self.ver)
    def close(self):self.conn.close()


def _barrier(data):
    print(json.dumps(data),flush=True)
    sys.stdin.buffer.read(1)
    raise AssertionError('parent must kill owned child')


def _child(path,mode):
    guard=MockHostSession.open(path)
    selected={'kind':'none'} if mode!='owner' else {'kind':'new_work','brief':draft()}
    turn=None
    def invoke(request):
        assert not owners.conn.in_transaction
        if mode=='admitted':_barrier({'turn_id':turn,'call_id':request['call_id']})
        return dumps({'reply':'mock answer','proposal':selected})
    owners=Owners(path,guard,invoke);owners.ready()
    if mode=='append':
        append=owners.mem.append
        def gap(request):
            receipt=value(append(request))
            _barrier({'record_ref':receipt['record_ref']})
        owners.mem.append=gap
        owners.submit(text='token=FIRST_PRIVATE')
    else:
        turn=owners.submit()
        if mode=='owner':
            create=owners.tasks.create
            def gap(request,*,request_scope):
                receipt=value(create(request,request_scope=request_scope))
                _barrier({'turn_id':turn,'receipt':receipt})
            owners.tasks.create=gap
        owners.host.run_turn({'turn_id':turn})
    raise AssertionError('child missed required barrier')


class PrimaryProcessTests(unittest.TestCase):
    def setUp(self):
        from pal.primary_host_v5 import PrimaryHost
        self.directory=tempfile.TemporaryDirectory(prefix='pal-pri-process-')
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'work.sqlite'
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.called=[]
    def invoke(self,request):
        self.called.append(request)
        return dumps({'reply':'mock reply','proposal':{'kind':'none'}})
    def open(self,*,ready=False,invoke=None):
        guard=MockHostSession.open(self.path)
        self.stack.callback(lambda:guard.close() if guard.phase!='closed' else None)
        owners=Owners(self.path,guard,invoke or self.invoke);self.stack.callback(owners.close)
        if ready:owners.ready()
        return owners
    def crash(self,mode):
        code='import sys;sys.path.insert(0,sys.argv[2]);from test_primary_process_v5 import _child;_child(sys.argv[1],sys.argv[3])'
        proc=subprocess.Popen([sys.executable,'-E','-s','-B','-c',code,str(self.path),str(ROOT/'tests'),mode],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=5)
            for pipe in (proc.stdin,proc.stdout,proc.stderr):pipe.close()
        self.addCleanup(cleanup)
        self.assertTrue(select.select([proc.stdout],[],[],10)[0],'child barrier timeout')
        line=proc.stdout.readline()
        if not line:self.fail('child exited before barrier: '+proc.stderr.read().decode()[-1500:])
        self.assertIsNone(proc.poll());checkpoint=json.loads(line)
        proc.kill();self.assertEqual(proc.wait(timeout=5),-signal.SIGKILL)
        return checkpoint

    def test_admitted_child_death_interrupts_no_reinference_or_refund(self):
        old=self.crash('admitted');owners=self.open();used=owners.used()
        recovered=value(owners.host.recover_turns())
        self.assertEqual(recovered,{'interrupted_turn_ids':[old['turn_id']],
                                   'committed_turn_ids':[],'held_turn_ids':[]})
        owners.ready();before=tuple(owners.conn.iterdump())
        status=value(owners.host.run_turn({'turn_id':old['turn_id']}))
        self.assertEqual(status['status'],'interrupted');self.assertNotIn('reply',status)
        self.assertEqual((owners.used(),self.called),(used,[]));self.assertEqual(used,1)
        self.assertEqual(tuple(owners.conn.iterdump()),before)

    def test_owner_commit_child_death_reconciles_original_receipt_no_reapply(self):
        old=self.crash('owner');owners=self.open();used=owners.used()
        recovered=value(owners.host.recover_turns());self.assertEqual(recovered['committed_turn_ids'],[old['turn_id']])
        self.assertEqual(recovered['held_turn_ids'],[]);owners.ready()
        self.assertEqual(value(owners.host.run_turn({'turn_id':old['turn_id']}))['status'],'committed')
        works=value(owners.tasks.list_candidates({'session_id':'session','limit':10}))['works']
        self.assertEqual(len(works),1);self.assertEqual(works[0]['work_ref']['goal_id'],old['receipt']['work_ref']['goal_id'])
        self.assertEqual((used,owners.used(),self.called),(1,1,[]))
        events=value(EventReader(owners.conn).get_events({'session_id':'session'}))['events']
        self.assertEqual(sum(e['kind']=='result' for e in events),1)
        before=tuple(owners.conn.iterdump());value(owners.host.get_turn({'turn_id':old['turn_id']}))
        self.assertEqual(tuple(owners.conn.iterdump()),before)

    def test_mem_commit_admission_gap_same_sanitized_client_resumes_no_duplicate(self):
        old=self.crash('append');owners=self.open()
        self.assertEqual(value(owners.host.recover_turns()),{'interrupted_turn_ids':[],
                           'committed_turn_ids':[],'held_turn_ids':[]});owners.ready()
        self.assertEqual(owners.used(),0)
        turn=owners.submit(text='token=SECOND_PRIVATE')
        recent=value(owners.mem.list_recent({'session_id':'session','limit':6}))
        self.assertEqual(recent,{'record_refs':[old['record_ref']],'truncated':False})
        self.assertEqual(owners.submit(text='token=THIRD_PRIVATE'),turn)
        self.assertEqual(owners.used(),0);self.assertEqual(self.called,[])
        self.assertEqual(value(owners.host.run_turn({'turn_id':turn}))['status'],'committed')
        self.assertEqual((owners.used(),len(self.called)),(1,1))
        self.assertNotIn('FIRST_PRIVATE','\n'.join(owners.conn.iterdump()))

    def test_two_connections_threads_entry_control_and_stop_before_cessation(self):
        main=self.open(ready=True);origin=main.record('origin','prior')
        made=value(main.tasks.create({'key':'work','session_id':'session','origin_record_ref':origin,
            'brief':draft()},request_scope=main.grant));work=made['work_ref']
        turn=main.submit();entered=threading.Event();release=threading.Event();result=[];failures=[];calls=[]
        def blocked(request):
            calls.append(request);entered.set()
            if not release.wait(5):raise AssertionError('owned callback release timed out')
            return dumps({'reply':'must be suppressed','proposal':{'kind':'none'}})
        def worker():
            owners=None
            try:
                owners=Owners(self.path,main.guard,blocked)
                result.append(value(owners.host.run_turn({'turn_id':turn})))
            except BaseException as exc:failures.append(exc)
            finally:
                if owners:owners.close()
        thread=threading.Thread(target=worker,name='owned-pri-fixed')
        thread.start()
        try:
            self.assertTrue(entered.wait(5),'callback admission failed')
            duplicate=value(main.host.run_turn({'turn_id':turn}));self.assertEqual(duplicate['status'],'pending')
            value(main.host.control({'client_key':'cancel','session_id':'session','work_ref':work,'command':'cancel'}))
            value(main.host.stop_reference({'client_key':'stop','session_id':'session','source_ref':origin}))
            self.assertTrue(thread.is_alive());self.assertFalse(release.is_set())
            self.assertEqual(value(main.tasks.get_work({'goal_id':work['goal_id']}))['state'],'cancelled')
            with self.assertRaises(RuntimeError):main.guard.close()
        finally:
            release.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(failures,[])
        self.assertEqual((len(calls),main.used()),(1,1));self.assertEqual(result[0]['status'],'failed')
        self.assertNotIn('reply',result[0])

    def test_whole_scripted_primary_expert_answer_change_saved_checked_readback_stop(self):
        phase='new'
        def primary(request):
            snapshot=loads(request['messages'][1]['text']);current=snapshot['record_ref']
            if phase=='new':proposal={'kind':'new_work','brief':draft()}
            elif phase=='answer':
                candidate=snapshot['candidates']['works'][0]
                proposal={'kind':'answer','work_ref':candidate['work_ref'],
                    'question_id':candidate['open_questions'][0]['id'],'record_ref':current}
            else:
                candidate=snapshot['candidates']['works'][0]
                proposal={'kind':'control','work_ref':candidate['work_ref'],
                    'command':{'kind':'change','brief':draft(),'origin_record_ref':current}}
            self.called.append(request)
            return dumps({'reply':'scripted acknowledgement','proposal':proposal})
        owners=self.open(ready=True,invoke=primary)
        value(owners.host.run_turn({'turn_id':owners.submit(key='new')}))
        goal=value(owners.tasks.list_candidates({'session_id':'session','limit':10}))['works'][0]['work_ref']['goal_id']
        expert=[]
        def ask(context,**diagnostics):
            expert.append('ask')
            return {'kind':'ask','question':'日時はいつですか','missing_fact':'date',
                    'source_refs':[body['ref'] for body in context['context']]}
        value(owners.runner().run_once(ask));work=value(owners.tasks.get_work({'goal_id':goal}))
        self.assertEqual(work['state'],'waiting_input')
        phase='answer';value(owners.host.run_turn({'turn_id':owners.submit(key='answer',text='来週月曜です')}))
        self.assertEqual(value(owners.tasks.get_work({'goal_id':goal}))['state'],'queued')
        phase='change';value(owners.host.run_turn({'turn_id':owners.submit(key='change',text='送信せず下書きのみ')}))
        self.assertEqual(value(owners.tasks.get_work({'goal_id':goal}))['work_ref']['revision'],2)
        def compose(context,**diagnostics):
            expert.append('compose')
            return {'kind':'compose','content':'案内の下書き。送信していません。','media_type':'text/plain',
                    'source_refs':[body['ref'] for body in context['context']]}
        completed=value(owners.runner().run_once(compose));self.assertEqual(completed['status'],'completed')
        self.assertEqual(expert,['ask','compose']);self.assertEqual(len(self.called),3)
        work=value(owners.tasks.get_work({'goal_id':goal}));self.assertEqual(work['state'],'completed')
        self.assertEqual(owners.used(),5)
        reader=HostReader(memory=owners.mem,artifacts=owners.art,verifications=owners.ver)
        view=value(inspect_session({'session_id':'session'},events=EventReader(owners.conn),tasks=owners.tasks,reader=reader))
        self.assertTrue(view['items']);self.assertIn('案内の下書き',dumps(view))
        source=self.called[-1]['source_refs'][0]
        value(owners.host.stop_reference({'client_key':'stop-final','session_id':'session','source_ref':source}))
        historical=value(owners.ver.get_verification({'verification_ref':completed['verification']['verification_ref']}))
        self.assertEqual(historical['status'],'invalidated')
        view=value(inspect_session({'session_id':'session'},events=EventReader(owners.conn),tasks=owners.tasks,reader=reader))
        self.assertIn('source stopped',dumps(view));self.assertEqual(owners.used(),5)
