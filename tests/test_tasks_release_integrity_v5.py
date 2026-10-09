"""Uncertain saved call state must retain the occupied execution slot."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unittest
import test_tasks_v5 as fixtures


class ReleaseIntegrityTests(unittest.TestCase):
    def test_unknown_call_status_cannot_release_or_rewrite_current_control(self):
        for status in (None, 'unknown', 'not-a-status'):
            for control in (None, 'pause', 'cancel'):
                for outcome in ('yield', 'failed'):
                    with self.subTest(status=status, control=control, outcome=outcome):
                        fixture = fixtures.TaskTests()
                        fixture.setUp()
                        try:
                            claim = fixture.start()
                            call = fixture.admit_request(claim)
                            fixture.value(fixture.store.admit_call(call))
                            if control:
                                fixture.value(fixture.control(claim, control))
                            fixture.conn.execute('UPDATE v5_tsk_call SET status=? WHERE id=?',
                                                 (status, call['call_id']))
                            before = fixture.snapshot()
                            result = fixture.release(claim, outcome)
                            self.assertFalse(result.ok, result.to_json())
                            self.assertEqual(result.error.code, 'unavailable')
                            self.assertEqual(fixture.snapshot(), before)
                            self.assertFalse(fixture.conn.in_transaction)
                        finally:
                            fixture.doCleanups()


if __name__ == '__main__':
    unittest.main()
