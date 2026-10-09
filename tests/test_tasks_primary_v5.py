"""PRI01-TSK fixed prerequisites, real owners and disposable managed SQLite."""
import copy
import sqlite3
import unittest
from unittest.mock import patch
from pal.contracts_v5 import Limits, Result, dumps, loads
from pal.tasks_v5 import TaskStore
import test_tasks_recovery_v5 as fixture

class PrimaryTaskTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.RecoveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.t,self.conn=self.f.t,self.f.conn
    def value(self,r):return self.f.value(r)
    def error(self,r,code):self.f.error(r,code)
    def snapshot(self):return self.f.snapshot()
    def candidates(self,**kw):return self.t.list_candidates({'session_id':'reader','limit':20,**kw})
    def primary(self,key='primary'):return self.t.reserve_budget({'key':key,'kind':'model','role':'primary'})
    def consume(self,r,identity='turn-one'):return self.t.consume({'reservation_id':r['reservation_id'],'call_or_operation_id':identity})
    def ceiling(self,n):self.conn.execute("UPDATE v5_tsk_host SET ceiling=used+? WHERE kind='model'",(n,))
    def create(self,key='new',session='other',purpose='別の依頼'):
        req={'key':key,'session_id':session,'origin_record_ref':self.f.origin,'brief':{**copy.deepcopy(self.f.draft),'purpose':purpose}}
        return req,self.value(self.t.create(req,request_scope=self.f.grant))
    def release(self):return self.value(self.t.release({'lease_id':self.f.lease['lease_id'],'work_ref':self.f.lease['work_ref'],'outcome':'yield','reason':'idle'}))
    def control(self,command,key='control',work=None):
        req={'key':key,'work_ref':work or self.f.work()['work_ref'],'command':command}
        return req,self.value(self.t.control(req))
    def stop(self,ref):return self.value(self.f.mem.stop_reference({'key':self.f.key(),'source_ref':ref},session_id='stopper'))
    def test_candidates_closed_shape_cross_session_order_terminal_and_empty_filter(self):
        req,new=self.create();self.release();self.control('cancel',work=new['work_ref'])
        before=self.snapshot();out=self.value(self.candidates(limit=1))
        self.assertEqual(set(out),{'works','truncated'});self.assertTrue(out['truncated']);self.assertEqual(len(out['works']),1)
        entry=out['works'][0];self.assertEqual(set(entry),{'work_ref','brief_summary','expert_id','state','open_questions','dependency_refs','text_withheld'})
        self.assertEqual((entry['work_ref']['goal_id'],entry['state'],entry['brief_summary']), (new['work_ref']['goal_id'],'cancelled','別の依頼'))
        self.assertEqual(entry['dependency_refs'],[self.f.origin]);self.assertFalse(entry['text_withheld'])
        self.assertEqual(self.value(self.candidates(goal_ids=[])),{'works':[],'truncated':False});self.assertEqual(self.snapshot(),before)
    def test_candidates_latest_revision_and_safe_japanese_prefix(self):
        text='日'*400;origin=self.f.record('correction')
        self.control({'kind':'change','origin_record_ref':origin,'brief':{**self.f.draft,'purpose':text}})
        out=self.value(self.candidates(goal_ids=[self.f.goal]));entry=out['works'][0]
        self.assertEqual(len(out['works']),1);self.assertEqual(entry['work_ref']['revision'],2)
        self.assertEqual(entry['brief_summary'],'日'*170);self.assertLessEqual(len(entry['brief_summary'].encode()),512)
    def test_candidates_full_registered_refs_withheld_after_optional_stop(self):
        self.value(self.t.register_sources({'work_ref':self.f.lease['work_ref'],'refs':[self.f.optional,self.f.origin]}))
        self.stop(self.f.optional);before=self.snapshot();entry=self.value(self.candidates())['works'][0]
        self.assertEqual(entry['brief_summary'],'');self.assertTrue(entry['text_withheld']);self.assertEqual(entry['dependency_refs'],[self.f.origin,self.f.optional]);self.assertEqual(self.snapshot(),before)
    def test_candidates_ask_question_and_full_producer_dependencies(self):
        _,step=self.f.stage('ask');a=step['action'];self.value(self.t.ask({'key':'ask','work_ref':step['work_ref'],'step_id':step['step_id'],**{k:v for k,v in a.items() if k!='kind'}}))
        entry=self.value(self.candidates())['works'][0];self.assertEqual(entry['open_questions'][0]['text'],a['question']);self.assertEqual(entry['dependency_refs'],[self.f.origin,self.f.optional])
        original=self.t._source_gate
        try:
            self.t._source_gate=lambda c,r:'not_found'
            hidden=self.value(self.candidates())['works'][0];self.assertEqual(hidden['open_questions'][0]['text'],'');self.assertTrue(hidden['text_withheld'])
            self.assertEqual(hidden['open_questions'][0]['id'],entry['open_questions'][0]['id'])
        finally:self.t._source_gate=original
    def test_candidates_strict_input_and_query_not_silently_ignored(self):
        before=self.snapshot()
        for kw in ({'limit':True},{'limit':0},{'limit':21},{'session_id':''},{'goal_ids':['a','a']},{'goal_ids':[1]},{'extra':1},{'goal_ids':['a']*21}):
            with self.subTest(kw=kw):self.error(self.candidates(**kw),'invalid_input')
        self.error(self.candidates(query='text'),'unavailable');self.assertEqual(self.snapshot(),before)
    def test_candidates_read_transaction_and_gate_failures(self):
        original=self.t._source_gate
        for mode in ('denied','not_found','unavailable','protocol','exception','write','commit','interrupt'):
            with self.subTest(mode=mode):
                before=self.snapshot()
                def gate(c,refs):
                    self.assertTrue(c.in_transaction);self.assertEqual(tuple(r.to_json() for r in refs),(self.f.origin,))
                    if mode=='exception':raise RuntimeError('private gate')
                    if mode=='interrupt':raise KeyboardInterrupt()
                    if mode=='write':c.execute("UPDATE v5_tsk_host SET used=used+1 WHERE kind='model'");return 'available'
                    if mode=='commit':c.execute('COMMIT');return 'available'
                    return mode
                self.t._source_gate=gate
                try:
                    if mode=='interrupt':
                        with self.assertRaises(KeyboardInterrupt):self.candidates()
                    elif mode in ('denied','not_found','unavailable'):self.assertTrue(self.value(self.candidates())['works'][0]['text_withheld'])
                    else:self.error(self.candidates(),'unavailable')
                finally:self.t._source_gate=original
                self.assertFalse(self.conn.in_transaction);self.assertEqual(self.snapshot(),before)
    def test_candidates_refuses_caller_transaction_and_corrupt_snapshot(self):
        self.conn.execute('BEGIN');before=self.snapshot();self.error(self.candidates(),'unavailable');self.assertTrue(self.conn.in_transaction);self.assertEqual(self.snapshot(),before);self.conn.execute('ROLLBACK')
        self.conn.execute("UPDATE v5_intake_work SET state='unknown'");before=self.snapshot();self.error(self.candidates(),'unavailable');self.assertEqual(self.snapshot(),before)
    def test_original_create_receipt_after_change_stop_and_config_replacement(self):
        req,receipt=self.create();self.control('cancel',work=receipt['work_ref']);self.stop(self.f.origin)
        self.f.reopen();self.t,self.conn=self.f.t,self.f.conn
        self.t._expert_id='different';self.t._host_grant=None
        self.t._source_gate=lambda *args: (_ for _ in ()).throw(AssertionError('receipt must not gate'))
        before=self.snapshot();self.assertEqual(self.value(self.t.get_create_by_key({'key':req['key']})),receipt);self.assertEqual(self.snapshot(),before)
    def test_control_receipt_original_state_after_later_control(self):
        self.release();req,receipt=self.control('pause');self.control('resume',key='resume');self.control('cancel',key='cancel')
        before=self.snapshot();self.assertEqual(self.value(self.t.get_control_by_key({'key':req['key']})),receipt);self.assertEqual(self.snapshot(),before)
    def test_change_receipt_historical_next_revision_binding(self):
        origin=self.f.record('change');req,out=self.control({'kind':'change','origin_record_ref':origin,'brief':self.f.draft},key='change')
        self.control('cancel');self.stop(origin);before=self.snapshot();self.assertEqual(self.value(self.t.get_control_by_key({'key':'change'})),out);self.assertEqual(self.snapshot(),before)
    def test_receipt_namespace_missing_bad_input_and_caller_transaction(self):
        req,out=self.create();self.error(self.t.get_control_by_key({'key':req['key']}),'not_found')
        for method in (self.t.get_create_by_key,self.t.get_control_by_key):
            self.error(method({'key':'absent'}),'not_found')
            for request in ({'key':''},{'key':False},{'key':'x','extra':1}):self.error(method(request),'invalid_input')
        self.conn.execute('BEGIN');self.conn.execute("UPDATE v5_tsk_host SET ceiling=ceiling-1");before=self.snapshot()
        self.assertEqual(self.value(self.t.get_create_by_key({'key':req['key']})),out);self.assertTrue(self.conn.in_transaction);self.assertEqual(self.snapshot(),before);self.conn.execute('ROLLBACK')
    def test_receipt_corrupt_canonical_input_and_result_fail_closed(self):
        req,out=self.create();saved=self.conn.execute("SELECT input_json,result_json FROM v5_intake_replay WHERE command='C03.create' AND key=?",(req['key'],)).fetchone()
        for column,text in (('input_json','{}'),('input_json',' '+saved[0]),('result_json','{}'),('result_json',dumps(Result.success({'work_ref':{'goal_id':'foreign','revision':1,'epoch':0}})))):
            with self.subTest(column=column,text=text):
                self.conn.execute(f'UPDATE v5_intake_replay SET {column}=? WHERE command=\'C03.create\' AND key=?',(text,req['key']));before=self.snapshot();self.error(self.t.get_create_by_key({'key':req['key']}),'unavailable');self.assertEqual(self.snapshot(),before)
                self.conn.execute("UPDATE v5_intake_replay SET input_json=?,result_json=? WHERE command='C03.create' AND key=?",(*saved,req['key']))
    def test_primary_workless_shape_only_shared_counter_and_replay(self):
        before_goal=self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall();before_events=self.f.events();before_used=self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0]
        receipt=self.value(self.primary());self.assertEqual(set(receipt),{'reservation_id','remaining'});self.assertEqual(set(receipt['remaining']),{'host'})
        row=self.conn.execute('SELECT lease,work,idx,kind,role,binding FROM v5_tsk_reservation WHERE id=?',(receipt['reservation_id'],)).fetchone();self.assertEqual(row,(None,None,None,'model','primary',None))
        self.assertEqual(self.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0],before_used+1)
        before=self.snapshot();self.assertEqual(self.value(self.primary()),receipt);self.assertEqual(self.snapshot(),before);self.assertEqual(self.conn.execute('SELECT * FROM v5_tsk_usage').fetchall(),before_goal);self.assertEqual(self.f.events(),before_events)
    def test_primary_consume_once_and_conflicting_binding_no_debit(self):
        r=self.value(self.primary());self.value(self.consume(r));before=self.snapshot();self.value(self.consume(r));self.assertEqual(self.snapshot(),before);self.error(self.consume(r,'different'),'conflict');self.assertEqual(self.snapshot(),before)
    def test_primary_strict_branch_inputs(self):
        before=self.snapshot()
        for request in ({'key':'x','kind':'model','role':'primary','work_ref':None},{'key':'x','kind':'step','role':'primary'},{'key':'x','kind':'model','role':'expert'},{'key':'x','kind':'operation','role':'primary'},{'key':'x','kind':'model','role':'primary','extra':1}):
            with self.subTest(request=request):self.error(self.t.reserve_budget(request),'invalid_input')
        self.assertEqual(self.snapshot(),before)
    def test_primary_zero_model_and_step_zero(self):
        self.ceiling(0);before=self.snapshot();self.error(self.primary(),'limit');self.assertEqual(self.snapshot(),before)
        self.ceiling(1);self.conn.execute("UPDATE v5_tsk_host SET ceiling=used WHERE kind='step'");self.value(self.primary());self.error(self.primary('next'),'limit')
    def test_primary_and_expert_share_last_model_unit_two_connections(self):
        conn,t,*_=self.f.connect(self.f.guard);self.ceiling(1)
        self.value(self.primary());before=self.snapshot();self.error(t.reserve_budget({'key':'expert','work_ref':self.f.lease['work_ref'],'kind':'model','role':'expert'}),'limit');self.assertEqual(self.snapshot(),before)
        self.ceiling(1);self.value(t.reserve_budget({'key':'expert2','work_ref':self.f.lease['work_ref'],'kind':'model','role':'expert'}));before=self.snapshot();self.error(self.primary('last'),'limit');self.assertEqual(self.snapshot(),before)
    def test_primary_new_host_session_cannot_replay_or_consume_foreign(self):
        r=self.value(self.primary());self.release();self.f.reopen();self.value(self.f.t.finish_startup());self.t,self.conn=self.f.t,self.f.conn
        before=self.snapshot();self.error(self.primary(),'denied');self.error(self.consume(r),'denied');self.assertEqual(self.snapshot(),before)
    def test_primary_legacy_and_closed_or_startup_guard_refuse(self):
        _,legacy,*_=self.f.connect();self.error(legacy.reserve_budget({'key':'p','kind':'model','role':'primary'}),'unavailable')
        self.release();self.f.reopen();self.t,self.conn=self.f.t,self.f.conn;before=self.snapshot();self.error(self.primary(),'conflict');self.assertEqual(self.snapshot(),before)
        self.value(self.t.finish_startup());r=self.value(self.primary());self.f.guard.close();before=self.snapshot();self.error(self.consume(r),'unavailable');self.assertEqual(self.snapshot(),before)
    def test_primary_corrupt_host_or_reservation_not_null_lease_proof(self):
        r=self.value(self.primary());self.conn.execute("UPDATE v5_tsk_reservation SET role='expert' WHERE id=?",(r['reservation_id'],));before=self.snapshot();self.error(self.consume(r),'unavailable');self.error(self.primary(),'unavailable');self.assertEqual(self.snapshot(),before)
    def test_primary_premint_and_postwrite_fault_roll_back(self):
        original=self.t._id_factory
        def bad_mint(kind):self.conn.execute('COMMIT');return 'mint'
        self.t._id_factory=bad_mint;before=self.snapshot();self.error(self.primary(),'unavailable');self.assertEqual(self.snapshot(),before);self.t._id_factory=original
        for failure in (RuntimeError,KeyboardInterrupt):
            with self.subTest(failure=failure):
                before=self.snapshot();self.conn.fault=failure;self.conn.writes_until_fault=1
                if failure is KeyboardInterrupt:
                    with self.assertRaises(KeyboardInterrupt):self.primary('fault')
                else:self.error(self.primary('fault'),'unavailable')
                self.assertFalse(self.conn.in_transaction);self.assertEqual(self.snapshot(),before)
    def test_answer_receipt_historical_question_and_stopped_answer(self):
        _,step=self.f.stage('ask');action=step['action'];question=self.value(self.t.ask({'key':'ask','work_ref':step['work_ref'],'step_id':step['step_id'],**{k:v for k,v in action.items() if k!='kind'}}))
        answer=self.f.record('月曜日です');req,out=self.control({'kind':'answer','question_id':question['question_id'],'answer_record_ref':answer},key='answer')
        self.stop(answer);before=self.snapshot();self.assertEqual(self.value(self.t.get_control_by_key({'key':req['key']})),out);self.assertEqual(self.snapshot(),before)
    def test_primary_corrupt_model_counter_and_caller_transaction(self):
        original=self.conn.execute("SELECT used,ceiling FROM v5_tsk_host WHERE kind='model'").fetchone()
        for used,ceiling in ((-1,10),(11,10),(0,-1),(0,'invalid')):
            with self.subTest(used=used,ceiling=ceiling):
                self.conn.execute("UPDATE v5_tsk_host SET used=?,ceiling=? WHERE kind='model'",(used,ceiling));before=self.snapshot();self.error(self.primary(),'unavailable');self.assertEqual(self.snapshot(),before)
                self.conn.execute("UPDATE v5_tsk_host SET used=?,ceiling=? WHERE kind='model'",original)
        self.conn.execute('BEGIN');before=self.snapshot();self.error(self.primary(),'unavailable');self.assertTrue(self.conn.in_transaction);self.assertEqual(self.snapshot(),before);self.conn.execute('ROLLBACK')
    def test_control_receipt_corrupt_command_target_or_result(self):
        self.release();req,out=self.control('pause');saved=self.conn.execute("SELECT input_json,result_json FROM v5_intake_replay WHERE command='control' AND key=?",(req['key'],)).fetchone()
        for which in ('command','target','result'):
            with self.subTest(which=which):
                data=loads(saved[0]);result=loads(saved[1])
                if which=='command':data['command']='unknown'
                elif which=='target':data['work_ref']['goal_id']='foreign'
                else:result['value']['work_ref']['revision']=2
                self.conn.execute("UPDATE v5_intake_replay SET input_json=?,result_json=? WHERE command='control' AND key=?",(dumps(data),dumps(result),req['key']));before=self.snapshot();self.error(self.t.get_control_by_key({'key':req['key']}),'unavailable');self.assertEqual(self.snapshot(),before)
                self.conn.execute("UPDATE v5_intake_replay SET input_json=?,result_json=? WHERE command='control' AND key=?",(*saved,req['key']))
