"""Fixed wrapper sidecar behavior using fake public owners only; no CO/provider calls."""
import json,stat,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_native_devin_text_v5 as f
import test_native_devin_stop_order_v5 as order_fixture
FIELDS={'sessionUpdate':'config_option_update','configOptions':[{'id':'model','type':'boolean','currentValue':False} for _ in range(17)]}
class WrapperOverflowTests(unittest.TestCase):
 def fixture(self):
  c=f.NativeDevinTextTests(methodName='runTest');c.setUp();self.addCleanup(c.doCleanups);parent=c.owners.api.DevinAdapter
  class Adapter(parent):
   def events(self,*args,**kwargs):
    self.kw['observe_model'](FIELDS,current_update=False)
    return super().events(*args,**kwargs)
  c.owners.api.DevinAdapter=Adapter;return c
 def read(self,c):
  paths=list(c.attempt_root.rglob('model-overflow.json'));self.assertEqual(len(paths),1);self.assertEqual(stat.S_IMODE(paths[0].stat().st_mode),0o600)
  value=json.loads(paths[0].read_text());self.assertEqual(value['authority'],'unqualified');self.assertEqual(value['version'],'PRI02-MODEL-OVERFLOW/1');self.assertEqual(set(value),{'version','authority','request_sha256','profile_sha256','attempt_ref','requested_model_id','status','first_overflow','limits'});return value
 def assert_calls(self,c):self.assertEqual(c.owners.pool.executions,1);self.assertEqual(c.owners.log.count('pool_stop'),1);self.assertNotIn('cancel_reserved',c.owners.log)
 def test_success_sidecar_once_after_stop_and_ending_original_evidence_unchanged(self):
  c=self.fixture();original=c.module._write;order=[]
  def write(path,value):
   if Path(path).name in ('ending.json','model-overflow.json'):
    self.assertEqual(c.owners.log.count('pool_stop'),1);order.append(Path(path).name)
   return original(path,value)
  with patch.object(c.module,'_write',side_effect=write):returned=c.invoke()
  value=self.read(c);self.assertEqual(value['status'],'overflow');self.assertEqual(value['first_overflow']['reason'],'option_count');self.assertFalse(value['first_overflow']['current_update']);self.assertEqual(order,['ending.json','model-overflow.json']);self.assert_calls(c)
  self.assertEqual(len(json.loads(next(c.attempt_root.rglob('model-observations.json')).read_text())),9)
  ending=json.loads(next(c.attempt_root.rglob('ending.json')).read_text())
  self.assertNotIn('first_overflow',json.dumps(ending));self.assertIsInstance(returned,c.values.NativeReturned)
 def test_strict_null_false_refusal_keeps_sidecar_without_authority(self):
  for changes in ({'effective_model':None},{'effective_model_verified':False}):
   with self.subTest(changes=changes):
    c=self.fixture();c.owners.ending_changes=changes;original=c.module._write;writes=[]
    def write(path,value):
     if Path(path).name=='model-overflow.json':self.assertEqual(c.owners.log.count('pool_stop'),1);writes.append(1)
     return original(path,value)
    with patch.object(c.module,'_write',side_effect=write):c.unknown()
    self.assertEqual(self.read(c)['first_overflow']['reason'],'option_count');self.assertEqual(writes,[1]);self.assertEqual(list(c.attempt_root.rglob('ending.json')),[]);self.assert_calls(c)
 def test_sidecar_snapshot_and_write_exception_or_baseexception_preserve_success(self):
  for point in ('snapshot','write'):
   for error in (RuntimeError('fixture marker'),ValueError('fixture marker size refusal'),KeyboardInterrupt('fixture marker')):
    with self.subTest(point=point,error=type(error).__name__):
     c=self.fixture();collector=c.module.NativeModelDiagnostic;original=c.module._write
     def snapshot(*args):self.assertEqual(c.owners.log.count('pool_stop'),1);raise error
     def write(path,value):
      if Path(path).name=='model-overflow.json':self.assertEqual(c.owners.log.count('pool_stop'),1);raise error
      return original(path,value)
     target=patch.object(collector,'overflow_snapshot',side_effect=snapshot) if point=='snapshot' else patch.object(c.module,'_write',side_effect=write)
     with target:result=c.invoke()
     self.assertIsInstance(result,c.values.NativeReturned);self.assert_calls(c);self.assertEqual(len(list(c.attempt_root.rglob('ending.json'))),1)
 def test_original_raised_hook_marked_without_replacing_owner_failure(self):
  c=self.fixture();c.owners.observe_error=True;c.unknown();marker=self.read(c)['first_overflow'];self.assertEqual(marker['original_hook'],'raised');self.assertEqual(marker['hook'],'observe');self.assert_calls(c)
 def test_primary_interrupt_and_marker_failure_no_extra_pumping(self):
  for error in (RuntimeError('fixture marker'),SystemExit('fixture marker')):
   with self.subTest(error=type(error).__name__):
    primary=KeyboardInterrupt('fixture original');owner=order_fixture.StopOrderTests(methodName='runTest');c,order=owner.fixture(primary=primary);self.addCleanup(owner.doCleanups);original=c.module._write;attempts=[]
    def write(path,value):
     if Path(path).name=='model-overflow.json':
      self.assertEqual(order.count('stop'),1);attempts.append(1);raise error
     return original(path,value)
    with patch.object(c.module,'_write',side_effect=write),self.assertRaises(KeyboardInterrupt) as caught:c.invoke()
    self.assertIs(caught.exception,primary);self.assertEqual(attempts,[1]);self.assertEqual(order.count('stop'),1);self.assertEqual(order.count('events'),1);self.assertNotIn('status',order);self.assertEqual(c.owners.pool.executions,1)
 def test_no_overflow_success_and_preentry_neverentered_omission(self):
  c=f.NativeDevinTextTests(methodName='runTest');c.setUp();self.addCleanup(c.doCleanups);c.invoke();value=self.read(c);self.assertEqual((value['status'],value['first_overflow']),('not_observed',None));self.assert_calls(c)
  c=self.fixture()
  def refuse(*args):raise ValueError('fixture local refusal')
  with self.assertRaises(Exception):c.invoke(hook=refuse)
  self.assertEqual(list(c.attempt_root.rglob('model-overflow.json')),[]);self.assertEqual(list(c.attempt_root.rglob('model-observations.json')),[])
  c=self.fixture();c.owners.mode='never_started'
  with self.assertRaises(c.values.NativeNeverEntered):c.invoke()
  self.assertEqual(list(c.attempt_root.rglob('model-overflow.json')),[]);self.assertEqual(list(c.attempt_root.rglob('model-observations.json')),[])
if __name__=='__main__':unittest.main()
