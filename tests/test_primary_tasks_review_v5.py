"""Independent exact-source probes; not source-author acceptance fixtures."""
import copy
import sqlite3
import threading
import unittest
from unittest.mock import patch
from pal.contracts_v5 import Result,dumps,loads,Limits
from pal.tasks_v5 import TaskStore
import test_tasks_primary_v5 as primary
import test_completion_connection_v5 as completion

class PrimaryReview(unittest.TestCase):
    def setUp(self):
        self.f=primary.PrimaryTaskTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_consume_one_sided_corruption_and_session_binding_deletion(self):
        for mode in ('binding','consume','session','consume_pair'):
            with self.subTest(mode=mode):
                f=primary.PrimaryTaskTests();f.setUp()
                try:
                    r=f.value(f.primary());f.value(f.consume(r))
                    if mode=='binding':f.conn.execute("UPDATE v5_tsk_reservation SET binding='forged' WHERE id=?",(r['reservation_id'],))
                    elif mode=='consume':f.conn.execute("DELETE FROM v5_intake_replay WHERE command='consume' AND key=?",(r['reservation_id'],))
                    elif mode=='session':f.conn.execute("DELETE FROM v5_tsk_primary_reservation WHERE reservation=?",(r['reservation_id'],))
                    else:
                        forged={'reservation_id':r['reservation_id'],'call_or_operation_id':'forged'}
                        f.conn.execute("UPDATE v5_intake_replay SET input_json=?,result_json=? WHERE command='consume' AND key=?",(dumps(forged),dumps(Result.success(forged)),r['reservation_id']))
                    before=f.snapshot();f.error(f.consume(r),'unavailable');self.assertEqual(f.snapshot(),before)
                finally:f.doCleanups()
    def test_complete_receipt_survives_actual_ver_invalidation_after_stop(self):
        f=completion.CompletionConnectionTests();f.setUp();self.addCleanup(f.doCleanups)
        ver,req=f.ready();out=f.value(f.tasks.control(req));f.value(f.stop(f.memory,f.refs[0]))
        self.assertEqual(f.value(f.status(ver))['status'],'invalidated')
        before=f.snapshot();self.assertEqual(f.value(f.tasks.get_control_by_key({'key':req['key']})),out);self.assertEqual(f.snapshot(),before)
    def test_read_sql_failure_is_bounded_and_caller_writes_preserved(self):
        f=self.f;req,out=f.create();f.conn.execute('BEGIN');f.conn.execute("UPDATE v5_tsk_host SET ceiling=ceiling-1");before=f.snapshot()
        with patch.object(f.t,'_one',side_effect=sqlite3.OperationalError('private sql path')):f.error(f.t.get_create_by_key({'key':req['key']}),'unavailable')
        self.assertTrue(f.conn.in_transaction);self.assertEqual(f.snapshot(),before);f.conn.execute('ROLLBACK')
    def test_running_pause_receipt_contradictory_control_status_refused(self):
        f=self.f;req,out=f.control('pause');self.assertEqual(out['control_status'],'pause_requested')
        row=f.conn.execute("SELECT result_json FROM v5_intake_replay WHERE command='control' AND key=?",(req['key'],)).fetchone()
        forged=loads(row[0]);forged['value']['control_status']='none'
        f.conn.execute("UPDATE v5_intake_replay SET result_json=? WHERE command='control' AND key=?",(dumps(forged),req['key']));before=f.snapshot()
        f.error(f.t.get_control_by_key({'key':req['key']}),'unavailable');self.assertEqual(f.snapshot(),before)
    def test_two_threads_share_one_final_host_model_unit(self):
        f=self.f;initialized=threading.Barrier(3);race=threading.Barrier(3);results=[];errors=[]
        def worker(key):
            conn=None
            try:
                conn=sqlite3.connect(f.f.path,isolation_level=None,timeout=3)
                t=TaskStore(conn,host_limits=Limits(0,100,100),host_grant=f.f.grant,expert_id='expert',startup_guard=f.f.guard,source_gate=lambda c,r:'available')
                initialized.wait(5);race.wait(5)
                results.append(t.reserve_budget({'key':key,'kind':'model','role':'primary'}).to_json())
            except BaseException as error:errors.append(repr(error))
            finally:
                if conn is not None:conn.close()
        # Ready barrier ensures host config has settled before final-unit setting.
        threads=[threading.Thread(target=worker,args=(str(i),)) for i in range(2)]
        for t in threads:t.start()
        initialized.wait(5);f.ceiling(1);before=f.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0];race.wait(5)
        for t in threads:t.join(5)
        self.assertFalse(any(t.is_alive() for t in threads));self.assertEqual(errors,[])
        self.assertEqual(sorted(r['ok'] for r in results),[False,True]);self.assertEqual([r['error']['code'] for r in results if not r['ok']],['limit'])
        self.assertEqual(f.conn.execute("SELECT used FROM v5_tsk_host WHERE kind='model'").fetchone()[0],before+1)
    def test_candidate_output_cap_and_unregistered_required_ref(self):
        f=self.f;f.f.mem._id_factory=lambda kind:'r'*132000
        huge=f.f.record('bounded body')
        f.value(f.t.register_sources({'work_ref':f.f.lease['work_ref'],'refs':[huge]}))
        before=f.snapshot();f.error(f.candidates(),'limit');self.assertEqual(f.snapshot(),before)
        f.conn.execute('DELETE FROM v5_intake_source WHERE id=?',(f.f.origin['id'],));before=f.snapshot()
        f.error(f.candidates(),'unavailable');self.assertEqual(f.snapshot(),before)
