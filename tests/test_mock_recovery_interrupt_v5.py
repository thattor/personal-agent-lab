"""Primary interruption survives failed end recording; no fabricated cessation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from pal.contracts_v5 import dumps
from pal.mock_runner_v5 import MockInvoker
import test_mock_execution_v5 as fixture


class HostInterruption(BaseException):
    pass


class RecoveryInterruptTests(unittest.TestCase):
    def owners(self):
        f = fixture.MockExecutionTests(); f.setUp(); self.addCleanup(f.doCleanups)
        ref, _ = f.create()
        lease = f.value(f.tasks.claim({'runner_id': 'one-host'}))
        reservation = f.value(f.tasks.reserve_budget({'key': 'reserve',
            'work_ref': lease['work_ref'], 'kind': 'model', 'role': 'expert'}))
        admission = {'call_id': dumps(['C15.call', lease['lease_id'], 0]),
            'lease_id': lease['lease_id'], 'work_ref': lease['work_ref'],
            'reservation_id': reservation['reservation_id'], 'source_refs': [ref]}
        return f, lease, admission

    def test_original_primary_interrupt_survives_end_record_exception(self):
        for interruption in (KeyboardInterrupt, SystemExit, HostInterruption):
            for end_failure in (RuntimeError, Exception):
                with self.subTest(interruption=interruption, end_failure=end_failure):
                    f, lease, admission = self.owners()
                    primary = interruption('private callback interrupted')
                    calls, attempts = [], []
                    def callback():
                        calls.append(True)
                        raise primary
                    def end(request):
                        attempts.append(request)
                        raise end_failure('private end record failed')
                    f.tasks.end_call = end
                    with self.assertRaises(interruption) as raised:
                        MockInvoker().invoke(f.tasks, admission, callback)
                    self.assertIs(raised.exception, primary)
                    self.assertEqual(calls, [True])
                    self.assertEqual(attempts, [{'call_id': admission['call_id'], 'outcome': 'raised'}])
                    call = f.value(f.tasks.get_call({'call_id': admission['call_id']}))
                    self.assertEqual((call['status'], call.get('step_id')), ('admitted', None))
                    self.assertEqual(f.conn.execute('SELECT active FROM v5_tsk_lease WHERE id=?',
                        (lease['lease_id'],)).fetchone()[0], 1)
                    before = tuple(f.conn.iterdump())
                    replay = MockInvoker().invoke(f.tasks, admission, callback)
                    self.assertFalse(replay.ok)
                    self.assertEqual(calls, [True])
                    self.assertEqual(tuple(f.conn.iterdump()), before)

    def test_guardless_owner_runtime_error_is_not_host_refusal(self):
        f, _, admission = self.owners()
        failure = RuntimeError('private owner readiness failure')
        observed = []
        def unavailable(request):
            observed.append(request)
            raise failure
        f.tasks.get_call = unavailable
        before = tuple(f.conn.iterdump()); callbacks = []
        with self.assertRaises(RuntimeError) as raised:
            MockInvoker().invoke(f.tasks, admission, lambda: callbacks.append(True))
        self.assertIs(raised.exception, failure)
        self.assertEqual(observed, [{'call_id': admission['call_id']}])
        self.assertEqual(callbacks, [])
        self.assertEqual(tuple(f.conn.iterdump()), before)


if __name__ == '__main__':
    unittest.main()
