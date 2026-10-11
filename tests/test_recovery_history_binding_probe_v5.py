"""Prior managed producing-call history retains exact session/claim proof."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from pal.contracts_v5 import dumps
import test_tasks_recovery_v5 as fixture


class HistoricalManagedBindingProbes(unittest.TestCase):
    def test_corrupt_managed_historical_lease_proof_cannot_settle_next_orphan(self):
        for corruption in ('missing_owner','wrong_claim_epoch'):
            with self.subTest(corruption=corruption):
                f=fixture.RecoveryTests();f.setUp();self.addCleanup(f.doCleanups)
                _,step=f.stage();old=f.lease.copy()
                f.value(f.t.finish_step({'work_ref':old['work_ref'],'step_id':step['step_id'],'result_refs':[]}))
                f.value(f.t.release({'lease_id':old['lease_id'],'work_ref':old['work_ref'],'outcome':'yield','reason':'finished history'}))
                f.reopen();f.value(f.t.finish_startup())
                f.lease=f.value(f.t.claim({'runner_id':f.guard.runner_id}));f.call();f.reopen()
                if corruption=='missing_owner':
                    f.conn.execute('DELETE FROM v5_tsk_lease_owner WHERE lease=?',(old['lease_id'],))
                else:
                    f.conn.execute('UPDATE v5_tsk_lease_owner SET claim_work=? WHERE lease=?',
                        (dumps({**old['work_ref'],'epoch':old['work_ref']['epoch']+1}),old['lease_id']))
                before=f.snapshot();f.error(f.recover(),'unavailable')
                self.assertEqual(f.snapshot(),before)
                self.assertEqual(f.conn.execute('SELECT active FROM v5_tsk_lease WHERE id=?',(f.lease['lease_id'],)).fetchone()[0],1)


if __name__=='__main__':unittest.main()
