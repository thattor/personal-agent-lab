"""Frozen RECOVERY02 acceptance with real managed HOST/MEM/ART/VER/TSK.

Owner exceptions/projections are injected only at the public ART collaborator;
no fake lifetime proof or external effect. Root owns process-death connection.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import sqlite3
import unittest
from pal.contracts_v5 import Grant, Limits, Result, Ref, dumps, loads
from pal.tasks_v5 import TaskStore
from pal.memory_v5 import MemoryStore
from pal.artifacts_v5 import ArtifactStore, artifact_save_key
from pal.verification_v5 import VerificationStore
import test_tasks_recovery_v5 as fixture
import test_tasks_ask_v5 as old_fixture


class ArtifactRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.mode='actual';self.calls=[];self.transform=None;self.no_lookup=False
        self.f=fixture.RecoveryTests()
        self.f.connect=lambda guard=None:self.connect(guard)
        self.f.setUp();self.addCleanup(self.f.doCleanups)

    def connect(self,guard=None):
        f=self.f;conn=sqlite3.connect(f.path,isolation_level=None,timeout=0,factory=old_fixture.FaultConnection)
        f.addCleanup(conn.close);mem=art=ver=None
        def lookup(connection,request):
            self.calls.append(copy.deepcopy(request))
            self.assertIs(connection,conn);self.assertTrue(conn.in_transaction)
            if self.mode=='exception':raise RuntimeError('private ART unavailable')
            if self.mode=='interrupt':raise KeyboardInterrupt('private lookup interrupted')
            if self.mode=='write':conn.execute('UPDATE v5_tsk_usage SET used=used+1')
            elif self.mode=='commit':conn.execute('COMMIT')
            elif self.mode=='rollback_begin':conn.execute('ROLLBACK');conn.execute('BEGIN IMMEDIATE')
            if self.mode in ('denied','unavailable','not_found','conflict','invalid_input'):
                return Result.failure(self.mode,'bounded ART failure')
            result=art.lookup_saved(connection,request)
            if self.transform is not None and result.ok:return self.transform(result)
            return result
        kwargs={'startup_guard':guard}
        if not self.no_lookup:kwargs['artifact_lookup']=lookup
        t=TaskStore(conn,host_grant=f.grant,host_limits=Limits(0,100,100),expert_id='expert',
            source_gate=lambda c,refs:mem.source_gate(c,refs),
            artifact_inspect=lambda c,r:art.inspect(c,r),verification_inspect=lambda c,r:ver.inspect(c,r),**kwargs)
        mem=MemoryStore(conn,sanitize_text=lambda x:x,append_event=t.append_event,invalidate_by_refs=t.invalidate_by_refs)
        art=ArtifactStore(conn,authorize_save=t.authorize_artifact_save,source_gate=mem.source_gate)
        ver=VerificationStore(conn,context=t.verification_context,artifact_inspect=art.inspect,source_gate=mem.source_gate)
        return conn,t,mem,art,ver

    def stage(self,saved=True):
        call,step=self.f.stage('compose');work=self.f.lease['work_ref']
        request={'key':artifact_save_key(work,step['step_id']),'work_ref':work,'step_id':step['step_id'],
                 **{k:v for k,v in step['action'].items() if k!='kind'}}
        receipt=self.f.value(self.f.art.save(request)) if saved else None
        self.call,self.step,self.save,self.receipt=call,step,request,receipt
        return step

    def restart(self):self.f.reopen();self.calls.clear()
    def recover(self,key='saved-recovery'):return self.f.recover(key=key)
    def settled(self,key='saved-recovery'):return self.f.settled(self.recover(key))
    def snapshot(self):return self.f.snapshot()
    def wire(self):return loads(self.f.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',(self.step['step_id'],)).fetchone()[0])
    def art_rows(self):
        return tuple((line,) for line in self.f.conn.iterdump() if line.startswith('INSERT INTO "v5_art_'))
    def assert_hold(self,result,before):
        value=self.f.value(result);self.assertEqual(value['disposition'],'held');self.assertEqual(value['reason'],'artifact_tail')
        self.assertEqual(value['step_id'],self.step['step_id']);self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.f.guard.phase,'startup');self.f.error(self.f.t.finish_startup(),'conflict')

    def test_adopt_once_original_step_exact_event_bindings_and_zero_new_charges(self):
        self.stage();original=copy.deepcopy(self.step);self.restart();before_usage=self.f.usage();art=self.art_rows();before_events=len(self.f.events())
        old_epoch=self.f.work()['work_ref']['epoch'];out=self.settled()
        self.assertEqual(out['state'],'queued');self.assertEqual(out['work_ref']['epoch'],old_epoch+1)
        self.assertEqual(self.wire(),{**original,'status':'finished','result_refs':[self.receipt['artifact_ref']]})
        self.assertEqual(self.f.work()['current_artifact_refs'],[self.receipt['artifact_ref']]);self.assertEqual(self.f.usage(),before_usage);self.assertEqual(self.art_rows(),art)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0],{'key':self.save['key'],'work_ref':self.save['work_ref'],'step_id':self.step['step_id'],'action':original['action']})
        events=self.f.events();self.assertEqual(len(events),before_events+1)
        self.assertEqual((events[-1]['kind'],events[-1]['text'],events[-1]['refs'],events[-1]['work_ref']),
            ('state','mock saved draft recovered',[self.receipt['artifact_ref']],out['work_ref']))
        rows=self.f.conn.execute('SELECT * FROM v5_tsk_recovery_adoption WHERE step_id=?',(self.step['step_id'],)).fetchall();self.assertEqual(len(rows),1)
        self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_tsk_artifact_set').fetchone()[0],1)
        self.assertEqual(self.f.conn.execute("SELECT COUNT(*) FROM v5_intake_replay WHERE command='recover' AND key='saved-recovery'").fetchone()[0],1)

    def test_replay_historical_receipt_no_relookup_or_writes_and_changed_input_conflicts(self):
        self.stage();self.restart();out=self.settled();before=self.snapshot();calls=len(self.calls)
        self.assertEqual(self.f.value(self.recover()),out);self.assertEqual(self.snapshot(),before);self.assertEqual(len(self.calls),calls)
        self.f.error(self.f.t.recover({'key':'saved-recovery','lease_id':'other'}),'conflict');self.assertEqual(self.snapshot(),before)
        self.f.value(self.f.t.finish_startup());self.f.lease=self.f.value(self.f.t.claim({'runner_id':self.f.guard.runner_id}))
        self.restart();before=self.snapshot();self.assertEqual(self.f.value(self.recover()),out);self.assertEqual(self.snapshot(),before)

    def test_exhausted_goal_and_host_budget_still_adopts_without_refund(self):
        self.stage();self.restart()
        self.f.conn.execute('UPDATE v5_tsk_host SET ceiling=used')
        row=self.f.conn.execute('SELECT grant_json FROM v5_intake_work WHERE goal_id=?',(self.f.goal,)).fetchone()[0]
        grant=loads(row);used=dict(self.f.conn.execute('SELECT kind,used FROM v5_tsk_usage WHERE goal=?',(self.f.goal,)).fetchall())
        grant['limits']['max_model_calls']=used.get('model',0);grant['limits']['max_steps']=used.get('step',0)
        self.f.conn.execute('UPDATE v5_intake_work SET grant_json=? WHERE goal_id=?',(dumps(grant),self.f.goal))
        usage=self.f.usage();self.settled();self.assertEqual(self.f.usage(),usage)
        self.f.value(self.f.t.finish_startup());self.f.error(self.f.t.claim({'runner_id':self.f.guard.runner_id}),'limit')

    def test_actual_definitive_absence_abandons_without_save(self):
        self.stage(False);self.restart();usage=self.f.usage();out=self.settled()
        self.assertEqual(out['state'],'queued');self.assertEqual(self.wire()['status'],'abandoned');self.assertEqual(self.wire()['result_refs'],[])
        self.assertEqual(self.f.work()['current_artifact_refs'],[]);self.assertEqual(self.f.usage(),usage)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_tsk_recovery_adoption').fetchone()[0],0)
        self.assertEqual(self.f.events()[-1]['text'],'mock execution recovered')

    def test_uncertain_owner_outcomes_hold_then_same_key_can_adopt(self):
        for mode in ('unavailable','denied','conflict','invalid_input','exception'):
            with self.subTest(mode=mode):
                self.setUp();self.stage();self.restart();self.mode=mode;before=self.snapshot();self.assert_hold(self.recover(),before)
                self.mode='actual';self.settled();self.assertEqual(self.wire()['status'],'finished')

    def test_source_gate_uncertainty_holds_before_art_lookup_then_retry(self):
        for code in ('not_found','unavailable'):
            with self.subTest(code=code):
                self.setUp();self.stage();self.restart();gate=self.f.t._source_gate
                self.f.t._source_gate=lambda c,refs:Result.failure(code,'bounded source check')
                before=self.snapshot();self.assert_hold(self.recover(),before);self.assertEqual(self.calls,[])
                self.f.t._source_gate=gate;self.settled()

    def test_latest_pause_cancel_replacement_or_source_denial_abandons_without_lookup(self):
        for intent in ('pause','cancel','change','source_stop'):
            with self.subTest(intent=intent):
                self.setUp();self.stage();correction=self.f.record('replacement');self.restart()
                _,controller,mem,_,_=self.f.connect()
                if intent=='source_stop':self.f.value(mem.stop_reference({'key':self.f.key(),'source_ref':self.f.optional},session_id='control'))
                else:
                    command={'kind':'change','brief':self.f.draft,'origin_record_ref':correction} if intent=='change' else intent
                    self.f.value(controller.control({'key':self.f.key(),'work_ref':self.f.work()['work_ref'],'command':command}))
                out=self.settled();self.assertEqual(self.calls,[]);self.assertEqual(self.wire()['status'],'abandoned')
                self.assertEqual(self.f.work()['current_artifact_refs'],[])
                self.assertEqual(out['state'],'paused' if intent=='pause' else 'cancelled' if intent=='cancel' else 'queued')
                self.assertEqual(self.f.value(self.f.art.get_by_key({'key':self.save['key']})),self.receipt)

    def test_same_revision_drain_is_eligible_but_lookup_gets_original_claim(self):
        unused=self.f.record('unused optional source')
        self.f.value(self.f.t.register_sources({'work_ref':self.f.lease['work_ref'],'refs':[unused]}))
        self.stage();self.restart();self.f.value(self.f.mem.stop_reference({'key':self.f.key(),'source_ref':unused},session_id='control'))
        self.assertEqual(self.f.conn.execute('SELECT drain FROM v5_tsk_control WHERE goal=? AND revision=1',(self.f.goal,)).fetchone()[0],1)
        out=self.settled();self.assertEqual(self.calls[0]['work_ref'],self.step['work_ref'])
        self.assertGreater(out['work_ref']['epoch'],self.step['work_ref']['epoch']);self.assertEqual(self.wire()['status'],'finished')

    def test_no_lookup_collaborator_preserves_legacy_hold(self):
        self.stage();self.no_lookup=True;self.restart();before=self.snapshot();self.assert_hold(self.recover(),before);self.assertEqual(self.calls,[])

    def test_malformed_lookup_projection_hold_zero_writes(self):
        cases=('extra','wrong_work','wrong_step','reversed_sources','duplicate_sources','missing_source','wrong_kind','bad_hash','bool_bytes')
        for case in cases:
            with self.subTest(case=case):
                self.setUp();self.stage();self.restart()
                def change(result):
                    value=result.value.to_json()
                    if case=='extra':value['content']='private body'
                    elif case=='wrong_work':value['work_ref']={**value['work_ref'],'epoch':value['work_ref']['epoch']+1}
                    elif case=='wrong_step':value['step_id']='foreign'
                    elif case=='reversed_sources':value['source_refs']=list(reversed(value['source_refs']))
                    elif case=='duplicate_sources':value['source_refs']+=[value['source_refs'][0]]
                    elif case=='missing_source':value['source_refs']=value['source_refs'][:1]
                    elif case=='wrong_kind':value['artifact_ref']={'kind':'record','id':'foreign'}
                    elif case=='bad_hash':value['hash']='invalid'
                    else:value['bytes']=False
                    return Result.success(value)
                self.transform=change;before=self.snapshot();self.assert_hold(self.recover(),before)

    def test_started_compose_result_error_or_provenance_corruption_refuses_before_lookup(self):
        for case in ('result','error','duplicate_call_sources','missing_required','call_work','call_status'):
            with self.subTest(case=case):
                self.setUp();self.stage();self.restart()
                if case in ('result','error'):
                    wire=self.wire()
                    if case=='result':wire['result_refs']=[self.receipt['artifact_ref']]
                    else:wire['error']='unexpected'
                    self.f.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?',(dumps(wire),self.step['step_id']))
                elif case in ('duplicate_call_sources','missing_required'):
                    refs=[self.f.origin,self.f.origin] if case=='duplicate_call_sources' else [self.f.optional]
                    self.f.conn.execute('UPDATE v5_tsk_call SET sources=? WHERE id=?',(dumps(refs),self.call))
                elif case=='call_work':self.f.conn.execute('UPDATE v5_tsk_call SET work=? WHERE id=?',(dumps({**self.step['work_ref'],'epoch':self.step['work_ref']['epoch']+1}),self.call))
                else:self.f.conn.execute("UPDATE v5_tsk_call SET status='raised' WHERE id=?",(self.call,))
                before=self.snapshot();self.f.error(self.recover(),'unavailable');self.assertEqual(self.snapshot(),before);self.assertEqual(self.calls,[])

    def test_adoption_annotation_set_event_or_generic_replay_damage_fail_closed(self):
        for case in ('delete_adoption','delete_set','delete_event','delete_replay','adoption_work','event_ref','replay_receipt'):
            with self.subTest(case=case):
                self.setUp();self.stage();self.restart();out=self.settled()
                if case=='delete_adoption':self.f.conn.execute('DELETE FROM v5_tsk_recovery_adoption')
                elif case=='delete_set':self.f.conn.execute('DELETE FROM v5_tsk_artifact_set')
                elif case=='delete_event':self.f.conn.execute("DELETE FROM v5_intake_event WHERE text='mock saved draft recovered'")
                elif case=='delete_replay':self.f.conn.execute("DELETE FROM v5_intake_replay WHERE command='recover' AND key='saved-recovery'")
                elif case=='adoption_work':self.f.conn.execute('UPDATE v5_tsk_recovery_adoption SET adopted_work_json=?',(dumps({**out['work_ref'],'epoch':out['work_ref']['epoch']+1}),))
                elif case=='event_ref':self.f.conn.execute("UPDATE v5_intake_event SET refs_json='[]' WHERE text='mock saved draft recovered'")
                else:self.f.conn.execute("UPDATE v5_intake_replay SET result_json=? WHERE command='recover' AND key='saved-recovery'",(dumps(Result.success({**out,'state':'completed'})),))
                before=self.snapshot();self.f.error(self.recover(),'unavailable');self.assertEqual(self.snapshot(),before)
                self.f.error(self.f.t.get_work({'goal_id':self.f.goal}),'unavailable');self.assertEqual(self.snapshot(),before)

    def test_recovery_internal_binding_deletion_detected_without_private_table_name(self):
        self.stage();self.restart();self.settled()
        candidates=[]
        for name, in self.f.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            if name.startswith('v5_tsk_') and name!='v5_tsk_recovery_adoption':
                fields={r[1] for r in self.f.conn.execute('PRAGMA table_info('+name+')').fetchall()}
                if {'recover_key','adopted_step_id','event_id'}<=fields:candidates.append(name)
        self.assertEqual(len(candidates),1,'frozen recovery replay binding must be inspectable')
        self.f.conn.execute('DELETE FROM '+candidates[0]);before=self.snapshot();self.f.error(self.recover(),'unavailable');self.assertEqual(self.snapshot(),before)
        self.f.error(self.f.t.get_work({'goal_id':self.f.goal}),'unavailable')

    def test_ordinary_finished_compose_without_recovery_annotations_stays_valid(self):
        self.stage();work=self.f.lease['work_ref'];finished=self.f.value(self.f.t.finish_step({'work_ref':work,'step_id':self.step['step_id'],'result_refs':[self.receipt['artifact_ref']]}))
        self.assertEqual(self.f.work()['current_artifact_refs'],[self.receipt['artifact_ref']]);self.restart();self.settled()
        self.assertEqual(self.wire(),finished);self.assertEqual(self.f.conn.execute('SELECT COUNT(*) FROM v5_tsk_recovery_adoption').fetchone()[0],0)

    def test_callback_mutation_transaction_replacement_or_interrupt_never_adopts(self):
        for mode in ('write','commit','rollback_begin','interrupt'):
            with self.subTest(mode=mode):
                self.setUp();self.stage();self.restart();before=self.snapshot();self.mode=mode
                if mode=='interrupt':
                    with self.assertRaises(KeyboardInterrupt):self.recover()
                else:
                    result=self.recover();self.assertTrue(not result.ok or result.value.to_json()['disposition']=='held')
                self.assertEqual(self.snapshot(),before);self.assertFalse(self.f.conn.in_transaction)
                self.mode='actual';self.settled()

    def test_premint_and_postwrite_faults_roll_back_adoption_and_replay(self):
        for failure in (RuntimeError,KeyboardInterrupt):
            with self.subTest(failure=failure):
                self.setUp();self.stage();self.restart();before=self.snapshot();self.f.conn.fault=failure;self.f.conn.writes_until_fault=1
                if failure is KeyboardInterrupt:
                    with self.assertRaises(KeyboardInterrupt):self.recover()
                else:self.f.error(self.recover(),'unavailable')
                self.assertEqual(self.snapshot(),before);self.assertFalse(self.f.conn.in_transaction);self.settled()
        self.setUp();self.stage();self.restart();before=self.snapshot();original=self.f.t._id_factory
        self.f.t._id_factory=lambda prefix: (_ for _ in ()).throw(RuntimeError('private mint failure'))
        try:self.f.error(self.recover(),'unavailable')
        finally:self.f.t._id_factory=original
        self.assertEqual(self.snapshot(),before);self.settled()

    def test_fresh_verification_can_use_recovered_artifact_old_epoch_cannot_complete(self):
        self.stage();old_work=self.f.lease['work_ref'];old_ref=self.receipt['artifact_ref']
        self.f.value(self.f.t.finish_step({'work_ref':old_work,'step_id':self.step['step_id'],'result_refs':[old_ref]}))
        old_ver=self.f.value(self.f.ver.verify({'key':dumps(['C09.verify',old_work,[old_ref]]),'work_ref':old_work,'artifact_refs':[old_ref]}))
        self.stage();new_ref=self.receipt['artifact_ref'];self.restart();self.settled();self.f.value(self.f.t.finish_startup())
        self.f.lease=self.f.value(self.f.t.claim({'runner_id':self.f.guard.runner_id}));work=self.f.lease['work_ref']
        before=self.snapshot();self.f.error(self.f.t.control({'key':self.f.key(),'work_ref':work,
            'command':{'kind':'complete','verification_ref':old_ver['verification_ref']}}),'stale');self.assertEqual(self.snapshot(),before)
        refs=[old_ref,new_ref];self.assertEqual(self.f.work()['current_artifact_refs'],refs)
        checked=self.f.value(self.f.ver.verify({'key':dumps(['C09.verify',work,refs]),'work_ref':work,'artifact_refs':refs}))
        self.assertTrue(all(c['status']=='met' for c in checked['checks']))
        self.f.value(self.f.t.control({'key':self.f.key(),'work_ref':work,'command':{'kind':'complete','verification_ref':checked['verification_ref']}}))
        self.assertEqual(self.f.work()['state'],'completed')

    def test_terminal_or_paused_saved_intent_abandons_without_new_lookup(self):
        for state in ('completed','failed','paused'):
            with self.subTest(state=state):
                self.setUp();self.stage();self.restart()
                # Frozen recovery defines these persisted intents; this is no
                # claim that a started draft satisfies ordinary completion.
                self.f.conn.execute('UPDATE v5_intake_work SET state=? WHERE goal_id=?',(state,self.f.goal))
                epoch=self.f.work()['work_ref']['epoch'];out=self.settled()
                self.assertEqual(out['state'],state);self.assertEqual(self.calls,[]);self.assertEqual(self.wire()['status'],'abandoned')
                self.assertEqual(out['work_ref']['epoch'],epoch if state in ('completed','failed') else epoch+1)

    def test_tsk_gates_full_producer_union_once_before_art_lookup(self):
        self.stage();self.restart();gate=self.f.t._source_gate;seen=[]
        def observed(conn,refs):
            seen.append(refs);self.assertEqual(self.calls,[]);return gate(conn,refs)
        self.f.t._source_gate=observed;self.settled()
        self.assertEqual(seen,[(Ref.from_json(self.f.origin),Ref.from_json(self.f.optional))]);self.assertEqual(len(self.calls),1)

    def test_constructor_rejects_noncallable_lookup(self):
        conn=sqlite3.connect(':memory:',isolation_level=None);self.addCleanup(conn.close)
        with self.assertRaises((TypeError,ValueError)):
            TaskStore(conn,host_grant=self.f.grant,host_limits=Limits(0,100,100),expert_id='expert',
                source_gate=self.f.mem.source_gate,artifact_lookup=False)


if __name__=='__main__':unittest.main()
