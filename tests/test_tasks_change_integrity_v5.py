"""Stored identities and source bindings must survive old-lease cleanup checks."""
import unittest

from pal.contracts_v5 import dumps, loads
import test_tasks_change_v5 as fixture


class ChangeIntegrityTests(unittest.TestCase):
    def test_consistently_corrupted_call_reservation_step_and_sources_do_not_release(self):
        cases = ('empty_call_id', 'null_call_id', 'noncanonical_call_id',
                 'empty_reservation_id', 'empty_step_id', 'malformed_sources',
                 'missing_required_source', 'unregistered_source', 'invalid_source_ref')
        for case in cases:
            with self.subTest(case=case):
                f = fixture.ChangeTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                call = f.admitted()
                f.value(f.t.end_call({'call_id': call['call_id'], 'outcome': 'returned'}))
                step = None
                if case == 'empty_step_id':
                    step = f.value(f.t.begin_step({'key': 'integrity-step',
                        'work_ref': f.f.lease['work_ref'],
                        'action': {'kind': 'report', 'summary': 'ended old call'}}))
                f.change()
                if case.endswith('call_id'):
                    bad_id = {'empty_call_id': '', 'null_call_id': None,
                              'noncanonical_call_id': 'forged-consistent-call'}[case]
                    f.conn.execute('UPDATE v5_tsk_call SET id=? WHERE id=?',
                                   (bad_id, call['call_id']))
                    f.conn.execute('UPDATE v5_tsk_reservation SET binding=? WHERE id=?',
                                   (bad_id, call['reservation_id']))
                elif case == 'empty_reservation_id':
                    f.conn.execute("UPDATE v5_tsk_reservation SET id='' WHERE id=?", (call['reservation_id'],))
                    f.conn.execute("UPDATE v5_tsk_call SET reservation='' WHERE id=?", (call['call_id'],))
                elif case == 'empty_step_id':
                    wire = loads(f.conn.execute('SELECT wire FROM v5_tsk_step WHERE id=?',
                                                (step['step_id'],)).fetchone()[0])
                    wire['step_id'] = ''
                    f.conn.execute("UPDATE v5_tsk_step SET id='',wire=? WHERE id=?",
                                   (dumps(wire), step['step_id']))
                    f.conn.execute("UPDATE v5_tsk_call SET step='' WHERE id=?", (call['call_id'],))
                else:
                    source = {'malformed_sources': {}, 'missing_required_source': [],
                              'unregistered_source': [f.f.origin, {'kind': 'record', 'id': 'unregistered'}],
                              'invalid_source_ref': [{'kind': 'invalid', 'id': 'bad'}]}[case]
                    f.conn.execute('UPDATE v5_tsk_call SET sources=? WHERE id=?',
                                   (dumps(source), call['call_id']))
                before = f.f.dump()
                result = f.release()
                f.error(result, 'unavailable')
                self.assertEqual(f.f.dump(), before)
                self.assertFalse(f.conn.in_transaction)
                self.assertEqual(f.conn.execute('SELECT active FROM v5_tsk_lease').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
