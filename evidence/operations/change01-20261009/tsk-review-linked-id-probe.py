"""Disposable SQLite reproduction; run from repository root with Python3.13."""
import sys
sys.path.insert(0, 'tests')
import test_tasks_change_v5 as fixture
from pal.contracts_v5 import dumps, loads
for target in ('step', 'reservation'):
    f = fixture.ChangeTests(); f.setUp()
    try:
        if target == 'step':
            f.f.call([f.f.origin])
            f.value(f.t.begin_step({'key': f.f.key(), 'work_ref': f.f.lease['work_ref'], 'action': {'kind': 'report', 'summary': 'old'}}))
            f.change()
            wire = loads(f.conn.execute('SELECT wire FROM v5_tsk_step').fetchone()[0]); wire['step_id'] = ''
            f.conn.execute('UPDATE v5_tsk_step SET id=?,wire=?', ('', dumps(wire)))
            f.conn.execute('UPDATE v5_tsk_call SET step=?', ('',))
        else:
            call = f.admitted(); f.value(f.t.end_call({'call_id': call['call_id'], 'outcome': 'returned'})); f.change()
            f.conn.execute('UPDATE v5_tsk_reservation SET id=?', ('',))
            f.conn.execute('UPDATE v5_tsk_call SET reservation=?', ('',))
        before = f.f.dump(); result = f.release().to_json()
        print(target, 'ok=', result['ok'], 'error=', result.get('error'), 'mutated=', before != f.f.dump())
    finally:
        f.doCleanups()
