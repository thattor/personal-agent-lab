"""PRI03 fixed TSK owner behavior; typed fixture endings are not native proof."""
import copy
import hashlib
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.contracts_v5 import Result,dumps,loads
from pal.native_call_v5 import NativeNeverEntered,NativeProfile
from native_expert_fixtures_v5 import NativeFixture


class NativeTasksTests(unittest.TestCase):
    def fixture(self):return NativeFixture(self)
    def ok(self,result):
        self.assertIs(type(result),Result);self.assertTrue(result.ok,result.to_json());return result.value.to_json()
    def refused(self,result,code=None):
        self.assertIs(type(result),Result);self.assertFalse(result.ok,result.to_json())
        if code:self.assertEqual(result.error.code.value,code)
        self.assertNotIn('RAW_NATIVE_CANARY',result.error.message);self.assertLess(len(result.error.message),160)
    def ended(self,n):self.ok(n.admit());self.ok(n.enter());self.ok(n.end())
    def test_admission_receipt_replay_native_shape_and_no_extra_budget(self):
        n=self.fixture();n.prepare();used=n.f.usage();expected={'call_id':n.call_id,'status':'admitted'}
        self.assertEqual(self.ok(n.admit()),expected)
        after=n.f.usage();self.assertEqual(after[:2],used[:2])
        self.assertEqual(len(after[2]),len(used[2]))
        for original,current in zip(used[2],after[2]):
            self.assertEqual(current[:-1],original[:-1])
            if original[0]==n.admission['reservation_id']:
                self.assertIsNone(original[-1]);self.assertEqual(current[-1],n.call_id)
            else:self.assertEqual(current,original)
        before=n.f.snapshot();self.assertEqual(self.ok(n.admit()),expected);self.assertEqual(n.f.snapshot(),before)
        call=self.ok(n.t.get_call({'call_id':n.call_id}))
        self.assertEqual(call['profile_id'],'co-devin-acp-dynamic-text/1');self.assertEqual(call['native_phase'],'prepared')
        self.assertIs(call['may_enter'],False);self.assertNotIn('content',call)
    def test_admission_closed_request_profile_and_binding_rejection(self):
        variants=({'role':'primary'},{'output_kind':'primary_proposal'},{'index':False},
                  {'call_id':'foreign'},{'reservation_id':'foreign'},{'source_refs':[]},
                  {'work_ref':{'goal_id':'other','revision':1,'epoch':1}},
                  {'messages':[{'role':'user','text':'x','extra':1}]},
                  {'messages':[{'role':'user','text':'x'*65536}]})
        for change in variants:
            with self.subTest(change=list(change)):
                n=self.fixture();n.prepare();request={**copy.deepcopy(n.request),**change};before=n.f.snapshot()
                self.refused(n.t.admit_native_call(n.admission,c15_request=request,profile=n.profile))
                self.assertEqual(n.f.snapshot(),before)
        n=self.fixture();n.prepare();before=n.f.snapshot()
        self.refused(n.t.admit_native_call(n.admission,c15_request=n.request,profile=n.profile.to_json()))
        self.assertEqual(n.f.snapshot(),before)
    def test_admission_changed_original_body_or_profile_conflicts(self):
        n=self.fixture();self.ok(n.admit());before=n.f.snapshot()
        request=copy.deepcopy(n.request);request['messages'][0]['text']='different'
        self.refused(n.t.admit_native_call(n.admission,c15_request=request,profile=n.profile),'conflict')
        other=NativeProfile(model_id='swe-2-high',qualification_sha256='9'*64,evidence_kind='fixture')
        self.refused(n.t.admit_native_call(n.admission,c15_request=n.request,profile=other),'conflict')
        self.assertEqual(n.f.snapshot(),before)
    def test_duplicate_entry_is_not_dispatch_permission(self):
        n=self.fixture();self.ok(n.admit());self.assertEqual(self.ok(n.enter()),{'call_id':n.call_id,'status':'entered'})
        before=n.f.snapshot();self.refused(n.enter(),'conflict');self.assertEqual(n.f.snapshot(),before)
        self.assertEqual(self.ok(n.t.get_call({'call_id':n.call_id}))['native_phase'],'entering')
    def test_pause_cancel_and_full_optional_stop_before_entry_fence(self):
        for command in ('pause','cancel','stop'):
            with self.subTest(command=command):
                n=self.fixture();self.ok(n.admit())
                self.ok(n.stop() if command=='stop' else n.control(command));before=n.f.snapshot()
                self.refused(n.enter());self.assertEqual(n.f.snapshot(),before)
                self.refused(n.release());self.assertEqual(n.f.snapshot(),before)
    def test_original_ending_after_control_preserved_but_raw_and_step_fenced(self):
        for command in ('pause','cancel','stop'):
            with self.subTest(command=command):
                n=self.fixture();self.ok(n.admit());self.ok(n.enter())
                self.ok(n.stop() if command=='stop' else n.control(command));self.ok(n.end())
                before=n.f.snapshot();self.refused(n.output());self.refused(n.begin());self.assertEqual(n.f.snapshot(),before)
                result=self.ok(n.release());self.assertEqual(result['state'],'cancelled' if command=='cancel' else 'paused' if command=='pause' else 'queued')
    def test_raw_exact_current_replay_and_ending_idempotence(self):
        n=self.fixture();self.ended(n);before=n.f.snapshot()
        expected={'call_id':n.call_id,'status':'succeeded','content':dumps(n.action),'model_id':'swe-2-high'}
        self.assertEqual(self.ok(n.output()),expected);self.assertEqual(self.ok(n.end()),{'call_id':n.call_id,'status':'returned'})
        self.assertEqual(n.f.snapshot(),before)
        self.refused(n.end(n.returned(text=dumps({'kind':'report','summary':'changed'}))),'conflict')
        self.assertEqual(n.f.snapshot(),before)
    def test_foreign_attempt_request_and_profile_endings_do_not_write(self):
        for field in ('attempt','request','profile'):
            with self.subTest(field=field):
                n=self.fixture();self.ok(n.admit());self.ok(n.enter())
                kwargs={'attempt':{**n.attempt,'attempt_id':'foreign'}} if field=='attempt' else (
                    {'request':{**n.request,'call_id':'foreign'}} if field=='request' else
                    {'profile':NativeProfile(model_id='swe-2-high',qualification_sha256='9'*64,evidence_kind='fixture')})
                before=n.f.snapshot();self.refused(n.end(n.returned(**kwargs)));self.assertEqual(n.f.snapshot(),before)
    def test_never_entered_requires_exact_typed_binding_and_replays(self):
        n=self.fixture();self.ok(n.admit())
        receipt=NativeNeverEntered(request_sha256=hashlib.sha256(dumps(n.request).encode()).hexdigest(),
            profile_sha256=n.profile.profile_sha256,evidence_ref='fixture:original-refusal')
        wrong=NativeNeverEntered(request_sha256='0'*64,profile_sha256=n.profile.profile_sha256,evidence_ref='fixture:wrong')
        before=n.f.snapshot();self.refused(n.end(wrong));self.assertEqual(n.f.snapshot(),before)
        self.assertEqual(self.ok(n.end(receipt)),{'call_id':n.call_id,'status':'not_entered'})
        before=n.f.snapshot();self.ok(n.end(receipt));self.assertEqual(n.f.snapshot(),before);self.refused(n.output())
        self.ok(n.release())
    def test_unknown_idempotent_never_ends_or_releases(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter())
        expected={'call_id':n.call_id,'status':'admitted','phase':'unknown'}
        self.assertEqual(self.ok(n.t.mark_native_unknown({'call_id':n.call_id})),expected)
        before=n.f.snapshot();self.assertEqual(self.ok(n.t.mark_native_unknown({'call_id':n.call_id})),expected)
        self.refused(n.output());self.refused(n.begin());self.refused(n.release());self.assertEqual(n.f.snapshot(),before)
    def test_string_end_call_cannot_downgrade_native(self):
        n=self.fixture();self.ok(n.admit());before=n.f.snapshot()
        for outcome in ('returned','raised','not_entered'):
            self.refused(n.t.end_call({'call_id':n.call_id,'outcome':outcome}))
        self.refused(n.t.admit_call(n.admission));self.assertEqual(n.f.snapshot(),before)
    def test_prepared_entering_unknown_startup_holds_zero_settlement(self):
        for phase in ('prepared','entering','unknown'):
            with self.subTest(phase=phase):
                n=self.fixture();self.ok(n.admit())
                if phase!='prepared':self.ok(n.enter())
                if phase=='unknown':self.ok(n.t.mark_native_unknown({'call_id':n.call_id}))
                n.f.reopen();before=n.f.snapshot();out=self.ok(n.f.recover())
                self.assertEqual(out['disposition'],'held');self.assertNotIn('RAW_NATIVE_CANARY',dumps(out))
                self.assertEqual(n.f.snapshot(),before);self.refused(n.t.finish_startup());self.assertEqual(n.f.snapshot(),before)
                self.assertEqual(self.ok(n.t.get_call({'call_id':n.call_id}))['status'],'admitted')
                self.ok(n.control('cancel'));self.refused(n.release())
    def test_returned_without_step_recovery_preserves_raw_but_not_new_epoch_reuse(self):
        n=self.fixture();self.ended(n);n.f.reopen();out=self.ok(n.f.recover())
        self.assertEqual(out['disposition'],'settled');self.assertEqual(out['interrupted_call_ids'],[])
        self.ok(n.t.finish_startup());self.refused(n.output());self.assertEqual(self.ok(n.t.get_call({'call_id':n.call_id}))['status'],'returned')
        self.assertEqual(out['state'],'queued')
    def test_begin_step_must_match_original_raw_action(self):
        n=self.fixture();self.ended(n);before=n.f.snapshot()
        self.refused(n.begin({'kind':'report','summary':'different'}));self.assertEqual(n.f.snapshot(),before)
        step=self.ok(n.begin());self.assertEqual(step['action'],n.action);self.assertEqual(step['status'],'started')
    def test_known_ended_malformed_action_cannot_be_repaired_in_memory(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter());self.ok(n.end(n.returned(text='not JSON')))
        self.assertEqual(self.ok(n.output())['content'],'not JSON');before=n.f.snapshot()
        self.refused(n.begin());self.assertEqual(n.f.snapshot(),before);self.ok(n.release('failed'))
    def test_same_transaction_postwrite_fault_rolls_back_admission_entry_and_ending(self):
        for operation in ('admit','enter','end'):
            for failure in (RuntimeError,KeyboardInterrupt):
                with self.subTest(operation=operation,failure=failure.__name__):
                    n=self.fixture();n.prepare()
                    if operation!='admit':self.ok(n.admit())
                    if operation=='end':self.ok(n.enter())
                    before=n.f.snapshot();n.f.conn.fault=failure;n.f.conn.writes_until_fault=2
                    if failure is KeyboardInterrupt:
                        with self.assertRaises(KeyboardInterrupt):getattr(n,operation)()
                    else:self.refused(getattr(n,operation)())
                    self.assertFalse(n.f.conn.in_transaction);self.assertEqual(n.f.snapshot(),before)
                    self.ok(getattr(n,operation)())
    def test_ending_commit_reply_loss_replays_without_additional_usage(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter());ending=n.returned();used=n.f.usage()
        original=n.t.end_native_call
        def lost(request,*,ending):
            self.ok(original(request,ending=ending));return Result.failure('unavailable','fixture lost response')
        self.refused(lost({'call_id':n.call_id},ending=ending),'unavailable')
        self.ok(original({'call_id':n.call_id},ending=ending));self.assertEqual(n.f.usage(),used)
        self.assertEqual(self.ok(n.output())['content'],dumps(n.action))
    def test_two_connections_only_one_entry_wins(self):
        n=self.fixture();self.ok(n.admit());barrier=threading.Barrier(2);out=[];errors=[]
        connections=[n.connect_owned() for _ in range(2)]
        for conn,*_ in connections:self.addCleanup(conn.close)
        def worker(owners):
            conn,t,mem,art,ver=owners
            try:
                barrier.wait(3)
                out.append(t.enter_native_call({'call_id':n.call_id,'attempt_ref':copy.deepcopy(n.attempt)}))
            except BaseException as exc:errors.append(exc)
            finally:
                if conn:conn.close()
        threads=[threading.Thread(target=worker,args=(owners,)) for owners in connections]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(errors,[]);self.assertEqual(len(out),2);self.assertEqual(sum(r.ok for r in out),1)
        self.assertEqual(self.ok(n.t.get_call({'call_id':n.call_id}))['native_phase'],'entering')
    def test_corrupt_base_index_or_sources_blocks_all_ended_consumers_without_writes(self):
        for column,bad in (('idx',-1),('sources','{}'),('reservation','foreign')):
            with self.subTest(column=column):
                n=self.fixture();self.ended(n)
                n.f.conn.execute('UPDATE v5_tsk_call SET '+column+'=? WHERE id=?',(bad,n.call_id));before=n.f.snapshot()
                for result in (n.t.get_call({'call_id':n.call_id}),n.output(),n.begin(),n.release()):self.refused(result,'unavailable')
                self.assertEqual(n.f.snapshot(),before)

    def test_reserved_last_model_unit_admits_without_new_charge_step_debits_once(self):
        n=self.fixture()
        # Disposable counter boundary; no provider or 99 fabricated call records.
        n.f.conn.execute("UPDATE v5_tsk_host SET used=99 WHERE kind='model'")
        n.prepare();self.assertEqual(n.f.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0],100)
        self.ok(n.admit());self.ok(n.enter());self.ok(n.end());before=n.f.usage();step=self.ok(n.begin())
        self.assertEqual(n.f.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0],100)
        self.assertEqual(step['index'],0)
        self.ok(n.t.finish_step({'work_ref':n.work,'step_id':step['step_id'],'result_refs':[]}))
        self.assertNotEqual(n.f.usage(),before)

    def test_end_evidence_cap_and_plain_model_mapping_are_not_authority(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter());before=n.f.snapshot()
        self.refused(n.end({'text':dumps(n.action),'verified':True}))
        oversized=n.returned(extra={'fixture_optional':'x'*65536})
        self.refused(n.end(oversized));self.assertEqual(n.f.snapshot(),before)

    def test_change_then_latest_pause_or_cancel_wins_old_ended_release(self):
        for command in ('pause','cancel'):
            with self.subTest(command=command):
                n=self.fixture();self.ok(n.admit());self.ok(n.enter())
                changed=self.ok(n.control({'kind':'change','brief':copy.deepcopy(n.f.draft),'origin_record_ref':n.f.optional}))
                self.ok(n.t.control({'key':n.f.key(),'work_ref':changed['work_ref'],'command':command}))
                self.ok(n.end());self.refused(n.output());out=self.ok(n.release())
                self.assertEqual(out['state'],'paused' if command=='pause' else 'cancelled')

    def test_completed_step_replay_and_context_require_intact_native_producer(self):
        n=self.fixture();self.ended(n);step=self.ok(n.begin())
        request={'work_ref':n.work,'step_id':step['step_id'],'result_refs':[]}
        self.ok(n.t.finish_step(request));n.f.conn.execute("UPDATE v5_tsk_call SET sources='{}' WHERE id=?",(n.call_id,))
        before=n.f.snapshot()
        self.refused(n.t.finish_step(request),'unavailable')
        self.refused(n.t.get_execution_context({'lease_id':n.f.lease['lease_id'],'work_ref':n.work}),'unavailable')
        self.assertEqual(n.f.snapshot(),before)

    def test_same_ready_session_unknown_expert_does_not_forbid_primary_reserve(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter())
        self.ok(n.t.mark_native_unknown({'call_id':n.call_id}))
        reservation=self.ok(n.t.reserve_budget({'key':n.f.key(),'kind':'model','role':'primary'}))
        self.ok(n.t.consume({'reservation_id':reservation['reservation_id'],'call_or_operation_id':'fixture-primary-call'}))
        self.refused(n.release())
        self.assertEqual(self.ok(n.t.get_call({'call_id':n.call_id}))['native_phase'],'unknown')

    def test_foreign_reopened_session_cannot_record_original_ending_or_entry(self):
        n=self.fixture();self.ok(n.admit());self.ok(n.enter());ending=n.returned();n.f.reopen();before=n.f.snapshot()
        self.refused(n.end(ending));self.refused(n.enter());self.assertEqual(n.f.snapshot(),before)
