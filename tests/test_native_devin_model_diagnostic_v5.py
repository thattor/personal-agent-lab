"""Public owner doubles only; model observations never qualify a native call."""
import json
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_native_devin_text_v5 as f
import test_native_devin_stop_order_v5 as order_fixture

FIELDS={'sessionUpdate':'config_option_update','configOptions':[{'id':'model','type':'select','currentValue':'swe-2-high','options':[{'value':'swe-2-high'}]}]}
class WrapperModelDiagnosticTests(unittest.TestCase):
    def fixture(self):
        c=f.NativeDevinTextTests(methodName='runTest');c.setUp();self.addCleanup(c.doCleanups)
        parent=c.owners.api.DevinAdapter
        class Adapter(parent):
            def events(self,*args,**kw):
                self.kw['observe_model'](FIELDS,current_update=True)
                return super().events(*args,**kw)
        c.owners.api.DevinAdapter=Adapter
        return c
    def read(self,c):
        paths=list(c.attempt_root.rglob('model-observations.json'));self.assertEqual(len(paths),1)
        self.assertEqual(stat.S_IMODE(paths[0].stat().st_mode),0o600)
        value=json.loads(paths[0].read_text());self.assertEqual(value['authority'],'unqualified');return value
    def test_success_original_hooks_and_stop_before_single_write(self):
        c=self.fixture();original=c.module._write;order=[]
        def write(path,value):
            name=Path(path).name
            if name in ('ending.json','model-observations.json'):
                self.assertEqual(c.owners.log.count('pool_stop'),1);order.append(name)
            return original(path,value)
        with patch.object(c.module,'_write',side_effect=write):c.invoke()
        value=self.read(c);rows=value['observations'];self.assertEqual([o['hook'] for o in rows],['observe','verify_session']);self.assertEqual([o['original_hook'] for o in rows],['returned','returned']);self.assertEqual(rows[0]['effective_model_hint'],{'option_id':'model','current_value':'swe-2-high'});self.assertEqual(order,['ending.json','model-observations.json']);self.assertEqual(c.owners.pool.executions,1)
    def test_matching_hint_does_not_override_null_or_false_original_model(self):
        for change in ({'effective_model':None},{'effective_model_verified':False}):
            with self.subTest(change=change):
                c=self.fixture();c.owners.ending_changes=change;original=c.module._write;order=[]
                def write(path,value):
                    name=Path(path).name
                    if name in ('unqualified-output.json','model-observations.json','diagnostic.json'):
                        self.assertEqual(c.owners.log.count('pool_stop'),1);order.append(name)
                    return original(path,value)
                with patch.object(c.module,'_write',side_effect=write):c.unknown()
                self.assertEqual(self.read(c)['observations'][0]['effective_model_hint']['current_value'],'swe-2-high');self.assertEqual(order,['unqualified-output.json','model-observations.json','diagnostic.json']);self.assertEqual(list(c.attempt_root.rglob('ending.json')),[]);self.assertEqual(c.owners.pool.executions,1)
    def test_original_observe_exception_recorded_without_replacement(self):
        c=self.fixture();c.owners.observe_error=True;c.unknown();rows=self.read(c)['observations'];self.assertEqual(len(rows),1);self.assertEqual((rows[0]['hook'],rows[0]['original_hook']),('observe','raised'));self.assertEqual(c.owners.log.count('pool_stop'),1)
    def test_original_verify_baseexception_preserved_and_recorded(self):
        c=self.fixture();primary=KeyboardInterrupt('fixture original');parent=c.owners.api.DevinTextHost
        class Host(parent):
            def verify(self,request,phase,native):
                if phase=='session':raise primary
                return super().verify(request,phase,native)
        c.owners.api.DevinTextHost=Host
        with self.assertRaises(KeyboardInterrupt) as caught:c.invoke()
        self.assertIs(caught.exception,primary);rows=self.read(c)['observations'];self.assertEqual((rows[-1]['hook'],rows[-1]['original_hook']),('verify_session','raised'));self.assertEqual(c.owners.log.count('pool_stop'),1)
    def test_collector_and_write_baseexceptions_do_not_change_success(self):
        c=self.fixture();collector=getattr(c.module,'NativeModelDiagnostic')
        for point in ('constructor','observe','snapshot','write'):
            with self.subTest(point=point):
                c=self.fixture();original=c.module._write
                def write(path,value):
                    if Path(path).name=='model-observations.json':raise KeyboardInterrupt('fixture diagnostic')
                    return original(path,value)
                target=patch.object(c.module,'NativeModelDiagnostic',side_effect=SystemExit('fixture diagnostic')) if point=='constructor' else patch.object(collector,point,side_effect=SystemExit('fixture diagnostic')) if point in ('observe','snapshot') else patch.object(c.module,'_write',side_effect=write)
                with target:result=c.invoke()
                self.assertIsInstance(result,c.values.NativeReturned);self.assertEqual(c.owners.log.count('pool_stop'),1);self.assertEqual(c.owners.pool.executions,1)
    def test_generic_failure_snapshot_interrupt_does_not_pump_or_replace(self):
        primary=KeyboardInterrupt('fixture original');owner=order_fixture.StopOrderTests(methodName='runTest');c,order=owner.fixture(primary=primary);self.addCleanup(owner.doCleanups)
        collector=getattr(c.module,'NativeModelDiagnostic')
        def snapshot(*args):self.assertEqual(order.count('stop'),1);raise SystemExit('fixture diagnostic')
        with patch.object(collector,'snapshot',side_effect=snapshot):
            with self.assertRaises(KeyboardInterrupt) as caught:c.invoke()
        self.assertIs(caught.exception,primary);self.assertEqual(order.count('stop'),1);self.assertNotIn('status',order);self.assertEqual(order.count('events'),1);self.assertEqual(c.owners.pool.executions,1)
    def test_preentry_and_exact_never_entered_write_no_model_file(self):
        c=self.fixture()
        def refuse(*args):raise ValueError('fixture preentry')
        with self.assertRaises(Exception):c.invoke(hook=refuse)
        self.assertEqual(list(c.attempt_root.rglob('model-observations.json')),[])
        c=self.fixture();c.owners.mode='never_started'
        with self.assertRaises(c.values.NativeNeverEntered):c.invoke()
        self.assertEqual(list(c.attempt_root.rglob('model-observations.json')),[])

if __name__=='__main__':unittest.main()
