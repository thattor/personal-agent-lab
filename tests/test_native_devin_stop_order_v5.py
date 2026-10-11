"""Failure cleanup order fixtures only; never native/provider cessation proof."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import test_native_devin_text_v5 as fixtures


class StopOrderTests(unittest.TestCase):
    def fixture(self,*,primary=None,diagnostic=None):
        case=fixtures.NativeDevinTextTests(methodName='runTest');case.setUp()
        self.addCleanup(case.doCleanups)
        order=[];parent=case.owners.api.PooledAdapter
        class Pool(parent):
            def events(self,*args,**kw):
                order.append('events')
                raise primary if primary is not None else RuntimeError('fixture protocol failure')
            def status(self,*args,**kw):
                order.append('status');raise AssertionError('failure diagnosis must not pump')
            def stop(self,ref):
                order.append('stop')
                # Original execute receipt must be retained before cleanup.
                assert len(list(case.attempt_root.rglob('execute.json')))==1
                return super().stop(ref)
        case.owners.api.PooledAdapter=Pool
        original_adapter=case.owners.api.DevinAdapter
        class Adapter(original_adapter):
            def protocol_diagnostic(self,ref):
                order.append('diagnostic')
                if diagnostic is not None:raise diagnostic
                return {'fixture':'public diagnostic'}
        case.owners.api.DevinAdapter=Adapter
        original_host=case.owners.api.DevinTextHost
        class Host(original_host):
            def __getattribute__(self,name):
                if name=='observation':order.append('host_snapshot')
                return super().__getattribute__(name)
        case.owners.api.DevinTextHost=Host
        return case,order
    def assert_order(self,case,order):
        self.assertEqual(order.count('stop'),1)
        self.assertEqual(case.owners.pool.executions,1)
        self.assertNotIn('status',order)
        self.assertNotIn('cancel_reserved',case.owners.log)
        self.assertEqual(order.count('diagnostic'),1)
        self.assertLess(order.index('stop'),order.index('diagnostic'))
        self.assertLess(order.index('stop'),order.index('host_snapshot'))
    def test_supported_stop_precedes_public_diagnostic_even_when_callback_raises(self):
        case,order=self.fixture(diagnostic=RuntimeError('PRIVATE_DIAGNOSTIC_CANARY'))
        case.unknown();self.assert_order(case,order)
    def test_diagnostic_write_keyboard_interrupt_cannot_delay_or_repeat_stop(self):
        case,order=self.fixture();original=case.module._write;writes=[]
        def write(path,data):
            if Path(path).name=='diagnostic.json':
                writes.append('diagnostic');order.append('diagnostic_write')
                raise KeyboardInterrupt('fixture diagnostic write interrupt')
            return original(path,data)
        with patch.object(case.module,'_write',side_effect=write):case.unknown()
        self.assertEqual(writes,['diagnostic']);self.assert_order(case,order)
        self.assertLess(order.index('stop'),order.index('diagnostic_write'))
    def test_primary_keyboard_interrupt_preserved_after_stop_and_diagnostic_baseexception(self):
        primary=KeyboardInterrupt('fixture original interrupt')
        case,order=self.fixture(primary=primary,diagnostic=SystemExit('fixture diagnostic interrupt'))
        with self.assertRaises(KeyboardInterrupt) as caught:case.invoke()
        self.assertIs(caught.exception,primary)
        # A failed diagnostic must not replace the original BaseException.
        self.assertEqual(order.count('stop'),1);self.assertEqual(case.owners.pool.executions,1)
        self.assertNotIn('status',order);self.assertNotIn('cancel_reserved',case.owners.log)
        self.assertLess(order.index('stop'),order.index('diagnostic'))


if __name__=='__main__':unittest.main()
