import threading
import tempfile
import unittest
from pathlib import Path

from pal.native import ProviderUnavailable
from pal.runtime import Runtime
from scripts.live_gate import GatedProvider


class FakeNative:
    identity = 'scripted_gate_test_only'
    def __init__(self):
        self.calls = []
        self.stops = 0
    def complete(self, prompt):
        self.calls.append(prompt)
        return 'scripted response'
    def stop(self):
        self.stops += 1
    def status(self):
        return {'mode':'scripted_gate_test_only'}


class LiveGateTests(unittest.TestCase):
    def test_no_permit_never_invokes_native_and_closes_run(self):
        native = FakeNative(); events = []
        gate = GatedProvider(native, events.append, deadline=10, clock=lambda:0)
        with self.assertRaises(ProviderUnavailable):
            gate.complete('DRAFT\nsynthetic')
        self.assertEqual(native.calls, [])
        self.assertEqual(native.stops, 1)
        with self.assertRaises(ProviderUnavailable):
            gate.grant('K1', 'request', 'DRAFT')
        self.assertEqual(events[-1]['event'], 'run.closed')

    def test_primary_cannot_spend_historical_draft_permit(self):
        native=FakeNative()
        gate=GatedProvider(native,lambda e:None,deadline=10,clock=lambda:0)
        gate.grant('A1','request','DRAFT')
        with self.assertRaises(ProviderUnavailable):gate.complete('PRIMARY\nrequest')
        self.assertEqual(native.calls,[])
        self.assertEqual(native.stops,1)

    def test_per_input_permit_is_spent_before_call_and_retry_is_denied(self):
        native = FakeNative(); events = []
        gate = GatedProvider(native, events.append, deadline=10, clock=lambda:0)
        gate.grant('A1', 'request', 'DRAFT')
        self.assertEqual(gate.complete('DRAFT\nsynthetic'), 'scripted response')
        with self.assertRaises(ProviderUnavailable):
            gate.complete('DRAFT\nsynthetic retry')
        self.assertEqual(len(native.calls), 1)
        self.assertEqual(gate.attempts, 1)
        started = next(e for e in events if e['event']=='call.started')
        self.assertEqual((started['case'], started['phase']), ('A1','request'))
        self.assertEqual(started['call_sequence'], 1)
        self.assertEqual(len(started['prompt_sha256']), 64)

    def test_deadline_and_failure_stop_without_rearming(self):
        now = [0]; native = FakeNative()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:now[0])
        gate.grant('K1','request','DRAFT'); now[0] = 10
        with self.assertRaises(ProviderUnavailable): gate.complete('DRAFT\nsynthetic')
        self.assertEqual(native.calls, [])
        self.assertEqual(native.stops, 1)
        class Failing(FakeNative):
            def complete(self, prompt):
                self.calls.append(prompt)
                raise ProviderUnavailable('scripted error')
        native = Failing(); events = []
        gate = GatedProvider(native, events.append, deadline=10, clock=lambda:0)
        gate.grant('K1','request','DRAFT')
        with self.assertRaises(ProviderUnavailable): gate.complete('DRAFT\nsynthetic')
        self.assertEqual(gate.attempts, 1)
        self.assertEqual(native.stops, 1)
        self.assertTrue(any(e['event']=='call.failed' for e in events))
        with self.assertRaises(ProviderUnavailable): gate.grant('K1','retry','DRAFT')

    def test_close_of_one_runtime_does_not_stop_shared_provider(self):
        native = FakeNative()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:0)
        with tempfile.TemporaryDirectory() as temp:
            for name in ('first','second'):
                runtime = Runtime(Path(temp)/(name+'.db'), provider=gate)
                runtime.close()
                self.assertEqual(native.stops, 0)
        gate.grant('K1','request','DRAFT')
        gate.complete('DRAFT\nsynthetic')
        gate.close_run('finished'); gate.close_run('finished again')
        self.assertEqual(native.stops, 1)

    def test_total_attempt_cap_and_mismatched_kind_fail_closed(self):
        native = FakeNative()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:0, max_calls=2)
        for phase in ('one','two'):
            gate.grant('A1',phase,'DRAFT'); gate.complete('DRAFT\nsynthetic')
        with self.assertRaises(ProviderUnavailable): gate.grant('A1','three','DRAFT')
        self.assertEqual(len(native.calls), 2)
        native = FakeNative()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:0)
        gate.grant('A1','request','DRAFT')
        with self.assertRaises(ProviderUnavailable): gate.complete('unplanned conversation')
        self.assertEqual(native.calls, [])

    def test_concurrent_unplanned_call_stops_active_owner(self):
        entered = threading.Event(); released = threading.Event()
        class Blocking(FakeNative):
            def complete(self, prompt):
                self.calls.append(prompt); entered.set()
                if not released.wait(2): raise AssertionError('owner not stopped')
                return 'scripted response'
            def stop(self):
                super().stop(); released.set()
        native = Blocking()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:0)
        gate.grant('K1','request','DRAFT')
        errors = []
        def run():
            try: gate.complete('DRAFT\nsynthetic')
            except ProviderUnavailable as error: errors.append(error)
        worker = threading.Thread(target=run)
        worker.start(); self.assertTrue(entered.wait(2))
        with self.assertRaises(ProviderUnavailable): gate.complete('DRAFT\nunplanned')
        worker.join(2); self.assertFalse(worker.is_alive())
        self.assertEqual(len(native.calls), 1)
        self.assertEqual(native.stops, 1)
        self.assertEqual(len(errors), 1)

    def test_late_return_and_unencodable_prompt_never_become_accepted(self):
        now = [0]; events = []
        class Late(FakeNative):
            def complete(self, prompt):
                self.calls.append(prompt); now[0] = 10
                return 'late response'
        native = Late()
        gate = GatedProvider(native, events.append, deadline=10, clock=lambda:now[0])
        gate.grant('K1','request','DRAFT')
        with self.assertRaises(ProviderUnavailable): gate.complete('DRAFT\nsynthetic')
        self.assertEqual(native.stops, 1)
        self.assertTrue(next(e for e in events if e['event']=='call.returned')['discarded'])
        native = FakeNative()
        gate = GatedProvider(native, lambda e:None, deadline=10, clock=lambda:0)
        gate.grant('K1','request','DRAFT')
        with self.assertRaises(UnicodeError): gate.complete('DRAFT\n\ud800')
        self.assertEqual(native.calls, [])
        self.assertEqual(native.stops, 1)
