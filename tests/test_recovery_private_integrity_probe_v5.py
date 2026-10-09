"""Independent snapshot probes; managed cases require actual HOST, never a double."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from pal.contracts_v5 import dumps,loads,WorkRef
import pal.tasks_v5 as owner
import test_tasks_ask_v5 as legacy_fixture
import test_tasks_recovery_v5 as managed_fixture


class LegacyRecoveryValidatorProbes(unittest.TestCase):
    def history(self):
        f=legacy_fixture.TaskAskTests();f.setUp();self.addCleanup(f.doCleanups)
        old_call=f.call([f.origin])
        step=f.value(f.tasks.begin_step({'key':'history-step','work_ref':f.lease['work_ref'],
            'action':{'kind':'report','summary':'finished history'}}))
        f.value(f.tasks.finish_step({'work_ref':f.lease['work_ref'],'step_id':step['step_id'],'result_refs':[]}))
        f.value(f.tasks.release({'lease_id':f.lease['lease_id'],'work_ref':f.lease['work_ref'],'outcome':'yield','reason':'slice'}))
        f.lease=f.value(f.tasks.claim({'runner_id':'second'}));f.call([f.origin])
        row=f.tasks._one('SELECT * FROM v5_intake_work WHERE goal_id=?',(f.goal,))
        lease=f.tasks._one('SELECT * FROM v5_tsk_lease WHERE id=?',(f.lease['lease_id'],))
        return f,old_call,step,row,lease

    def test_valid_older_finished_step_is_preserved_by_recovery_validation(self):
        f,_,_,row,lease=self.history();before=f.dump()
        calls=f.tasks._old_calls(row,lease,claim=WorkRef.from_json(f.lease['work_ref']))
        self.assertEqual(len(calls),1);self.assertEqual(f.dump(),before)

    def test_corrupt_other_lease_history_does_not_pass_recovery_validation(self):
        for corruption in ('step_status','step_index','call_status'):
            with self.subTest(corruption=corruption):
                f,call,step,row,lease=self.history()
                if corruption=='call_status':f.conn.execute("UPDATE v5_tsk_call SET status='unknown' WHERE id=?",(call,))
                else:
                    wire=loads(f.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',(step['step_id'],)).fetchone()[0])
                    wire['status' if corruption=='step_status' else 'index']='unknown' if corruption=='step_status' else False
                    f.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?',(dumps(wire),step['step_id']))
                before=f.dump()
                with self.assertRaises(owner._Rejected) as rejection:
                    f.tasks._old_calls(row,lease,claim=WorkRef.from_json(f.lease['work_ref']))
                self.assertEqual(rejection.exception.result.error.code,'unavailable');self.assertEqual(f.dump(),before)


class ManagedRecoveryPrivateProbes(unittest.TestCase):
    def owners(self):
        f=managed_fixture.RecoveryTests();f.setUp();self.addCleanup(f.doCleanups);return f

    def test_enrollment_old_session_and_lease_claim_corruption_do_not_settle(self):
        cases=('uuid','profile','old_session_profile','old_session_runner','missing_owner','claim_shape','claim_epoch')
        for case in cases:
            with self.subTest(case=case):
                f=self.owners();f.call();f.reopen()
                old_session=f.conn.execute('SELECT session FROM v5_tsk_lease_owner WHERE lease=?',(f.lease['lease_id'],)).fetchone()[0]
                if case=='uuid':f.conn.execute("UPDATE v5_tsk_enrollment SET db_uuid='not-uuid'")
                elif case=='profile':f.conn.execute("UPDATE v5_tsk_enrollment SET profile='unknown'")
                elif case=='old_session_profile':f.conn.execute("UPDATE v5_tsk_session SET profile='unknown' WHERE id=?",(old_session,))
                elif case=='old_session_runner':f.conn.execute("UPDATE v5_tsk_session SET runner='forged' WHERE id=?",(old_session,))
                elif case=='missing_owner':f.conn.execute('DELETE FROM v5_tsk_lease_owner WHERE lease=?',(f.lease['lease_id'],))
                else:
                    claim={} if case=='claim_shape' else {**f.lease['work_ref'],'epoch':f.lease['work_ref']['epoch']+1}
                    f.conn.execute('UPDATE v5_tsk_lease_owner SET claim_work=? WHERE lease=?',(dumps(claim),f.lease['lease_id']))
                before=f.snapshot();f.error(f.recover(),'unavailable');self.assertEqual(f.snapshot(),before)

    def test_binding_uses_saved_claim_epoch_after_multiple_control_epochs(self):
        f=self.owners();call=f.call(None);old=copy.deepcopy(f.lease['work_ref'])
        f.value(f.t.control({'key':f.key(),'work_ref':f.work()['work_ref'],'command':'pause'}))
        f.value(f.t.control({'key':f.key(),'work_ref':f.work()['work_ref'],'command':'cancel'}))
        current=f.work()['work_ref'];self.assertGreater(current['epoch'],old['epoch'])
        f.reopen();before=f.usage();out=f.settled(f.recover(),[call])
        self.assertEqual((out['state'],out['work_ref']),('cancelled',current));self.assertEqual(f.usage(),before)
        self.assertEqual(loads(f.conn.execute('SELECT claim_work FROM v5_tsk_lease_owner WHERE lease=?',(f.lease['lease_id'],)).fetchone()[0]),old)

    def test_corrupt_other_lease_history_is_unavailable_before_recovery_writes(self):
        f=self.owners();_,step=f.stage();f.value(f.t.finish_step({'work_ref':f.lease['work_ref'],'step_id':step['step_id'],'result_refs':[]}))
        f.value(f.t.release({'lease_id':f.lease['lease_id'],'work_ref':f.lease['work_ref'],'outcome':'yield','reason':'slice'}))
        f.lease=f.value(f.t.claim({'runner_id':f.guard.runner_id}));f.call();f.reopen()
        wire=loads(f.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',(step['step_id'],)).fetchone()[0]);wire['status']='unknown'
        f.conn.execute('UPDATE v5_tsk_step SET wire=? WHERE id=?',(dumps(wire),step['step_id']))
        before=f.snapshot();f.error(f.recover(),'unavailable');self.assertEqual(f.snapshot(),before)


if __name__=='__main__':unittest.main()
