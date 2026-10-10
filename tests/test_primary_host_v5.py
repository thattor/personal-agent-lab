"""Frozen PRI01 managed actual-owner acceptance; in-process mock C15 only."""
import copy
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.artifacts_v5 import ArtifactStore
from pal.contracts_v5 import Grant, Limits, Ref, Result, dumps, loads
from pal.events_v5 import EventReader
from pal.memory_v5 import MemoryStore
from pal.mock_host_v5 import MockHostSession
from pal.mock_runner_v5 import MockInvoker
from pal.sanitize import sanitize
from pal.tasks_v5 import TaskStore
from pal.verification_v5 import VerificationStore


class PrimaryHostTests(unittest.TestCase):
    def setUp(self):
        from pal.primary_host_v5 import PrimaryHost
        self.Host=PrimaryHost
        self.directory=tempfile.TemporaryDirectory(prefix='pal-pri-fixed-')
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'work.sqlite'
        self.serial=0;self.calls=[];self.proposal={'kind':'none'};self.reply='mock reply';self.hook=None
        self.grant=Grant((),('repo',),Limits(0,20,20))
        self.connect(ready=True)
        self.host=self.make_host()

    def connect(self,ready):
        self.guard=MockHostSession.open(self.path)
        self.addCleanup(lambda guard=self.guard:guard.close() if guard.phase!='closed' else None)
        self.conn=sqlite3.connect(self.path,isolation_level=None,timeout=0)
        self.addCleanup(self.conn.close)
        self.mem=self.art=self.ver=None
        self.tasks=TaskStore(self.conn,startup_guard=self.guard,host_grant=self.grant,
            host_limits=Limits(0,100,100),expert_id='expert',
            source_gate=lambda c,r:self.mem.source_gate(c,r),
            artifact_inspect=lambda c,r:self.art.inspect(c,r),
            verification_inspect=lambda c,r:self.ver.inspect(c,r),
            artifact_lookup=lambda c,r:self.art.lookup_saved(c,r))
        self.mem=MemoryStore(self.conn,sanitize_text=sanitize,append_event=self.tasks.append_event,
                             invalidate_by_refs=self.tasks.invalidate_by_refs)
        self.art=ArtifactStore(self.conn,authorize_save=self.tasks.authorize_artifact_save,
                               source_gate=self.mem.source_gate)
        self.ver=VerificationStore(self.conn,context=self.tasks.verification_context,
            artifact_inspect=self.art.inspect,source_gate=self.mem.source_gate)
        self.ok(self.tasks.register_host())
        if ready:self.ok(self.tasks.finish_startup())

    def make_host(self,**changes):
        config=dict(guard=self.guard,memory=self.mem,tasks=self.tasks,request_scope=self.grant,
                    invoke=self.invoke,model_id='mock-fixed-primary')
        config.update(changes)
        return self.Host(self.conn,**config)

    def key(self):self.serial+=1;return 'k-'+str(self.serial)
    def ok(self,result):
        self.assertIs(type(result),Result);self.assertTrue(result.ok,result.to_json())
        return result.value.to_json()
    def error(self,result,code):
        self.assertFalse(result.ok);self.assertEqual(result.error.code.value,code)
        self.assertLessEqual(len(result.error.message),200)
        self.assertNotIn('PRIVATE_CANARY',dumps(result))
    def snapshot(self):return tuple(self.conn.iterdump())
    def used(self):return self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0]
    def record(self,text='prior',session='session'):
        return self.ok(self.mem.append({'client_key':self.key(),'session_id':session,'role':'user','text':text}))['record_ref']
    def submit(self,key=None,text='依頼の本文',session='session'):
        result=self.ok(self.host.submit({'client_key':key or self.key(),'session_id':session,'text':text}))
        self.assertEqual(set(result),{'turn_id','status'});self.assertEqual(result['status'],'pending')
        return result['turn_id']
    def get(self,turn):
        out=self.ok(self.host.get_turn({'turn_id':turn}))
        self.assertTrue({'status','effect_refs'}<=set(out));self.assertTrue(set(out)<= {'status','effect_refs','reply','error'})
        self.assertIn(out['status'],('pending','committed','failed','interrupted'))
        for ref in out['effect_refs']:Ref.from_json(ref)
        return out
    def run_turn(self,turn,status='committed'):
        out=self.ok(self.host.run_turn({'turn_id':turn}));self.assertEqual(out,self.get(turn))
        self.assertEqual(out['status'],status)
        if status=='failed':
            self.assertIn('error',out);self.assertNotIn('reply',out)
            self.assertNotIn('PRIVATE_CANARY',dumps(out))
        return out
    def draft(self,refs=()):
        return {'purpose':'draft','target':{'repository':'repo','issue_numbers':[],'files':[]},
            'constraints':['no sending'],'conditions':[{'description':'saved','check':'artifact_saved'}],
            'context_refs':list(refs)}
    def work(self,origin=None,purpose='existing'):
        origin=origin or self.record()
        request={'key':self.key(),'session_id':'session','origin_record_ref':origin,
                 'brief':{**self.draft(),'purpose':purpose}}
        return self.ok(self.tasks.create(request,request_scope=self.grant))['work_ref']
    def current(self,work):return self.ok(self.tasks.get_work({'goal_id':work['goal_id']}))
    def stop(self,ref):return self.ok(self.mem.stop_reference({'key':self.key(),'source_ref':ref},session_id='session'))
    def invoke(self,request):
        self.assertEqual(set(request),{'call_id','reservation_id','role','messages','source_refs','output_kind'})
        self.assertEqual((request['role'],request['output_kind']),('primary','primary_proposal'))
        self.assertFalse(self.conn.in_transaction)
        self.assertEqual([m['role'] for m in request['messages']],['system','user'])
        self.assertTrue(all(set(m)=={'role','text'} and type(m['text']) is str for m in request['messages']))
        snap=loads(request['messages'][1]['text'])
        self.assertEqual(set(snap),{'record_ref','session_id','candidates','context'})
        self.assertEqual(set(snap['candidates']),{'works','truncated'})
        self.assertEqual(set(snap['context']),{'summaries','records','records_truncated'})
        self.assertEqual(snap['context']['summaries'],[])
        self.assertLessEqual(len(dumps(snap).encode()),32768)
        self.assertLessEqual(len(snap['context']['records']),6)
        refs=[snap['record_ref']]
        for body in snap['context']['records']:
            self.assertEqual(set(body),{'ref','content','media_type','hash','observed_at','source_refs','usable'})
            self.assertTrue(body['usable']);self.assertEqual(body['hash'],hashlib.sha256(body['content'].encode()).hexdigest())
            refs.append(body['ref'])
        for item in snap['candidates']['works']:
            if not item['text_withheld']:refs.extend(item['dependency_refs'])
        dedup=[]
        for ref in refs:
            if ref not in dedup:dedup.append(ref)
        self.assertEqual(request['source_refs'],dedup)
        self.calls.append(copy.deepcopy(request))
        if self.hook:self.hook(snap)
        proposal=self.proposal(snap) if callable(self.proposal) else self.proposal
        return dumps({'reply':self.reply,'proposal':proposal})
    def restart(self):
        self.conn.close();self.guard.close();self.connect(ready=False);self.host=self.make_host()
    def ask(self,work):
        lease=self.ok(self.tasks.claim({'runner_id':self.guard.runner_id}))
        self.assertEqual(lease['work_ref']['goal_id'],work['goal_id'])
        reservation=self.ok(self.tasks.reserve_budget({'key':self.key(),'work_ref':lease['work_ref'],'kind':'model','role':'expert'}))
        admission={'call_id':dumps(['C15.call',lease['lease_id'],0]),'lease_id':lease['lease_id'],
            'work_ref':lease['work_ref'],'reservation_id':reservation['reservation_id'],
            'source_refs':self.current(work)['brief']['context_refs']}
        # Origin is always a required dependency even when Brief has no selected refs.
        refs=self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works'][0]['dependency_refs']
        admission['source_refs']=refs
        action={'kind':'ask','question':'いつですか','missing_fact':'date','source_refs':refs}
        self.ok(MockInvoker().invoke(self.tasks,admission,lambda:action))
        step=self.ok(self.tasks.begin_step({'key':self.key(),'work_ref':lease['work_ref'],'action':action}))
        receipt=self.ok(self.tasks.ask({'key':self.key(),'work_ref':lease['work_ref'],'step_id':step['step_id'],
                                     **{k:v for k,v in action.items() if k!='kind'}}))
        question=self.current(work)['open_questions'][0]['id']
        return self.current(work)['work_ref'],question,receipt

    def test_constructor_valid_and_invalid_config(self):
        self.assertIsInstance(self.host,self.Host)
        for changes in ({'guard':object()},{'request_scope':{}},{'invoke':None},{'model_id':''}):
            with self.assertRaises((TypeError,ValueError,RuntimeError)):self.make_host(**changes)

    def test_submit_no_inference_closed_admission_and_mem_identity(self):
        turn=self.submit(key='opaque:key')
        self.assertEqual(self.calls,[]);self.assertEqual(self.used(),0)
        receipt=self.ok(self.mem.append({'client_key':dumps(['PRI01.append','session','opaque:key']),
            'session_id':'session','role':'user','text':'依頼の本文'}))
        self.assertEqual(len(self.ok(self.mem.list_recent({'session_id':'session','limit':6}))['record_refs']),1)
        self.assertEqual(self.get(turn)['status'],'pending')

    def test_duplicate_submit_sanitized_identity_conflict_and_sessions(self):
        first=self.submit(key='same',text='token=FIRST_PRIVATE')
        self.assertEqual(self.submit(key='same',text='token=SECOND_PRIVATE'),first)
        self.error(self.host.submit({'client_key':'same','session_id':'session','text':'changed'}),'conflict')
        self.assertNotEqual(self.submit(key='same',session='other'),first)
        self.assertNotIn('FIRST_PRIVATE','\n'.join(self.snapshot()))

    def test_submit_strict_input_and_inclusive_utf8_bound(self):
        for req in ({},{'client_key':'','session_id':'s','text':'x'}, {'client_key':'k','session_id':'','text':'x'},
                    {'client_key':'k','session_id':'s','text':'\ud800'}, {'client_key':'k','session_id':'s','text':1},
                    {'client_key':'k','session_id':'s','text':'x','grant':{}}):self.error(self.host.submit(req),'invalid_input')
        self.submit(text='x'*16384)
        self.error(self.host.submit({'client_key':'big','session_id':'s','text':'界'*5462}),'limit')

    def test_turn_request_errors_and_unknown(self):
        for method in (self.host.get_turn,self.host.run_turn):
            self.error(method({'turn_id':'absent'}),'not_found')
            for req in ({},{'turn_id':''},{'turn_id':'x','extra':1}):self.error(method(req),'invalid_input')

    def test_none_commits_one_fixed_event_no_assistant_record(self):
        turn=self.submit();self.run_turn(turn)
        events=self.ok(EventReader(self.conn).get_events({'session_id':'session'}))['events']
        terminals=[e for e in events if e['kind'] in ('result','error')]
        self.assertEqual(len(terminals),1);self.assertNotIn(self.reply,dumps(terminals))
        self.assertEqual(len(self.ok(self.mem.list_recent({'session_id':'session','limit':6}))['record_refs']),1)

    def test_terminal_duplicate_run_read_no_new_call_effect_or_charge(self):
        turn=self.submit();result=self.run_turn(turn);before=self.snapshot()
        self.assertEqual(self.run_turn(turn),result);self.assertEqual(self.get(turn),result)
        self.assertEqual(self.snapshot(),before);self.assertEqual(len(self.calls),1)

    def test_active_reentrant_duplicate_does_not_take_over(self):
        turn=self.submit();nested=[]
        second=self.make_host()
        def reenter(snap):
            nested.append(self.ok(self.host.run_turn({'turn_id':turn})))
            nested.append(self.ok(second.run_turn({'turn_id':turn})))
        self.hook=reenter
        self.run_turn(turn);self.assertEqual([x['status'] for x in nested],['pending','pending'])
        self.assertEqual(len(self.calls),1)

    def test_c15_binds_turn_reservation_and_no_transaction(self):
        turn=self.submit();self.run_turn(turn)
        call=self.calls[0];self.assertEqual(call['call_id'],dumps(['PRI01.call',turn]))
        reservation=self.ok(self.tasks.reserve_budget({'key':dumps(['PRI01.reserve',turn]),'kind':'model','role':'primary'}))
        self.assertEqual(call['reservation_id'],reservation['reservation_id']);self.assertEqual(self.used(),1)
        self.ok(self.tasks.consume({'reservation_id':reservation['reservation_id'],'call_or_operation_id':call['call_id']}))

    def test_model_zero_refuses_before_callback_step_zero_permits(self):
        turn=self.submit();self.conn.execute("UPDATE v5_tsk_host SET ceiling=0 WHERE kind='model'")
        out=self.run_turn(turn,'failed');self.assertNotIn('reply',out);self.assertEqual(self.calls,[])
        self.conn.execute("UPDATE v5_tsk_host SET ceiling=1 WHERE kind='model'")
        self.conn.execute("UPDATE v5_tsk_host SET ceiling=0 WHERE kind='step'")
        self.run_turn(self.submit());self.assertEqual(self.used(),1)

    def test_snapshot_same_session_current_mandatory_optional_six_truncated(self):
        for n in range(8):self.record('prior-'+str(n))
        other=self.record('other-secret',session='other')
        turn=self.submit();self.run_turn(turn);snap=loads(self.calls[0]['messages'][1]['text'])
        self.assertEqual(len(snap['context']['records']),6);self.assertTrue(snap['context']['records_truncated'])
        self.assertIn(snap['record_ref'],[r['ref'] for r in snap['context']['records']])
        self.assertNotIn(other,self.calls[0]['source_refs'])

    def test_optional_oldest_body_drops_for_snapshot_byte_cap(self):
        for n in range(5):self.record('x'*10000+str(n))
        self.run_turn(self.submit());snap=loads(self.calls[0]['messages'][1]['text'])
        self.assertTrue(snap['context']['records_truncated']);self.assertLess(len(snap['context']['records']),6)

    def test_mandatory_overcap_fails_before_budget_and_callback(self):
        # JSON escaping expands legal input beyond the C01 byte cap.
        turn=self.submit(text='\x01'*10000)
        self.run_turn(turn,'failed');self.assertEqual((self.used(),self.calls),(0,[]))

    def test_stopped_current_before_entry_is_not_empty_fallback(self):
        turn=self.submit(key='current');ref=self.ok(self.mem.append({'client_key':dumps(['PRI01.append','session','current']),
            'session_id':'session','role':'user','text':'依頼の本文'}))['record_ref'];self.stop(ref)
        self.run_turn(turn,'failed');self.assertEqual((self.used(),self.calls),(0,[]))

    def test_malformed_c11_body_shape_hash_and_usability_fail_before_callback(self):
        original=self.mem.read
        for change in ({'hash':'0'*64},{'usable':False},{'extra':True}):
            def broken(req,*,purpose,change=change):
                body=self.ok(original(req,purpose=purpose));body.update(change);return Result.success(body)
            self.mem.read=original;turn=self.submit()
            self.mem.read=broken;self.run_turn(turn,'failed');self.assertEqual(self.calls,[])
        self.mem.read=original;self.assertEqual(self.used(),0)

    def test_new_work_full_exposure_closure_and_trusted_grant(self):
        optional=self.record('uncited')
        self.proposal={'kind':'new_work','brief':self.draft()};turn=self.submit();self.run_turn(turn)
        works=self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works']
        self.assertEqual(len(works),1);work=self.current(works[0]['work_ref'])
        self.assertIn(optional,work['brief']['context_refs']);self.assertEqual(work['grant']['capabilities'],[])
        self.assertEqual(work['brief']['context_refs'],self.calls[0]['source_refs'])

    def test_withheld_historic_a_does_not_block_unrelated_new_b(self):
        origin=self.record('old source');a=self.work(origin);self.stop(origin)
        self.proposal={'kind':'new_work','brief':self.draft()};self.run_turn(self.submit())
        snap=loads(self.calls[0]['messages'][1]['text']);entry=snap['candidates']['works'][0]
        self.assertTrue(entry['text_withheld']);self.assertEqual(entry['brief_summary'],'')
        self.assertNotIn(origin,self.calls[0]['source_refs'])
        works=self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works']
        self.assertEqual(len(works),2)

    def test_answer_actual_question_current_record_and_same_goal(self):
        work=self.work();target,q,_=self.ask(work)
        self.proposal=lambda snap:{'kind':'answer','work_ref':target,'question_id':q,'record_ref':snap['record_ref']}
        self.run_turn(self.submit(text='来週です'))
        current=self.current(work);self.assertEqual(current['work_ref']['goal_id'],work['goal_id'])
        self.assertEqual(current['state'],'queued');self.assertEqual(current['open_questions'],[])

    def test_change_same_goal_next_revision_prior_authority_closed_sources(self):
        work=self.work()
        self.proposal=lambda snap:{'kind':'control','work_ref':snap['candidates']['works'][0]['work_ref'],
            'command':{'kind':'change','brief':self.draft(),'origin_record_ref':snap['record_ref']}}
        self.run_turn(self.submit(text='内容を変更'))
        current=self.current(work);self.assertEqual(current['work_ref']['revision'],2)
        self.assertEqual(current['grant']['capabilities'],[])
        self.assertEqual(current['brief']['context_refs'],self.calls[0]['source_refs'])

    def test_wrong_but_listed_control_is_owner_effect_not_intention_proof(self):
        work=self.work()
        self.proposal={'kind':'control','work_ref':work,'command':'cancel'}
        self.run_turn(self.submit(text='semantically ambiguous'))
        self.assertEqual(self.current(work)['state'],'cancelled')

    def test_invalid_outofset_or_model_grant_fails_no_effect_reply(self):
        for proposal in ({'kind':'control','work_ref':{'goal_id':'absent','revision':1,'epoch':0},'command':'cancel'},
                         {'kind':'new_work','brief':self.draft(),'grant':{}},{'kind':'continue'}):
            self.proposal=proposal;out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out)
        self.assertEqual(self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works'],[])

    def test_fingerprint_goal_revision_question_changes_stale_without_effect(self):
        work=self.work()
        for mutation in ('revision','question','new_goal'):
            with self.subTest(mutation=mutation):
                self.proposal={'kind':'new_work','brief':self.draft()}
                current=self.current(work)['work_ref']
                if mutation=='new_goal':self.hook=lambda snap:self.work(purpose='concurrent work')
                elif mutation=='revision':
                    correction=self.record('correction')
                    self.hook=lambda snap:self.ok(self.tasks.control({'key':self.key(),'work_ref':current,
                        'command':{'kind':'change','brief':self.draft(),'origin_record_ref':correction}}))
                else:self.hook=lambda snap:self.ask(current)
                count=len(self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works'])
                out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out)
                expected=count+1 if mutation=='new_goal' else count
                self.assertEqual(len(self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works']),expected)

    def test_fingerprint_epoch_state_change_alone_does_not_invalidate_none(self):
        work=self.work();self.hook=lambda snap:self.ok(self.tasks.control({'key':self.key(),'work_ref':work,'command':'pause'}))
        self.run_turn(self.submit());self.assertEqual(self.current(work)['state'],'paused')

    def test_exposed_uncited_optional_stop_before_dispatch_denies_new_work(self):
        optional=self.record('uncited');self.proposal={'kind':'new_work','brief':self.draft()}
        self.hook=lambda snap:self.stop(optional)
        out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out)
        self.assertEqual(self.ok(self.tasks.list_candidates({'session_id':'session','limit':10}))['works'],[])

    def test_committed_reply_read_suppressed_after_source_stop_no_new_effect(self):
        optional=self.record('uncited');turn=self.submit();self.run_turn(turn)
        self.stop(optional);before=self.snapshot();out=self.get(turn)
        self.assertEqual(out['status'],'committed');self.assertNotIn('reply',out);self.assertIn('error',out)
        self.assertEqual(self.snapshot(),before);self.assertEqual(len(self.calls),1)

    def test_model_memory_stop_retains_receipt_suppresses_invalidated_reply(self):
        ref=self.record();self.proposal={'kind':'memory','operation':{'kind':'stop_reference','source_ref':ref}}
        out=self.run_turn(self.submit());self.assertNotIn('reply',out);self.assertIn(ref,out['effect_refs'])
        self.error(self.mem.read({'ref':ref},purpose='model_context'),'denied')

    def test_structured_control_bypasses_callback_memory_and_primary_budget(self):
        work=self.work();before=self.used();records=self.ok(self.mem.list_recent({'session_id':'session','limit':6}))
        receipt=self.ok(self.host.control({'client_key':'direct','session_id':'session','work_ref':work,'command':'cancel'}))
        self.assertEqual(receipt,self.ok(self.tasks.get_control_by_key({'key':dumps(['PRI01.control','session','direct'])})))
        self.assertEqual((self.used(),self.calls),(before,[]));self.assertEqual(self.ok(self.mem.list_recent({'session_id':'session','limit':6})),records)

    def test_structured_stop_during_callback_no_mutex_and_reply_suppression(self):
        ref=self.record();seen=[]
        self.hook=lambda snap:seen.append(self.ok(self.host.stop_reference({'client_key':'direct-stop',
            'session_id':'session','source_ref':ref})))
        out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out);self.assertEqual(len(seen),1)
        self.assertEqual(seen[0],self.ok(self.mem.get_stop_reference_by_key({'key':dumps(['PRI01.stop','session','direct-stop'])})))

    def test_structured_input_shapes_no_model_complete_or_kind_substitution(self):
        work=self.work()
        self.error(self.host.control({'client_key':'x','session_id':'session','work_ref':work,'command':'complete'}),'invalid_input')
        self.error(self.host.stop_reference({'client_key':'x','session_id':'session','source_ref':{'kind':'artifact','id':'a'}}),'invalid_input')
        self.assertEqual(self.calls,[])

    def test_definitive_owner_refusal_is_failed_no_reply(self):
        self.proposal={'kind':'new_work','brief':self.draft()};original=self.tasks.create
        self.tasks.create=lambda *a,**kw:Result.failure('denied','PRIVATE_CANARY')
        out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out)
        self.assertNotIn('PRIVATE_CANARY',dumps(out));self.tasks.create=original

    def test_uncertain_owner_failure_never_redispatches_or_reinfers(self):
        self.proposal={'kind':'new_work','brief':self.draft()}
        for mode in ('unavailable','exception','malformed'):
            dispatched=[];before=len(self.calls)
            def uncertain(*args,**kw):
                dispatched.append(1)
                if mode=='exception':raise RuntimeError('PRIVATE_CANARY')
                if mode=='malformed':return {'guessed_success':True}
                return Result.failure('unavailable','PRIVATE_CANARY')
            self.tasks.create=uncertain;turn=self.submit();out=self.run_turn(turn,'pending')
            self.assertNotIn('reply',out);self.run_turn(turn,'pending')
            self.assertEqual((len(dispatched),len(self.calls)-before),(1,1))

    def test_owner_commit_reply_loss_recovery_uses_receipt_without_reapply(self):
        self.proposal={'kind':'new_work','brief':self.draft()};create=self.tasks.create
        def lost(*args,**kw):self.ok(create(*args,**kw));raise RuntimeError('PRIVATE_CANARY')
        self.tasks.create=lost;turn=self.submit();self.run_turn(turn,'pending');self.restart()
        recovery=self.ok(self.host.recover_turns());self.assertIn(turn,recovery['committed_turn_ids'])
        self.assertEqual(self.get(turn)['status'],'committed');self.assertEqual(len(self.calls),1)
        self.ok(self.tasks.finish_startup());self.run_turn(turn);self.assertEqual(len(self.calls),1)

    def test_owner_absence_startup_interrupts_unknown_lookup_holds(self):
        self.proposal={'kind':'new_work','brief':self.draft()}
        self.tasks.create=lambda *a,**kw:Result.failure('unavailable','unknown')
        turn=self.submit();self.run_turn(turn,'pending');self.restart()
        lookup=self.tasks.get_create_by_key
        self.tasks.get_create_by_key=lambda req:Result.failure('unavailable','unknown')
        out=self.ok(self.host.recover_turns());self.assertIn(turn,out['held_turn_ids'])
        self.tasks.get_create_by_key=lookup
        out=self.ok(self.host.recover_turns());self.assertIn(turn,out['interrupted_turn_ids'])
        self.assertEqual(self.get(turn)['status'],'interrupted');self.assertEqual(len(self.calls),1)

    def test_skipped_pri_recovery_refuses_new_inference(self):
        turn=self.submit();self.restart();self.ok(self.tasks.finish_startup())
        self.error(self.host.run_turn({'turn_id':turn}),'conflict');self.assertEqual(self.calls,[])

    def test_caller_transaction_mutations_refuse_and_preserve_owned_write(self):
        work=self.work();ref=self.record();turn=self.submit()
        self.conn.execute('CREATE TABLE caller(value)');self.conn.execute('BEGIN')
        self.conn.execute('INSERT INTO caller VALUES(7)')
        self.error(self.host.submit({'client_key':'nested','session_id':'session','text':'x'}),'unavailable')
        self.error(self.host.run_turn({'turn_id':turn}),'unavailable')
        self.error(self.host.control({'client_key':'nested','session_id':'session','work_ref':work,'command':'cancel'}),'unavailable')
        self.error(self.host.stop_reference({'client_key':'nested','session_id':'session','source_ref':ref}),'unavailable')
        self.assertTrue(self.conn.in_transaction);self.assertEqual(self.conn.execute('SELECT * FROM caller').fetchall(),[(7,)])
        self.conn.rollback();self.assertEqual(self.calls,[])

    def test_baseexception_propagates_releases_activity_no_repeat(self):
        turn=self.submit()
        def abort(snap):
            with self.assertRaises(RuntimeError):self.guard.close()
            raise KeyboardInterrupt('PRIVATE_CANARY')
        self.hook=abort
        with self.assertRaises(KeyboardInterrupt):self.host.run_turn({'turn_id':turn})
        self.assertFalse(self.conn.in_transaction);self.assertEqual(len(self.calls),1)
        self.restart();out=self.ok(self.host.recover_turns());self.assertIn(turn,out['interrupted_turn_ids'])
        self.assertNotIn('PRIVATE_CANARY','\n'.join(self.snapshot()))

    def test_terminal_event_failure_rolls_back_terminal_then_startup_no_reapply(self):
        event=self.tasks.append_event
        def broken(conn,req):
            if loads(req['key'])[0]=='PRI01.turn':return Result.failure('unavailable','event unavailable')
            return event(conn,req)
        self.tasks.append_event=broken
        self.proposal={'kind':'new_work','brief':self.draft()};turn=self.submit();self.run_turn(turn,'pending')
        self.tasks.append_event=event;self.restart()
        out=self.ok(self.host.recover_turns());self.assertIn(turn,out['committed_turn_ids'])
        self.assertEqual(len(self.calls),1)

    def test_callback_exception_and_nontext_are_bounded_charged_failures(self):
        def broken(request):raise RuntimeError('PRIVATE_CANARY')
        self.host=self.make_host(invoke=broken);out=self.run_turn(self.submit(),'failed');self.assertNotIn('reply',out)
        self.assertEqual(self.used(),1);self.assertNotIn('PRIVATE_CANARY','\n'.join(self.snapshot()))
        self.host=self.make_host(invoke=lambda req:{'reply':'not text'});self.run_turn(self.submit(),'failed');self.assertEqual(self.used(),2)

    def test_closed_guard_and_ready_recover_refuse(self):
        turn=self.submit();self.error(self.host.recover_turns(),'conflict')
        self.guard.close();self.error(self.host.run_turn({'turn_id':turn}),'unavailable')
