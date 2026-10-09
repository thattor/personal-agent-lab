"""Public owner doubles; local unqualified files are not provider evidence."""
import json
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_native_devin_text_v5 as f
import test_native_devin_stop_order_v5 as order_fixture

class WrapperUnqualifiedTests(unittest.TestCase):
    def fixture(self):
        c=f.NativeDevinTextTests(methodName='runTest');c.setUp();self.addCleanup(c.doCleanups);return c
    def test_failed_strict_model_saves_private_unqualified_text_after_stop(self):
        for change in ({'effective_model':'other'},{'effective_model':None},{'effective_model_verified':False}):
            with self.subTest(change=change):
                c=self.fixture();c.owners.ending_changes=change;sequence=[];original=c.module._write
                def write(path,value):
                    if Path(path).name=='unqualified-output.json':
                        self.assertEqual(c.owners.log.count('pool_stop'),1);sequence.append('snapshot')
                    if Path(path).name=='diagnostic.json':sequence.append('diagnostic')
                    return original(path,value)
                with patch.object(c.module,'_write',side_effect=write):c.unknown()
                paths=list(c.attempt_root.rglob('unqualified-output.json'));self.assertEqual(len(paths),1)
                self.assertEqual(stat.S_IMODE(paths[0].stat().st_mode),0o600)
                body=json.loads(paths[0].read_text());self.assertEqual(body['text'],''.join(c.owners.chunks))
                self.assertEqual((body['authority'],body['phase']),('unqualified','capturing'))
                self.assertEqual(sequence,['snapshot','diagnostic']);self.assertEqual(c.owners.pool.executions,1)
    def test_snapshot_and_write_failures_are_best_effort_after_single_stop(self):
        for point in ('snapshot','write'):
            for error in (RuntimeError('private'),KeyboardInterrupt('private')):
                with self.subTest(point=point,error=type(error).__name__):
                    owner=order_fixture.StopOrderTests(methodName='runTest');c,order=owner.fixture();self.addCleanup(owner.doCleanups)
                    writes=[];original=c.module._write
                    def snapshot(*args):
                        self.assertEqual(order.count('stop'),1)
                        if point=='snapshot':raise error
                        return {'fixture':'unqualified'}
                    def write(path,value):
                        if Path(path).name=='unqualified-output.json':
                            writes.append('unqualified');self.assertEqual(order.count('stop'),1)
                            if point=='write':raise error
                        return original(path,value)
                    with patch.object(c.module.NativeTextBuffer,'unqualified_snapshot',side_effect=snapshot,create=True),patch.object(c.module,'_write',side_effect=write):c.unknown()
                    self.assertEqual(order.count('stop'),1);self.assertEqual(order.count('diagnostic'),1)
                    self.assertEqual(c.owners.pool.executions,1);self.assertNotIn('status',order)
                    self.assertEqual(writes,[] if point=='snapshot' else ['unqualified'])
    def test_original_baseexception_survives_snapshot_baseexception(self):
        primary=KeyboardInterrupt('original');owner=order_fixture.StopOrderTests(methodName='runTest')
        c,order=owner.fixture(primary=primary);self.addCleanup(owner.doCleanups)
        def snapshot(*args):self.assertEqual(order.count('stop'),1);raise SystemExit('diagnostic')
        with patch.object(c.module.NativeTextBuffer,'unqualified_snapshot',side_effect=snapshot,create=True):
            with self.assertRaises(KeyboardInterrupt) as caught:c.invoke()
        self.assertIs(caught.exception,primary);self.assertEqual(order.count('stop'),1);self.assertEqual(c.owners.pool.executions,1)
    def test_success_and_typed_never_entered_add_no_unqualified_record(self):
        c=self.fixture();c.invoke();self.assertEqual(list(c.attempt_root.rglob('unqualified-output.json')),[])
        c=self.fixture();c.owners.mode='never_started'
        with self.assertRaises(c.values.NativeNeverEntered):c.invoke()
        self.assertEqual(list(c.attempt_root.rglob('unqualified-output.json')),[])

if __name__=='__main__':unittest.main()
